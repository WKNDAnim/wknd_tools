import maya.cmds as mc
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
