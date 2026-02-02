import maya.cmds as mc
import maya.OpenMayaUI as omui
import os
import re
import shutil
import tempfile
from ..core import exporters


def publish_animation(context, engine, log, selected_assets):

    tk = engine.sgtk
    sg = engine.shotgun

    # log_text.clear()
    log("=" * 60)
    log("STARTING SPLIT")
    log("=" * 60)

    scene_path = mc.file(q=True, sn=True)

    # # Store a backup of the main file
    # backup_file_path = _backup_current_scene_temp(scene_path)

    # log(f"SCENE backupped to: {backup_file_path}")

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

    log(f"- SCENE FIELDS FROM TEMPLATE:\n {scene_fields}")

    # Get Shot info from SG
    query = ["sg_cut_in", 
             "sg_cut_out"]
    shot_info_sg = sg.find_one("Shot", [["code", "is", scene_fields["Shot"]]], query)

    ###################
    # GET FRAME RANGE #
    ###################

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

    template_asset_by_shot = tk.templates["maya_shot_anim_assets_abc_publish"]
    errorRig = []

    for asset in selected_assets:

        log(f"-Exporting {asset}")

        ns = f"[{asset['namespace']}]" if asset['namespace'] else ""
        print(f"  • {asset['group']}: {asset['name']} {ns} (full: {asset['full_name']})")

        scene_fields['Asset'] = format_namespace(asset['namespace'])

        # # Miramos si es una instancia
        # if asset['instance_num']:
        #     scene_fields['copyNum'] = asset['instance_num']

        # Formamos el path de export
        ma_path = template_asset_by_shot.apply_fields(scene_fields)

        geo_to_export = (asset['namespace'] + ':geo')
        log(f"\t- GEO: {geo_to_export} --> {ma_path}")

        # Si es un character añadimos la geo que tiene el hair
        if asset["group"] == "CHAR":

            log(f"\t- Is a CHAR!:")

            success = switch_to_hair_rig(geo_to_export, log)

            if success:

                template_asset_hair_by_shot = tk.templates["maya_shot_anim_assets_abc_hair_publish"]
                ma_path_hair = template_asset_hair_by_shot.apply_fields(scene_fields)

                geo_to_export_hair = geo_to_export.split(":")[0] + ":hair"

                log(f"\t\t- GEO (HAIR): {geo_to_export_hair} --> {ma_path_hair}")

                # Exportamos la geo del hair
                exporters.export_alembic(geo_to_export_hair, ma_path_hair, frame_in, frame_out)

                log("\t 👍 Hair abc exported!")

            else:

                errorRig.append(asset["name"])
                log(f"\t ❌ ERROR: Cannot switch -{asset['name']}- Rig to hair...!")

        # Exportamos la geo
        exporters.export_alembic(geo_to_export, ma_path, frame_in, frame_out)
        log("👍 Geo abc exported!")

    log("="*60)
    log(f"Total: {len(selected_assets)} assets\n")
    if errorRig:
        log(f"ERROR changing Rig for: {errorRig}")

    return True, "✅ DONE :)"

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


def switch_to_hair_rig(asset_geo_node, log):

    hair_rig_dict = {}

    log("\t\t\t- Switching to hair Rig...")

    hair_rig_dict['hair_rig_path'] = get_hair_rig_from_character(asset_geo_node)

    log(f"\t\t\t- HAIR RIG PATH: {hair_rig_dict['hair_rig_path']}")

    if not hair_rig_dict['hair_rig_path']:
        return

    mesh = mc.listRelatives(asset_geo_node, ad=1)[0]
    hair_rig_dict['reference_node'] = mc.referenceQuery(mesh, referenceNode=True)

    log(f"\t\t\t- REF NODE: {hair_rig_dict['reference_node']}")

    # Get current rig
    hair_rig_dict['current_path'] = mc.referenceQuery(hair_rig_dict['reference_node'], filename=True)

    log(f"\t\t\t- CURRENT PATH: {hair_rig_dict['current_path']}")

    # Replace actual rig for hair rig
    mc.file(hair_rig_dict['hair_rig_path'], loadReference=hair_rig_dict['reference_node'])

    log("\t\t\t- Done! :)")

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
