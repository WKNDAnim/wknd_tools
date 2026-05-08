import maya.cmds as mc
import os
import json


def get_reference_top_node(ref_node):
    """Obtiene el transform top level de una referencia."""
    try:
        # Obtener todos los nodos de la referencia
        ref_contents = mc.referenceQuery(ref_node, nodes=True, dagPath=True)

        # Filtrar solo transforms
        transforms = [n for n in ref_contents if mc.nodeType(n) == 'transform']

        # Buscar el transform que NO tiene parent (o su parent no es parte de la referencia)
        for t in transforms:
            parent = mc.listRelatives(t, parent=True, fullPath=True)
            if not parent or parent[0] not in ref_contents:
                return t

        # Si no encontramos uno, devolver el primero
        if transforms:
            return transforms[0]

    except Exception as e:
        print(f"Error obteniendo top node de {ref_node}: {str(e)}")

    return None


def get_all_reference_instances(ref_node): 
    """
    Obtiene todas las instancias de una referencia (incluido el original).
    Actualizado para manejar jerarquías con nodos padre no-referenciados.
    """
    try:
        top_node = get_reference_top_node(ref_node)
    except:
        return []

    if not top_node:
        return []

    # Obtener la shape de este transform
    shapes = mc.listRelatives(top_node, shapes=True, fullPath=True)
    if not shapes:
        # Si no tiene shapes directamente, buscar en hijos
        all_shapes = mc.listRelatives(top_node, allDescendents=True, type='mesh', fullPath=True)
        if all_shapes:
            shapes = [all_shapes[0]]

    if not shapes:
        return [top_node]  # No hay shapes, devolver solo el transform

    # Obtener todos los top-level parents de esta shape
    all_parents = mc.listRelatives(shapes[0], allParents=True, fullPath=True) or []

    # Subir al top level de cada parent, pero SOLO dentro de la referencia
    top_parents = []
    for parent in all_parents:
        current = parent
        while True:
            p = mc.listRelatives(current, parent=True, fullPath=True)
            if not p:
                # No hay más padres, este es el top
                top_parents.append(current)
                break

            parent_node = p[0]
            # Verificar si el padre pertenece a la misma referencia
            try:
                parent_ref = mc.referenceQuery(parent_node, referenceNode=True)
                if parent_ref == ref_node:
                    # El padre sigue siendo de nuestra referencia, seguir subiendo
                    current = parent_node
                else:
                    # El padre es de otra referencia, detenerse aquí
                    top_parents.append(current)
                    break
            except:
                # El padre no es referenciado, detenerse aquí
                top_parents.append(current)
                break

    # Eliminar duplicados manteniendo el orden
    top_parents = list(dict.fromkeys(top_parents))

    return top_parents if len(top_parents) > 0 else [top_node]


def change_MDL_references_to_SURF():

    all_refs = mc.ls(type='reference')
    print(all_refs)
    for ref in all_refs:
        # Hacemos un try por si hay un foster parent o algo asi, que daria error
        try:
            filename = mc.referenceQuery(ref, filename=True)
        except:
            filename = False

        if filename:
            if 'MDL' in filename and not "camerarig" in filename.lower():
                print("="*50)
                print(filename)
                surf_file = get_last_shading_reference(ref)
                print(f" ***** Changing to --> {surf_file}")
                mc.file(surf_file, loadReference=ref)


def get_last_shading_reference(reference_node):

    file_name = mc.referenceQuery(reference_node, filename=True)
    asset_name = file_name.split('/')[5]

    print(f"asset_name --> {asset_name}")

    if "ELEM" in file_name:
        surface_folder = 'Z:/02Proyectos/gus/assets/ELEM/' + asset_name + '/SURF/Shading/publish/caches/'
    elif "PRP" in file_name:
        surface_folder = 'Z:/02Proyectos/gus/assets/PRP/' + asset_name + '/SURF/Shading/publish/caches/'

    print(f"surface_folder --> {surface_folder}")

    surface_file = sorted(os.listdir(surface_folder))[-1]
    surface_file_path = os.path.join(surface_folder , surface_file)
    return surface_file_path


# Get elements from  scene
def getAllElements():

    print("\t\t - Getting All Elements...")

    # First, change all existing MDL for SURF
    change_MDL_references_to_SURF()

    all_refs = mc.ls(exactType='reference')
    elem_dict = dict()

    for node in all_refs:

        try:
            file_name = mc.referenceQuery(node, filename=True)
        except:
            file_name = False

        if file_name:
            if 'Shading' or 'Model' in file_name:
                if not 'scene_shaders' in file_name:
                    if not 'Rig' in file_name:

                        asset_name = os.path.basename(file_name).split('_')[0]

                        print("="*70)
                        print(asset_name)

                        if not asset_name in elem_dict.keys():

                            elem_dict[asset_name] = dict()
                            elem_dict[asset_name]['node'] = node
                            elem_dict[asset_name]['file'] = file_name
                            elem_dict[asset_name]['transforms'] = []

                            shader_file = file_name.replace('scene_Shading', 'scene_shaders').replace('caches', 'maya/shaders').replace('.abc', '.ma')
                            if 'scene_shaders' in shader_file:
                                elem_dict[asset_name]['shader_file'] = shader_file
                            else:
                                elem_dict[asset_name]['shader_file'] = ''

                        all_inst = ''
                        try:
                            all_inst = get_all_reference_instances(node)

                            # print("- ALL INST:")
                            # print(all_inst)

                            # elem_dict[asset_name]['transforms'] = []

                            for obj in all_inst:

                                t = mc.xform(obj, q=True, t=True, ws=True)
                                r = mc.xform(obj, q=True, ro=True, ws=True)
                                s = mc.xform(obj, q=True, s=True, r=True)

                                # Harcodeamos un par de fixes para el descampado
                                if "descampado" in obj:
                                    
                                    if "carretera" in obj:
                                        s = [1.52, 1.52, 1.52]
                                    if "fabrica" in obj:
                                        s = mc.xform(obj, q=True, s=True, ws=True)

                                # Miramos si la escala está a 0 para no poner eso en la escena
                                if all(i < 0.0000001 for i in s):
                                    continue

                                elem_dict[asset_name]['transforms'].append({'obj': obj, 't': t, 'r': r, 's': s})

                                # print("ADDEEEEEED :)")

                        except:
                            pass

    return elem_dict


# WRITE JSON
def writeElemDictToJson(elem_dict, json_path):

    with open(json_path, 'w') as f:
        json.dump(elem_dict, f, indent=2)


def changeAbcToCleanAsset(elem_dict):

    vegetation_list = [
        'platanera',
        'arbusto',
        'arbustoAlto',
        'plataneraNaranja',
        'plataneraAmarilla',
        'plataneraVerdeOscuro',
        'plataneraPequena',
        'arbustoFloresAmarillas'
        ]

    noCleanAsset = []
    noAss = []

    for elem in elem_dict:

        ref_file = elem_dict[elem]['file']
        ref_node = elem_dict[elem]['node']
        shader_file = elem_dict[elem]['shader_file']
        directory = os.path.dirname(ref_file)

        if elem in vegetation_list:

            new_directory = directory.replace('caches', 'ass')

            if os.path.exists(new_directory):
                files = sorted([f for f in os.listdir(new_directory) if f.endswith('.ass')])
                if files:
                    new_file = os.path.join(new_directory, files[-1])

            else:
                noAss.append(elem)
                continue

            mc.file(referenceNode=ref_node, removeReference=True)

            if os.path.exists(shader_file):
                mc.file(shader_file, removeReference=True)

            from mtoa.core import createStandIn
            node = createStandIn()
            mc.setAttr(node + '.mode', 3)
            standIn = mc.listRelatives(node, parent=1)[0]

            mc.setAttr(node + '.dso', new_file , type='string')
            standIn = mc.rename(standIn, elem + '_std')

            new_group = mc.group(n=elem, em=True)

            for i, data in enumerate(elem_dict[elem]['transforms']):
                if i == 0:
                    mc.xform(standIn, t=data['t'], ro=data['r'], s=data['s'], ws=True)
                else:
                    instance = mc.instance(standIn)[0]
                    mc.xform(instance, t=data['t'], ro=data['r'], s=data['s'], ws=True)
                    mc.parent(instance, new_group)

            try:
                mc.parent(standIn, new_group)
                mc.parent(new_group, 'SET')
            except:
                pass

        else:

            blacklist = ['bloque01', 'conoGimnasio']
            whitelist = ['carretera']
            if not elem in blacklist:

                if 'caches' in directory:
                    new_directory = directory.replace('caches', 'maya/assets')
                else:
                    if 'Model' in directory:
                        new_directory = directory.replace('MDL/Model/publish/maya', 'SURF/Shading/publish/maya/assets')
                    else:
                        new_directory = directory.replace('maya', 'maya/assets')

                if os.path.exists(new_directory):
                    files = sorted([f for f in os.listdir(new_directory) if f.endswith('.ma')])
                    if files:
                        new_file = os.path.join(new_directory, files[-1])
                    else:
                        noCleanAsset.append(elem)
                        continue

                else:
                    noCleanAsset.append(elem)
                    continue

                mc.file(referenceNode=ref_node, removeReference = True)

                if os.path.exists(shader_file):
                    mc.file(shader_file, removeReference = True)

                mc.file(new_file, r=True)
                ref_node = mc.referenceQuery(new_file, referenceNode=True)
                new_objects = mc.referenceQuery(ref_node, nodes=True)
                new_transforms = mc.ls(new_objects, type='transform', long=True)
                new_top = [t for t in new_transforms if not mc.listRelatives(t, parent=True)][0]

                new_group = mc.group(n=elem, em=True)

                for i, data in enumerate(elem_dict[elem]['transforms']):
                    if i == 0:
                        mc.xform(new_top, t=data['t'], ro=data['r'], s=data['s'], ws=True)
                    else:
                        instance = mc.instance(new_top)[0]
                        mc.xform(instance, t=data['t'], ro=data['r'], s=data['s'], ws=True)
                        mc.parent(instance , new_group)                

                try:
                    mc.parent(new_top , new_group)
                    mc.parent(new_group , 'SET')

                except:
                    pass

    print('No Clean Assets')
    print(noCleanAsset)
    print('No Asses')
    print(noAss)


# READ FROM JSON
def createShotFromJson(json_path):

    with open(json_path, 'r') as f:
        elem_dict = json.load(f)

    vegetation_list = [
        'platanera',
        'arbusto',
        'arbustoAlto',
        'plataneraNaranja',
        'plataneraAmarilla',
        'plataneraVerdeOscuro',
        'plataneraPequena',
        'arbustoFloresAmarillas',
        'bloque01'
        ]

    noCleanAsset = []
    noAss = []

    set_group = mc.group(n="SET", em=True)

    for elem in elem_dict:

        ref_file = elem_dict[elem]['file']
        ref_node = elem_dict[elem]['node']
        shader_file = elem_dict[elem]['shader_file']
        directory = os.path.dirname(ref_file)

        if elem in vegetation_list:

            new_directory = directory.replace('caches', 'ass')

            if os.path.exists(new_directory):
                files = sorted([f for f in os.listdir(new_directory) if f.endswith('.ass')])
                if files:
                    new_file = os.path.join(new_directory, files[-1])

            else:
                noAss.append(elem)
                continue

            from mtoa.core import createStandIn
            node = createStandIn()
            mc.setAttr(node + '.mode', 3)
            standIn = mc.listRelatives(node, parent=1)[0]

            mc.setAttr(node + '.dso', new_file, type='string')
            standIn = mc.rename(standIn, elem + '_std')

            new_group = mc.group(n=elem, em=True)

            for i, data in enumerate(elem_dict[elem]['transforms']):
                if i == 0:
                    mc.xform(standIn, t=data['t'], ro=data['r'], s=data['s'], ws=True)
                else:
                    instance = mc.instance(standIn)[0]
                    mc.xform(instance, t=data['t'], ro=data['r'], s=data['s'], ws=True)
                    mc.parent(instance, new_group)

            try:
                mc.parent(standIn, new_group)
                mc.parent(new_group, 'SET')
            except:
                pass

        else:

            blacklist = []
            whitelist = ['bloque02']
            if not elem in blacklist:

                if 'caches' in directory:
                    new_directory = directory.replace('caches', 'maya/assets')
                else:
                    if 'Model' in directory:
                        new_directory = directory.replace('MDL/Model/publish/maya', 'SURF/Shading/publish/maya/assets')
                    else:
                        new_directory = directory.replace('maya', 'maya/assets')

                if os.path.exists(new_directory):
                    files = sorted([f for f in os.listdir(new_directory) if f.endswith('.ma')])
                    if files:
                        new_file = os.path.join(new_directory, files[-1])
                    else:
                        noCleanAsset.append(elem)
                        continue

                else:
                    noCleanAsset.append(elem)
                    continue

                mc.file(new_file, r=True)

                ref_node = mc.referenceQuery(new_file, referenceNode=True)

                new_objects = mc.referenceQuery(ref_node, nodes=True)
                new_transforms = mc.ls(new_objects, type='transform', long=True)
                new_top = [t for t in new_transforms if not mc.listRelatives(t, parent=True)][0]

                new_group = mc.group(n=elem, em=True)

                print(new_top)

                for i, data in enumerate(elem_dict[elem]['transforms']):
                    if i == 0:
                        mc.xform(new_top, t=data['t'], ro=data['r'], s=data['s'], ws=True)

                    else:
                        instance = mc.instance(new_top)[0]
                        mc.xform(instance, t=data['t'], ro=data['r'], s=data['s'], ws=True)
                        mc.parent(instance, new_group)

                try:
                    mc.parent(new_top, new_group)
                    mc.parent(new_group, set_group)
                except:
                    pass

    print('No Clean Assets')
    print(noCleanAsset)
    print('No Asses')
    print(noAss)


# USE ###############################################################

# # Get elements from scene
# elem_dict = getAllElements()

# # Get JSON path
# json_path = 'C:/Users/cpuigdollers/Documents/testShotJson.json'

# ---------------

# # WRITE JSON
# writeElemDictToJson(elem_dict , json_path)

# ---------------

# # READ FROM JSON
# createShotFromJson(json_path)
