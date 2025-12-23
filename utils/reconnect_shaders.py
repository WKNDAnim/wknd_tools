import maya.cmds as cmds

def _reconnect_shaders():
    """ Recorremos todas las shapes de la escena y cargamos su shader"""

    shapes = cmds.ls(exactType="mesh")
    shaders = cmds.ls(exactType="shadingEngine")

    for shape in shapes:
        try:
            try:
                shaderName = cmds.getAttr(shape + "." + "GUS_shading_grp")
            except:
                shaderName = cmds.getAttr(shape + "." + "GUS_relatedShader")
            shaderEngine = [s for s in shaders if shaderName in s][0]
            cmds.sets(shape, e=True, forceElement=shaderEngine)
            print(f"'{shaderName}' connected to '{shape}'")
        except Exception as e:
            print(f"ERROR: Cannot connect Shader for Shape {shape}: {e}")
