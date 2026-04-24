import sys
sys.path.insert(0, r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config\install\core\python")
sys.path.insert(0, r"Z:\05Framework\users\aferraz")

import maya.standalone
maya.standalone.initialize(name='python')
import maya.cmds as mc

mc.loadPlugin("AbcImport")

import sgtk
import os
import shutil
import pprint

import wknd_tools
from wknd_tools.utils import json_set
from wknd_tools.core import exporters
from wknd_tools.UI import animPublisher_ui
from wknd_tools.animPub import animation_publisher
from wknd_tools.updater import prop_updater
import importlib
importlib.reload(json_set)
importlib.reload(exporters)
importlib.reload(animPublisher_ui)
importlib.reload(animation_publisher)
importlib.reload(prop_updater)

#######################
# Conectar a ShotGrid #
#######################

tk = sgtk.sgtk_from_path(r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config")
sg = tk.shotgun

#############################################################################


BAD_ASSETS = [
    "baul",
    "capibaraToy",
    "cronometro",
    "escalerasMecanicas",
    "huesoPerpetuo",
    "panMordido",
    "plataformaEquilibrio",
    "porcionCesped",
    "puertaCasaAcogida",
    "puertaEntrenamiento",
    "puertaEscuela",
    "puertaGimnasio",
    "puertaPasillo",
    "telefonoMovil",
    "transportin",
    "tren"
]


def find_last_cache_folder_sg(shot_name):

    # Search for published files
    fields = [
        ["entity.Shot.code", "is", shot_name],
        ["published_file_type.PublishedFileType.code", "in", ["Anim Cache Folder", "JSON Set"]],
        ]
    queries = [
        "code", "published_file_type.PublishedFileType.code", "version_number", "path"
        ]
    published_files = sg.find("PublishedFile", fields, queries, order=[{"field_name": "version_number", "direction": "desc"}])

    caches = [i for i in published_files if i['published_file_type.PublishedFileType.code']=="Anim Cache Folder"]

    anim_cache_folder = caches[0]["path"]["local_path"]

    # Get cache files from folder
    anim_cache_files = [os.path.join(anim_cache_folder, file) for file in os.listdir(anim_cache_folder) if os.path.join(anim_cache_folder, file).endswith("abc")]
    anim_cache_files = [cache for cache in anim_cache_files if "_hair_" not in cache] # Filtramos los HAIR

    return anim_cache_files


def find_approved_anim_tasks():

    filters = [
        ["entity", "type_is", "Shot"],
        ["content", "is", "Animation"],
        ["sg_status_list", "is", "apppbl"],
        ["entity.Shot.code", "is", "sq0040_sh0010"],
    ]

    queries = ["entity.Shot.code"]

    tasks = sg.find("Task", filters, queries)

    return tasks


def _remove_exported_caches():

    exporteds = mc.ls("exported*")
    if exporteds:
        for ref_node in exporteds:
            mc.file(referenceNode=ref_node, removeReference=True)


def main():

    error = []
    processed = []

    template_work = tk.templates["maya_shot_work"]
    template_publish = tk.templates["maya_shot_publish"]
    template_anim_cache_root = tk.templates["maya_shot_anim_assets_abc_publish_root"]
    template_anim_cache = tk.templates["maya_shot_anim_assets_abc_publish"]

    # Buscamos las task de ANIM aprobadas
    tasks = find_approved_anim_tasks()

    # Creamos un diccionario con los elementos a procesar
    # {shot_name: {task: {task_dic}, caches: [list of caches to process], assets: []}
    to_process = {}
    for task in tasks:
        # print("============================")
        # print(f"- TASK --> {task}")
        bads = []
        assets = []
        try:
            # Buscamos las caches
            anim_cache_files = find_last_cache_folder_sg(task["entity.Shot.code"])

            # Miramos si hay alguna en BAD ASSETS
            for anim_cache in anim_cache_files:
                for bad_asset in BAD_ASSETS:
                    if bad_asset in anim_cache:
                        bads.append(anim_cache)
                        fields = template_anim_cache.get_fields(anim_cache)
                        assets.append(fields["Asset"])
            if bads:
                print("============================")
                print(f"- TASK --> {task}")
                print("- anim_cache_files:")
                for i in bads: print(i)

                to_process[task["entity.Shot.code"]] = {"task": task, "caches": bads, "assets": assets}

        except:
            error.append(task["entity.Shot.code"])

    pprint.pprint(to_process)

    # Procesamos los shots
    for shot in to_process:

        print(f"= PROCESSING {shot} ==============================")

        mc.file(new=True)

        cache_folder = os.path.dirname(to_process[shot]["caches"][0])
        fields = template_anim_cache_root.get_fields(cache_folder)
        fields["name"] = "scene"

        publish_path = template_publish.apply_fields(fields)
        work_path = template_work.apply_fields(fields)

        print(f"- Copiamos {publish_path} a {work_path}")

        shutil.copy2(publish_path, work_path)

        mc.file(work_path, open=True, f=True)

        # First UNHIDE CHAR and PROPS groups
        # mc.setAttr("CHAR.v", True)
        mc.setAttr("PROPS.v", True)

        # Remove previous exported caches
        print("- Removing caches...")
        _remove_exported_caches()

        # Get publicable elements of the scene
        elems = animPublisher_ui.get_characters_and_props()
        elements_to_render = [elem for elem in elems["props"] if elem["name"] in to_process[shot]["assets"]]

        print("ELEMENTS TO RENDER ------------")
        pprint.pprint(elements_to_render)

        # Hacemos update de los PROPS
        props = prop_updater._search_props()
        if props:
            for node in props:
                prop_updater._update_rig(node)

        print("\t - PROPS UPDATED :)")

        # Get Playback
        frame_in = int(mc.playbackOptions(q=1, min=1)) - 1
        frame_out = int(mc.playbackOptions(q=1, max=1)) + 1

        # Hacemos el export de las caches
        # Cambiamos el modo de Evaluation a 'DG'
        mc.evaluationManager(mode='off')

        for asset in elements_to_render:

            scene_fields = fields.copy()
            scene_fields['Asset'] = asset['name']
            scene_fields['variante'] = asset['variant']
            # Miramos si es una instancia
            if asset['instance_num']:
                scene_fields['copyNum'] = asset['instance_num']

            geo_to_export = (asset['namespace'] + ':geo')
            abc_path = template_anim_cache.apply_fields(scene_fields)

            exporters.export_alembic(geo_to_export, abc_path, frame_in, frame_out)

        # Volvemos a 'Parallel'
        mc.evaluationManager(mode='off')

        # Guardamos la escena y la reemplazamos por la publicada
        mc.file(save=True, f=True)
        shutil.copy2(publish_path, publish_path.replace("scene", "oldPublish"))
        print(f"- Copiamos de vuelta {work_path} a {publish_path}")
        shutil.copy2(work_path, publish_path)

        processed.append(shot)
        print(f"============= {shot} DONE :) ===================")

        print("** Processed ------------------------------------------------------------------------")
        pprint.pprint(processed)


if __name__ == "__main__":
    main()

## USE ##
# "C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe" Z:\05Framework\users\aferraz\wknd_tools\utils\republishAnimCaches.py
