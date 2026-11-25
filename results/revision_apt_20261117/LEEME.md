# Revisión independiente del APT reescrito (17-11-2026)

Un agente revisor, sin las conclusiones de la sesión principal, comprobó que
`rtl/trng/health_tests.vhd` (cierre de ventana del APT con comparaciones
contra constantes) hace lo mismo que la versión anterior
(`health_tests_old.vhd`, la de HEAD 075e3c2):

- `tb_arit.vhd` → `arit_principal.log`: las dos condiciones con la semántica
  de `numeric_std`, c en [1, W]: 34 236 958 casos, 0 diferencias.
  `arit_c16.log`: con c fuera de [1, W] (inalcanzable) sí difieren.
- `tb_cosim.vhd`, `casos.txt`, `corre_cosim.sh` → `cosim.log`: las dos
  versiones en paralelo con estímulos aleatorios, borrados y resets, 30 juegos
  de genéricos, 0 diferencias en las seis salidas (dos mutantes, cazados, no
  se incluyen).
- `formal/`: Yosys + ABC `dsec`, "equivalent" con (W, C) = (7,4), (8,8), (7,9);
  con (1024,766) y (1023,767) sin veredicto (hacen falta 1024 ciclos).
