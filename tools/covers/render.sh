#!/bin/sh
# Render tools/covers/<name>.html to src/assets/work/<name>.png (light) and
# <name>-dark.png at 2x, using headless Chrome. Usage: tools/covers/render.sh cka-dojo
set -eu
name=$1
dir=$(cd "$(dirname "$0")" && pwd)
out="$dir/../../src/assets/work"
chrome=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
mkdir -p "$out"
for theme in light dark; do
  suffix=$([ "$theme" = dark ] && echo "-dark" || echo "")
  "$chrome" --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
    --window-size=1120,840 --virtual-time-budget=5000 \
    --screenshot="$out/$name$suffix.png" "file://$dir/$name.html?theme=$theme" 2>/dev/null
done
ls -l "$out/$name.png" "$out/$name-dark.png"
