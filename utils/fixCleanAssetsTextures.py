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
from wknd_tools.core import exporters
import importlib
importlib.reload(json_set)
importlib.reload(exporters)

#######################
# Conectar a ShotGrid #
#######################

tk = sgtk.sgtk_from_path(r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config")
sg = tk.shotgun

#############################################################################


def search_assets():

    assets = sg.find("Asset", 
                     [
                         ["project","is",{"type":"Project", "id":91}],
                         ["sg_asset_type", "not_in", ["DMP", "FX", "SET", "TEST", "LIB", "TEMPLATE"]],
                         ["sg_status_list", "is_not", "omt"],
                         ["sg_asset_type", "in", ["CHM", "CHS", "CHE"]],
                        #  ["code","is","frida"]
                    ],
                    ["code", "sg_asset_type"],
                    order=[{"field_name": "code", "direction": "asc"}]
                    )

    print("="*70)
    print(f"Numero de assets: {len(assets)}")

    template = tk.templates["maya_asset_clean_publish"]

    chosen_paths = {}
    no_proc = []
    for asset in assets:

        if asset["sg_asset_type"] in ["CHM", "CHS", "CHE"]:

            fields = {
                        "Asset": asset["code"],
                        "sg_asset_type": asset["sg_asset_type"],
                        "Step": "GROOM",
                        "Task": "Groom",
                        "name": "scene",
                    }

        else:

            fields = {
                        "Asset": asset["code"],
                        "sg_asset_type": asset["sg_asset_type"],
                        "Step": "SURF",
                        "Task": "Shading",
                        "name": "scene",
                    }

        paths = tk.paths_from_template(template, fields)
        if paths:
            paths.sort(reverse=True)

            chosen_paths[asset["code"]] = paths[0]
        else:
            no_proc.append(asset["code"])

    print(f"Total procesados: {len(chosen_paths)}")

    for i in no_proc:
        print(i)

    print("="*50)

    return chosen_paths


def get_shaders_and_textures(asset_name):

    ############################
    # Get Shaders and Textures #
    ############################

    # Get all shaders and textures from all meshes on geo grp from asset name
    try:
        meshes_in_asset = mc.listRelatives(f"{asset_name}|geo", ad=True, type='mesh', f=True)
    except:
        try:
            meshes_in_asset = mc.listRelatives(f"geo", ad=True, type='mesh', f=True)
        except:
            meshes_in_asset = mc.listRelatives("hair", ad=True, type='xgmSplineDescription', f=True)

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
            mesh_shader[mesh]['textures'] = get_textures_from_shading_groups(shading_engine)

        # Print dict for debug
        import pprint
        print("ACTUAL SHADERS AND TEXTURES -----------------------------------------------")
        pprint.pprint(mesh_shader)
        return mesh_shader


def get_textures_from_shading_groups(shading_groups):
    """
    Busca recursivamente todos los nodos de textura (file, aiImage) 
    conectados a una lista de shading groups.

    Args:
        shading_groups: Lista de shading groups (ej: ['lambert1SG', 'blinn2SG'])

    Returns:
        dict: {node_name: texture_path}

    Example:
        sgs = mc.ls(type='shadingEngine')
        textures = get_textures_from_shading_groups(sgs)
        # {'file1': 'C:/textures/diffuse.png', 'aiImage1': 'C:/textures/normal.exr'}
    """

    texture_nodes = {}
    visited = set()  # Para evitar loops infinitos
    shaders = []

    for sg in shading_groups:

        if not mc.objExists(sg):
            continue

        # Obtener shader conectado al shading group
        shaders = mc.listConnections(f"{sg}.surfaceShader", source=True, destination=False)
        dshader = mc.listConnections(f"{sg}.displacementShader", source=True, destination=False)
        aiShader = mc.listConnections(f"{sg}.aiSurfaceShader", source=True, destination=False)

        if dshader:
            shaders.append(dshader[0])
        if aiShader:
            shaders.append(aiShader[0])

        if not shaders:
            continue

        # Search for textures on Shader
        texture_nodes[sg] = {}

        for shader in shaders:
            # Buscar recursivamente texturas desde el shader
            found_textures = find_texture_nodes_recursive(shader, visited)
            # Añadir al diccionario
            texture_nodes[sg].update(found_textures)

    print(f"✓ Encontradas {len(found_textures)} texturas únicas")

    return texture_nodes[sg]


def find_texture_nodes_recursive(node, visited=None):
    """
    Busca recursivamente nodos de textura (file, aiImage) 
    en toda la red de shading.

    Args:
        node: Nodo desde donde empezar la búsqueda
        visited: Set de nodos ya visitados (para evitar loops)

    Returns:
        dict: {node_name: texture_path}
    """

    if visited is None:
        visited = set()

    # Evitar loops infinitos
    if node in visited:
        return {}

    visited.add(node)

    textures = {}

    # Verificar si el nodo actual es un nodo de textura
    node_type = mc.nodeType(node)

    if node_type == 'file':
        # Nodo file
        texture_path = mc.getAttr(f"{node}.fileTextureName")
        if texture_path:
            textures[node] = texture_path

    elif node_type == 'aiImage':
        # Nodo aiImage
        texture_path = mc.getAttr(f"{node}.filename")
        if texture_path:
            textures[node] = texture_path

    # Buscar en todos los inputs del nodo
    connections = mc.listConnections(node, source=True, destination=False, plugs=False) or []

    for connected_node in connections:
        # Recursión en cada nodo conectado
        found = find_texture_nodes_recursive(connected_node, visited)
        textures.update(found)

    return textures


def main():

    print("="*100)
    print("STARTING ROUTINE ------------------")
    print("="*100)

    assets = search_assets()

    print(assets)

    scene_template = tk.templates["maya_asset_clean_publish"]
    folder_template = tk.templates["texture_folder_publish"]

    bad_assets = []
    unprocessed = []
    errores = []

    for asset_name in assets:

        print(f" ######### PROCESSING --> {asset_name}")

        aux2 = []
        aux = []

        try:

            # Abrimos la escena #############################
            mc.file(new=True)
            mc.file(assets[asset_name], open=True, f=True)

            print("="*50)
            print(f"Asset --> {asset_name}\n")

            fields = scene_template.get_fields(assets[asset_name])
            textures_export_folder = folder_template.apply_fields(fields)

            mesh_shader = get_shaders_and_textures(asset_name)

            for geo in mesh_shader:
                for node in mesh_shader[geo]["textures"]:
                    if not "/publish/textures" in mesh_shader[geo]["textures"][node]:  #"/SURF/Shading/publish/textures"
                        aux.append(mesh_shader[geo]["textures"][node])
                        pprint.pprint(mesh_shader[geo]["textures"][node])

            print(f" PATHS ERRONEOS:\n \t\t - {aux}")

        except:
            aux = False
            unprocessed.append(asset_name)

        if aux:

            bad_assets.append(asset_name)
            texture_work_paths = exporters._export_textures(mesh_shader, textures_export_folder)

            # Guardamos la escena completa
            mc.file(save=True, f=True)

            # Comprobamos que todo bien
            new_textures = get_shaders_and_textures(asset_name)
            print(" - NEW_PATHS in scene shaders --> \n")
            pprint.pprint(new_textures)

            for geo in new_textures:
                for node in mesh_shader[geo]["textures"]:
                    if not "publish/textures" in mesh_shader[geo]["textures"][node]:
                        aux2.append(mesh_shader[geo]["textures"][node])
            if aux2:
                print(f"xxxxxxxxxx ERROR: ESTE ASSET {asset_name} no se ha hecho bien.... xxxxxxxxx")
                print(f"AUX 2 --> {aux2}")
                errores.append(asset_name)
            else:
                print("DONE ...................................................... \n\n")

        else:

            print(" - Este ya estaba bien :) ...................................................... \n\n")

    print("="*100)
    print("FINISH ROUTINE ------------------")
    print("\t - BAD ASSETS:")
    pprint.pprint(bad_assets)
    print("\t - ERRORES:")
    pprint.pprint(errores)
    print("\t - NO PROCESADOS:")
    pprint.pprint(unprocessed)
    print("="*100)


if __name__ == "__main__":
    main()

## USE ##
# "C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe" Z:\05Framework\users\aferraz\wknd_tools\utils\fixCleanAssetsTextures.py
