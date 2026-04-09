#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <input-video> [output-dir]" >&2
  exit 1
fi

INPUT="$1"
OUT_DIR="${2:-dash-content/video}"
mkdir -p "$OUT_DIR"

ffmpeg -y -i "$INPUT" \
  -map 0:v:0 -map 0:v:0 -map 0:v:0 -map 0:a:0 \
  -b:v:0 800k -s:v:0 640x360 \
  -b:v:1 1800k -s:v:1 1280x720 \
  -b:v:2 3500k -s:v:2 1920x1080 \
  -b:a:0 128k \
  -use_timeline 1 -use_template 1 \
  -adaptation_sets "id=0,streams=v id=1,streams=a" \
  -f dash "$OUT_DIR/stream.mpd"

echo "DASH assets written to $OUT_DIR"
