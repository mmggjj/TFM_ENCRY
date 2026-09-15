-- Cruce de dominio de un bit con su valido, por conmutacion de nivel.
--
-- Lleva cada bit muestreado del dominio del anillo al de sistema. En
-- origen se registra el bit y se invierte una senal de conmutacion; en
-- destino se sincroniza esa conmutacion con tres biestables y su cambio
-- marca un bit nuevo. El dato se lee entonces directamente, porque lleva
-- estable desde que cambio la conmutacion.
--
-- Vale mientras cada bit dure bastante mas que la sincronizacion: al
-- menos 8 ciclos de destino. Con K_D >= 64 se cumple de sobra; ver
-- docs/mapa_registros.md. Para tasas mayores (medida de jitter con K_D
-- pequeno) se usa trng_capture, que no cruza bit a bit.

library ieee;
use ieee.std_logic_1164.all;

entity bit_cdc is
  port (
    -- Origen
    clk_o   : in  std_logic;
    bit_o   : in  std_logic;
    stb_o   : in  std_logic;
    -- Destino
    clk_d   : in  std_logic;
    rst_n_d : in  std_logic;
    bit_d   : out std_logic;
    stb_d   : out std_logic
  );
end entity bit_cdc;

architecture rtl of bit_cdc is
  signal dato_o : std_logic := '0';
  signal tog_o  : std_logic := '0';
  signal tog_d  : std_logic_vector(2 downto 0) := (others => '0');
  attribute ASYNC_REG : string;
  attribute ASYNC_REG of tog_d : signal is "TRUE";
begin

  p_origen : process (clk_o)
  begin
    if rising_edge(clk_o) then
      if stb_o = '1' then
        dato_o <= bit_o;
        tog_o  <= not tog_o;
      end if;
    end if;
  end process p_origen;

  p_destino : process (clk_d, rst_n_d)
  begin
    if rst_n_d = '0' then
      tog_d <= (others => '0');
      stb_d <= '0';
      bit_d <= '0';
    elsif rising_edge(clk_d) then
      tog_d <= tog_d(1 downto 0) & tog_o;
      stb_d <= tog_d(2) xor tog_d(1);
      if (tog_d(2) xor tog_d(1)) = '1' then
        bit_d <= dato_o;
      end if;
    end if;
  end process p_destino;

end architecture rtl;
