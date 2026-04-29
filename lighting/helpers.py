import maya.app.renderSetup.model.renderSetup as rs
import maya.app.renderSetup.model.renderLayer as renderLayer
import maya.app.renderSetup.model.override as override
import maya.cmds as mc
import mtoa.aovs as aovs
from mtoa.core import createOptions
import mtoa.ui.arnoldmenu as arnoldmenu


def _createRenderLayers():

    # Crear render layer
    renderSetup = rs.instance()
    layer = renderSetup.createRenderLayer("collisionAO")


def _hideThings():

    all_refs = mc.ls(type='reference')

    for ref_node in all_refs:

        objects = mc.referenceQuery(ref_node, nodes=True)
        transforms = mc.ls(objects, type='transform', long=True)
        cache_top = [t for t in transforms if not mc.listRelatives(t, parent=True)][0]

        # Hide de los transforms que no necesitamos
        for t in transforms:  #mc.listRelatives(cache_top, ad=1, c=1, type='transform'):
            if 'hair' in t.lower() or 'proxy' in t.lower() or "sclera" in t.lower():
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
    mc.setAttr("defaultArnoldDriver.exrCompression", 3)  # 2 = zip
    mc.setAttr("defaultArnoldDriver.halfPrecision", True)
    mc.setAttr("defaultArnoldDriver.tiled", False)

    # Arnodl settings
    mc.setAttr("defaultArnoldRenderOptions.AASamples", 3)
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

    # Set AOVs
    _set_aovs()


def _set_aovs():

    # First Clean ourshelves
    __clear_all_aovs()

    aov_list = [
        'N',
        'P',
        'Z',
        'albedo',
        'coat',
        # 'crypto_material',
        # 'crypto_object',
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
    ]

    aov_interface = aovs.AOVInterface()
    for aov in aov_list:
        aov_interface.addAOV(aov)

    # Add custom AOVs
    __add_ao_aov()

    __add_cryptos()

    # __add_z_driver

    # # Refresh UI de Arnold
    # try:
    #     arnoldmenu.arnoldMenuUpdate()
    # except:
    #     pass


def __add_z_driver():

    aov_interface = aovs.AOVInterface()
    z_aov = aov_interface.addAOV('Z')

    driver = mc.createNode('aiAOVDriver', name='aiAOVDriver_Z')
    mc.setAttr(driver + '.prefix', 'Z_pass', type='string')
    mc.setAttr(driver + '.halfPrecision', 0)
    mc.setAttr(driver + '.mergeAOVs', 0)

    # Conexión correcta usando outputs.driver
    next_plug = mc.getAttr(z_aov.node + '.outputs', size=True)
    mc.connectAttr(driver + '.message', f'{z_aov.node}.outputs[{next_plug}].driver', force=True)


def __add_ao_aov():

    aov_interface = aovs.AOVInterface()

    # Crear el AOV
    aov = aov_interface.addAOV('AO')

    # Crear el shader aiAmbientOcclusion
    if not mc.objExists('aiAO_shader'):
        ao_shader = mc.shadingNode('aiAmbientOcclusion', asShader=True, name='aiAO_shader')
    else:
        ao_shader = mc.select('aiAO_shader')

    # Conectar el shader al AOV
    mc.connectAttr(ao_shader + '.outColor', aov.node + '.defaultValue', force=True)


def __add_cryptos():

    aov_interface = aovs.AOVInterface()

    # Crear el AOV
    c_material = aov_interface.addAOV('crypto_material')
    c_asset = aov_interface.addAOV('crypto_asset')

    # Creamos en nodo cryptomate
    if not mc.objExists("_aov_cryptomatte"):
        shader = mc.createNode("cryptomatte", n="_aov_cryptomatte")
    else:
        shader = mc.select('_aov_cryptomatte')


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
