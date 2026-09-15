-- AES-CMAC (SP 800-38B / RFC 4493) sobre el nucleo de cifrado.
--
-- Es la primitiva del reto-respuesta: el ESP32 manda un numero de un solo
-- uso y el motor devuelve su etiqueta calculada con la clave que el mismo
-- genero. Cuesta un cifrado por bloque de mensaje, mas uno para las
-- subclaves que se calcula una sola vez al cargar la clave.
--
-- Subclaves (seccion 6.1 de la norma): L = AES_K(0), y luego cada subclave
-- es la anterior desplazada un bit a la izquierda, con XOR de 0x87 si el
-- bit que se pierde por arriba era uno. Ese 0x87 es el polinomio
-- irreducible de GF(2^128).
--
-- Mensaje: se entrega bloque a bloque. El ultimo lleva su cuenta de bytes
-- validos; si esta completo se le suma K1, y si no se rellena con un uno
-- seguido de ceros y se le suma K2. Un mensaje vacio es un ultimo bloque
-- con cero bytes validos.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.aes_pkg.all;

entity aes_cmac is
  port (
    clk         : in  std_logic;
    rst_n       : in  std_logic;

    carga_clave : in  std_logic;                       -- pulso
    clave       : in  std_logic_vector(127 downto 0);
    clave_lista : out std_logic;

    inicia      : in  std_logic;                       -- pulso, mensaje nuevo
    bloque      : in  std_logic_vector(127 downto 0);
    bloque_val  : in  std_logic;                       -- pulso
    ultimo      : in  std_logic;
    n_bytes     : in  unsigned(4 downto 0);            -- validos del ultimo

    etiqueta    : out std_logic_vector(127 downto 0);
    listo       : out std_logic;                       -- pulso
    ocupado     : out std_logic
  );
end entity aes_cmac;

architecture rtl of aes_cmac is

  -- Desplaza a la izquierda y suma el polinomio si se desborda.
  function subclave(v : std_logic_vector(127 downto 0))
    return std_logic_vector is
    variable r : std_logic_vector(127 downto 0);
  begin
    r := v(126 downto 0) & '0';
    if v(127) = '1' then
      r := r xor (x"00000000000000000000000000000087");
    end if;
    return r;
  end function;

  type t_estado is (REPOSO, SUB_L, SUB_FIN, ESPERA_BLOQUE, CIFRA, FIN_MENSAJE);
  signal estado : t_estado := REPOSO;

  signal k1, k2 : std_logic_vector(127 downto 0) := (others => '0');
  signal x      : std_logic_vector(127 downto 0) := (others => '0');
  signal era_ultimo : std_logic := '0';

  -- Hacia el nucleo AES
  signal aes_arranca : std_logic := '0';
  signal aes_dato    : std_logic_vector(127 downto 0) := (others => '0');
  signal aes_salida  : std_logic_vector(127 downto 0);
  signal aes_listo   : std_logic;
  signal aes_clave   : std_logic_vector(127 downto 0) := (others => '0');

begin

  etiqueta <= x;
  ocupado  <= '0' when estado = REPOSO or estado = ESPERA_BLOQUE else '1';

  nucleo : entity work.aes_enc
    port map (clk => clk, rst_n => rst_n, arranca => aes_arranca,
              clave => aes_clave, dato => aes_dato,
              salida => aes_salida, listo => aes_listo, ocupado => open);

  p_cmac : process (clk, rst_n)
    variable relleno : std_logic_vector(127 downto 0);
    variable n       : integer range 0 to 16;
  begin
    if rst_n = '0' then
      estado      <= REPOSO;
      k1          <= (others => '0');
      k2          <= (others => '0');
      x           <= (others => '0');
      aes_arranca <= '0';
      aes_clave   <= (others => '0');
      aes_dato    <= (others => '0');
      era_ultimo  <= '0';
      listo       <= '0';
      clave_lista <= '0';

    elsif rising_edge(clk) then
      aes_arranca <= '0';
      listo       <= '0';
      clave_lista <= '0';

      case estado is

        when REPOSO =>
          if carga_clave = '1' then
            aes_clave   <= clave;
            aes_dato    <= (others => '0');   -- L = AES_K(0)
            aes_arranca <= '1';
            estado      <= SUB_L;
          end if;

        when SUB_L =>
          if aes_listo = '1' then
            k1     <= subclave(aes_salida);
            estado <= SUB_FIN;
          end if;

        when SUB_FIN =>
          k2          <= subclave(k1);
          clave_lista <= '1';
          estado      <= ESPERA_BLOQUE;

        when ESPERA_BLOQUE =>
          if carga_clave = '1' then          -- se puede recargar la clave
            aes_dato    <= (others => '0');
            aes_clave   <= clave;
            aes_arranca <= '1';
            estado      <= SUB_L;
          elsif inicia = '1' then
            x <= (others => '0');            -- CBC-MAC arranca en cero
          elsif bloque_val = '1' then
            n := to_integer(n_bytes);
            if ultimo = '1' and n < 16 then
              -- Relleno: se conservan n bytes, luego 0x80 y ceros.
              relleno := (others => '0');
              for i in 0 to 15 loop
                if i < n then
                  relleno(127 - 8 * i downto 120 - 8 * i)
                    := bloque(127 - 8 * i downto 120 - 8 * i);
                elsif i = n then
                  relleno(127 - 8 * i downto 120 - 8 * i) := x"80";
                end if;
              end loop;
              aes_dato <= x xor relleno xor k2;
            elsif ultimo = '1' then
              aes_dato <= x xor bloque xor k1;
            else
              aes_dato <= x xor bloque;
            end if;
            era_ultimo  <= ultimo;
            aes_arranca <= '1';
            estado      <= CIFRA;
          end if;

        when CIFRA =>
          if aes_listo = '1' then
            x <= aes_salida;
            if era_ultimo = '1' then
              estado <= FIN_MENSAJE;
            else
              estado <= ESPERA_BLOQUE;
            end if;
          end if;

        when FIN_MENSAJE =>
          listo  <= '1';
          estado <= ESPERA_BLOQUE;

      end case;
    end if;
  end process p_cmac;

end architecture rtl;
