-- Cuatro digitos de 7 segmentos multiplexados (anodo comun, activos a
-- nivel bajo, como en la Basys 3). Refresco: clk / 2**G_DIV por digito.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity siete_seg is
  generic (
    G_DIV : positive := 17            -- 100 MHz / 2**17: ~760 Hz los cuatro
  );
  port (
    clk    : in  std_logic;
    bcd    : in  std_logic_vector(15 downto 0);   -- digito 3 (izquierda) arriba
    punto  : in  std_logic_vector(3 downto 0);    -- punto decimal por digito
    raya   : in  std_logic;                       -- muestra "----"
    seg    : out std_logic_vector(6 downto 0);    -- g f e d c b a
    dp     : out std_logic;
    an     : out std_logic_vector(3 downto 0)
  );
end entity siete_seg;

architecture rtl of siete_seg is

  signal div : unsigned(G_DIV - 1 downto 0) := (others => '0');

  -- Segmentos encendidos (1) de cada cifra, en el orden g f e d c b a.
  function cifra(d : std_logic_vector(3 downto 0)) return std_logic_vector is
  begin
    case d is
      when x"0" => return "0111111";
      when x"1" => return "0000110";
      when x"2" => return "1011011";
      when x"3" => return "1001111";
      when x"4" => return "1100110";
      when x"5" => return "1101101";
      when x"6" => return "1111101";
      when x"7" => return "0000111";
      when x"8" => return "1111111";
      when x"9" => return "1101111";
      when others => return "1000000";  -- no es BCD: raya
    end case;
  end function;

begin

  p_div : process (clk)
  begin
    if rising_edge(clk) then
      div <= div + 1;
    end if;
  end process p_div;

  p_salida : process (div, bcd, punto, raya)
    variable i : natural range 0 to 3;
    variable s : std_logic_vector(6 downto 0);
  begin
    i := to_integer(div(G_DIV - 1 downto G_DIV - 2));
    if raya = '1' then
      s := "1000000";
    else
      s := cifra(bcd(4 * i + 3 downto 4 * i));
    end if;
    seg <= not s;
    dp <= not punto(i);
    an <= (others => '1');
    an(i) <= '0';
  end process p_salida;

end architecture rtl;
