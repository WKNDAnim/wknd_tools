import maya.app.renderSetup.model.renderSetup as rs
import maya.app.renderSetup.model.renderLayer as renderLayer
import maya.app.renderSetup.model.override as override
import maya.cmds as cmds


def createColisionTestRenderLayer():

    # Crear render layer
    renderSetup = rs.instance()
    layer = renderSetup.createRenderLayer("collisionAO")

    # Crear collection con todos los transforms
    col = layer.createCollection("all_transforms")
    col.getSelector().setPattern("ANIM* , SET* , CAMERA*")
    col.getSelector().setFilterType(1)

    # Crear shader aiUtility
    shader = cmds.shadingNode("aiUtility", asShader=True, n ='OcclusionTester')
    cmds.setAttr(shader + ".shadeMode", 3)
    cmds.setAttr(shader + ".colorMode", 21)
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=shader + "SG")
    cmds.connectAttr(shader + ".outColor", sg + ".surfaceShader")

    # Shader override
    so = col.createOverride("shader_override", override.typeIDs.shaderOverride)
    so.setShader(shader)

    # Quitar renderable de masterLayer
    masterLayer = renderSetup.getDefaultRenderLayer()
    masterLayer.setRenderable(False)

    # Activar renderable y visibility en la Layer
    layer = renderSetup.getRenderLayer("collisionAO")
    layer.setRenderable(True)
    renderSetup.switchToLayer(layer)

    # Render globals
    cmds.setAttr("defaultRenderGlobals.imageFilePrefix", "<Scene>/<RenderLayer>/<Scene>_<RenderLayer>", type="string")
    cmds.setAttr("defaultRenderGlobals.animation", True)
    cmds.setAttr("defaultRenderGlobals.outFormatControl", 0)
    cmds.setAttr("defaultRenderGlobals.putFrameBeforeExt", True)
    cmds.setAttr("defaultRenderGlobals.extensionPadding", 4)
    cmds.setAttr("defaultRenderGlobals.startFrame", 1000)
    cmds.setAttr("defaultRenderGlobals.endFrame", cmds.playbackOptions(q=True, maxTime=True) + 1)

    # Formato EXR
    cmds.setAttr("defaultRenderGlobals.imageFormat", 40)  # 40 = EXR
    

    # Arnold EXR settings
    cmds.setAttr("defaultArnoldDriver.exrCompression", 2)  # 2 = zip
    cmds.setAttr("defaultArnoldDriver.halfPrecision", True)
    cmds.setAttr("defaultArnoldDriver.tiled", False)

    # Resolución
    render_scale = 0.5
    width = 2048
    height = 870
    pixel_aspect = 1
    device_aspect = float(width * pixel_aspect) / float(height)

    cmds.setAttr("defaultResolution.width", width*render_scale)
    cmds.setAttr("defaultResolution.height", height*render_scale)
    cmds.setAttr("defaultResolution.pixelAspect", pixel_aspect)
    cmds.setAttr("defaultResolution.deviceAspectRatio", device_aspect)

    # Arnodl settings
    cmds.setAttr("defaultArnoldRenderOptions.AASamples", 3)
    cmds.setAttr("defaultArnoldRenderOptions.GIDiffuseSamples", 0)
    cmds.setAttr("defaultArnoldRenderOptions.GISpecularSamples", 0)
    cmds.setAttr("defaultArnoldRenderOptions.GITransmissionSamples", 0)
    cmds.setAttr("defaultArnoldRenderOptions.GISssSamples", 0)
    cmds.setAttr("defaultArnoldRenderOptions.GIVolumeSamples", 0)
    cmds.setAttr("defaultArnoldRenderOptions.autotx", 0)

    # Borrar el denoiser
    imagers = cmds.ls(type="aiImagerDenoiserOidn")
    for imager in imagers:
        cmds.delete(imager)

    # Skip licence check
    cmds.setAttr("defaultArnoldRenderOptions.skipLicenseCheck", True)


def clear_render_setup_layers():
    renderSetup = rs.instance()
    default_layer = renderSetup.getDefaultRenderLayer()

    try:
        renderSetup.switchToLayer(default_layer)
    except Exception as e:
        print(f"Could not switch to default layer first: {e}")

    for layer in list(renderSetup.getRenderLayers()):
        if layer == default_layer:
            continue

        try:
            name = layer.name()
        except Exception:
            name = str(layer)

        try:
            print(f"Deleting Render Setup layer: {name}")
            renderLayer.delete(layer)
        except Exception as e:
            print(f"Could not delete Render Setup layer {name}: {e}")

    try:
        rs.switchToLayer(default_layer)
    except Exception as e:
        print(f"Could not switch back to default layer: {e}")


# createColisionTestRenderLayer()

# clear_render_setup_layers()
