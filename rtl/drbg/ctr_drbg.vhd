-- CTR_DRBG con AES-128 y funcion de derivacion (SP 800-90A Rev. 1,
-- secciones 10.2.1 y 10.3.2).
--
-- Es el fabricante de claves del motor. Recibe entropia cruda del anillo
-- (256 bits) mas un nonce (128 bits), la acondiciona con Block_Cipher_df
-- y mantiene el estado (Key, V) del que salen las claves. Todo son
-- cifrados AES encadenados con un control alrededor: no hay ninguna otra
-- primitiva. Ver docs/arquitectura.md seccion 9.
--
-- Tamanos fijos, a proposito. La norma admite entradas de cualquier
-- longitud, pero en hardware una longitud fija convierte la funcion de
-- derivacion en una secuencia cerrada de cifrados:
--   S = L(4) || N(4) || entropia(32) || nonce(16) || 0x80 || ceros
--     = 64 bytes = 4 bloques, con L = 48 y N = 32.
-- Coste: instanciar o resembrar = 14 cifrados; generar 256 bits = 4.
--
-- El modelo de referencia bit a bit es analysis/ctr_drbg_ref.py, validado
-- contra 960 vectores del CAVP; los vectores de este nucleo salen de el
-- con esta misma disposicion de entrada.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity ctr_drbg is
  port (
    clk        : in  std_logic;
    rst_n      : in  std_logic;

    instanciar : in  std_logic;                       -- pulso: Key=V=0 y siembra
    resembrar  : in  std_logic;                       -- pulso: siembra sobre el estado
    entropia   : in  std_logic_vector(255 downto 0);
    nonce      : in  std_logic_vector(127 downto 0);

    generar    : in  std_logic;                       -- pulso: 256 bits nuevos
    salida     : out std_logic_vector(255 downto 0);

    listo      : out std_logic;                       -- pulso al acabar cualquier orden
    ocupado    : out std_logic;
    sembrado   : out std_logic;                       -- hay estado valido
    peticiones : out unsigned(31 downto 0)            -- reseed_counter
  );
end entity ctr_drbg;

architecture rtl of ctr_drbg is

  constant C_K0 : std_logic_vector(127 downto 0)
    := x"000102030405060708090a0b0c0d0e0f";
  constant C_L  : std_logic_vector(31 downto 0) := x"00000030";  -- 48 bytes
  constant C_N  : std_logic_vector(31 downto 0) := x"00000020";  -- 32 bytes

  type t_fase is (REPOSO, DF_BCC, DF_X, UPDATE, GEN);
  signal fase : t_fase := REPOSO;
  signal tras_update : t_fase := REPOSO;   -- a donde volver tras UPDATE

  -- Estado del DRBG
  signal key : std_logic_vector(127 downto 0) := (others => '0');
  signal v   : std_logic_vector(127 downto 0) := (others => '0');
  signal cnt_reseed : unsigned(31 downto 0) := (others => '0');
  signal valido : std_logic := '0';

  -- Entrada capturada al recibir la orden
  signal ent_r   : std_logic_vector(255 downto 0) := (others => '0');
  signal nonce_r : std_logic_vector(127 downto 0) := (others => '0');

  -- Funcion de derivacion
  signal i_bcc, j_bcc : integer range 0 to 4 := 0;
  signal cadena  : std_logic_vector(127 downto 0) := (others => '0');
  signal t0      : std_logic_vector(127 downto 0) := (others => '0');
  signal kdf     : std_logic_vector(127 downto 0) := (others => '0');
  signal x_df    : std_logic_vector(127 downto 0) := (others => '0');
  signal paso    : integer range 0 to 3 := 0;

  -- Material de 256 bits que entra al Update (semilla o ceros)
  signal material : std_logic_vector(255 downto 0) := (others => '0');
  signal temp_hi  : std_logic_vector(127 downto 0) := (others => '0');
  signal sal_r    : std_logic_vector(255 downto 0) := (others => '0');

  -- Interfaz con el AES
  signal aes_arranca : std_logic := '0';
  signal aes_clave   : std_logic_vector(127 downto 0) := (others => '0');
  signal aes_dato    : std_logic_vector(127 downto 0) := (others => '0');
  signal aes_salida  : std_logic_vector(127 downto 0);
  signal aes_listo   : std_logic;
  signal lanzado     : std_logic := '0';   -- hay un cifrado en curso

  -- Bloque j de S (0..3), a partir de la entrada capturada.
  function bloque_s(j : integer;
                    e : std_logic_vector(255 downto 0);
                    n : std_logic_vector(127 downto 0))
    return std_logic_vector is
  begin
    case j is
      when 0 => return C_L & C_N & e(255 downto 192);
      when 1 => return e(191 downto 64);
      when 2 => return e(63 downto 0) & n(127 downto 64);
      when others => return n(63 downto 0) & x"80" & x"00000000000000";
    end case;
  end function;

  function inc(vv : std_logic_vector(127 downto 0)) return std_logic_vector is
  begin
    return std_logic_vector(unsigned(vv) + 1);
  end function;

begin

  salida     <= sal_r;
  ocupado    <= '0' when fase = REPOSO else '1';
  sembrado   <= valido;
  peticiones <= cnt_reseed;

  nucleo : entity work.aes_enc
    port map (clk => clk, rst_n => rst_n, arranca => aes_arranca,
              clave => aes_clave, dato => aes_dato,
              salida => aes_salida, listo => aes_listo, ocupado => open);

  p_drbg : process (clk, rst_n)
    variable iv : std_logic_vector(127 downto 0);
  begin
    if rst_n = '0' then
      fase <= REPOSO; tras_update <= REPOSO;
      key <= (others => '0'); v <= (others => '0');
      cnt_reseed <= (others => '0'); valido <= '0';
      ent_r <= (others => '0'); nonce_r <= (others => '0');
      i_bcc <= 0; j_bcc <= 0; paso <= 0;
      cadena <= (others => '0'); t0 <= (others => '0');
      kdf <= (others => '0'); x_df <= (others => '0');
      material <= (others => '0'); temp_hi <= (others => '0');
      sal_r <= (others => '0');
      aes_arranca <= '0'; aes_clave <= (others => '0');
      aes_dato <= (others => '0'); lanzado <= '0';
      listo <= '0';

    elsif rising_edge(clk) then
      aes_arranca <= '0';
      listo <= '0';

      case fase is

        when REPOSO =>
          if instanciar = '1' or resembrar = '1' then
            if instanciar = '1' then
              key <= (others => '0');
              v   <= (others => '0');
            end if;
            ent_r   <= entropia;
            nonce_r <= nonce;
            i_bcc <= 0; j_bcc <= 0;
            cadena <= (others => '0');
            fase <= DF_BCC;
            lanzado <= '0';
          elsif generar = '1' and valido = '1' then
            paso <= 0;
            fase <= GEN;
            lanzado <= '0';
          end if;

        -- BCC(K0, IV_i || S): cinco cifrados encadenados por cada i.
        when DF_BCC =>
          if lanzado = '0' then
            if j_bcc = 0 then
              iv := std_logic_vector(to_unsigned(i_bcc, 32)) & (95 downto 0 => '0');
              aes_dato <= cadena xor iv;
            else
              aes_dato <= cadena xor bloque_s(j_bcc - 1, ent_r, nonce_r);
            end if;
            aes_clave   <= C_K0;
            aes_arranca <= '1';
            lanzado     <= '1';
          elsif aes_listo = '1' then
            lanzado <= '0';
            if j_bcc = 4 then
              -- Fin de una BCC: temp = T0 || T1.
              if i_bcc = 0 then
                t0     <= aes_salida;
                i_bcc  <= 1;
                j_bcc  <= 0;
                cadena <= (others => '0');
              else
                kdf   <= t0;               -- K = primeros 128 bits de temp
                x_df  <= aes_salida;       -- X = siguientes 128 bits
                paso  <= 0;
                fase  <= DF_X;
              end if;
            else
              cadena <= aes_salida;
              j_bcc  <= j_bcc + 1;
            end if;
          end if;

        -- X <- E_K(X), dos veces: 256 bits de material de semilla.
        when DF_X =>
          if lanzado = '0' then
            aes_clave   <= kdf;
            aes_dato    <= x_df;
            aes_arranca <= '1';
            lanzado     <= '1';
          elsif aes_listo = '1' then
            lanzado <= '0';
            x_df    <= aes_salida;
            if paso = 0 then
              material(255 downto 128) <= aes_salida;
              paso <= 1;
            else
              material(127 downto 0) <= aes_salida;
              paso <= 0;
              tras_update <= REPOSO;
              fase <= UPDATE;
            end if;
          end if;

        -- Update(material): V+1 y V+2 cifrados con Key, XOR con material.
        when UPDATE =>
          if lanzado = '0' then
            v           <= inc(v);
            aes_clave   <= key;
            aes_dato    <= inc(v);
            aes_arranca <= '1';
            lanzado     <= '1';
          elsif aes_listo = '1' then
            lanzado <= '0';
            if paso = 0 then
              temp_hi <= aes_salida;
              paso <= 1;
            else
              key  <= temp_hi xor material(255 downto 128);
              v    <= aes_salida xor material(127 downto 0);
              paso <= 0;
              if tras_update = REPOSO then
                -- Venimos de sembrar: estado valido, contador a 1.
                valido     <= '1';
                cnt_reseed <= to_unsigned(1, 32);
                listo      <= '1';
              else
                -- Venimos de generar: contador +1.
                cnt_reseed <= cnt_reseed + 1;
                listo      <= '1';
              end if;
              fase <= REPOSO;
            end if;
          end if;

        -- Generate 256 bits: dos cifrados de V+1, V+2, luego Update(0).
        when GEN =>
          if lanzado = '0' then
            v           <= inc(v);
            aes_clave   <= key;
            aes_dato    <= inc(v);
            aes_arranca <= '1';
            lanzado     <= '1';
          elsif aes_listo = '1' then
            lanzado <= '0';
            if paso = 0 then
              sal_r(255 downto 128) <= aes_salida;
              paso <= 1;
            else
              sal_r(127 downto 0) <= aes_salida;
              paso <= 0;
              material    <= (others => '0');
              tras_update <= GEN;
              fase        <= UPDATE;
            end if;
          end if;

      end case;
    end if;
  end process p_drbg;

end architecture rtl;
