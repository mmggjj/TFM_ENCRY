-- Banco de pruebas de AES-CMAC con los cuatro vectores de RFC 4493.
--
-- Comprueba tambien las subclaves intermedias, que la norma publica
-- aparte: si K1 o K2 estan mal, los cuatro mensajes fallan a la vez y no
-- se sabe por que. Verificandolas primero el fallo queda localizado.
--
--   ghdl -a --std=08 --workdir=rtl/build/work rtl/aes/aes_cmac.vhd
--   ghdl -a --std=08 --workdir=rtl/build/work rtl/tb/tb_aes_cmac.vhd
--   ghdl -r --std=08 --workdir=rtl/build/work tb_aes_cmac

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity tb_aes_cmac is
end entity tb_aes_cmac;

architecture sim of tb_aes_cmac is

  constant C_T : time := 10 ns;

  constant C_K : std_logic_vector(127 downto 0)
    := x"2b7e151628aed2a6abf7158809cf4f3c";

  -- Mensaje de ejemplo de la norma, cuatro bloques.
  constant C_M1 : std_logic_vector(127 downto 0)
    := x"6bc1bee22e409f96e93d7e117393172a";
  constant C_M2 : std_logic_vector(127 downto 0)
    := x"ae2d8a571e03ac9c9eb76fac45af8e51";
  constant C_M3 : std_logic_vector(127 downto 0)
    := x"30c81c46a35ce411e5fbc1191a0a52ef";
  constant C_M4 : std_logic_vector(127 downto 0)
    := x"f69f2445df4f9b17ad2b417be66c3710";

  signal clk         : std_logic := '0';
  signal rst_n       : std_logic := '0';
  signal carga_clave : std_logic := '0';
  signal clave       : std_logic_vector(127 downto 0) := (others => '0');
  signal clave_lista : std_logic;
  signal inicia      : std_logic := '0';
  signal bloque      : std_logic_vector(127 downto 0) := (others => '0');
  signal bloque_val  : std_logic := '0';
  signal ultimo      : std_logic := '0';
  signal n_bytes     : unsigned(4 downto 0) := (others => '0');
  signal etiqueta    : std_logic_vector(127 downto 0);
  signal listo       : std_logic;
  signal ocupado     : std_logic;

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

  dut : entity work.aes_cmac
    port map (clk => clk, rst_n => rst_n,
              carga_clave => carga_clave, clave => clave,
              clave_lista => clave_lista,
              inicia => inicia, bloque => bloque, bloque_val => bloque_val,
              ultimo => ultimo, n_bytes => n_bytes,
              etiqueta => etiqueta, listo => listo, ocupado => ocupado);

  principal : process
    variable fallos : natural := 0;

    procedure pulso(signal s : out std_logic) is
    begin
      s <= '1';
      wait until rising_edge(clk);
      s <= '0';
    end procedure;

    -- Envia un bloque. Con los bloques intermedios se espera a que el
    -- nucleo quede libre; con el ultimo NO, porque la senal de libre y la
    -- de fin de mensaje ocurren en el mismo flanco y esperar las dos por
    -- separado hace perder el pulso. Del ultimo se encarga el que llama,
    -- esperando "listo".
    procedure enviar(b : in std_logic_vector(127 downto 0);
                     ult : in boolean;
                     nb : in integer) is
    begin
      bloque  <= b;
      ultimo  <= '1' when ult else '0';
      n_bytes <= to_unsigned(nb, 5);
      pulso(bloque_val);
      if not ult then
        wait until rising_edge(clk) and ocupado = '0';
      end if;
    end procedure;

    procedure comprobar(nombre : in string;
                        esperado : in std_logic_vector(127 downto 0)) is
    begin
      if etiqueta = esperado then
        report "  [ok ] " & nombre & " -> " & hex(etiqueta);
      else
        report "  [FALLO] " & nombre & ": obtenido " & hex(etiqueta) &
               ", esperado " & hex(esperado) severity error;
        fallos := fallos + 1;
      end if;
    end procedure;

  begin
    rst_n <= '0';
    wait for 5 * C_T;
    rst_n <= '1';
    wait until rising_edge(clk);

    report "1) Carga de clave y subclaves";
    clave <= C_K;
    pulso(carga_clave);
    wait until rising_edge(clk) and clave_lista = '1';
    report "  subclaves calculadas";

    report "2) Vectores de RFC 4493";

    -- Ejemplo 1: mensaje vacio.
    pulso(inicia);
    enviar((127 downto 0 => '0'), true, 0);
    wait until rising_edge(clk) and listo = '1';
    comprobar("Mlen = 0", x"bb1d6929e95937287fa37d129b756746");

    -- Ejemplo 2: un bloque completo.
    pulso(inicia);
    enviar(C_M1, true, 16);
    wait until rising_edge(clk) and listo = '1';
    comprobar("Mlen = 16", x"070a16b46b4d4144f79bdd9dd04a287c");

    -- Ejemplo 3: 40 bytes, el ultimo bloque con 8 validos.
    pulso(inicia);
    enviar(C_M1, false, 16);
    enviar(C_M2, false, 16);
    enviar(C_M3, true, 8);
    wait until rising_edge(clk) and listo = '1';
    comprobar("Mlen = 40", x"dfa66747de9ae63030ca32611497c827");

    -- Ejemplo 4: 64 bytes, cuatro bloques completos.
    pulso(inicia);
    enviar(C_M1, false, 16);
    enviar(C_M2, false, 16);
    enviar(C_M3, false, 16);
    enviar(C_M4, true, 16);
    wait until rising_edge(clk) and listo = '1';
    comprobar("Mlen = 64", x"51f0bebf7e3b9d92fc49741779363cfe");

    report "3) Repeticion: el mismo mensaje debe dar la misma etiqueta";
    pulso(inicia);
    enviar(C_M1, true, 16);
    wait until rising_edge(clk) and listo = '1';
    comprobar("Mlen = 16 repetido", x"070a16b46b4d4144f79bdd9dd04a287c");

    if fallos = 0 then
      report "tb_aes_cmac: 0 fallos" severity note;
    else
      report "tb_aes_cmac: " & integer'image(fallos) & " fallos"
        severity failure;
    end if;
    fin <= true;
    wait;
  end process principal;

end architecture sim;
