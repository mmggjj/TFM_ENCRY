-- Banco del motor completo: un maestro I2C recorre la secuencia tipica
-- del ESP32 (docs/mapa_registros.md) contra el nivel superior con los
-- anillos de verdad (modelos con jitter) por debajo.
--
-- Lo que un banco VHDL puede comprobar solo: identificacion, siembra sin
-- alarmas, clave generada y distinta en dos generaciones, etiqueta que
-- cambia con el reto, captura de bits crudos con contenido variado. Lo
-- que NO puede: que la etiqueta sea el CMAC correcto, porque la clave
-- sale del ruido y no se conoce de antemano. Para eso el banco vuelca
-- clave, reto y etiqueta a results/tb_motor_top.txt y
-- analysis/verifica_top.py lo comprueba con el modelo de referencia.
-- Es la misma verificacion cruzada que hara el ESP32 con mbedtls.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;

library unisim;
use unisim.sim_cfg.all;

entity tb_motor_top is
end entity tb_motor_top;

architecture sim of tb_motor_top is

  constant C_T     : time := 10 ns;      -- 100 MHz
  constant C_T_BIT : time := 2 us;       -- 500 kHz I2C
  constant C_DIR   : std_logic_vector(6 downto 0) := "0110000";

  signal clk, rst_n : std_logic := '0';
  signal scl, sda   : std_logic;
  signal m_sda_oe   : std_logic := '0';
  signal s_sda_oe   : std_logic;
  signal scl_m      : std_logic := '1';
  signal modo_test  : std_logic := '1';
  signal led_alarma : std_logic;
  signal fin        : boolean := false;

  function hex(v_in : std_logic_vector) return string is
    constant digitos : string := "0123456789abcdef";
    -- Se normaliza a indices descendentes: una concatenacion como
    -- x"FF" & v(119 downto 0) llega con rango ascendente y el troceado
    -- fallaba en tiempo de ejecucion.
    variable v : std_logic_vector(v_in'length - 1 downto 0) := v_in;
    variable r : string(1 to v'length / 4);
    variable n : integer;
  begin
    for i in 0 to v'length / 4 - 1 loop
      n := to_integer(unsigned(v(v'high - 4 * i downto v'high - 4 * i - 3)));
      r(i + 1) := digitos(n + 1);
    end loop;
    return r;
  end function;

begin

  clk <= '0' when fin else not clk after C_T / 2;
  scl <= scl_m;
  sda <= '0' when (m_sda_oe = '1' or s_sda_oe = '1') else '1';

  dut : entity work.motor_top
    generic map (G_DIR_I2C => C_DIR)
    port map (clk => clk, rst_n => rst_n, scl_in => scl, sda_in => sda,
              sda_oe => s_sda_oe, modo_test => modo_test,
              led_alarma => led_alarma);

  principal : process
    variable fallos : natural := 0;
    file f : text;
    variable l : line;

    procedure comprobar(cond : boolean; msg : string) is
    begin
      if cond then
        report "  [ok ] " & msg;
      else
        report "  [FALLO] " & msg severity error;
        fallos := fallos + 1;
      end if;
    end procedure;

    -- ---- maestro I2C -------------------------------------------------
    procedure arranque is
    begin
      m_sda_oe <= '0'; scl_m <= '1'; wait for C_T_BIT / 2;
      m_sda_oe <= '1';               wait for C_T_BIT / 2;
      scl_m    <= '0';               wait for C_T_BIT / 2;
    end procedure;

    procedure parada is
    begin
      m_sda_oe <= '1'; scl_m <= '0'; wait for C_T_BIT / 2;
      scl_m    <= '1';               wait for C_T_BIT / 2;
      m_sda_oe <= '0';               wait for C_T_BIT;
    end procedure;

    procedure enviar(dato : in std_logic_vector(7 downto 0); ack : out boolean) is
    begin
      for i in 7 downto 0 loop
        m_sda_oe <= not dato(i); wait for C_T_BIT / 4;
        scl_m <= '1'; wait for C_T_BIT / 2;
        scl_m <= '0'; wait for C_T_BIT / 4;
      end loop;
      m_sda_oe <= '0'; wait for C_T_BIT / 4;
      scl_m <= '1'; wait for C_T_BIT / 4;
      ack := (sda = '0');
      wait for C_T_BIT / 4;
      scl_m <= '0'; wait for C_T_BIT / 4;
    end procedure;

    procedure recibir(seguir : in boolean; dato : out std_logic_vector(7 downto 0)) is
      variable v : std_logic_vector(7 downto 0);
    begin
      m_sda_oe <= '0';
      for i in 7 downto 0 loop
        wait for C_T_BIT / 4;
        scl_m <= '1'; wait for C_T_BIT / 4;
        v(i) := sda;
        wait for C_T_BIT / 4;
        scl_m <= '0'; wait for C_T_BIT / 4;
      end loop;
      m_sda_oe <= '1' when seguir else '0';
      wait for C_T_BIT / 4;
      scl_m <= '1'; wait for C_T_BIT / 2;
      scl_m <= '0'; wait for C_T_BIT / 4;
      m_sda_oe <= '0';
      dato := v;
    end procedure;

    procedure escribir_reg(dir : in std_logic_vector(7 downto 0);
                           dato : in std_logic_vector(7 downto 0)) is
      variable ack : boolean;
    begin
      arranque;
      enviar(C_DIR & '0', ack);
      assert ack report "sin ACK a la direccion" severity failure;
      enviar(dir, ack);
      enviar(dato, ack);
      parada;
    end procedure;

    -- Lee n bytes consecutivos desde dir en v (byte 0 a la izquierda).
    procedure leer_bloque(dir : in std_logic_vector(7 downto 0);
                          n : in positive;
                          v : out std_logic_vector) is
      variable ack : boolean;
      variable b : std_logic_vector(7 downto 0);
    begin
      arranque;
      enviar(C_DIR & '0', ack);
      enviar(dir, ack);
      arranque;
      enviar(C_DIR & '1', ack);
      for i in 0 to n - 1 loop
        recibir(i < n - 1, b);
        v(v'high - 8 * i downto v'high - 8 * i - 7) := b;
      end loop;
      parada;
    end procedure;

    procedure leer_reg(dir : in std_logic_vector(7 downto 0);
                       dato : out std_logic_vector(7 downto 0)) is
      variable v : std_logic_vector(7 downto 0);
    begin
      leer_bloque(dir, 1, v);
      dato := v;
    end procedure;

    -- Sondea STATUS hasta que baje "ocupado".
    procedure esperar_libre(status : out std_logic_vector(7 downto 0)) is
      variable s : std_logic_vector(7 downto 0);
      variable n : natural := 0;
    begin
      loop
        leer_reg(x"02", s);
        exit when s(1) = '0';
        n := n + 1;
        assert n < 2000 report "el motor no se libera" severity failure;
      end loop;
      status := s;
    end procedure;

    variable b, status : std_logic_vector(7 downto 0);
    variable clave1, clave2, reto, etiqueta1, etiqueta2 : std_logic_vector(127 downto 0);
    variable aleatorio : std_logic_vector(255 downto 0);
    variable captura : std_logic_vector(127 downto 0);
    variable ack : boolean;
    variable distintos : natural;
  begin
    -- Anillos con jitter. El retardo por etapa se pone diez veces mayor
    -- que el fisico (1,5 ns en vez de 150 ps) SOLO en este banco: con la
    -- velocidad real la simulacion del sistema completo, que dura casi
    -- un milisegundo de I2C, superaba los veinte minutos de CPU sin
    -- terminar. El jitter relativo se conserva (sigma/tpd = 2,7 %).
    cfg.configurar(1.5, 0.04);
    rst_n <= '0';
    wait for 200 ns;
    rst_n <= '1';
    wait for 2 us;

    report "1) Identificacion";
    leer_reg(x"00", b);
    comprobar(b = x"A5", "ID = 0xA5");
    leer_reg(x"02", status);
    comprobar(status(7) = '1', "STATUS refleja modo test");
    comprobar(status(0) = '0', "sin sembrar al arrancar");

    report "2) Sembrar";
    -- K_D = 16: con el anillo lento del banco, un bit cada 16 x 15 ns = 240 ns,
    -- 24 ciclos de sistema, por encima de los 8 que exige el cruce de dominio.
    escribir_reg(x"04", x"04");
    escribir_reg(x"03", x"01");                 -- sembrar
    esperar_libre(status);
    comprobar(status(0) = '1', "sembrado");
    comprobar(status(2) = '0' and status(3) = '0', "sin alarmas de salud");

    report "3) Generar clave";
    escribir_reg(x"03", x"02");
    esperar_libre(status);
    comprobar(status(4) = '1', "clave valida");
    leer_bloque(x"10", 16, clave1);
    leer_bloque(x"40", 32, aleatorio);
    comprobar(clave1 = aleatorio(255 downto 128),
              "CLAVE = primeros 16 bytes de ALEATORIO");
    comprobar(clave1 /= (127 downto 0 => '0'), "clave no nula: " & hex(clave1));

    report "4) Reto-respuesta";
    reto := x"00112233445566778899aabbccddeeff";
    for i in 0 to 15 loop
      escribir_reg(std_logic_vector(to_unsigned(16#20# + i, 8)),
                   reto(127 - 8 * i downto 120 - 8 * i));
    end loop;
    escribir_reg(x"03", x"04");                 -- autenticar
    esperar_libre(status);
    comprobar(status(6) = '1', "etiqueta lista");
    leer_bloque(x"30", 16, etiqueta1);
    comprobar(etiqueta1 /= (127 downto 0 => '0'), "etiqueta: " & hex(etiqueta1));

    -- Otro reto, otra etiqueta.
    escribir_reg(x"20", x"FF");
    escribir_reg(x"03", x"04");
    esperar_libre(status);
    leer_bloque(x"30", 16, etiqueta2);
    comprobar(etiqueta1 /= etiqueta2, "la etiqueta cambia con el reto");

    report "5) Segunda clave distinta";
    escribir_reg(x"03", x"02");
    esperar_libre(status);
    leer_bloque(x"10", 16, clave2);
    comprobar(clave1 /= clave2, "dos generaciones dan claves distintas");

    report "6) Captura de bits crudos";
    escribir_reg(x"03", x"10");                 -- capturar
    for i in 1 to 400 loop                      -- 4096 bits a ~5 Mbit/s
      leer_reg(x"02", status);
      exit when status(5) = '1';
    end loop;
    comprobar(status(5) = '1', "buffer de captura lleno");
    escribir_reg(x"05", x"00");
    leer_bloque(x"80", 16, captura);
    distintos := 0;
    for i in 1 to 15 loop
      if captura(127 - 8 * i downto 120 - 8 * i) /=
         captura(135 - 8 * i downto 128 - 8 * i) then
        distintos := distintos + 1;
      end if;
    end loop;
    comprobar(distintos >= 8, "bits crudos con contenido variado: " & hex(captura));

    report "7) Sin modo test la clave no se lee";
    modo_test <= '0';
    wait for 1 us;
    leer_bloque(x"10", 16, captura);
    comprobar(captura = (127 downto 0 => '0'), "CLAVE devuelve ceros sin modo test");
    modo_test <= '1';

    -- Volcado para la verificacion cruzada en Python.
    file_open(f, "results/tb_motor_top.txt", write_mode);
    write(l, string'("clave1 ") & hex(clave1)); writeline(f, l);
    write(l, string'("reto1 ") & hex(reto)); writeline(f, l);
    write(l, string'("etiqueta1 ") & hex(etiqueta1)); writeline(f, l);
    write(l, string'("reto2 ") & hex(x"FF" & reto(119 downto 0))); writeline(f, l);
    write(l, string'("etiqueta2 ") & hex(etiqueta2)); writeline(f, l);
    write(l, string'("clave2 ") & hex(clave2)); writeline(f, l);
    write(l, string'("aleatorio1 ") & hex(aleatorio)); writeline(f, l);
    file_close(f);
    report "  volcado en results/tb_motor_top.txt";

    if fallos = 0 then
      report "tb_motor_top: 0 fallos" severity note;
    else
      report "tb_motor_top: " & integer'image(fallos) & " fallos" severity failure;
    end if;
    fin <= true;
    wait;
  end process principal;

end architecture sim;
