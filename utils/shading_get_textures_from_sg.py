import maya.cmds as mc
import maya.cmds as cmds


# Get all textures from SG


def get_textures_from_shading_groups(shading_groups):
    """
    Busca recursivamente todos los nodos de textura (file, aiImage) 
    conectados a una lista de shading groups.

    Args:
        shading_groups: Lista de shading groups (ej: ['lambert1SG', 'blinn2SG'])

    Returns:
        dict: {node_name: texture_path}

    Example:
        sgs = cmds.ls(type='shadingEngine')
        textures = get_textures_from_shading_groups(sgs)
        # {'file1': 'C:/textures/diffuse.png', 'aiImage1': 'C:/textures/normal.exr'}
    """

    texture_nodes = {}
    visited = set()  # Para evitar loops infinitos
    shaders = []

    for sg in shading_groups:

        if not cmds.objExists(sg):
            continue

        # Obtener shader conectado al shading group
        shaders = cmds.listConnections(f"{sg}.surfaceShader", source=True, destination=False)
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

    print(f"✓ Encontradas {len(texture_nodes)} texturas únicas")

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
    node_type = cmds.nodeType(node)

    if node_type == 'file':
        # Nodo file
        texture_path = cmds.getAttr(f"{node}.fileTextureName")
        if texture_path:
            textures[node] = texture_path

    elif node_type == 'aiImage':
        # Nodo aiImage
        texture_path = cmds.getAttr(f"{node}.filename")
        if texture_path:
            textures[node] = texture_path

    # Buscar en todos los inputs del nodo
    connections = cmds.listConnections(node, source=True, destination=False, plugs=False) or []

    for connected_node in connections:
        # Recursión en cada nodo conectado
        found = find_texture_nodes_recursive(connected_node, visited)
        textures.update(found)

    return textures

# USAGE
"""
asset_name = 'aceraTest'

meshes_in_asset = mc.listRelatives(f"{asset_name}|geo", ad=True, type='mesh', f=True)

mesh_shader = {}

for mesh in meshes_in_asset:
    shading_engine = mc.listConnections (mesh, source=False, destination=True)
    mesh_shader[mesh] = {}
    mesh_shader[mesh]['shading_engine'] = shading_engine[0]
    mesh_shader[mesh]['textures'] = get_textures_from_shading_groups(shading_engine)
    
import pprint
pprint.pprint(sg_dict)


"""
    