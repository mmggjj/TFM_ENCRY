-- Nucleo ERO: muestrea RO1 con RO2 dividido por K_D.
--
-- Es la arquitectura con modelo estocastico demostrable (Baudet 2011,
-- Killmann-Schindler 2008) y con medidor de jitter embebido publicado
-- (Fischer-Lubicz 2014), que es lo que permite acotar la min-entropia en
-- vez de solo pasar tests. Ver docs/modelo_ero_resultados.md.
--
-- K_D = 2**kd_sel es ajustable en caliente porque el nucleo trabaja en
-- dos modos con necesidades opuestas:
--   - medida de jitter: K_D pequeno, para que la fase acumulada entre
--     bits emparejados no alcance el vertice de la onda triangular;
--   - generacion: K_D grande, para acumular Q >= 0,23 por bit.
--
-- Este modulo no cruza de dominio de reloj: entrega el bit en el dominio
-- de RO2. El paso a clk_sys lo hace el buffer de captura, que guarda un
-- trozo entero a la velocidad del anillo y luego lo vuelca despacio.
--
-- Independiente de la tecnologia: solo logica sintetizable estandar.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity ero_core is
  generic (
    -- Ancho del divisor. K_D maximo = 2**G_CNT_BITS.
    G_CNT_BITS : positive := 20
  );
  port (
    ro1     : in  std_logic;                     -- anillo muestreado
    ro2     : in  std_logic;                     -- anillo de muestreo
    rst_n   : in  std_logic;                     -- asincrono
    kd_sel  : in  unsigned(4 downto 0);          -- K_D = 2**kd_sel
    bit_o   : out std_logic;                     -- bit crudo
    bit_stb : out std_logic                      -- valido un periodo de ro2
  );
end entity ero_core;

architecture rtl of ero_core is

  signal cuenta   : unsigned(G_CNT_BITS - 1 downto 0) := (others => '0');
  signal mascara  : unsigned(G_CNT_BITS - 1 downto 0);
  signal tic      : std_logic;

  -- Captura directa de ro1: puede quedar metaestable, y esa
  -- metaestabilidad forma parte de la fuente de entropia. Se le da un
  -- flip-flop de resolucion antes de que el bit toque nada mas, para que
  -- la metaestabilidad no se propague a la logica de control.
  signal muestra_cruda : std_logic := '0';
  signal muestra_res   : std_logic := '0';
  -- El valido se retrasa dos ciclos, los mismos que tarda la muestra en
  -- llegar a muestra_res, para que salgan alineados.
  signal stb_d1 : std_logic := '0';

  attribute ASYNC_REG : string;
  attribute ASYNC_REG of muestra_cruda : signal is "TRUE";
  attribute ASYNC_REG of muestra_res   : signal is "TRUE";

begin

  -- mascara = 2**kd_sel - 1. Con kd_sel = 0 la mascara es cero, la
  -- condicion se cumple siempre y K_D vale 1 (modo medida).
  mascara <= shift_left(to_unsigned(1, G_CNT_BITS), to_integer(kd_sel))
             - to_unsigned(1, G_CNT_BITS);

  tic <= '1' when (cuenta and mascara) = mascara else '0';

  p_divisor : process (ro2, rst_n)
  begin
    if rst_n = '0' then
      cuenta <= (others => '0');
    elsif rising_edge(ro2) then
      cuenta <= cuenta + 1;
    end if;
  end process p_divisor;

  p_muestreo : process (ro2, rst_n)
  begin
    if rst_n = '0' then
      muestra_cruda <= '0';
      muestra_res   <= '0';
      stb_d1        <= '0';
      bit_stb       <= '0';
    elsif rising_edge(ro2) then
      if tic = '1' then
        muestra_cruda <= ro1;
      end if;
      muestra_res <= muestra_cruda;
      stb_d1      <= tic;
      bit_stb     <= stb_d1;
    end if;
  end process p_muestreo;

  bit_o <= muestra_res;

end architecture rtl;
