-- Banco de pruebas del oscilador de anillo.
--
-- Comprueba tres cosas, en este orden, porque cada una solo tiene sentido
-- si la anterior se cumple:
--   1. que el anillo arranca, para y oscila a la frecuencia que toca;
--   2. cual es la resolucion del banco, midiendo el jitter con el ruido
--      apagado (lo que salga ahi es ruido numerico del simulador, y marca
--      hasta donde podemos bajar);
--   3. que con ruido inyectado el jitter medido coincide con el teorico.
--
-- El tercero es el que valida el modelo de simulacion: un periodo son 2N
-- retardos de etapa independientes, asi que la desviacion del periodo debe
-- ser sqrt(2N) veces la de una etapa. Si no sale eso, el modelo miente y
-- no sirve de banco para nada.
--
--   ghdl -a --std=08 --work=unisim rtl/sim/unisim_modelos.vhd
--   ghdl -a --std=08 rtl/trng/ring_osc.vhd rtl/tb/tb_ring_osc.vhd
--   ghdl -r --std=08 tb_ring_osc

library ieee;
use ieee.std_logic_1164.all;
use ieee.math_real.all;

library unisim;
use unisim.sim_cfg.all;

entity tb_ring_osc is
end entity tb_ring_osc;

architecture sim of tb_ring_osc is

  constant C_ETAPAS : positive := 5;
  constant C_TPD    : real     := 0.150;   -- ns por etapa
  constant C_SIGMA  : real     := 0.002;   -- ns, 2 ps por etapa
  constant C_N_MED  : positive := 20000;   -- periodos por medida

  signal en  : std_logic := '0';
  signal osc : std_logic;

  -- Devuelve (media, desviacion) del periodo en ps.
  procedure medir(signal s : in std_logic;
                  n : in positive;
                  media : out real;
                  sigma : out real) is
    variable t_ant, t_act : time;
    variable p, suma, suma2, var : real;
  begin
    wait until rising_edge(s);
    t_ant := now;
    suma  := 0.0;
    suma2 := 0.0;
    for i in 1 to n loop
      wait until rising_edge(s);
      t_act := now;
      p     := real((t_act - t_ant) / 1 fs) / 1000.0;   -- ps
      suma  := suma + p;
      suma2 := suma2 + p * p;
      t_ant := t_act;
    end loop;
    media := suma / real(n);
    var   := suma2 / real(n) - media * media;
    sigma := sqrt(abs(var));
  end procedure;

begin

  dut : entity work.ring_osc
    generic map (G_ETAPAS => C_ETAPAS)
    port map (en => en, osc => osc);

  principal : process
    variable media, sigma, esperado, suelo : real;
    variable fallos : natural := 0;

    procedure comprobar(cond : boolean; msg : string) is
    begin
      if cond then
        report "  [ok ] " & msg;
      else
        report "  [FALLO] " & msg severity error;
        fallos := fallos + 1;
      end if;
    end procedure;

  begin
    report "1) Arranque, parada y frecuencia nominal";

    -- Sin ruido: comportamiento determinista.
    cfg.configurar(C_TPD, 0.0);
    en <= '0';
    wait for 50 ns;
    comprobar(osc'stable(20 ns),
              "con habilitacion a cero el anillo esta quieto");

    en <= '1';
    wait for 50 ns;                        -- arranque
    medir(osc, 200, media, sigma);
    esperado := 2.0 * real(C_ETAPAS) * C_TPD * 1000.0;   -- ps
    report "  periodo medido " & real'image(media) &
           " ps, esperado " & real'image(esperado) & " ps";
    comprobar(abs(media - esperado) < 0.02 * esperado,
              "la frecuencia coincide con 1/(2*N*tpd) dentro del 2 %");
    comprobar(media > 0.0, "frecuencia = " &
              real'image(1.0e6 / media) & " MHz");

    report "2) Resolucion del banco: jitter con el ruido apagado";
    medir(osc, C_N_MED, media, suelo);
    report "  suelo de ruido numerico " & real'image(suelo) & " ps";
    comprobar(suelo < 0.05 * sqrt(2.0 * real(C_ETAPAS)) * C_SIGMA * 1000.0,
              "el suelo esta muy por debajo del jitter que hay que medir");

    report "3) Jitter inyectado frente al teorico";
    cfg.configurar(C_TPD, C_SIGMA);
    wait for 100 ns;
    medir(osc, C_N_MED, media, sigma);
    esperado := sqrt(2.0 * real(C_ETAPAS)) * C_SIGMA * 1000.0;   -- ps
    report "  sigma medido " & real'image(sigma) &
           " ps, teorico " & real'image(esperado) & " ps";
    comprobar(abs(sigma - esperado) < 0.10 * esperado,
              "sigma_periodo = sqrt(2N)*sigma_etapa dentro del 10 %");
    report "  jitter relativo sigma/T = " & real'image(sigma / media);

    en <= '0';
    wait for 50 ns;
    comprobar(osc'stable(20 ns), "el anillo vuelve a pararse");

    if fallos = 0 then
      report "tb_ring_osc: 0 fallos" severity note;
    else
      report "tb_ring_osc: " & integer'image(fallos) & " fallos"
        severity failure;
    end if;
    std.env.stop;
  end process principal;

end architecture sim;
