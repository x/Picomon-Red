#!/bin/sh
# usage: ./build.sh "Pokemon - Red Version (USA, Europe).gb"   ->  cart/pokered.p8.png (and cart/pokered.p8)
# needs uv (https://docs.astral.sh/uv/): it installs the python dependencies on first run
set -e
[ -f "$1" ] || { echo "usage: $0 path/to/pokemon_red.gb"; exit 1; }
rom="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
cd "$(dirname "$0")"
rm -rf build/pokered
mkdir -p build/pokered cart
uv run tools/extract.py "$rom" build/pokered
uv run tools/build.py
