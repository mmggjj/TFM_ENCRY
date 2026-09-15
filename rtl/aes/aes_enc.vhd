-- Nucleo AES-128 de cifrado, iterativo: una ronda por ciclo.
--
-- Once ciclos por bloque (carga mas diez rondas). A 100 MHz son 1,16
-- Gbit/s de nucleo, muy por encima de lo que puede tragar un enlace I2C,
-- asi que no tiene ningun sentido segmentarlo. Se elige la version
-- iterativa por lo contrario: porque una ronda es una funcion
-- combinacional que se coteja directamente contra el estandar.
--
-- La expansion de clave va al vuelo, generando la clave de cada ronda a
-- partir de la anterior. Ahorra guardar once claves de ronda y basta
-- porque solo se cifra.
--
-- Este mismo nucleo lo comparten el acondicionador de entropia, el
-- generador determinista y el autenticador. Ver docs/arquitectura.md
-- seccion 9.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.aes_pkg.all;

entity aes_enc is
  port (
    clk    : in  std_logic;
    rst_n  : in  std_logic;
    arranca : in  std_logic;                       -- pulso de un ciclo
    clave  : in  std_logic_vector(127 downto 0);
    dato   : in  std_logic_vector(127 downto 0);
    salida : out std_logic_vector(127 downto 0);
    listo  : out std_logic;                        -- pulso de un ciclo
    ocupado : out std_logic
  );
end entity aes_enc;

architecture rtl of aes_enc is

  signal estado_dato : std_logic_vector(127 downto 0) := (others => '0');
  signal clave_ronda : std_logic_vector(127 downto 0) := (others => '0');
  signal ronda       : integer range 0 to 11 := 0;
  signal activo      : std_logic := '0';

begin

  salida  <= estado_dato;
  ocupado <= activo;

  p_aes : process (clk, rst_n)
    variable tras_sub : std_logic_vector(127 downto 0);
    variable siguiente_clave : std_logic_vector(127 downto 0);
  begin
    if rst_n = '0' then
      estado_dato <= (others => '0');
      clave_ronda <= (others => '0');
      ronda       <= 0;
      activo      <= '0';
      listo       <= '0';

    elsif rising_edge(clk) then
      listo <= '0';

      if arranca = '1' and activo = '0' then
        -- Ronda inicial: solo AddRoundKey con la clave original.
        estado_dato <= dato xor clave;
        clave_ronda <= clave;
        ronda       <= 1;
        activo      <= '1';

      elsif activo = '1' then
        siguiente_clave := expandir_clave(clave_ronda, rcon_de(ronda));
        tras_sub := shift_rows(sub_bytes(estado_dato));

        if ronda = 10 then
          -- La ultima ronda no lleva MixColumns.
          estado_dato <= tras_sub xor siguiente_clave;
          activo      <= '0';
          listo       <= '1';
          ronda       <= 0;
        else
          estado_dato <= mix_columns(tras_sub) xor siguiente_clave;
          ronda       <= ronda + 1;
        end if;

        clave_ronda <= siguiente_clave;
      end if;
    end if;
  end process p_aes;

end architecture rtl;
