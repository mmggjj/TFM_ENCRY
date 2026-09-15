-- Modelos de simulacion de las primitivas LUT1 y LUT2 de Xilinx.
--
-- Vivado trae los modelos UNISIM reales, pero no se distribuyen por
-- separado, asi que para simular con GHDL o NVC sin tener Vivado
-- instalado se compila este fichero en la biblioteca "unisim".
--
--   ghdl -a --std=08 --work=unisim rtl/sim/unisim_modelos.vhd
--
-- Diferencia deliberada con el modelo real: aqui la LUT tiene retardo, y
-- ese retardo lleva ruido gaussiano opcional. Sin retardo un oscilador de
-- anillo no converge en simulacion, y sin ruido no se puede comprobar que
-- la cadena de medida de jitter recupera el jitter inyectado.
--
-- El banco de pruebas ajusta retardo y ruido con unisim.sim_cfg.cfg.

library ieee;
use ieee.math_real.all;

package sim_cfg is

  type t_cfg is protected
    -- tpd_ns: retardo medio por LUT. sigma_ns: desviacion tipica del
    -- ruido por transicion (0 = sin jitter, simulacion determinista).
    procedure configurar(tpd_ns : real; sigma_ns : real);
    procedure sembrar(s1 : positive; s2 : positive);
    impure function tpd return real;
    impure function retardo return real;
  end protected t_cfg;

  shared variable cfg : t_cfg;

end package sim_cfg;


package body sim_cfg is

  type t_cfg is protected body
    variable v_tpd      : real     := 0.150;   -- ns
    variable v_sigma    : real     := 0.0;     -- ns
    variable v_s1       : positive := 42;
    variable v_s2       : positive := 4242;
    variable v_pendiente : boolean := false;
    variable v_guardado  : real    := 0.0;

    procedure configurar(tpd_ns : real; sigma_ns : real) is
    begin
      v_tpd   := tpd_ns;
      v_sigma := sigma_ns;
    end procedure;

    procedure sembrar(s1 : positive; s2 : positive) is
    begin
      v_s1 := s1;
      v_s2 := s2;
      v_pendiente := false;
    end procedure;

    impure function tpd return real is
    begin
      return v_tpd;
    end function;

    -- Box-Muller; la segunda muestra se guarda para la llamada siguiente.
    impure function retardo return real is
      variable r1, r2, g, d : real;
    begin
      if v_sigma = 0.0 then
        return v_tpd;
      end if;
      if v_pendiente then
        v_pendiente := false;
        g := v_guardado;
      else
        uniform(v_s1, v_s2, r1);
        uniform(v_s1, v_s2, r2);
        if r1 < 1.0e-12 then
          r1 := 1.0e-12;
        end if;
        g          := sqrt(-2.0 * log(r1)) * cos(MATH_2_PI * r2);
        v_guardado := sqrt(-2.0 * log(r1)) * sin(MATH_2_PI * r2);
        v_pendiente := true;
      end if;
      d := v_tpd + g * v_sigma;
      if d < 0.001 then      -- un retardo nulo o negativo colgaria el motor
        d := 0.001;
      end if;
      return d;
    end function;

  end protected body t_cfg;

end package body sim_cfg;


-- ---------------------------------------------------------------------
-- LUT1: O = INIT(conv(I0))
-- ---------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
library unisim;
use unisim.sim_cfg.all;

entity LUT1 is
  generic (INIT : bit_vector(1 downto 0) := "00");
  port (
    O  : out std_ulogic;
    I0 : in  std_ulogic
  );
end entity LUT1;

architecture modelo of LUT1 is
begin
  -- Con la entrada desconocida se evaluan las dos posibilidades: si
  -- ambas dan lo mismo, la salida esta definida. Es lo que hace una
  -- puerta real cuando una entrada es dominante, y es imprescindible
  -- aqui: al arrancar la simulacion la cadena del anillo esta indefinida,
  -- y sin esto el indefinido se realimenta para siempre y el anillo no
  -- arranca nunca.
  process (I0)
    variable v : std_ulogic;
  begin
    case I0 is
      when '0' | 'L' => v := to_stdulogic(INIT(0));
      when '1' | 'H' => v := to_stdulogic(INIT(1));
      when others    =>
        if INIT(0) = INIT(1) then
          v := to_stdulogic(INIT(0));
        else
          v := 'X';
        end if;
    end case;
    O <= v after cfg.retardo * 1 ns;
  end process;
end architecture modelo;


-- ---------------------------------------------------------------------
-- LUT2: O = INIT(I1 & I0)
-- ---------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;
library unisim;
use unisim.sim_cfg.all;

entity LUT2 is
  generic (INIT : bit_vector(3 downto 0) := "0000");
  port (
    O  : out std_ulogic;
    I0 : in  std_ulogic;
    I1 : in  std_ulogic
  );
end entity LUT2;

architecture modelo of LUT2 is

  -- Valores posibles de una entrada: (0,0) si vale cero, (1,1) si vale
  -- uno, y (0,1) si es desconocida.
  procedure rango(v : in std_ulogic; lo : out natural; hi : out natural) is
  begin
    case v is
      when '0' | 'L' => lo := 0; hi := 0;
      when '1' | 'H' => lo := 1; hi := 1;
      when others    => lo := 0; hi := 1;
    end case;
  end procedure;

begin
  -- Se recorren todas las combinaciones compatibles con lo que se sabe de
  -- las entradas. Si todas dan el mismo valor, la salida esta definida
  -- aunque una entrada sea desconocida: es el caso de la NAND de
  -- arranque del anillo con la habilitacion a cero, que debe dar uno sin
  -- importar lo que llegue por la realimentacion. Sin esto el anillo no
  -- sale nunca del estado indefinido al empezar la simulacion.
  process (I0, I1)
    variable a_lo, a_hi, b_lo, b_hi : natural;
    variable v, primero : std_ulogic;
    variable igual : boolean := true;
  begin
    rango(I0, a_lo, a_hi);
    rango(I1, b_lo, b_hi);
    primero := to_stdulogic(INIT(b_lo * 2 + a_lo));
    igual   := true;
    for a in a_lo to a_hi loop
      for b in b_lo to b_hi loop
        if to_stdulogic(INIT(b * 2 + a)) /= primero then
          igual := false;
        end if;
      end loop;
    end loop;
    if igual then
      v := primero;
    else
      v := 'X';
    end if;
    O <= v after cfg.retardo * 1 ns;
  end process;
end architecture modelo;


-- ---------------------------------------------------------------------
-- Paquete de componentes, con el mismo nombre que el de Vivado para que
-- el RTL no cambie entre simulacion y sintesis.
-- ---------------------------------------------------------------------
library ieee;
use ieee.std_logic_1164.all;

package vcomponents is

  component LUT1 is
    generic (INIT : bit_vector(1 downto 0) := "00");
    port (
      O  : out std_ulogic;
      I0 : in  std_ulogic
    );
  end component LUT1;

  component LUT2 is
    generic (INIT : bit_vector(3 downto 0) := "0000");
    port (
      O  : out std_ulogic;
      I0 : in  std_ulogic;
      I1 : in  std_ulogic
    );
  end component LUT2;

end package vcomponents;
