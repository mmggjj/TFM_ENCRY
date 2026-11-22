-- Revision 22-11: ventana del ERO en periodos de ro2 frente a CFG_KD, con el
-- motor_top del repositorio sin tocar. Escribe CFG_KD por I2C, para clk y
-- cuenta flancos de ro2 entre dos muestras validas (flanco de ro2c con tic).
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
library unisim;
use unisim.sim_cfg.all;

entity tb_rev_ventana is
  generic (
    G_PRESC : natural := 4;
    G_MAX   : natural := 26;
    G_MIN   : natural := 25;
    G_RST   : natural := 25;
    G_KD_HASTA : natural := 26;      -- mide kd 0..G_KD_HASTA (ver lista)
    G_GRANDES  : boolean := true;    -- incluye 21..26
    G_KD_DESDE : natural := 0;
    G_OOR      : boolean := true
  );
end entity;

architecture sim of tb_rev_ventana is
  constant C_T     : time := 10 ns;
  constant C_T_BIT : time := 1 us;
  constant C_DIR   : std_logic_vector(6 downto 0) := "0110000";
  signal clk, rst_n : std_logic := '0';
  signal clk_en : boolean := true;
  signal scl, sda   : std_logic;
  signal m_sda_oe   : std_logic := '0';
  signal s_sda_oe   : std_logic;
  signal scl_m      : std_logic := '1';
  signal modo_test  : std_logic := '1';
  signal led_alarma : std_logic;
  signal fin : boolean := false;

  -- medidas
  signal n_muestras : natural := 0;
  signal ult_dif    : natural := 0;
begin
  clk <= '0' when (fin or not clk_en) else not clk after C_T / 2;
  scl <= scl_m;
  sda <= '0' when (m_sda_oe = '1' or s_sda_oe = '1') else '1';

  dut : entity work.motor_top
    generic map (G_DIR_I2C => C_DIR, G_ETAPAS_RO1 => 3, G_ETAPAS_RO2 => 3,
                 G_PRESC_RO2 => G_PRESC, G_KD_MAX => G_MAX, G_KD_MIN => G_MIN,
                 G_KD_RESET => G_RST)
    port map (clk => clk, rst_n => rst_n, scl_in => scl, sda_in => sda,
              sda_oe => s_sda_oe, modo_test => modo_test,
              led_alarma => led_alarma);

  monitor : block
    alias ro2  is << signal .tb_rev_ventana.dut.ro2  : std_logic >>;
    alias ro2c is << signal .tb_rev_ventana.dut.ro2c : std_logic >>;
    alias tic  is << signal .tb_rev_ventana.dut.u_ero.tic : std_logic >>;
  begin
    p : process (ro2, ro2c)
      variable cnt, prev : natural := 0;
      variable hay_prev : boolean := false;
    begin
      if rising_edge(ro2) then
        cnt := cnt + 1;
      end if;
      if rising_edge(ro2c) and tic = '1' then
        if hay_prev then
          ult_dif <= cnt - prev;
        end if;
        prev := cnt; hay_prev := true;
        n_muestras <= n_muestras + 1;
      end if;
    end process;
  end block;

  principal : process
    variable fallos : natural := 0;
    variable b : std_logic_vector(7 downto 0);

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

    procedure medir(kd : natural; nvent : positive) is
      variable esperado, n0 : natural;
    begin
      escribir_reg(x"04", std_logic_vector(to_unsigned(kd, 8)));
      leer_reg(x"04", b);
      comprobar(to_integer(unsigned(b)) = kd, "CFG_KD " & integer'image(kd) & " escrito");
      clk_en <= false;
      if kd >= G_PRESC then esperado := 2**kd; else esperado := 2**G_PRESC; end if;
      -- descarta la muestra de transicion y la primera ventana completa
      wait until n_muestras'event; wait until n_muestras'event;
      for i in 1 to nvent loop
        wait until n_muestras'event;
        wait for 0 ns;
        comprobar(ult_dif = esperado, "kd " & integer'image(kd) & " ventana " & integer'image(i) &
                  ": " & integer'image(ult_dif) & " periodos de ro2 (esperado 2^kd efectivo " &
                  integer'image(esperado) & ", 2^CFG_KD " & integer'image(2**kd) & ")");
      end loop;
      clk_en <= true;
      wait for 1 us;
    end procedure;
  begin
    cfg.configurar(0.15, 0.0);
    rst_n <= '0'; wait for 200 ns; rst_n <= '1';
    wait for 20 us;

    leer_reg(x"04", b);
    comprobar(to_integer(unsigned(b)) = G_RST, "reset CFG_KD = " & integer'image(to_integer(unsigned(b))));

    -- Escrituras fuera de rango por I2C
    if G_OOR then
    for v in G_MAX + 1 to 40 loop
      escribir_reg(x"04", std_logic_vector(to_unsigned(G_RST, 8)));
      escribir_reg(x"04", std_logic_vector(to_unsigned(v, 8)));
      leer_reg(x"04", b);
      report "  escribir CFG_KD = " & integer'image(v) & " -> se lee " & integer'image(to_integer(unsigned(b)));
      leer_reg(x"0E", b);
      report "    DIAG = " & integer'image(to_integer(unsigned(b))) & " (bit1 rechazada)";
    end loop;
    -- rechazada se queda puesta tras una escritura valida de CFG_KD?
    escribir_reg(x"04", x"1F");
    escribir_reg(x"04", std_logic_vector(to_unsigned(G_RST, 8)));
    leer_reg(x"0E", b);
    report "  tras 0x1F y luego una escritura valida, DIAG.rechazada = " & std_logic'image(b(1));
    end if;

    for kd in 0 to 20 loop
      if kd <= G_KD_HASTA and kd >= G_KD_DESDE then medir(kd, 2); end if;
    end loop;
    if G_GRANDES then
      for kd in 21 to G_MAX loop
        if kd <= G_KD_HASTA and kd >= G_KD_DESDE then medir(kd, 1); end if;
      end loop;
    end if;

    report "FIN: fallos = " & integer'image(fallos);
    fin <= true;
    std.env.stop;
    wait;
  end process;
end architecture;
