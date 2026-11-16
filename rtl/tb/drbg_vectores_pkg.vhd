-- GENERADO por analysis/gen_drbg_vectores.py. No editar a mano.
-- Vectores del CTR_DRBG AES-128 con df obtenidos del modelo de
-- referencia ctr_drbg_ref.py (960/960 casos CAVP).
library ieee;
use ieee.std_logic_1164.all;

package drbg_vectores_pkg is
  constant C_E1 : std_logic_vector(383 downto 0)
    := x"5df3e462358a35273f15aaf24b9903a81cee98c34121f7104d5288dd438e15a5a233dfd48d4327e83e3aa0e99499af30";

  constant C_N1 : std_logic_vector(127 downto 0)
    := x"06ab9fa0d19628874f1e10c76bfbc25f";

  constant C_SAL1A : std_logic_vector(255 downto 0)
    := x"9d2a0b1f6551de8d54456b728c16f18cc67695ae39a6309b0512f11dfd252dfd";

  constant C_SAL1B : std_logic_vector(255 downto 0)
    := x"78c7ff6ac0ca9e646b193a82440c1225f19315c405ed298f5b424fd74fd6d62d";

  constant C_E2 : std_logic_vector(383 downto 0)
    := x"27c225620375890796dca9d99b14407b619ca9ab59626c0626b7c6dce1dd19c92588373c818c95d64f11f58397f0fc19";

  constant C_N2 : std_logic_vector(127 downto 0)
    := x"60fbf57ac643214378c44edcd1d4b458";

  constant C_SAL2 : std_logic_vector(255 downto 0)
    := x"8f85260e0942b53dcf44d436b4ad141ecb8419638c4dcbb8f185d10168fde7a2";

  constant C_CNT_TRAS_DOS_GEN : natural := 3;
  constant C_CNT_TRAS_RESEED_GEN : natural := 2;
end package drbg_vectores_pkg;
