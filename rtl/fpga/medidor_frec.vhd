-- Frecuencimetro de un anillo, solo para la placa.
--
-- El anillo se divide por 2**G_PRE en su propio dominio; el divisor se
-- sincroniza al reloj de placa y se cuentan sus flancos durante
-- G_VENTANA ciclos, en BCD. Con los valores por defecto (64 y 64 000
-- ciclos de 100 MHz = 640 us) una cuenta vale 100 kHz: los cuatro digitos
-- son la frecuencia en MHz con un decimal, hasta 999,9. Error de +-1
-- cuenta (100 kHz) mas la tolerancia del oscilador de placa (+-50 ppm).
-- Limite: el anillo dividido debe quedar por debajo de clk/2, 3,2 GHz.
--
-- Razon en docs/puesta_en_marcha_fpga.md.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity medidor_frec is
  generic (
    G_PRE     : positive := 6;
    G_VENTANA : positive := 64000
  );
  port (
    clk      : in  std_logic;
    rst_n    : in  std_logic;                       -- dominio clk, ya sincronizado
    ro       : in  std_logic;
    presc_o  : out std_logic;                       -- ro / 2**G_PRE, dominio ro
    bcd      : out std_logic_vector(15 downto 0);   -- 4 digitos, el de mayor peso arriba
    desborde : out std_logic;                       -- la ultima ventana paso de 9999
    nueva    : out std_logic                        -- pulso: bcd actualizado
  );
end entity medidor_frec;

architecture rtl of medidor_frec is

  -- Sin reset: solo cuenta, y su valor inicial da igual.
  signal presc : unsigned(G_PRE - 1 downto 0) := (others => '0');

  signal sinc  : std_logic_vector(2 downto 0) := (others => '0');
  attribute ASYNC_REG : string;
  attribute ASYNC_REG of sinc : signal is "TRUE";

  type t_digitos is array (0 to 3) of unsigned(3 downto 0);
  signal cuenta  : t_digitos := (others => (others => '0'));
  signal lleno   : std_logic := '0';
  signal ciclos  : natural range 0 to G_VENTANA - 1 := 0;
  signal bcd_r   : std_logic_vector(15 downto 0) := (others => '0');
  signal desb_r  : std_logic := '0';
  signal nueva_r : std_logic := '0';

begin

  p_presc : process (ro)
  begin
    if rising_edge(ro) then
      presc <= presc + 1;
    end if;
  end process p_presc;
  presc_o <= presc(G_PRE - 1);

  p_cuenta : process (clk, rst_n)
    variable acarreo : boolean;
    variable c       : t_digitos;
    variable ll      : std_logic;
  begin
    if rst_n = '0' then
      sinc <= (others => '0');
      cuenta <= (others => (others => '0'));
      lleno <= '0'; ciclos <= 0;
      bcd_r <= (others => '0'); desb_r <= '0'; nueva_r <= '0';
    elsif rising_edge(clk) then
      sinc <= sinc(1 downto 0) & presc(G_PRE - 1);
      nueva_r <= '0';
      c := cuenta;
      ll := lleno;
      -- Flanco de subida del anillo dividido: +1 en BCD, saturando en 9999.
      if sinc(2) = '0' and sinc(1) = '1' and ll = '0' then
        acarreo := true;
        for i in 0 to 3 loop
          if acarreo then
            if c(i) = 9 then
              c(i) := (others => '0');
            else
              c(i) := c(i) + 1;
              acarreo := false;
            end if;
          end if;
        end loop;
        if acarreo then                 -- 9999 + 1
          c := (others => to_unsigned(9, 4));
          ll := '1';
        end if;
      end if;
      if ciclos = G_VENTANA - 1 then
        ciclos <= 0;
        bcd_r <= std_logic_vector(c(3)) & std_logic_vector(c(2))
               & std_logic_vector(c(1)) & std_logic_vector(c(0));
        desb_r <= ll;
        nueva_r <= '1';
        cuenta <= (others => (others => '0'));
        lleno <= '0';
      else
        ciclos <= ciclos + 1;
        cuenta <= c;
        lleno <= ll;
      end if;
    end if;
  end process p_cuenta;

  bcd <= bcd_r;
  desborde <= desb_r;
  nueva <= nueva_r;

end architecture rtl;
