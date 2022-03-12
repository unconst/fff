#!/bin/bash
#      ^^^^ - NOT /bin/sh, as this code uses arrays

pids=( )

# define cleanup function
cleanup() {
  for pid in "${pids[@]}"; do
    kill -0 "$pid" && kill "$pid" # kill process only if it's still running
  done
}

# and set that function to run before we exit, or specifically when we get a SIGTERM
trap cleanup EXIT TERM

echo "Script: $1";
echo "Coldkey: $2";
echo "Hotkey: $3";
echo "NProcs: $4";

python3 check.py $2 $3 & pids+=( "$!" )
for i in $(seq $4); do
    python3 $1 register --no_prompt --wallet.name $2 --wallet.hotkey $3 & pids+=( "$!" )
done

wait # sleep until all background processes have exited, or a trap fires