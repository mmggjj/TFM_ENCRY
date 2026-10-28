-- Banco de pruebas del esclavo I2C.
--
-- Modela un maestro I2C y un banco de registros. Los cuatro primeros
-- pasos son el uso normal, lo que tiene que salir bien para que el ESP32
-- hable con el motor: que el esclavo responde a su direccion y solo a la
-- suya, que una escritura de varios bytes avanza el puntero, que una
-- lectura con arranque repetido devuelve lo que hay y que tambien
-- autoincrementa.
--
-- Del paso 5 en adelante es el bus bajo abuso. El I2C es la unica puerta
-- del chip y un maestro roto, un cable suelto o un espurio no pueden
-- dejar al esclavo colgado, tirando de SDA o escribiendo medio byte:
--   5) espurios mas cortos que el filtro, en reposo y dentro de un byte,
--      en SDA con SCL alto (seria START+STOP) y en SCL en su fase baja;
--   6) STOP a mitad de byte: no se escribe nada y la siguiente va bien;
--   7) START repetido a mitad de byte: tampoco, y la lectura que sigue
--      sale del puntero fijado;
--   8) tras una direccion ajena, los bytes siguientes se ignoran;
--   9) el puntero sobrevive al STOP: una lectura sin fijarlo lee de el;
--  10) la lectura da la vuelta en 0xFF;
--  11) el maestro desaparece con SCL parado y el esclavo tirando de SDA
--      en el ACK: la guarda lo suelta a los G_GUARDA ciclos;
--  12) el maestro hace STOP tras un ACK de lectura en vez de NACK: si el
--      byte siguiente empieza por 1 el esclavo suelta y el STOP vale; si
--      empieza por 0 el esclavo retiene SDA (asi es I2C) y la guarda
--      resuelve el bloqueo;
--  13) bus a 1 MHz y a 100 kHz con reloj de sistema de 20 MHz.
-- Una propiedad PSL vigila en cada ciclo que el esclavo nunca tira de SDA
-- estando en reposo, y el banco cuenta los pulsos de escritura al banco
-- de registros para asegurar que ninguna transaccion abortada escribe.
--
-- El bus se modela con un solo asignador por linea en lugar de con
-- resolucion y niveles debiles: asi las entradas del esclavo son siempre
-- '0' o '1' y no hay que preocuparse de que 'H' no sea igual a '1' al
-- comparar.
--
--   python rtl/run_tb.py i2c

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_i2c_slave is
end entity tb_i2c_slave;

architecture sim of tb_i2c_slave is

  constant C_DIR    : std_logic_vector(6 downto 0) := "0110000";  -- 0x30
  constant C_T_CLK  : time := 50 ns;      -- 20 MHz de sistema
  constant C_GUARDA : positive := 2000;   -- 100 us a 20 MHz (en hardware, 35 ms)
  constant C_GLITCH : time := 100 ns;     -- 2 ciclos: por debajo del filtro (5)

  signal clk    : std_logic := '0';
  signal rst_n  : std_logic := '0';

  signal m_sda_oe : std_logic := '0';     -- el maestro tira de SDA
  signal s_sda_oe : std_logic;            -- el esclavo tira de SDA
  signal scl      : std_logic := '1';
  signal sda      : std_logic;

  -- Tiempo de bit del maestro; el paso 13 lo cambia.
  signal t_bit    : time := 2 us;         -- 500 kHz

  signal reg_dir   : std_logic_vector(7 downto 0);
  signal reg_wdato : std_logic_vector(7 downto 0);
  signal reg_we    : std_logic;
  signal reg_rdato : std_logic_vector(7 downto 0);
  signal reg_re    : std_logic;
  signal ocupado   : std_logic;
  signal n_we      : natural := 0;        -- pulsos de escritura vistos

  type t_mem is array (0 to 255) of std_logic_vector(7 downto 0);

  -- El patron inicial se pone con un valor inicial de la senal, NO desde
  -- el proceso de estimulo: si dos procesos asignan la misma senal hay dos
  -- fuentes y la resolucion de valores distintos da 'X'. Es lo que hacia
  -- fallar la primera version de este banco.
  function patron_inicial return t_mem is
    variable m : t_mem;
  begin
    for i in 0 to 255 loop
      m(i) := std_logic_vector(to_unsigned(i, 8)) xor x"5A";
    end loop;
    return m;
  end function;

  signal mem : t_mem := patron_inicial;

  signal fin : boolean := false;

begin

  clk <= '0' when fin else not clk after C_T_CLK / 2;

  -- Linea con resistencia de subida: baja si alguien tira, alta si nadie.
  sda <= '0' when (m_sda_oe = '1' or s_sda_oe = '1') else '1';

  dut : entity work.i2c_slave
    generic map (G_DIR => C_DIR, G_FILTRO => 5, G_GUARDA => C_GUARDA)
    port map (
      clk => clk, rst_n => rst_n,
      scl_in => scl, sda_in => sda, sda_oe => s_sda_oe,
      reg_dir => reg_dir, reg_wdato => reg_wdato, reg_we => reg_we,
      reg_rdato => reg_rdato, reg_re => reg_re, ocupado => ocupado);

  -- Banco de registros: lectura combinacional, escritura sincrona.
  reg_rdato <= mem(to_integer(unsigned(reg_dir)));

  p_mem : process (clk)
  begin
    if rising_edge(clk) then
      if reg_we = '1' then
        mem(to_integer(unsigned(reg_dir))) <= reg_wdato;
        n_we <= n_we + 1;
      end if;
    end if;
  end process p_mem;

  -- Propiedad vigilada en cada ciclo de reloj de toda la simulacion.
  propiedades : block is
    default clock is rising_edge(clk);
  begin
    p_suelta_en_reposo : assert always (ocupado = '0') -> (s_sda_oe = '0')
      report "el esclavo tira de SDA estando en reposo";
    c_tiraba_y_solto : cover {s_sda_oe = '1'; s_sda_oe = '0'};
  end block propiedades;

  principal : process
    variable fallos : natural := 0;

    procedure comprobar(cond : boolean; msg : string) is
    begin
      if cond then
        report "  [ok ] " & msg;
      else
        report "  [FALLO] " & msg severity error;
        fallos := fallos + 1;
      end if;
    end procedure;

    procedure arranque is
    begin
      m_sda_oe <= '0'; scl <= '1'; wait for t_bit / 2;
      m_sda_oe <= '1';             wait for t_bit / 2;   -- SDA baja con SCL alto
      scl      <= '0';             wait for t_bit / 2;
    end procedure;

    procedure parada is
    begin
      m_sda_oe <= '1'; scl <= '0'; wait for t_bit / 2;
      scl      <= '1';             wait for t_bit / 2;
      m_sda_oe <= '0';             wait for t_bit;       -- SDA sube con SCL alto
    end procedure;

    -- Envia un byte y devuelve true si el esclavo lo reconoce.
    procedure enviar(dato : in std_logic_vector(7 downto 0);
                     ack  : out boolean) is
    begin
      for i in 7 downto 0 loop
        m_sda_oe <= not dato(i);          -- colector abierto
        wait for t_bit / 4;
        scl <= '1'; wait for t_bit / 2;
        scl <= '0'; wait for t_bit / 4;
      end loop;
      m_sda_oe <= '0';                    -- suelta para leer el ACK
      wait for t_bit / 4;
      scl <= '1'; wait for t_bit / 4;
      ack := (sda = '0');
      wait for t_bit / 4;
      scl <= '0'; wait for t_bit / 4;
    end procedure;

    -- Envia solo los n_bits primeros bits de un byte y se queda con SCL
    -- bajo: lo que precede a un STOP o a un START repetido fuera de sitio.
    procedure enviar_parcial(dato : in std_logic_vector(7 downto 0);
                             n_bits : in positive) is
    begin
      for i in 7 downto 8 - n_bits loop
        m_sda_oe <= not dato(i);
        wait for t_bit / 4;
        scl <= '1'; wait for t_bit / 2;
        scl <= '0'; wait for t_bit / 4;
      end loop;
      m_sda_oe <= '0';
    end procedure;

    -- Como enviar, con dos espurios dentro del byte: en el bit 4 (que debe
    -- ser '1') un pulso a bajo en SDA con SCL alto, que sin filtro seria
    -- un START seguido de un STOP; en el bit 2 un pulso a alto en SCL en
    -- su fase baja, que sin filtro seria un flanco de muestreo de mas.
    procedure enviar_con_espurios(dato : in std_logic_vector(7 downto 0);
                                  ack  : out boolean) is
    begin
      assert dato(4) = '1' report "el dato del paso 5 necesita el bit 4 a uno" severity failure;
      for i in 7 downto 0 loop
        m_sda_oe <= not dato(i);
        wait for t_bit / 4;
        scl <= '1';
        if i = 4 then
          wait for t_bit / 8;
          m_sda_oe <= '1'; wait for C_GLITCH; m_sda_oe <= '0';
          wait for t_bit / 2 - t_bit / 8 - C_GLITCH;
        else
          wait for t_bit / 2;
        end if;
        scl <= '0';
        if i = 2 then
          wait for t_bit / 8;
          scl <= '1'; wait for C_GLITCH; scl <= '0';
          wait for t_bit / 4 - t_bit / 8 - C_GLITCH;
        else
          wait for t_bit / 4;
        end if;
      end loop;
      m_sda_oe <= '0';
      wait for t_bit / 4;
      scl <= '1'; wait for t_bit / 4;
      ack := (sda = '0');
      wait for t_bit / 4;
      scl <= '0'; wait for t_bit / 4;
    end procedure;

    -- Lee un byte; con seguir = true responde ACK para pedir mas.
    procedure recibir(seguir : in boolean;
                      dato   : out std_logic_vector(7 downto 0)) is
      variable v : std_logic_vector(7 downto 0);
    begin
      m_sda_oe <= '0';
      for i in 7 downto 0 loop
        wait for t_bit / 4;
        scl <= '1'; wait for t_bit / 4;
        v(i) := sda;
        wait for t_bit / 4;
        scl <= '0'; wait for t_bit / 4;
      end loop;
      m_sda_oe <= '1' when seguir else '0';
      wait for t_bit / 4;
      scl <= '1'; wait for t_bit / 2;
      scl <= '0'; wait for t_bit / 4;
      m_sda_oe <= '0';
      dato := v;
    end procedure;

    -- Escritura completa de un byte en un registro, con STOP.
    procedure escribir(reg, dato : in std_logic_vector(7 downto 0)) is
      variable a : boolean;
    begin
      arranque;
      enviar(C_DIR & '0', a);
      enviar(reg, a);
      enviar(dato, a);
      parada;
    end procedure;

    -- Lectura completa de un byte de un registro, con STOP.
    procedure leer(reg : in std_logic_vector(7 downto 0);
                   dato : out std_logic_vector(7 downto 0)) is
      variable a : boolean;
    begin
      arranque;
      enviar(C_DIR & '0', a);
      enviar(reg, a);
      arranque;
      enviar(C_DIR & '1', a);
      recibir(false, dato);
      parada;
    end procedure;

    variable ack   : boolean;
    variable byte  : std_logic_vector(7 downto 0);
    variable we0   : natural;
    variable t0    : time;
    variable dt    : time;
  begin
    rst_n <= '0';
    wait for 1 us;
    rst_n <= '1';
    wait for 1 us;

    report "1) Direccionamiento";
    arranque;
    enviar(C_DIR & '0', ack);
    comprobar(ack, "reconoce su propia direccion en escritura");

    report "2) Escritura de varios bytes con autoincremento";
    enviar(x"10", ack);                    -- puntero
    comprobar(ack, "reconoce el byte de puntero");
    enviar(x"A1", ack);
    comprobar(ack, "reconoce el primer dato");
    enviar(x"B2", ack);
    comprobar(ack, "reconoce el segundo dato");
    enviar(x"C3", ack);
    comprobar(ack, "reconoce el tercer dato");
    parada;
    wait for 2 us;
    comprobar(mem(16) = x"A1", "el primer dato fue a la direccion 0x10");
    comprobar(mem(17) = x"B2", "el segundo avanzo a 0x11");
    comprobar(mem(18) = x"C3", "el tercero avanzo a 0x12");

    report "3) Lectura con arranque repetido y autoincremento";
    arranque;
    enviar(C_DIR & '0', ack);
    comprobar(ack, "segunda transaccion, direccion reconocida");
    enviar(x"10", ack);
    comprobar(ack, "puntero colocado en 0x10");
    arranque;                              -- arranque repetido
    enviar(C_DIR & '1', ack);
    comprobar(ack, "acepta la direccion en modo lectura");
    recibir(true, byte);
    comprobar(byte = x"A1", "primer byte leido = 0xA1");
    recibir(true, byte);
    comprobar(byte = x"B2", "segundo byte leido = 0xB2");
    recibir(false, byte);                  -- NACK: ultimo
    comprobar(byte = x"C3", "tercer byte leido = 0xC3");
    parada;

    report "4) No responde a una direccion ajena";
    arranque;
    enviar("1010101" & '0', ack);
    comprobar(not ack, "no reconoce una direccion que no es la suya");
    parada;

    -- ------------------------------------------------------------------
    report "5) Espurios por debajo del filtro";
    -- En reposo, SDA a bajo 100 ns con SCL alto: sin filtro seria START.
    m_sda_oe <= '1'; wait for C_GLITCH; m_sda_oe <= '0';
    wait for 1 us;
    comprobar(ocupado = '0', "un pulso de 100 ns en SDA en reposo no se toma por START");
    -- En reposo, SCL a bajo 100 ns.
    scl <= '0'; wait for C_GLITCH; scl <= '1';
    wait for 1 us;
    comprobar(ocupado = '0', "un pulso de 100 ns en SCL en reposo no hace nada");
    -- Dentro de un byte de dato.
    we0 := n_we;
    arranque;
    enviar(C_DIR & '0', ack);
    enviar(x"30", ack);
    enviar_con_espurios(x"96", ack);
    comprobar(ack, "el byte con dos espurios dentro recibe ACK");
    parada;
    wait for 1 us;
    comprobar(mem(16#30#) = x"96", "el byte con espurios se escribio entero y bien (0x96)");
    comprobar(n_we = we0 + 1, "una sola escritura");

    -- ------------------------------------------------------------------
    report "6) STOP a mitad de byte";
    we0 := n_we;
    arranque;
    enviar(C_DIR & '0', ack);
    enviar(x"31", ack);
    enviar_parcial(x"AA", 4);
    parada;
    wait for 1 us;
    comprobar(ocupado = '0' and s_sda_oe = '0', "tras el STOP el esclavo esta en reposo y suelta SDA");
    comprobar(mem(16#31#) = (x"31" xor x"5A"), "el medio byte no se escribio");
    comprobar(n_we = we0, "ningun pulso de escritura");
    escribir(x"31", x"77");
    wait for 1 us;
    comprobar(mem(16#31#) = x"77", "la escritura siguiente va bien");

    -- ------------------------------------------------------------------
    report "7) START repetido a mitad de byte";
    we0 := n_we;
    arranque;
    enviar(C_DIR & '0', ack);
    enviar(x"32", ack);
    enviar_parcial(x"55", 5);
    arranque;                              -- START repetido fuera de sitio
    enviar(C_DIR & '1', ack);
    comprobar(ack, "acepta la direccion en lectura tras el START repetido");
    recibir(false, byte);
    comprobar(byte = (x"32" xor x"5A"), "lee del puntero fijado antes del byte abortado (0x32)");
    parada;
    wait for 1 us;
    comprobar(n_we = we0, "el byte abortado no se escribio");

    -- ------------------------------------------------------------------
    report "8) Bytes tras una direccion ajena";
    we0 := n_we;
    arranque;
    enviar("1010101" & '0', ack);
    comprobar(not ack, "no reconoce la direccion ajena");
    enviar(x"33", ack);
    comprobar(not ack, "no reconoce el puntero que sigue");
    enviar(x"EE", ack);
    comprobar(not ack, "no reconoce el dato que sigue");
    parada;
    wait for 1 us;
    comprobar(mem(16#33#) = (x"33" xor x"5A") and n_we = we0, "nada se escribio");

    -- ------------------------------------------------------------------
    report "9) El puntero sobrevive al STOP";
    escribir(x"40", x"11");                -- deja el puntero en 0x41
    arranque;
    enviar(C_DIR & '1', ack);              -- lectura sin fijar el puntero
    comprobar(ack, "acepta una lectura directa");
    recibir(false, byte);
    comprobar(byte = (x"41" xor x"5A"), "lee del puntero que quedo tras la escritura (0x41)");
    parada;

    -- ------------------------------------------------------------------
    report "10) La lectura da la vuelta en 0xFF";
    arranque;
    enviar(C_DIR & '0', ack);
    enviar(x"FE", ack);
    arranque;
    enviar(C_DIR & '1', ack);
    recibir(true, byte);
    comprobar(byte = (x"FE" xor x"5A"), "0xFE");
    recibir(true, byte);
    comprobar(byte = (x"FF" xor x"5A"), "0xFF");
    recibir(false, byte);
    comprobar(byte = (x"00" xor x"5A"), "0x00: el puntero de 8 bits da la vuelta");
    parada;

    -- ------------------------------------------------------------------
    report "11) El maestro desaparece con el esclavo tirando de SDA";
    arranque;
    byte := C_DIR & '0';
    for i in 7 downto 0 loop               -- direccion propia, bit a bit
      m_sda_oe <= not byte(i);
      wait for t_bit / 4;
      scl <= '1'; wait for t_bit / 2;
      scl <= '0'; wait for t_bit / 4;
    end loop;
    m_sda_oe <= '0';
    wait for t_bit / 4;
    scl <= '1'; wait for t_bit / 4;
    comprobar(sda = '0' and s_sda_oe = '1', "el esclavo esta dando el ACK (tira de SDA)");
    -- ... y aqui el maestro muere con SCL en alto.
    t0 := now;
    wait until ocupado = '0' for 300 us;
    dt := now - t0;
    comprobar(ocupado = '0' and s_sda_oe = '0', "la guarda devuelve el esclavo a reposo y suelta SDA");
    report "  la guarda tardo " & time'image(dt) & " (G_GUARDA = " & integer'image(C_GUARDA) & " ciclos)";
    comprobar(dt >= 99 us and dt <= 101 us, "en los ~100 us que fijan G_GUARDA y el reloj");
    -- El maestro vuelve: baja SCL antes de nada para no fabricar un START.
    scl <= '0'; wait for t_bit;
    parada;
    escribir(x"34", x"99");
    wait for 1 us;
    comprobar(mem(16#34#) = x"99", "la escritura siguiente va bien");

    -- ------------------------------------------------------------------
    report "12) STOP tras un ACK de lectura, en vez de NACK";
    -- a) El byte siguiente empieza por 1: el esclavo suelta SDA y el STOP vale.
    arranque;
    enviar(C_DIR & '0', ack);
    enviar(x"A5", ack);                    -- mem(0xA5) = 0xFF, mem(0xA6) = 0xFC
    arranque;
    enviar(C_DIR & '1', ack);
    recibir(true, byte);
    comprobar(byte = x"FF", "primer byte 0xFF");
    parada;
    wait for 1 us;
    comprobar(ocupado = '0' and s_sda_oe = '0', "el siguiente empezaba por 1: STOP aceptado, esclavo en reposo");
    -- b) El byte siguiente empieza por 0: el esclavo retiene SDA y el
    --    maestro no puede hacer STOP. Es asi en cualquier esclavo I2C; lo
    --    que distingue a este es que la guarda lo resuelve.
    arranque;
    enviar(C_DIR & '0', ack);
    enviar(x"5A", ack);                    -- mem(0x5A) = 0x00, mem(0x5B) = 0x01
    arranque;
    enviar(C_DIR & '1', ack);
    recibir(true, byte);
    comprobar(byte = x"00", "primer byte 0x00");
    parada;                                -- intento de STOP
    comprobar(sda = '0' and s_sda_oe = '1', "el siguiente empezaba por 0: el esclavo retiene SDA, el STOP no vale");
    t0 := now;
    wait until ocupado = '0' for 300 us;
    dt := now - t0;
    comprobar(ocupado = '0' and s_sda_oe = '0', "la guarda suelta SDA");
    report "  la guarda tardo " & time'image(dt);
    wait for 1 ns;                         -- sda es un delta posterior a s_sda_oe
    comprobar(sda = '1', "el bus queda libre");
    wait for 1 us;
    escribir(x"35", x"3C");
    wait for 1 us;
    comprobar(mem(16#35#) = x"3C", "la escritura siguiente va bien");

    -- ------------------------------------------------------------------
    report "13) Velocidad del bus";
    t_bit <= 1 us;                         -- 1 MHz con reloj de sistema de 20 MHz
    wait for 1 us;
    escribir(x"36", x"C3");
    leer(x"36", byte);
    comprobar(byte = x"C3", "a 1 MHz escribe y lee bien");
    t_bit <= 10 us;                        -- 100 kHz
    wait for 1 us;
    escribir(x"37", x"E7");
    leer(x"37", byte);
    comprobar(byte = x"E7", "a 100 kHz escribe y lee bien");
    t_bit <= 2 us;
    wait for 1 us;

    if fallos = 0 then
      report "tb_i2c_slave: 0 fallos" severity note;
    else
      report "tb_i2c_slave: " & integer'image(fallos) & " fallos"
        severity failure;
    end if;
    fin <= true;
    wait;
  end process principal;

end architecture sim;
