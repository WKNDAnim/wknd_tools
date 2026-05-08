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
from collections import defaultdict

###########
# GLOBALS #
###########

LINUX_ROOT = "/nbpt/remote/nbfxpt/jobs/GUS/mirror_weeknd"
WINDOWS_ROOT = "Z:/02Proyectos"

#######################
# Conectar a ShotGrid #
#######################

tk = sgtk.sgtk_from_path(r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config")
sg = tk.shotgun

###########################

def _search_shots_to_process():

    print("- Buscando shots...")

    # Get those with Previs Aproved
    filters_task = [
        # ["entity.Shot.code", "is", "sq0260_sh0010"],
        ["entity.Shot.code", "not_contains", "master_"],
        ["content", "is", "Lighting"],
        ["sg_status_list", "is", "psr"],
    ]

    queries_task = [
        "entity.Shot.code",
        "entity.Shot.sg_sequence.Sequence.code",
        "entity.Shot.id",
    ]

    tasks = sg.find("Task", filters_task, queries_task)

    if tasks:
        print(f"\t  + {len(tasks)} shots encontrados :)")
        return tasks
    else:
        print("ERROR: No se han encontrado shots -------------------------------------------------------")
        return False
    

def _find_shot_paths(shot):

    paths = defaultdict(dict)

    sequence_name = shot["entity.Shot.sg_sequence.Sequence.code"]
    shot_name = shot["entity.Shot.code"]

    paths["sequence_name"] = sequence_name
    paths["shot_name"] = shot_name

    ###############
    # MAYA SCENES #
    ###############

    # MAYA SCENES
    template_pt_maya = "Z:/02Proyectos/Gus/sequences/{seq}/{shot}/RND/Lighting/publish/maya/images/workfileLighting"
    template_work_maya = "Z:/02Proyectos/Gus/sequences/{seq}/{shot}/LGT/Lighting/work/maya/{shot}_scene_Lighting_v{version:03d}.ma"

    # Buscamos la root
    maya_pt_root = template_pt_maya.format(seq=sequence_name, shot=shot_name)

    # Buscamos la version que tiene la escena de Nuboyana
    versiones = os.listdir(maya_pt_root)
    versiones.sort(reverse=True)
    version = int(versiones[0][1:])

    paths["version"] = version

    # Formamos el path a la escena
    version_folder = os.path.join(maya_pt_root, versiones[0])
    maya_scene = os.listdir(version_folder)[0]

    # Nuboyana publish
    maya_pt_path = os.path.join(version_folder, maya_scene)
    paths["nuboyana"]["maya_scene"] = maya_pt_path

    # WKND work
    maya_work_path = template_work_maya.format(seq=sequence_name, 
                                               shot=shot_name, 
                                               version=version)
    paths["work"]["maya_scene"] = maya_work_path

    ###############
    # RENDERS EXR #
    ###############

    # RENDERS
    template_pt_renders = "Z:/02Proyectos/Gus/sequences/{seq}/{shot}/RND/Lighting/publish/maya/images/"
    template_work_renders = "Z:/02Proyectos/Gus/sequences/{seq}/{shot}/LGT/Lighting/work/maya/images/{shot}_scene_Lighting_v{version:03d}"

    # Formamos la root de work
    renders_work_root = template_work_renders.format(seq=sequence_name, shot=shot_name, version=version)

    # Buscamos la root de PT
    renders_pt_root = template_pt_renders.format(seq=sequence_name, shot=shot_name)

    paths["nuboyana"]["render"] = renders_pt_root
    paths["work"]["render"] = renders_work_root

    return paths


def copy_renders(paths):

    renders_pt_root = paths["nuboyana"]["render"]
    renders_work_root = paths["work"]["render"]
    shot_name = paths["shot_name"] 
    version = paths["version"]

    print("\t\t - renders_pt_root --> {renders_pt_root}")
    print("\t\t - renders_work_root --> {renders_work_root}")
    print("\t\t - shot_name --> {shot_name}")
    print("\t\t - version --> {version}")

    # Buscamos las render Layers
    render_layers = os.listdir(renders_pt_root)
    render_layers = [r for r in render_layers if not shot_name in r]
    render_layers = [r for r in render_layers if r != "workfileLighting"]

    for layer in render_layers:

        print("\t\t - LAYER --> {layer} ---------- ")

        # Formamos la carpeta del LAYER
        layer_folder_pt = os.path.join(renders_pt_root, layer)
        print("\t\t\t - layer_folder_pt --> {layer_folder_pt}")
        
        # Buscamos la última version dentro de la LAYER
        versiones = os.listdir(layer_folder_pt)
        versiones.sort(reverse=True)
        version_folder_pt = os.path.join(layer_folder_pt, versiones[0])
        print("\t\t\t - version_folder_pt --> {version_folder_pt}")

        # Filtramos las Render Layers
        if not "renderSlapcomp" in layer:
            renderLayer_name = layer.replace("renderLighting", "").replace("_beauty", "")
        else:
            renderLayer_name = layer
        
        # Formamos la carpeta de la versión
        layer_folder_work = os.path.join(renders_work_root, renderLayer_name)
        print("\t\t\t - layer_folder_work --> {layer_folder_work}")
        if not os.path.exists(layer_folder_work):
            os.makedirs(layer_folder_work)

        # Copiamos los frames a work
        for frame in os.listdir(version_folder_pt):

            new_frame_name = frame.replace(layer, renderLayer_name).replace(versiones[0], f"v{version:03d}")

            frame_pt_path = os.path.join(version_folder_pt, frame)
            frame_work_path = os.path.join(layer_folder_work, new_frame_name)

            shutil.copy2(frame_pt_path, frame_work_path)

    return paths


def repath_references():

    refs = mc.file(query=True, reference=True) or []

    if not refs:
        print("No se encontraron referencias en la escena.")
        return

    print("=" * 60)
    print(f"Referencias encontradas: {len(refs)}")
    print("=" * 60)

    replaced = 0
    skipped = 0

    for ref in refs:
        print(f"\n  ORIGINAL:  {ref}")

        if LINUX_ROOT in ref:
            new_path = ref.replace(LINUX_ROOT, WINDOWS_ROOT)
            try:
                ref_node = mc.referenceQuery(ref, referenceNode=True)
                mc.file(new_path, loadReference=ref_node)
                print(f"  NUEVO:     {new_path}")
                print(f"  ESTADO:    OK - Reemplazado")
                replaced += 1
            except Exception as e:
                print(f"  NUEVO:     {new_path}")
                print(f"  ESTADO:    AVISO - {e}")
                replaced += 1
        else:
            print(f"  ESTADO:    Sin cambios")
            skipped += 1

    print("\n" + "=" * 60)
    print(f"Reemplazadas: {replaced} | Sin cambios: {skipped}")
    print("=" * 60)


############################################

def main():

    print("="*70)
    print("STARTING ROUTINE ==============")
    print("="*70)

    # Buscamos los shots en Pending Sup Review
    shots = _search_shots_to_process()

    # Recorremos los shots
    for shot in shots:

        print(f" + Procesando {shot['entity.Shot.code']} ============")
        print(f"\t - shot --> {shot}")

        # Copiamos la escena a work
        print("\t - Copiamos la escena a work...")
        
        paths = _find_shot_paths(shot)
        maya_pt_path = paths["nuboyana"]["maya_scene"]
        maya_work_path = paths["work"]["maya_scene"]

        print(f"\t\t - PATH RECIBIDO DE NUBOYANA --> {maya_pt_path}")
        print(f"\t\t - PATH TARGET WKND --> {maya_work_path}")

        if os.path.exists(maya_work_path):
            continue

        shutil.copy2(maya_pt_path, maya_work_path)
        print(f"\t\t - Escena copiada :)")

        # Abrimos la escena
        print("\t - Abriendo la escena en Maya...")
        mc.file(maya_work_path, open=True, force=True)

        #############
        # DO THINGS #
        #############

        # Cambiamos las refs para que apunten a nuestro server
        print("\t - Cambiando el path de las referencias...")
        repath_references()

        # Cambiamos el archivo OCIO
        print("\t - Cambiamos el archivo OCIO...")
        ocio_file = r"\\192.168.23.2\DataCenter\05Framework\packages\resources\config.ocio"
        mc.colorManagementPrefs(e=True, configFilePath=ocio_file)
        print("\t - OCIO Path actualizado :) ")

        # Guardamos la escena con los paths actualizados
        mc.file(save=True, force=True)
        print("\t - Escena guardada :) ")

        ##################################
        # MOVEMOS LOS RENDERS A SU SITIO #
        ##################################

        print("\t - Copiando Renders... ")

        copy_renders(paths)

    maya.standalone.uninitialize()

############################################

if __name__ == "__main__":
    main()

## USE ##
# "C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe" Z:\05Framework\users\aferraz\wknd_tools\lighting\move_FML_nuboyana.py
