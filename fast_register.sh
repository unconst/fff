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

echo "Coldkey: $1";
echo "Hotkey: $2";
echo "NProcs: $3";

python3 check.py $1 $2 & pids+=( "$!" )
for i in $(seq $3); do
    python3 ~/.bittensor/bittensor/bin/btcli register --no_prompt --wallet.name $1 --wallet.hotkey $2 & pids+=( "$!" )
done

wait # sleep until all background processes have exited, or a trap fires