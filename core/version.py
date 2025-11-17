"""Version creation and management"""
import sgtk


def create_version(context, version_name, description=""):
    """
    Create a Version in ShotGrid

    Args:
        context: ShotGrid context
        version_name (str): Version name
        description (str): Optional description

    Returns:
        dict: Created Version entity
    """
    engine = sgtk.platform.current_engine()
    sg = engine.shotgun

    if not context.entity:
        raise ValueError("No entity in context")

    if not context.task:
        raise ValueError("No task in context")

    version_data = {
        'project': context.project,
        'entity': context.entity,
        'sg_task': context.task,
        'user': context.user,
        'code': version_name,
        'sg_status_list': 'rev',
        'description': description or f"Published version {version_name}"
    }

    version = sg.create('Version', version_data)

    return version


def upload_video(version_id, video_path):
    """Upload video to Version"""

    engine = sgtk.platform.current_engine()
    sg = engine.shotgun
    # Upload File
    sg.upload('Version', version_id, video_path, 'sg_uploaded_movie')
    # Update Version Path
    sg.update('Version', version_id, {'sg_path_to_movie': video_path})


def upload_thumbnail(version_id, thumbnail_path):
    """Upload thumbnail to Version"""

    engine = sgtk.platform.current_engine()
    sg = engine.shotgun
    sg.upload_thumbnail('Version', version_id, thumbnail_path)