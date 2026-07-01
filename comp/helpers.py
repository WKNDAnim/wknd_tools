import os
import nuke
import sgtk

CAMERA_EXTENSIONS = (".abc",)

# Pares (Step, Task) a probar, en orden de preferencia
CAMERA_SOURCES = [
    ("FLAY", "FLay"),
    ("LAY", "Layout"),
]


def import_camera(camera_path):
    cam = nuke.nodes.Camera2()
    cam["read_from_file"].setValue(True)
    cam["file"].setValue(camera_path)
    cam["frame_rate"].setValue(24)
    return cam


def find_latest_camera(template, fields, step, task):
    """Devuelve la ruta de la cámara más reciente para un Step/Task, o None."""

    fields = dict(fields)
    fields["Step"] = step
    fields["Task"] = task
    root = template.apply_fields(fields)

    if not os.path.isdir(root):
        return None

    cameras = sorted(
        (
            os.path.join(root, f)
            for f in os.listdir(root)
            if f.lower().endswith(CAMERA_EXTENSIONS)
        ),
        reverse=True,
    )
    return cameras[0] if cameras else None


def import_shot_camera():

    engine = sgtk.platform.current_engine()
    tk = engine.sgtk
    ctx = engine.context

    template = tk.templates["maya_shot_camera_abc_publish_root"]
    fields = ctx.as_template_fields(template)

    for step, task in CAMERA_SOURCES:
        camera_path = find_latest_camera(template, fields, step, task)
        if camera_path:
            import_camera(camera_path)
            nuke.tprint(f"Cámara importada --> {camera_path}")
            return camera_path

    nuke.warning("ERROR: No existen cámaras para este shot.")
    return None


def _import_nuke_template():

    template_path = r"Z:\02Proyectos\Gus\resources\nuke_template.nk"
    nuke.nodePaste(template_path)

    # Obtener nodos pegados (los seleccionados)
    nodes = nuke.selectedNodes()

    # Offset deseado
    offset_x = 8390
    offset_y = 8730

    for n in nodes:
        n.setXpos(n.xpos() + offset_x)
        n.setYpos(n.ypos() + offset_y)
