-- Nivel superior del motor criptografico de generacion de claves.
--
-- Une la fuente de entropia, los tests de salud, el buffer de captura, el
-- generador determinista y el autenticador detras de un esclavo I2C con
-- el mapa de registros de docs/mapa_registros.md.
--
-- Flujo de una clave:
--   anillos -> ero_core -> bit_cdc -> health_tests
--                                  -> recogida de 384 bits (semilla)
--                                  -> ctr_drbg.instanciar
--   ctr_drbg.generar (orden generar)   -> CLAVE (128 b) -> aes_cmac.carga
--   ctr_drbg.generar (orden aleatorio) -> ALEATORIO (256 b), generacion
--                                         independiente: nunca contiene la clave
--   RETO -> aes_cmac -> ETIQUETA
--
-- Lo unico atado a la FPGA son los dos anillos. El resto es RTL portable.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity motor_top is
  generic (
    G_ETAPAS_RO1 : positive := 7;      -- anillo muestreado
    G_ETAPAS_RO2 : positive := 5;      -- anillo de muestreo
    G_DIR_I2C    : std_logic_vector(6 downto 0) := "0110000";
    -- Divisor minimo (CFG_KD) con el que se acepta sembrar. Por debajo, el
    -- cruce de dominio pierde bits en silencio y la semilla acumula muy
    -- poco jitter; los tests de salud no lo detectan. Antes esto era una
    -- obligacion del maestro que el hardware no imponia; ahora la impone.
    -- 6 (K_D = 64) para anillos a velocidad fisica con reloj de 100 MHz.
    G_KD_MIN     : natural := 6;
    -- CFG_KD tras el reset. El maximo: un maestro que no lo escriba
    -- siembra con la tasa mas lenta y mas entropia por bit, nunca con una
    -- por debajo de la caracterizada. Antes arrancaba en 7 (K_D = 128).
    G_KD_RESET   : natural := 24;
    -- Bits del contador de peticiones que cuentan para agotarlo: con todos
    -- a uno el DRBG no genera mas hasta resembrar (SP 800-90A,
    -- reseed_interval). 32 en hardware; el banco lo baja para probarlo.
    G_PET_BITS   : positive := 32;
    -- Un solo nucleo AES para el generador y el autenticador. El
    -- secuenciador ya los serializa (nunca cifran a la vez), asi que el
    -- segundo nucleo era area sin uso: la primera optimizacion del
    -- capitulo de integrado. false deja un nucleo por bloque.
    G_AES_COMPARTIDO : boolean := true
  );
  port (
    clk       : in  std_logic;         -- 100 MHz de placa
    rst_n     : in  std_logic;
    scl_in    : in  std_logic;
    sda_in    : in  std_logic;
    sda_oe    : out std_logic;
    modo_test : in  std_logic;         -- habilita leer CLAVE y CAPTURA
    led_alarma : out std_logic
  );
end entity motor_top;

architecture rtl of motor_top is

  -- Resets: el de la placa, soltado sincrono en cada dominio
  signal rst_n_s       : std_logic;           -- dominio clk
  signal rst_n_ro      : std_logic;           -- dominio ro2

  -- Anillos y muestreo
  signal ro1, ro2      : std_logic;
  signal en_anillos    : std_logic := '0';
  signal kd_sel        : unsigned(4 downto 0) := to_unsigned(G_KD_RESET, 5);
  signal bit_ro, stb_ro : std_logic;          -- dominio ro2
  signal bit_s, stb_s   : std_logic;          -- dominio clk

  -- Salud
  signal borrar_alm  : std_logic := '0';
  signal alm_rct, alm_apt, alm : std_logic;
  signal ventana_fin : std_logic;
  signal rct_max, apt_max : unsigned(15 downto 0);
  -- Test de arranque (SP 800-90B 4.3): una ventana completa del APT, 1024
  -- muestras, sin alarma desde el reset o el ultimo borrado. Sin el no se
  -- siembra.
  signal arrancado   : std_logic := '0';
  -- La ultima orden escrita en CONTROL se ignoro. Sin esto el maestro no
  -- distingue un rechazo de una orden que acabo enseguida.
  signal rechazada   : std_logic := '0';

  -- Captura. Mientras hay una captura en curso no se siembra, y al reves:
  -- el buffer recoge los mismos bits crudos que la semilla, y una captura
  -- lanzada durante una siembra dejaba la semilla legible en modo test.
  signal cap_arranca : std_logic := '0';
  signal cap_en_curso : std_logic := '0';
  signal cap_lleno   : std_logic;
  signal cap_dir     : std_logic_vector(15 downto 0);
  signal cap_dato    : std_logic_vector(7 downto 0);
  signal pagina      : unsigned(1 downto 0) := (others => '0');

  -- Recogida de semilla: 256 entropia + 128 nonce = 384 bits
  signal recogiendo  : std_logic := '0';
  signal n_recogidos : unsigned(8 downto 0) := (others => '0');
  signal semilla     : std_logic_vector(383 downto 0) := (others => '0');
  signal siembra_es_reseed : std_logic := '0';

  -- DRBG
  signal drbg_inst, drbg_reseed, drbg_gen, drbg_borrar : std_logic := '0';
  signal drbg_salida : std_logic_vector(255 downto 0);
  signal drbg_listo, drbg_ocupado, drbg_sembrado, drbg_agotado : std_logic;
  signal drbg_pet    : unsigned(31 downto 0);
  signal aleatorio   : std_logic_vector(255 downto 0) := (others => '0');

  -- Nucleo AES compartido
  signal aes_arranca, cmac_aes_arranca, drbg_aes_arranca : std_logic;
  signal aes_borrar  : std_logic;
  signal aes_clave, cmac_aes_clave, drbg_aes_clave : std_logic_vector(127 downto 0);
  signal aes_dato, cmac_aes_dato, drbg_aes_dato : std_logic_vector(127 downto 0);
  signal aes_salida  : std_logic_vector(127 downto 0) := (others => '0');
  signal aes_listo   : std_logic := '0';

  -- Clave y autenticador
  signal clave       : std_logic_vector(127 downto 0) := (others => '0');
  signal clave_valida : std_logic := '0';
  signal cmac_carga, cmac_inicia, cmac_bloque_val : std_logic := '0';
  signal cmac_clave_lista, cmac_listo, cmac_ocupado : std_logic;
  signal etiqueta    : std_logic_vector(127 downto 0);
  signal etiqueta_lista : std_logic := '0';
  signal reto        : std_logic_vector(127 downto 0) := (others => '0');
  signal cmac_en_curso : std_logic := '0';

  -- Secuenciador de ordenes
  -- GENERANDO produce la clave y no deja nada legible; GENERANDO_ALEATORIO
  -- es otra generacion independiente cuyo resultado si va al registro
  -- ALEATORIO. Antes ambas cosas salian de la misma generacion y el
  -- registro ALEATORIO, legible sin modo test, contenia la clave.
  -- VALIDANDO espera a que se cierre la ventana del APT que contiene el
  -- ultimo bit de la semilla: hasta entonces esos bits no estan evaluados.
  -- ZEROIZANDO (orden borrar_todo) deja clave, ALEATORIO, RETO, semilla y
  -- el estado del DRBG a cero y carga la clave nula en el autenticador.
  type t_orden is (LIBRE, SEMBRANDO, VALIDANDO, ESPERA_DRBG, GENERANDO,
                   CARGANDO_CLAVE, GENERANDO_ALEATORIO, AUTENTICANDO,
                   ZEROIZANDO);
  signal orden : t_orden := LIBRE;
  signal ocupado : std_logic;

  -- I2C y registros
  signal reg_dir   : std_logic_vector(7 downto 0);
  signal reg_wdato : std_logic_vector(7 downto 0);
  signal reg_we, reg_re : std_logic;
  signal reg_rdato : std_logic_vector(7 downto 0);
  signal status    : std_logic_vector(7 downto 0);
  -- modo_test es un interruptor de la placa: dos biestables antes de
  -- usarlo en la maquina de estados.
  signal modo_test_s : std_logic_vector(1 downto 0) := (others => '0');

  function byte_de(v : std_logic_vector; i : integer) return std_logic_vector is
    -- byte i contando desde la izquierda de un vector (N-1 downto 0)
  begin
    return v(v'high - 8 * i downto v'high - 8 * i - 7);
  end function;

begin

  led_alarma <= alm;
  ocupado <= '0' when orden = LIBRE else '1';

  p_modo_test : process (clk, rst_n_s)
  begin
    if rst_n_s = '0' then
      modo_test_s <= (others => '0');
    elsif rising_edge(clk) then
      modo_test_s <= modo_test_s(0) & modo_test;
    end if;
  end process p_modo_test;

  -- ------------------------------------------------------------------
  -- Resets. El del anillo solo se suelta cuando el anillo oscila, y el
  -- anillo arranca cuando el dominio de sistema sale de su reset.
  -- ------------------------------------------------------------------
  u_rst_s : entity work.reset_sync
    port map (clk => clk, rst_n_in => rst_n, rst_n_out => rst_n_s);

  u_rst_ro : entity work.reset_sync
    port map (clk => ro2, rst_n_in => rst_n, rst_n_out => rst_n_ro);

  -- ------------------------------------------------------------------
  -- Fuente de entropia
  -- ------------------------------------------------------------------
  u_ro1 : entity work.ring_osc
    generic map (G_ETAPAS => G_ETAPAS_RO1)
    port map (en => en_anillos, osc => ro1);

  u_ro2 : entity work.ring_osc
    generic map (G_ETAPAS => G_ETAPAS_RO2)
    port map (en => en_anillos, osc => ro2);

  u_ero : entity work.ero_core
    port map (ro1 => ro1, ro2 => ro2, rst_n => rst_n_ro, kd_sel => kd_sel,
              bit_o => bit_ro, bit_stb => stb_ro);

  u_cdc : entity work.bit_cdc
    port map (clk_o => ro2, rst_n_o => rst_n_ro, bit_o => bit_ro, stb_o => stb_ro,
              clk_d => clk, rst_n_d => rst_n_s, bit_d => bit_s, stb_d => stb_s);

  u_salud : entity work.health_tests
    port map (clk => clk, rst_n => rst_n_s, bit_i => bit_s, bit_stb => stb_s,
              borrar => borrar_alm, alarma_rct => alm_rct,
              alarma_apt => alm_apt, alarma => alm,
              ventana_fin => ventana_fin,
              rct_max => rct_max, apt_max => apt_max);

  u_captura : entity work.trng_capture
    generic map (G_PALABRAS => 512)
    port map (ro_clk => ro2, rst_n_ro => rst_n_ro, bit_dato => bit_ro, bit_stb => stb_ro,
              clk => clk, rst_n => rst_n_s, arranca => cap_arranca,
              lleno => cap_lleno, rd_dir => cap_dir, rd_dato => cap_dato);

  -- ------------------------------------------------------------------
  -- Criptografia
  -- ------------------------------------------------------------------
  u_drbg : entity work.ctr_drbg
    generic map (G_PET_BITS => G_PET_BITS, G_AES_EXTERNO => G_AES_COMPARTIDO)
    port map (clk => clk, rst_n => rst_n_s,
              instanciar => drbg_inst, resembrar => drbg_reseed,
              borrar => drbg_borrar, agotado => drbg_agotado,
              aes_arranca_o => drbg_aes_arranca, aes_borrar_o => aes_borrar, aes_clave_o => drbg_aes_clave,
              aes_dato_o => drbg_aes_dato, aes_salida_i => aes_salida,
              aes_listo_i => aes_listo,
              entropia => semilla(383 downto 128),
              nonce => semilla(127 downto 0),
              generar => drbg_gen, salida => drbg_salida,
              listo => drbg_listo, ocupado => drbg_ocupado,
              sembrado => drbg_sembrado, peticiones => drbg_pet);

  u_cmac : entity work.aes_cmac
    generic map (G_AES_EXTERNO => G_AES_COMPARTIDO)
    port map (clk => clk, rst_n => rst_n_s,
              aes_arranca_o => cmac_aes_arranca, aes_borrar_o => open, aes_clave_o => cmac_aes_clave,
              aes_dato_o => cmac_aes_dato, aes_salida_i => aes_salida,
              aes_listo_i => aes_listo,
              carga_clave => cmac_carga, clave => clave,
              clave_lista => cmac_clave_lista,
              inicia => cmac_inicia, bloque => reto,
              bloque_val => cmac_bloque_val, ultimo => '1',
              n_bytes => to_unsigned(16, 5),
              etiqueta => etiqueta, listo => cmac_listo, ocupado => cmac_ocupado);

  -- El nucleo compartido. aes_enc captura clave y dato en el ciclo de
  -- arranca, asi que basta elegir las entradas por quien arranca; la
  -- salida y el listo van a los dos, y solo el que lanzo el cifrado esta
  -- esperandolos.
  g_nucleo_unico : if G_AES_COMPARTIDO generate
    aes_arranca <= cmac_aes_arranca or drbg_aes_arranca;
    aes_clave   <= cmac_aes_clave when cmac_aes_arranca = '1' else drbg_aes_clave;
    aes_dato    <= cmac_aes_dato  when cmac_aes_arranca = '1' else drbg_aes_dato;
    u_aes : entity work.aes_enc
      port map (clk => clk, rst_n => rst_n_s, arranca => aes_arranca, borrar => aes_borrar,
                clave => aes_clave, dato => aes_dato,
                salida => aes_salida, listo => aes_listo, ocupado => open);
  end generate g_nucleo_unico;

  -- ------------------------------------------------------------------
  -- I2C
  -- ------------------------------------------------------------------
  u_i2c : entity work.i2c_slave
    generic map (G_DIR => G_DIR_I2C)
    port map (clk => clk, rst_n => rst_n_s,
              scl_in => scl_in, sda_in => sda_in, sda_oe => sda_oe,
              reg_dir => reg_dir, reg_wdato => reg_wdato, reg_we => reg_we,
              reg_rdato => reg_rdato, reg_re => reg_re, ocupado => open);

  status <= modo_test_s(1) & etiqueta_lista & cap_lleno & clave_valida &
            alm_apt & alm_rct & ocupado & drbg_sembrado;

  cap_dir <= std_logic_vector(resize(pagina & unsigned(reg_dir(6 downto 0)), 16));

  -- Lectura combinacional del mapa.
  p_lectura : process (all)
    variable d : integer range 0 to 255;
  begin
    d := to_integer(unsigned(reg_dir));
    reg_rdato <= x"00";
    case d is
      when 16#00# => reg_rdato <= x"A5";
      when 16#01# => reg_rdato <= x"03";
      when 16#02# => reg_rdato <= status;
      when 16#04# => reg_rdato <= "000" & std_logic_vector(kd_sel);
      when 16#05# => reg_rdato <= "000000" & std_logic_vector(pagina);
      when 16#06# => reg_rdato <= std_logic_vector(rct_max(7 downto 0));
      when 16#07# => reg_rdato <= std_logic_vector(rct_max(15 downto 8));
      when 16#08# => reg_rdato <= std_logic_vector(apt_max(7 downto 0));
      when 16#09# => reg_rdato <= std_logic_vector(apt_max(15 downto 8));
      when 16#0A# => reg_rdato <= std_logic_vector(drbg_pet(7 downto 0));
      when 16#0B# => reg_rdato <= std_logic_vector(drbg_pet(15 downto 8));
      when 16#0C# => reg_rdato <= std_logic_vector(drbg_pet(23 downto 16));
      when 16#0D# => reg_rdato <= std_logic_vector(drbg_pet(31 downto 24));
      when 16#0E# => reg_rdato <= "00000" & drbg_agotado & rechazada & arrancado;
      when 16#10# to 16#1F# =>
        if modo_test_s(1) = '1' then
          reg_rdato <= byte_de(clave, d - 16#10#);
        end if;
      when 16#30# to 16#3F# =>
        -- Solo la etiqueta del reto actual: sin esto, tras borrar_todo o
        -- con un reto nuevo a medias seguia leyendose la anterior.
        if etiqueta_lista = '1' then
          reg_rdato <= byte_de(etiqueta, d - 16#30#);
        end if;
      when 16#40# to 16#5F# => reg_rdato <= byte_de(aleatorio, d - 16#40#);
      when 16#80# to 16#FF# =>
        if modo_test_s(1) = '1' then
          reg_rdato <= cap_dato;
        end if;
      when others => null;
    end case;
  end process p_lectura;

  -- ------------------------------------------------------------------
  -- Escrituras, ordenes y secuenciador
  -- ------------------------------------------------------------------
  p_control : process (clk, rst_n_s)
    variable d : integer range 0 to 255;
  begin
    if rst_n_s = '0' then
      en_anillos <= '0';
      kd_sel <= to_unsigned(G_KD_RESET, 5);
      pagina <= (others => '0');
      borrar_alm <= '0'; cap_arranca <= '0'; cap_en_curso <= '0';
      recogiendo <= '0'; n_recogidos <= (others => '0');
      semilla <= (others => '0'); siembra_es_reseed <= '0';
      drbg_inst <= '0'; drbg_reseed <= '0'; drbg_gen <= '0'; drbg_borrar <= '0';
      aleatorio <= (others => '0');
      clave <= (others => '0'); clave_valida <= '0';
      cmac_carga <= '0'; cmac_inicia <= '0'; cmac_bloque_val <= '0';
      etiqueta_lista <= '0'; reto <= (others => '0');
      cmac_en_curso <= '0';
      arrancado <= '0'; rechazada <= '0';
      orden <= LIBRE;

    elsif rising_edge(clk) then
      -- Pulsos de un ciclo
      borrar_alm <= '0'; cap_arranca <= '0';
      drbg_inst <= '0'; drbg_reseed <= '0'; drbg_gen <= '0'; drbg_borrar <= '0';
      cmac_carga <= '0'; cmac_inicia <= '0'; cmac_bloque_val <= '0';

      en_anillos <= '1';    -- los anillos corren siempre tras el reset

      -- cap_lleno sigue a 1 un ciclo despues de lanzar la captura siguiente
      -- (trng_capture lo baja al ver arranca): sin la segunda condicion toda
      -- captura salvo la primera se daba por acabada al instante y una
      -- siembra volvia a poder solapar una captura (revision del 27-10).
      if cap_lleno = '1' and cap_arranca = '0' then
        cap_en_curso <= '0';
      end if;

      -- Test de arranque. Borrar las alarmas reinicia la ventana del APT y
      -- obliga a pasarlo de nuevo.
      if borrar_alm = '1' then
        arrancado <= '0';
      elsif ventana_fin = '1' and alm = '0' then
        arrancado <= '1';
      end if;

      -- Escrituras del maestro
      if reg_we = '1' then
        d := to_integer(unsigned(reg_dir));
        case d is
          when 16#03# =>                              -- CONTROL
            if reg_wdato(3) = '1' then
              borrar_alm <= '1';
            end if;
            if orden = LIBRE then
              -- Una orden por escritura, la de mayor prioridad primero.
              -- Sembrar exige el test de arranque pasado, ninguna alarma, un
              -- divisor por encima del minimo (con CFG_KD bajo la semilla
              -- seria de calidad no garantizada y ningun test lo delataria)
              -- y ninguna captura en curso. Generar y aleatorio exigen
              -- ninguna alarma (con la fuente degradada no sale nada del
              -- motor, SP 800-90B 4.3) y el contador de peticiones sin
              -- agotar. Borrar_todo se atiende siempre.
              if reg_wdato(7) = '1' then
                clave <= (others => '0'); clave_valida <= '0';
                aleatorio <= (others => '0'); reto <= (others => '0');
                semilla <= (others => '0'); etiqueta_lista <= '0';
                drbg_borrar <= '1';
                cmac_carga <= '1';               -- clave nula al autenticador
                rechazada <= '0';
                orden <= ZEROIZANDO;
              elsif reg_wdato(0) = '1' or reg_wdato(5) = '1' then
                if alm = '0' and arrancado = '1' and cap_en_curso = '0'
                   and to_integer(kd_sel) >= G_KD_MIN
                   and (reg_wdato(0) = '1' or drbg_sembrado = '1') then   -- resembrar necesita estado
                  siembra_es_reseed <= reg_wdato(5);
                  recogiendo  <= '1';
                  n_recogidos <= (others => '0');
                  rechazada <= '0';
                  orden <= SEMBRANDO;
                else
                  rechazada <= '1';
                end if;
              elsif reg_wdato(1) = '1' then
                if drbg_sembrado = '1' and alm = '0' and drbg_agotado = '0' then
                  drbg_gen <= '1';
                  rechazada <= '0';
                  orden <= GENERANDO;
                else
                  rechazada <= '1';
                end if;
              elsif reg_wdato(6) = '1' then
                if drbg_sembrado = '1' and alm = '0' and drbg_agotado = '0' then
                  drbg_gen <= '1';
                  rechazada <= '0';
                  orden <= GENERANDO_ALEATORIO;
                else
                  rechazada <= '1';
                end if;
              elsif reg_wdato(2) = '1' then
                if clave_valida = '1' then
                  cmac_inicia <= '1';
                  etiqueta_lista <= '0';
                  rechazada <= '0';
                  orden <= AUTENTICANDO;
                  cmac_en_curso <= '0';
                else
                  rechazada <= '1';
                end if;
              elsif reg_wdato(4) = '1' then
                -- Capturar: solo en modo test (sin el, el buffer no se puede
                -- leer y una captura solo serviria para guardar bits), con
                -- el motor libre y sin otra captura en marcha.
                if modo_test_s(1) = '1' and cap_en_curso = '0' then
                  cap_arranca <= '1';
                  cap_en_curso <= '1';
                  rechazada <= '0';
                else
                  rechazada <= '1';
                end if;
              end if;
            elsif (reg_wdato(0) or reg_wdato(1) or reg_wdato(2) or reg_wdato(4) or
                   reg_wdato(5) or reg_wdato(6) or reg_wdato(7)) = '1' then
              rechazada <= '1';          -- orden con el motor ocupado
            end if;
          when 16#04# =>
            -- Solo con el motor libre: cambiar la tasa de muestreo a mitad
            -- de un sembrado invalidaria el modelo estocastico de esa
            -- semilla. Con una orden en curso la escritura se ignora.
            if orden = LIBRE then
              kd_sel <= unsigned(reg_wdato(4 downto 0));
            end if;
          when 16#05# => pagina <= unsigned(reg_wdato(1 downto 0));
          when 16#20# to 16#2F# =>
            reto(127 - 8 * (d - 16#20#) downto 120 - 8 * (d - 16#20#)) <= reg_wdato;
            etiqueta_lista <= '0';
          when others => null;
        end case;
      end if;

      -- Secuenciador
      case orden is
        when LIBRE => null;

        when SEMBRANDO =>
          if alm = '1' or borrar_alm = '1' then
            -- La fuente se degrado a mitad, o se reinicio la ventana del APT
            -- y estos bits ya no quedarian evaluados: se aborta sin sembrar.
            recogiendo <= '0';
            rechazada <= '1';
            orden <= LIBRE;
          elsif stb_s = '1' and recogiendo = '1' then
            semilla <= semilla(382 downto 0) & bit_s;
            if n_recogidos = 383 then
              recogiendo <= '0';
              orden <= VALIDANDO;
            else
              n_recogidos <= n_recogidos + 1;
            end if;
          end if;

        when VALIDANDO =>
          -- La ventana que se cierre aqui contiene el ultimo bit de la
          -- semilla, y las anteriores ya se cerraron sin alarma. Su veredicto
          -- llega en el mismo ciclo que ventana_fin.
          if alm = '1' or borrar_alm = '1' then
            rechazada <= '1';
            orden <= LIBRE;
          elsif ventana_fin = '1' then
            if siembra_es_reseed = '1' then
              drbg_reseed <= '1';
            else
              drbg_inst <= '1';
            end if;
            orden <= ESPERA_DRBG;
          end if;

        when ESPERA_DRBG =>
          if drbg_listo = '1' then
            orden <= LIBRE;
          end if;

        when GENERANDO =>
          if drbg_listo = '1' then
            -- Solo la clave. Los otros 128 bits se descartan: no deben
            -- quedar en ningun registro legible.
            clave     <= drbg_salida(255 downto 128);
            clave_valida <= '0';
            etiqueta_lista <= '0';
            cmac_carga <= '1';
            orden <= CARGANDO_CLAVE;
          end if;

        when CARGANDO_CLAVE =>
          if cmac_clave_lista = '1' then
            clave_valida <= '1';
            orden <= LIBRE;
          end if;

        when GENERANDO_ALEATORIO =>
          if drbg_listo = '1' then
            aleatorio <= drbg_salida;
            orden <= LIBRE;
          end if;

        when AUTENTICANDO =>
          if cmac_en_curso = '0' then
            cmac_bloque_val <= '1';      -- el reto es un bloque completo
            cmac_en_curso <= '1';
          elsif cmac_listo = '1' then
            etiqueta_lista <= '1';
            cmac_en_curso <= '0';
            orden <= LIBRE;
          end if;

        when ZEROIZANDO =>
          -- El DRBG se borra en un ciclo; el autenticador tarda en expandir
          -- la clave nula. clave_valida se queda a 0.
          if cmac_clave_lista = '1' and drbg_ocupado = '0' then
            orden <= LIBRE;
          end if;
      end case;
    end if;
  end process p_control;

end architecture rtl;
