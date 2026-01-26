import sgtk
import maya.cmds as mc
import re
import os
import shutil

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

    ###############
    # SPLIT SHOTS #
    ###############

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

        # Get current Shot entity
        shot_entity = sg.find_one(
                'Shot',
                [['project', 'is', context.project],
                ['code', 'is', shot_name]],
                ['code']
            )

        ##############
        # GET AUDIOS #
        ##############

        log(f"Getting audio/s for shot {shot_name}...")

        audio_clips = _get_audio_clips_for_shot(start_frame, end_frame)

        log(f"AUDIO ---> {audio_clips}")

        ###############
        # LAYOUT PATH #
        ###############

        log("Getting Layout path...")

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
        shot_context_lay = tk.context_from_entity('Task', task['id'])
        fields = shot_context_lay.as_template_fields(template)
        fields["name"] = fields_work["name"]
        fields["version"] = current_version
        layout_scene_path = template.apply_fields(fields)

        # Get camera export path
        template_camera_abc = tk.templates["maya_shot_camera_abc_publish"]
        template_camera_ma = tk.templates["maya_shot_camera_ma_publish"]

        camera_publish_path_abc = template_camera_abc.apply_fields(fields)
        camera_publish_path_ma = template_camera_ma.apply_fields(fields)

        log(f"camera_publish_path_abc ---> {camera_publish_path_abc}")
        log(f"camera_publish_path_ma ---> {camera_publish_path_ma}")

        ##################
        # ANIMATION PATH #
        ##################

        log("Getting Animation path...")

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
        shot_context_anim = tk.context_from_entity('Task', task['id'])
        fields = shot_context_anim.as_template_fields(template)
        # fields["Task"] = 'Animation'
        fields["name"] = fields_work["name"]
        fields["version"] = 1  # For animation, restart versioning
        anim_scene_path = template.apply_fields(fields)

        log(f"anim_scene_path ---> {anim_scene_path}")

        ##############
        # CLEAN KEYS #
        ##############

        log("Cleaning keys...")

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

        log("KEYS CLEANED!\n")        

        ##################
        # EXPORT CAMERAS #
        ##################

        log("Exporting cameras...")

        # MAYA SCENE
        if not os.path.exists(os.path.dirname(camera_publish_path_ma)):
            os.makedirs(os.path.dirname(camera_publish_path_ma))

        mc.select(shot_camera, r=1)
        mc.file(camera_publish_path_ma, type='mayaAscii', exportSelected=True, force=True)

        # ALEMBIC CACHE - (add -step 1 to get animation)
        if not os.path.exists(os.path.dirname(camera_publish_path_abc)):
            os.makedirs(os.path.dirname(camera_publish_path_abc))

        shot_camera_baked = _bake_camera(shot_camera, start_frame-offset, end_frame-offset)

        # Get camera movement information
        cameraInfo, finalMovement, movements = camera_info.get_camera_movement(shot_camera_baked)
        log(f"CAMERA INFO ---> {cameraInfo}")

        cmd = '-root ' + shot_camera_baked + ' -frameRange ' + str(start_frame-offset) + ' ' + str(end_frame-offset) + ' -step 1 -attr focalLength -worldSpace -writeVisibility -dataFormat ogawa -file ' + camera_publish_path_abc
        mc.AbcExport(j=cmd)

        log("✅ Cameras exported!📹")

        #################
        # EXPORT LAYOUT #
        #################

        log("Exporting Layout...")

        # Delete shots from sequencer
        mc.delete(shots)

        # Delete cameras
        _delete_all_in_group("CAMERAS")

        # Import shot camera (as .ma for now)
        mc.file(camera_publish_path_ma, r=True, ignoreVersion=True, namespace=shot_camera)

        # solo cámaras
        cams = mc.ls(type="camera")
        cam_shapes = [cam for cam in cams if shot_camera in cam]
        # cam_shapes = mc.ls(f"{shot_camera}:*", type="camera") or []
        log(f"CAMERA SHAPES -> {cam_shapes}")

        cam_transforms = []
        for s in cam_shapes:
            p = mc.listRelatives(s, parent=True, fullPath=True)
            if p:
                cam_transforms.append(p[0])

        # evita duplicados
        cam_transforms = list(dict.fromkeys(cam_transforms))
        log(f"CAMERA TRANSFORMS -> {cam_transforms}")

        _parent_safe(cam_transforms + [shot_camera_baked], "CAMERAS")

        # Load Audios
        loaded_audios = _load_audio_clips(audio_clips, offset, tk, fields)
        log(f"✅ Audios Loaded!🦻 --> {loaded_audios}")        

        # Set frame range in scene
        mc.playbackOptions(min=start_frame-offset, max=end_frame-offset, animationStartTime=start_frame-offset, animationEndTime=end_frame-offset)

        # Create folder
        if not os.path.exists(os.path.dirname(layout_scene_path)):
            os.makedirs(os.path.dirname(layout_scene_path))

        # Rename and save layout scene
        mc.file(rename=layout_scene_path)
        mc.file(save=True, type='mayaAscii')

        log(f"✅ LAYOUT scene exported! --> {layout_scene_path}")

        ##################
        # PLAYBLAST SHOT #
        ##################

        from wknd_tools.core import publish_version
        import importlib
        importlib.reload(publish_version)

        description = "Layout Shot Splitted Version"

        publisher = publish_version.Publisher(shot_context_lay, current_version, description, use_playblast=True, log_callback=log)
        publish_result = publisher.publish()

        log("-"*50)
        log(f" PUBLISH RESULT --> {publish_result}")
        log("-"*50)

        ####################
        # EXPORT ANIMATION #
        ####################

        # Remove ma camera and import alembic camera
        _delete_something(cam_transforms[0])
        log("MA camera deleted!")
        mc.file(camera_publish_path_abc, r=True, ignoreVersion=True, namespace=shot_camera)
        log("ABC camera imported!")

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

        # Delete PREVIS group
        _delete_all_in_group("PREVIS")

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

        # if cameraInfo:
        if finalMovement:
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


def _delete_all_in_group(groupName):

    # Verificar que el grupo existe
    if not mc.objExists(groupName):

        print(f"El grupo {groupName} no existe")

    else:

        # Buscamos dentro del grupo
        items = mc.listRelatives(groupName, children=True, fullPath=True)

        if items:

            for item in items:

                _delete_something(item)

            print("Proceso completado")

        else:
            print(f"El grupo {groupName} está vacío...")


def _delete_something(item):

    # Eliminamos referencias
    if mc.referenceQuery(item, isNodeReferenced=True):

        try:
            refFile = mc.referenceQuery(item, filename=True, withoutCopyNumber=True)
            mc.file(refFile, removeReference=True)
            print(f"Referencia eliminada: {refFile}")
        except Exception as e:
            print(f"Error al quitar referencia {item}: {e}")

    else:

        # Eliminamos imports
        try:
            mc.delete(item)
            print(f"Objeto nativo borrado: {item}")
        except Exception as e:
            print(f"Error al borrar {item}: {e}")


def _parent_safe(nodes, parent_grp):
    """ Parent nodes to groups in Maya"""
    for n in nodes:
        if not mc.objExists(n):
            continue

        # solo transforms
        if mc.nodeType(n) != "transform":
            continue

        # si ya está bajo el grupo, saltar
        try:
            current_parent = mc.listRelatives(n, parent=True, fullPath=True) or []
            if current_parent and current_parent[0].split("|")[-1] == parent_grp:
                continue
            mc.parent(n, parent_grp)
        except Exception:
            pass


def _get_audio_clips_for_shot(shot_start, shot_end):
    """
    Encuentra todos los clips de audio que se solapan con el rango del plano
    """
    audio_clips = []

    # Obtener todos los audio nodes en la escena
    audio_nodes = mc.ls(type='audio')

    for audio in audio_nodes:
        # Obtener offset y duración del audio
        offset = mc.getAttr(f'{audio}.offset')
        source_start = mc.getAttr(f'{audio}.sourceStart')
        source_end = mc.getAttr(f'{audio}.sourceEnd')

        audio_start = offset
        audio_end = offset + (source_end - source_start)

        # Verificar si hay overlap
        if audio_start < shot_end and audio_end > shot_start:
            # Calcular el segmento exacto que necesitamos
            clip_info = {
                'node': audio,
                'filepath': mc.getAttr(f'{audio}.filename'),
                'original_offset': offset,
                'source_start': source_start,
                'source_end': source_end,
                'clip_start': max(audio_start, shot_start),
                'clip_end': min(audio_end, shot_end)
            }
            audio_clips.append(clip_info)

    return audio_clips


def _load_audio_clips(audio_clips, shot_offset, tk, fields):
    """
    Carga múltiples clips de audio en la escena, ajustados al offset del plano
    """
    loaded_audios = []

    # template_in_shot = tk.templates["maya_shot_audio"]
    # template_in_edit = tk.templates["atic_shot_layout_audio"]
    template_out = tk.templates["maya_shot_audio"]

    # Get root path
    audio_shot_path = template_out.apply_fields(fields)
    audio_shot_root = os.path.dirname(audio_shot_path)

    for clip in audio_clips:

        # Formamos el path para cada clip
        clip_name = os.path.basename(clip['filepath'])
        audio_shot_path = os.path.join(audio_shot_root, clip_name)

        # Copiamos el audio a la carpeta editorial del shot
        shutil.copy2(clip['filepath'], audio_shot_path)
        print(f"AUDIO copied from - {clip['filepath']} - to - {audio_shot_path} -")

        new_offset = (clip['original_offset'] - shot_offset)

        audio_node = mc.sound(
            file=audio_shot_path,
            offset=new_offset,
            sourceStart=clip['source_start'],
            sourceEnd=clip['source_end'],
            name=clip['node']
        )

        loaded_audios.append(audio_node)

    return loaded_audios
