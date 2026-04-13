import maya.cmds as mc


def fix_arbustos_vallas():

    def setTxTzRy(object , tx , tz , ry):

        mc.setAttr (object + '.tx' , tx)
        mc.setAttr (object + '.tz' , tz)
        mc.setAttr (object + '.ry' , ry)

    # Crear arbusto alto para exterior escuela
    mc.select(cl=1)

    # Seleccionar el arbusto que ya tenemos en la escena normalmente
    arbusto_alto_orig = 'arbustoAlto_std'

    mc.setAttr (arbusto_alto_orig + 'Shape.mode', 0)
    setTxTzRy(arbusto_alto_orig , 1436, 4005, 0)
    mc.setAttr (arbusto_alto_orig + '.sx', 0.84)
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
            mc.setAttr(inst + '.sx' , 0.9)
        else:
            setTxTzRy(inst, posX, 4005, 0)
        
    posX = -700
    for i in range(0,5):
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

    # PArte Lateral

    all_inst = []

    arbusto_alto_orig = 'arbustoAlto_std1'
    setTxTzRy(arbusto_alto_orig, 5568, 3254, 90)

    all_inst.append(arbusto_alto_orig)
    posZ = 3254
    for i in range(0,5):
        inst = mc.instance(arbusto_alto_orig)[0]
        all_inst.append(inst)
        posZ -= 1399
        setTxTzRy(inst, 5568, posZ, 90)
        if i == 4:
            mc.setAttr(inst + '.sx' , 0.7)
            mc.setAttr(inst + '.tz' , -3466)

    for ins in all_inst:
        inst = mc.instance(ins)[0]
        mc.setAttr(inst + '.tx' , -5567)

    ###################
    # Calle delantera #
    ###################

    arbusto_alto_orig = 'arbustoAlto_std4'

    inst = mc.instance(arbusto_alto_orig)[0]
    mc.setAttr(inst + '.tz' , 5380)

    arbusto_alto_orig = inst

    posX = 4993

    for i in range(0,8):

        inst = mc.instance(arbusto_alto_orig)[0]
        posX -= 1248
        setTxTzRy(inst, posX, 5380, 0)
