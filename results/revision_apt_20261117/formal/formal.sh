#!/bin/bash
# uso: formal.sh W C  -> AIG de las dos versiones y ABC cec (y dsec si cec no basta)
export PATH=$HOME/eda/oss-cad-suite/bin:$PATH
cd /tmp/claude-1000/revision_b3/formal
W=$1; C=$2; n=w${W}_c${C}
for v in old new; do
  ent=health_tests; [ $v = old ] && ent=health_tests_old
  yosys -m ghdl -q -l $n_$v.ylog -p "ghdl --std=08 -gG_APT_W=$W -gG_APT_C=$C -gG_RCT_C=5 ../health_tests_$v.vhd -e $ent
hierarchy -top $ent; rename $ent top; proc; flatten; opt; async2sync; techmap; opt -fast; setundef -zero; dffunmap; aigmap; opt_clean; write_aiger -zinit ${n}_$v.aig" > ${n}_$v.out 2>&1 || { echo "$n: yosys fallo ($v)"; cat ${n}_$v.out; exit 1; }
done
echo "$n: cabeceras $(head -1 ${n}_old.aig) | $(head -1 ${n}_new.aig)"
echo "$n: cec  -> $(yosys-abc -c "cec ${n}_old.aig ${n}_new.aig" 2>&1 | tail -1)"
echo "$n: dsec -> $(yosys-abc -c "dsec ${n}_old.aig ${n}_new.aig" 2>&1 | tail -1)"
