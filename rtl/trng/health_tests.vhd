-- Tests de salud de la fuente de entropia (SP 800-90B, seccion 4.4).
--
-- Vigilan los bits crudos de forma continua y levantan alarma si la fuente
-- se degrada. Con estos dos la norma no exige ninguno mas (4.4: "no other
-- tests are required"). AIS 20/31 v3.0 acepta ademas el RCT como test de
-- fallo total (par. 847).
--
-- Repetition Count Test (4.4.1): cuenta cuantas muestras seguidas son
-- iguales. Corte C = 1 + ceil(-log2(alfa) / H). Detecta la fuente pegada.
--
-- Adaptive Proportion Test (4.4.2): en una ventana de W muestras cuenta
-- cuantas repiten la primera. Corte C = 1 + CRITBINOM(W, 2^-H, 1-alfa).
-- Detecta perdidas grandes de entropia (sesgo). Para fuente binaria la
-- norma fija W = 1024 (no 512, ese es el valor para fuentes no binarias).
-- Aqui se mira tambien el complemento, que la norma permite para fuentes
-- binarias: una fuente pegada al valor contrario al primero de la ventana
-- daria cuenta cero y pasaria el test de la letra pero no el del espiritu.
--
-- Valores por defecto para H = 0,98 bit/bit y alfa = 2^-20, calculados en
-- docs/estado_del_arte_trng.md seccion 5.1: RCT C = 22, APT C = 596.
-- Son genericos porque H se fija con la min-entropia MEDIDA (objetivo
-- O3), no con una suposicion.
--
-- Las alarmas son pegajosas: quedan levantadas hasta que se borran a
-- proposito, para que ninguna capa superior pueda perderselas. La logica
-- que consume bits debe bloquear la salida mientras haya alarma.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity health_tests is
  generic (
    G_RCT_C   : positive := 22;     -- corte del test de repeticion
    G_APT_W   : positive := 1024;   -- ventana del test de proporcion
    G_APT_C   : positive := 596     -- corte del test de proporcion
  );
  port (
    clk      : in  std_logic;
    rst_n    : in  std_logic;
    bit_i    : in  std_logic;
    bit_stb  : in  std_logic;       -- una muestra nueva
    borrar   : in  std_logic;       -- baja las alarmas
    alarma_rct : out std_logic;
    alarma_apt : out std_logic;
    alarma     : out std_logic;     -- cualquiera de las dos
    -- Para diagnostico por el bus: lo peor visto desde el ultimo borrado.
    rct_max  : out unsigned(15 downto 0);
    apt_max  : out unsigned(15 downto 0)
  );
end entity health_tests;

architecture rtl of health_tests is

  -- RCT
  signal rct_ant   : std_logic := '0';
  signal rct_cnt   : unsigned(15 downto 0) := (others => '0');
  signal rct_pri   : std_logic := '1';   -- aun sin muestra previa
  signal rct_alm   : std_logic := '0';
  signal rct_pico  : unsigned(15 downto 0) := (others => '0');

  -- APT
  signal apt_ref   : std_logic := '0';
  signal apt_pos   : unsigned(15 downto 0) := (others => '0');  -- 0..W-1
  signal apt_cnt   : unsigned(15 downto 0) := (others => '0');  -- coincidencias
  signal apt_alm   : std_logic := '0';
  signal apt_pico  : unsigned(15 downto 0) := (others => '0');

begin

  alarma_rct <= rct_alm;
  alarma_apt <= apt_alm;
  alarma     <= rct_alm or apt_alm;
  rct_max    <= rct_pico;
  apt_max    <= apt_pico;

  p_rct : process (clk, rst_n)
  begin
    if rst_n = '0' then
      rct_ant  <= '0';
      rct_cnt  <= (others => '0');
      rct_pri  <= '1';
      rct_alm  <= '0';
      rct_pico <= (others => '0');
    elsif rising_edge(clk) then
      if borrar = '1' then
        rct_alm  <= '0';
        rct_pico <= (others => '0');
      end if;
      if bit_stb = '1' then
        if rct_pri = '1' then
          rct_pri <= '0';
          rct_ant <= bit_i;
          rct_cnt <= to_unsigned(1, 16);
        elsif bit_i = rct_ant then
          rct_cnt <= rct_cnt + 1;
          if rct_cnt + 1 >= G_RCT_C then
            rct_alm <= '1';
          end if;
          if rct_cnt + 1 > rct_pico then
            rct_pico <= rct_cnt + 1;
          end if;
        else
          rct_ant <= bit_i;
          rct_cnt <= to_unsigned(1, 16);
        end if;
      end if;
    end if;
  end process p_rct;

  p_apt : process (clk, rst_n)
    variable coincide : unsigned(15 downto 0);
    variable peor     : unsigned(15 downto 0);
  begin
    if rst_n = '0' then
      apt_ref  <= '0';
      apt_pos  <= (others => '0');
      apt_cnt  <= (others => '0');
      apt_alm  <= '0';
      apt_pico <= (others => '0');
    elsif rising_edge(clk) then
      if borrar = '1' then
        apt_alm  <= '0';
        apt_pico <= (others => '0');
      end if;
      if bit_stb = '1' then
        if apt_pos = 0 then
          -- Primera muestra de la ventana: referencia, cuenta 1.
          apt_ref <= bit_i;
          apt_cnt <= to_unsigned(1, 16);
          apt_pos <= to_unsigned(1, 16);
        else
          if bit_i = apt_ref then
            coincide := apt_cnt + 1;
          else
            coincide := apt_cnt;
          end if;
          apt_cnt <= coincide;

          if apt_pos = G_APT_W - 1 then
            -- Ventana completa: se evalua la cuenta y su complemento.
            if coincide >= G_APT_C or
               (to_unsigned(G_APT_W, 16) - coincide) >= G_APT_C then
              apt_alm <= '1';
            end if;
            if coincide >= to_unsigned(G_APT_W, 16) - coincide then
              peor := coincide;
            else
              peor := to_unsigned(G_APT_W, 16) - coincide;
            end if;
            if peor > apt_pico then
              apt_pico <= peor;
            end if;
            apt_pos <= (others => '0');
          else
            apt_pos <= apt_pos + 1;
          end if;
        end if;
      end if;
    end if;
  end process p_apt;

end architecture rtl;
