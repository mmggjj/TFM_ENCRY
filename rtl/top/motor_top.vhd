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
    G_DIR_I2C    : std_logic_vector(6 downto 0) := "0110000"
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

  -- Anillos y muestreo
  signal ro1, ro2      : std_logic;
  signal en_anillos    : std_logic := '0';
  signal kd_sel        : unsigned(4 downto 0) := to_unsigned(7, 5);
  signal bit_ro, stb_ro : std_logic;          -- dominio ro2
  signal bit_s, stb_s   : std_logic;          -- dominio clk

  -- Salud
  signal borrar_alm  : std_logic := '0';
  signal alm_rct, alm_apt, alm : std_logic;
  signal rct_max, apt_max : unsigned(15 downto 0);

  -- Captura
  signal cap_arranca : std_logic := '0';
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
  signal drbg_inst, drbg_reseed, drbg_gen : std_logic := '0';
  signal drbg_salida : std_logic_vector(255 downto 0);
  signal drbg_listo, drbg_ocupado, drbg_sembrado : std_logic;
  signal drbg_pet    : unsigned(31 downto 0);
  signal aleatorio   : std_logic_vector(255 downto 0) := (others => '0');

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
  type t_orden is (LIBRE, SEMBRANDO, ESPERA_DRBG, GENERANDO, CARGANDO_CLAVE,
                   GENERANDO_ALEATORIO, AUTENTICANDO);
  signal orden : t_orden := LIBRE;
  signal ocupado : std_logic;

  -- I2C y registros
  signal reg_dir   : std_logic_vector(7 downto 0);
  signal reg_wdato : std_logic_vector(7 downto 0);
  signal reg_we, reg_re : std_logic;
  signal reg_rdato : std_logic_vector(7 downto 0);
  signal status    : std_logic_vector(7 downto 0);

  function byte_de(v : std_logic_vector; i : integer) return std_logic_vector is
    -- byte i contando desde la izquierda de un vector (N-1 downto 0)
  begin
    return v(v'high - 8 * i downto v'high - 8 * i - 7);
  end function;

begin

  led_alarma <= alm;
  ocupado <= '0' when orden = LIBRE else '1';

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
    port map (ro1 => ro1, ro2 => ro2, rst_n => rst_n, kd_sel => kd_sel,
              bit_o => bit_ro, bit_stb => stb_ro);

  u_cdc : entity work.bit_cdc
    port map (clk_o => ro2, bit_o => bit_ro, stb_o => stb_ro,
              clk_d => clk, rst_n_d => rst_n, bit_d => bit_s, stb_d => stb_s);

  u_salud : entity work.health_tests
    port map (clk => clk, rst_n => rst_n, bit_i => bit_s, bit_stb => stb_s,
              borrar => borrar_alm, alarma_rct => alm_rct,
              alarma_apt => alm_apt, alarma => alm,
              rct_max => rct_max, apt_max => apt_max);

  u_captura : entity work.trng_capture
    generic map (G_PALABRAS => 512)
    port map (ro_clk => ro2, bit_dato => bit_ro, bit_stb => stb_ro,
              clk => clk, rst_n => rst_n, arranca => cap_arranca,
              lleno => cap_lleno, rd_dir => cap_dir, rd_dato => cap_dato);

  -- ------------------------------------------------------------------
  -- Criptografia
  -- ------------------------------------------------------------------
  u_drbg : entity work.ctr_drbg
    port map (clk => clk, rst_n => rst_n,
              instanciar => drbg_inst, resembrar => drbg_reseed,
              entropia => semilla(383 downto 128),
              nonce => semilla(127 downto 0),
              generar => drbg_gen, salida => drbg_salida,
              listo => drbg_listo, ocupado => drbg_ocupado,
              sembrado => drbg_sembrado, peticiones => drbg_pet);

  u_cmac : entity work.aes_cmac
    port map (clk => clk, rst_n => rst_n,
              carga_clave => cmac_carga, clave => clave,
              clave_lista => cmac_clave_lista,
              inicia => cmac_inicia, bloque => reto,
              bloque_val => cmac_bloque_val, ultimo => '1',
              n_bytes => to_unsigned(16, 5),
              etiqueta => etiqueta, listo => cmac_listo, ocupado => cmac_ocupado);

  -- ------------------------------------------------------------------
  -- I2C
  -- ------------------------------------------------------------------
  u_i2c : entity work.i2c_slave
    generic map (G_DIR => G_DIR_I2C)
    port map (clk => clk, rst_n => rst_n,
              scl_in => scl_in, sda_in => sda_in, sda_oe => sda_oe,
              reg_dir => reg_dir, reg_wdato => reg_wdato, reg_we => reg_we,
              reg_rdato => reg_rdato, reg_re => reg_re, ocupado => open);

  status <= modo_test & etiqueta_lista & cap_lleno & clave_valida &
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
      when 16#01# => reg_rdato <= x"01";
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
      when 16#10# to 16#1F# =>
        if modo_test = '1' then
          reg_rdato <= byte_de(clave, d - 16#10#);
        end if;
      when 16#30# to 16#3F# => reg_rdato <= byte_de(etiqueta, d - 16#30#);
      when 16#40# to 16#5F# => reg_rdato <= byte_de(aleatorio, d - 16#40#);
      when 16#80# to 16#FF# =>
        if modo_test = '1' then
          reg_rdato <= cap_dato;
        end if;
      when others => null;
    end case;
  end process p_lectura;

  -- ------------------------------------------------------------------
  -- Escrituras, ordenes y secuenciador
  -- ------------------------------------------------------------------
  p_control : process (clk, rst_n)
    variable d : integer range 0 to 255;
  begin
    if rst_n = '0' then
      en_anillos <= '0';
      kd_sel <= to_unsigned(7, 5);
      pagina <= (others => '0');
      borrar_alm <= '0'; cap_arranca <= '0';
      recogiendo <= '0'; n_recogidos <= (others => '0');
      semilla <= (others => '0'); siembra_es_reseed <= '0';
      drbg_inst <= '0'; drbg_reseed <= '0'; drbg_gen <= '0';
      aleatorio <= (others => '0');
      clave <= (others => '0'); clave_valida <= '0';
      cmac_carga <= '0'; cmac_inicia <= '0'; cmac_bloque_val <= '0';
      etiqueta_lista <= '0'; reto <= (others => '0');
      cmac_en_curso <= '0';
      orden <= LIBRE;

    elsif rising_edge(clk) then
      -- Pulsos de un ciclo
      borrar_alm <= '0'; cap_arranca <= '0';
      drbg_inst <= '0'; drbg_reseed <= '0'; drbg_gen <= '0';
      cmac_carga <= '0'; cmac_inicia <= '0'; cmac_bloque_val <= '0';

      en_anillos <= '1';    -- los anillos corren siempre tras el reset

      -- Escrituras del maestro
      if reg_we = '1' then
        d := to_integer(unsigned(reg_dir));
        case d is
          when 16#03# =>                              -- CONTROL
            if reg_wdato(3) = '1' then
              borrar_alm <= '1';
            end if;
            if reg_wdato(4) = '1' then
              cap_arranca <= '1';
            end if;
            if orden = LIBRE then
              if (reg_wdato(0) = '1' or reg_wdato(5) = '1') and alm = '0' then
                siembra_es_reseed <= reg_wdato(5);
                recogiendo  <= '1';
                n_recogidos <= (others => '0');
                orden <= SEMBRANDO;
              elsif reg_wdato(1) = '1' and drbg_sembrado = '1' then
                drbg_gen <= '1';
                orden <= GENERANDO;
              elsif reg_wdato(6) = '1' and drbg_sembrado = '1' then
                drbg_gen <= '1';
                orden <= GENERANDO_ALEATORIO;
              elsif reg_wdato(2) = '1' and clave_valida = '1' then
                cmac_inicia <= '1';
                etiqueta_lista <= '0';
                orden <= AUTENTICANDO;
                cmac_en_curso <= '0';
              end if;
            end if;
          when 16#04# => kd_sel <= unsigned(reg_wdato(4 downto 0));
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
          if alm = '1' then
            -- La fuente se degrado a mitad: se aborta sin sembrar.
            recogiendo <= '0';
            orden <= LIBRE;
          elsif stb_s = '1' and recogiendo = '1' then
            semilla <= semilla(382 downto 0) & bit_s;
            if n_recogidos = 383 then
              recogiendo <= '0';
              if siembra_es_reseed = '1' then
                drbg_reseed <= '1';
              else
                drbg_inst <= '1';
              end if;
              orden <= ESPERA_DRBG;
            else
              n_recogidos <= n_recogidos + 1;
            end if;
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
      end case;
    end if;
  end process p_control;

end architecture rtl;
