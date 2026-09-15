-- Banco de pruebas del CTR_DRBG contra el modelo de referencia.
--
-- Los valores esperados vienen de drbg_vectores_pkg.vhd, que genera
-- analysis/gen_drbg_vectores.py con el modelo Python validado contra el
-- CAVP. Asi el VHDL se contrasta con una implementacion independiente
-- que a su vez esta contrastada con el estandar.
--
-- Se comprueba: instanciar y generar dos veces (dos salidas distintas y
-- ambas correctas), resembrar y generar, el contador de peticiones, y que
-- instanciar de nuevo borra el estado y reproduce la primera salida.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library work;
use work.drbg_vectores_pkg.all;

entity tb_ctr_drbg is
end entity tb_ctr_drbg;

architecture sim of tb_ctr_drbg is

  constant C_T : time := 10 ns;

  signal clk, rst_n : std_logic := '0';
  signal instanciar, resembrar, generar : std_logic := '0';
  signal entropia : std_logic_vector(255 downto 0) := (others => '0');
  signal nonce    : std_logic_vector(127 downto 0) := (others => '0');
  signal salida   : std_logic_vector(255 downto 0);
  signal listo, ocupado, sembrado : std_logic;
  signal peticiones : unsigned(31 downto 0);
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

  dut : entity work.ctr_drbg
    port map (clk => clk, rst_n => rst_n,
              instanciar => instanciar, resembrar => resembrar,
              entropia => entropia, nonce => nonce,
              generar => generar, salida => salida,
              listo => listo, ocupado => ocupado, sembrado => sembrado,
              peticiones => peticiones);

  principal : process
    variable fallos : natural := 0;
    variable ciclos : natural;

    procedure orden(signal s : out std_logic; n : out natural) is
      variable c : natural := 0;
    begin
      s <= '1';
      wait until rising_edge(clk);
      s <= '0';
      loop
        wait until rising_edge(clk);
        c := c + 1;
        exit when listo = '1';
        assert c < 2000 report "el DRBG no termina" severity failure;
      end loop;
      n := c;
    end procedure;

    procedure comprobar(cond : boolean; msg : string) is
    begin
      if cond then
        report "  [ok ] " & msg;
      else
        report "  [FALLO] " & msg severity error;
        fallos := fallos + 1;
      end if;
    end procedure;

  begin
    rst_n <= '0';
    wait for 5 * C_T;
    rst_n <= '1';
    wait until rising_edge(clk);

    report "1) Instanciar con entropia y nonce";
    comprobar(sembrado = '0', "sin sembrar al arrancar");
    entropia <= C_E1;
    nonce    <= C_N1;
    orden(instanciar, ciclos);
    comprobar(sembrado = '1', "sembrado tras instanciar (" &
              integer'image(ciclos) & " ciclos)");
    comprobar(peticiones = 1, "contador de peticiones = 1");

    report "2) Generar dos veces";
    orden(generar, ciclos);
    comprobar(salida = C_SAL1A, "primera salida = referencia (" &
              integer'image(ciclos) & " ciclos)");
    orden(generar, ciclos);
    comprobar(salida = C_SAL1B, "segunda salida = referencia");
    comprobar(C_SAL1A /= C_SAL1B, "las dos salidas son distintas");
    comprobar(peticiones = C_CNT_TRAS_DOS_GEN,
              "contador = " & integer'image(C_CNT_TRAS_DOS_GEN));

    report "3) Resembrar y generar";
    entropia <= C_E2;
    nonce    <= C_N2;
    orden(resembrar, ciclos);
    comprobar(peticiones = 1, "el contador vuelve a 1 tras resembrar");
    orden(generar, ciclos);
    comprobar(salida = C_SAL2, "salida tras resembrar = referencia");
    comprobar(peticiones = C_CNT_TRAS_RESEED_GEN, "contador tras generar");

    report "4) Instanciar de nuevo borra el estado";
    entropia <= C_E1;
    nonce    <= C_N1;
    orden(instanciar, ciclos);
    orden(generar, ciclos);
    comprobar(salida = C_SAL1A, "vuelve a dar la primera salida");

    report "5) Generar sin sembrar no hace nada";
    rst_n <= '0';
    wait for 3 * C_T;
    rst_n <= '1';
    wait until rising_edge(clk);
    generar <= '1';
    wait until rising_edge(clk);
    generar <= '0';
    wait for 5 * C_T;
    comprobar(ocupado = '0' and sembrado = '0',
              "la orden se ignora sin estado valido");

    if fallos = 0 then
      report "tb_ctr_drbg: 0 fallos" severity note;
    else
      report "tb_ctr_drbg: " & integer'image(fallos) & " fallos"
        severity failure;
    end if;
    fin <= true;
    wait;
  end process principal;

end architecture sim;
