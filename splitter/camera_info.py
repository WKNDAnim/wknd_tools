import maya.cmds as cmds


def _get_camera_keyframes_by_frame(camera_name):
    """
    Obtiene todos los keyframes de una cámara organizados por frame

    Args:
        camera_name: Nombre de la cámara (puede ser el transform o el shape)

    Returns:
        dict: {camera: {keyframe: {keyframe_data}}} or False
        dict: {camera_name: {frame: [values]}}
    """

    # Si es un shape, obtener el transform
    if cmds.objectType(camera_name) == 'camera':
        camera_transform = cmds.listRelatives(camera_name, parent=True)[0]
    else:
        camera_transform = camera_name

    # Obtener el shape de la cámara
    camera_shape = cmds.listRelatives(camera_transform, shapes=True)[0]

    # Atributos a consultar
    transform_attrs = [
        'translateX', 'translateY', 'translateZ',
        'rotateX', 'rotateY', 'rotateZ'
    ]

    camera_attrs = [
        'focalLength',
        'focusDistance',
        'fStop',
    ]

    #################
    # Get KeyFrames #
    #################

    # Recopilar todos los frames únicos que tienen keyframes
    all_frames = set()

    # Obtener frames de transformación
    for attr in transform_attrs:
        full_attr = f"{camera_transform}.{attr}"
        keyframes = cmds.keyframe(full_attr, query=True, timeChange=True)
        if keyframes:
            all_frames.update(keyframes)

    # Obtener frames de atributos de cámara
    for attr in camera_attrs:
        full_attr = f"{camera_shape}.{attr}"
        keyframes = cmds.keyframe(full_attr, query=True, timeChange=True)
        if keyframes:
            all_frames.update(keyframes)

    if not all_frames:
        return False, {camera_name: all_frames}

    ##################
    # Ordenar frames #
    ##################

    all_frames = sorted(all_frames)

    # Construir el diccionario resultado
    result = {camera_transform: {}}

    for frame in all_frames:
        # values = []
        result[camera_transform][frame] = {}

        # Obtener valores de transformación en ese frame
        for attr in transform_attrs:
            full_attr = f"{camera_transform}.{attr}"
            value = cmds.getAttr(full_attr, time=frame)
            result[camera_transform][frame][attr] = value

        # Obtener valores de cámara en ese frame
        for attr in camera_attrs:
            full_attr = f"{camera_shape}.{attr}"
            value = cmds.getAttr(full_attr, time=frame)
            result[camera_transform][frame][attr] = value

    return result, {camera_name: all_frames}


def _define_camera_changes(cameraInfo, keyedFrames):

    for c, keyframes in cameraInfo.items():

        moving = []
        t = r = z = False

        for frame in keyedFrames:

            keyFrameValues = keyframes[frame]
            if frame == keyedFrames[0]:
                prevKeyFrameValues = keyFrameValues
                prevFrame = frame
                continue

            # Translacion
            x_t = [prevKeyFrameValues['translateX'], prevKeyFrameValues['translateY'], prevKeyFrameValues['translateZ']]
            y_t = [keyFrameValues['translateX'], keyFrameValues['translateY'], keyFrameValues['translateZ']]
            traslacion = _dist(x_t, y_t)

            # Rotacion
            x_r = [prevKeyFrameValues['rotateX'], prevKeyFrameValues['rotateY'], prevKeyFrameValues['rotateZ']]
            y_r = [keyFrameValues['rotateX'], keyFrameValues['rotateY'], keyFrameValues['rotateZ']]
            rotacion = _dist(x_r, y_r)

            # Zoom
            x_z = [prevKeyFrameValues['focalLength']]
            y_z = [keyFrameValues['focalLength']]
            zoom = _dist(x_z, y_z)

            # Focus
            x_f = [prevKeyFrameValues['focusDistance']]
            y_f = [keyFrameValues['focusDistance']]
            focus = _dist(x_f, y_f)

            if traslacion:
                print(f"Hay TRASLACION del frame {prevFrame} al {frame}")
            t = traslacion or t

            if rotacion:
                print(f"Hay ROTACION del frame {prevFrame} al {frame}")
            r = rotacion or r

            if zoom:
                print(f"Hay ZOOM del frame {prevFrame} al {frame}")
            z = zoom or z

            # if focus:
            #     print(f"Hay FOCUS del frame {prevFrame} al {frame}")

            if any([traslacion, rotacion, zoom, focus]):
                moving.append([prevFrame, frame])

            prevKeyFrameValues = keyFrameValues
            prevFrame = frame

        return t, r, z, moving


# UTILS ##########

def _dist(x, y):

    threshold = 1e-4

    if len(x) != len(y):
        print(f"Los dos vectores no son de la misma longitud: len(x)={len(x)} | len(y)={len(y)}")
        return False

    return not all(abs(a - b) <= threshold for a, b in zip(x, y))


def _unir_rangos(rangos):
    """
    rangos: lista de pares [inicio, fin]
    Devuelve la lista de rangos fusionados (sin frames repetidos).
    """
    if not rangos:
        return []

    # Aseguramos orden por frame inicial
    rangos = sorted(rangos, key=lambda r: r[0])

    fusionados = [rangos[0]]

    for start, end in rangos[1:]:
        last_start, last_end = fusionados[-1]

        # Si el rango nuevo toca o solapa al último rango, unir
        if start <= last_end:
            fusionados[-1][1] = max(last_end, end)
        else:
            fusionados.append([start, end])

    return fusionados


###############################

def get_camera_movement(camera):

    """"
    Input:

        -Camera name

    Output:

        - Camera info --> {camera{keyframe{keyframe_data}}}
        - Movement Frame Range --> String
        - Translation, rotation, zoom --> Boolean array

    """

    # Obtener keyframes en el formato solicitado
    cameraInfo, keyedFrames = _get_camera_keyframes_by_frame(camera)

    if not cameraInfo:
        movement = "NO MOVEMENT"
        translation = rotation = zoom = False
        return False, "NO MOVEMENT", [translation, rotation, zoom]

    # Buscamos los cambios en la camara
    translation, rotation, zoom, movement = _define_camera_changes(cameraInfo, keyedFrames[camera])

    # Unimos los frame ranges si es necesario
    finalMovement = _unir_rangos(movement)

    return cameraInfo, finalMovement, [translation, rotation, zoom]
