-- Banco del frecuencimetro de la placa (medidor_frec + siete_seg).
--
-- Un anillo de periodo conocido con jitter aleatorio entra al medidor con
-- los valores de la placa (prescaler 64, ventana de 64 000 ciclos de
-- 100 MHz). Cada lectura debe caer a +-1 cuenta de 10 us / (P * 64 ns),
-- el desborde debe saltar por encima de 999,9 MHz y el display debe
-- mostrar, digito a digito, lo mismo que el registro BCD.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;

entity tb_medidor_frec is
end entity tb_medidor_frec;

architecture sim of tb_medidor_frec is

  constant C_CLK     : time := 10 ns;
  constant C_VENTANA : positive := 64000;

  signal clk   : std_logic := '0';
  signal rst_n : std_logic := '0';
  signal ro    : std_logic := '0';
  signal periodo_ps : real := 2500.0;   -- periodo del anillo
  signal fin   : boolean := false;

  signal presc : std_logic;
  signal bcd   : std_logic_vector(15 downto 0);
  signal desb, nueva : std_logic;
  signal seg   : std_logic_vector(6 downto 0);
  signal dp    : std_logic;
  signal an    : std_logic_vector(3 downto 0);

  function a_entero(v : std_logic_vector(15 downto 0)) return integer is
  begin
    return to_integer(unsigned(v(15 downto 12))) * 1000
         + to_integer(unsigned(v(11 downto 8))) * 100
         + to_integer(unsigned(v(7 downto 4))) * 10
         + to_integer(unsigned(v(3 downto 0)));
  end function;

  -- Inversa de la tabla del display (activos a nivel bajo): -1 si no es cifra.
  function de_seg(s : std_logic_vector(6 downto 0)) return integer is
  begin
    case not s is
      when "0111111" => return 0;
      when "0000110" => return 1;
      when "1011011" => return 2;
      when "1001111" => return 3;
      when "1100110" => return 4;
      when "1101101" => return 5;
      when "1111101" => return 6;
      when "0000111" => return 7;
      when "1111111" => return 8;
      when "1101111" => return 9;
      when "1000000" => return 10;   -- raya
      when others    => return -1;
    end case;
  end function;

begin

  clk <= not clk after C_CLK / 2 when not fin;

  -- Anillo: semiperiodo con jitter uniforme de +-2 % (gaussiano no hace
  -- falta: el medidor solo cuenta flancos).
  p_ro : process
    variable s1, s2 : positive := 7;
    variable u : real;
  begin
    while not fin loop
      uniform(s1, s2, u);
      wait for (periodo_ps / 2.0) * (1.0 + 0.04 * (u - 0.5)) * 1 ps;
      ro <= not ro;
    end loop;
    wait;
  end process p_ro;

  dut : entity work.medidor_frec
    generic map (G_PRE => 6, G_VENTANA => C_VENTANA)
    port map (clk => clk, rst_n => rst_n, ro => ro, presc_o => presc,
              bcd => bcd, desborde => desb, nueva => nueva);

  u_disp : entity work.siete_seg
    generic map (G_DIV => 4)
    port map (clk => clk, bcd => bcd, punto => "0010", raya => desb,
              seg => seg, dp => dp, an => an);

  p_estimulo : process
    -- Espera dos ventanas: la primera tras un cambio de frecuencia mezcla
    -- las dos.
    variable n_ok, n_fallo : natural := 0;

    procedure chk(c : boolean; m : string) is
    begin
      if c then
        n_ok := n_ok + 1;
        report "[ok] " & m;
      else
        n_fallo := n_fallo + 1;
        report "[FALLO] " & m severity error;
      end if;
    end procedure;

    procedure leer(variable n : out integer; variable d : out std_logic) is
    begin
      wait until rising_edge(clk) and nueva = '1';
      wait until rising_edge(clk) and nueva = '1';
      wait until rising_edge(clk);
      n := a_entero(bcd);
      d := desb;
    end procedure;

    procedure medir(p_ps : real) is
      variable n : integer;
      variable d : std_logic;
      variable esperado : real;
    begin
      periodo_ps <= p_ps;
      leer(n, d);
      esperado := real(C_VENTANA) * 10_000.0 / (p_ps * 64.0);
      chk(d = '0' and abs (real(n) - esperado) <= 1.0,
          "periodo " & integer'image(integer(p_ps)) & " ps: lectura "
          & integer'image(n) & " (x100 kHz), esperado "
          & real'image(esperado));
    end procedure;

    variable n : integer;
    variable d : std_logic;
    variable dig : integer;
    variable visto : std_logic_vector(3 downto 0);
    variable bien : boolean;
    variable t0 : time;
  begin
    rst_n <= '0';
    wait for 100 ns;
    rst_n <= '1';

    -- 1. Frecuencias de anillo de FPGA plausibles y la del XDC (1,4 ns)
    medir(2500.0);      -- 400 MHz: lectura exacta 4000
    medir(1400.0);      -- 714,3 MHz
    medir(3700.0);      -- 270,3 MHz
    medir(5333.0);      -- 187,5 MHz
    medir(20000.0);     -- 50 MHz

    -- 2. Por encima de 999,9 MHz: desborde y 9999
    periodo_ps <= 800.0;  -- 1,25 GHz
    leer(n, d);
    chk(d = '1' and n = 9999, "1,25 GHz: desborde y lectura saturada en 9999 ("
        & integer'image(n) & ")");

    -- 3. Vuelve a medir tras un desborde
    medir(2500.0);

    -- 4. Display: los cuatro anodos, cada uno con su cifra y el punto solo
    --    en el digito 1 (XXX.X)
    periodo_ps <= 1400.0;
    wait until rising_edge(clk) and nueva = '1';
    wait until rising_edge(clk) and nueva = '1';
    visto := "0000";
    bien := true;
    for k in 0 to 4 * 16 * 2 loop
      wait until rising_edge(clk);
      wait for 1 ns;
      for i in 0 to 3 loop
        if an(i) = '0' then
          visto(i) := '1';
          dig := de_seg(seg);
          if dig /= to_integer(unsigned(bcd(4 * i + 3 downto 4 * i)))
             or (dp = '0') /= (i = 1) then
            bien := false;
          end if;
        end if;
      end loop;
      if not (an = "1110" or an = "1101" or an = "1011" or an = "0111") then
        bien := false;
      end if;
    end loop;
    chk(bien and visto = "1111", "display: un anodo a la vez, cifras = BCD ("
        & integer'image(a_entero(bcd)) & "), punto en el digito 1");

    -- 5. Display en desborde: raya en los cuatro
    periodo_ps <= 800.0;
    wait until rising_edge(clk) and nueva = '1';
    wait until rising_edge(clk) and nueva = '1';
    bien := true;
    for k in 0 to 4 * 16 loop
      wait until rising_edge(clk);
      wait for 1 ns;
      if de_seg(seg) /= 10 then bien := false; end if;
    end loop;
    chk(bien, "display en desborde: ----");

    -- 6. Prescaler: periodo de presc_o = 64 periodos del anillo
    --    (media sobre 100 periodos: el jitter de cada uno es +-2 %)
    periodo_ps <= 2500.0;
    wait until rising_edge(presc);
    t0 := now;
    for k in 1 to 100 loop
      wait until rising_edge(presc);
    end loop;
    chk(abs (real((now - t0) / 1 ps) / 100.0 - 64.0 * 2500.0) < 0.01 * 64.0 * 2500.0,
        "presc_o: periodo medio " & integer'image((now - t0) / 100 ps)
        & " ps = 64 x 2500 ps");
    report "resultado: " & integer'image(n_ok) & " ok, "
           & integer'image(n_fallo) & " fallos";
    assert n_fallo = 0 report "tb_medidor_frec: hay fallos" severity failure;
    fin <= true;
    wait;
  end process p_estimulo;

end architecture sim;
