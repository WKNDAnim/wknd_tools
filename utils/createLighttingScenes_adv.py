import sys
sys.path.insert(0, r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config\install\core\python")
sys.path.insert(0, r"Z:\05Framework\users\aferraz")

import sgtk
import os

from wknd_tools.utils import reconnect_shaders
import imp
imp.reload(reconnect_shaders)


try:
    import maya.standalone
    maya.standalone.initialize(name='python')
except:
    pass


import maya.cmds as mc
mc.loadPlugin("AbcImport")
mc.loadPlugin('mtoa')

#############################################

MAYAPY = r"C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe"
LGT_SETUP = r"Z:\02Proyectos\Gus\resources\lights\white_lights.ma"

#############################################

#######################
# Conectar a ShotGrid #
#######################

tk = sgtk.sgtk_from_path(r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config")
sg = tk.shotgun

#############################################

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
        ["sg_status_list", "is_not", "omt"]
    ]
    query = ["code", "sg_sequence", "sg_status_list"]

    return sg.find("Shot", filters, query)


def _export_camera(camera_path):

    # Seleccionamos el grupo camara
    try:
        mc.select("CAMERA", hi=True)
    except:
        print("ERROR: No existe el grupo CAMERA...")

    mc.file(camera_path, type="mayaAscii", exportSelected=True)


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


def _create_lgt_scene(fields_anm):

    mc.file(new=True)

    fields = fields_anm.copy()
    fields["Step"] = "LGT"
    fields["Task"] = "Lighting"
    fields["Version"] = 1

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
    scene_dir = os.path.dirname(scene_path)
    os.makedirs(scene_dir, exist_ok=True)

    mc.file(rename=scene_path)
    mc.file(save=True, type='mayaAscii', f=True)

    print("----- ESCENA DE LGT VACIA CREADA!")

    template_caches = tk.templates["maya_shot_anim_assets_abc_publish_root"]
    template_anim_cache = tk.templates["maya_shot_anim_assets_abc_publish"]

    cache_root = template_caches.apply_fields(fields_anm)

    for cache in os.listdir(cache_root):

        cache_path = os.path.join(cache_root, cache)
        print(f"LOADING: {cache_path} ========================================")

        load_cache(cache_path)

    # Conectamos los shaders con las geos
    reconnect_shaders._reconnect_shaders()

    # Cargamos el setup de luces
    load_lgt()




def main():

    #
    # Buscamos los shots a procesar #
    #

    seq_name = "sq9200"
    shots = _search_shots_in_seq(seq_name)

    for shot in shots:

        print("-"*50)
        print(shot["code"])
        print("-"*20)

        #
        # Exportamos la camara #
        #

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

        #
        # Creamos la escena de LGT #
        #

        _create_lgt_scene(fields)

        
    create_file()
    load_things()
    save()