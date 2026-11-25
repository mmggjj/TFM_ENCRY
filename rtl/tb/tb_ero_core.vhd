-- Banco de ero_core: las dos formas de muestrear ro1 (con habilitacion y
-- libre, G_MUESTREO_LIBRE) dan los mismos bits con los mismos anillos.
--
-- Anillos ideales de periodos inconmensurables (ro1 9,2 ns, ro2 7,0 ns
-- con un paso de fase lento) y varios divisores; se comparan bit y valido
-- de las dos instancias en cada flanco de ro2 y se cuenta que haya bits y
-- de los dos valores.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_ero_core is
end entity tb_ero_core;

architecture sim of tb_ero_core is
  signal ro1, ro2  : std_logic := '0';
  signal rst_n     : std_logic := '0';
  signal kd_sel    : unsigned(4 downto 0) := to_unsigned(0, 5);
  signal b_h, b_l  : std_logic;
  signal s_h, s_l  : std_logic;
  signal fin       : boolean := false;
  signal n_bits, n_unos, n_dif, n_stb_dif : natural := 0;
begin

  -- ro1 con un periodo que deriva despacio: la fase relativa recorre todo
  -- el periodo de ro2 y salen bits de los dos valores.
  p_ro1 : process
    variable t : time := 4600 ps;
  begin
    while not fin loop
      ro1 <= not ro1;
      wait for t;
      t := 4600 ps + ((t - 4600 ps + 3 ps) mod 200 ps);
    end loop;
    wait;
  end process;

  p_ro2 : process
  begin
    while not fin loop
      ro2 <= not ro2;
      wait for 3500 ps;
    end loop;
    wait;
  end process;

  u_hab : entity work.ero_core
    generic map (G_MUESTREO_LIBRE => false)
    port map (ro1 => ro1, ro2 => ro2, rst_n => rst_n, kd_sel => kd_sel,
              bit_o => b_h, bit_stb => s_h);

  u_lib : entity work.ero_core
    generic map (G_MUESTREO_LIBRE => true)
    port map (ro1 => ro1, ro2 => ro2, rst_n => rst_n, kd_sel => kd_sel,
              bit_o => b_l, bit_stb => s_l);

  p_cmp : process (ro2)
  begin
    if falling_edge(ro2) and rst_n = '1' then
      if s_h /= s_l then
        n_stb_dif <= n_stb_dif + 1;
      end if;
      if s_h = '1' then
        n_bits <= n_bits + 1;
        if b_h = '1' then
          n_unos <= n_unos + 1;
        end if;
        if b_h /= b_l then
          n_dif <= n_dif + 1;
        end if;
      end if;
    end if;
  end process;

  p_main : process
    variable fallos : natural := 0;
    variable b0, u0 : natural;
    procedure chk(c : boolean; m : string) is
    begin
      if c then
        report "[ok] " & m;
      else
        report "[FALLO] " & m severity error;
        fallos := fallos + 1;
      end if;
    end procedure;
  begin
    for kd in 0 to 4 loop
      rst_n <= '0';
      kd_sel <= to_unsigned(kd, 5);
      wait for 20 ns;
      rst_n <= '1';
      b0 := n_bits;
      u0 := n_unos;
      wait for 400 us;
      chk(n_bits - b0 > 1000 / (2 ** kd), "kd " & integer'image(kd) & ": " &
          integer'image(n_bits - b0) & " bits");
      chk(n_unos - u0 > 0 and n_unos - u0 < n_bits - b0,
          "kd " & integer'image(kd) & ": bits de los dos valores (" &
          integer'image(n_unos - u0) & " unos)");
    end loop;
    chk(n_dif = 0, "mismo bit en las dos variantes (" & integer'image(n_dif) &
        " distintos de " & integer'image(n_bits) & ")");
    chk(n_stb_dif = 0, "mismo valido en las dos variantes (" &
        integer'image(n_stb_dif) & " ciclos distintos)");
    if fallos = 0 then
      report "tb_ero_core: todo correcto";
    else
      report "tb_ero_core: " & integer'image(fallos) & " fallos" severity error;
    end if;
    fin <= true;
    std.env.stop;
    wait;
  end process;

end architecture sim;
