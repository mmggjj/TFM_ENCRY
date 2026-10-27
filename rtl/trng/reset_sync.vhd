-- Sincronizador de reset: se activa asincrono y se suelta sincrono.
--
-- El reset de la placa llega cuando quiere. Activarlo asincrono es
-- correcto; soltarlo asincrono no, porque si se suelta cerca de un
-- flanco unos biestables salen del reset en ese ciclo y otros en el
-- siguiente, y una maquina de estados puede arrancar en un estado que
-- no existe. Tres biestables en cadena, a '0' por el reset y rellenados
-- con unos, sueltan el reset con el reloj de su dominio. Hace falta uno
-- por dominio de reloj: el de sistema y el del anillo de muestreo.

library ieee;
use ieee.std_logic_1164.all;

entity reset_sync is
  port (
    clk       : in  std_logic;
    rst_n_in  : in  std_logic;      -- asincrono, de la placa
    rst_n_out : out std_logic       -- activo asincrono, soltado con clk
  );
end entity reset_sync;

architecture rtl of reset_sync is
  signal cadena : std_logic_vector(2 downto 0) := (others => '0');
  attribute ASYNC_REG : string;
  attribute ASYNC_REG of cadena : signal is "TRUE";
begin

  p_sync : process (clk, rst_n_in)
  begin
    if rst_n_in = '0' then
      cadena <= (others => '0');
    elsif rising_edge(clk) then
      cadena <= cadena(1 downto 0) & '1';
    end if;
  end process p_sync;

  rst_n_out <= cadena(2);

end architecture rtl;
