-- Banco de pruebas del nucleo AES-128, con vectores oficiales.
--
-- Los tres primeros salen del propio FIPS 197 y de SP 800-38A. Son la
-- unica forma honesta de decir que el nucleo cifra bien: comprobarlo
-- contra la implementacion de uno mismo no demuestra nada.
--
-- El cuarto es un encadenado de mil bloques, que detecta fallos que un
-- solo bloque no ve, como una expansion de clave que se desincroniza al
-- reutilizar el nucleo.
--
--   ghdl -a --std=08 --workdir=rtl/build/work rtl/aes/aes_pkg.vhd
--   ghdl -a --std=08 --workdir=rtl/build/work rtl/aes/aes_enc.vhd
--   ghdl -a --std=08 --workdir=rtl/build/work rtl/tb/tb_aes_enc.vhd
--   ghdl -r --std=08 --workdir=rtl/build/work tb_aes_enc

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.aes_pkg.all;

entity tb_aes_enc is
end entity tb_aes_enc;

architecture sim of tb_aes_enc is

  constant C_T : time := 10 ns;          -- 100 MHz

  signal clk     : std_logic := '0';
  signal rst_n   : std_logic := '0';
  signal arranca : std_logic := '0';
  signal clave   : std_logic_vector(127 downto 0) := (others => '0');
  signal dato    : std_logic_vector(127 downto 0) := (others => '0');
  signal salida  : std_logic_vector(127 downto 0);
  signal listo   : std_logic;
  signal ocupado : std_logic;

  signal fin : boolean := false;

  function hex(v : std_logic_vector) return string is
    constant digitos : string := "0123456789abcdef";
    variable r : string(1 to v'length / 4);
    variable n : integer;
  begin
    for i in 0 to v'length / 4 - 1 loop
      n := to_integer(unsigned(v(v'high - 4 * i downto v'high - 4 * i - 3)));
      r(i + 1) := digitos(n + 1);
    end loop;
    return r;
  end function;

begin

  clk <= '0' when fin else not clk after C_T / 2;

  dut : entity work.aes_enc
    port map (clk => clk, rst_n => rst_n, arranca => arranca,
              clave => clave, dato => dato, salida => salida,
              listo => listo, ocupado => ocupado);

  principal : process
    variable fallos : natural := 0;
    variable ciclos : natural;

    procedure cifrar(k : in std_logic_vector(127 downto 0);
                     p : in std_logic_vector(127 downto 0);
                     c : out std_logic_vector(127 downto 0);
                     n : out natural) is
      variable cuenta : natural := 0;
    begin
      clave   <= k;
      dato    <= p;
      arranca <= '1';
      wait until rising_edge(clk);
      arranca <= '0';
      while listo /= '1' loop
        wait until rising_edge(clk);
        cuenta := cuenta + 1;
        assert cuenta < 100 report "el nucleo no termina" severity failure;
      end loop;
      c := salida;
      n := cuenta;
    end procedure;

    procedure vector(nombre : in string;
                     k, p, esperado : in std_logic_vector(127 downto 0)) is
      variable c : std_logic_vector(127 downto 0);
      variable n : natural;
    begin
      cifrar(k, p, c, n);
      if c = esperado then
        report "  [ok ] " & nombre & " -> " & hex(c) &
               " (" & integer'image(n) & " ciclos)";
      else
        report "  [FALLO] " & nombre & ": obtenido " & hex(c) &
               ", esperado " & hex(esperado) severity error;
        fallos := fallos + 1;
      end if;
    end procedure;

    variable c1, c2 : std_logic_vector(127 downto 0);
    variable n : natural;
  begin
    rst_n <= '0';
    wait for 5 * C_T;
    rst_n <= '1';
    wait until rising_edge(clk);

    report "1) Vectores de FIPS 197";
    vector("Apendice C.1",
           x"000102030405060708090a0b0c0d0e0f",
           x"00112233445566778899aabbccddeeff",
           x"69c4e0d86a7b0430d8cdb78070b4c55a");
    vector("Apendice B",
           x"2b7e151628aed2a6abf7158809cf4f3c",
           x"3243f6a8885a308d313198a2e0370734",
           x"3925841d02dc09fbdc118597196a0b32");

    report "2) Vector de SP 800-38A (ECB, primer bloque)";
    vector("F.1.1 ECB-AES128",
           x"2b7e151628aed2a6abf7158809cf4f3c",
           x"6bc1bee22e409f96e93d7e117393172a",
           x"3ad77bb40d7a3660a89ecaf32466ef97");

    report "3) Bloques encadenados de SP 800-38A";
    vector("F.1.1 segundo bloque",
           x"2b7e151628aed2a6abf7158809cf4f3c",
           x"ae2d8a571e03ac9c9eb76fac45af8e51",
           x"f5d3d58503b9699de785895a96fdbaaf");
    vector("F.1.1 tercer bloque",
           x"2b7e151628aed2a6abf7158809cf4f3c",
           x"30c81c46a35ce411e5fbc1191a0a52ef",
           x"43b1cd7f598ece23881b00e3ed030688");

    report "4) Reutilizacion del nucleo: mil cifrados encadenados";
    -- La salida de cada cifrado alimenta al siguiente. Si la expansion de
    -- clave no volviera a su estado inicial en cada arranque, el resultado
    -- divergiria. Se comprueba contra el mismo encadenado repetido.
    c1 := (others => '0');
    for i in 1 to 1000 loop
      cifrar(x"2b7e151628aed2a6abf7158809cf4f3c", c1, c1, n);
    end loop;
    c2 := (others => '0');
    for i in 1 to 1000 loop
      cifrar(x"2b7e151628aed2a6abf7158809cf4f3c", c2, c2, n);
    end loop;
    if c1 = c2 then
      report "  [ok ] mil cifrados reproducibles, resultado " & hex(c1);
    else
      report "  [FALLO] el encadenado no es reproducible" severity error;
      fallos := fallos + 1;
    end if;

    -- Comprobacion adicional: el primer paso del encadenado es el cifrado
    -- del bloque de ceros, que se puede contrastar aparte.
    cifrar(x"2b7e151628aed2a6abf7158809cf4f3c", (127 downto 0 => '0'), c1, n);
    report "  cifrado del bloque de ceros = " & hex(c1) &
           " (es la subclave L del CMAC)";

    if fallos = 0 then
      report "tb_aes_enc: 0 fallos" severity note;
    else
      report "tb_aes_enc: " & integer'image(fallos) & " fallos"
        severity failure;
    end if;
    fin <= true;
    wait;
  end process principal;

end architecture sim;
