#!/usr/bin/env bash
# Ejecuta un script de Blender en modo headless con ruta absoluta.
# Uso: blender/run.sh build_robin.py [-- --render --save]
# Por defecto usa el flatpak org.blender.Blender. Con otra instalacion, define BLENDER:
#   BLENDER=/ruta/a/blender blender/run.sh rig_ignis.py
set -euo pipefail
DIR=$(cd "$(dirname "$0")" && pwd)
script="$DIR/$1"; shift
if [[ -n "${BLENDER:-}" ]]; then
  exec "$BLENDER" --background --python "$script" "$@"
fi
exec flatpak run org.blender.Blender --background --python "$script" "$@"
