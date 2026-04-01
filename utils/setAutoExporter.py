import sys
sys.path.insert(0, r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config\install\core\python")
sys.path.insert(0, r"Z:\05Framework\users\aferraz")

import maya.standalone
maya.standalone.initialize(name='python')
import maya.cmds as mc

mc.loadPlugin("AbcImport")

import time
import sgtk
import logging
import pprint
import os

import datetime
now = datetime.datetime.now()

import wknd_tools
from wknd_tools.utils import json_set
import importlib
importlib.reload(json_set)

#######################
# Conectar a ShotGrid #
#######################

tk = sgtk.sgtk_from_path(r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config")
sg = tk.shotgun


def setup_logger():
    logger = logging.getLogger("wknd_autopub")
    logger.setLevel(logging.DEBUG)

    # 🔥 clave: evita que también lo maneje el logger padre (root)
    logger.propagate = False

    # Si quieres que sea idempotente “de verdad”, puedes limpiar siempre:
    # logger.handlers.clear()

    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        sh = logging.StreamHandler()
        sh.setLevel(logging.DEBUG)
        sh.setFormatter(fmt)
        logger.addHandler(sh)

        log_path = r"Z:\05Framework\logs\auto_publish\autoPublish_SETs_log.txt"
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)

    return logger


def _search_masters(sequence_name=False):

    # Get those with Previs Aproved
    filters_task = [
        ["entity.Shot.code", "contains", "master_"],
        ["content", "is", "Previs"],
        ["sg_status_list", "is", "apr"],
    ]

    if sequence_name:
        print("Adding sequence Filter to sg query!")
        filters_task.append(["entity.Shot.sg_sequence.Sequence.code", "is", sequence_name])

    queries_task = [
        "entity.Shot.code",
        "entity.Shot.sg_sequence.Sequence.code",
        "entity.Shot.sg_set_json_exported",
        "entity.Shot.id",
    ]

    tasks = sg.find("Task", filters_task, queries_task)

    return tasks


def _open_scene(shot):

    template = tk.templates["maya_shot_publish"]

    fields = {"Step": "LAY",
              "Task": "Previs",
              "name": "scene",
              "Shot": shot["entity.Shot.code"],
              "Sequence": shot["entity.Shot.sg_sequence.Sequence.code"]
              }

    paths = tk.paths_from_template(template, fields)
    paths.sort(reverse=True)
    scene_path = paths[0]

    print(f"Scene path is --> {scene_path}")

    fields = template.get_fields(scene_path)

    if not scene_path:
        return False

    # mc.file(scene_path, open=True, f=True)

    # Cargamos la escena sin nada y luego cargamos las refs
    mc.file(scene_path, o=True, f=True, prompt=False, loadReferenceDepth="none")

    ref_nodes = mc.ls(references=True) or []
    for ref_node in ref_nodes:
        print(f"Cargando {ref_node}", flush=True)
        fn = mc.referenceQuery(ref_node, filename=True)
        print(f"\t - {fn}")
        # Cargamos la ref si no es un CHAR
        if any(x in fn for x in ("CHS", "CHE", "CHM")):
            print(f" xxxxxxx Not loading due to is a CHAR")
            continue
        mc.file(loadReference=ref_node, loadReferenceDepth="all")

    return fields


def get_shots_from_sequencer():

    # get shots from sequencer
    seq_manager = mc.sequenceManager(q=True, node=True)
    sequencer = mc.listConnections(seq_manager, type='sequencer')[0]
    shots = mc.listConnections(sequencer, type="shot") or []  # Get a list of all shots from the sequencer.
    return shots


def main():

    if len(sys.argv) < 2:
        print("No se ha recibido el nombre de la secuencia")
        sequence_name = False
    else:
        sequence_name = sys.argv[1]
        print(f"Secuencia recibida: {sequence_name}")

    logger = setup_logger()

    logger.info("--------------------------------------------------------- ")
    logger.info(f"STARTING ROUTINE ----------- {now} ---- ")
    logger.info("--------------------------------------------------------- ")

    # Init things
    succeed_all = {}

    # Get mastershots and iterate it
    mastershots = _search_masters(sequence_name)
    logger.info(f"MASTERS TO PROCESS: {mastershots}")

    # Iterate Master Shots -------------------------------------
    for mastershot in mastershots:

        succeed = []

        logger.info(f"- {mastershot} ------------")

        # Check if has been already processed
        if mastershot["entity.Shot.sg_set_json_exported"]:
            continue

        # Open MasterShot and get its Shots
        logger.info("\t - Opening scene...")
        mastershot_fields = _open_scene(mastershot)
        logger.info("\t - Scene opened!")
        if not mastershot_fields:
            return False
        shots_in_master = get_shots_from_sequencer()
        logger.info(f"\t - SHOTS in Master: {shots_in_master}")

        shotnames_in_master = []

        # Iterate Shots ----------------------------------------
        logger.info("\t - Processing Shots:")
        for shot in shots_in_master:

            logger.info(f"\t\t - {shot} ------------")

            # Get Shot Name
            shot_name = mc.getAttr(f"{shot}.shotName")
            logger.info(f"\t\t + {shot_name}")
            shotnames_in_master.append(shot_name)

            # Get Shot entity from SG
            shot_entity = sg.find_one(
                    'Shot',
                    [['code', 'is', shot_name]],
                    ['code', 'sg_set_json_exported']
                )

            # Check if has been already processed
            if shot_entity['sg_set_json_exported']:
                succeed.append(shot_name)
                continue

            # Form Shot fields and resolve SET template
            shot_fields = {
                "Sequence": mastershot_fields["Sequence"],
                "Shot": shot_name,
                "Step": mastershot_fields["Step"],
                "Task": "Layout",
                "name": "scene",
                "version": mastershot_fields["version"]
            }

            template_set = tk.templates["maya_shot_set_json_publish"]
            shot_set_path = template_set.apply_fields(shot_fields)

            logger.info(f"\t\t + Set Path -> {shot_set_path}")

            # Create folders if not exists
            if not os.path.exists(os.path.dirname(shot_set_path)):
                logger.info("\t\t + Creating SET folder...")
                os.makedirs(os.path.dirname(shot_set_path))

            # Get frame range of Shot
            start_frame = mc.getAttr(f"{shot}.startFrame")
            end_frame = mc.getAttr(f"{shot}.endFrame")
            logger.info(f"\t\t + Frame Range -> {start_frame} - {end_frame}")

            # Change current frame to Shot start frame
            mc.currentTime(start_frame, edit=True)
            logger.info(f"\t\t + Current Time -> {mc.currentTime(q=True)}")

            # Get element dict for that frame
            elem_dict = json_set.getAllElements()
            logger.info(f"\t\t + Element Dict -> {elem_dict}")

            # Write elements to JSON
            json_set.writeElemDictToJson(elem_dict, shot_set_path)
            logger.info("\t\t + JSON Writed :)")

            # Publish to SG
            publish_name = f"{shot_fields['Shot']}_set_v{shot_fields['version']:03}"
            context = tk.context_from_entity("Shot", shot_entity["id"])

            logger.info("\t\t + Publishing SET...")

            publish = sgtk.util.register_publish(
                tk,
                context,
                shot_set_path,
                publish_name,
                shot_fields["version"],
                published_file_type="JSON Set"
            )

            if publish:
                succeed.append(shot_name)
                sg.update("Shot", shot_entity["id"], {"sg_set_json_exported": True})

            logger.info("---------- Shot Done ----------")

        logger.info(f" ** Succeed --> {succeed}")

        all_shots_done = all(elem in succeed for elem in shotnames_in_master)
        print(f"ALL SHOTS DONE? --> {all_shots_done}")
        if all_shots_done:
            sg.update("Shot", mastershot["entity.Shot.id"], {"sg_set_json_exported": True})
            print(f"{mastershot['entity.Shot.code']} info updated! :)")

        succeed_all[mastershot["entity.Shot.code"]] = succeed
        logger.info("---------- Master Done ----------")

    logger.info("---------- FINAL:")
    logger.info(succeed_all)
    logger.info("--------------------------------------------------")


#############################################################################

if __name__ == "__main__":
    main()

## USE ##
# "C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe" Z:\05Framework\users\aferraz\wknd_tools\utils\setAutoExporter.py
