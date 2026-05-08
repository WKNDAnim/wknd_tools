import sys
sys.path.insert(0, r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config\install\core\python")
sys.path.insert(0, r"Z:\05Framework\users\aferraz")

import sgtk
import os
import shutil
import tempfile
import subprocess
import re

try:
    import maya.standalone
    maya.standalone.initialize(name='python')
except:
    pass

import maya.cmds as mc
mc.loadPlugin("AbcImport")

import wknd_tools
from wknd_tools.utils import json_set, createColissionRenderLayer, reconnect_shaders
from wknd_tools.flay import fix_escuelaExt
import importlib
importlib.reload(json_set)
importlib.reload(createColissionRenderLayer)
importlib.reload(reconnect_shaders)
importlib.reload(fix_escuelaExt)

DEADLINECOMMAND = r"C:\Program Files\Thinkbox\Deadline10\bin\deadlinecommand.exe"
MAYAPY = r"C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe"
RENDER_QT_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(__file__)), r"utils\render_qt_and_publish.py")

#######################
# Conectar a ShotGrid #
#######################

tk = sgtk.sgtk_from_path(r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config")
sg = tk.shotgun

##################################################


def error(msg):

    print(msg, flush=True)
    sys.exit(1)

####################################


def _search_shots_in_seq(seq_name):
    """ Dado el nombre de una secuencia, buscamos en SG sus shots que no estén omitidos """

    filters = [
        ["project", "is", {"type": "Project", "id": 91}],
        ["sg_sequence.Sequence.code", "is", seq_name],
        ["code", "not_contains", "master"],
        ["sg_status_list", "is_not", "omt"]
    ]
    query = ["code", "sg_sequence", "sg_status_list", "sg_auto_flay"]

    return sg.find("Shot", filters, query)


def _search_published_files(shot):
    """ Buscamos el SET y la cache folder en SG """

    shot_name = shot["code"]

    # Search for published files
    fields = [
        ["entity.Shot.code", "is", shot_name],
        ["published_file_type.PublishedFileType.code", "in", ["Anim Cache Folder", "JSON Set"]],
        ]
    queries = [
        "code", "published_file_type.PublishedFileType.code", "version_number", "path"
        ]
    published_files = sg.find("PublishedFile", fields, queries, order=[{"field_name": "version_number", "direction": "desc"}])

    if not published_files:
        error(f"ERROR: No published files found! Neither CACHES or JSON files for SHOT - {shot_name}")
        return

    # JSON #########################
    jsons = [i for i in published_files if i['published_file_type.PublishedFileType.code']=="JSON Set"]
    if not jsons:
        error("ERROR: No JSON path found...")
        return False

    set_path = jsons[0]["path"]["local_path"]

    # CACHE PATH #########################
    caches = [i for i in published_files if i['published_file_type.PublishedFileType.code']=="Anim Cache Folder"]
    if not caches:
        print("WARNING: No Anim Cache folder path found... --> Comprobamos que este Shot no necesita Animacion...")
        anim_task = sg.find_one("Task", [["entity", "is", shot], ["content", "is", "Animation"]], ["sg_status_list"])
        print(f"\t - Anim Task: {anim_task}")

        # Si el estatus es NA, devolvemos False para las caches
        if anim_task["sg_status_list"] != "na":
            error("ERROR: No hay CACHES de ANIM publicadas y este Shot las necesita.")
        else:
            print("INFO: This shot do not apply for Animation!")
            return set_path, "na"

    anim_cache_folder = caches[0]["path"]["local_path"]

    # Get cache files from folder
    anim_cache_files = [os.path.join(anim_cache_folder, file) for file in os.listdir(anim_cache_folder) if os.path.join(anim_cache_folder, file).endswith("abc")]
    anim_cache_files = [cache for cache in anim_cache_files if "_hair_" not in cache] # Filtramos los HAIR, los cargamos después

    if not anim_cache_files:

        error(" ERROR: NO ANIM CACHE FILES.")

    return set_path, anim_cache_files


def _create_scenes(shot, create_flay=True):

    """
    Creamos la escena de lighting cargando el BG del JSON, las caches de ANIM y la cámara.

        - create_flay --> Crea también la escena de Final Layout y lanza un Job de Render a Deadline

        """

    fields_lgt = {
        "Step": "LGT",
        "Task": "Lighting",
        "name": "scene",
        "Shot": shot["code"],
        "Sequence": shot["sg_sequence"]["name"],
        "version": 1
        }

    # Create the scene and save it
    print("\t - Creando escena de Lighting...")

    scene_path_lgt = _new_scene(shot, fields_lgt)

    print(f"\t - Escena creada --> {scene_path_lgt}")

    # Buscamos las caches de anim
    print("\t - Buscando SET y CACHES")

    set_path, anim_cache_files = _search_published_files(shot)

    print(f"\t - SET --> {set_path}")
    print(f"\t - CACHES --> {anim_cache_files}")

    ########################
    # Load assets to scene #
    ########################

    #######
    # SET #
    #######

    print("\t - Importando JSON SET...")

    json_set.createShotFromJson(set_path)

    print("\t - JSON SET importado ")
    print("="*70)
    print("="*70)

    #########
    # FIXES #
    #########

    print("- Miramos si hacen falta Fixes....")

    # Fix escuelaExt
    escuelaExt = {'id': 1866, 'name': 'escuelaExt', 'type': 'Asset'}

    sg_shot = sg.find_one("Shot", [["code", "is", shot["code"]]], ["parent_shots"])
    print("SG SHOT:")
    print(sg_shot)

    parent_shots = sg.find_one("Shot", [["code", "is", sg_shot["parent_shots"][0]["name"]]], ["assets"])
    print("PARENT SHOTS:")
    print(parent_shots)

    if escuelaExt in parent_shots["assets"]:

        print("\t - Contiene EscuelaExt ----------------------------------------")
        fix_escuelaExt.fix_arbustos_vallas()
        print("\t\t - Añadimos Arbustos y Vallas")
        fix_escuelaExt.fix_cesped()
        print("\t\t - Añadimos Cesped")

    # Fix Descampado
    descampado = {'id': 2017, 'name': 'descampado', 'type': 'Asset'}

    if descampado in parent_shots["assets"]:

        print("\t - Contiene Descampado ----------------------------------------")

        path_tendido_electrico = rf'Z:\02Proyectos\Gus\sequences\{shot["code"].split("_")[0]}\{shot["code"]}\ANM\Animation\publish\caches\_extras\{shot["code"]}_redElectrica.abc'

        print(f"\t\t - path_tendido_electrico --> {path_tendido_electrico}")

        if os.path.exists(path_tendido_electrico):

            # Cargamos la GEO
            print("\t\t - Cargamos la GEO...")
            if not is_file_referenced(path_tendido_electrico):
                ref_node = mc.file(path_tendido_electrico, r=True)
            else:
                ref_node = mc.referenceQuery(path_tendido_electrico, rfn=True)

            # Buscamos el top node
            print("\t\t - Buscamos el top node")
            top_nodes = mc.referenceQuery(path_tendido_electrico, nodes=True, dagPath=True)
            cache_top = mc.ls(top_nodes, assemblies=True, long=True)[0]
            print(f"cache_top --> {cache_top}")

            asset_name = "redElectrica_abc"

            # Creamos el grupo del ASSET_NAME si no existe
            if not transform_exists(asset_name):
                mc.group(n=asset_name, em=True)

            mc.parent(cache_top, asset_name)
            mc.parent(asset_name, "SET")

            # Cargamos sus shaders
            load_shaders("cable")
            load_shaders("tendidoElectrico")

            # Escondemos el Tendido Eléctrico que viene con el JSON
            mc.setAttr('tendidoElectrico.v', 0)

    print("- Fin Fixes....")

    ########
    # ANIM #
    ########

    if anim_cache_files and anim_cache_files != "na":

        print("\t - Importando ANIM CACHES...")
        print("="*70)
        for i in anim_cache_files:
            print(i)
        print("="*30)

        # Creamos el grupo del ANIM si no existe
        if not transform_exists("ANIM"):
            mc.group(n="ANIM", em=True)

        for cache_path in anim_cache_files:

            load_cache(cache_path)

        print("\t - ANIM CACHES importadas ")

    #####################
    # RECONNECT SHADERS #
    #####################

    print("\t - Reconectando shaders...")

    reconnect_shaders._reconnect_shaders()

    print("\t - Shaders conectados! ")

    # Guardamos la escena completa
    mc.file(save=True, f=True)

    print("\t - Escena guardada!!")

    ##########
    # CAMARA #
    ##########

    print("\t - Importando CAMARA...")

    template_camera = tk.templates["maya_shot_camera_abc_publish"]
    fields_camera = fields_lgt.copy()
    fields_camera.pop("version")
    fields_camera.pop("name")
    try:
        fields_camera.pop("maya_extension")
    except:
        pass
    fields_camera["Step"] = "LAY"
    fields_camera["Task"] = "Layout"

    camera_paths = tk.paths_from_template(template_camera, fields_camera)
    camera_paths.sort(reverse=True)

    print(f"CAMERA PATHS --> {camera_paths}")

    ref_node = mc.file(camera_paths[0], r=True)
    camera_group = mc.group(n="CAMERA", em=True)

    # ref_node = mc.referenceQuery(camera_paths[0])
    new_objects = mc.referenceQuery(ref_node, nodes=True)
    new_transforms = mc.ls(new_objects, type='transform', long=True)
    camera_top = [t for t in new_transforms if not mc.listRelatives(t, parent=True)][0]

    mc.parent(camera_top, camera_group)

    print(f"\t - CAMARA importada --> |CAMERA{camera_top} ")

    ##############
    # SET RENDER #
    ##############

    # FRAME RANGE

    print("\t - Seteando FRAME RANGE...")

    filters_shot = [
        ["code", "is", shot["code"]],
        ]
    queries_shot = ["sg_cut_duration", "sg_cut_in", "sg_cut_out"]
    shot_info = sg.find_one("Shot", filters_shot, queries_shot)

    mc.playbackOptions(minTime=shot_info["sg_cut_in"], maxTime=shot_info["sg_cut_out"], animationStartTime=shot_info["sg_cut_in"], animationEndTime=shot_info["sg_cut_out"])

    print("\t - FRAME RANGE seteado ")

    # RENDER SETTINGS
    print("\t - RENDER Settings... ")

    _set_render_settings()

    print("\t - RENDER Settings Done ")

    #############
    # SAVE FILE #
    #############

    mc.file(save=True, type='mayaAscii')

    print("** Escena Final de LGT guardada!")

    #####################################
    # Copiamos la escena a Final Layout #
    #####################################

    if create_flay:

        print("- Copiando escena a FINAL LAYOUT...")

        # Get Final Lay path
        lay_fields = fields_lgt.copy()
        lay_fields["Task"] = "FLay"
        lay_fields["Step"] = "FLAY"

        # Query FLAY task
        filters_task = [
            ["entity.Shot.code", "is", shot["code"]],
            ["step.Step.code", "is", "Final Layout"],
            ["content", "is", lay_fields["Task"]],
            ]
        queries_task = ["entity.Shot.id"]
        task_flay = sg.find_one("Task", filters_task, queries_task)

        # Resolve template
        template = tk.templates["maya_shot_work"]
        final_flay_path = template.apply_fields(lay_fields)

        # Ensure folders are created
        tk.create_filesystem_structure("Task", task_flay["id"])

        if not os.path.exists(os.path.dirname(final_flay_path)):
            os.makedirs(os.path.dirname(final_flay_path))

        shutil.copy2(scene_path_lgt, final_flay_path)

        print("** FINAL LAYOUT escena creada!")

        # Seteamos el render
        print("- Seteando render...")
        _set_flay_render(final_flay_path)
        print("- Render Layers setted! ")

        ######################
        # Lanzamos el render #
        ######################

        print("- Lanzando el job a Deadline...")

        # Get Output path
        render_template = tk.templates["maya_shot_render_root"]
        render_root_path = render_template.apply_fields(lay_fields)

        print(f"\t - Render OUT root: {render_root_path}")

        duration = (shot_info['sg_cut_out'] + 1) - (shot_info['sg_cut_in'] - 1) + 1
        workers = 5
        threshold = 50
        chunk = duration if duration < threshold else int(round(duration/workers + .5))  # Le sumamos 0.5 para que siempre redondee hacia arriba

        print(f"\t - Submitting Render Job to Deadline...")

        result = submit_render_and_post_job(
            post_script_path=RENDER_QT_SCRIPT,
            shot_name=shot['code'],
            scene_path=final_flay_path,
            frames=f"{shot_info['sg_cut_in']-1}-{shot_info['sg_cut_out']+1}",
            maya_version="2026",
            pool="none",
            group="none",
            priority=50,
            chunk_size=chunk,
            camera=f"|CAMERA{camera_top}",
            renderer="arnold",
            output_path=render_root_path,
            version=lay_fields["version"]
        )

        # print(result["render_job_id"])
        # print(result["post_job_id"])

        print("- Job lanzado ")

        # Cambiamos el status de la task FLAY a IP
        sg.update(
            "Task",
            task_flay["id"],
            {"sg_status_list": "ip"}
            )

        print("- Task updated! :) ")

        # Chek de AUTO FLAY en el Shot
        sg.update(
            "Shot",
            task_flay["entity.Shot.id"],
            {"sg_auto_flay": True}
            )

        print("- Shot updated! :) ")

        return final_flay_path


def _set_flay_render(final_lay_path):

    # Abrimos la escena
    mc.file(final_lay_path, open=True, f=True)

    # Creamos la Colission Layer
    createColissionRenderLayer.createColisionTestRenderLayer()

    mc.file(save=True, f=True)


def _set_render_settings():

    from mtoa.core import createOptions
    createOptions()

    mc.setAttr("defaultRenderGlobals.currentRenderer", "arnold", type="string")
    print("Arnold setted!")

    mc.setAttr("defaultRenderGlobals.imageFilePrefix", "<Scene>/<RenderLayer>/<Scene>_<RenderLayer>", type="string")
    mc.setAttr("defaultRenderGlobals.imageFormat", 40)  # 40 = EXR
    mc.setAttr("defaultArnoldDriver.exrCompression", 2)  # 2 = zips / 3 = zip
    mc.setAttr("defaultArnoldDriver.halfPrecision", True)
    mc.setAttr("defaultArnoldDriver.tiled", False)
    mc.setAttr("defaultArnoldDriver.mergeAOVs", True)
    print("Arnold settings done")

    # Hacemos que no se renderice PERSP
    mc.setAttr("perspShape.renderable", 0)
    print("PERSP cam not renderable")

    width = 2048
    height = 870
    pixel_aspect = 1
    device_aspect = float(width * pixel_aspect) / float(height)

    mc.setAttr("defaultResolution.width", width)
    mc.setAttr("defaultResolution.height", height)
    mc.setAttr("defaultResolution.pixelAspect", pixel_aspect)
    mc.setAttr("defaultResolution.deviceAspectRatio", device_aspect)
    print("Resolution setted!")

    # Arnold Settings
    mc.setAttr("defaultArnoldRenderOptions.autotx", 0)
    mc.setAttr("defaultArnoldRenderOptions.textureMaxMemoryMB", 24096)

    _clear_imagers()
    print("Imagers cleared")


def _clear_imagers():

    plug = "defaultArnoldRenderOptions.imagers"

    if not mc.objExists(plug):
        print("No existe el atributo imagers")
        return

    connections = mc.listConnections(plug, plugs=True, connections=True) or []

    # connections viene como pares [src, dst, src, dst...]
    for i in range(0, len(connections), 2):
        dst = connections[i]
        src = connections[i + 1]

        try:
            mc.disconnectAttr(src, dst)
            print(f"Disconnected: {src} -> {dst}")
        except Exception as e:
            print(f"Error desconectando {src}: {e}")

    print("Imagers limpiados.")


def _new_scene(shot, fields):

    mc.file(new=True)

    # Nos aseguramos que las carpetas existen #
    # Query task
    filters_task = [
        ["entity.Shot.code", "is", shot["code"]],
        ["step.Step.code", "is", "Light"],
        ["content", "is", fields["Task"]],
        ]
    queries_task = []
    task_lgt = sg.find_one("Task", filters_task, queries_task)

    # Resolve template
    template = tk.templates["maya_shot_work"]
    scene_path = template.apply_fields(fields)
    scene_path = scene_path.replace("\\", "/")
    print(f"\t\t - SCENE LGT --> {scene_path}")

    # Borramos la escena si ya existe
    if os.path.exists(scene_path):
        print("\t\t - WARNING --> La escena ya existe!!")
        os.remove(scene_path)
        print("\t\t - INFO --> Escena eliminada. La volvemos a crear :)")

    # Ensure folders are created
    tk.create_filesystem_structure("Task", task_lgt["id"])
    scene_dir = os.path.dirname(scene_path)
    os.makedirs(scene_dir, exist_ok=True)

    mc.file(rename=scene_path)
    mc.file(save=True, type='mayaAscii', f=True)

    return scene_path


def submit_deadline_job(job_info_lines, plugin_info_lines):
    with tempfile.TemporaryDirectory() as tmpdir:
        job_info_path = os.path.join(tmpdir, "job_info.job")
        plugin_info_path = os.path.join(tmpdir, "plugin_info.job")

        with open(job_info_path, "w", encoding="utf-8") as f:
            f.write("\n".join(job_info_lines))

        with open(plugin_info_path, "w", encoding="utf-8") as f:
            f.write("\n".join(plugin_info_lines))

        result = subprocess.run(
            [DEADLINECOMMAND, job_info_path, plugin_info_path],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Error enviando job a Deadline.\n"
                f"STDOUT:\n{result.stdout}\n\n"
                f"STDERR:\n{result.stderr}"
            )

        match = re.search(r"JobID=([a-fA-F0-9]+)", result.stdout)
        if not match:
            raise RuntimeError(
                "No se pudo extraer el JobID de la respuesta de Deadline.\n"
                f"STDOUT:\n{result.stdout}"
            )

        return match.group(1), result.stdout


def submit_mayabatch_render_job(
    scene_path: str,
    job_name: str,
    frames: str,
    maya_version: str = "2026",
    pool: str = "none",
    group: str = "none",
    priority: int = 50,
    chunk_size: int = 1,
    camera: str = "",
    render_layer: str = "",
    renderer: str = "arnold",
    output_path: str = "",
    project_path: str = "",
    batch_name: str = "",
) -> str:
    """
    Envía un job MayaBatch a Deadline.

    Parámetros mínimos:
        scene_path
        job_name
        frames
        deadlinecommand

    Devuelve el stdout de deadlinecommand.
    Lanza excepción si falla la sumisión.
    """

    if not os.path.exists(DEADLINECOMMAND):
        raise FileNotFoundError(f"No existe deadlinecommand: {DEADLINECOMMAND}")

    if not os.path.exists(scene_path):
        raise FileNotFoundError(f"No existe la escena: {scene_path}")

    job_info_lines = [
        "Plugin=MayaBatch",
        f"Name={job_name}",
        f"Frames={frames}",
        f"ChunkSize={chunk_size}",
        f"Pool={pool}",
        f"Group={group}",
        f"Priority={priority}",
    ]

    if batch_name:
        job_info_lines.append(f"BatchName={batch_name}")

    plugin_info_lines = [
        f"SceneFile={scene_path}",
        f"Version={maya_version}",
        f"Renderer={renderer}",
        "StrictErrorChecking=0"
    ]

    if camera:
        plugin_info_lines.append(f"Camera={camera}")

    if render_layer:
        plugin_info_lines.append("UsingRenderLayers=1")
        plugin_info_lines.append(f"RenderLayer={render_layer}")

    if output_path:
        plugin_info_lines.append(f"OutputFilePath={output_path}")

    if project_path:
        plugin_info_lines.append(f"ProjectPath={project_path}")

    return submit_deadline_job(job_info_lines, plugin_info_lines)


def submit_post_job(
    script_path: str,
    shot_name: str,
    dependency_job_id: str,
    pool: str = "none",
    group: str = "none",
    priority: int = 60,
    batch_name: str = "",
    job_name="Render_QT",
    version=1,
    description="Publish from auto FLAY to review",
    auto=True,
    sg_version=False
):

    if not os.path.exists(MAYAPY):
        raise FileNotFoundError(f"No existe python_exe: {MAYAPY}")

    if not os.path.exists(script_path):
        raise FileNotFoundError(f"No existe script_path: {script_path}")

    job_info_lines = [
        "Plugin=CommandLine",
        f"Name={job_name}",
        "Comment=Quicktime + ShotGrid publish",
        f"Pool={pool}",
        f"Group={group}",
        f"Priority={priority}",
        "Frames=0",
        "ChunkSize=1",
        f"JobDependencies={dependency_job_id}",
    ]

    if batch_name:
        job_info_lines.append(f"BatchName={batch_name}")

    plugin_info_lines = [
        f"Executable={MAYAPY}",
        f'Arguments="{script_path}" --shot "{shot_name}" --version "{version}" --description "{description}" --auto "{auto}" --sg_version "{sg_version}"'.strip(),
    ]

    return submit_deadline_job(job_info_lines, plugin_info_lines)


def submit_render_and_post_job(
    post_script_path: str,
    shot_name: str,
    scene_path: str,
    frames: str,
    maya_version: str = "2026",
    pool: str = "none",
    group: str = "none",
    priority: int = 50,
    chunk_size: int = 1,
    camera: str = "",
    render_layer: str = "",
    renderer: str = "arnold",
    output_path: str = "",
    project_path: str = "",
    version=1,
    description="Publish from auto FLAY to review",
    auto=True,
    sg_version=False
):
    batch_name = f"{shot_name}_FLAY_Render"

    render_job_id, render_stdout = submit_mayabatch_render_job(
        scene_path=scene_path,
        job_name=f"{shot_name}_FLAY_v{version:03d}",
        frames=frames,
        maya_version=maya_version,
        pool=pool,
        group=group,
        priority=priority,
        chunk_size=chunk_size,
        camera=camera,
        # render_layer=render_layer,
        renderer=renderer,
        output_path=output_path,
        # project_path=project_path,
        batch_name=batch_name,
    )

    post_job_id, post_stdout = submit_post_job(
        script_path=post_script_path,
        shot_name=shot_name,
        dependency_job_id=render_job_id,
        pool=pool,
        group=group,
        priority=priority + 1,
        batch_name=batch_name,
        job_name=f"RenderQT_{shot_name}_v{version:03d}",
        version=version,
        description=description,
        auto=auto,
        sg_version=sg_version
    )

    return {
        "render_job_id": render_job_id,
        "render_stdout": render_stdout,
        "post_job_id": post_job_id,
        "post_stdout": post_stdout,
    }


def transform_exists(node):

    if not mc.objExists(node):
        return False

    try:
        return mc.nodeType(node) == "transform"
    except:
        return False


def is_file_referenced(file_path):

    file_path = os.path.normpath(file_path)

    refs = mc.file(q=True, reference=True) or []

    for ref in refs:
        ref_norm = os.path.normpath(ref)
        if ref_norm == file_path:
            return True

    return False


def is_arnes_visible(cache_top):

    b = mc.listRelatives(cache_top, fullPath=True, type="transform")
    c = mc.listRelatives(b, fullPath=True, type="transform")
    x = [i for i in c if "arnes_C_grp" in i]
    if x:
        return mc.getAttr(f"{x[0]}.v")
    else:
        return False


def load_shaders(asset_name):

    template_shader = tk.templates["maya_asset_shader_publish"]

    print("\t\t- Buscando shader...")

    shader_fields = {
        "Asset": asset_name,
        "Step": "SURF",
        "Task": "Shading",
        "name": "scene"
        }
    shader_paths = tk.paths_from_template(template_shader, shader_fields)
    shader_paths.sort(reverse=True)

    if not is_file_referenced(shader_paths[0]):
        mc.file(shader_paths[0], r=True)
        print(f"\t\t\t - Referenciamos el shader: {shader_paths[0]}")
    else:
        print("\t\t\t - El Shader ya está en la escena.")


def load_ch_from_geo(cache_top, asset_name, cache_fields):

    template_hair_cache = tk.templates["maya_shot_anim_assets_abc_hair_publish"]
    template_groom = tk.templates["maya_asset_clean_publish"]

    ########
    # HAIR #
    ########

    try:
        hair_path = template_hair_cache.apply_fields(cache_fields)
    except:
        hair_path = False

    print(f"HAIR PATHHHHH --> {hair_path} =================")

    if os.path.exists(hair_path):

        # CARGAMOS LA GEO DEL HAIR

        ref_node_h = mc.file(hair_path, r=True)
        new_objects_h = mc.referenceQuery(ref_node_h, nodes=True)
        new_transforms_h = mc.ls(new_objects_h, type='transform', long=True)
        hair_shapes = mc.ls(new_objects_h, type='mesh')
        cache_top_h = [t for t in new_transforms_h if not mc.listRelatives(t, parent=True)][0]

        print("\t\t- Geo de HAIR cargada :)")

        # CARGAMOS GROOM

        print("\t\t- Buscando pelo...")

        # Miramos si el arnes está visible
        print("\t\t\t- Miramos si el arnes está visible...")

        arnes = is_arnes_visible(cache_top)

        print(f"\t\t\t\t-ARNES VISIBLE --> {arnes}")

        groom_fields = {
            "Asset": asset_name,
            "Step": "GROOM",
            "Task": "Groom",
            "name": "arnes" if arnes else "scene"
            }

        groom_paths = tk.paths_from_template(template_groom, groom_fields)
        groom_paths.sort(reverse=True)

        print(groom_paths)

        ref_node_g = mc.file(groom_paths[0], r=True, ns=f"{asset_name}")  # {copy_n or ''}")

        print("\t\t- Pelo referenciado")

        # ref_node = mc.referenceQuery(groom_paths[0])
        new_objects_g = mc.referenceQuery(ref_node_g, nodes=True)
        new_transforms_g = mc.ls(new_objects_g, type='transform', long=True)
        groom_shapes = mc.ls(new_objects_g, type='mesh') #, long=True)
        cache_top_g = [t for t in new_transforms_g if not mc.listRelatives(t, parent=True)][0]

        # Hide de las meshes que no necesitamos
        for t in mc.listRelatives(cache_top_g , ad=1, c=1, type='mesh'):
            parent = mc.listRelatives(t, p=1)[0]
            mc.setAttr(parent + '.v', 0)

        print(f"\t\t\t- HAIR SHAPE --> {hair_shapes[0]}")
        print(f"\t\t\t- GROOM SHAPE --> {groom_shapes[0]}")

        # # Si hay ARNES, conectamos al shapeOrig
        # if arnes:
        #     groom_shape = [s for s in groom_shapes if "orig" in s.lower()]
        #     groom_shape = groom_shape[0]
        # else:
        #     groom_shape = groom_shapes[0]

        # Conectamos el out_mesh del hair al in_mesh del groom
        mc.connectAttr(f"{hair_shapes[0]}.outMesh", f"{groom_shapes[0]}.inMesh")

        print("\t\t- Pelo conectado a su geo!")

        # Emparentamos al grupo del asset
        mc.parent(cache_top_h, asset_name)
        mc.parent(cache_top_g, asset_name)


def load_cache(cache_path):

    print(f"LOADING: {cache_path} ========================================")

    template_anim_cache = tk.templates["maya_shot_anim_assets_abc_publish"]

    #######
    # GEO #
    #######

    # Cargamos la GEO
    if not is_file_referenced(cache_path):
        ref_node = mc.file(cache_path, r=True)
    else:
        ref_node = mc.referenceQuery(cache_path, rfn=True)

    # Sacamos los fields de la cache
    try:
        cache_fields = template_anim_cache.get_fields(cache_path)
        asset_name = cache_fields["Asset"]
    except:
        cache_fields = False

    print(f"CACHE_FIELDS: {cache_fields}")
    print(f"asset_name: {asset_name}")

    new_objects = mc.referenceQuery(ref_node, nodes=True)
    new_transforms = mc.ls(new_objects, type='transform', long=True)
    cache_top = [t for t in new_transforms if not mc.listRelatives(t, parent=True)][0]

    # Hide de los transforms que no necesitamos
    for t in mc.listRelatives(cache_top, ad=1, c=1, type='transform'):
        if 'hair' in t.lower() or 'proxy' in t.lower():
            mc.setAttr(t + '.v', 0)

    # Creamos el grupo del ASSET_NAME si no existe
    if not transform_exists(asset_name):
        mc.group(n=asset_name, em=True)

    ###########
    # SHADERS #
    ###########

    # First, try to remove old refs
    for ref_node in mc.ls(type="reference") or []:
        try:
            ref_path = mc.referenceQuery(ref_node, filename=True)
            if "shaders" in ref_path and f"{asset_name}_" in ref_path:
                print(f"{ref_node} --> {ref_path}")
                mc.file(removeReference=True, referenceNode=ref_node)
        except RuntimeError:
            continue

    # Load Shaders
    load_shaders(asset_name)

    ########
    # HAIR #
    ########

    load_ch_from_geo(cache_top, asset_name, cache_fields)

    # PARENT
    mc.parent(cache_top, asset_name)

    # PARENT
    mc.parent(asset_name, "ANIM")


######################################

def main():
    if len(sys.argv) < 2:
        raise RuntimeError("No se ha recibido el nombre de la secuencia")

    sequence_name = sys.argv[1]
    print(f"Secuencia recibida: {sequence_name}")

    # Recorremos la seq y enviamos los jobs
    print("Buscando shots en la sequence...")
    shots = _search_shots_in_seq(sequence_name)

    print(f"Shots a procesar --> {shots}")

    total = len(shots)

    # for shot in shots:
    for i, shot in enumerate(shots, start=1):
        print(f"[INFO] Procesando {shot['code']} -----------------", flush=True)
        print(shot)

        if shot["sg_auto_flay"]:
            print(f"*********** EL SHOT {shot['code']} ya ha sido procesado antes!! SKIP...")
            continue
        try:
            _create_scenes(shot, create_flay=True)
        except:
            print(f"ERROR: No se ha podido procesar el SHOT {shot['code']}")

        print("**** SHOT DONE!")
        progress = int((i / total) * 100)
        print(f"Progress: {progress}%", flush=True)

######################################


if __name__ == "__main__":
    main()
