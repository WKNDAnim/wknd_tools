import maya.cmds as cmds


def _reconnect_shaders():
    """ Recorremos todas las shapes de la escena y cargamos su shader"""

    shapes = cmds.ls(exactType="mesh")
    shaders = cmds.ls(exactType="shadingEngine")

    for shape in shapes:
        print(f"- SHAPE ----------- {shape}")
        if not "shapeorig" in shape.lower() and not "scalp" in shape.lower():
            try:
                try:
                    assetName = cmds.getAttr(shape + "." + "GUS_asset_name")
                except:
                    assetName = cmds.getAttr(shape + "." + "GUS_SG_assetName")
            except:
                continue
            try:
                try:
                    shaderName = cmds.getAttr(shape + "." + "GUS_shading_grp")
                except:
                    shaderName = cmds.getAttr(shape + "." + "GUS_relatedShader")
                print(f"- SHADER ----------- {shaderName}")
                try:
                    shaderEngine = [s for s in shaders if shaderName in s and assetName in s][0]
                except:
                    shaderEngine = [s for s in shaders if shaderName in s][0]
                cmds.sets(shape, e=True, forceElement=shaderEngine)
                print(f"'{shaderName}' connected to '{shape}'")
            except Exception as e:
                print(f"ERROR: Cannot connect Shader for Shape {shape}: {e}")
