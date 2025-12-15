import sgtk
import maya.cmds as mc
import re
import os

from wknd_tools.splitter import camera_info
import importlib
importlib.reload(camera_info)


def split_scene_per_shot(context, engine, log, selectedShots):

    log("Splitting scene per shot:")
    log(f"\t- Selected SHOTS are {selectedShots}")

    tk = engine.sgtk
    sg = engine.shotgun

    # Get work template
    template = tk.templates["maya_shot_work"]

    # get current version fields
    current_file = mc.file(query=True, sceneName=True)
    log(f"📝 Current File: {current_file}")
    fields_work = template.get_fields(current_file)
    current_version = fields_work["version"]
    log(f"🧺 Fields WORK: {fields_work}")

    # get shots from sequencer
    seq_manager = mc.sequenceManager(q=True, node=True)
    sequencer = mc.listConnections(seq_manager, type='sequencer')[0]
    shots = mc.listConnections(sequencer, type="shot") or []  # Get a list of all shots from the sequencer.
    log(f"🤸‍♀️ Shots from sequencer: {shots}")

    # get all shot cameras to delete them later
    all_cameras = list()
    for shot in shots:
        all_cameras.append(mc.listConnections(f"{shot}.currentCamera")[0])
    log(f"📹 Cameras: {all_cameras}")

    # logic for all shots to export them separately
    processedShots = []
    for shot in shots:

        # Get Shot info
        shot_name = mc.getAttr(f"{shot}.shotName")  # Query shot's name.
        log(f"PROCESSING SHOT 🎯 --> {shot_name}")
        if shot_name not in selectedShots:
            continue
        start_frame = mc.getAttr(f"{shot}.startFrame")  # Query shot's start frame.
        end_frame = mc.getAttr(f"{shot}.endFrame")  # Query shot's end frame.
        shot_camera = mc.listConnections(f"{shot}.currentCamera")[0]  # Query shot's camera.
        log(f"shotcamera --> {shot_camera}")

        # Get current Shot entity
        shot_entity = sg.find_one(
                'Shot',
                [['project', 'is', context.project],
                ['code', 'is', shot_name]],
                ['code']
            )

        ###############
        # LAYOUT PATH #
        ###############

        # Get current layout task entity
        step_name = 'Layout'
        task = sg.find_one(
            'Task',
            [['entity', 'is', shot_entity], ['step.Step.code', 'is', step_name]],
            ['content', 'step']
        )

        # Ensure folders are created
        tk.create_filesystem_structure("Task", task["id"])

        # Build path for LAYOUT
        shot_context = tk.context_from_entity('Task', task['id'])
        fields = shot_context.as_template_fields(template)
        fields["name"] = fields_work["name"]
        fields["version"] = current_version
        layout_scene_path = template.apply_fields(fields)

        # Get camera export path
        template_camera_abc = tk.templates["maya_shot_camera_abc_publish"]
        template_camera_ma = tk.templates["maya_shot_camera_ma_publish"]

        camera_publish_path_abc = template_camera_abc.apply_fields(fields)
        camera_publish_path_ma = template_camera_ma.apply_fields(fields)

        ##################
        # ANIMATION PATH #
        ##################

        # Get current shot ANIMATION task entity
        step_name = 'Animation'
        task = sg.find_one(
            'Task',
            [['entity', 'is', shot_entity], ['step.Step.code', 'is', step_name]],
            ['content', 'step']
        )
        # Ensure folders are created
        tk.create_filesystem_structure("Task", task["id"])

        # Build path for ANIMATION
        shot_context = tk.context_from_entity('Task', task['id'])
        fields = shot_context.as_template_fields(template)
        # fields["Task"] = 'Animation'
        fields["name"] = fields_work["name"]
        fields["version"] = 1  # For animation, restart versioning
        anim_scene_path = template.apply_fields(fields)

        log(f"ANIM END")

        ##############
        # CLEAN KEYS #
        ##############

        # Delete keys out of range
        curves = mc.ls(type='animCurve') or []
        for curve in curves:
            try:
                mc.cutKey(curve, time=(-1000000, start_frame - 1), clear=True)
                mc.cutKey(curve, time=(end_frame + 1, 1000000), clear=True)
            except:
                pass

        # Move Animation
        if start_frame == 1001.0:
            offset = 0
        else:
            offset = start_frame - 1001.0

        curves = mc.ls(type='animCurve')        
        for curve in curves:
            mc.keyframe(curve, e=1, r=1, timeChange=offset*(-1))

        cameraInfo, finalMovement, movements = camera_info.get_camera_movement(shot_camera)
        log(f"--------- CAMERA_INFO --> {cameraInfo}")
        log(f"--------- finalMovement --> {finalMovement}")
        log(f"--------- movements --> {movements}")

        ##################
        # EXPORT CAMERAS #
        ##################

        # MAYA SCENE
        if not os.path.exists(os.path.dirname(camera_publish_path_ma)):
            os.makedirs(os.path.dirname(camera_publish_path_ma))

        mc.select(shot_camera, r=1)
        mc.file(camera_publish_path_ma, type='mayaAscii', exportSelected=True, force=True)

        # ALEMBIC CACHE - (add -step 1 to get animation)
        if not os.path.exists(os.path.dirname(camera_publish_path_abc)):
            os.makedirs(os.path.dirname(camera_publish_path_abc))

        shot_camera_baked = _bake_camera(shot_camera, start_frame-offset, end_frame-offset)

        # cmd = '-root ' + shot_camera_baked + ' -frameRange ' + str(start_frame-offset) + ' ' + str(end_frame-offset) + ' -step 1 -attr focalLength -worldSpace -writeVisibility -dataFormat ogawa -file ' + camera_publish_path_abc
        
        cmd = '-root ' + shot_camera_baked + ' -frameRange ' + str(start_frame-offset) + ' ' + str(end_frame-offset) + ' -step 1 -attr focalLength -worldSpace -writeVisibility -dataFormat ogawa -file ' + camera_publish_path_abc
        mc.AbcExport(j=cmd)

        log("✅ Cameras exported!📹")

        #################
        # EXPORT LAYOUT #
        #################

        # Delete shots from sequencer
        mc.delete(shots)

        # Delete cameras
        for cam in all_cameras:
            try:
                mc.delete(cam)
            except:
                pass

        # Import shot camera (as .ma for now)
        mc.file(camera_publish_path_ma, r=True, ignoreVersion=True, namespace=shot_camera)

        # Set frame range in scene
        mc.playbackOptions(min=start_frame-offset, max=end_frame-offset, animationStartTime=start_frame-offset, animationEndTime=end_frame-offset)

        # Create folder
        if not os.path.exists(os.path.dirname(layout_scene_path)):
            os.makedirs(os.path.dirname(layout_scene_path))

        # Rename and save layout scene
        mc.file(rename=layout_scene_path)
        mc.file(save=True, type='mayaAscii')

        log(f"✅ LAYOUT scene exported! --> {layout_scene_path}")

        ####################
        # EXPORT ANIMATION #
        ####################

        # Remove ma camera and import alembic camera
        ref_node = mc.referenceQuery(camera_publish_path_ma, referenceNode=True)
        mc.file(referenceNode=ref_node, removeReference=True)
        mc.file(camera_publish_path_abc, r=True, ignoreVersion=True, namespace=shot_camera)

        # # Parent Cameras to group
        # _parent_safe(cameras, "CAMERAS")

        # if camera is static camera, lock attributes
        try:
            attrs = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v']
            cam = shot_camera + ':' + shot_camera
            for attr in attrs:
                mc.setAttr(f"{cam}.{attr}", lock=True)

            cam_shape = mc.listRelatives(cam, shapes=True)[0]
            mc.setAttr(f"{cam_shape}.focalLength", lock=True)
        except:
            pass

        # Create folder
        if not os.path.exists(os.path.dirname(anim_scene_path)):
            os.makedirs(os.path.dirname(anim_scene_path))

        # rename and save as animation scene
        mc.file(rename=anim_scene_path)
        mc.file(save=True, type='mayaAscii')

        log(f"✅ ANIMATION scene exported! --> {anim_scene_path}")

        ##################
        # UPDATE SG INFO #
        ##################

        shot_data = {
            "sg_cam_mov": False,
            "sg_translation": movements[0],
            "sg_rotation": movements[1],
            "sg_zoom": movements[2],
            "sg_cam_mov_range": str(finalMovement)
        }

        if cameraInfo:
            shot_data["sg_cam_mov"] = True

        sg.update("Shot", shot_entity["id"], shot_data)

        log("📲 SHOTGRID SHOT INFO UPDATED!")

        ###############
        # RENEW SCENE #
        ###############

        # reopen original master sequence scene to continue
        mc.file(current_file, open=True, force=True)

        # Mark as processed
        processedShots.append(shot_name)

    return True

def _parent_safe(nodes, parent_grp):
    """ Parent nodes to groups in Maya"""
    for n in nodes:
        if not mc.objExists(n):
            continue
        # si ya está bajo el grupo, saltar
        try:
            current_parent = mc.listRelatives(n, parent=True, fullPath=True) or []
            if current_parent and current_parent[0].split("|")[-1] == parent_grp:
                continue
            mc.parent(n, parent_grp)
        except Exception:
            # evita romper el flujo si algún nodo no puede parentarse
            pass

def _top_level_transforms():
    """Top DAG nodes visibles en el Outliner (excluye cámaras por defecto)."""
    roots = mc.ls(assemblies=True, long=True) or []
    exclude = {"|persp", "|top", "|front", "|side", "|SET", "|CHAR", "|CAMERAS", "|PROPS", "|PREVIS", "|AUDIOS"}
    return [r for r in roots if r not in exclude]

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
        shape=False
    )

    # Bakear manualmente los atributos de la cámara frame por frame
    # Primero recolectamos los valores mientras están conectados
    baked_values = {}
    for attr in camera_attrs:
        source_attr = f"{main_camera_shape}.{attr}"
        target_attr = f"{baked_camera_shape}.{attr}"
        if mc.objExists(source_attr) and mc.objExists(target_attr):
            baked_values[attr] = {}
            for frame in range(int(start_frame), int(end_frame) + 1):
                mc.currentTime(frame)
                try:
                    value = mc.getAttr(source_attr)
                    baked_values[attr][frame] = value
                except:
                    pass

    # Desconectar todos los atributos conectados
    for attr in camera_attrs:
        target_attr = f"{baked_camera_shape}.{attr}"
        connections = mc.listConnections(target_attr, source=True, destination=False, plugs=True)
        if connections:
            try:
                mc.disconnectAttr(connections[0], target_attr)
            except:
                pass

    # Ahora aplicar los keyframes con los valores guardados
    for attr, frame_values in baked_values.items():
        target_attr = f"{baked_camera_shape}.{attr}"
        for frame, value in frame_values.items():
            try:
                mc.setKeyframe(target_attr, time=frame, value=value)
            except:
                pass

    # Eliminar el constraint
    mc.delete(parent_constraint)
        
    print(f"Cámara bakeada creada: {baked_camera_transform}")
    return baked_camera_transform
