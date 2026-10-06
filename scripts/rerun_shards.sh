#!/bin/zsh
# Re-run named shards (e.g. after one hung): scripts/rerun_shards.sh 10 11 12
cd ~/Desktop/ux-gift; source ~/Desktop/bricks/.venv/bin/activate
for i in "$@"; do
  ( caffeinate -dims python ~/.claude/skills/mobile-ui-audit/audit.py $(cat data/audit/urls-$i.txt) --links --hop \
      --json data/audit/shard-$i.json --shots data/shots > data/audit/shard-$i.log 2>&1 ) &
done; wait; echo done
