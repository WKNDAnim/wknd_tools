import sgtk
import maya.cmds as cmds

# Create master shot for layout
# we NEED to be on a master shot scene, saved with SG (hasta que Alberto lo haga automatico)

engine = sgtk.platform.current_engine()
sg = engine.shotgun
context = engine.context

def get_sequence_shots_data(sequence_code):
    """
    Obtiene info de shots de una secuencia en un solo query eficiente.
    
    Args:
        sequence_code: Código de la secuencia (ej: 'sq9999')
        
    Returns:
        dict: Diccionario con formato para crear secuencia de cámaras
    """
    
    # Query 1: Obtener la secuencia
    sequence = sg.find_one(
        'Sequence',
        [['project', 'is', context.project],
         ['code', 'is', sequence_code]],
        ['code', 'shots']
    )
    
    if not sequence:
        print(f"❌ No se encontró secuencia: {sequence_code}")
        return {}
    
    # Query 2: Obtener TODOS los shots de la secuencia en un solo query
    shot_ids = [shot['id'] for shot in sequence['shots']]
    
    shots_data = sg.find(
        'Shot',
        [['id', 'in', shot_ids]],  # Buscar por lista de IDs
        ['code', 'sg_cut_in', 'sg_cut_out']
    )
    
    # Construir diccionario para la función de Maya
    seq_dict = {}
    master_shot = None
    
    for shot in shots_data:
        shot_name = shot['code']
        
        # Identificar master shot
        if 'master' in shot_name.lower():
            master_shot = shot_name
            continue  # No incluir master en la secuencia
        
        # Validar que tenga cut in/out
        if not shot['sg_cut_in'] or not shot['sg_cut_out']:
            print(f"⚠ {shot_name}: sin cut in/out, ignorado")
            continue
        
        seq_dict[shot_name] = {
            'frame_in': shot['sg_cut_in'],
            'frame_out': shot['sg_cut_out']
        }
    
    print(f"✓ Secuencia: {sequence_code}")
    print(f"✓ Master shot: {master_shot}")
    print(f"✓ Shots en secuencia: {len(seq_dict)}")
    
    return seq_dict, master_shot


def create_sequence_cameras(seq_dict):
    """
    Crea cámaras para cada shot y las monta en el camera sequencer.
    
    Args:
        seq_dict: {shot_name: {frame_in, frame_out}}
    """
    
    # Limpiar secuencia existente si hay
    if cmds.objExists('sequencer2'):
        shots = cmds.sequenceManager('sequencer2', q=True, listShots=True) or []
        for shot in shots:
            cmds.delete(shot)
    
    cameras_info = {}
    current_frame = 1001  # Frame inicial de la secuencia
    
    # Ordenar shots por nombre para mantener consistencia
    sorted_shots = sorted(seq_dict.keys())
    
    for shot_name in sorted_shots:
        shot_data = seq_dict[shot_name]
        
        # Calcular duración del shot
        shot_duration = shot_data['frame_out'] - shot_data['frame_in'] + 1
        seq_start = current_frame
        seq_end = current_frame + shot_duration - 1
        
        # Crear cámara
        cam_transform, cam_shape = cmds.camera(name=f"{shot_name}_cam")

        # Renombrar DESPUÉS de crear para asegurar el nombre exacto
        cam_transform = cmds.rename(cam_transform, f"{shot_name}_cam")
        
        print(f"✓ Cámara creada: {cam_transform}")
                
        # Setear focal length (lens)
        #cmds.setAttr(f"{cam_shape}.focalLength", shot_data['camera_lens'])
        
        # Crear shot en el sequencer
        shot_node = cmds.shot(
            shotName=shot_name,
            currentCamera=cam_transform,
            startTime=seq_start,      # Frame in interno del shot
            endTime=seq_end,        # Frame out interno del shot
            sequenceStartTime=seq_start,           # Donde empieza en la secuencia
            sequenceEndTime=seq_end                # Donde termina en la secuencia
        )
        
        # Guardar info
        cameras_info[shot_name] = {
            'camera': cam_transform,
            'camera_shape': cam_shape,
            'original_range': (shot_data['frame_in'], shot_data['frame_out']),
            'sequence_range': (seq_start, seq_end),
            'shot_node': shot_node
        }
        
        print(f"✓ {shot_name}: frames {seq_start}-{seq_end}")
        
        # Actualizar frame para el siguiente shot
        current_frame = seq_end + 1
    
    # Setear timeline al rango completo de la secuencia
    cmds.playbackOptions(
        min=1001,
        max=current_frame - 1,
        animationStartTime=1001,
        animationEndTime=current_frame - 1
    )
    
    print(f"\n✓ Secuencia completa: frames 1001-{current_frame - 1}")
    print(f"✓ Total shots: {len(cameras_info)}")
    cmds.select(cl=1)
    
    return cameras_info


def create_layout_master_scene(seq_name):

    # Uso
    seq_dict, master_shot = get_sequence_shots_data(seq_name)
    
    print("\nDiccionario resultante:")
    for shot, data in seq_dict.items():
        print(f"  {shot}: {data['frame_in']}-{data['frame_out']}")
        
        
    create_sequence_cameras(seq_dict)
    
# Get sequence name from context
sequence = context.entity['name'].split('_')[-2]
# Call function to create cameras and sequencer shots
create_layout_master_scene(sequence)