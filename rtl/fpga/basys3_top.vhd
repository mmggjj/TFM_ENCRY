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
-- Probado en placa el 17-11-2026 (docs/basys3.md): motor entero con el
-- ESP32, anillos de 11/13 etapas.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity basys3_top is
  generic (
    G_MEDIDOR : boolean := true;
    -- Display apagado y LED de latido fijo, para las capturas: en la
    -- Basys 2 el display multiplexado modulaba los anillos (docs/basys2.md).
    G_QUIETO  : boolean := false;
    -- Etapas de los anillos en esta placa: con 5/7 ro2 iba a 357,8 MHz y con
    -- 7/9 a 293 MHz, y el dominio de ro2 no cerraba tiempos (camino de
    -- 3,9 ns). 11/13 (docs/basys3.md). El integrado lleva 11/13 al reves
    -- (ro1 11, ro2 13) con preescalador de ro2 (19-11-2026).
    G_ETAPAS_RO1 : positive := 13;
    G_ETAPAS_RO2 : positive := 11;
    -- Prueba de la raya de ~38 kHz (docs/basys3.md): G_CARGA biestables que
    -- conmutan a 100 MHz con sw1 arriba, lejos de los anillos, para cambiar
    -- el consumo del nucleo. 0 en uso normal: no hay nada.
    G_CARGA      : natural  := 0;
    -- Divisor minimo y de reset en la placa: 19, el que pide el jitter
    -- termico medido (docs/basys3.md, 18/19-11-2026). La variante de
    -- caracterizacion se compila con G_KD_MIN=6 (flujo y siembra a kd bajo).
    G_KD_MIN     : natural  := 19;
    G_KD_RESET   : natural  := 19
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
    generic map (G_FLUJO_BYTES => 256,
                 G_ETAPAS_RO1 => G_ETAPAS_RO1, G_ETAPAS_RO2 => G_ETAPAS_RO2,
                 G_KD_MIN => G_KD_MIN, G_KD_RESET => G_KD_RESET,
                 -- contador de 24 bits como hasta el 18-11: con 26 el camino
                 -- de ro2 pasa a 4,41 ns, sobre 0,9 x 4,88 (build.tcl)
                 G_KD_MAX => 24, G_PRESC_RO2 => 0)
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
  g_display : if not G_QUIETO generate
    u_display : entity work.siete_seg
      port map (clk => clk, bcd => bcd_sel, punto => "0010", raya => raya,
                seg => seg, dp => dp, an => an);
  end generate g_display;
  g_sin_display : if G_QUIETO generate
    seg <= (others => '1'); dp <= '1'; an <= (others => '1');
  end generate g_sin_display;

  gen_carga : if G_CARGA > 0 generate
    signal carga : std_logic_vector(G_CARGA - 1 downto 0) := (others => '0');
    attribute dont_touch : string;
    attribute dont_touch of carga : signal is "true";
  begin
    p_carga : process (clk)
    begin
      if rising_edge(clk) then
        if sel_s(1) = '1' then
          carga <= not carga;
        end if;
      end if;
    end process p_carga;
  end generate gen_carga;

  -- Mux combinacional de dos relojes de anillo a un pin: solo observacion.
  ro_div <= presc(sel) when test_s(1) = '1' else '0';

  -- ~0,7 s de periodo a 100 MHz. Sin reset: solo dice que hay reloj.
  p_latido : process (clk)
  begin
    if rising_edge(clk) then
      latido <= latido + 1;
    end if;
  end process p_latido;
  led_vivo <= '0' when G_QUIETO else latido(26);

end architecture rtl;
