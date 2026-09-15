-- Oscilador de anillo con habilitacion.
--
-- ES EL UNICO MODULO ATADO A LA TECNOLOGIA. El resto del motor (SHA-256,
-- DRBG, AES, CMAC, SPI) se escribe en VHDL independiente del fabricante
-- para que pueda sintetizarse tambien sobre celdas estandar. Aqui no hay
-- alternativa: en FPGA el inversor es una LUT1 y en un circuito integrado
-- seria una celda inversora, y el jitter de cada uno no tiene nada que
-- ver. Ver docs/via_asic.md.
--
-- Por que primitivas y no "q <= not q":
--   - la sintesis eliminaria el lazo por considerarlo logica inutil;
--   - dos anillos descritos igual pueden fusionarse en uno solo, y se
--     mediria "N anillos" teniendo uno;
--   - DONT_TOUCH se propaga a implementacion, KEEP solo llega a sintesis.
-- Ademas hace falta, en el fichero de restricciones y no aqui:
--   set_property ALLOW_COMBINATORIAL_LOOPS TRUE [get_nets .../cadena[*]]
--   set_disable_timing -from I0 -to O [get_cells .../u_inv[*]]
-- y un pblock por anillo para que no compartan region.
--
-- El numero de inversiones debe ser impar contando la NAND, que con
-- habilitacion a 1 se comporta como inversor. Con habilitacion a 0 la
-- cadena queda en un estado estable conocido y el anillo no consume.

library ieee;
use ieee.std_logic_1164.all;

library unisim;
use unisim.vcomponents.all;

entity ring_osc is
  generic (
    -- Etapas totales, impar. La 0 es la NAND de arranque.
    G_ETAPAS : positive := 5
  );
  port (
    en  : in  std_logic;   -- asincrono: arranca y para el anillo
    osc : out std_logic
  );
end entity ring_osc;

architecture rtl of ring_osc is

  signal cadena : std_logic_vector(G_ETAPAS - 1 downto 0);

  -- Impiden que la sintesis borre el lazo o fusione anillos iguales.
  attribute DONT_TOUCH : string;
  attribute DONT_TOUCH of cadena : signal is "TRUE";

begin

  assert (G_ETAPAS mod 2) = 1
    report "ring_osc: G_ETAPAS debe ser impar para que el anillo oscile"
    severity failure;

  -- Etapa 0: NAND. INIT "0111" = not (I0 and I1).
  u_nand : LUT2
    generic map (INIT => "0111")
    port map (
      O  => cadena(0),
      I0 => en,
      I1 => cadena(G_ETAPAS - 1)
    );

  -- Etapas 1..N-1: inversores. INIT "01" = not I0.
  g_inv : for i in 1 to G_ETAPAS - 1 generate
    u_inv : LUT1
      generic map (INIT => "01")
      port map (
        O  => cadena(i),
        I0 => cadena(i - 1)
      );
  end generate g_inv;

  osc <= cadena(G_ETAPAS - 1);

end architecture rtl;
