-- GENERADO por analysis/gen_drbg_vectores.py. No editar a mano.
-- Vectores del CTR_DRBG AES-128 con df obtenidos del modelo de
-- referencia ctr_drbg_ref.py (960/960 casos CAVP).
library ieee;
use ieee.std_logic_1164.all;

package drbg_vectores_pkg is
  constant C_E1 : std_logic_vector(255 downto 0)
    := x"5df3e462358a35273f15aaf24b9903a81cee98c34121f7104d5288dd438e15a5";

  constant C_N1 : std_logic_vector(127 downto 0)
    := x"06ab9fa0d19628874f1e10c76bfbc25f";

  constant C_SAL1A : std_logic_vector(255 downto 0)
    := x"918759d4314517fa80dd584bcd386d2e138b94baa8f5abb9395422571034c7a7";

  constant C_SAL1B : std_logic_vector(255 downto 0)
    := x"9bf1c08f4f03168e5633fb4ca8fc9e0614dbd6388099b53384bf196a1a38e21f";

  constant C_E2 : std_logic_vector(255 downto 0)
    := x"27c225620375890796dca9d99b14407b619ca9ab59626c0626b7c6dce1dd19c9";

  constant C_N2 : std_logic_vector(127 downto 0)
    := x"60fbf57ac643214378c44edcd1d4b458";

  constant C_SAL2 : std_logic_vector(255 downto 0)
    := x"93175c2b35ae38ee864a803fdbc5918bb2b5e62f32676e69883452f3eb401a9d";

  constant C_CNT_TRAS_DOS_GEN : natural := 3;
  constant C_CNT_TRAS_RESEED_GEN : natural := 2;
end package drbg_vectores_pkg;
