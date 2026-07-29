import maya.cmds as mc
import maya.mel as mm
import os
from mtoa.core import createStandIn
from . import crowds


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
    children = mc.listRelatives(f"|SET|{elem}", children=True, fullPath=True, type="transform") or []

    ref_path = None
    for child in children:
        if mc.referenceQuery(child, isNodeReferenced=True):
            ref_path = mc.referenceQuery(child, filename=True)
            print(ref_path)
            break

    if not ref_path:
        raise RuntimeError(f"No se encontró ninguna referencia entre los hijos de {elem}")

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


def add_hierba(location):

    accepted_locations = [
        "descampadoSuelo",
        "parqueSuelo",
        "escuelaExtSuelo",
    ]
    if location not in accepted_locations:
        print(f"⚠️⚠️⚠️ WARNING --> No podemos importar la hierba. La location - {location} - no es aceptada...")
        return False

    publish_path = rf"Z:\02Proyectos\Gus\assets\ELEM\{location}\SURF\Shading\publish\maya"

    files = os.listdir(publish_path)
    files = [f for f in files if "hierba" in f]
    files.sort(reverse=True)
    path = os.path.join(publish_path, files[0])

    # Miramos que no este ya en la escena
    refs = mc.file(q=True, reference=True)
    if path in refs:
        print(f"⚠️⚠️⚠️ WARNING --> LA hierba para - {location} - ya está en la escena")
        return False

    return mc.file(path, r=True, returnNewNodes=True)


def add_hierba_auto():

    accepted_locations = [
        "descampadoSuelo",
        "parqueSuelo",
        "escuelaExtSuelo",
    ]

    refs = mc.file(q=True, reference=True)
    print("- Buscando en las referencias de la escena...")
    for ref_path in refs:
        for location in accepted_locations:
            if location in ref_path:
                print(f"- Referenciando hierba para {location}...")
                new_nodes = add_hierba(location)
                if new_nodes:
                    top_nodes = mc.ls(new_nodes, assemblies=True)
                    mc.parent(top_nodes, "SET")
                    mc.select(top_nodes)


def createWrap(source, target):
    mc.select(source, r=1)
    mc.select(target, add=1)
    wrapNode = mm.eval('doWrapArgList "7" { "1", "1", "1", "2", "1", "1", "0", "0" };')
    baseGeo = mc.listConnections(f'{wrapNode[0]}.basePoints[0]')
    return baseGeo[0]


def create_wrap(driver, driven, exclusive_bind=True, auto_weight_threshold=True,
                 falloff_mode=0, max_distance=1.0, weight_threshold=0.0):

    # CreateWrap necesita la selección: primero el/los driven, luego el driver
    mc.select(driven, replace=True)
    mc.select(driver, add=True)

    mm.eval("CreateWrap;")

    # Buscamos el wrap recién creado en la history del driven
    history = mc.listHistory(driven)
    wrap_node = mc.ls(history, type="wrap")[0]

    # Ajustamos las opciones por nombre de atributo (fiable, documentado)
    mc.setAttr(f"{wrap_node}.exclusiveBind", exclusive_bind)
    mc.setAttr(f"{wrap_node}.autoWeightThreshold", auto_weight_threshold)
    mc.setAttr(f"{wrap_node}.falloffMode", falloff_mode)
    mc.setAttr(f"{wrap_node}.maxDistance", max_distance)
    mc.setAttr(f"{wrap_node}.weightThreshold", weight_threshold)

    return wrap_node


def _fix_hombre03():

    asset="hombre03"
    surf_path = r"Z:\02Proyectos\Gus\assets\CHE\hombre03\SURF\Shading\publish\maya\hombre03_scene_Shading_v005.ma"

    mc.file(surf_path, r=True, ns=asset)

    meshes = mc.ls(f"{asset}:*", type="mesh")

    for mesh in meshes:
        attr = mc.getAttr(f"{mesh}.GUS_shading_grp")
        print(f"{mesh} --> {attr}")
        mc.setAttr(f"{mesh.split(':')[-1]}.GUS_relatedShader", attr, type="string")

    mc.file(surf_path, removeReference=True)


def acabar_extras():

    from wknd_tools.utils import reconnect_shaders
    import imp
    imp.reload(reconnect_shaders)

    # Buscamos el nombre del crowd
    file_path = mc.file(q=True, sn=True)
    print(file_path)
    crowd_name = os.path.basename(file_path).split("_")[0]

    # Buscamos qué Asset es
    meshes = mc.ls(type="mesh")
    asset_name = mc.getAttr(f"{meshes[0]}.GUS_SG_assetName")
    print(asset_name)

    if asset_name == "hombre03":
        _fix_hombre03()

    # Importamos sus shaders
    shader_root = rf"Z:\02Proyectos\Gus\assets\CHE\{asset_name}\SURF\Shading\publish\maya\shaders"
    shaders = os.listdir(shader_root)
    shaders.sort(reverse=True)
    shader_path = os.path.join(shader_root, shaders[0])
    print(shader_path)
    mc.file(shader_path, i=True)

    # Reconectamos los shaders
    reconnect_shaders._reconnect_shaders()

    # Importamos el groom
    groom_root = rf"Z:\02Proyectos\Gus\assets\CHE\{asset_name}\GROOM\Groom\publish\maya\assets"
    groom = os.listdir(groom_root)
    groom.sort(reverse=True)
    groom_path = os.path.join(groom_root, groom[0])
    print(groom_path)

    nuevos_nodos = mc.file(groom_path, i=True, returnNewNodes=True)

    top_nodes = mc.ls(nuevos_nodos, assemblies=True, long=True)
    if top_nodes:
        grupo = mc.parent(top_nodes,f"{crowd_name}_crowds")
        print(f"Nodos agrupados en: {grupo}")
    else:
        print("No se encontraron nodos de nivel superior para agrupar")

    # Hacemos el wrap del scalp
    driver = "body_C_msh"
    driven = "bodyScalp_C_msh"

    create_wrap(driver, driven)
    # createWrap(source, target)

    # Unos pocos render settings
    mc.setAttr("defaultArnoldRenderOptions.autotx", 0)
    mc.setAttr("defaultArnoldRenderOptions.textureMaxMemoryMB", 24096)

    # mc.setAttr("defaultResolution.width", 540)
    # mc.setAttr("defaultResolution.height", 960)
    # mc.setAttr("defaultResolution.pixelAspect", 1)

    import mtoa.utils as mutils

    skydome = mutils.createLocator("aiSkyDomeLight", asLight=True)

    mc.confirmDialog(m="DONE :)")


def import_crowds_ui():

    folder_path = r"Z:\02Proyectos\Gus\assets\CHE\crowds\MDL\Model\publish\maya"

    win_name = "importMaFilesWin"
    if mc.window(win_name, exists=True):
        mc.deleteUI(win_name)

    window = mc.window(win_name, title="Importar Crowds", widthHeight=(350, 400), sizeable=True)

    mc.columnLayout(adjustableColumn=True, rowSpacing=5, columnAttach=("both", 10))
    mc.text(label=f"Carpeta: {folder_path}", align="left", wordWrap=True)
    mc.separator(height=10, style="in")

    file_list = mc.textScrollList(allowMultiSelection=False, height=280)

    # Listamos solo los .ma de la carpeta
    if os.path.isdir(folder_path):
        ma_files = sorted([f for f in os.listdir(folder_path) if f.lower().endswith(".ma")], reverse=True)
        for f in ma_files:
            mc.textScrollList(file_list, edit=True, append=f)
    else:
        mc.text(label="⚠ La carpeta no existe", align="left")

    mc.separator(height=10, style="in")

    def do_import(*args):
        selected = mc.textScrollList(file_list, query=True, selectItem=True)
        if not selected:
            mc.warning("Selecciona un archivo antes de importar.")
            return

        # Primero hacemos el fix de las gradas
        try:
            crowds._fixGradas()
        except:
            mc.warning("[WARNING] --> No existen las gradas en la escena")

        # Importamos
        file_path = os.path.join(folder_path, selected[0])
        nuevos_nodos = mc.file(file_path, i=True, returnNewNodes=True)
        top_nodes = mc.ls(nuevos_nodos, assemblies=True, long=True)

        print(f"Importado: {file_path}")
        if top_nodes:
            print(f"Nodos de nivel superior: {top_nodes}")

        mc.deleteUI(window)

    mc.button(label="Importar", height=35, command=do_import)

    mc.showWindow(window)
