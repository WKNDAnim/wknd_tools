import maya.cmds as mc
import os


def setTxTzRy(object, tx, tz, ry):

    mc.setAttr(object + '.tx', tx)
    mc.setAttr(object + '.tz', tz)

    mc.setAttr(object + '.ry', ry)


def setTransRot(object, tx=0, ty=0, tz=0, rx=0, ry=0, rz=0):

    mc.setAttr(f"{object}.tx", tx)
    mc.setAttr(f"{object}.ty", ty)
    mc.setAttr(f"{object}.tz", tz)

    mc.setAttr(f"{object}.rx", rx)
    mc.setAttr(f"{object}.ry", ry)
    mc.setAttr(f"{object}.rz", rz)


def get_top_transforms_from_reference(ref_node):

    nodes = mc.referenceQuery(ref_node, nodes=True) or []
    transforms = mc.ls(nodes, type="transform", long=True) or []

    top = []

    for t in transforms:
        parent = mc.listRelatives(t, parent=True, fullPath=True)

        # si no tiene padre o el padre NO está en la referencia → es root
        if not parent or parent[0] not in transforms:
            top.append(t)

    return top


def update_ref(asset_name):

    print("="*70)

    # Get all refs
    refs = mc.file(q=True, reference=True)

    # Search the one for the asset we need
    current_path = [i for i in refs if asset_name in i]
    current_path = current_path[0]
    print(f" - current_path --> {current_path}")

    # Get node
    ref_node = mc.referenceQuery(current_path, referenceNode=True)
    print(f" - ref_node --> {ref_node}")

    # Search for the new path
    pub_root = os.path.dirname(current_path)
    files = os.listdir(pub_root)
    files.sort(reverse=True)
    files = [file for file in files if not os.path.isdir(os.path.join(pub_root, file)) and "scene" in file]
    new_path = os.path.join(pub_root, files[0])
    print(f" - NEW PATH --> {new_path}")

    print(os.path.basename(new_path))
    print(os.path.basename(current_path))

    # Replace reference
    if os.path.basename(new_path) in os.path.basename(current_path):
        print("- PATH ALREADY UPDATED!")
        return ref_node

    # Cambiar el path
    mc.file(new_path, loadReference=ref_node)

    print("Referencia actualizada:")
    print(f"{os.path.basename(current_path)} --> {os.path.basename(new_path)}")

    return ref_node


def fix_valla():

    asset_name = "verjaEscuela"

    ref_node = update_ref(asset_name)
    t = get_top_transforms_from_reference(ref_node)
    setTransRot(t[0])  # By default sets all to 0


def fix_arbustos():

    # Limpiamos la selección
    mc.select(cl=1)

    # Seleccionar el arbusto que ya tenemos en la escena normalmente
    arbusto_alto_orig = 'arbustoAlto_std'

    # Seteamos la posición del primer seto
    x = 1436
    y = 4005
    z = 0

    mc.setAttr(arbusto_alto_orig + 'Shape.mode', 0)
    setTxTzRy(arbusto_alto_orig, x, y, z)
    mc.setAttr(arbusto_alto_orig + '.sx', 0.84)

    all_inst = []

    ###################
    # Parte Delantera #
    ###################

    posX = 1436
    for i in range(0, 3):
        inst = mc.instance(arbusto_alto_orig)[0]
        all_inst.append(inst)
        posX += 1179
        if i == 2:
            setTxTzRy(inst, posX + 20, 4005, 0)
            mc.setAttr(inst + '.sx', 0.9)
        else:
            setTxTzRy(inst, posX, 4005, 0)

    posX = -700
    for i in range(0, 5):
        inst = mc.instance(arbusto_alto_orig)[0]
        all_inst.append(inst)
        if i == 4:
            setTxTzRy(inst, -5234, 4005, 0)
            mc.setAttr(inst + '.sx', 0.6)
        else:
            setTxTzRy(inst, posX, 4005, 0)
        posX -= 1179

    #################
    # Parte Trasera #
    #################

    for ins in all_inst:
        inst = mc.instance(ins)[0]
        mc.setAttr(inst + '.tz', -3939)

    #################
    # Parte Lateral #
    #################

    all_inst = []

    arbusto_alto_orig = 'arbustoAlto_std1'
    setTxTzRy(arbusto_alto_orig, 5568, 3254, 90)

    all_inst.append(arbusto_alto_orig)
    posZ = 3254
    for i in range(0, 5):
        inst = mc.instance(arbusto_alto_orig)[0]
        all_inst.append(inst)
        posZ -= 1399
        setTxTzRy(inst, 5568, posZ, 90)
        if i == 4:
            mc.setAttr(inst + '.sx', 0.7)
            mc.setAttr(inst + '.tz', -3466)

    for ins in all_inst:
        inst = mc.instance(ins)[0]
        mc.setAttr(inst + '.tx', -5567)

    ###################
    # Calle delantera #
    ###################

    arbusto_alto_orig = 'arbustoAlto_std4'

    inst = mc.instance(arbusto_alto_orig)[0]
    mc.setAttr(inst + '.tz', 5380)

    arbusto_alto_orig = inst

    posX = 4993

    for i in range(0,8):

        inst = mc.instance(arbusto_alto_orig)[0]
        posX -= 1248
        setTxTzRy(inst, posX, 5380, 0)


def fix_arbustos_vallas():

    fix_arbustos()
    fix_valla()


def fix_cesped():

    publish_path = r"Z:\02Proyectos\Gus\assets\ELEM\escuelaExtSuelo\SURF\Shading\publish\maya"

    files = os.listdir(publish_path)
    files = [f for f in files if "hierba" in f]
    files.sort(reverse=True)
    path = os.path.join(publish_path, files[0])

    mc.file(path, r=True)
