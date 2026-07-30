import maya.app.renderSetup.model.renderSetup as rs
import maya.app.renderSetup.model.renderLayer as renderLayer
import maya.app.renderSetup.model.override as override
import maya.app.renderSetup.model.utils as utils
import maya.cmds as mc
import mtoa.aovs as aovs
from mtoa.core import createOptions
import mtoa.ui.arnoldmenu as arnoldmenu


OCIO_FILE = r"\\192.168.23.2\DataCenter\05Framework\packages\resources\config.ocio"

######################################
# PUBLIC


def _createRenderLayers():

    renderSetup = rs.instance()

    ######
    # BG #
    ######

    bg_layer = renderSetup.createRenderLayer("BG")

    # Collection
    col = bg_layer.createCollection("Set")
    col.getSelector().setPattern("SET*")
    col.getSelector().setFilterType(1)

    col_lgt = bg_layer.createCollection("Light")
    col_lgt.getSelector().setFilterType(1)

    ########
    # CHAR #
    ########

    char_layer = renderSetup.createRenderLayer("CHAR")

    # Collection
    col = char_layer.createCollection("Char")
    col.getSelector().setPattern("ANIM*")
    col.getSelector().setFilterType(1)

    col_lgt = char_layer.createCollection("Light")
    col_lgt.getSelector().setFilterType(1)

    col_charset = char_layer.createCollection("CharSet")
    shapes_col_charset = col_charset.createCollection("Shapes")
    shapes_col_charset.getSelector().setPattern("*")
    abs_ov = shapes_col_charset.createOverride("aiMatte", override.AbsOverride.kTypeId)
    abs_ov.setAttributeName("aiMatte")
    nodes = mc.ls("SET*", dagObjects=True, shapes=True)
    if nodes:
        plug = mc.ls(nodes[0] + ".aiMatte")[0]
        abs_ov.finalize(plug)
        abs_ov.setAttrValue(True)

    ######
    # SH #
    ######

    sh_layer = renderSetup.createRenderLayer("SH")

    # Collection
    col = sh_layer.createCollection("ShadowCaster")
    col.getSelector().setPattern("ANIM*")
    col.getSelector().setFilterType(1)

    # Collection
    col_geo = sh_layer.createCollection("ShadowsReceiver")

    # Subcollection shapes
    shapes_col = col.createCollection("Shapes")
    shapes_col.getSelector().setPattern("*")
    shapes_col.getSelector().setFilterType(2)

    # Crear AbsOverride
    abs_ov = shapes_col.createOverride("primaryVisibility", override.AbsOverride.kTypeId)
    abs_ov.setAttributeName("primaryVisibility")
    nodes = mc.ls("ANIM*", dagObjects=True, shapes=True)
    if nodes:
        plug = mc.ls(nodes[0] + ".primaryVisibility")[0]
        abs_ov.finalize(plug)
        abs_ov.setAttrValue(False)

    col_lgt = sh_layer.createCollection("Light")
    col_lgt.getSelector().setFilterType(1)

    #########
    # VOLUM #
    #########

    volum_layer = renderSetup.createRenderLayer("VOLUM")

    # Collection SET
    set_col = volum_layer.createCollection("All")
    set_col.getSelector().setPattern("SET*, CHAR*")
    set_col.getSelector().setFilterType(1)

    # Subcollection shapes para aiMatte
    set_shapes = set_col.createCollection("Shapes")
    set_shapes.getSelector().setFilterType(2)
    set_shapes.getSelector().setPattern("*")

    # Crear AbsOverride
    abs_ov = set_shapes.createOverride("aiMatte", override.AbsOverride.kTypeId)
    abs_ov.setAttributeName("aiMatte")
    nodes = mc.ls("SET*", dagObjects=True, shapes=True)
    if nodes:
        plug = mc.ls(nodes[0] + ".aiMatte")[0]
        abs_ov.finalize(plug)
        abs_ov.setAttrValue(True)

    col_lgt = volum_layer.createCollection("Light")
    col_lgt.getSelector().setFilterType(1)


def _createRenderLayersFromJson(path_to_json):

    renderSetup = rs.instance()

    # behavior controla qué hacer si ya existen layers con el mismo nombre
    renderSetup.importAllFromFile(
        path_to_json,
        behavior=1,        # 0=merge, 1=replace — hay que verificar los valores exactos
        prependToName=""   # prefijo opcional para los nombres
    )


def _hideThings():

    keywords = ['muzzlehair', 'eyebrowhair', 'proxy', 'sclera', '_scalp', '_hair', 'eyebrow', 'eyelash']
    avoid = ["groom"]

    all_refs = mc.ls(type='reference')
    for ref_node in all_refs:

        # Miramos solo los que necesitamos
        ref_path = mc.referenceQuery(ref_node, f=True)
        if any(i in ref_path.lower() for i in avoid):
            continue

        # Pedimos los transforms de la
        new_objects = mc.referenceQuery(ref_node, nodes=True)
        new_transforms = mc.ls(new_objects, type='transform', long=True)

        # Hide de los transforms que no necesitamos
        for t in new_transforms:
            if any(kw in t.lower() for kw in keywords):
                mc.setAttr(t + '.v', 0)


def _setRenderSettings():

    createOptions()

    mc.setAttr("defaultRenderGlobals.currentRenderer", "arnold", type="string")
    print("Arnold setted!")

    mc.setAttr("defaultRenderGlobals.imageFilePrefix", "<Scene>/<RenderLayer>/<Scene>_<RenderLayer>", type="string")
    mc.setAttr("defaultRenderGlobals.imageFormat", 40)  # 40 = EXR
    mc.setAttr("defaultArnoldDriver.exrCompression", 3)  # 2 = zips / 3 = zip
    mc.setAttr("defaultArnoldDriver.halfPrecision", True)
    mc.setAttr("defaultArnoldDriver.tiled", False)
    mc.setAttr("defaultArnoldDriver.mergeAOVs", True)
    mc.setAttr("defaultArnoldDriver.multipart", True)
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

    # Formato EXR
    mc.setAttr("defaultRenderGlobals.imageFormat", 40)  # 40 = EXR

    # Arnold EXR settings
    mc.setAttr("defaultArnoldDriver.exrCompression", 2)  # 2 = zips -> 1 scanline, 3 = zip -> 16 scanlines
    mc.setAttr("defaultArnoldDriver.halfPrecision", True)
    mc.setAttr("defaultArnoldDriver.tiled", False)

    # Arnodl settings
    mc.setAttr("defaultArnoldRenderOptions.AASamples", 5)
    mc.setAttr("defaultArnoldRenderOptions.GIDiffuseSamples", 2)
    mc.setAttr("defaultArnoldRenderOptions.GISpecularSamples", 2)
    mc.setAttr("defaultArnoldRenderOptions.GITransmissionSamples", 2)
    mc.setAttr("defaultArnoldRenderOptions.GISssSamples", 2)
    mc.setAttr("defaultArnoldRenderOptions.GIVolumeSamples", 2)

    # Borrar el denoiser
    imagers = mc.ls(type="aiImagerDenoiserOidn")
    for imager in imagers:
        mc.delete(imager)

    # Frame/Animation ext: "name.#.ext" = opción 3
    mc.setAttr("defaultRenderGlobals.animation", 1)
    mc.setAttr("defaultRenderGlobals.outFormatControl", 0)
    mc.setAttr("defaultRenderGlobals.putFrameBeforeExt", 1)  # pone el frame antes de la extensión
    mc.setAttr("defaultRenderGlobals.extensionPadding", 4)   # padding de 4
    mc.setAttr("defaultRenderGlobals.periodInExt", 1)

    # Frame range
    end_frame = mc.playbackOptions(q=True, maxTime=True)
    mc.setAttr("defaultRenderGlobals.startFrame", 1001)
    mc.setAttr("defaultRenderGlobals.endFrame", end_frame)

    # Color Management
    mc.colorManagementPrefs(e=True, configFilePath=OCIO_FILE)

    # Set AOVs
    __set_aovs()


######################################
# PRIVATE

def __set_aovs():

    # First Clean ourshelves
    __clear_all_aovs()

    aov_list = [
        'N',
        'P',
        'albedo',
        'coat',
        'diffuse',
        'direct',
        'emission',
        'indirect',
        'shadow',
        'shadow_matte',
        'sheen',
        'specular',
        'sss',
        'transmission',
        "RGBA"
    ]

    aov_interface = aovs.AOVInterface()
    for aov in aov_list:
        aov_interface.addAOV(aov)

    # Add custom AOVs
    __add_ao_aov()

    __add_cryptos()

    __add_z_driver()


def __add_z_driver():

    aov_interface = aovs.AOVInterface()
    z_aov = aov_interface.addAOV('Z')

    driver = 'defaultArnoldDriver'
    aov_filter = mc.createNode('aiAOVFilter')

    next_plug = mc.getAttr(z_aov.node + '.outputs', size=True)
    mc.connectAttr(driver + '.message', f'{z_aov.node}.outputs[{next_plug}].driver', force=True)
    mc.connectAttr(aov_filter + '.message', f'{z_aov.node}.outputs[{next_plug}].filter', force=True)


def __add_ao_aov():

    aov_interface = aovs.AOVInterface()

    # Crear el AOV
    aov = aov_interface.addAOV('AO')

    # Crear el shader aiAmbientOcclusion
    if not mc.objExists('aiAO_shader'):
        ao_shader = mc.shadingNode('aiAmbientOcclusion', asShader=True, name='aiAO_shader')
    else:
        ao_shader = 'aiAO_shader'

    # Conectar el shader al AOV
    mc.connectAttr(ao_shader + '.outColor', aov.node + '.defaultValue', force=True)


def __add_cryptos():

    aov_interface = aovs.AOVInterface()

    # Crear el AOV
    c_material = aov_interface.addAOV('crypto_material')
    c_asset = aov_interface.addAOV('crypto_object')

    # Creamos en nodo cryptomate
    if not mc.objExists("_aov_cryptomatte"):
        shader = mc.createNode("cryptomatte", n="_aov_cryptomatte")
    else:
        shader = '_aov_cryptomatte'


    # Configurar parámetros del AO
    # mc.setAttr(ao_shader + '.samples', 5)
    # mc.setAttr(ao_shader + '.falloff', 0.0)

    # Conectar el shader al AOV
    mc.connectAttr(shader + '.outColor', c_material.node + '.defaultValue', force=True)
    mc.connectAttr(shader + '.outColor', c_asset.node + '.defaultValue', force=True)


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


def __clear_all_aovs():
    aov_interface = aovs.AOVInterface()
    existing = aov_interface.getAOVs()
    if existing:
        aov_interface.removeAOVs(existing)
