import os
import nuke
from wknd_tools.comp import helpers

import flowReadFromWrite


def build_gizmo_menus(gizmos_root, top_tb_name="Gizmos", node_tb_path="Nodes"):
    """
    Escanea gizmos_root y crea submenús por carpeta.
    Cada .gizmo aparece como comando que crea el nodo.
    """

    gizmos_root = os.path.normpath(gizmos_root)

    if not os.path.isdir(gizmos_root):
        nuke.tprint(f"[GIZMOS] Carpeta no encontrada: {gizmos_root}")
        return

    # Hace que Nuke pueda encontrar los .gizmo en esa ruta (y subrutas)
    nuke.pluginAddPath(gizmos_root)

    node_tb = nuke.menu(node_tb_path)
    top_menu = node_tb.addMenu(top_tb_name, icon="Gizmo.png")

    # Para no recrear menús duplicados si recargas menu.py
    created_menus = {}

    for dirpath, dirnames, filenames in os.walk(gizmos_root):
        gizmo_files = [f for f in filenames if f.lower().endswith(".gizmo")]
        if not gizmo_files:
            continue

        rel_dir = os.path.relpath(dirpath, gizmos_root)
        rel_dir = "" if rel_dir == "." else rel_dir

        # Crea (o reutiliza) submenús para la ruta relativa
        parent = top_menu
        if rel_dir:
            parts = rel_dir.split(os.sep)
            current_path_key = ""
            for p in parts:
                current_path_key = (current_path_key + "/" + p) if current_path_key else p
                if current_path_key not in created_menus:
                    created_menus[current_path_key] = parent.addMenu(p)
                parent = created_menus[current_path_key]

        # Añade cada gizmo como comando
        for gizmo in sorted(gizmo_files, key=str.lower):
            gizmo_name = os.path.splitext(gizmo)[0]

            # Evita problemas con nombres raros (espacios, etc.)
            # Si tus gizmos tienen espacios, conviene renombrarlos.
            cmd = f'nuke.createNode("{gizmo_name}")'

            # Etiqueta bonita: puedes usar gizmo_name o algo formateado
            parent.addCommand(gizmo_name, cmd)

    nuke.tprint(f"[GIZMOS] Menús creados desde: {gizmos_root}")


####################################################################

# ==== TOP MENU =====

menu = nuke.menu("Nuke").addMenu("WKND")
menu.addCommand("Import Shot Camera", helpers.import_shot_camera)
menu.addCommand('Read from FlowWrite','flowReadFromWrite.run()','alt+r')
# menu.addCommand("Import Template", helpers.import_template)


####################################################################

# ===== TOOLBAR ======

# Ruta raíz de gizmos
GIZMOS_ROOT = r"Z:/05Framework/packages/resources/nuketools/nodes"

build_gizmo_menus(
    gizmos_root=GIZMOS_ROOT,
    top_tb_name="WKND",   # el menú principal
    node_tb_path="Nodes"    # normalmente "Nodes"
)

