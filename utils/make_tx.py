#!/usr/bin/env mayapy
"""
make_tx_maya.py
---------------
Genera archivos .tx con maketx (Arnold) para todas las texturas de la escena
abierta, respetando el color space asignado en cada nodo de textura.

Naming de los .tx según color space del nodo:
    ACEScg  →  {nombre}.exr  →  {nombre}_raw.exr.tx
    Raw     →  {nombre}.exr  →  {nombre}_Raw_ACEScg.exr.tx

Uso:
    mayapy make_tx_maya.py /ruta/a/escena.mb
    mayapy make_tx_maya.py /ruta/a/escena.mb --maketx "C:/Program Files/Autodesk/bin/maketx.exe"
    mayapy make_tx_maya.py /ruta/a/escena.mb --dry-run
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

MAKETX_DEFAULT = r"C:/Program Files/Autodesk/bin/maketx.exe"

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
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Genera .tx con maketx (Arnold) para todas las texturas de una escena Maya."
    )
    parser.add_argument("scene", help="Ruta al fichero .mb o .ma")
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

    # --- Validar escena ---
    scene_path = os.path.abspath(args.scene)
    if not os.path.isfile(scene_path):
        print(f"Error: no se encuentra la escena '{scene_path}'")
        sys.exit(1)

    # --- Validar maketx ---
    if not os.path.isfile(args.maketx):
        print(f"Error: no se encuentra maketx en '{args.maketx}'")
        print("Usa --maketx para especificar la ruta correcta.")
        sys.exit(1)
    print(f"Usando maketx: {args.maketx}")

    # --- Inicializar Maya ---
    cmds = init_maya()
    open_scene(cmds, scene_path)

    # --- Recoger texturas ---
    textures = collect_textures(cmds)
    if not textures:
        print("\nNo se encontraron nodos de textura en la escena.")
        sys.exit(0)

    print(f"\nTexturas encontradas en la escena: {len(textures)}")

    # --- Clasificar ---
    pending  = []
    skipped  = []
    missing  = []  # textura original no existe en disco

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
        print("\nTodo al día, no hay nada que generar. ✓")
        sys.exit(0)

    # --- Generar ---
    print("\n" + "=" * 60)
    ok, fail = 0, 0
    for tex in pending:
        print(f"\n[{tex['node']}]  color space: {tex['color_space']}")
        success = generate_tx(args.maketx, tex["path"], tex["tx_path"], dry_run=args.dry_run)
        if success:
            ok += 1
        else:
            fail += 1

    # --- Resumen ---
    print("\n" + "=" * 60)
    print(f"Resumen: {ok} generados correctamente, {fail} con errores.")
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
