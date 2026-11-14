#!/usr/bin/env bash
# Comprueba que motor_top no cambia de logica respecto a un commit: elabora
# las dos versiones con Yosys + GHDL hasta una AIG plana (sin mapear a
# celdas) y las compara byte a byte, para cada variante de genericos.
# Identicas = misma logica, mismos biestables, mismas conexiones; los kGE o
# LUT de abc pueden moverse algo aunque lo sean (dependen de los nombres).
# Si los bytes difieren (puertas numeradas en otro orden), ABC cec compara
# las dos redes con los biestables emparejados por orden: equivalentes ahi
# es la misma funcion de salida y de siguiente estado. Si cec no lo prueba
# no demuestra un fallo: toca mirar el cambio.
#   bash synth/equivalencia.sh [ref]     (ref por defecto HEAD; desde la raiz)
# Log integro en results/equivalencia_motor_top.log.
set -uo pipefail
REF=${1:-HEAD}
OSS=${OSS:-$HOME/eda/oss-cad-suite}
export PATH=$OSS/bin:$PATH
RAIZ=$(pwd)
W=$(mktemp -d)
trap 'git -C "$RAIZ" worktree remove --force "$W/ref" >/dev/null 2>&1; rm -rf "$W"' EXIT
git worktree add --detach "$W/ref" "$REF" >/dev/null 2>&1 || { echo "no se puede sacar $REF"; exit 2; }
F="rtl/aes/aes_pkg.vhd rtl/aes/aes_enc.vhd rtl/aes/aes_enc_32.vhd rtl/aes/aes_cmac.vhd
   rtl/drbg/ctr_drbg.vhd rtl/synth/ring_osc_stub.vhd rtl/trng/reset_sync.vhd
   rtl/trng/ero_core.vhd rtl/trng/bit_cdc.vhd rtl/trng/health_tests.vhd
   rtl/trng/trng_capture.vhd rtl/trng/flujo_crudo.vhd rtl/io/i2c_slave.vhd
   rtl/top/motor_top.vhd"
LOG=$RAIZ/results/equivalencia_motor_top.log
VARIANTES=("base:" "flujo256:-gG_FLUJO_BYTES=256" "aes11:-gG_AES_COMPACTO=false"
           "pet4:-gG_PET_BITS=4")

aig() {  # raiz salida genericos...
  local d=$1 o=$2; shift 2
  local fs=""; for f in $F; do fs="$fs $d/$f"; done
  yosys -m ghdl -l "$o.log" -p "ghdl --std=08 $* $fs -e motor_top
hierarchy -top motor_top; proc; flatten; memory -nomap; memory_map; opt
async2sync; techmap; opt -fast; setundef -zero; dffunmap; aigmap
delete t:\$scopeinfo; opt_clean; stat; write_aiger -zinit $o.aig" > /dev/null 2>&1
}

{
  echo "equivalencia de motor_top: arbol de trabajo frente a $REF ($(git rev-parse --short "$REF"))"
  echo "yosys: $(yosys -V)"
  fallos=0
  for v in "${VARIANTES[@]}"; do
    n=${v%%:*}; g=${v#*:}
    aig "$W/ref" "$W/ref_$n" $g; r1=$?
    aig "$RAIZ" "$W/act_$n" $g; r2=$?
    if [ $r1 -ne 0 ] || [ $r2 -ne 0 ]; then
      echo "$n: Yosys fallo (ref $r1, actual $r2)"; fallos=$((fallos + 1)); continue
    fi
    cab=$(head -1 "$W/act_$n.aig")
    if cmp -s "$W/ref_$n.aig" "$W/act_$n.aig"; then
      echo "$n [$g]: identicas ($cab; sha256 $(sha256sum < "$W/act_$n.aig" | cut -c1-16))"
    else
      cec=$(yosys-abc -c "cec $W/ref_$n.aig $W/act_$n.aig" 2>&1 | tail -1)
      if echo "$cec" | grep -q "Networks are equivalent"; then
        echo "$n [$g]: equivalentes por ABC cec, bytes distintos ($cab; $cec)"
      else
        echo "$n [$g]: DIFIEREN (ref $(head -1 "$W/ref_$n.aig"); actual $cab; cec: $cec)"
        fallos=$((fallos + 1))
      fi
    fi
  done
  echo "variantes distintas o con fallo: $fallos"
  [ $fallos -eq 0 ]
} | tee "$LOG"
exit "${PIPESTATUS[0]}"
