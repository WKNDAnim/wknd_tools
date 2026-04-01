# from Deadline.Scripting import *

import sys
sys.path.insert(0, r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config\install\core\python")
sys.path.insert(0, r"Z:\05Framework\users\aferraz")

import sgtk
import os
import shutil

import wknd_tools
from wknd_tools.core import version as version_core
from wknd_tools.media import playblast_tool
import importlib
importlib.reload(version_core)
importlib.reload(playblast_tool)

#######################
# Conectar a ShotGrid #
#######################

tk = sgtk.sgtk_from_path(r"Z:\05Framework\users\aferraz\packages\dev_tk\master_tk_config")
sg = tk.shotgun

##################################################


def publish(shot_name):

    task = sg.find_one("Task",
                       [["entity.Shot.code", "is", shot_name], ["content", "is", "FLay"]],
                       ["entity.Shot.sg_sequence"])

    fields = {
        "Step": "FLAY",
        "Task": "FLay",
        "name": "scene",
        "Shot": shot_name,
        "Sequence": task["entity.Shot.sg_sequence"]["name"],
        "version": 1
    }

    # Get templates
    template_work = tk.templates["maya_shot_work"]
    template_render = tk.templates["maya_shot_render_exr_root"]
    template_movie = tk.templates["maya_shot_playblast_publish"]

    # Get paths
    scene_path = template_work.apply_fields(fields)
    media_folder = template_render.apply_fields(fields)
    version_movie_path = template_movie.apply_fields(fields)

    context = tk.context_from_entity("Task", task["id"])
    description = "Publish from auto FLAY to review"
    version_name = os.path.splitext(os.path.basename(version_movie_path))[0]

    print(f"\t - VERSION NAME --> {version_name}")

    ########################
    # Create version on SG #
    ########################

    print("Creating Version...")

    version = version_core.create_version(context, version_name, description, sg=sg)

    print(f"Version created: {version['code']}\n")

    #############
    # Render QT #
    #############

    try:
        print("Creating movie from folder images...")
        print(f"\t - Input path --> {media_folder}")
        print(f"\t - Output path --> {version_movie_path}")

        # Get layer path
        layers = os.listdir(media_folder)
        layer_root_path = os.path.join(media_folder, layers[0])

        print(f"\t - layer_root_path --> {layer_root_path}")

        output_video = playblast_tool.create_movie_from_folder(layer_root_path, output_path=version_movie_path)

        print(f"\t ** output_video --> {output_video}")

    except:

        print("ERROR: Cannot create movie from folder...\n")
        output_video = False
        sys.exit(1)

    print("- Uploading video...")
    if output_video:

        version_id = version['id']
        video_path = output_video

        # Upload File
        sg.upload('Version', version_id, video_path, 'sg_uploaded_movie')
        # Update Version Path
        sg.update('Version', version_id, {'sg_path_to_movie': video_path})

        print("- Video Uploaded\n")

    else:

        print("ERROR: Cannot upload movie to SG...\n")
        sys.exit(1)

    fields["version"] = 2
    scene_path_new = template_work.apply_fields(fields)
    print(f"INFO --> Incrementing scene version... ({scene_path_new})")
    shutil.copy2(scene_path, scene_path_new)

    print("INFO --> Updating task status to PSR")

    # Cambiamos el status de la task FLAY a Pending Sup Review
    sg.update(
        "Task",
        task["id"],
        {"sg_status_list": "psr"}
        )


def main():

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--shot", required=True)
    args = parser.parse_args()

    print(f"[POST] SHOT: {args.shot}", flush=True)

    publish(args.shot)

    print("Version created and movie DONE! :)")


##################################################

if __name__ == "__main__":
    main()
