#!/bin/sh
set -eu

OUT_DIR="${1:-/tmp/host-talk-random}"
mkdir -p "$OUT_DIR"
rm -f "$OUT_DIR"/host-talk-loop-*.webp "$OUT_DIR"/host-talk-loop-*.txt

make_loop() {
  out="$1"
  shift
  list="$OUT_DIR/${out}.txt"
  : > "$list"
  last=""

  for pair in "$@"; do
    frame="${pair%:*}"
    duration="${pair#*:}"
    printf "file '/app/assets/host-mouth-%s.webp'\n" "$frame" >> "$list"
    printf "duration %s\n" "$duration" >> "$list"
    last="$frame"
  done

  printf "file '/app/assets/host-mouth-%s.webp'\n" "$last" >> "$list"
  ffmpeg -y -hide_banner -loglevel error \
    -f concat -safe 0 -i "$list" \
    -vf "format=rgba,fps=16" \
    -loop 0 -q:v 68 -compression_level 6 \
    "$OUT_DIR/${out}.webp"
}

make_loop host-talk-loop-01 small:0.10 medium:0.12 small:0.09 open:0.13 medium:0.11 closed:0.08 small:0.11 medium:0.10 open:0.12 medium:0.11 small:0.10 closed:0.09
make_loop host-talk-loop-02 closed:0.08 small:0.11 open:0.10 medium:0.13 small:0.09 medium:0.11 open:0.12 medium:0.10 closed:0.08 small:0.10 medium:0.12 small:0.09
make_loop host-talk-loop-03 medium:0.10 small:0.09 closed:0.07 small:0.10 medium:0.11 open:0.12 medium:0.10 small:0.09 open:0.11 medium:0.12 small:0.10 closed:0.08
make_loop host-talk-loop-04 small:0.09 medium:0.10 open:0.11 medium:0.09 small:0.08 closed:0.07 small:0.11 open:0.12 medium:0.10 small:0.09 medium:0.11 closed:0.08
make_loop host-talk-loop-05 closed:0.07 small:0.09 medium:0.10 small:0.08 open:0.12 medium:0.11 small:0.09 closed:0.08 medium:0.10 open:0.11 medium:0.10 small:0.09
make_loop host-talk-loop-06 small:0.08 open:0.11 medium:0.10 small:0.09 medium:0.12 open:0.10 medium:0.09 closed:0.07 small:0.10 medium:0.11 small:0.08 closed:0.08
make_loop host-talk-loop-07 medium:0.09 open:0.10 medium:0.10 small:0.08 closed:0.07 small:0.09 medium:0.11 small:0.08 open:0.12 medium:0.10 small:0.09 closed:0.07
make_loop host-talk-loop-08 small:0.10 medium:0.09 small:0.08 closed:0.07 small:0.08 open:0.11 medium:0.10 open:0.10 medium:0.11 small:0.09 closed:0.08 small:0.09
make_loop host-talk-loop-09 closed:0.07 medium:0.10 small:0.08 medium:0.09 open:0.11 medium:0.10 small:0.08 closed:0.07 small:0.09 medium:0.11 open:0.10 small:0.09
make_loop host-talk-loop-10 small:0.08 medium:0.10 open:0.09 medium:0.09 small:0.08 medium:0.10 closed:0.07 small:0.09 open:0.11 medium:0.10 small:0.08 closed:0.07
make_loop host-talk-loop-11 medium:0.09 small:0.08 open:0.10 medium:0.09 closed:0.07 small:0.08 medium:0.10 open:0.11 medium:0.09 small:0.08 closed:0.07 small:0.09
make_loop host-talk-loop-12 small:0.08 closed:0.07 small:0.09 medium:0.10 open:0.10 medium:0.09 small:0.08 medium:0.10 open:0.11 medium:0.09 small:0.08 closed:0.07

ls -lh "$OUT_DIR"/host-talk-loop-*.webp
