-- Esclavo I2C con puntero de registro.
--
-- Es la interfaz de producto del motor: el ESP32 pide claves y resultados
-- criptograficos por aqui. Se elige I2C y no SPI porque es lo que usan los
-- elementos seguros comerciales, son dos pines en vez de cuatro y permite
-- varios dispositivos en el mismo bus.
--
-- La via de volcado masivo de entropia en crudo NO pasa por aqui: a 400
-- kHz sacar los megabytes que exige SP 800-90B llevaria horas, y ademas
-- dejar accesible la entropia cruda en un producto es un agujero de
-- seguridad. Esa via es un puerto de test aparte, que en silicio de
-- produccion se deshabilita de forma permanente.
--
-- Protocolo, el habitual de puntero de registro:
--   escritura: START, dir+W, ACK, registro, ACK, dato, ACK, ..., STOP
--   lectura:   START, dir+W, ACK, registro, ACK, START repetido,
--              dir+R, ACK, dato, ACK, ..., dato, NACK, STOP
-- El puntero se autoincrementa, asi que una lectura larga saca un bloque
-- entero sin repetir la direccion.
--
-- Independiente de la tecnologia: logica sintetizable estandar, sin
-- primitivas de fabricante. Las salidas son de colector abierto, como
-- exige I2C: se entrega la habilitacion de bajada, nunca un nivel alto.
--
-- SIN ESTIRAMIENTO DE RELOJ, a proposito. El esclavo debe contestar
-- dentro de un tiempo de bit, y le sobra: a 400 kHz con reloj de sistema
-- de 100 MHz hay 250 ciclos por periodo de SCL, frente a los 11 que
-- tarda una ronda de AES. Lo que NO cabe en ese tiempo son las
-- operaciones largas, como generar una clave o sembrar el generador. Para
-- esas el maestro lanza el comando, sondea un bit de estado y recoge el
-- resultado despues, que es como funcionan los elementos seguros
-- comerciales. Si en el futuro se quisiera estirar el reloj, habria que
-- sacar ademas una habilitacion de bajada para SCL.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity i2c_slave is
  generic (
    -- Direccion de 7 bits. 0x30 no choca con los perifericos habituales
    -- de un montaje con ESP32 [PENDIENTE: comprobar en el banco real].
    G_DIR      : std_logic_vector(6 downto 0) := "0110000";
    -- Ciclos de reloj de sistema que debe durar un nivel para darlo por
    -- bueno. I2C exige suprimir pulsos de hasta 50 ns; a 100 MHz son 5.
    G_FILTRO   : positive := 5
  );
  port (
    clk       : in  std_logic;
    rst_n     : in  std_logic;

    -- Bus. Entradas ya en el dominio del pad; salidas de colector
    -- abierto: '1' = tirar de la linea a nivel bajo.
    scl_in    : in  std_logic;
    sda_in    : in  std_logic;
    sda_oe    : out std_logic;

    -- Banco de registros
    reg_dir   : out std_logic_vector(7 downto 0);
    reg_wdato : out std_logic_vector(7 downto 0);
    reg_we    : out std_logic;                     -- un ciclo
    reg_rdato : in  std_logic_vector(7 downto 0);
    reg_re    : out std_logic;                     -- un ciclo, antes de leer

    -- Util para los tests de salud y para depurar
    ocupado   : out std_logic
  );
end entity i2c_slave;

architecture rtl of i2c_slave is

  -- Sincronizacion y filtrado de pulsos
  signal scl_s, sda_s   : std_logic_vector(2 downto 0) := (others => '1');
  signal scl_f, sda_f   : std_logic := '1';
  signal cnt_scl        : unsigned(7 downto 0) := (others => '0');
  signal cnt_sda        : unsigned(7 downto 0) := (others => '0');
  signal scl_f_d, sda_f_d : std_logic := '1';

  signal scl_sube, scl_baja : std_logic;
  signal cond_start, cond_stop : std_logic;

  type t_estado is (REPOSO, DIRECCION, ACK_DIR, RECIBE, ACK_RECIBE,
                    ENVIA, ACK_ENVIA);
  signal estado : t_estado := REPOSO;

  signal desp      : std_logic_vector(7 downto 0) := (others => '0');
  signal n_bit     : unsigned(3 downto 0) := (others => '0');
  signal leyendo   : std_logic := '0';   -- la transaccion es de lectura
  signal puntero   : unsigned(7 downto 0) := (others => '0');
  signal hay_punt  : std_logic := '0';   -- ya se recibio el registro
  -- El ultimo byte recibido fue dato, no puntero. Hace falta porque el
  -- puntero se incrementa un estado despues de escribir: durante el pulso
  -- de escritura la direccion debe seguir siendo la de ese byte.
  signal fue_dato  : std_logic := '0';
  signal tirar     : std_logic := '0';   -- valor de sda_oe

  attribute ASYNC_REG : string;
  attribute ASYNC_REG of scl_s : signal is "TRUE";
  attribute ASYNC_REG of sda_s : signal is "TRUE";

begin

  sda_oe  <= tirar;
  reg_dir <= std_logic_vector(puntero);
  ocupado <= '0' when estado = REPOSO else '1';

  -- ----------------------------------------------------------------
  -- Entrada: dos biestables de sincronizacion y filtro de pulsos. El
  -- nivel solo se da por bueno tras G_FILTRO muestras iguales, que es lo
  -- que pide la norma para suprimir espurios.
  -- ----------------------------------------------------------------
  p_entrada : process (clk, rst_n)
  begin
    if rst_n = '0' then
      scl_s   <= (others => '1');
      sda_s   <= (others => '1');
      scl_f   <= '1';
      sda_f   <= '1';
      cnt_scl <= (others => '0');
      cnt_sda <= (others => '0');
      scl_f_d <= '1';
      sda_f_d <= '1';
    elsif rising_edge(clk) then
      scl_s <= scl_s(1 downto 0) & scl_in;
      sda_s <= sda_s(1 downto 0) & sda_in;

      if scl_s(2) = scl_f then
        cnt_scl <= (others => '0');
      elsif cnt_scl = G_FILTRO - 1 then
        scl_f   <= scl_s(2);
        cnt_scl <= (others => '0');
      else
        cnt_scl <= cnt_scl + 1;
      end if;

      if sda_s(2) = sda_f then
        cnt_sda <= (others => '0');
      elsif cnt_sda = G_FILTRO - 1 then
        sda_f   <= sda_s(2);
        cnt_sda <= (others => '0');
      else
        cnt_sda <= cnt_sda + 1;
      end if;

      scl_f_d <= scl_f;
      sda_f_d <= sda_f;
    end if;
  end process p_entrada;

  scl_sube <= '1' when scl_f = '1' and scl_f_d = '0' else '0';
  scl_baja <= '1' when scl_f = '0' and scl_f_d = '1' else '0';
  -- START y STOP son transiciones de SDA con SCL en alto.
  cond_start <= '1' when scl_f = '1' and sda_f = '0' and sda_f_d = '1' else '0';
  cond_stop  <= '1' when scl_f = '1' and sda_f = '1' and sda_f_d = '0' else '0';

  -- ----------------------------------------------------------------
  -- Maquina de estados
  -- ----------------------------------------------------------------
  p_fsm : process (clk, rst_n)
  begin
    if rst_n = '0' then
      estado   <= REPOSO;
      desp     <= (others => '0');
      n_bit    <= (others => '0');
      leyendo  <= '0';
      puntero  <= (others => '0');
      hay_punt <= '0';
      tirar    <= '0';
      reg_we   <= '0';
      reg_re   <= '0';
      reg_wdato <= (others => '0');

    elsif rising_edge(clk) then
      reg_we <= '0';
      reg_re <= '0';

      -- START y STOP mandan sobre cualquier estado.
      if cond_start = '1' then
        estado   <= DIRECCION;
        n_bit    <= (others => '0');
        tirar    <= '0';
        hay_punt <= '0';        -- un START repetido reusa el puntero ya fijado
                                -- pero obliga a releer la direccion del esclavo
      elsif cond_stop = '1' then
        estado <= REPOSO;
        tirar  <= '0';

      else
        case estado is

          when REPOSO =>
            tirar <= '0';

          -- Ocho bits: siete de direccion y el de lectura/escritura.
          when DIRECCION =>
            if scl_sube = '1' then
              desp  <= desp(6 downto 0) & sda_f;
              n_bit <= n_bit + 1;
            elsif scl_baja = '1' and n_bit = 8 then
              n_bit <= (others => '0');
              if desp(7 downto 1) = G_DIR then
                leyendo <= desp(0);
                tirar   <= '1';           -- ACK
                estado  <= ACK_DIR;
                if desp(0) = '1' then
                  reg_re <= '1';          -- adelanta el primer dato a enviar
                end if;
              else
                estado <= REPOSO;         -- no es para nosotros
                tirar  <= '0';
              end if;
            end if;

          -- Al soltar el ACK hay que sacar YA el bit mas significativo:
          -- el maestro lo muestrea en el flanco de subida inmediato. Si
          -- se esperase al siguiente flanco de bajada, todo el byte
          -- saldria desplazado un bit.
          when ACK_DIR =>
            if scl_baja = '1' then
              if leyendo = '1' then
                tirar  <= not reg_rdato(7);
                desp   <= reg_rdato(6 downto 0) & '0';
                n_bit  <= to_unsigned(1, n_bit'length);
                estado <= ENVIA;
              else
                tirar  <= '0';
                estado <= RECIBE;
              end if;
            end if;

          -- Escritura del maestro: primer byte es el puntero, el resto
          -- son datos.
          when RECIBE =>
            if scl_sube = '1' then
              desp  <= desp(6 downto 0) & sda_f;
              n_bit <= n_bit + 1;
            elsif scl_baja = '1' and n_bit = 8 then
              n_bit <= (others => '0');
              tirar <= '1';               -- ACK
              if hay_punt = '0' then
                puntero  <= unsigned(desp);
                hay_punt <= '1';
                fue_dato <= '0';
              else
                reg_wdato <= desp;
                reg_we    <= '1';
                fue_dato  <= '1';
              end if;
              estado <= ACK_RECIBE;
            end if;

          when ACK_RECIBE =>
            if scl_baja = '1' then
              tirar <= '0';
              if fue_dato = '1' then
                puntero <= puntero + 1;   -- autoincremento tras escribir
              end if;
              estado <= RECIBE;
            end if;

          -- Lectura: se envia el byte apuntado y el puntero avanza.
          when ENVIA =>
            if scl_baja = '1' then
              if n_bit = 8 then
                n_bit   <= (others => '0');
                tirar   <= '0';           -- suelta la linea para leer el ACK
                puntero <= puntero + 1;
                estado  <= ACK_ENVIA;
              else
                tirar <= not desp(7);     -- colector abierto: solo baja
                desp  <= desp(6 downto 0) & '0';
                n_bit <= n_bit + 1;
              end if;
            end if;

          when ACK_ENVIA =>
            if scl_sube = '1' then
              if sda_f = '0' then         -- ACK del maestro: sigue leyendo
                reg_re <= '1';
              else                        -- NACK: fin de la transaccion
                estado <= REPOSO;
              end if;
            elsif scl_baja = '1' then
              -- El puntero ya se incremento al entrar aqui, asi que
              -- reg_rdato es el byte siguiente.
              tirar  <= not reg_rdato(7);
              desp   <= reg_rdato(6 downto 0) & '0';
              n_bit  <= to_unsigned(1, n_bit'length);
              estado <= ENVIA;
            end if;

        end case;
      end if;
    end if;
  end process p_fsm;

end architecture rtl;
