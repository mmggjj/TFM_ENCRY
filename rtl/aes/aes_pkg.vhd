-- Funciones de AES-128 (FIPS 197). Solo cifrado.
--
-- El motor usa AES para las tres cosas que hace: acondicionar la entropia
-- (Block_Cipher_df), generar claves (CTR_DRBG) y autenticar (CMAC). Por
-- eso no hay SHA-256 y por eso no hace falta descifrar. Razonamiento en
-- docs/arquitectura.md seccion 9.
--
-- Convenio de orden. El estado son 128 bits con el byte 0 a la IZQUIERDA,
-- igual que se escribe en hexadecimal en el estandar: el byte i ocupa
-- v(127-8i downto 120-8i). En la matriz de FIPS 197 ese byte i es la fila
-- i mod 4 y la columna i / 4.
--
-- Sin primitivas de fabricante: sintetizable tanto en FPGA como sobre
-- celdas estandar.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

package aes_pkg is

  subtype t_byte    is std_logic_vector(7 downto 0);
  subtype t_word    is std_logic_vector(31 downto 0);
  subtype t_bloque  is std_logic_vector(127 downto 0);

  function sbox(b : t_byte) return t_byte;
  function sub_bytes(v : t_bloque) return t_bloque;
  function shift_rows(v : t_bloque) return t_bloque;
  function mix_columns(v : t_bloque) return t_bloque;
  function expandir_clave(k : t_bloque; rcon : t_byte) return t_bloque;
  function rcon_de(ronda : integer) return t_byte;

end package aes_pkg;


package body aes_pkg is

  type t_tabla is array (0 to 255) of t_byte;

  constant C_SBOX : t_tabla := (
    x"63", x"7c", x"77", x"7b", x"f2", x"6b", x"6f", x"c5",
    x"30", x"01", x"67", x"2b", x"fe", x"d7", x"ab", x"76",
    x"ca", x"82", x"c9", x"7d", x"fa", x"59", x"47", x"f0",
    x"ad", x"d4", x"a2", x"af", x"9c", x"a4", x"72", x"c0",
    x"b7", x"fd", x"93", x"26", x"36", x"3f", x"f7", x"cc",
    x"34", x"a5", x"e5", x"f1", x"71", x"d8", x"31", x"15",
    x"04", x"c7", x"23", x"c3", x"18", x"96", x"05", x"9a",
    x"07", x"12", x"80", x"e2", x"eb", x"27", x"b2", x"75",
    x"09", x"83", x"2c", x"1a", x"1b", x"6e", x"5a", x"a0",
    x"52", x"3b", x"d6", x"b3", x"29", x"e3", x"2f", x"84",
    x"53", x"d1", x"00", x"ed", x"20", x"fc", x"b1", x"5b",
    x"6a", x"cb", x"be", x"39", x"4a", x"4c", x"58", x"cf",
    x"d0", x"ef", x"aa", x"fb", x"43", x"4d", x"33", x"85",
    x"45", x"f9", x"02", x"7f", x"50", x"3c", x"9f", x"a8",
    x"51", x"a3", x"40", x"8f", x"92", x"9d", x"38", x"f5",
    x"bc", x"b6", x"da", x"21", x"10", x"ff", x"f3", x"d2",
    x"cd", x"0c", x"13", x"ec", x"5f", x"97", x"44", x"17",
    x"c4", x"a7", x"7e", x"3d", x"64", x"5d", x"19", x"73",
    x"60", x"81", x"4f", x"dc", x"22", x"2a", x"90", x"88",
    x"46", x"ee", x"b8", x"14", x"de", x"5e", x"0b", x"db",
    x"e0", x"32", x"3a", x"0a", x"49", x"06", x"24", x"5c",
    x"c2", x"d3", x"ac", x"62", x"91", x"95", x"e4", x"79",
    x"e7", x"c8", x"37", x"6d", x"8d", x"d5", x"4e", x"a9",
    x"6c", x"56", x"f4", x"ea", x"65", x"7a", x"ae", x"08",
    x"ba", x"78", x"25", x"2e", x"1c", x"a6", x"b4", x"c6",
    x"e8", x"dd", x"74", x"1f", x"4b", x"bd", x"8b", x"8a",
    x"70", x"3e", x"b5", x"66", x"48", x"03", x"f6", x"0e",
    x"61", x"35", x"57", x"b9", x"86", x"c1", x"1d", x"9e",
    x"e1", x"f8", x"98", x"11", x"69", x"d9", x"8e", x"94",
    x"9b", x"1e", x"87", x"e9", x"ce", x"55", x"28", x"df",
    x"8c", x"a1", x"89", x"0d", x"bf", x"e6", x"42", x"68",
    x"41", x"99", x"2d", x"0f", x"b0", x"54", x"bb", x"16");

  -- Rcon de las diez rondas: 2^(i-1) en GF(2^8).
  type t_rcon is array (1 to 10) of t_byte;
  constant C_RCON : t_rcon := (
    x"01", x"02", x"04", x"08", x"10",
    x"20", x"40", x"80", x"1b", x"36");

  function sbox(b : t_byte) return t_byte is
  begin
    return C_SBOX(to_integer(unsigned(b)));
  end function;

  function rcon_de(ronda : integer) return t_byte is
  begin
    if ronda >= 1 and ronda <= 10 then
      return C_RCON(ronda);
    end if;
    return x"00";
  end function;

  -- Byte i contando desde la izquierda.
  function get_byte(v : t_bloque; i : integer) return t_byte is
  begin
    return v(127 - 8 * i downto 120 - 8 * i);
  end function;

  function sub_bytes(v : t_bloque) return t_bloque is
    variable r : t_bloque;
  begin
    for i in 0 to 15 loop
      r(127 - 8 * i downto 120 - 8 * i) := sbox(get_byte(v, i));
    end loop;
    return r;
  end function;

  -- La fila r se desplaza r posiciones a la izquierda. Con el byte i en la
  -- fila i mod 4 y la columna i / 4, el byte (r + 4c) toma el valor del
  -- byte (r + 4*((c + r) mod 4)).
  function shift_rows(v : t_bloque) return t_bloque is
    variable r : t_bloque;
    variable destino, origen : integer;
  begin
    for fila in 0 to 3 loop
      for col in 0 to 3 loop
        destino := fila + 4 * col;
        origen  := fila + 4 * ((col + fila) mod 4);
        r(127 - 8 * destino downto 120 - 8 * destino) := get_byte(v, origen);
      end loop;
    end loop;
    return r;
  end function;

  -- Multiplicacion por x en GF(2^8) con el polinomio 0x11b.
  function xtime(b : t_byte) return t_byte is
  begin
    if b(7) = '1' then
      return std_logic_vector(shift_left(unsigned(b), 1)) xor x"1b";
    end if;
    return std_logic_vector(shift_left(unsigned(b), 1));
  end function;

  -- Cada columna se multiplica por la matriz circulante [2 3 1 1].
  -- La columna c ocupa los bytes 4c+0 .. 4c+3 (filas 0 a 3).
  function mix_columns(v : t_bloque) return t_bloque is
    variable r  : t_bloque;
    variable s0, s1, s2, s3 : t_byte;
    variable d0, d1, d2, d3 : t_byte;
    variable i0, i1, i2, i3 : integer;
  begin
    for col in 0 to 3 loop
      i0 := 4 * col; i1 := i0 + 1; i2 := i0 + 2; i3 := i0 + 3;
      s0 := get_byte(v, i0); s1 := get_byte(v, i1);
      s2 := get_byte(v, i2); s3 := get_byte(v, i3);

      d0 := xtime(s0) xor (xtime(s1) xor s1) xor s2 xor s3;
      d1 := s0 xor xtime(s1) xor (xtime(s2) xor s2) xor s3;
      d2 := s0 xor s1 xor xtime(s2) xor (xtime(s3) xor s3);
      d3 := (xtime(s0) xor s0) xor s1 xor s2 xor xtime(s3);

      r(127 - 8 * i0 downto 120 - 8 * i0) := d0;
      r(127 - 8 * i1 downto 120 - 8 * i1) := d1;
      r(127 - 8 * i2 downto 120 - 8 * i2) := d2;
      r(127 - 8 * i3 downto 120 - 8 * i3) := d3;
    end loop;
    return r;
  end function;

  -- Expansion de clave al vuelo: de la clave de la ronda i sale la de la
  -- ronda i+1. Solo hace falta hacia delante porque no se descifra, lo
  -- que ahorra guardar las once claves de ronda.
  function expandir_clave(k : t_bloque; rcon : t_byte) return t_bloque is
    variable w0, w1, w2, w3, temp : t_word;
  begin
    w0 := k(127 downto 96);
    w1 := k(95 downto 64);
    w2 := k(63 downto 32);
    w3 := k(31 downto 0);

    -- RotWord seguido de SubWord, y Rcon sobre el byte mas significativo.
    temp := sbox(w3(23 downto 16)) & sbox(w3(15 downto 8)) &
            sbox(w3(7 downto 0))   & sbox(w3(31 downto 24));
    temp(31 downto 24) := temp(31 downto 24) xor rcon;

    w0 := w0 xor temp;
    w1 := w1 xor w0;
    w2 := w2 xor w1;
    w3 := w3 xor w2;
    return w0 & w1 & w2 & w3;
  end function;

end package body aes_pkg;
