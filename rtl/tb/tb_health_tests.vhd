-- Banco de los tests de salud: una fuente sana debe pasar y tres
-- degradaciones tipicas deben disparar la alarma que les toca.
--
--  1. Fuente sana (LFSR de 31 bits, equilibrada, sin rachas largas a la
--     escala de la ventana): ninguna alarma en 20 ventanas.
--  2. Fuente pegada: el RCT debe saltar exactamente en la muestra C.
--  3. Fuente sesgada al 70 %: el APT debe saltar en la primera ventana
--     completa; el RCT no deberia (rachas de 22 iguales son improbables).
--  4. Fuente pegada al valor opuesto al primero de la ventana: el APT solo
--     la detecta gracias a mirar el complemento.
--  5. Las alarmas se quedan hasta borrar, y borrar las baja.
--  6. ventana_fin pulsa una vez por ventana, junto con el veredicto del APT,
--     y borrar reinicia la ventana.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;

entity tb_health_tests is
end entity tb_health_tests;

architecture sim of tb_health_tests is

  constant C_T : time := 10 ns;
  constant C_RCT : positive := 22;
  constant C_W   : positive := 1024;
  constant C_APT : positive := 596;

  signal clk, rst_n : std_logic := '0';
  signal bit_i, bit_stb, borrar : std_logic := '0';
  signal alarma_rct, alarma_apt, alarma : std_logic;
  signal ventana_fin : std_logic;
  signal rct_max, apt_max : unsigned(15 downto 0);
  signal fin : boolean := false;
  -- Cierres de ventana vistos; el ultimo, con o sin alarma de APT a la vez.
  signal n_fin : natural := 0;
  signal apt_al_cerrar : std_logic := '0';

begin

  clk <= '0' when fin else not clk after C_T / 2;

  dut : entity work.health_tests
    generic map (G_RCT_C => C_RCT, G_APT_W => C_W, G_APT_C => C_APT)
    port map (clk => clk, rst_n => rst_n, bit_i => bit_i, bit_stb => bit_stb,
              borrar => borrar, alarma_rct => alarma_rct,
              alarma_apt => alarma_apt, alarma => alarma,
              ventana_fin => ventana_fin,
              rct_max => rct_max, apt_max => apt_max);

  cuenta_fin : process (clk)
  begin
    if rising_edge(clk) then
      if rst_n = '0' then
        n_fin <= 0;
      elsif ventana_fin = '1' then
        n_fin <= n_fin + 1;
        apt_al_cerrar <= alarma_apt;
      end if;
    end if;
  end process cuenta_fin;

  principal : process
    variable fallos : natural := 0;
    -- Semilla densa: con un solo uno el registro arranca con una racha de
    -- 27 ceros y una ventana al 76 %, y el test la caza (bien hecho).
    variable lfsr   : std_logic_vector(30 downto 0) := "1011001110001111010101100110101";
    variable s1, s2 : positive := 17;
    variable u      : real;
    variable n_disparo : natural;

    procedure comprobar(cond : boolean; msg : string) is
    begin
      if cond then
        report "  [ok ] " & msg;
      else
        report "  [FALLO] " & msg severity error;
        fallos := fallos + 1;
      end if;
    end procedure;

    procedure muestra(b : std_logic) is
    begin
      bit_i   <= b;
      bit_stb <= '1';
      wait until rising_edge(clk);
      bit_stb <= '0';
      wait until rising_edge(clk);
    end procedure;

    -- El contador de cierres se actualiza un ciclo despues de la muestra.
    procedure asentar is
    begin
      wait until rising_edge(clk);
      wait for 1 ns;
    end procedure;

    procedure reiniciar is
    begin
      rst_n <= '0';
      wait for 3 * C_T;
      rst_n <= '1';
      wait until rising_edge(clk);
    end procedure;

    -- LFSR x^31 + x^28 + 1, periodo maximo.
    impure function bit_lfsr return std_logic is
      variable nuevo : std_logic;
    begin
      nuevo := lfsr(30) xor lfsr(27);
      lfsr  := lfsr(29 downto 0) & nuevo;
      return nuevo;
    end function;

  begin
    reiniciar;

    -- Calentamiento del generador antes de medir nada con el.
    for i in 1 to 128 loop
      bit_i <= bit_lfsr;
    end loop;
    report "1) Fuente sana: 20 ventanas sin alarma";
    for i in 1 to 20 * C_W loop
      muestra(bit_lfsr);
    end loop;
    comprobar(alarma = '0', "sin alarmas tras " & integer'image(20 * C_W) &
              " muestras");
    comprobar(rct_max < C_RCT, "racha maxima vista " &
              integer'image(to_integer(rct_max)) & " < " & integer'image(C_RCT));
    comprobar(apt_max < C_APT, "proporcion maxima vista " &
              integer'image(to_integer(apt_max)) & " < " & integer'image(C_APT));

    report "2) Fuente pegada: el RCT salta en la muestra C";
    reiniciar;
    n_disparo := 0;
    for i in 1 to C_RCT + 5 loop
      muestra('1');
      if alarma_rct = '1' and n_disparo = 0 then
        n_disparo := i;
      end if;
    end loop;
    comprobar(n_disparo = C_RCT, "RCT dispara en la muestra " &
              integer'image(n_disparo) & " (esperado " & integer'image(C_RCT) & ")");

    report "3) Fuente sesgada al 70 %: salta el APT, no el RCT";
    reiniciar;
    for i in 1 to C_W loop
      uniform(s1, s2, u);
      if u < 0.7 then muestra('1'); else muestra('0'); end if;
    end loop;
    comprobar(alarma_apt = '1', "APT dispara con proporcion " &
              integer'image(to_integer(apt_max)) & " >= " & integer'image(C_APT));
    comprobar(alarma_rct = '0', "RCT no dispara con racha maxima " &
              integer'image(to_integer(rct_max)));

    report "4) Pegada al valor opuesto al de referencia: detecta el complemento";
    reiniciar;
    muestra('0');                          -- referencia de la ventana
    for i in 2 to C_W loop
      muestra('1');
    end loop;
    comprobar(alarma_apt = '1', "APT dispara aunque la cuenta directa sea 1");

    report "5) Las alarmas son pegajosas y se borran a proposito";
    for i in 1 to 50 loop
      muestra(bit_lfsr);
    end loop;
    comprobar(alarma = '1', "sigue en alarma con fuente ya sana");
    borrar <= '1';
    wait until rising_edge(clk);
    borrar <= '0';
    wait until rising_edge(clk);
    comprobar(alarma = '0', "borrar baja las alarmas");

    report "6) ventana_fin: una por ventana, con el veredicto, y borrar la reinicia";
    reiniciar;
    for i in 1 to C_W - 1 loop
      muestra(bit_lfsr);
    end loop;
    asentar;
    comprobar(n_fin = 0, "sin cierre con W-1 muestras");
    muestra(bit_lfsr);
    asentar;
    comprobar(n_fin = 1 and apt_al_cerrar = '0',
              "un cierre en la muestra W, sin alarma");
    for i in 1 to 2 * C_W loop
      muestra(bit_lfsr);
    end loop;
    asentar;
    comprobar(n_fin = 3, "tres cierres en 3W muestras: " & integer'image(n_fin));
    -- Ventana sesgada: el pulso de cierre llega con la alarma ya puesta.
    for i in 1 to C_W loop
      muestra('1');
    end loop;
    asentar;
    comprobar(n_fin = 4 and apt_al_cerrar = '1',
              "el cierre de una ventana mala llega con alarma_apt = 1");
    -- Borrar a mitad de ventana: la siguiente necesita W muestras nuevas.
    for i in 1 to C_W / 2 loop
      muestra(bit_lfsr);
    end loop;
    borrar <= '1';
    wait until rising_edge(clk);
    borrar <= '0';
    wait until rising_edge(clk);
    for i in 1 to C_W - 1 loop
      muestra(bit_lfsr);
    end loop;
    asentar;
    comprobar(n_fin = 4, "tras borrar, W-1 muestras no cierran ventana");
    muestra(bit_lfsr);
    asentar;
    comprobar(n_fin = 5 and apt_al_cerrar = '0',
              "tras borrar, la ventana se cierra en la muestra W y limpia");

    if fallos = 0 then
      report "tb_health_tests: 0 fallos" severity note;
    else
      report "tb_health_tests: " & integer'image(fallos) & " fallos"
        severity failure;
    end if;
    fin <= true;
    wait;
  end process principal;

end architecture sim;
