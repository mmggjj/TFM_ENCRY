-- Sustituto de ring_osc para la sintesis a celdas estandar.
--
-- El anillo real (rtl/trng/ring_osc.vhd) se describe con primitivas
-- UNISIM de Xilinx (LUT1/LUT2) porque en FPGA no hay otra forma de
-- impedir que la sintesis borre el lazo combinacional. Esas primitivas no
-- existen fuera de Vivado, asi que el bloque no puede sintetizarse sobre
-- celdas estandar y por eso motor_top se quedaba sin cifra de area.
--
-- Este sustituto tiene la misma entidad y deja la salida quieta. Sirve
-- SOLO para medir el area del resto del motor en el nivel superior; el
-- area del anillo se cuenta aparte (unas pocas celdas inversoras por
-- anillo) y se declara asi en la memoria. No forma parte del diseno ni se
-- usa en simulacion.

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
  osc <= '0';
end architecture stub;
