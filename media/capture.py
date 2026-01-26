"""Maya viewport capture utilities"""
import maya.cmds as mc
import tempfile
import os
import glob


def capture_viewport_sequence(start_frame=None, end_frame=None, sequence_capture=False, width=1280, height=720):
    """
    Capture viewport as image sequence

    Returns:
        dict: {'pattern': str, 'files': list, 'format': str}
    """
    if start_frame is None:
        start_frame = mc.playbackOptions(query=True, minTime=True)
    if end_frame is None:
        end_frame = mc.playbackOptions(query=True, maxTime=True)

    # Save current state
    original_time = mc.currentTime(query=True)

    # Configure viewport
    panel = _get_active_panel()
    _setup_clean_viewport(panel)

    # Playblast to temp
    temp_dir = os.path.realpath(tempfile.gettempdir())
    output_base = os.path.join(temp_dir, "wknd_capture")
    # Create folder if not exists
    if not os.path.exists(output_base):
        os.makedirs(output_base)

    if sequence_capture:

        filename = "temp.mov"
        output_base_file = os.path.join(output_base, filename)
        width = 1280
        height = 720

        mc.playblast(
            filename=output_base_file,
            format='qt',
            sequenceTime=True,
            clearCache=True,
            viewer=False,
            showOrnaments=False,
            framePadding=4,
            percent=100,
            compression='H.264',
            quality=100,
            widthHeight=[width, height],
            startTime=start_frame,
            endTime=end_frame,
            forceOverwrite=True,
            useTraxSounds=True
        )

        # Restore
        mc.currentTime(original_time)

        # Find generated files
        return {
            'files': output_base_file,
            'format': 'qt'
        }

    else:

        mc.playblast(
            filename=output_base,
            format='image',
            sequenceTime=False,
            clearCache=True,
            viewer=False,
            showOrnaments=False,
            framePadding=4,
            percent=100,
            compression='png',
            quality=100,
            widthHeight=[width, height],
            startTime=start_frame,
            endTime=end_frame,
            forceOverwrite=True
        )

        # Find generated files
        files = sorted(glob.glob(os.path.join(temp_dir, "wknd_capture.*.png")))
        pattern = os.path.join(temp_dir, "wknd_capture.%04d.png")

        # Restore
        mc.currentTime(original_time)

        return {
            'pattern': pattern,
            'files': files,
            'format': 'png',
            'count': len(files)
        }


def capture_playblast_with_sound(output_video, sound):

    start_frame = mc.playbackOptions(query=True, minTime=True)
    end_frame = mc.playbackOptions(query=True, maxTime=True)

    # Save current state
    original_time = mc.currentTime(query=True)

    # Get active panel or the one with the camera we want
    panel = _get_active_panel()
    camera = mc.modelPanel(panel, q=True, camera=True)
    if not "sq" in camera:
        panel = get_valid_model_panel()

    # Configure viewport
    _setup_clean_viewport(panel)

    if sound == "trax":

        print("INFO --> Using Trax Sound for playblast")

        mc.playblast(
            filename=output_video,
            format='qt',
            forceOverwrite=True,
            clearCache=True,
            viewer=False,
            showOrnaments=False,
            percent=100,
            compression='H.264',
            quality=100,
            startTime=start_frame,
            endTime=end_frame,
            # camera=camera,
            editorPanelName=panel,
            widthHeight=[1280, 720],
            useTraxSounds=True
        )

    else:

        print("INFO --> Using Trax Sound for playblast")

        mc.playblast(
            filename=output_video,
            format='qt',
            forceOverwrite=True,
            clearCache=True,
            viewer=False,
            showOrnaments=False,
            percent=100,
            compression='H.264',
            quality=100,
            startTime=start_frame,
            endTime=end_frame,
            # camera=camera,
            editorPanelName=panel,
            widthHeight=[1280, 720],
            sound=sound
        )
    print("Playblast donee -----------")

    # Restore
    mc.currentTime(original_time)

    print("TIME RESTORED -----------")

    return True


def _get_active_panel():
    """Get active model panel"""
    panel = mc.getPanel(withFocus=True)
    if 'modelPanel' not in panel:
        panel = mc.getPanel(type='modelPanel')[0]
    return panel


def is_default_camera(cam):
    shape = cam
    if mc.nodeType(cam) == "transform":
        shapes = mc.listRelatives(cam, s=True, type="camera") or []
        shape = shapes[0] if shapes else None
    return shape and mc.camera(shape, q=True, startupCamera=True)


def get_valid_model_panel():
    for p in mc.getPanel(type="modelPanel"):
        cam = mc.modelPanel(p, q=True, camera=True)
        print(f"{p} --> {cam}")
        if not is_default_camera(cam):
            return p
    return None


def _setup_clean_viewport(panel):
    """Configure viewport for clean playblast"""
    mc.modelEditor(panel, edit=True,
                     grid=False,
                     displayAppearance='smoothShaded',
                     displayTextures=True,
                     wireframeOnShaded=False,
                     allObjects=False,
                     polymeshes=True,
                     nurbsSurfaces=True,
                     subdivSurfaces=True)


def cleanup_capture_files(capture_info):
    """Delete temporary capture files"""
    if 'files' in capture_info:
        for f in capture_info['files']:
            try:
                os.remove(f)
            except:
                pass
