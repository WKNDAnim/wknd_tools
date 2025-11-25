"""Playblast to video"""
from . import capture
from . import video_encoder
import importlib
importlib.reload(capture)
importlib.reload(video_encoder)
import maya.cmds as mc
import tempfile
import os
import shutil


def create_playblast(output_video):
    """
    Create playblast video from current camera

    Returns:
        str: Path to video or None
    """

    # Create folder if needed
    if not os.path.exists(os.path.dirname(output_video)):
        os.makedirs(os.path.dirname(output_video))

    # capture viewport
    capture_info = capture.capture_viewport_sequence()

    if not capture_info['files']:
        return None

    success = video_encoder.images_to_video(
        capture_info['pattern'] ,
        output_video,
        'playblast')

    # Cleanup
    capture.cleanup_capture_files(capture_info)

    return output_video if success else None


def create_movie_from_folder(folder, output_path=None):
    """
    Create movie from images from folder for version thumbnail

    Returns:
        str: Path to video or None

    """

    if not output_path:
        temp_dir = os.path.realpath(tempfile.gettempdir())
        output_video = os.path.join(temp_dir, "wknd_playblast.mp4")

    else:
        # Create folder if needed
        if not os.path.exists(os.path.dirname(output_path)):
            os.makedirs(os.path.dirname(output_path))
        output_video = output_path

    success = video_encoder.images_to_video(
        folder,
        output_video,
        'folder')

    return output_video if success else None


def create_sequence_playblast(output_video):

    # Create folder if neededs
    if not os.path.exists(os.path.dirname(output_video)):
        os.makedirs(os.path.dirname(output_video))

    # Create sequence playblast
    seq_manager = mc.sequenceManager(q=True, node=True)
    sequencer = mc.listConnections(seq_manager, type='sequencer')[0]
    shots = mc.listConnections(sequencer, type="shot") or []  # Get a list of all shots from the sequencer.

    start = mc.getAttr(sequencer + '.minFrame')
    end = mc.getAttr(sequencer + '.maxFrame')
    
    capture_info = capture.capture_viewport_sequence(start, end, sequence_capture=True)

    print(f"CAPTURE INFO --> {capture_info}")

    if not capture_info['files']:
        return None

    # success = video_encoder.images_to_video(
    #     capture_info['pattern'] ,
    #     output_video,
    #     'playblast')

    success = _copy_to_movies(capture_info, output_video)

    # Cleanup
    capture.cleanup_capture_files(capture_info)

    return output_video if success else None

def _copy_to_movies(capture_info, output_video):

    shutil.copy2(capture_info["files"], output_video)
    if not os.path.exists(output_video):
        return False
    return True
