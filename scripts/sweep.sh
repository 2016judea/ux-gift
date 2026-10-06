#!/bin/zsh
# Stage 2: audit the top N of data/pool.csv in parallel shards with mobile-ui-audit (--links --hop).
# Usage: scripts/sweep.sh 150 10 [pool.csv] [outdir]   -> <outdir>/shard-*.json, data/shots/
N=${1:-150}; S=${2:-10}; POOL=${3:-data/pool.csv}; OUT=${4:-data/audit}
cd ~/Desktop/ux-gift
source ~/Desktop/bricks/.venv/bin/activate
mkdir -p $OUT data/shots
python3 -c "
import csv
rows=list(csv.DictReader(open('$POOL')))[:$N]
for i in range($S):
    open(f'$OUT/urls-{i}.txt','w').write('\n'.join(r['website'] for r in rows[i::$S]))
"
for i in $(seq 0 $((S-1))); do
  ( caffeinate -dims python ~/.claude/skills/mobile-ui-audit/audit.py $(cat $OUT/urls-$i.txt) --links --hop \
      --json $OUT/shard-$i.json --shots data/shots > $OUT/shard-$i.log 2>&1 ) &
done
wait
echo done
