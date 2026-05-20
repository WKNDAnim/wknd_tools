#!/usr/bin/env mayapy
"""
make_tx_batch.py
----------------
Genera archivos .tx con maketx (Arnold) para las texturas de todas las
escenas del proyecto, respetando el color space asignado en cada nodo.
Maya standalone se inicializa una sola vez para todo el batch.

Naming de los .tx según color space del nodo:
    ACEScg  →  {nombre}.exr  →  {nombre}_raw.exr.tx
    Raw     →  {nombre}.exr  →  {nombre}_Raw_ACEScg.exr.tx

Uso:
    mayapy make_tx_batch.py
    mayapy make_tx_batch.py --dry-run
"""

import sys
import os
import glob
import re
import argparse
import subprocess


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

MAKETX_DEFAULT  = r"C:/Program Files/Autodesk/bin/maketx.exe"
PROJECT_ROOT    = r"Z:/02Proyectos/Gus/assets"

# Mapa color space → sufijo que Arnold añade al .tx
COLORSPACE_SUFFIX = {
    "ACEScg": "_raw",
    "Raw":    "_Raw_ACEScg",
}


# ---------------------------------------------------------------------------
# Inicialización de Maya Standalone
# ---------------------------------------------------------------------------

def init_maya():
    import maya.standalone
    maya.standalone.initialize(name="python")
    import maya.cmds as cmds
    return cmds


def open_scene(cmds, scene_path):
    print(f"Abriendo escena: {scene_path}")
    cmds.file(scene_path, open=True, force=True)


# ---------------------------------------------------------------------------
# Lógica de naming
# ---------------------------------------------------------------------------

def get_tx_path(texture_path, color_space):
    """
    Calcula el path del .tx que Arnold generaría para una textura dado su color space.

    ACEScg:  /ruta/textura.exr  →  /ruta/textura_raw.exr.tx
    Raw:     /ruta/textura.exr  →  /ruta/textura_Raw_ACEScg.exr.tx
    """
    suffix = COLORSPACE_SUFFIX.get(color_space)
    if suffix is None:
        print(f"  ⚠ Color space desconocido '{color_space}' para {os.path.basename(texture_path)}, se usará sufijo Raw.")
        suffix = COLORSPACE_SUFFIX["Raw"]

    base, ext = os.path.splitext(texture_path)
    return f"{base}{suffix}{ext}.tx"


def tx_exists(tx_path):
    return os.path.isfile(tx_path)


UDIM_TOKEN = re.compile(r"<udim>", re.IGNORECASE)


def expand_udim(path):
    """Dado un path con <UDIM> o <udim>, devuelve la lista de tiles reales que existen en disco."""
    pattern = UDIM_TOKEN.sub("[0-9][0-9][0-9][0-9]", path)
    return sorted(glob.glob(pattern))


# ---------------------------------------------------------------------------
# Recolección de texturas desde la escena
# ---------------------------------------------------------------------------

def _add_texture(textures, seen_paths, node, path, cs):
    """Añade una textura a la lista, expandiendo tiles si contiene <UDIM>."""
    if UDIM_TOKEN.search(path):
        tiles = expand_udim(path)
        if not tiles:
            # Sin tiles en disco: se reportará como missing en main()
            if path not in seen_paths:
                seen_paths.add(path)
                textures.append({"node": node, "path": path, "color_space": cs})
        else:
            for tile in tiles:
                if tile not in seen_paths:
                    seen_paths.add(tile)
                    textures.append({"node": node, "path": tile, "color_space": cs})
    else:
        if path not in seen_paths:
            seen_paths.add(path)
            textures.append({"node": node, "path": path, "color_space": cs})


def collect_textures(cmds):
    """
    Devuelve lista de dicts con {node, path, color_space}
    para todos los nodos aiImage y file de la escena.
    """
    textures = []
    seen_paths = set()

    # Nodos Arnold (aiImage)
    for node in cmds.ls(type="aiImage") or []:
        try:
            path = cmds.getAttr(f"{node}.filename")
            cs   = cmds.getAttr(f"{node}.colorSpace")
        except Exception:
            continue
        if path:
            _add_texture(textures, seen_paths, node, path, cs)

    # Nodos Maya estándar (file)
    for node in cmds.ls(type="file") or []:
        try:
            path = cmds.getAttr(f"{node}.fileTextureName")
            cs   = cmds.getAttr(f"{node}.colorSpace")
        except Exception:
            continue
        if path:
            _add_texture(textures, seen_paths, node, path, cs)

    return textures


# ---------------------------------------------------------------------------
# Generación de .tx
# ---------------------------------------------------------------------------

def generate_tx(maketx, texture_path, tx_path, dry_run=False):
    """Llama a maketx para generar el .tx. Retorna True si tuvo éxito."""

    cmd = [
        maketx,
        "-v",        # verbose
        "-u",        # skip si el .tx ya está actualizado
        "--oiio",    # metadatos optimizados para Arnold
        "-o", tx_path,
        texture_path,
    ]

    print(f"\n  {'[DRY-RUN] ' if dry_run else ''}Generando:")
    print(f"    origen:  {os.path.basename(texture_path)}")
    print(f"    destino: {os.path.basename(tx_path)}")

    if dry_run:
        print(f"    cmd: {' '.join(cmd)}")
        return True

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout.strip())
        print("    ✓ Generado correctamente.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"    ✗ Error:")
        if e.stderr:
            print(f"      {e.stderr.strip()}")
        return False


# ---------------------------------------------------------------------------
# Descubrimiento de escenas
# ---------------------------------------------------------------------------

_VERSION_RE = re.compile(r"_v(\d+)\.ma$", re.IGNORECASE)


def find_latest_scenes(root):
    """
    Busca en root/{Asset_type}/{Asset}/publish/maya/assets/ y devuelve,
    por cada asset, la escena con el número de versión más alto.
    """
    pattern = os.path.join(root, "*", "*", "publish", "maya", "assets", "*.ma")
    scenes = glob.glob(pattern)

    latest = {}
    for scene in scenes:
        m = _VERSION_RE.search(scene)
        if not m:
            continue
        base = scene[: m.start()]
        version = int(m.group(1))
        if base not in latest or version > latest[base][0]:
            latest[base] = (version, scene)

    return sorted(path for _, path in latest.values())


# ---------------------------------------------------------------------------
# Proceso de una escena
# ---------------------------------------------------------------------------

def process_scene(cmds, maketx, scene_path, dry_run=False):
    """Procesa una escena: recoge texturas, clasifica y genera .tx. Retorna (ok, fail)."""
    open_scene(cmds, scene_path)

    textures = collect_textures(cmds)
    if not textures:
        print("  No se encontraron nodos de textura.")
        return 0, 0

    print(f"  Texturas encontradas: {len(textures)}")

    pending = []
    skipped = []
    missing = []

    for tex in textures:
        if not os.path.isfile(tex["path"]):
            missing.append(tex)
            continue
        tx_path = get_tx_path(tex["path"], tex["color_space"])
        tex["tx_path"] = tx_path
        if tx_exists(tx_path):
            skipped.append(tex)
        else:
            pending.append(tex)

    print(f"  Ya tienen .tx:          {len(skipped)}")
    print(f"  Pendientes de generar:  {len(pending)}")
    if missing:
        print(f"  Textura no encontrada:  {len(missing)}")
        for tex in missing:
            print(f"    ⚠ {tex['node']}: {tex['path']}")

    if not pending:
        print("  Todo al día. ✓")
        return 0, 0

    ok, fail = 0, 0
    for tex in pending:
        print(f"\n  [{tex['node']}]  color space: {tex['color_space']}")
        success = generate_tx(maketx, tex["path"], tex["tx_path"], dry_run=dry_run)
        if success:
            ok += 1
        else:
            fail += 1

    return ok, fail


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Genera .tx con maketx (Arnold) para todas las escenas del proyecto."
    )
    parser.add_argument(
        "--maketx",
        default=MAKETX_DEFAULT,
        help=f"Ruta al ejecutable maketx (default: {MAKETX_DEFAULT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra qué se haría sin ejecutar nada",
    )
    args = parser.parse_args()

    # --- Validar maketx ---
    if not os.path.isfile(args.maketx):
        print(f"Error: no se encuentra maketx en '{args.maketx}'")
        print("Usa --maketx para especificar la ruta correcta.")
        sys.exit(1)
    print(f"Usando maketx: {args.maketx}")

    # --- Descubrir escenas ---
    if not os.path.isdir(PROJECT_ROOT):
        print(f"Error: la carpeta raíz '{PROJECT_ROOT}' no existe.")
        sys.exit(1)
    scene_paths = find_latest_scenes(PROJECT_ROOT)
    if not scene_paths:
        print(f"No se encontraron escenas en '{PROJECT_ROOT}'.")
        sys.exit(0)
    print(f"Escenas a procesar: {len(scene_paths)}")

    # --- Inicializar Maya (una sola vez) ---
    cmds = init_maya()

    # --- Procesar escenas ---
    total_ok, total_fail = 0, 0
    for i, scene_path in enumerate(scene_paths, 1):
        print(f"\n{'=' * 60}")
        print(f"[{i}/{len(scene_paths)}] {os.path.basename(scene_path)}")
        print("=" * 60)
        ok, fail = process_scene(cmds, args.maketx, scene_path, dry_run=args.dry_run)
        total_ok += ok
        total_fail += fail

    # --- Resumen global ---
    print(f"\n{'=' * 60}")
    print(f"TOTAL: {total_ok} generados correctamente, {total_fail} con errores.")
    if total_fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
