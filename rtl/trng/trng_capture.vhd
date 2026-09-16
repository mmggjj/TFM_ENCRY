-- Buffer de captura por trozos de los bits crudos del TRNG.
--
-- Captura un trozo contiguo a la velocidad del anillo y luego lo deja
-- disponible para volcarlo despacio. La campana de medida de jitter no
-- necesita una tira continua de megabits: le basta con muchos trozos
-- INDEPENDIENTES de N+M bits cada uno, y de hecho con trozos
-- independientes el estimador sale mejor. Comprobado en
-- analysis/jitter_estimator.py, apartado 4 del autotest: 20.000 trozos de
-- 2100 bits recuperan el jitter con un error del 0,3 %.
--
-- Eso rebaja la memoria necesaria de megabits a unos pocos kilobits, que
-- es la diferencia entre no caber y sobrar.
--
-- Cruce de dominios: escritura en el dominio del anillo, lectura en el de
-- sistema, y nunca a la vez. El control va por conmutacion de nivel
-- sincronizada en los dos sentidos, asi que no hace falta una FIFO
-- asincrona de verdad.
--
-- Nota de portabilidad a circuito integrado: la memoria se describe como
-- una matriz, que en FPGA se infiere como bloque de RAM. En un circuito
-- integrado habria que sustituirla por una SRAM compilada o por un banco
-- de registros, segun tamano.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity trng_capture is
  generic (
    -- Palabras de 8 bits. 512 palabras = 4096 bits, suficiente para
    -- N = 100 pares y distancias de hasta 4000.
    G_PALABRAS : positive := 512
  );
  port (
    -- Dominio del anillo de muestreo
    ro_clk    : in  std_logic;
    bit_dato  : in  std_logic;
    bit_stb   : in  std_logic;

    -- Dominio de sistema
    clk       : in  std_logic;
    rst_n     : in  std_logic;
    arranca   : in  std_logic;                      -- pulso de un ciclo
    lleno     : out std_logic;                      -- trozo disponible
    rd_dir    : in  std_logic_vector(15 downto 0);
    rd_dato   : out std_logic_vector(7 downto 0)
  );
end entity trng_capture;

architecture rtl of trng_capture is

  type t_mem is array (0 to G_PALABRAS - 1) of std_logic_vector(7 downto 0);
  signal mem : t_mem;

  -- Dominio del anillo
  signal w_desp  : std_logic_vector(7 downto 0) := (others => '0');
  signal w_nbit  : unsigned(2 downto 0) := (others => '0');
  signal w_dir   : unsigned(15 downto 0) := (others => '0');
  signal captura : std_logic := '0';
  signal tog_fin : std_logic := '0';
  signal arr_ro  : std_logic_vector(2 downto 0) := (others => '0');

  -- Dominio de sistema
  signal tog_arr : std_logic := '0';
  signal fin_sys : std_logic_vector(2 downto 0) := (others => '0');
  signal lleno_r : std_logic := '0';

  attribute ASYNC_REG : string;
  attribute ASYNC_REG of arr_ro  : signal is "TRUE";
  attribute ASYNC_REG of fin_sys : signal is "TRUE";

begin

  lleno <= lleno_r;

  -- ----------------------------------------------------------------
  -- Peticion de captura: conmutacion de nivel del dominio de sistema al
  -- del anillo. Un pulso no sobreviviria al cruce; un nivel que cambia,
  -- si.
  -- ----------------------------------------------------------------
  p_peticion : process (clk, rst_n)
  begin
    if rst_n = '0' then
      tog_arr <= '0';
      fin_sys <= (others => '0');
      lleno_r <= '0';
    elsif rising_edge(clk) then
      if arranca = '1' then
        tog_arr <= not tog_arr;
        lleno_r <= '0';
      end if;
      fin_sys <= fin_sys(1 downto 0) & tog_fin;
      if fin_sys(2) /= fin_sys(1) then
        lleno_r <= '1';
      end if;
    end if;
  end process p_peticion;

  -- ----------------------------------------------------------------
  -- Escritura, en el dominio del anillo
  -- ----------------------------------------------------------------
  p_escritura : process (ro_clk, rst_n)
  begin
    if rst_n = '0' then
      arr_ro  <= (others => '0');
      captura <= '0';
      w_desp  <= (others => '0');
      w_nbit  <= (others => '0');
      w_dir   <= (others => '0');
      tog_fin <= '0';
    elsif rising_edge(ro_clk) then
      arr_ro <= arr_ro(1 downto 0) & tog_arr;

      if arr_ro(2) /= arr_ro(1) then      -- llego una peticion
        captura <= '1';
        w_dir   <= (others => '0');
        w_nbit  <= (others => '0');
      elsif captura = '1' and bit_stb = '1' then
        w_desp <= w_desp(6 downto 0) & bit_dato;
        if w_nbit = 7 then
          w_nbit <= (others => '0');
          mem(to_integer(w_dir)) <= w_desp(6 downto 0) & bit_dato;
          if w_dir = G_PALABRAS - 1 then
            captura <= '0';
            tog_fin <= not tog_fin;
          else
            w_dir <= w_dir + 1;
          end if;
        else
          w_nbit <= w_nbit + 1;
        end if;
      end if;
    end if;
  end process p_escritura;

  -- ----------------------------------------------------------------
  -- Lectura, en el dominio de sistema. Solo es valida con lleno = '1':
  -- mientras se captura, la memoria es del otro dominio. Antes esa regla
  -- estaba escrita pero no impuesta, y una lectura durante la captura
  -- daba un acceso simultaneo entre dominios sobre la misma matriz. Ahora
  -- se devuelven ceros hasta que el trozo esta completo.
  -- ----------------------------------------------------------------
  p_lectura : process (clk, rst_n)
  begin
    if rst_n = '0' then
      rd_dato <= (others => '0');
    elsif rising_edge(clk) then
      if lleno_r = '1' then
        rd_dato <= mem(to_integer(unsigned(rd_dir)) mod G_PALABRAS);
      else
        rd_dato <= (others => '0');
      end if;
    end if;
  end process p_lectura;

end architecture rtl;
