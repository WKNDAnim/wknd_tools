import sys
sys.path.insert(0, r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config\install\core\python")
sys.path.insert(0, r"Z:\05Framework\users\aferraz")

import os

# --- Inicializamos Maya standalone ANTES de tocar nada de maya.* ---
try:
    import maya.standalone
    maya.standalone.initialize(name='python')

    import maya.OpenMaya as om

    om.MGlobal.setDisplayWarnings(False)   # oculta "Warning: ..."
    om.MGlobal.setDisplayInfos(False)      # oculta líneas informativas tipo "Read 11 files in..."
    # om.MGlobal.setDisplayErrors(False)   # NO lo actives: oculta errores reales, te interesa verlos
except:
    pass


import maya.cmds as mc

mc.loadPlugin("AbcImport")
mc.loadPlugin('mtoa')

# --- Ahora sí, importamos sgtk y los módulos propios ---
import sgtk

from wknd_tools.utils import reconnect_shaders
from wknd_tools.lighting import helpers
import importlib
importlib.reload(reconnect_shaders)
importlib.reload(helpers)

#############################################

LGT_SETUP = r"Z:\02Proyectos\Gus\resources\lights\white_lights.ma"
ERROR = []

#############################################

#######################
# Conectar a ShotGrid #
#######################

tk = sgtk.sgtk_from_path(r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config")
sg = tk.shotgun

###################################################


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


def _search_shots_in_seq(seq_name):

    filters = [
        ["project", "is", {"type": "Project", "id": 91}],
        ["sg_sequence.Sequence.code", "is", seq_name],
        ["code", "not_contains", "master"],
        ["sg_status_list", "not_in", ["omt", "wtg"]]
    ]
    query = ["code", "sg_sequence", "sg_status_list"]

    return sg.find("Shot", filters, query)


def is_arnes_visible(cache_top):

    b = mc.listRelatives(cache_top, fullPath=True, type="transform")
    c = mc.listRelatives(b, fullPath=True, type="transform")
    x = [i for i in c if "arnes_C_grp" in i]
    if x:
        return mc.getAttr(f"{x[0]}.v")
    else:
        return False


def _export_camera(camera_path):

    # Seleccionamos el grupo camara
    try:
        mc.select("CAMERA", hi=True)
    except:
        print("WARNING: No existe el grupo CAMERA...")

        # Creamos el grupo
        mc.group(n="CAMERA", em=True)

        # Buscamos la camara y la seleccionamos
        cameras = mc.ls(type="camera")
        avoid = ['frontShape', 'perspShape', 'sideShape', 'topShape']

        camera_shape = [cam for cam in cameras if cam not in avoid]  
        camera_transform = mc.listRelatives(camera_shape[0], p=True)[0]
        mc.select(clear=True)
        mc.parent(camera_transform, "CAMERA")

        mc.select("CAMERA", hi=True)

    # Aseguramos que la carpeta de destino existe
    camera_dir = os.path.dirname(camera_path)
    os.makedirs(camera_dir, exist_ok=True)

    try:
        mc.file(camera_path, type="mayaAscii", exportSelected=True, f=True)
    except Exception as e:
        print(f"ERROR: No se ha podido exportar la camara --> {e}")
        return


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
        ref_node_h = mc.file(hair_path, r=True, ns=f"{asset_name}_hair")
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

        ref_node_g = mc.file(groom_paths[0], r=True, ns=f"{asset_name}_groom")  # {copy_n or ''}")

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
        asset_name = False

    print(f"CACHE_FIELDS: {cache_fields}")
    print(f"asset_name: {asset_name}")

    if not asset_name:
        print(f"ERROR: No se ha podido obtener el asset_name de {cache_path}. Saltando cache...")
        return

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

    # Creamos el grupo del ANIM si no existe
    if not transform_exists("ANIM"):
        mc.group(n="ANIM", em=True)

    # PARENT
    mc.parent(asset_name, "ANIM")


def load_lgt():

    ref_node = mc.file(LGT_SETUP, r=True)

    # Creamos el grupo LIGHTS si no existe
    if not transform_exists("LIGHTS"):
        mc.group(n="LIGHTS", em=True)

    new_objects = mc.referenceQuery(ref_node, nodes=True)
    new_transforms = mc.ls(new_objects, type='transform', long=True)
    cache_top = [t for t in new_transforms if not mc.listRelatives(t, parent=True)][0]

    # PARENT
    mc.parent(cache_top, "LIGHTS")


def load_camera(camera_path):

    ref_node = mc.file(camera_path, r=True)


def _create_lgt_scene(fields_anm, camera_path):

    mc.file(new=True, f=True)

    fields = fields_anm.copy()
    fields["Step"] = "LGT"
    fields["Task"] = "Lighting"
    fields["version"] = 1

    template = tk.templates["maya_shot_work"]
    scene_path = template.apply_fields(fields)
    scene_path = scene_path.replace("\\", "/")
    print(f"--------------------------- SCENE LGT --> {scene_path}")

    if os.path.exists(scene_path):
        print("-----------ERROR---------- LA ESCENA DE LGT YA EXISTE!!!")
        ERROR.append(fields["Shot"])
        return

    # Borramos la escena si ya existe
    if os.path.exists(scene_path):
        print("\t\t - WARNING --> La escena ya existe!!")
        os.remove(scene_path)
        print("\t\t - INFO --> Escena eliminada. La volvemos a crear :)")

    # Ensure folders are created
    scene_dir = os.path.dirname(scene_path)
    os.makedirs(scene_dir, exist_ok=True)
    # mc.file(save=True, type='mayaAscii', f=True)

    print("--------------------------- ESCENA DE LGT VACIA CREADA!")

    template_caches = tk.templates["maya_shot_anim_assets_abc_publish_root"]
    template_anim_cache = tk.templates["maya_shot_anim_assets_abc_publish"]

    paths = tk.paths_from_template(template_caches, fields_anm, skip_keys=["version"])
    if not paths:
        ERROR.append(fields["Shot"])
        return
    paths.sort(reverse=True)
    cache_root = paths[0]
    # cache_root = template_caches.apply_fields(fields_anm)

    for cache in os.listdir(cache_root):

        cache_path = os.path.join(cache_root, cache)
        print(f"LOADING: {cache_path} ========================================")

        load_cache(cache_path)

    # Conectamos los shaders con las geos
    reconnect_shaders._reconnect_shaders()

    # Cargamos el setup de luces
    load_lgt()
    print("--------------------------- LUCES CARGADAS")

    # Cargamos la camara
    load_camera(camera_path)
    print("--------------------------- CAMARA CARGADA")

    # Render settings
    helpers._setRenderSettings()

    mc.file(rename=scene_path)
    mc.file(save=True, type='mayaAscii', f=True)


def main():

    #
    # Buscamos los shots a procesar #
    #

    print("------------ BUSCANDO SHOTS")

    seq_name = "sq9200"
    shots = _search_shots_in_seq(seq_name)

    for shot in shots:

        print("\n")
        print("-"*50)
        print(shot["code"])
        print("-"*20)
        print("\n")

        if shot["code"] in ["sq9200_sh0010", "sq9200_sh0020", "sq9200_sh0030", "sq9200_sh0040"]:
            print("----- SKIPPING!")
            continue

        # Buscamos el status de la task de ANM
        anim_task = sg.find_one("Task", [["entity", "is", shot], ["content", "is", "Animation"]], ["sg_status_list"])
        if anim_task["sg_status_list"] != "apr":
            print("----------ERROR--------------- ANIM TASK NO APROBADA AUN")
            continue

        #
        # Exportamos la camara #
        #

        print("------------ EXPORTAMOS CAMARA")

        # Buscamos la escena
        template_work = tk.templates["maya_shot_work"]
        fields_anm = {
            "Step": "ANM",
            "Task": "Animation",
            "name": "scene",
            "Shot": shot["code"],
            "Sequence": shot["sg_sequence"]["name"],
            }

        paths = tk.paths_from_template(template_work, fields_anm)
        paths.sort(reverse=True)
        anim_scene = paths[0]
        print(paths[0])

        fields = template_work.get_fields(anim_scene)
        camera_template = tk.templates["maya_shot_camera_ma_publish"]
        camera_path = camera_template.apply_fields(fields)

        # Abrimos la escena
        mc.file(anim_scene, open=True, f=True)

        # Exportamos
        _export_camera(camera_path)

        if not os.path.exists(camera_path):
            print("ERROR --> No se ha podido exportar la cámara...")
            continue

        #
        # Creamos la escena de LGT #
        #

        print("------------ CREAMOS LA ESCENA DE LGT")

        _create_lgt_scene(fields, camera_path)

        print("------------ DONEEEE ---------------------------")

    print(f"ERRORES --> {ERROR}")


if __name__ == "__main__":
    main()


# USE: "C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe" "Z:\05Framework\users\aferraz\wknd_tools\utils\createLighttingScenes_adv.py"