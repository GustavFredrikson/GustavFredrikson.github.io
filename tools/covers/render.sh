#!/bin/sh
# Render tools/covers/<name>.html to src/assets/work/<name>.png (light) and
# <name>-dark.png at 2x, using headless Chrome. Usage: tools/covers/render.sh cka-dojo
# `render.sh og` renders public/og.png at 1x instead. Use CHROME=chrome-headless-shell
# for it: new headless Chrome's viewport is shorter than --window-size.
set -eu
name=$1
dir=$(cd "$(dirname "$0")" && pwd)
out="$dir/../../src/assets/work"
chrome=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
if [ "$name" = og ]; then
  "$chrome" --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --window-size=1200,630 --virtual-time-budget=5000 \
    --screenshot="$dir/../../public/og.png" "file://$dir/og.html" 2>/dev/null
  ls -l "$dir/../../public/og.png"
  exit
fi
mkdir -p "$out"
for theme in light dark; do
  suffix=$([ "$theme" = dark ] && echo "-dark" || echo "")
  "$chrome" --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
    --window-size=1120,840 --virtual-time-budget=5000 \
    --screenshot="$out/$name$suffix.png" "file://$dir/$name.html?theme=$theme" 2>/dev/null
done
ls -l "$out/$name.png" "$out/$name-dark.png"
