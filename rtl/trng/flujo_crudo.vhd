-- Captura continua de los bits crudos: una FIFO de bytes en el dominio de
-- sistema que el maestro vacia por I2C mientras se llena.
--
-- trng_capture da trozos de 4096 bits sin relacion entre si, que es lo que
-- quiere el estimador de jitter; SP 800-90B pide un millon de bits
-- CONSECUTIVOS. Aqui entran los bits ya cruzados (los mismos que ven los
-- tests de salud y la recogida de semilla), se empaquetan de ocho en ocho,
-- el primero en el bit alto, y salen en orden. Si el maestro no vacia a
-- tiempo, la FIFO no pisa nada: levanta desbordado y se para, y la tira
-- deja de valer. Razonamiento y tasas en docs/captura_continua.md.
--
-- Lectura con credito: leer_n fija cuantos bytes (hasta 31) puede sacar la
-- transaccion en curso y los devuelve en n; cada leer_dato con credito
-- saca uno. Sin credito sale 0x00 y no se saca nada, asi que un byte que
-- llega a mitad de la lectura no se pierde.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity flujo_crudo is
  generic (
    G_BYTES : positive := 256          -- potencia de dos
  );
  port (
    clk        : in  std_logic;
    rst_n      : in  std_logic;
    bit_i      : in  std_logic;
    bit_stb    : in  std_logic;
    arrancar   : in  std_logic;        -- pulso: vacia y activa
    parar      : in  std_logic;        -- vacia y desactiva
    activo     : out std_logic;
    desbordado : out std_logic;        -- se baja al arrancar
    leer_n     : in  std_logic;        -- pulso, antes de leer n
    leer_dato  : in  std_logic;        -- pulso, antes de leer dato
    n          : out std_logic_vector(7 downto 0);
    dato       : out std_logic_vector(7 downto 0)
  );
end entity flujo_crudo;

architecture rtl of flujo_crudo is

  function log2(v : positive) return natural is
    variable r : natural := 0;
  begin
    while 2 ** r < v loop
      r := r + 1;
    end loop;
    return r;
  end function;

  constant C_W : natural := log2(G_BYTES);

  type t_mem is array (0 to G_BYTES - 1) of std_logic_vector(7 downto 0);
  signal mem : t_mem;

  signal p_esc, p_lec : unsigned(C_W - 1 downto 0) := (others => '0');
  signal cuenta   : unsigned(C_W downto 0) := (others => '0');
  signal desp     : std_logic_vector(6 downto 0) := (others => '0');
  signal n_bit    : unsigned(2 downto 0) := (others => '0');
  signal credito  : unsigned(4 downto 0) := (others => '0');
  signal activo_r, desb_r : std_logic := '0';

begin

  assert 2 ** C_W = G_BYTES
    report "flujo_crudo: G_BYTES debe ser potencia de dos" severity failure;

  activo     <= activo_r;
  desbordado <= desb_r;

  p_fifo : process (clk, rst_n)
    variable mete, saca : boolean;
  begin
    if rst_n = '0' then
      p_esc <= (others => '0'); p_lec <= (others => '0');
      cuenta <= (others => '0'); desp <= (others => '0');
      n_bit <= (others => '0'); credito <= (others => '0');
      activo_r <= '0'; desb_r <= '0';
      n <= (others => '0'); dato <= (others => '0');
    elsif rising_edge(clk) then
      mete := false;
      saca := false;

      if activo_r = '1' and bit_stb = '1' then
        desp <= desp(5 downto 0) & bit_i;
        n_bit <= n_bit + 1;
        if n_bit = 7 then
          if cuenta = G_BYTES then
            desb_r   <= '1';
            activo_r <= '0';
          else
            mem(to_integer(p_esc)) <= desp & bit_i;
            p_esc <= p_esc + 1;
            mete := true;
          end if;
        end if;
      end if;

      if leer_n = '1' then
        if cuenta > 31 then
          credito <= to_unsigned(31, 5);
          n <= x"1F";
        else
          credito <= cuenta(4 downto 0);
          n <= "000" & std_logic_vector(cuenta(4 downto 0));
        end if;
      elsif leer_dato = '1' then
        if credito /= 0 then
          dato <= mem(to_integer(p_lec));
          p_lec <= p_lec + 1;
          credito <= credito - 1;
          saca := true;
        else
          dato <= (others => '0');
        end if;
      end if;

      if mete and not saca then
        cuenta <= cuenta + 1;
      elsif saca and not mete then
        cuenta <= cuenta - 1;
      end if;

      -- Mandan sobre lo anterior. Los punteros a cero bastan para vaciar:
      -- lo que queda en la memoria no se puede leer sin credito.
      if arrancar = '1' or parar = '1' then
        p_esc <= (others => '0'); p_lec <= (others => '0');
        cuenta <= (others => '0'); n_bit <= (others => '0');
        credito <= (others => '0');
        dato <= (others => '0');
      end if;
      if parar = '1' then
        activo_r <= '0';
      elsif arrancar = '1' then
        activo_r <= '1';
        desb_r   <= '0';
      end if;
    end if;
  end process p_fifo;

end architecture rtl;
