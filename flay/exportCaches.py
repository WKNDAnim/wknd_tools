import maya.cmds as mc
from wknd_tools.core import exporters
import imp
imp.reload(exporters)

import sgtk
engine = sgtk.platform.current_engine()
tk = engine.sgtk
sg = engine.shotgun


def _export_hair(ref_path_hair, cache_out_path_hair, frame_in, frame_out):

    # Path de la ref del hair
    # ref_path_hair = ref_path.replace("None", "hair")

    # Buscamos su top node
    refNodes = mc.referenceQuery(ref_path_hair, n=1)
    transforms = mc.ls(refNodes, type="transform")
    hair_to_export = transforms[0]

    previous_parent = mc.listRelatives(hair_to_export, allParents=True, fullPath=True)
    mc.parent(hair_to_export, w=1)

    print(f"\t- HAIR - {hair_to_export} - will be exported to {cache_out_path_hair} ----------------")

    # Exportamos la geo para el pelo
    exporters.export_alembic(hair_to_export, cache_out_path_hair, frame_in, frame_out)

    # Put the obj back to its previous parent
    mc.parent(hair_to_export, previous_parent)


############################################################################################

# def export_selected_geos():

# Get work template
template = tk.templates["maya_shot_work"]

# Get current version fields
current_file = mc.file(query=True, sceneName=True)
print(f"📝 Current File: {current_file}")
fields_work = template.get_fields(current_file)
current_version = fields_work["version"]
print(f"🧺 Fields WORK: {fields_work}")

# Template OUT CACHE
cache_out_path_template = tk.templates["maya_shot_anim_assets_abc_publish"]

# FRAME RANGE
frame_in = int(mc.playbackOptions(q=1, min=1)) - 1
frame_out = int(mc.playbackOptions(q=1, max=1)) + 1

error = []

selected = mc.ls(sl=1)
# obj = selected[0]
for obj in selected:

    # Buscamos el path a la referencia actual
    try:
        ref_path = mc.referenceQuery(obj, filename=True)
        print(ref_path)
    except:
        ref_path = False
        print(f"❌ ERROR: '{obj}' no pertenece a un nodo de referencia")
        mc.confirmDialog(message=f"❌ ERROR: '{obj}' no pertenece a un nodo de referencia")

    # Get its childs
    children = mc.listRelatives(obj, allDescendents=True, fullPath=True)

    # Get shapes in childs
    shapes = mc.ls(children, type="mesh")

    # Comprobamos si la shape tiene los extra attr
    if not "GUS_asset_id" in mc.listAttr(shapes[0]):
        print(f"❌ ERROR: Faltan los CUSTOM ATTRIBUTES en este asset... --> {children}")
        error.append(obj)
        continue

    # Buscamos el asset en sg
    id = mc.getAttr(shapes[0] + ".GUS_asset_id")
    sg_asset = sg.find_one("Asset", [["id","is",id]], ["sg_asset_type", "code"])

    # Sacamos los Fields del path
    cache_fields = cache_out_path_template.get_fields(ref_path)

    # Formamos el path de HAIR
    cache_hair_template = tk.templates["maya_shot_anim_assets_abc_hair_publish"]
    ref_hair_path = cache_hair_template.apply_fields(cache_fields)

    # Formamos el path de out para la cache de ese asset
    cache_fields["Step"] = "FLAY"
    cache_fields["Task"] = "FLay"
    cache_fields["version"] = current_version

    cache_out_path = cache_out_path_template.apply_fields(cache_fields)

    print(f"- GEO will be exported to {cache_out_path} ----------------")

    # Exportamos la geo
    previous_parent = mc.listRelatives(obj, allParents=True, fullPath=True)
    mc.parent(obj, w=1)
    exporters.export_alembic(obj, cache_out_path, frame_in, frame_out)
    print(f"Exporting GEO to --> {cache_out_path}")

    # Filtramos el export dependiendo del asset type
    if "CH" in sg_asset["sg_asset_type"]:

        # Formamos el path de out para la cache de ese asset
        cache_out_path_hair = cache_hair_template.apply_fields(cache_fields)
        _export_hair(ref_hair_path, cache_out_path_hair, frame_in, frame_out)

    # Put the obj back to its previous parent
    mc.parent(obj, previous_parent)
