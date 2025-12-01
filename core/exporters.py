import maya.cmds as mc
import maya.mel as mm
import os
import glob
from ..utils import shading_get_textures_from_sg, scene_usd_export_utils
import importlib
importlib.reload(shading_get_textures_from_sg)


def export_maya_scene(file_path, file_type='mayaAscii'):

    """
    Export current Maya scene

    Args:
        file_path (str): Destination path
        file_type (str): 'mayaAscii' or 'mayaBinary'
    """

    # Create directory if needed
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Save scene
    mc.file(rename=file_path)
    mc.file(save=True, type=file_type)

    return file_path


def export_maya_asset(object_to_export, file_path, file_type='mayaAscii'):

    """
    Export current Maya scene

    Args:
        object_to_export (str): geo grp from asset to export as .ma
        file_path (str): Destination path
        file_type (str): 'mayaAscii' or 'mayaBinary'
    """

    # Create directory if needed
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    mc.select(object_to_export, r=1)
    parent = mc.listRelatives(object_to_export, p=1)
    mc.parent(object_to_export, w=1)
    mc.file(file_path, type=file_type, exportSelected=True, force=True)
    if parent:
        mc.parent(mc.ls(sl=1)[0], parent[0])
    mc.select(cl=1)


def export_alembic(object_to_export, file_path, frameIn, frameOut):
    """
    Export geometry as Alembic

    Args:
        file_path (str): Destination path
        selection (bool): Export selected objects only
        frame_range (tuple): (start, end) or None for current frame
    """

    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    if isinstance(object_to_export, list):
        # Get objects to export
        root_str = ' -root '.join(object_to_export)
    else:
        root_str = object_to_export

    # change file_path
    file_path = file_path.replace('\\', '/')

    # Ensure we can use Abc Export
    mc.loadPlugin('AbcExport.mll')
    mc.loadPlugin('AbcImport.mll')

    abc_cmd = f'-root {root_str} -frameRange {str(frameIn)} {str(frameOut)} -noNormals -uvWrite -worldSpace -attrPrefix GUS -attrPrefix ai -attrPrefix lineWidth -dataFormat ogawa -writeVisibility -file "{file_path}"'
    mc.AbcExport(j=abc_cmd)


def export_ass(object_to_export, file_path):
    """
    Export geometry with shaders as ASS

    Args:
        file_path (str): Destination path
        selection (bool): Export selected objects only
    """

    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Change file_path
    file_path = file_path.replace('\\', '/')

    mc.select(object_to_export, r=1)
    line = 'arnoldExportAss -f "' + file_path + '" -s -boundingBox -mask 24 -lightLinks 0 -shadowLinks 0 -fullPath -cam perspShape;'
    mm.eval(line)
    mc.select(cl=1)

def export_shaders_and_textures_for_hair(asset_name, shaders_file_path, textures_export_folder):

    ############################
    # Get Shaders and Textures #
    ############################

    # Get all shaders and textures from all meshes on geo grp from asset name
    hair_in_asset = mc.listRelatives(f"{asset_name}|hair", ad=True, type='xgmSplineDescription', f=True)

    if not hair_in_asset:

        print(f"❌ ERROR: Cannot find {asset_name}|hair group relatives...")
        return False
    
    else:

        mesh_shader = {}
        shaders_list = list()
        for hair in hair_in_asset:
            shading_engine = mc.listConnections(hair, source=False, destination=True,type='shadingEngine')
            if not shading_engine:
                print(f" WARNING: No Shading Engine for {hair}.")
                continue
            mesh_shader[hair] = {}
            mesh_shader[hair]['shading_engine'] = shading_engine[0]
            shaders_list.append(shading_engine[0])
            mesh_shader[hair]['textures'] = shading_get_textures_from_sg.get_textures_from_shading_groups(shading_engine)

        # Print dict for debug
        import pprint
        pprint.pprint(mesh_shader)

    ###################
    # Export textures #
    ###################

    texture_work_paths = _export_textures(mesh_shader, textures_export_folder)

    ##################
    # Export shaders #
    ##################

    shaders_file_path = _export_shaders(shaders_list, shaders_file_path)

    ##############################################
    # RePath texture nodes to original work file #
    ##############################################

    for mesh in texture_work_paths:

        for texture_node in texture_work_paths[mesh]:

            # Change texture path on node for publish
            node_type = mc.nodeType(texture_node)

            if node_type == 'file':
                # Nodo file
                mc.setAttr(f"{texture_node}.fileTextureName", texture_work_paths[mesh][texture_node], type='string')

            elif node_type == 'aiImage':
                # Nodo aiImage
                mc.setAttr(f"{texture_node}.filename", texture_work_paths[mesh][texture_node], type='string')

    return shaders_file_path, mesh_shader


def export_shaders_and_textures(asset_name, shaders_file_path, textures_export_folder):

    ############################
    # Get Shaders and Textures #
    ############################

    # Get all shaders and textures from all meshes on geo grp from asset name
    meshes_in_asset = mc.listRelatives(f"{asset_name}|geo", ad=True, type='mesh', f=True)

    if not meshes_in_asset:

        print(f"❌ ERROR: Cannot find {asset_name}|geo group relatives...")
        return False

    else:

        mesh_shader = {}
        shaders_list = list()
        for mesh in meshes_in_asset:
            shading_engine = mc.listConnections(mesh, source=False, destination=True,type='shadingEngine')
            if not shading_engine:
                print(f" WARNING: No Shading Engine for {mesh}.")
                continue
            mesh_shader[mesh] = {}
            mesh_shader[mesh]['shading_engine'] = shading_engine[0]
            shaders_list.append(shading_engine[0])
            mesh_shader[mesh]['textures'] = shading_get_textures_from_sg.get_textures_from_shading_groups(shading_engine)

        # Print dict for debug
        import pprint
        pprint.pprint(mesh_shader)

    ###################
    # Export textures #
    ###################

    texture_work_paths = _export_textures(mesh_shader, textures_export_folder)

    ##################
    # Export shaders #
    ##################

    shaders_file_path = _export_shaders(shaders_list, shaders_file_path)

    ##############################################
    # RePath texture nodes to original work file #
    ##############################################

    for mesh in texture_work_paths:

        for texture_node in texture_work_paths[mesh]:

            # Change texture path on node for publish
            node_type = mc.nodeType(texture_node)

            if node_type == 'file':
                # Nodo file
                mc.setAttr(f"{texture_node}.fileTextureName", texture_work_paths[mesh][texture_node], type='string')

            elif node_type == 'aiImage':
                # Nodo aiImage
                mc.setAttr(f"{texture_node}.filename", texture_work_paths[mesh][texture_node], type='string')

    return shaders_file_path, mesh_shader


def export_usd(publish_path):

    # Ensure publish folder exists
    publish_folder = os.path.dirname(publish_path)
    if not os.path.exists(publish_folder):
        os.makedirs(publish_folder)

    print(f"Exporting scene to USD: {publish_path}")

    # Configure USD export settings (simplified)
    export_settings = {
        "format": "usda",
        "export_visible_only": True,
        "include_materials": True,
    }

    # try:
    # Perform USD export (simplified - export entire scene)
    success = scene_usd_export_utils.export_scene_to_usd(
        output_path=publish_path,
        settings=export_settings
    )

    if not success:
        print(f"❌ ERROR: Cannot export USD to {publish_path}...")
        return False

    print(f"✓ Successfully exported scene USD to: {publish_path}")

    return True


# PRIVATE ##############################

def _export_textures(mesh_shader, textures_export_folder):

    # Create Textures folder
    if not os.path.exists(textures_export_folder):
        os.makedirs(textures_export_folder)

    import shutil

    texture_work_paths = {}

    for mesh in mesh_shader:

        texture_work_paths[mesh] = {}

        for texture_node in mesh_shader[mesh]['textures']:

            texture_work_path = mesh_shader[mesh]['textures'][texture_node]
            texture_file_name = os.path.basename(texture_work_path)
            texture_export_path = os.path.join(textures_export_folder, texture_file_name)
            texture_export_folder = os.path.dirname(texture_export_path)

            texture_work_path_spt, ext = os.path.splitext(texture_work_path)
            texture_work_path_spt2, seq = os.path.splitext(texture_work_path_spt)

            print(f"✓ TEXTURE WORK PATHHHHHHHHHH ---- {texture_work_path}")

            if seq.startswith("."):
                texture_work_path_aux = ".".join([texture_work_path_spt2, "<udim>", ext[1:]])
            else:
                texture_work_path_aux = texture_work_path

            # Miramos si el path es un pattern de UDIMs
            if "<udim>" in texture_work_path_aux.lower():

                glob_pattern = texture_work_path_aux.lower().replace("<udim>", "????")

                # Busca todos los archivos que coincidan
                udim_files = glob.glob(glob_pattern)

                # Copia cada archivo
                for f in udim_files:
                    shutil.copy(f, texture_export_folder)

            else:

                # Copy texture to publish
                shutil.copyfile(texture_work_path, texture_export_path)

            # Change texture path on node for publish
            node_type = mc.nodeType(texture_node)

            if node_type == 'file':
                # Nodo file
                mc.setAttr(f"{texture_node}.fileTextureName", texture_export_path, type='string')

            elif node_type == 'aiImage':
                # Nodo aiImage
                mc.setAttr(f"{texture_node}.filename", texture_export_path, type='string')

            # Save old texture path to recover it after export
            texture_work_paths[mesh].update({texture_node: texture_work_path})

    return texture_work_paths


def _export_shaders(shaders_list, shaders_file_path):

    # Ensure Shaders folder
    if not os.path.exists(os.path.dirname(shaders_file_path)):
        os.makedirs(os.path.dirname(shaders_file_path))

    mc.select(cl=1)
    mc.select(shaders_list, r=1, ne=1)
    mc.file(rename=shaders_file_path)
    mc.file(op='v=0', force=True, exportSelected=True, type="mayaAscii")

    return shaders_file_path
