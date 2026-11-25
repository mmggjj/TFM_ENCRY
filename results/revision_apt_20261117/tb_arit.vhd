-- Comparacion exhaustiva de las condiciones de cierre de ventana del APT:
-- HEAD (restas en 16 bits) frente a la version nueva (constantes).
library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use std.textio.all;

entity tb_arit is
  generic (W_MAX : positive := 300; C_EXTRA : natural := 3;
           TODO_C16 : boolean := false);
end entity;

architecture sim of tb_arit is
  procedure probar(W, C : positive; cmin, cmax : natural;
                   variable n, nd_alm, nd_peor : inout natural) is
    variable coincide : unsigned(15 downto 0);
    variable alm_old, alm_new, may_old, may_new : boolean;
    variable comp : boolean;
    variable lim, mitad : natural;
    variable l : line;
  begin
    comp := W >= C;
    if W >= C then lim := W - C; else lim := 0; end if;
    mitad := (W + 1) / 2;
    for cv in cmin to cmax loop
      coincide := to_unsigned(cv, 16);
      alm_old := coincide >= C or (to_unsigned(W, 16) - coincide) >= C;
      alm_new := coincide >= C or (comp and coincide <= lim);
      may_old := coincide >= to_unsigned(W, 16) - coincide;
      may_new := coincide >= mitad;
      n := n + 1;
      if alm_old /= alm_new then
        nd_alm := nd_alm + 1;
        if nd_alm <= 5 then
          write(l, string'("DIF alarma W=") & integer'image(W) & " C=" & integer'image(C) &
                " c=" & integer'image(cv) & " old=" & boolean'image(alm_old) &
                " new=" & boolean'image(alm_new));
          writeline(output, l);
        end if;
      end if;
      if may_old /= may_new then
        nd_peor := nd_peor + 1;
        if nd_peor <= 5 then
          write(l, string'("DIF peor W=") & integer'image(W) & " C=" & integer'image(C) &
                " c=" & integer'image(cv) & " old=" & boolean'image(may_old) &
                " new=" & boolean'image(may_new));
          writeline(output, l);
        end if;
      end if;
    end loop;
  end procedure;
begin
  process
    variable n, nda, ndp : natural := 0;
    variable l : line;
    type t_ws is array (natural range <>) of positive;
    constant WS : t_ws := (511, 512, 513, 766, 767, 1023, 1024, 1025, 2047, 2048);
    constant WG : t_ws := (32767, 32768, 65533, 65534, 65535);
  begin
    if not TODO_C16 then
      -- 1) Rango alcanzable c en [1, W], todo W <= W_MAX, todo C <= W + C_EXTRA.
      for W in 1 to W_MAX loop
        for C in 1 to W + C_EXTRA loop
          probar(W, C, 1, W, n, nda, ndp);
        end loop;
      end loop;
      write(l, string'("tramo1 W<=") & integer'image(W_MAX) & " casos=" & integer'image(n) &
            " dif_alarma=" & integer'image(nda) & " dif_peor=" & integer'image(ndp));
      writeline(output, l);
      -- 2) W tipicos, todo C <= W + 3, c en [1, W].
      for i in WS'range loop
        for C in 1 to WS(i) + 3 loop
          probar(WS(i), C, 1, WS(i), n, nda, ndp);
        end loop;
      end loop;
      write(l, string'("tramo2 casos acumulados=") & integer'image(n) &
            " dif_alarma=" & integer'image(nda) & " dif_peor=" & integer'image(ndp));
      writeline(output, l);
      -- 3) W grandes (hasta el limite de 16 bits), C muestreado, c en [1, W].
      for i in WG'range loop
        for k in 0 to 40 loop
          probar(WG(i), 1 + (k * WG(i)) / 40 + (k mod 3), 1, WG(i), n, nda, ndp);
        end loop;
        probar(WG(i), WG(i), 1, WG(i), n, nda, ndp);
        probar(WG(i), WG(i) + 1, 1, WG(i), n, nda, ndp);
        probar(WG(i), (WG(i) + 1) / 2, 1, WG(i), n, nda, ndp);
      end loop;
      write(l, string'("tramo3 casos acumulados=") & integer'image(n) &
            " dif_alarma=" & integer'image(nda) & " dif_peor=" & integer'image(ndp));
      writeline(output, l);
    else
      -- 4) Informativo: c en todo el rango de 16 bits (incluye c = 0 y c > W,
      --    inalcanzables en el diseno).
      for W in 1 to 40 loop
        for C in 1 to W + 3 loop
          probar(W, C, 0, 65535, n, nda, ndp);
        end loop;
      end loop;
      write(l, string'("tramo4 (c en 0..65535) casos=") & integer'image(n) &
            " dif_alarma=" & integer'image(nda) & " dif_peor=" & integer'image(ndp));
      writeline(output, l);
    end if;
    wait;
  end process;
end architecture;
