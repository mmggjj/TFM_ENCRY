-- Sustituto de ring_osc para la sintesis a celdas estandar.
--
-- El anillo real (rtl/trng/ring_osc.vhd) se describe con primitivas
-- UNISIM de Xilinx (LUT1/LUT2) porque en FPGA no hay otra forma de
-- impedir que la sintesis borre el lazo combinacional. Esas primitivas no
-- existen fuera de Vivado, asi que el bloque no puede sintetizarse sobre
-- celdas estandar y por eso motor_top se quedaba sin cifra de area.
--
-- Este sustituto tiene la misma entidad. Sirve SOLO para medir el area del
-- resto del motor en el nivel superior; el area del anillo se cuenta
-- aparte (unas pocas celdas inversoras por anillo) y se declara asi en la
-- memoria. No forma parte del diseno ni se usa en simulacion.
--
-- OJO CON LA SALIDA, que es la parte no evidente. La primera version hacia
-- "osc <= '0'" y el resultado estaba mal: con la salida constante, el
-- plugin de GHDL aplana la jerarquia, Yosys propaga la constante hacia
-- delante y el optimizador borra todo lo que cuelga del anillo. Medido
-- sobre motor_top con IHP SG13G2:
--
--     osc <= '0'   ->  3365 biestables,  438834 um2  (60,5 kGE)
--     osc <= en    ->  8405 biestables,  827254 um2  (114,0 kGE)
--
-- Cinco mil biestables desaparecidos: el buffer de captura entero y el
-- registro de semilla. El area habria salido a poco mas de la mitad.
--
-- Con "osc <= en" la salida depende de un biestable (en_anillos), el
-- optimizador ya no puede plegarla y la logica de detras sobrevive. El
-- circuito resultante no oscila, pero para contar area da igual: se mide
-- cuanta logica hay, no si funciona. Marcar el modulo como caja negra no
-- sirve aqui, porque "ghdl -e" ya ha aplanado la jerarquia y Yosys no ve
-- ninguna instancia llamada ring_osc.

library ieee;
use ieee.std_logic_1164.all;

entity ring_osc is
  generic (
    G_ETAPAS : positive := 5
  );
  port (
    en  : in  std_logic;
    osc : out std_logic
  );
end entity ring_osc;

architecture stub of ring_osc is
begin
  -- No constante, a proposito: ver la nota de la cabecera.
  osc <= en;
end architecture stub;
