import maya.cmds as mc


def __select_top_rig_group(camera):

    # First, clean selection
    mc.select(clear=True)

    target = camera

    print('Full hierarchy: {}'.format(mc.ls(target, long=True)[0]))

    parent = None
    stop = False

    while not stop:
        p = mc.listRelatives(parent or target, parent=True)
        # print(f"{p} - PARENT: {parent} - STOP: {stop}")  # Logging to see iterations
        if p[0] == "CAMERAS":
            stop = True
        else:
            parent = p[0]

    if parent:
        print('{} has top-level parent {}'.format(target, parent))
        mc.select(parent)
        return mc.ls(sl=True, long=True)
    else:
        print('{} is top-level object'.format(target))
        return False


def _get_transform(node):
    """Devuelve un transform válido aunque selecciones un shape."""
    if not node:
        return None
    if mc.nodeType(node) == "transform":
        return node
    parents = mc.listRelatives(node, parent=True, fullPath=True) or []
    return parents[0] if parents else None


def _find_camera_transform_under(root_transform):
    """
    Busca la primera cámara (shape tipo 'camera') dentro del grupo/jerarquía.
    Devuelve el transform que la contiene.
    """
    if not root_transform or not mc.objExists(root_transform):
        return None

    # Incluye root + descendientes
    nodes = [root_transform] + (mc.listRelatives(root_transform, allDescendents=True, fullPath=True) or [])
    for n in nodes:
        if mc.nodeType(n) != "transform":
            continue
        shapes = mc.listRelatives(n, shapes=True, fullPath=True) or []
        for s in shapes:
            if mc.nodeType(s) == "camera":
                return n
    return None


def merge_namespaces_with_parent_and_rename_camera(sel, shotName):

    if not sel:
        mc.warning(u"No hay nada seleccionado.")
        return

    selected = sel[0]
    selected_xform = _get_transform(selected)
    if not selected_xform:
        mc.warning(u"No pude determinar el transform del elemento seleccionado.")
        return

    # Guardar UUID del objeto seleccionado (el que vamos a renombrar)
    uid = mc.ls(selected_xform, uuid=True)[0]

    # Nombre corto (sin path)
    leaf = selected_xform.split('|')[-1]

    # Extraer namespaces del objeto seleccionado
    parts = leaf.split(':')
    namespaces = parts[:-1]  # [] si no hay

    # Ir al root namespace
    mc.namespace(set=':')

    # Merge namespaces desde el más profundo al más alto
    for depth in range(len(namespaces), 0, -1):
        ns = ':'.join(namespaces[:depth])
        if mc.namespace(exists=ns):
            try:
                mc.namespace(removeNamespace=ns, mergeNamespaceWithParent=True)
            except:
                pass

    # Re-encontrar el objeto por UUID (robusto para cualquier versión)
    target = None
    # (Para no iterar TODO el DAG si no hace falta, probamos primero selection actual + parientes)
    all_nodes = mc.ls(long=True) or []
    for n in all_nodes:
        try:
            if mc.ls(n, uuid=True)[0] == uid:
                target = n
                break
        except:
            pass

    if not target:
        mc.warning(u"No pude reencontrar el objeto tras el merge.")
        return

    # # Pop-up para renombrar
    # short = target.split('|')[-1]
    # default_text = parts[-1] if parts else short

    # result = mc.promptDialog(
    #     title=u"Renombrar",
    #     message=u"Nuevo nombre para:\n{}".format(short),
    #     button=[u"OK", u"Cancelar"],
    #     defaultButton=u"OK",
    #     cancelButton=u"Cancelar",
    #     dismissString=u"Cancelar",
    #     text=default_text
    # )

    # if result != u"OK":
    #     return

    # new_name = mc.promptDialog(query=True, text=True).strip()

    new_name = shotName
    if not new_name:
        mc.warning(u"Nombre vacío.")
        return
    else:
        new_name = new_name + "_camera"

    # Renombrar el objeto (target)
    print("-"*100)
    print(f"TARGET ------> {target}")
    renamed_obj = mc.rename(target, new_name + "_rig")
    print(f"renamed_obj ------> {renamed_obj}")

    # Buscar y renombrar cámara dentro del grupo seleccionado (OJO: usamos el grupo original seleccionado)
    # Si el merge cambió nombres en la jerarquía, el path del grupo podría cambiar; así que lo buscamos por UUID también.
    # Para el "grupo" tomamos el transform que seleccionaste originalmente.
    # Si quieres que sea "el padre" del objeto seleccionado, dime y lo adapto.
    group_root = selected_xform
    if not mc.objExists(group_root):
        # Si el nombre cambió, intentamos reconstruirlo por UUID también (mismo uid solo para el target, no para el grupo).
        # En este caso, usamos el nuevo objeto renombrado como raíz de búsqueda (mejor que nada).
        group_root = renamed_obj

    cam_xform = _find_camera_transform_under(group_root)

    print(f"cam_xform ------> {cam_xform}")

    cam_renamed = None
    if cam_xform:

        new_cam_xform = mc.rename(cam_xform, new_name)


    # # Feedback
    # msg = u"<hl>Namespace limpiado</hl>. Objeto: <hl>{}</hl>".format(renamed_obj.split('|')[-1])
    # if cam_renamed:
    #     msg += u" | Cámara: <hl>{}</hl>".format(cam_renamed.split('|')[-1])
    # elif cam_xform:
    #     msg += u" | Cámara encontrada pero no se pudo renombrar."
    # else:
    #     msg += u" | No encontré cámara dentro del grupo seleccionado."

    # mc.select(renamed_obj, r=True)
    # mc.inViewMessage(amg=msg, pos='midCenter', fade=True)


## EXEC ##
def main():

    seq_manager = mc.sequenceManager(q=True, node=True)
    sequencer = mc.listConnections(seq_manager, type='sequencer')[0]
    shots = mc.listConnections(sequencer, type="shot") or []

    if shots:
        for shot in shots:

            print("-"*70)
            print(shot)

            shot_name = mc.getAttr(f"{shot}.shotName")
            shot_camera = mc.listConnections(f"{shot}.currentCamera")[0]
            print(f"SHOT --> {shot_name}")
            print(f"CAM --> {shot_camera}\n")

            selection = __select_top_rig_group(shot_camera)

            merge_namespaces_with_parent_and_rename_camera(selection, shot_name)

        # Feedback
        msg = u"<hl>DONE :) </hl>."
        mc.inViewMessage(amg=msg, pos='midCenter', fade=True)
