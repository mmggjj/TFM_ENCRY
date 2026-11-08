-- Envoltorio del motor para la Basys 3 (Artix-7 XC7A35T-1CPG236C).
--
-- Lo unico que anade al motor es lo que la placa pide: el boton de reset
-- activo a nivel alto, el SDA bidireccional en colector abierto, y un LED
-- que parpadea para saber que el bitstream esta vivo antes de que el
-- ESP32 diga nada. Los pines estan en synth/basys3/basys3.xdc.
--
-- Y un frecuencimetro de los anillos (medidor_frec): el display muestra
-- la frecuencia en MHz con un decimal, de ro2 con sw1 abajo y de ro1 con
-- sw1 arriba. Con modo_test (sw0) el anillo elegido sale dividido por 64
-- por JA3, para un osciloscopio; sin modo_test ese pin queda a 0, porque
-- un anillo visible desde fuera deja seguir su fase. G_MEDIDOR = false
-- quita el medidor, para comprobar que no altera la campana de entropia.
-- Detalle en docs/puesta_en_marcha_fpga.md.
--
-- NO PROBADO EN PLACA: esta escrito para que la puesta en marcha sea
-- programar y medir, no empezar de cero. El reloj del anillo de muestreo
-- (ro2) se restringe en el XDC con un periodo estimado; el primer
-- bitstream sirve para leer su frecuencia real y ajustarlo.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity basys3_top is
  generic (
    G_MEDIDOR : boolean := true
  );
  port (
    clk        : in    std_logic;   -- W5, 100 MHz
    btn_rst    : in    std_logic;   -- U18 (btnC), activo a nivel alto
    sw_test    : in    std_logic;   -- V17 (sw0): modo_test
    scl        : in    std_logic;   -- JA1: el motor nunca estira el reloj
    sda        : inout std_logic;   -- JA2: colector abierto
    led_alarma : out   std_logic;   -- U16 (ld0)
    led_vivo   : out   std_logic;   -- L1 (ld15): parpadeo
    sw_ro      : in    std_logic;   -- V16 (sw1): 0 ro2, 1 ro1 en el display
    ro_div     : out   std_logic;   -- JA3: anillo / 64, solo en modo test
    seg        : out   std_logic_vector(6 downto 0);
    dp         : out   std_logic;
    an         : out   std_logic_vector(3 downto 0)
  );
end entity basys3_top;

architecture rtl of basys3_top is
  signal rst_n   : std_logic;
  signal sda_oe  : std_logic;
  signal latido  : unsigned(26 downto 0) := (others => '0');
  signal rst_n_s : std_logic;
  signal ro_mon  : std_logic_vector(1 downto 0);
  signal presc   : std_logic_vector(1 downto 0) := (others => '0');
  type t_bcd is array (0 to 1) of std_logic_vector(15 downto 0);
  signal bcd     : t_bcd := (others => (others => '0'));
  signal desb    : std_logic_vector(1 downto 0) := (others => '0');
  signal sel_s   : std_logic_vector(1 downto 0) := (others => '0');
  signal test_s  : std_logic_vector(1 downto 0) := (others => '0');
  signal sel     : natural range 0 to 1;
  signal raya    : std_logic;
  signal bcd_sel : std_logic_vector(15 downto 0);
begin

  rst_n <= not btn_rst;

  -- Colector abierto: el motor solo tira a cero; en reposo el pull-up
  -- (interno del pin o externo del bus) deja la linea en alto.
  sda <= '0' when sda_oe = '1' else 'Z';

  u_motor : entity work.motor_top
    port map (clk => clk, rst_n => rst_n,
              scl_in => scl, sda_in => sda, sda_oe => sda_oe,
              modo_test => sw_test, led_alarma => led_alarma,
              ro_mon => ro_mon);

  u_rst : entity work.reset_sync
    port map (clk => clk, rst_n_in => rst_n, rst_n_out => rst_n_s);

  g_con_medidor : if G_MEDIDOR generate
    g_ro : for i in 0 to 1 generate
      u_frec : entity work.medidor_frec
        port map (clk => clk, rst_n => rst_n_s, ro => ro_mon(i),
                  presc_o => presc(i), bcd => bcd(i), desborde => desb(i),
                  nueva => open);
    end generate g_ro;
  end generate g_con_medidor;

  -- Interruptores: dos biestables, como modo_test dentro del motor.
  p_sw : process (clk)
  begin
    if rising_edge(clk) then
      sel_s  <= sel_s(0) & sw_ro;
      test_s <= test_s(0) & sw_test;
    end if;
  end process p_sw;
  sel <= 1 when sel_s(1) = '0' else 0;

  raya <= '1' when not G_MEDIDOR else desb(sel);
  bcd_sel <= bcd(sel);
  u_display : entity work.siete_seg
    port map (clk => clk, bcd => bcd_sel, punto => "0010", raya => raya,
              seg => seg, dp => dp, an => an);

  -- Mux combinacional de dos relojes de anillo a un pin: solo observacion.
  ro_div <= presc(sel) when test_s(1) = '1' else '0';

  -- ~0,7 s de periodo a 100 MHz. Sin reset: solo dice que hay reloj.
  p_latido : process (clk)
  begin
    if rising_edge(clk) then
      latido <= latido + 1;
    end if;
  end process p_latido;
  led_vivo <= latido(26);

end architecture rtl;
