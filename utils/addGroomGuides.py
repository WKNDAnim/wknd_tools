import maya.cmds as mc
import maya.mel as mm
import sgtk

engine = sgtk.platform.current_engine()
sg = engine.shotgun
tk = engine.sgtk

###################################################################


def get_xgen_children(transform):

    descendientes = mc.listRelatives(transform, allDescendents=True, type="transform") or []
    xgen_descriptions = []

    for nodo in descendientes:
        shapes = mc.listRelatives(nodo, shapes=True, fullPath=True) or []
        tipos = [mc.nodeType(nodo)] + [mc.nodeType(s) for s in shapes]

        if any(t.startswith("xgm") for t in tipos):
            xgen_descriptions.append(nodo)

    return xgen_descriptions

###################################################################


def addGuiasBakePelo(dryrun=False):

    #
    # Buscamos el nombre de la description de xgen que queremos bakear #
    #

    # Hay que tener un transform de personaje seleccionado
    transform = mc.ls(sl=1)
    if not transform or len(transform) > 1:
        print("WARNING: Selecciona el transform del grupo del perro que quieres fixear")
        return
    else:
        resultado = get_xgen_children(transform[0])

    if not resultado:
        return

    # Buscamos solo el groom del body del perro
    description = None
    for i in resultado:
        if "_body_" in i:
            description = i
            break

    if not description:
        print("WARNING: No se encontró ninguna description con '_body_'")
        return

    print(f"*Procesando: - {description} -")

    #
    # Formamos el path de export de la cache
    #

    file_path = mc.file(query=True, sceneName=True)
    print(f"/t - FILE PATH: {file_path}")

    template = tk.templates["maya_shot_work"]
    fields_shot = template.get_fields(file_path)

    reference_path = mc.referenceQuery(description, filename=True)

    template_asset = tk.templates["maya_asset_clean_publish"]
    fields_asset = template_asset.get_fields(reference_path)

    template_out = tk.templates["maya_shot_anim_assets_abc_publish_extras_groom"]
    fields = {
        "Sequence": fields_shot["Sequence"],
        "Step": "ANM",
        "Shot": fields_shot["Shot"],
        "name": fields_shot["name"],
        "Task": "Animation",
        "Asset": fields_asset["Asset"],
        "version": 1,
    }

    savePath = template_out.apply_fields(fields)
    print(f"/t - SAVE PATH: {savePath}")

    if not dryrun:

        #
        # Start y end frame de la animacion a cachear
        #

        start_frame = mc.playbackOptions(query=True, minTime=True)
        end_frame = mc.playbackOptions(query=True, maxTime=True)
        print(f"/t - START: {start_frame} // END: {end_frame}")

        #
        # CREAR LINEAR WIRE ########
        #

        # Apagar el description principal
        mc.setAttr(description + '.v', 0)

        shape = mc.listRelatives(description, s=1)[0]
        base = mc.listConnections(description + '.inSplineData')[0]

        linear_wire_name = description + "_LinearWire"

        linear_wire = mc.createNode("xgmModifierLinearWire", name=linear_wire_name)

        mc.connectAttr(base + '.outSplineData', linear_wire + '.inSplineData', f=1)
        mc.connectAttr(linear_wire + '.outSplineData', shape + '.inSplineData', f=1)

        # Crea las curvas de guide
        mel_command = f"xgmModifierLinearWireOpCB 0 {linear_wire_name};"
        mm.eval(mel_command)

        # Renombra las guias
        guide_name = description + '_inGuide'
        mc.rename("inGuide", guide_name)

        print("/t -- Guias creadas!")

        # EXPORTAR CACHE ########

        # Primero muteo el linear wire
        mc.setAttr(linear_wire_name + '.mute', 1)

        # exporto el cache de las guias
        job_command = f" -file \"{savePath}\" -df ogawa -fr {start_frame} {end_frame} -step 1 -obj {guide_name}"
        mc.xgmSplineCache(create=True, j=job_command)

        # Enciendo description general y linear wire
        mc.setAttr(linear_wire_name + '.mute', 0)
        mc.setAttr(description + '.v', 1)

        print("/t -- Cache creada! :)")
