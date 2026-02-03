import maya.cmds as mc
import maya.OpenMayaUI as omui
import sgtk
import os
import re
import shutil
import tempfile
from ..core import exporters


def publish_animation(context, engine, log, selected_assets):

    tk = engine.sgtk
    sg = engine.shotgun

    print("=" * 60)
    print("STARTING ANIM PUBLISH")
    print("=" * 60)

    scene_path = mc.file(q=True, sn=True)
    log(f"Publishing: {scene_path}")
    #################
    # Get templates #
    #################

    if context.entity['type'].lower() == "asset":
        scene_work_template = tk.templates["maya_asset_work"]
        try:
            movie_template = tk.templates["maya_asset_playblast_publish"]
        except:
            movie_template = False
    else:
        scene_work_template = tk.templates["maya_shot_work"]
        movie_template = tk.templates["maya_shot_playblast_publish"]

    # Get fields from file
    scene_fields = scene_work_template.get_fields(scene_path)

    print(f"- SCENE FIELDS FROM TEMPLATE:\n {scene_fields}")

    # Get Shot info from SG
    query = ["sg_cut_in", "sg_cut_out"]
    shot_info_sg = sg.find_one("Shot", [["code", "is", scene_fields["Shot"]]], query)

    ###################
    # GET FRAME RANGE #
    ###################

    log("Getting Frame Range")

    # From Playback
    frame_in = int(mc.playbackOptions(q=1, min=1)) - 1
    frame_out = int(mc.playbackOptions(q=1, max=1)) + 1

    # # Compare playback with SG
    # if frame_in != shot_info_sg["sg_cut_in"] or frame_out != shot_info_sg["sg_cut_out"]:

    #     print(f"FRAME IN ---> {frame_in}")
    #     print(f"CUT IN ---> {shot_info_sg['sg_cut_in']}")
    #     print(f"FRAME OUT ---> {frame_out}")
    #     print(f"CUT OUT ---> {shot_info_sg['sg_cut_out']}")

    #     log("❌ ERROR: Duration do not match with SG...")
    #     return False, "❌ ERROR: Duration do not match with SG..."

    ###############
    # LOOP ASSETS #
    ###############

    log("Processing Assets...")

    # Define templates
    template_asset_by_shot_root = tk.templates["maya_shot_anim_assets_abc_publish_root"]
    template_asset_by_shot = tk.templates["maya_shot_anim_assets_abc_publish"]
    template_asset_hair_by_shot = tk.templates["maya_shot_anim_assets_abc_hair_publish"]

    # Creamos la carpeta root si no existe
    publish_root = template_asset_by_shot_root.apply_fields(scene_fields)
    if not os.path.exists(publish_root):
        os.makedirs(publish_root)

    # errorRig = []

    for asset in selected_assets:

        log(f"Processing --> {asset}")

        ns = f"[{asset['namespace']}]" if asset['namespace'] else ""
        print(f"  • {asset['group']}: {asset['name']} {ns} (full: {asset['full_name']})")

        scene_fields['Asset'] = asset['name']
        scene_fields['variante'] = asset['variant']

        # Miramos si es una instancia
        if asset['instance_num']:
            scene_fields['copyNum'] = asset['instance_num']

        # Formamos el path de export
        abc_path = template_asset_by_shot.apply_fields(scene_fields)

        geo_to_export = (asset['namespace'] + ':geo')
        print(f"\t- GEO: {geo_to_export} --> {abc_path}")

        # Si es un character añadimos la geo que tiene el hair
        if asset["group"] == "CHAR":

            log(f"Switching rig to hair for -{asset['name']}-")

            success = switch_to_hair_rig(geo_to_export)

            if success:

                abc_path_hair = template_asset_hair_by_shot.apply_fields(scene_fields)

                geo_to_export_hair = geo_to_export.split(":")[0] + ":hair"

                print(f"\t\t- GEO (HAIR): {geo_to_export_hair} --> {abc_path_hair}")

                # Exportamos la geo del hair
                exporters.export_alembic(geo_to_export_hair, abc_path_hair, frame_in, frame_out)

                print("\t 👍 Hair abc exported!")

            else:

                # errorRig.append(asset["name"])
                return False, f"\t ❌ ERROR: Cannot switch -{asset['name']}- Rig to hair...!"

        # Exportamos la geo
        exporters.export_alembic(geo_to_export, abc_path, frame_in, frame_out)
        log("👍 Geo abc exported!")

    print("="*60)
    log(f"Total: {len(selected_assets)} assets exported! Publishing to SG...\n")

    # if errorRig:
    #     log(f"ERROR changing Rig for: {errorRig}")

    # Register publish on SG
    publish = sgtk.util.register_publish(
        tk,
        context,
        publish_root,           # <- puede ser carpeta también
        f"{scene_fields['Shot']}_caches",
        scene_fields["version"],
        published_file_type="Anim Cache Folder",  # o el type que tengáis
        comment="Publish de las caches de ANIM",
    )

    return True, "✅ DONE :) You can now close this window!"

#############################################################


def get_hair_rig_from_character(asset_geo_node):
    """this gets from asset['namespace'] + ':geo' a shape and Id attr and return 
    last published hair rig"""

    import sgtk
    engine = sgtk.platform.current_engine()
    sg = engine.shotgun

    # get one shape from geo grp and its asset_id
    geo_shape = mc.listRelatives(asset_geo_node, ad=1, c=1, type='mesh')[0]
    asset_id = mc.getAttr(f'{geo_shape}.GUS_asset_id')

    fields = [
        'code',                    # Nombre de la publicación
        'version_number',          # Número de versión
        'path',                    # Path al archivo publicado
        'created_at',              # Fecha de creación
        'created_by',              # Usuario que lo creó
        'description',             # Descripción
        'published_file_type',     # Tipo de archivo publicado
        'task',                    # Tarea asociada
        'version',                 # Versión asociada (si existe)
        'sg_status_list'           # Status de SG
    ]

    # Filtros para la búsqueda
    filters = [
        ['entity', 'is', {'type': 'Asset', 'id': asset_id}],
        ['task.Task.content', 'is', 'RigAnimation'],
        ['code', 'contains', 'hair'],  # El nombre contiene "hair"
        ['code', 'contains', '.ma']    # El nombre contiene ".ma"  # Filtra por tipo "Rig"
    ]

    rig_publishes = sg.find('PublishedFile', filters, fields)
    rig_publishes.sort(key=lambda x: x.get('version_number', 0), reverse=True)

    approved_hair_rig_publishes = [publish for publish in rig_publishes if publish['sg_status_list'] == 'apr']

    hair_rig = approved_hair_rig_publishes[0] if approved_hair_rig_publishes else None

    if hair_rig:

        hair_rig_path = hair_rig['path']['local_path']
        return hair_rig_path
    else:
        return None


def switch_to_hair_rig(asset_geo_node):

    hair_rig_dict = {}

    print("\t\t\t- Switching to hair Rig...")

    hair_rig_dict['hair_rig_path'] = get_hair_rig_from_character(asset_geo_node)

    print(f"\t\t\t- HAIR RIG PATH: {hair_rig_dict['hair_rig_path']}")

    if not hair_rig_dict['hair_rig_path']:
        return False

    mesh = mc.listRelatives(asset_geo_node, ad=1)[0]
    hair_rig_dict['reference_node'] = mc.referenceQuery(mesh, referenceNode=True)

    print(f"\t\t\t- REF NODE: {hair_rig_dict['reference_node']}")

    # Get current rig
    hair_rig_dict['current_path'] = mc.referenceQuery(hair_rig_dict['reference_node'], filename=True)

    print(f"\t\t\t- CURRENT PATH: {hair_rig_dict['current_path']}")

    # Replace actual rig for hair rig
    mc.file(hair_rig_dict['hair_rig_path'], loadReference=hair_rig_dict['reference_node'])

    print("\t\t\t- Done! :)")

    return hair_rig_dict

# def _backup_current_scene_temp(scene_path):
#     # Ruta actual de la escena en Maya

#     if not scene_path:
#         mc.error("Scene must be saved before publishing...")

#     # Carpeta temporal del sistema
#     temp_dir = tempfile.gettempdir()

#     # Nombre del archivo temporal basado en el nombre real
#     base = os.path.basename(scene_path)
#     temp_path = os.path.join(temp_dir, f"TMP_BACKUP_{base}")

#     # Copia fiel del archivo (.ma o .mb)
#     shutil.copy2(scene_path, temp_path)

#     print("Backup temporal creado en:", temp_path)
#     return temp_path


def format_namespace(ns):

    aux = ns.title()
    aux = aux.replace("_", "")
    return aux
