-- Nucleo AES-128 de cifrado con ruta de datos de 32 bits.
--
-- Mismo interfaz y mismo comportamiento visible que aes_enc (un pulso de
-- arranca, un pulso de listo, borrar que lo deja a cero), distinto
-- reparto en el tiempo: cuatro S-boxes en vez de veinte y un MixColumns
-- en vez de cuatro, trabajando una columna por ciclo. Cada ronda son
-- cinco ciclos: uno para la expansion de clave, cuyo SubWord pasa por las
-- mismas cuatro S-boxes, y cuatro para las columnas. 51 ciclos por bloque
-- frente a 11. A 100 MHz son 250 Mbit/s, cien veces lo que traga el I2C.
--
-- ShiftRows es una permutacion de bytes y conmuta con SubBytes, asi que
-- se aplica al registro de estado entero en el ciclo de clave (cableado,
-- sin logica) y despues cada columna se procesa en su sitio: la columna c
-- se lee, pasa por SubBytes, MixColumns y AddRoundKey y se escribe en c.
--
-- Es la segunda optimizacion del capitulo de integrado. Se verifica con
-- el mismo banco de vectores oficiales que aes_enc (tb_aes_enc ejecuta
-- los dos nucleos y exige que coincidan) y se mide en sintesis contra el.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.aes_pkg.all;

entity aes_enc_32 is
  port (
    clk     : in  std_logic;
    rst_n   : in  std_logic;
    arranca : in  std_logic;                       -- pulso de un ciclo
    borrar  : in  std_logic := '0';                -- pulso: aborta y deja estado y clave de ronda a cero
    clave   : in  std_logic_vector(127 downto 0);
    dato    : in  std_logic_vector(127 downto 0);
    salida  : out std_logic_vector(127 downto 0);
    listo   : out std_logic;                       -- pulso de un ciclo
    ocupado : out std_logic
  );
end entity aes_enc_32;

architecture rtl of aes_enc_32 is

  type t_fase is (REPOSO, EXPANDE, COLUMNA);

  signal fase        : t_fase := REPOSO;
  signal estado      : t_bloque := (others => '0');
  signal clave_ronda : t_bloque := (others => '0');
  signal ronda       : integer range 0 to 10 := 0;
  signal col         : integer range 0 to 3 := 0;

  -- Las cuatro S-boxes compartidas.
  signal sb_entrada  : t_word := (others => '0');
  signal sb_salida   : t_word := (others => '0');

  -- Columna c del estado (bytes 4c .. 4c+3, con el byte 0 a la izquierda).
  function palabra(v : t_bloque; c : integer range 0 to 3) return t_word is
  begin
    case c is
      when 0      => return v(127 downto 96);
      when 1      => return v(95 downto 64);
      when 2      => return v(63 downto 32);
      when others => return v(31 downto 0);
    end case;
  end function;

begin

  salida  <= estado;
  ocupado <= '0' when fase = REPOSO else '1';

  -- Lo que entra en las S-boxes: RotWord(w3) de la clave de ronda cuando
  -- se expande la clave, la columna en curso el resto del tiempo.
  sb_entrada <= clave_ronda(23 downto 0) & clave_ronda(31 downto 24) when fase = EXPANDE
                else palabra(estado, col);
  sb_salida  <= sub_word(sb_entrada);

  p_aes : process (clk, rst_n)
    variable w0, w1, w2, w3, temp : t_word;
    variable c : t_word;
  begin
    if rst_n = '0' then
      fase        <= REPOSO;
      estado      <= (others => '0');
      clave_ronda <= (others => '0');
      ronda       <= 0;
      col         <= 0;
      listo       <= '0';

    elsif rising_edge(clk) then
      listo <= '0';

      if borrar = '1' then
        -- Zeroizacion: el estado (que es la salida), la clave de ronda (de
        -- la que se recupera la clave) y lo que haya en vuelo.
        fase        <= REPOSO;
        estado      <= (others => '0');
        clave_ronda <= (others => '0');
        ronda       <= 0;
        col         <= 0;

      else
        case fase is

          when REPOSO =>
            if arranca = '1' then
              -- Ronda inicial: solo AddRoundKey con la clave original.
              estado      <= dato xor clave;
              clave_ronda <= clave;
              ronda       <= 1;
              col         <= 0;
              fase        <= EXPANDE;
            end if;

          when EXPANDE =>
            -- De la clave de la ronda anterior sale la de esta. SubWord ya
            -- ha pasado por las S-boxes compartidas.
            temp := sb_salida;
            temp(31 downto 24) := temp(31 downto 24) xor rcon_de(ronda);
            w0 := clave_ronda(127 downto 96) xor temp;
            w1 := clave_ronda(95 downto 64) xor w0;
            w2 := clave_ronda(63 downto 32) xor w1;
            w3 := clave_ronda(31 downto 0) xor w2;
            clave_ronda <= w0 & w1 & w2 & w3;
            -- ShiftRows de la ronda, por adelantado y sobre el estado entero.
            estado <= shift_rows(estado);
            col    <= 0;
            fase   <= COLUMNA;

          when COLUMNA =>
            c := sb_salida;                        -- SubBytes de la columna
            if ronda /= 10 then
              c := mix_columna(c);                 -- la ultima ronda no lleva MixColumns
            end if;
            c := c xor palabra(clave_ronda, col);  -- AddRoundKey
            case col is
              when 0      => estado(127 downto 96) <= c;
              when 1      => estado(95 downto 64)  <= c;
              when 2      => estado(63 downto 32)  <= c;
              when others => estado(31 downto 0)   <= c;
            end case;
            if col = 3 then
              if ronda = 10 then
                fase  <= REPOSO;
                ronda <= 0;
                listo <= '1';
              else
                ronda <= ronda + 1;
                fase  <= EXPANDE;
              end if;
            else
              col <= col + 1;
            end if;

        end case;
      end if;
    end if;
  end process p_aes;

end architecture rtl;
