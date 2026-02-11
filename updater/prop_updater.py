import maya.cmds as mc
import os


def _search_props():

    if mc.objExists('PROPS'):
        char_children = mc.listRelatives('PROPS', children=True, type='transform') or []
        print(f"\n🔍 Analizando {len(char_children)} characters...")
        return char_children
    return False


def _update_rig(node):

    # node = f"{asset_name}_scene:{asset_name}"
    print("-"*30, node, "-"*30)

    # Obtener el reference node
    ref_node = mc.referenceQuery(node, referenceNode=True)
    current_path = mc.referenceQuery(ref_node, filename=True)
    print(current_path)

    if not "RIG" in current_path:
        return False

    # Nuevo path
    rig_pub_root = os.path.dirname(current_path)

    rig_files = os.listdir(rig_pub_root)
    rig_files.sort(reverse=True)

    rig_path = os.path.join(rig_pub_root, rig_files[0])
    print(rig_path)

    if os.path.basename(rig_path) in os.path.basename(current_path):
        print("- PATH ALREADY UPDATED!")
        return False

    # Cambiar el path
    mc.file(rig_path, loadReference=ref_node)

    print("Referencia actualizada:")
    print(f"{os.path.basename(current_path)} --> {os.path.basename(rig_path)}")

    return True


def update_all_outdated():

    props = _search_props()
    if props:
        updated = []
        for node in props:
            updt = _update_rig(node)
            if updt:
                updated.append(node)

        msg = f"{len(updated)} rigs updated to last version :)"
        mc.confirmDialog(title='Update Rigs', message=msg, button=['Okay'])
