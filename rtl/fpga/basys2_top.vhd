-- Envoltorio del motor para la Basys 2 (Spartan-3E XC3S100E-CP132).
--
-- El motor va en su variante de solo fuente (G_SOLO_FUENTE, sin buffer de
-- captura): la criptografia no cabe en el 100E (docs/basys2.md). Mismo
-- mapa I2C; DIAG.solo_fuente lo anuncia al ESP32.
--
-- Lo mismo que basys3_top: reset por boton, SDA en colector abierto,
-- frecuencimetro de los anillos en el display (sw1 elige ro2/ro1) y el
-- anillo / 64 por JA3 solo en modo test. Ademas el LED de latido cambia
-- cada medio segundo exacto si el reloj es de G_CLK_MHZ: contando 60
-- parpadeos con un cronometro se sabe a que frecuencia va el oscilador
-- (el jumper JP4 viene sin soldar, se esperan 50 MHz).
--
-- Pines en synth/basys2/basys2.ucf. NO PROBADO EN PLACA.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity basys2_top is
  generic (
    G_CLK_MHZ : positive := 50;        -- reloj de placa (B8)
    G_MEDIDOR : boolean := true;
    -- Medio periodo del LED de latido en ciclos; 0 = medio segundo a
    -- G_CLK_MHZ. Solo el banco lo cambia.
    G_LATIDO  : natural := 0
  );
  port (
    clk        : in    std_logic;   -- B8
    btn_rst    : in    std_logic;   -- G12 (btn0), activo a nivel alto
    sw_test    : in    std_logic;   -- P11 (sw0): modo_test
    sw_ro      : in    std_logic;   -- L3 (sw1): 0 ro2, 1 ro1 en el display
    scl        : in    std_logic;   -- JA1: el motor nunca estira el reloj
    sda        : inout std_logic;   -- JA2: colector abierto
    ro_div     : out   std_logic;   -- JA3: anillo / 64, solo en modo test
    led_alarma : out   std_logic;   -- M5 (ld0)
    led_vivo   : out   std_logic;   -- G1 (ld7): 1 Hz si el reloj es G_CLK_MHZ
    seg        : out   std_logic_vector(6 downto 0);   -- g f e d c b a
    dp         : out   std_logic;
    an         : out   std_logic_vector(3 downto 0)
  );
end entity basys2_top;

architecture rtl of basys2_top is
  function medio_periodo return positive is
  begin
    if G_LATIDO = 0 then return 500_000 * G_CLK_MHZ; else return G_LATIDO; end if;
  end function;
  constant C_LATIDO : positive := medio_periodo;

  signal rst_n   : std_logic;
  signal sda_oe  : std_logic;
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
  signal latido  : natural range 0 to C_LATIDO - 1 := 0;
  signal vivo    : std_logic := '0';
begin

  rst_n <= not btn_rst;

  sda <= '0' when sda_oe = '1' else 'Z';

  -- G_KD_MIN 7 y no 6: con 50 MHz el cruce de dominio necesita el doble
  -- de divisor para los mismos 8 ciclos de sistema por bit.
  -- Anillos de 7 y 9 etapas, no de 5 y 7: con 5 etapas colocado en un CLB
  -- ro2 oscilaba a 204,8 MHz [medido] y el contador de ero_core solo esta
  -- garantizado hasta ~203 MHz (docs/basys2.md).
  u_motor : entity work.motor_top
    generic map (G_ETAPAS_RO1 => 9, G_ETAPAS_RO2 => 7,
                 G_KD_MIN => 7, G_FLUJO_BYTES => 256,
                 G_CAPTURA_BYTES => 0, G_SOLO_FUENTE => true)
    port map (clk => clk, rst_n => rst_n,
              scl_in => scl, sda_in => sda, sda_oe => sda_oe,
              modo_test => sw_test, led_alarma => led_alarma,
              ro_mon => ro_mon);

  u_rst : entity work.reset_sync
    port map (clk => clk, rst_n_in => rst_n, rst_n_out => rst_n_s);

  -- Ventana de 640 us a cualquier reloj: una cuenta = 100 kHz, como en la
  -- Basys 3.
  g_con_medidor : if G_MEDIDOR generate
    g_ro : for i in 0 to 1 generate
      u_frec : entity work.medidor_frec
        generic map (G_PRE => 6, G_VENTANA => 640 * G_CLK_MHZ)
        port map (clk => clk, rst_n => rst_n_s, ro => ro_mon(i),
                  presc_o => presc(i), bcd => bcd(i), desborde => desb(i),
                  nueva => open);
    end generate g_ro;
  end generate g_con_medidor;

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
  -- 2**16 ciclos por digito: ~190 Hz de refresco completo a 50 MHz.
  u_display : entity work.siete_seg
    generic map (G_DIV => 16)
    port map (clk => clk, bcd => bcd_sel, punto => "0010", raya => raya,
              seg => seg, dp => dp, an => an);

  ro_div <= presc(sel) when test_s(1) = '1' else '0';

  p_latido : process (clk)
  begin
    if rising_edge(clk) then
      if latido = C_LATIDO - 1 then
        latido <= 0;
        vivo <= not vivo;
      else
        latido <= latido + 1;
      end if;
    end if;
  end process p_latido;
  led_vivo <= vivo;

end architecture rtl;
