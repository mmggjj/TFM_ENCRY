-- Cosimulacion: health_tests (nueva) frente a health_tests_old (HEAD) con
-- los mismos genericos y estimulos aleatorios; compara todas las salidas.
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;
use std.textio.all;

entity tb_cosim is
  generic (W : positive := 1024; C : positive := 766; RCT : positive := 51;
           CICLOS : natural := 2_000_000; SEMILLA : positive := 1);
end entity;

architecture sim of tb_cosim is
  signal clk : std_logic := '0';
  signal rst_n, bit_i, bit_stb, borrar : std_logic := '0';
  signal a_rct, a_apt, a_alm, a_fin, b_rct, b_apt, b_alm, b_fin : std_logic;
  signal a_rmax, a_amax, b_rmax, b_amax : unsigned(15 downto 0);
  signal fin : boolean := false;
begin
  clk <= not clk after 5 ns when not fin;

  u_new : entity work.health_tests
    generic map (G_RCT_C => RCT, G_APT_W => W, G_APT_C => C)
    port map (clk, rst_n, bit_i, bit_stb, borrar, a_rct, a_apt, a_alm, a_fin, a_rmax, a_amax);
  u_old : entity work.health_tests_old
    generic map (G_RCT_C => RCT, G_APT_W => W, G_APT_C => C)
    port map (clk, rst_n, bit_i, bit_stb, borrar, b_rct, b_apt, b_alm, b_fin, b_rmax, b_amax);

  p_est : process
    variable s1, s2 : positive;
    variable r : real;
    variable p1 : real := 0.5;
    variable n_dif, n_fin, n_alm_apt, n_borr, n_peor_cambia : natural := 0;
    variable amax_ant : unsigned(15 downto 0) := (others => '0');
    variable apt_ant : std_logic := '0';
    variable n_sube : natural := 0;
    variable l : line;
    type t_p is array (0 to 7) of real;
    constant PS : t_p := (0.5, 0.0, 1.0, 0.25, 0.75, 0.05, 0.95, 0.5);
  begin
    s1 := SEMILLA; s2 := SEMILLA * 7 + 3;
    rst_n <= '0';
    wait until falling_edge(clk);
    wait until falling_edge(clk);
    rst_n <= '1';
    for i in 0 to CICLOS - 1 loop
      -- Sesgo que cambia de vez en cuando (en promedio cada ~W/2 muestras).
      uniform(s1, s2, r);
      if r < 2.0 / real(W + 2) then
        uniform(s1, s2, r);
        p1 := PS(integer(floor(r * 8.0)) mod 8);
        if p1 = 0.5 then
          uniform(s1, s2, r);
          p1 := r;   -- sesgo continuo
        end if;
      end if;
      uniform(s1, s2, r);
      if r < p1 then bit_i <= '1'; else bit_i <= '0'; end if;
      uniform(s1, s2, r);
      if r < 0.7 then bit_stb <= '1'; else bit_stb <= '0'; end if;
      uniform(s1, s2, r);
      if r < 1.0 / real(3 * W + 5) then borrar <= '1'; n_borr := n_borr + 1; else borrar <= '0'; end if;
      uniform(s1, s2, r);
      if r < 1.0e-5 then rst_n <= '0'; else rst_n <= '1'; end if;
      wait until rising_edge(clk);
      wait until falling_edge(clk);
      if a_rct /= b_rct or a_apt /= b_apt or a_alm /= b_alm or a_fin /= b_fin or
         a_rmax /= b_rmax or a_amax /= b_amax then
        n_dif := n_dif + 1;
        if n_dif <= 5 then
          write(l, string'("DIF ciclo ") & integer'image(i) & " apt " & std_logic'image(a_apt) &
                std_logic'image(b_apt) & " amax " & integer'image(to_integer(a_amax)) & "/" &
                integer'image(to_integer(b_amax)));
          writeline(output, l);
        end if;
      end if;
      if a_fin = '1' then n_fin := n_fin + 1; end if;
      if a_fin = '1' and a_apt = '1' then n_alm_apt := n_alm_apt + 1; end if;
      if a_amax /= amax_ant then n_peor_cambia := n_peor_cambia + 1; end if;
      amax_ant := a_amax;
      if a_apt = '1' and apt_ant = '0' then n_sube := n_sube + 1; end if;
      apt_ant := a_apt;
    end loop;
    write(l, string'("W=") & integer'image(W) & " C=" & integer'image(C) &
          " RCT=" & integer'image(RCT) & " ciclos=" & integer'image(CICLOS) &
          " ventanas=" & integer'image(n_fin) & " ventanas_con_alarma_apt=" & integer'image(n_alm_apt) &
          " alarmas_apt_levantadas=" & integer'image(n_sube) & " borrados=" & integer'image(n_borr) & " cambios_apt_max=" & integer'image(n_peor_cambia) &
          " diferencias=" & integer'image(n_dif));
    writeline(output, l);
    fin <= true;
    wait;
  end process;
end architecture;
