import maya.cmds as mc
import os
from mtoa.core import createStandIn


def _add_hierba_to_cesped():

    porcion_cesped_parent = 'porcionCesped'
    porciones_cesped = mc.listRelatives(porcion_cesped_parent, children=True, type="transform")

    n = 1
    for porcion_cesped in porciones_cesped:

        group_name = f"porcionCesped{n:02d}"

        mc.group(n=group_name, em=True)

        target_translate = mc.xform(porcion_cesped, q=1, t=1)  #, ws=1)
        target_rotate = mc.xform(porcion_cesped, q=1, ro=1)

        porcion_cesped_hierba_path = r"Z:\02Proyectos\Gus\assets\PRP\porcionCesped\SURF\Shading\publish\maya\ass\hierba_v001.ass"

        node = createStandIn()
        mc.setAttr(node + '.dso', porcion_cesped_hierba_path, type='string')

        parent = mc.listRelatives(node, p=1)[0]
        root = mc.rename(parent, "porcionCespedHierba_STD")

        mc.xform(root, t=target_translate, ws=1)
        mc.xform(root, ro=target_rotate)

        mc.select(cl=1)

        # PARENT
        mc.parent(porcion_cesped, group_name)
        mc.parent(root, group_name)

        mc.parent(group_name, porcion_cesped_parent)

        n +=1


def reload_all_references(verbose=True):
    """
    Recarga todas las referencias de la escena.
    
    Args:
        verbose (bool): Si True, imprime el estado de cada referencia en el Script Editor.
    
    Returns:
        dict: Resultado con listas de referencias recargadas y con errores.
    """
    resultado = {
        "recargadas": [],
        "errores": [],
        "omitidas": []
    }

    # Obtener todos los nodos de referencia (excluye la referencia compartida interna)
    referencias = mc.ls(type="reference")

    if not referencias:
        mc.warning("No se encontraron referencias en la escena.")
        return resultado

    if verbose:
        print("\n" + "=" * 50)
        print(f"  Recargando {len(referencias)} referencia(s)...")
        print("=" * 50)

    for ref_node in referencias:
        # Saltar la referencia interna de Maya (_UNKNOWN_REF_NODE_ o sharedReferenceNode)
        try:
            ref_path = mc.referenceQuery(ref_node, filename=True)
        except RuntimeError:
            if verbose:
                print(f"  [OMITIDA]  {ref_node} (referencia interna de Maya)")
            resultado["omitidas"].append(ref_node)
            continue

        try:
            # Recargar la referencia
            mc.file(ref_path, loadReference=ref_node)
            if verbose:
                print(f"  [OK]       {ref_node}  ->  {ref_path}")
            resultado["recargadas"].append(ref_node)

        except Exception as e:
            if verbose:
                print(f"  [ERROR]    {ref_node}  ->  {e}")
            resultado["errores"].append((ref_node, str(e)))

    if verbose:
        print("=" * 50)
        print(f"  Completado: {len(resultado['recargadas'])} OK | "
              f"{len(resultado['errores'])} errores | "
              f"{len(resultado['omitidas'])} omitidas")
        print("=" * 50 + "\n")

    return resultado


def _ref_to_standin(elem):

    ass_root = rf"Z:\02Proyectos\Gus\assets\ELEM\{elem}\SURF\Shading\publish\ass"
    asses = os.listdir(ass_root)
    asses.sort(reverse=True)
    ass_path = os.path.join(ass_root, asses[0])

    # 1. Recoger transforms
    try:
        children = mc.listRelatives(f"|SET|{elem}", children=True, fullPath=True, type="transform") or []
        mc.referenceQuery(children[0], filename=True)
    except:
        return False

    transforms = []
    for child in children:
        t = mc.xform(child, query=True, translation=True, worldSpace=True)
        r = mc.xform(child, query=True, rotation=True, worldSpace=True)
        s = mc.xform(child, query=True, scale=True, worldSpace=True)
        transforms.append({'t': t, 'r': r, 's': s})

    # 2. Crear standin y replicar transforms
    node = createStandIn()
    mc.setAttr(node + '.mode', 3)
    mc.setAttr(node + '.dso', ass_path, type='string')
    standIn = mc.listRelatives(node, parent=True)[0]
    standIn = mc.rename(standIn, 'pino_std')

    for i, data in enumerate(transforms):
        if i == 0:
            mc.xform(standIn, t=data['t'], ro=data['r'], s=data['s'], ws=True)
            mc.parent(standIn, elem)
        else:
            instance = mc.instance(standIn)[0]
            mc.xform(instance, t=data['t'], ro=data['r'], s=data['s'], ws=True)
            mc.parent(instance, elem)

    # Delete instances and reference
    mc.delete(children)

    for i in children:
        try:
            ref = mc.referenceQuery(children[0], filename=True)
        except:
            pass
        mc.file(ref, removeReference=True)
