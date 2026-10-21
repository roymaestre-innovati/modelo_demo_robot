#!/usr/bin/env bash
# Ejecuta un script de Blender (flatpak) en modo headless con ruta absoluta.
# Uso: blender/run.sh build_robin.py [-- --render --save]
set -euo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
script="$DIR/$1"; shift
exec flatpak run org.blender.Blender --background --python "$script" "$@"
