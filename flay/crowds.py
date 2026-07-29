import maya.cmds as cmds
import maya.cmds as mc
import os

# Variable con la carpeta a usar
carpeta = r"Z:\02Proyectos\Gus\assets\CHE\crowds\MDL\Model\publish\maya\animations"


def _fixGradas():

    mc.setAttr("gradasEscuela_scene_cleanAsset_Shading_v012_gradasEscuela5.v", 0)
    mc.setAttr("gradasEscuela_scene_cleanAsset_Shading_v012_gradasEscuela6.v", 0)

    mc.xform("escalerasGradas_scene_cleanAsset_Shading_v003_escalerasGradas", t=[4575.000, 0.000, 2135.132], ws=1)
    mc.xform("escalerasGradas_scene_cleanAsset_Shading_v003_escalerasGradas1", t=[4575.000, 0.000, 2011.132], ws=1)


def cargar_animacion(anim_path):

    sel = mc.ls(sl=1)[0]
    name = ":" + sel.split(":")[0]
    skeleton = sel.split(":")[0] + ":skeleton"
    current_pos = mc.xform(skeleton, q=1, t=1, ws=1)
    mc.namespace(set=name)

    cmds.file(anim_path,
              i=True,
              type="FBX",
              ignoreVersion=False,
              renameAll=True,
              mergeNamespacesOnClash=False,
              namespace="",
              preserveReferences=True)  # importTimeRange="combine"

    mc.xform(skeleton, t=current_pos, ws=1)
    mc.setAttr(skeleton + '.ry', -90)
    mc.select(skeleton, r=1)
    offset_animaction(1000)  # Poongo el offset para que empiece en el 1001 la anim por defecto
    mc.select(cl=1)
    mc.select(skeleton, r=1)


def offset_animaction(offset):

    sel = cmds.ls(selection=True)
    if not sel:
        cmds.warning("Selecciona el padre primero.")
        return

    nodes = cmds.listRelatives(sel[0], allDescendents=True, fullPath=True) or []
    nodes.append(sel[0])

    cmds.keyframe(nodes, edit=True, relative=True, timeChange=offset)

    mc.select(nodes, r=1)
    cmds.setInfinity( pri='cycle', poi='cycle' )
    mc.select(sel[0], r=1)


def crear_ui():
    sel = ''
    if cmds.window("miUI", exists=True):
        cmds.deleteUI("miUI")

    cmds.window("miUI", title="Editor de Animaciones de Crowds", widthHeight=(700, 150))
    cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

    archivos = [os.path.splitext(f)[0] for f in os.listdir(carpeta) if os.path.isfile(os.path.join(carpeta, f))]

    menu = cmds.optionMenu("dropdownArchivos", label="Animacion:")
    for a in archivos:
        cmds.menuItem(label=a)

    def carga_anim(*args):
        nombre = cmds.optionMenu(menu, query=True, value=True)
        for f in os.listdir(carpeta):
            if os.path.splitext(f)[0] == nombre:
                cargar_animacion(os.path.join(carpeta, f))
                break

    cmds.button(label="Cargar animacion", command=carga_anim)

    slider = cmds.intSliderGrp("miSlider", label="Valor:", field=True, minValue=-300, maxValue=300, value=0)

    def offset_de_animacion(*args):
        valor = cmds.intSliderGrp(slider, query=True, value=True)
        offset_animaction(valor)

    cmds.button(label="Ofsetear Animacion", command=offset_de_animacion)

    cmds.showWindow("miUI")

# crear_ui()