"""Core publish logic (no UI)"""
import sgtk
import maya.cmds as mc
import os
import datetime
from . import exporters
from . import version as version_core
from ..utils import add_attributes
import importlib
importlib.reload(exporters)
importlib.reload(version_core)
importlib.reload(add_attributes)


class Publisher:
    """Handles publishing logic without UI"""

    def __init__(self, context, current_version, description=None, asset_type=None, use_playblast=False, media_folder=None, log_callback=None, engine=None, sg=None, tk=None):

        if sg and tk:
            # Get APIs from constructor if passed
            self.tk = tk
            self.sg = sg
        else:
            # Try to get the engine from UI
            try:
                self.engine = sgtk.platform.current_engine()
            except:
                self.engine = engine

            # Get TK and SG from engine or params
            self.tk = self.engine.sgtk
            self.sg = self.engine.shotgun

        self.context = context
        self.file_name = ''
        self.log_callback = log_callback
        self.current_version = current_version
        self.description = description
        self.use_playblast = use_playblast
        self.media_folder = media_folder
        self.asset_type = asset_type
        self.asset_info = {}
        self.results = {
            'version': None,
            'published_files': [],
            'errors': []
        }

    def log(self, message):
        """Log message (call callback if provided)"""

        if self.log_callback:
            try:
                self.log_callback(message)  # ← Llama al callback del UI
                try:
                    self.engine.logger.debug(message)
                except:
                    pass
            except:
                self.log_callback.info(message)

    def publish(self):

        ##################
        # Create Version #
        ##################

        self.log("Creating Version in ShotGrid...")
        self.log(f"CONTEXT --> {self.context}")

        # Get current file
        self.file_path = mc.file(query=True, sceneName=True)
        self.log(self.file_path)
        self.file_name = os.path.splitext(os.path.basename(self.file_path))[0]
        self.log(self.file_name)

        # Get templates
        if self.context.entity['type'].lower() == "asset":
            self.scene_work_template = self.tk.templates["maya_asset_work"]
            self.log(f" self.scene_work_template --> {self.scene_work_template}")
            try:
                self.movie_template = self.tk.templates["maya_asset_playblast_publish"]
            except:
                self.movie_template = False
        else:
            self.scene_work_template = self.tk.templates["maya_shot_work"]
            self.movie_template = self.tk.templates["maya_shot_playblast_publish"]

        # Get fields from file
        self.scene_fields = self.scene_work_template.get_fields(self.file_path)
        self.log(f" self.scene_fields --> {self.scene_fields}")

        # Get version info
        if self.movie_template:
            self.version_movie_path = self.movie_template.apply_fields(self.scene_fields)
            self.version_name, self.version_ext = os.path.splitext(os.path.basename(self.version_movie_path))
        else:
            self.version_movie_path = ""
            self.version_name = f'{self.scene_fields["Asset"]}_{self.scene_fields["name"]}_{self.scene_fields["Task"]}_v{self.scene_fields["version"]:03d}'
            self.version_ext = ".mov"

        # Get User description
        description_with_work_path = f"{self.description} - (Published from {self.file_name})"

        # Create version on SG
        self.version = version_core.create_version(self.context, self.version_name, description_with_work_path)
        self.results['version'] = self.version

        self.log(f"✓ Version created: {self.version['code']}\n")

        ##########################
        # Export published files #
        ##########################

        # Export for Model Task
        if self.context.task['name'] == 'Model':

            if self.asset_type.lower() != 'set':

                # Add attributes on each mesh
                self._add_attributes_to_meshes()
                # Export geo grp as alembic cache
                self._publish_alembic(1001, 1001)
                # Export geo grp as maya .ma
                self._publish_maya_asset()

        # Export for Shading Task
        elif self.context.task['name'] == 'Shading':

            # Add attributes on each mesh
            self._add_attributes_to_meshes()
            # Export geo grp as alembic cache
            self._publish_alembic(1001, 1001)
            # Export geo grp as maya .ma
            self._publish_maya_asset()
            # Export shader and textures
            self._publish_shaders()
            # Export USD 
            self._publish_usd()
            # Export asset as .ass geo + shaders(for elements, not props or characters)
            if self.asset_type == 'ELEM':
                self._publish_Ass()

        # Export for Grooming Task cacacaca
        elif self.context.task['name'] == 'Groom':
            # Export geo grp as alembic cache
            # self._publish_alembic(1001, 1001)
            print ("ESTAMOS PROBANDO")
            # Export geo grp and hair grp as maya .ma(groom dpt debe guardar el pelo IGS en un grupo llamado HAIR, se exportan los dos grupos como .ma)
            self._publish_maya_asset()
            # Export hair as .xgip(se crea un xgip a partir del pelo que haya dentro del grupo HAIR)
            
            # Export hair shader(se exporta el shader igual que en shading)
            self._publish_shaders()
            

        # LAYOUT
        elif self.context.task['name'] == 'Layout':

            # Publish camera sequencer playblast
            print('publish version with video to SG, nothing more (cameras will be exported and shots will be created once sequence is approved or needed by anim/lihgting)')

        # ANIMATION
        elif self.context.task['name'] == 'Animation':

            # Publish version with video to SG to approve shot.
            print('publish version with video to SG, animation will be cached once animation is approved or needed by lighting')

        # LIGHTING
        elif self.context.task['name'] == 'Lighting':

            # Publish version with frames from folder to approve lighting

            # Publish version with rendered frames to approve shot

            # Export lightSets

            print('TO BE DISCUSSED WITH NUBOYANA')

        #######################################
        # Export maya publish scene as backup #
        #######################################

        self._publish_maya_scene()

        ################
        # Export Movie #
        ################

        from ..media import playblast_tool

        # Playblast
        if self.use_playblast:

            self.log("Capturing playblast ---------------\n")

            if self.context.step['name'] == 'Layout':  # if we are in layout, we need to publish full sequence, unless we are on a shot TEMP-----------------------------------------------------------

                output_video = playblast_tool.create_sequence_playblast(self.version_movie_path)

            else:

                output_video = playblast_tool.create_playblast(self.version_movie_path) # in every other case, we just need a playblast from the shot, plabackOptions define frame range

            if output_video:

                self.log("Uploading video ---------------\n")

                version_core.upload_video(self.version['id'], output_video)

                self.log("✓ Video Thumbnail Uploaded\n")

        # Render
        else:

            try:
                self.log("Creating movie from folder images...")

                output_video = playblast_tool.create_movie_from_folder(self.media_folder, output_path=self.version_movie_path)
                if output_video:

                    self.log("Uploading video...")

                    version_core.upload_video(self.version['id'], output_video)

                    self.log("✓ Video Thumbnail Uploaded\n")
            except:
                pass

        ####################
        # Version up Scene #
        ####################

        self.scene_fields["version"] = int(self.current_version) + 1

        new_file = self.scene_work_template.apply_fields(self.scene_fields)

        mc.file(rename=new_file)
        mc.file(save=True)

        self.log(f"Saved work scene as {new_file}\n")

    ########################
    # PUBLISH PLUGINS ######
    ########################

    def _publish_maya_scene(self):

        self.log("Publish Maya Scene -----------")

        # Export current work scene as publish maya scene
        if self.context.entity['type'].lower() == "asset":
            template = self.tk.templates["maya_asset_publish"]
        else:
            template = self.tk.templates["maya_shot_publish"]

        ma_path = template.apply_fields(self.scene_fields)

        # Export
        exporters.export_maya_scene(ma_path)

        # Register Publish
        self._register_publish_to_version(self.context, ma_path, self.scene_fields["version"], "Maya Scene", version_entity=self.version)
        self.results['published_files'].append(ma_path)

        self.log("Maya Scene Published!!\n")

    def _publish_maya_asset(self):

        self.log("Publish Maya Asset -----------")

        # Export current work scene as publish maya scene
        template = self.tk.templates["maya_asset_clean_publish"]
        ma_asset_path = template.apply_fields(self.scene_fields)

        # Create folder if needed
        if not os.path.exists(os.path.dirname(ma_asset_path)):
            os.makedirs(os.path.dirname(ma_asset_path))

        # Choose what is going to be exported on maya file
        if self.asset_type == 'ELEM':
            ma_export_object = self.context.entity['name']

        elif self.context.task['name'] == 'Groom':
            ma_export_object = f"{self.context.entity['name']}|hair"
        
        else:
            ma_export_object = f"{self.context.entity['name']}|geo"

        # Export
        exporters.export_maya_asset(ma_export_object, ma_asset_path)

        # Register Publish
        self._register_publish_to_version(self.context, ma_asset_path, self.scene_fields["version"], "Maya Scene", version_entity=self.version)
        self.results['published_files'].append(ma_asset_path)

        self.log("✓ Maya Asset Published!!\n")

    def _publish_alembic(self, frameIn, frameOut):

        self.log("Publish Alembic Geo -----------")

        template = self.tk.templates["asset_alembic_cache"]
        abc_path = template.apply_fields(self.scene_fields)

        # Choose what is going to be exported on alembic file
        if self.asset_type == 'ELEM' or self.context.step['name'] == "Surfacing":
            abc_export_object = self.context.entity['name']
        else: 
            abc_export_object = f"{self.context.entity['name']}|geo"

        # Export
        exporters.export_alembic(abc_export_object, abc_path, frameIn, frameOut)

        # Register Publish
        self._register_publish_to_version(self.context, abc_path, self.scene_fields["version"], "Alembic Cache", version_entity=self.version)
        self.results['published_files'].append(abc_path)

        self.log("✓ Alembic Geo Published!!\n")

    def _publish_Ass(self):

        self.log("Publish Ass Standin -----------")

        # Kick ASS
        template = self.tk.templates["asset_ass_cache"]
        assPath = template.apply_fields(self.scene_fields)

        # Create folder if needed
        if not os.path.exists(os.path.dirname(assPath)):
            os.makedirs(os.path.dirname(assPath))

        self.log(f"Exported ass: {assPath}")

        # Export
        exporters.export_ass(f"{self.context.entity['name']}|geo", assPath)

        # Register Publish
        self._register_publish_to_version(self.context, assPath, self.scene_fields["version"], "ASS Cache", version_entity=self.version)
        self.results['published_files'].append(assPath)

        self.log("✓ Ass Standin Published!!\n")

    def _publish_shaders(self):

        self.log("Publish Shaders -----------")

        # Get shaders export path
        template = self.tk.templates["maya_asset_shader_publish"]
        shaders_path = template.apply_fields(self.scene_fields)

        # Generate textures export folder
        template = self.tk.templates["texture_folder_publish"]
        textures_export_folder = template.apply_fields(self.scene_fields)

        # Export

        if self.context.task['name'] == 'Grooming':
            shaders_scene_path, textures_dict = exporters.export_shaders_and_textures_for_hair(self.context.entity['name'], shaders_path, textures_export_folder)
        else:
            shaders_scene_path, textures_dict = exporters.export_shaders_and_textures(self.context.entity['name'], shaders_path, textures_export_folder)

        # Register Publish
        self._register_publish_to_version(self.context, shaders_scene_path, self.scene_fields["version"], "Maya Shaders", version_entity=self.version, extra_info={"sg_textures": str(textures_dict)})
        self.results['published_files'].append(shaders_scene_path)

        self.log("✓ Shaders Published!!\n")

    def _publish_usd(self):

        self.log("Publish USD -----------")

        # Find geo grp using context entity name and export cache
        template = self.tk.templates["maya_asset_scene_usd_publish"]
        usd_path = template.apply_fields(self.scene_fields)

        success = exporters.export_usd(usd_path)

        if success:
            # Register Publish
            self._register_publish_to_version(self.context, usd_path, self.scene_fields["version"], "Usda File", version_entity=self.version)
            self.results['published_files'].append(usd_path)

            self.log("✓ USD Published!!\n")
        else:
            self.log(f"❌ ERROR: USD not exported...")

    ########################
    # UTILS ################
    ########################

    def _add_attributes_to_meshes(self):

        # This info is general for all meshes
        self.asset_info = {'GUS_asset_id': self.context.entity['id'],
                           'GUS_asset_name': self.context.entity['name'],
                           'GUS_asset_type': self.asset_type,
                           'GUS_source_scene': self.file_name,
                           'GUS_source_task': self.context.task['name'],
                           'GUS_publish_time': str(datetime.datetime.now()),
                           'GUS_user_name': self.context.user['name']
                           }

        add_attributes.add_attributes_to_geo_meshes(self.context.entity['name'], self.asset_info)

    def _register_publish_to_version(self, context, file_path, version_number, file_type, version_entity=None, extra_info=None):
        """
        Register a Published File in ShotGrid

        Args:
            context: ShotGrid context
            file_path (str): Path to published file
            version_number (int): Version number
            file_type (str): Published file type (e.g., "Maya Scene", "Alembic Cache")
            version_entity (dict): Optional Version to link to

        Returns:
            dict: Created PublishedFile entity
        """

        engine = sgtk.platform.current_engine()
        tk = engine.sgtk

        # Generate publish name
        file_name = os.path.basename(file_path)
        publish_name = os.path.splitext(file_name)[0]

        # Register
        publish = sgtk.util.register_publish(
            tk,
            context,
            file_path,
            publish_name,
            version_number,
            published_file_type=file_type,
            version_entity=version_entity,
            sg_fields=extra_info
        )

        return publish
