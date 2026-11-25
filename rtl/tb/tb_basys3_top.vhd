-- Banco del envoltorio de la Basys 3: el frecuencimetro sobre los anillos
-- de verdad del motor (modelo de LUT con retardo y jitter de
-- rtl/sim/unisim_modelos.vhd).
--
-- El banco mide el periodo medio de cada anillo contando sus flancos (por
-- nombre externo) y exige que el display marque esa frecuencia a +-1
-- cuenta; que sw1 elija el anillo; y que JA3 quede a 0 sin modo test y
-- saque el anillo / 64 con el. El motor en si lo cubre tb_motor_top.
-- Retardo de LUT 0,3 ns: ro2 (5 etapas) a ~333 MHz y ro1 (7) a ~238 MHz.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library unisim;
use unisim.sim_cfg.all;

entity tb_basys3_top is
end entity tb_basys3_top;

architecture sim of tb_basys3_top is

  signal clk     : std_logic := '0';
  signal btn_rst : std_logic := '1';
  signal sw_test : std_logic := '0';
  signal sw_ro   : std_logic := '0';
  signal scl     : std_logic := '1';
  signal sda     : std_logic := 'H';
  signal led_alarma, led_vivo, ro_div, dp : std_logic;
  signal seg     : std_logic_vector(6 downto 0);
  signal an      : std_logic_vector(3 downto 0);
  signal fin     : boolean := false;
  -- Copia de los anillos del motor: GHDL 4 no deja esperar sobre el alias
  -- de un nombre externo, si sobre una senal del banco.
  signal ro_mon  : std_logic_vector(1 downto 0);

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
      when others    => return -1;
    end case;
  end function;

begin

  clk <= not clk after 5 ns when not fin;
  sda <= 'H';                          -- pull-up del bus

  dut : entity work.basys3_top
    port map (clk => clk, btn_rst => btn_rst, sw_test => sw_test,
              scl => scl, sda => sda, led_alarma => led_alarma,
              led_vivo => led_vivo, sw_ro => sw_ro, ro_div => ro_div,
              seg => seg, dp => dp, an => an);

  -- Despues de dut: el nombre externo tiene que estar ya elaborado.
  b_ro : block is
    alias ro_dut is << signal .tb_basys3_top.dut.ro_mon : std_logic_vector(1 downto 0) >>;
  begin
    ro_mon <= ro_dut;
  end block b_ro;

  p_estimulo : process
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

    -- Periodo medio del anillo i en ps sobre n flancos de subida
    procedure periodo(i : natural; n : positive; variable p : out real) is
      variable t0 : time;
      variable prev : std_logic;
      variable k : integer := -1;
    begin
      prev := ro_mon(i);
      while k < n loop
        wait on ro_mon;
        if ro_mon(i) = '1' and prev = '0' then
          if k < 0 then t0 := now; end if;
          k := k + 1;
        end if;
        prev := ro_mon(i);
      end loop;
      p := real((now - t0) / 1 fs) / 1000.0 / real(n);
    end procedure;

    -- Lee el display completo: espera a ver los cuatro anodos
    procedure display(variable v : out integer; variable punto_ok : out boolean) is
      variable dig : integer;
      variable visto : std_logic_vector(3 downto 0) := "0000";
      variable d : integer;
    begin
      v := 0; punto_ok := true;
      while visto /= "1111" loop
        wait on an;
        wait for 1 ns;
        for i in 0 to 3 loop
          if an(i) = '0' and visto(i) = '0' then
            visto(i) := '1';
            d := de_seg(seg);
            if d < 0 then d := 0; punto_ok := false; end if;
            v := v + d * 10 ** i;
            if (dp = '0') /= (i = 1) then punto_ok := false; end if;
          end if;
        end loop;
      end loop;
    end procedure;

    -- Una ventana completa nueva: espera 2 x 640 us
    procedure ventanas is
    begin
      wait for 1300 us;
    end procedure;

    procedure comprobar(i : natural; nombre : string) is
      variable p : real;
      variable v : integer;
      variable pok : boolean;
      variable esperado : real;
    begin
      periodo(i, 20000, p);
      esperado := 10_000_000.0 / p;      -- en unidades de 100 kHz
      display(v, pok);
      chk(abs (real(v) - esperado) <= 1.0 and pok,
          nombre & ": periodo medio " & real'image(p) & " ps, display "
          & integer'image(v) & " (x100 kHz), esperado " & real'image(esperado));
    end procedure;

    variable t0 : time;
    variable cambios : natural;
    variable p : real;
  begin
    cfg.configurar(0.300, 0.002);
    btn_rst <= '1';
    wait for 200 ns;
    btn_rst <= '0';

    -- 1. ro2 en el display (sw1 abajo)
    sw_ro <= '0';
    ventanas;
    comprobar(1, "ro2");

    -- 2. JA3 a 0 sin modo test
    cambios := 0;
    t0 := now;
    while now - t0 < 20 us loop
      wait on ro_div for 20 us - (now - t0);
      if ro_div'event then cambios := cambios + 1; end if;
    end loop;
    chk(cambios = 0 and ro_div = '0', "JA3 quieto a 0 sin modo test ("
        & integer'image(cambios) & " cambios en 20 us)");

    -- 3. ro1 en el display (sw1 arriba)
    sw_ro <= '1';
    ventanas;
    comprobar(0, "ro1");

    -- 4. Con modo test JA3 saca ro1 / 64
    sw_test <= '1';
    wait for 1 us;
    periodo(0, 2000, p);
    wait until rising_edge(ro_div);
    t0 := now;
    for k in 1 to 50 loop
      wait until rising_edge(ro_div);
    end loop;
    chk(abs (real((now - t0) / 1 fs) / 1000.0 / 50.0 - 64.0 * p) < 0.01 * 64.0 * p,
        "JA3 con modo test: periodo " & integer'image((now - t0) / 50 ps)
        & " ps = 64 x ro1 (" & real'image(p) & " ps)");

    report "resultado: " & integer'image(n_ok) & " ok, "
           & integer'image(n_fallo) & " fallos";
    assert n_fallo = 0 report "tb_basys3_top: hay fallos" severity failure;
    fin <= true;
    std.env.stop;
    wait;
  end process p_estimulo;

end architecture sim;
