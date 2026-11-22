-- Revision 22-11: mascara y tic del ERO para CFG_KD 17..26 (las ventanas
-- grandes no caben en simulacion: ~8 000 periodos de ro2 por segundo).
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library unisim;
use unisim.sim_cfg.all;

entity tb_rev_mascara is
end entity;

architecture sim of tb_rev_mascara is
  constant C_T     : time := 10 ns;
  constant C_T_BIT : time := 1 us;
  constant C_DIR   : std_logic_vector(6 downto 0) := "0110000";
  constant NB      : natural := 22;     -- G_KD_MAX - G_PRESC_RO2
  signal clk, rst_n : std_logic := '0';
  signal scl, sda   : std_logic;
  signal m_sda_oe   : std_logic := '0';
  signal s_sda_oe   : std_logic;
  signal scl_m      : std_logic := '1';
  signal modo_test  : std_logic := '1';
  signal led_alarma : std_logic;
  signal fin : boolean := false;
begin
  clk <= '0' when fin else not clk after C_T / 2;
  scl <= scl_m;
  sda <= '0' when (m_sda_oe = '1' or s_sda_oe = '1') else '1';

  dut : entity work.motor_top
    generic map (G_DIR_I2C => C_DIR, G_ETAPAS_RO1 => 3, G_ETAPAS_RO2 => 3)
    port map (clk => clk, rst_n => rst_n, scl_in => scl, sda_in => sda,
              sda_oe => s_sda_oe, modo_test => modo_test,
              led_alarma => led_alarma);

  principal : process
    alias mascara is << signal .tb_rev_mascara.dut.u_ero.mascara : unsigned(NB - 1 downto 0) >>;
    alias cuenta  is << signal .tb_rev_mascara.dut.u_ero.cuenta  : unsigned(NB - 1 downto 0) >>;
    alias tic     is << signal .tb_rev_mascara.dut.u_ero.tic     : std_logic >>;
    alias kd_ero  is << signal .tb_rev_mascara.dut.kd_ero        : unsigned(4 downto 0) >>;
    variable fallos : natural := 0;
    variable b : std_logic_vector(7 downto 0);
    variable ke : natural;
    variable esp : unsigned(NB - 1 downto 0);

    procedure comprobar(cond : boolean; msg : string) is
    begin
      if cond then report "  [ok ] " & msg;
      else report "  [FALLO] " & msg severity error; fallos := fallos + 1; end if;
    end procedure;
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
    procedure escribir_reg(dir, dato : in std_logic_vector(7 downto 0)) is
      variable ack : boolean;
    begin
      arranque; enviar(C_DIR & '0', ack);
      assert ack report "sin ACK" severity failure;
      enviar(dir, ack); enviar(dato, ack); parada;
    end procedure;
    procedure leer_reg(dir : in std_logic_vector(7 downto 0); dato : out std_logic_vector(7 downto 0)) is
      variable ack : boolean;
    begin
      arranque; enviar(C_DIR & '0', ack); enviar(dir, ack);
      arranque; enviar(C_DIR & '1', ack); recibir(false, dato); parada;
    end procedure;
  begin
    cfg.configurar(0.15, 0.0);
    rst_n <= '0'; wait for 200 ns; rst_n <= '1';
    wait for 20 us;
    for kd in 0 to 26 loop
      escribir_reg(x"04", std_logic_vector(to_unsigned(kd, 8)));
      leer_reg(x"04", b);
      if kd >= 4 then ke := kd - 4; else ke := 0; end if;
      esp := shift_left(to_unsigned(1, NB), ke) - 1;   -- ke = 22 -> todo unos
      comprobar(to_integer(unsigned(b)) = kd and to_integer(kd_ero) = ke and mascara = esp,
                "kd " & integer'image(kd) & ": kd_ero " & integer'image(to_integer(kd_ero)) &
                ", unos en la mascara " & integer'image(ke));
      -- tic con la cuenta a todo unos y sin el bit alto de la ventana
      cuenta <= force (NB - 1 downto 0 => '1');
      wait for 1 ps;
      comprobar(tic = '1', "  tic con la cuenta a todo unos");
      if ke >= 1 then
        cuenta <= force shift_left(to_unsigned(1, NB), ke - 1) - 1;
        wait for 1 ps;
        comprobar(tic = '0', "  sin tic con 2^(kd_ero-1)-1");
        cuenta <= force (shift_left(to_unsigned(1, NB), ke) - 1);
        wait for 1 ps;
        comprobar(tic = '1', "  tic con 2^kd_ero-1");
      end if;
      cuenta <= release;
      wait for 1 us;
    end loop;
    report "FIN: fallos = " & integer'image(fallos);
    fin <= true;
    std.env.stop;
    wait;
  end process;
end architecture;
