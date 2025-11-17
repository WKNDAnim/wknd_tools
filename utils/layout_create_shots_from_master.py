import sgtk
import maya.cmds as mc
import re
import os

# SUPER TEMP! We need to test it with Isma and Joaquin, be sure everything work as it should---------------------------------------------------------------------------------

#LAYOUT TO ANIM SHOTS SCENES

#WE STILL NEED TO PUBLISH THE SET PER SHOT IF NEEDED

#EVERYTHING ELSE IS ACCOUNTED FOR, CAMERAS, MAYA SCENES, KEYS, SHOTS, AND MASTER SEQUENCE SCENE

engine = sgtk.platform.current_engine()
sg = engine.shotgun
context = engine.context
tk = engine.sgtk

print("Templates de Maya disponibles:")
for name, template in tk.templates.items():
    if 'area' in name.lower():
        print(f"  {name}: {template.definition}")


# get current version 
current_file = mc.file(query=True, sceneName=True)
version_match = re.search(r'v(\d+)', os.path.basename(current_file))
current_version = int(version_match.group(1))

# find sequence from shot
current_master_shot = sg.find_one(
        'Shot',
        [['project', 'is', context.project],
         ['code', 'is', context.entity['name']]],
        ['code', 'sg_sequence']  # Campo que linkea a la secuencia
    )

sequence_code = current_master_shot['sg_sequence']['name']

# get shots from sequencer

seq_manager = mc.sequenceManager(q=True, node=True)
sequencer = mc.listConnections(seq_manager, type='sequencer')[0]
shots = mc.listConnections(sequencer, type="shot") or []  # Get a list of all shots from the sequencer.

# get all shot cameras to delete them later

all_cameras = list()
for shot in shots:
    all_cameras.append(mc.listConnections(shot + '.currentCamera')[0])
    
# logic for all shots to export them separately

for shot in shots:
    
    
    shot_name = mc.getAttr("{}.shotName".format(shot))  # Query shot's name.
    start_frame = mc.getAttr("{}.startFrame".format(shot))  # Query shot's start frame.
    end_frame = mc.getAttr("{}.endFrame".format(shot))  # Query shot's end frame.
    shot_camera = mc.listConnections(shot + '.currentCamera')[0]# Query shot's camera.
    
    # get path from template
    # get current shot entity
    current_shot = sg.find_one(
            'Shot',
            [['project', 'is', context.project],
             ['code', 'is', shot_name]],
            ['code']
        )
        
    # get current shot layout task entity
    
    step_name = 'Layout'
    task = sg.find_one(
        'Task',
        [['entity', 'is', current_shot],
         ['step.Step.code', 'is', step_name]], 
        ['content', 'step']
    )
    
    # build path for current shot layout task using template
    
    template = tk.templates["maya_shot_work"]
    shot_context = tk.context_from_entity('Task', task['id'])
    fields = shot_context.as_template_fields(template)
    fields["name"] = 'scene'
    fields["version"] = current_version
    layout_scene_path = template.apply_fields(fields)
    
    
    # get TEMP path for area maya publish to publish cameras-------------------------------------------------------------
       
    template = tk.templates["shot_publish_area_maya"]
    shot_context = tk.context_from_entity('Task', task['id'])
    fields = shot_context.as_template_fields(template)
    fields["name"] = 'scene'
    fields["version"] = current_version
    camera_publish_area = template.apply_fields(fields)
    
    # GUARRADA MAXIMAAAAAA PARA GENERAR EL PATH DE LA CAMARA, NO HAY TEMPLATE TODAVIA------------------------------------
    camera_publish_path_ma = camera_publish_area + '\\' + shot_camera + '_v' + str(f'{current_version:03}' + '.ma')
    
    camera_publish_path_abc = camera_publish_area + '\\' + shot_camera + '_v' + str(f'{current_version:03}' + '.abc')
    camera_publish_path_abc = camera_publish_path_abc.replace('\\','/')

    
    # get current shot ANIMATION task entity
    
    step_name = 'Animation'
    task = sg.find_one(
        'Task',
        [['entity', 'is', current_shot],
         ['step.Step.code', 'is', step_name]], 
        ['content', 'step']
    )
    
    # build path for current shot ANIMATION task using template
    
    template = tk.templates["maya_shot_work"]
    shot_context = tk.context_from_entity('Task', task['id'])
    fields = shot_context.as_template_fields(template)
    fields["Task"] = 'Animation'
    fields["name"] = 'scene'
    fields["version"] = current_version
    anim_scene_path = template.apply_fields(fields)
    
    # Delete keys out of range    
    curves = mc.ls(type = 'animCurve') or []
    for curve in curves:
        try:
            mc.cutKey(curve, time=(-1000000, start_frame - 1), clear=True)
            mc.cutKey(curve, time=(end_frame + 1, 1000000), clear=True)
            
        except:pass
        
    # Move Animatoin
    
    if start_frame == 1001.0:offset = 0
    else:offset = start_frame - 1001.0
    
    curves = mc.ls(type = 'animCurve')        
    for curve in curves:
        mc.keyframe(curve, e=1,r=1,timeChange = offset * (-1))
    
    # export/publish shot cam as .ma----------------------------------
    
    mc.select(shot_camera, r=1)
    mc.file(camera_publish_path_ma, type = 'mayaAscii', exportSelected=True, force=True)
    
    # export/publish shot cam as alembic ----------------------------------(add -step 1 to get animation)
    
    cmd = '-root ' + shot_camera + ' -frameRange ' + str(start_frame-offset) + ' ' + str(end_frame-offset) + ' -step 1 -worldSpace -writeVisibility -dataFormat ogawa -file ' + camera_publish_path_abc
    mc.AbcExport(j=cmd)
    
    #Delete shots from sequencer
   
    mc.delete(shots)
    
    # Delete other shot cameras
    for cam in all_cameras:
        try:
            mc.delete(cam)
        except:pass
        
    # Import shot camera (as .ma for now)------------------------------------------------
    
    mc.file(camera_publish_path_ma, r=True, ignoreVersion=True, namespace=shot_camera)

    # Set frame range in scene
    mc.playbackOptions(min = start_frame-offset, max = end_frame-offset)
        
    # Rename and save layout scene
    
    mc.file(rename = layout_scene_path)
    mc.file(save=True, type = 'mayaAscii')
    
    # remove ma camera and import alembic camera
    
    ref_node = mc.referenceQuery(camera_publish_path_ma, referenceNode=True)
    mc.file(referenceNode=ref_node, removeReference=True)
    mc.file(camera_publish_path_abc, r=True, ignoreVersion=True, namespace=shot_camera)
    
    # if camera is static camera, lock attributes
    try:
        attrs = ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v']
        cam = shot_camera + ':' + shot_camera
        for attr in attrs:
            mc.setAttr(f"{cam}.{attr}", lock=True)
            
        cam_shape = mc.listRelatives(cam, shapes=True)[0]
        mc.setAttr(f"{cam_shape}.focalLength", lock=True)
    except:pass
        
    # rename and save as animation scene
    mc.file(rename = anim_scene_path)
    mc.file(save=True, type = 'mayaAscii')
    
    # reopen original master sequence scene to continue
    
    mc.file(current_file , open=True, force=True)