import maya.cmds as mc
from wknd_tools.core import exporters
from wknd_tools.splitter import camera_info
import imp
imp.reload(exporters)
imp.reload(camera_info)

import os

import sgtk
engine = sgtk.platform.current_engine()
tk = engine.sgtk
sg = engine.shotgun


def _export_hair(ref_path_hair, cache_out_path_hair, frame_in, frame_out):

    # Path de la ref del hair
    # ref_path_hair = ref_path.replace("None", "hair")

    # Buscamos su top node
    refNodes = mc.referenceQuery(ref_path_hair, n=1)
    transforms = mc.ls(refNodes, type="transform")
    hair_to_export = transforms[0]

    previous_parent = mc.listRelatives(hair_to_export, allParents=True, fullPath=True)
    mc.parent(hair_to_export, w=1)

    print(f"\t- HAIR - {hair_to_export} - will be exported to {cache_out_path_hair} ----------------")

    # Exportamos la geo para el pelo
    exporters.export_alembic(hair_to_export, cache_out_path_hair, frame_in, frame_out)

    # Put the obj back to its previous parent
    mc.parent(hair_to_export, previous_parent)


def _bake_camera(main_camera, start_frame, end_frame):

    new_camera_name = "_".join([main_camera, "baked"])

    baked_camera_transform, baked_camera_shape = mc.camera(n=new_camera_name)
    baked_camera_transform = mc.rename(baked_camera_transform, new_camera_name)
    baked_camera_shape = mc.listRelatives(baked_camera_transform, shapes=True, type='camera')[0]

    # Obtener el shape de la cámara principal
    main_camera_shape = mc.listRelatives(main_camera, shapes=True, type='camera')[0]
    if not main_camera_shape:
        mc.error(f"No se encontró una cámara en: {main_camera}")

    parent_constraint = mc.parentConstraint(main_camera, baked_camera_transform, mo=False)[0]

    camera_attrs = [
        'focalLength',
        'focusDistance',
        'fStop',
        'nearClipPlane',
        'farClipPlane'
    ]

    for attr in camera_attrs:

        source_attr = f"{main_camera_shape}.{attr}"
        target_attr = f"{baked_camera_shape}.{attr}"

        # Verificar que el atributo existe y se puede conectar
        if mc.objExists(source_attr) and mc.objExists(target_attr):
            # Verificar si el atributo no está ya conectado o bloqueado
            if not mc.listConnections(target_attr, source=True, destination=False):
                try:
                    mc.connectAttr(source_attr, target_attr, force=True)
                except:
                    print(f"No se pudo conectar: {attr}")

    # Bakear las transformaciones del transform
    mc.bakeResults(
        baked_camera_transform,
        simulation=True,
        time=(start_frame, end_frame),
        sampleBy=1,
        oversamplingRate=1,
        disableImplicitControl=True,
        preserveOutsideKeys=True,
        sparseAnimCurveBake=False,
        removeBakedAttributeFromLayer=False,
        bakeOnOverrideLayer=False,
        minimizeRotation=True,
        controlPoints=False,
        shape=True
    )

    # Eliminar el constraint
    mc.delete(parent_constraint)

    print(f"Cámara bakeada creada: {baked_camera_transform}")
    return baked_camera_transform


def force_delete(node):
    # Obtener todos los nodos hijos (incluyendo shapes)
    children = mc.listRelatives(node, allDescendents=True, fullPath=True) or []
    all_nodes = children + [node]

    # Desbloquear todos
    for n in all_nodes:
        try:
            mc.lockNode(n, lock=False)
        except:
            pass

    # Eliminar
    mc.delete(node)


############################################################################################

def export_selected_geos():

    # Get work template
    template = tk.templates["maya_shot_work"]

    # Get current version fields
    current_file = mc.file(query=True, sceneName=True)
    print(f"📝 - Current File: {current_file}")
    fields_work = template.get_fields(current_file)
    current_version = fields_work["version"]
    print(f"🧺 - Fields WORK: {fields_work}")

    # Template OUT CACHE
    cache_out_path_template = tk.templates["maya_shot_anim_assets_abc_publish"]

    # FRAME RANGE
    frame_in = int(mc.playbackOptions(q=1, min=1)) - 1
    frame_out = int(mc.playbackOptions(q=1, max=1)) + 1

    error = []

    selected = mc.ls(sl=1)
    for obj in selected:

        print(f"----- {obj} ----- ")

        # Buscamos el path a la referencia actual
        try:
            ref_path = mc.referenceQuery(obj, filename=True)
            print(f"\t + Reference path: {ref_path}")
        except:
            ref_path = False
            print(f"❌ ERROR: '{obj}' no pertenece a un nodo de referencia")
            mc.confirmDialog(message=f"❌ ERROR: '{obj}' no pertenece a un nodo de referencia")

        # Get its childs
        children = mc.listRelatives(obj, allDescendents=True, fullPath=True)

        # Get shapes in childs
        shapes = mc.ls(children, type="mesh")
        if not shapes:
            shapes = mc.ls(children, type="shape")

        print(f"\t + 🧺 SHAPES: {shapes}")

        # Comprobamos si la shape tiene los extra attr
        if not "GUS_asset_id" in mc.listAttr(shapes[0]):

            # Check if it is a camera
            if "_CAM_" in shapes[0]:

                print(f"\t + 📹 Exportando cámara: {shapes[0]}")

                camera_path_template = tk.templates["maya_shot_camera_abc_publish"]

                # Sacamos los Fields del path
                cache_fields = camera_path_template.get_fields(ref_path)

                # Formamos el path de out para la cache de ese asset
                cache_fields["Step"] = "FLAY"
                cache_fields["Task"] = "FLay"
                cache_fields["version"] = current_version

                camera_publish_path = camera_path_template.apply_fields(cache_fields)

                new_camera_name = "_".join([obj, "baked"])

                if not os.path.exists(os.path.dirname(camera_publish_path)):
                    os.makedirs(os.path.dirname(camera_publish_path))

                cmd = '-root ' + new_camera_name + ' -frameRange ' + str(frame_in) + ' ' + str(frame_out) + ' -step 1 -attr focalLength -worldSpace -writeVisibility -dataFormat ogawa -file ' + camera_publish_path
                mc.AbcExport(j=cmd)

                # Importamos la nueva cámara
                new_camera = mc.file(camera_publish_path, r=True, ns="Flay_Cam")
                top_nodes = mc.referenceQuery(new_camera, nodes=True, dagPath=True)
                cache_top = mc.ls(top_nodes, assemblies=True, long=True)[0]

                mc.parent(cache_top, "CAMERA")

                continue

            else:

                print(f"❌ ERROR: Faltan los CUSTOM ATTRIBUTES en este asset... --> {children}")
                error.append(obj)
                continue

        # Buscamos el asset en sg
        id = mc.getAttr(shapes[0] + ".GUS_asset_id")
        sg_asset = sg.find_one("Asset", [["id", "is", id]], ["sg_asset_type", "code"])

        # Sacamos los Fields del path
        cache_fields = cache_out_path_template.get_fields(ref_path)

        # Formamos el path de HAIR
        cache_hair_template = tk.templates["maya_shot_anim_assets_abc_hair_publish"]
        ref_hair_path = cache_hair_template.apply_fields(cache_fields)

        # Formamos el path de out para la cache de ese asset
        cache_fields["Step"] = "FLAY"
        cache_fields["Task"] = "FLay"
        cache_fields["version"] = current_version

        cache_out_path = cache_out_path_template.apply_fields(cache_fields)

        print(f"- GEO will be exported to {cache_out_path} ----------------")

        # Exportamos la geo
        previous_parent = mc.listRelatives(obj, allParents=True, fullPath=True)
        mc.parent(obj, w=1)
        exporters.export_alembic(obj, cache_out_path, frame_in, frame_out)
        print(f"Exporting GEO to --> {cache_out_path}")

        # Filtramos el export dependiendo del asset type
        if "CH" in sg_asset["sg_asset_type"]:

            # Formamos el path de out para la cache de ese asset
            cache_out_path_hair = cache_hair_template.apply_fields(cache_fields)
            _export_hair(ref_hair_path, cache_out_path_hair, frame_in, frame_out)

        # Put the obj back to its previous parent
        mc.parent(obj, previous_parent)


def export_selected_camera():

    start_frame = mc.playbackOptions(q=True, min=True)
    end_frame = mc.playbackOptions(q=True, max=True)

    main_camera = mc.ls(sl=1)[0]

    # Bake Camera
    shot_camera_baked = _bake_camera(main_camera, start_frame, end_frame)

    # Get camera movement information and publish to SG
    cameraInfo, finalMovement, movements = camera_info.get_camera_movement(shot_camera_baked)
    print(f"CAMERA INFO ---> {cameraInfo}")

    mc.select(main_camera)

    # Exportamos la geo
    export_selected_geos()

    force_delete(shot_camera_baked)

    mc.confirmDialog(message="✅ Cameras exported!📹")

