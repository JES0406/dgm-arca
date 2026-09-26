#!/usr/bin/env bash
# Serial baseline queue for the shortlisted topics (one laptop GPU, so strictly one at a time).
# Base: Qwen3-0.6B bf16, 20 problems, 1024 new tokens. Teacher proxy: Qwen3-4B NF4 4-bit,
# 12 problems, 2048 new tokens (a 4 GB GPU cannot hold 4B in bf16; small n because each 4B
# batch takes tens of minutes on a thermally throttled laptop).
set -u
B="$(cd "$(dirname "$0")/.." && pwd)"
PY="$B/../../../.venv/bin/python"
# wait for any teacher run already on the GPU
while pgrep -f "Qwen3-4B --four-bit" >/dev/null; do sleep 15; done
for topic in pvpc nutriscore per riego; do
  "$PY" "$B/common/harness.py" --problems "$B/$topic/problems_test.jsonl" \
    --verifier "$B/$topic/generator.py" --model Qwen/Qwen3-0.6B --max-new-tokens 1024 \
    --batch-size 5 --limit 20 --out "$B/$topic/baseline_qwen3-0.6b.json" 2>&1 | grep -E '"pass@1"|Error|Traceback'
  echo "done 0.6b $topic"
done
for topic in pvpc nutriscore per riego; do
  "$PY" "$B/common/harness.py" --problems "$B/$topic/problems_test.jsonl" \
    --verifier "$B/$topic/generator.py" --model Qwen/Qwen3-4B --four-bit --max-new-tokens 2048 \
    --batch-size 4 --limit 12 --out "$B/$topic/baseline_qwen3-4b-nf4.json" 2>&1 | grep -E '"pass@1"|Error|Traceback'
  echo "done 4b $topic"
done
