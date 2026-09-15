-- Banco de pruebas del esclavo I2C.
--
-- Modela un maestro I2C y un banco de registros, y comprueba las cuatro
-- cosas que tienen que salir bien para que el ESP32 pueda hablar con el
-- motor: que el esclavo responde a su direccion y solo a la suya, que una
-- escritura de varios bytes seguidos avanza el puntero, que una lectura
-- con arranque repetido devuelve lo que hay, y que la lectura tambien
-- autoincrementa.
--
-- El bus se modela con un solo asignador por linea en lugar de con
-- resolucion y niveles debiles: asi las entradas del esclavo son siempre
-- '0' o '1' y no hay que preocuparse de que 'H' no sea igual a '1' al
-- comparar.
--
--   ghdl -a --std=08 --workdir=rtl/build/work rtl/io/i2c_slave.vhd
--   ghdl -a --std=08 --workdir=rtl/build/work rtl/tb/tb_i2c_slave.vhd
--   ghdl -r --std=08 --workdir=rtl/build/work tb_i2c_slave

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_i2c_slave is
end entity tb_i2c_slave;

architecture sim of tb_i2c_slave is

  constant C_DIR    : std_logic_vector(6 downto 0) := "0110000";  -- 0x30
  constant C_T_CLK  : time := 50 ns;      -- 20 MHz de sistema
  constant C_T_BIT  : time := 2 us;       -- 500 kHz de bus

  signal clk    : std_logic := '0';
  signal rst_n  : std_logic := '0';

  signal m_sda_oe : std_logic := '0';     -- el maestro tira de SDA
  signal s_sda_oe : std_logic;            -- el esclavo tira de SDA
  signal scl      : std_logic := '1';
  signal sda      : std_logic;

  signal reg_dir   : std_logic_vector(7 downto 0);
  signal reg_wdato : std_logic_vector(7 downto 0);
  signal reg_we    : std_logic;
  signal reg_rdato : std_logic_vector(7 downto 0);
  signal reg_re    : std_logic;
  signal ocupado   : std_logic;

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
    generic map (G_DIR => C_DIR, G_FILTRO => 5)
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
      end if;
    end if;
  end process p_mem;

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
      m_sda_oe <= '0'; scl <= '1'; wait for C_T_BIT / 2;
      m_sda_oe <= '1';             wait for C_T_BIT / 2;   -- SDA baja con SCL alto
      scl      <= '0';             wait for C_T_BIT / 2;
    end procedure;

    procedure parada is
    begin
      m_sda_oe <= '1'; scl <= '0'; wait for C_T_BIT / 2;
      scl      <= '1';             wait for C_T_BIT / 2;
      m_sda_oe <= '0';             wait for C_T_BIT;       -- SDA sube con SCL alto
    end procedure;

    -- Envia un byte y devuelve true si el esclavo lo reconoce.
    procedure enviar(dato : in std_logic_vector(7 downto 0);
                     ack  : out boolean) is
    begin
      for i in 7 downto 0 loop
        m_sda_oe <= not dato(i);          -- colector abierto
        wait for C_T_BIT / 4;
        scl <= '1'; wait for C_T_BIT / 2;
        scl <= '0'; wait for C_T_BIT / 4;
      end loop;
      m_sda_oe <= '0';                    -- suelta para leer el ACK
      wait for C_T_BIT / 4;
      scl <= '1'; wait for C_T_BIT / 4;
      ack := (sda = '0');
      wait for C_T_BIT / 4;
      scl <= '0'; wait for C_T_BIT / 4;
    end procedure;

    -- Lee un byte; con seguir = true responde ACK para pedir mas.
    procedure recibir(seguir : in boolean;
                      dato   : out std_logic_vector(7 downto 0)) is
      variable v : std_logic_vector(7 downto 0);
    begin
      m_sda_oe <= '0';
      for i in 7 downto 0 loop
        wait for C_T_BIT / 4;
        scl <= '1'; wait for C_T_BIT / 4;
        v(i) := sda;
        wait for C_T_BIT / 4;
        scl <= '0'; wait for C_T_BIT / 4;
      end loop;
      m_sda_oe <= '1' when seguir else '0';
      wait for C_T_BIT / 4;
      scl <= '1'; wait for C_T_BIT / 2;
      scl <= '0'; wait for C_T_BIT / 4;
      m_sda_oe <= '0';
      dato := v;
    end procedure;

    variable ack  : boolean;
    variable byte : std_logic_vector(7 downto 0);
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
