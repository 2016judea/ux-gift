#!/bin/zsh
# Stage 2: audit the top N of data/pool.csv in parallel shards with mobile-ui-audit (--links --hop).
# Usage: scripts/sweep.sh 150 10   -> data/audit/shard-*.json, data/shots/
N=${1:-150}; S=${2:-10}
cd ~/Desktop/ux-gift
source ~/Desktop/bricks/.venv/bin/activate
mkdir -p data/audit data/shots
python3 -c "
import csv
rows=list(csv.DictReader(open('data/pool.csv')))[:$N]
for i in range($S):
    open(f'data/audit/urls-{i}.txt','w').write('\n'.join(r['website'] for r in rows[i::$S]))
"
for i in $(seq 0 $((S-1))); do
  ( caffeinate -dims python ~/.claude/skills/mobile-ui-audit/audit.py $(cat data/audit/urls-$i.txt) --links --hop \
      --json data/audit/shard-$i.json --shots data/shots > data/audit/shard-$i.log 2>&1 ) &
done
wait
echo done
