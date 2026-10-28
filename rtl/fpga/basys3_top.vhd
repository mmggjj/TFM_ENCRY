-- Envoltorio del motor para la Basys 3 (Artix-7 XC7A35T-1CPG236C).
--
-- Lo unico que anade al motor es lo que la placa pide: el boton de reset
-- activo a nivel alto, el SDA bidireccional en colector abierto, y un LED
-- que parpadea para saber que el bitstream esta vivo antes de que el
-- ESP32 diga nada. Los pines estan en synth/basys3/basys3.xdc.
--
-- NO PROBADO EN PLACA: esta escrito para que la puesta en marcha sea
-- programar y medir, no empezar de cero. El reloj del anillo de muestreo
-- (ro2) se restringe en el XDC con un periodo estimado; el primer
-- bitstream sirve para leer su frecuencia real y ajustarlo.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity basys3_top is
  port (
    clk        : in    std_logic;   -- W5, 100 MHz
    btn_rst    : in    std_logic;   -- U18 (btnC), activo a nivel alto
    sw_test    : in    std_logic;   -- V17 (sw0): modo_test
    scl        : in    std_logic;   -- JA1: el motor nunca estira el reloj
    sda        : inout std_logic;   -- JA2: colector abierto
    led_alarma : out   std_logic;   -- U16 (ld0)
    led_vivo   : out   std_logic    -- L1 (ld15): parpadeo
  );
end entity basys3_top;

architecture rtl of basys3_top is
  signal rst_n   : std_logic;
  signal sda_oe  : std_logic;
  signal latido  : unsigned(26 downto 0) := (others => '0');
begin

  rst_n <= not btn_rst;

  -- Colector abierto: el motor solo tira a cero; en reposo el pull-up
  -- (interno del pin o externo del bus) deja la linea en alto.
  sda <= '0' when sda_oe = '1' else 'Z';

  u_motor : entity work.motor_top
    port map (clk => clk, rst_n => rst_n,
              scl_in => scl, sda_in => sda, sda_oe => sda_oe,
              modo_test => sw_test, led_alarma => led_alarma);

  -- ~0,7 s de periodo a 100 MHz. Sin reset: solo dice que hay reloj.
  p_latido : process (clk)
  begin
    if rising_edge(clk) then
      latido <= latido + 1;
    end if;
  end process p_latido;
  led_vivo <= latido(26);

end architecture rtl;
