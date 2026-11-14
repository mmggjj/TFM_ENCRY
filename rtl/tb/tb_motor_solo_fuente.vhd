-- Banco de motor_top con G_SOLO_FUENTE (la variante de la Basys 2,
-- docs/basys2.md): mismo mapa I2C, sin criptografia ni captura por trozos.
-- Comprueba que DIAG.solo_fuente lo anuncia, que toda orden criptografica
-- y capturar se rechazan sin dejar el motor ocupado, que borrar_todo acaba,
-- y que el flujo continuo saca los bits crudos igual que en el motor entero.

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

library unisim;
use unisim.sim_cfg.all;

entity tb_motor_solo_fuente is
end entity tb_motor_solo_fuente;

architecture sim of tb_motor_solo_fuente is

  constant C_T     : time := 10 ns;
  constant C_T_BIT : time := 1 us;
  constant C_DIR   : std_logic_vector(6 downto 0) := "0110000";

  signal clk, rst_n : std_logic := '0';
  signal scl, sda   : std_logic;
  signal m_sda_oe   : std_logic := '0';
  signal s_sda_oe   : std_logic;
  signal scl_m      : std_logic := '1';
  signal modo_test  : std_logic := '1';
  signal led_alarma : std_logic;
  signal fin        : boolean := false;

  signal ref_bits   : std_logic_vector(0 to 8191) := (others => '0');
  signal ref_n      : natural := 0;

begin

  clk <= '0' when fin else not clk after C_T / 2;
  scl <= scl_m;
  sda <= '0' when (m_sda_oe = '1' or s_sda_oe = '1') else '1';

  -- G_KD_MIN = 4 por el anillo lento del banco, como en tb_motor_top.
  dut : entity work.motor_top
    generic map (G_DIR_I2C => C_DIR, G_KD_MIN => 4, G_FLUJO_BYTES => 64,
                 G_CAPTURA_BYTES => 0, G_SOLO_FUENTE => true)
    port map (clk => clk, rst_n => rst_n, scl_in => scl, sda_in => sda,
              sda_oe => s_sda_oe, modo_test => modo_test,
              led_alarma => led_alarma);

  propiedades : block
    alias ocupado       is << signal .tb_motor_solo_fuente.dut.ocupado : std_logic >>;
    alias recogiendo    is << signal .tb_motor_solo_fuente.dut.recogiendo : std_logic >>;
    alias drbg_gen      is << signal .tb_motor_solo_fuente.dut.drbg_gen : std_logic >>;
    alias cmac_inicia   is << signal .tb_motor_solo_fuente.dut.cmac_inicia : std_logic >>;
    alias cap_arranca   is << signal .tb_motor_solo_fuente.dut.cap_arranca : std_logic >>;
    alias flujo_arranca is << signal .tb_motor_solo_fuente.dut.flujo_arranca : std_logic >>;
    alias flujo_activo  is << signal .tb_motor_solo_fuente.dut.flujo_activo : std_logic >>;
    alias bit_s         is << signal .tb_motor_solo_fuente.dut.bit_s : std_logic >>;
    alias stb_s         is << signal .tb_motor_solo_fuente.dut.stb_s : std_logic >>;
  begin
    default clock is rising_edge(clk);
    p_sin_semilla : assert never (recogiendo = '1')
      report "recogida de semilla sin criptografia";
    p_sin_gen     : assert never (drbg_gen = '1' or cmac_inicia = '1')
      report "orden criptografica lanzada sin criptografia";
    p_sin_cap     : assert never (cap_arranca = '1')
      report "captura lanzada sin buffer";
    p_vivo        : assert always (ocupado = '1' -> eventually! (ocupado = '0'))
      report "el motor se queda ocupado";
    c_flujo       : cover {flujo_arranca = '1'};
    c_ocupado     : cover {ocupado = '1'};

    p_ref : process (clk)
    begin
      if rising_edge(clk) then
        if flujo_arranca = '1' then
          ref_n <= 0;
        elsif flujo_activo = '1' and stb_s = '1' and ref_n < ref_bits'length then
          ref_bits(ref_n) <= bit_s;
          ref_n <= ref_n + 1;
        end if;
      end if;
    end process p_ref;
  end block propiedades;

  principal : process
    variable fallos : natural := 0;

    procedure comprobar(cond : boolean; msg : string) is
    begin
      if cond then
        report "  [ok ] " & msg;
      else
        report "  [FALLO] " & msg severity error;
        fallos := fallos + 1;
      end if;
    end procedure;

    procedure arranque is
    begin
      m_sda_oe <= '0'; scl_m <= '1'; wait for C_T_BIT / 2;
      m_sda_oe <= '1';               wait for C_T_BIT / 2;
      scl_m    <= '0';               wait for C_T_BIT / 2;
    end procedure;

    procedure parada is
    begin
      m_sda_oe <= '1'; scl_m <= '0'; wait for C_T_BIT / 2;
      scl_m    <= '1';               wait for C_T_BIT / 2;
      m_sda_oe <= '0';               wait for C_T_BIT;
    end procedure;

    procedure enviar(dato : in std_logic_vector(7 downto 0); ack : out boolean) is
    begin
      for i in 7 downto 0 loop
        m_sda_oe <= not dato(i); wait for C_T_BIT / 4;
        scl_m <= '1'; wait for C_T_BIT / 2;
        scl_m <= '0'; wait for C_T_BIT / 4;
      end loop;
      m_sda_oe <= '0'; wait for C_T_BIT / 4;
      scl_m <= '1'; wait for C_T_BIT / 4;
      ack := (sda = '0');
      wait for C_T_BIT / 4;
      scl_m <= '0'; wait for C_T_BIT / 4;
    end procedure;

    procedure recibir(seguir : in boolean; dato : out std_logic_vector(7 downto 0)) is
      variable v : std_logic_vector(7 downto 0);
    begin
      m_sda_oe <= '0';
      for i in 7 downto 0 loop
        wait for C_T_BIT / 4;
        scl_m <= '1'; wait for C_T_BIT / 4;
        v(i) := sda;
        wait for C_T_BIT / 4;
        scl_m <= '0'; wait for C_T_BIT / 4;
      end loop;
      m_sda_oe <= '1' when seguir else '0';
      wait for C_T_BIT / 4;
      scl_m <= '1'; wait for C_T_BIT / 2;
      scl_m <= '0'; wait for C_T_BIT / 4;
      m_sda_oe <= '0';
      dato := v;
    end procedure;

    procedure escribir_reg(dir : in std_logic_vector(7 downto 0);
                           dato : in std_logic_vector(7 downto 0)) is
      variable ack : boolean;
    begin
      arranque;
      enviar(C_DIR & '0', ack);
      assert ack report "sin ACK a la direccion" severity failure;
      enviar(dir, ack);
      enviar(dato, ack);
      parada;
    end procedure;

    procedure leer_bloque(dir : in std_logic_vector(7 downto 0);
                          n : in positive;
                          v : out std_logic_vector) is
      variable ack : boolean;
      variable b : std_logic_vector(7 downto 0);
    begin
      arranque;
      enviar(C_DIR & '0', ack);
      enviar(dir, ack);
      arranque;
      enviar(C_DIR & '1', ack);
      for i in 0 to n - 1 loop
        recibir(i < n - 1, b);
        v(v'high - 8 * i downto v'high - 8 * i - 7) := b;
      end loop;
      parada;
    end procedure;

    procedure leer_reg(dir : in std_logic_vector(7 downto 0);
                       dato : out std_logic_vector(7 downto 0)) is
      variable v : std_logic_vector(7 downto 0);
    begin
      leer_bloque(dir, 1, v);
      dato := v;
    end procedure;

    procedure esperar_libre(status : out std_logic_vector(7 downto 0)) is
      variable s : std_logic_vector(7 downto 0);
      variable n : natural := 0;
    begin
      loop
        leer_reg(x"02", s);
        exit when s(1) = '0';
        n := n + 1;
        assert n < 2000 report "el motor no se libera" severity failure;
      end loop;
      status := s;
    end procedure;

    procedure esperar_arranque is
      variable d : std_logic_vector(7 downto 0);
      variable n : natural := 0;
    begin
      loop
        leer_reg(x"0E", d);
        exit when d(0) = '1';
        n := n + 1;
        assert n < 2000 report "el test de arranque no pasa" severity failure;
      end loop;
    end procedure;

    procedure orden_rechazada(ctl : in std_logic_vector(7 downto 0); msg : in string) is
      variable s, d : std_logic_vector(7 downto 0);
    begin
      escribir_reg(x"03", ctl);
      wait for 5 us;
      leer_reg(x"02", s);
      leer_reg(x"0E", d);
      comprobar(s(1) = '0' and d(1) = '1', msg);
    end procedure;

    variable b, status : std_logic_vector(7 downto 0);
    variable bloque : std_logic_vector(255 downto 0);
    variable v16 : std_logic_vector(127 downto 0);
    variable n_flujo, total, distintos : natural;
    variable iguales, resto_cero : boolean;

    procedure leer_flujo is
      variable byte_ref : std_logic_vector(7 downto 0);
    begin
      leer_bloque(x"60", 32, bloque);
      n_flujo := to_integer(unsigned(bloque(255 downto 248)));
      for i in 1 to 31 loop
        b := bloque(255 - 8 * i downto 248 - 8 * i);
        if i <= n_flujo then
          byte_ref := ref_bits(8 * total to 8 * total + 7);
          if b /= byte_ref then
            iguales := false;
          end if;
          if b /= x"00" and b /= x"FF" then
            distintos := distintos + 1;
          end if;
          total := total + 1;
        elsif b /= x"00" then
          resto_cero := false;
        end if;
      end loop;
    end procedure;
  begin
    -- Anillo diez veces mas lento que el fisico, como en tb_motor_top.
    cfg.configurar(1.5, 0.04);
    rst_n <= '0';
    wait for 200 ns;
    rst_n <= '1';
    wait for 2 us;

    report "1) Identificacion";
    leer_reg(x"00", b);
    comprobar(b = x"A5", "ID = 0xA5");
    leer_reg(x"01", b);
    comprobar(b = x"04", "VERSION = 0x04, la misma que el motor entero");
    leer_reg(x"0E", b);
    comprobar(b = "00001000", "DIAG.solo_fuente = 1 y el resto a cero");

    report "2) Fuente y tests de salud";
    escribir_reg(x"04", x"04");
    esperar_arranque;
    leer_reg(x"02", status);
    comprobar(status(3 downto 2) = "00", "test de arranque pasado sin alarmas");
    leer_reg(x"08", b);
    comprobar(b /= x"00", "el APT ha visto muestras (APT_MAX_L = " &
              integer'image(to_integer(unsigned(b))) & ")");

    report "3) Ordenes sin criptografia ni buffer";
    orden_rechazada(x"01", "sembrar se rechaza");
    orden_rechazada(x"20", "resembrar se rechaza");
    orden_rechazada(x"02", "generar se rechaza");
    orden_rechazada(x"40", "aleatorio se rechaza");
    orden_rechazada(x"04", "autenticar se rechaza");
    orden_rechazada(x"10", "capturar se rechaza (sin buffer)");
    leer_reg(x"02", status);
    comprobar(status(0) = '0' and status(4) = '0' and status(6) = '0',
              "ni sembrado, ni clave, ni etiqueta");
    leer_bloque(x"10", 16, v16);
    comprobar(v16 = (127 downto 0 => '0'), "CLAVE se lee como ceros en modo test");
    leer_bloque(x"40", 32, bloque);
    comprobar(bloque = (255 downto 0 => '0'), "ALEATORIO se lee como ceros");
    escribir_reg(x"03", x"80");                 -- borrar_todo
    esperar_libre(status);
    leer_reg(x"0E", b);
    comprobar(b(1) = '0', "borrar_todo se acepta y acaba");

    report "4) Captura continua";
    escribir_reg(x"04", x"07");                 -- K_D = 128, como tb_motor_top
    escribir_reg(x"0F", x"01");
    leer_reg(x"0F", b);
    leer_reg(x"0E", status);
    comprobar(b = x"01" and status(1) = '0', "flujo activo");
    total := 0; iguales := true; resto_cero := true; distintos := 0;
    while total < 200 loop
      leer_flujo;
    end loop;
    comprobar(iguales, integer'image(total) &
              " bytes consecutivos iguales a los bits crudos, sin huecos");
    comprobar(distintos > 150, "y con contenido: " & integer'image(distintos) &
              " no son 0x00 ni 0xFF");
    comprobar(resto_cero, "sin credito se leen ceros");
    leer_reg(x"0F", b);
    comprobar(b = x"01", "sin desbordar");
    escribir_reg(x"0F", x"00");
    leer_reg(x"0F", b);
    comprobar(b = x"00", "escribir 0 lo para");

    if fallos = 0 then
      report "tb_motor_solo_fuente: 0 fallos" severity note;
    else
      report "tb_motor_solo_fuente: " & integer'image(fallos) & " fallos" severity failure;
    end if;
    fin <= true;
    std.env.stop;
    wait;
  end process principal;

end architecture sim;
