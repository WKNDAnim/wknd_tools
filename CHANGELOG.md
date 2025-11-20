# Changelog

All notable changes to the Toolkit Configuration will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.8.3] - 2025-11-XX

## Added
   - Avoid `cleanAssets` and `scene.` when filtering lastest published files.

## Changed
   - Tk-Maya:
      - Tk-multi-workfiles2:
         - Code logic changed when creating new SETs for the first time. Added Window to choose for Asset's variations.
   - Tk-Maya:
      - Tk-multi-loader2:
         - Namespace is now only the name of the entity + the name of the variation


## [1.8.2] - 2025-11-11

# Added
   - Templates added:
      - maya_asset_clean_publish
      - texture_folder_publish
      - asset_ass_cache
      - maya_shot_playblast
      - maya_shot_playblast_publish
      - atic_shot_audio

   - Shelf `WKND` to use wknd_tools as publisher

# Changed
   - Tk-Maya:
      - Tk-multi-workfiles2:
         - New File for Previs: Now Loaded things are parented to its respective group



## [1.8.1] - 2025-11-04

# Added
   - Custom WKND Publish files - NOT IMPLEMENTED YET -
   - Tk-Maya:
      - Tk-multi-workfiles2:
         - Add `Grooming` to the same implementation of `Surfacing` when New File

### Changed
   - Tk-substancepainter:
      - Changed git repo to WKNDAnim\tk-substancepainter.git

### Fixed
   - Tk-Maya:
      - Tk-multi-workfiles2:
         - Status update was working only for Shots. Unintent in order to make it work for Assets too.

## [1.8.0] - 2025-10-31

### Changed and Added
   - Tk-Maya:
      - Tk-multi-publish2:
         - Avoid reference import logic when publishing SETs
            - publish_session.py plugin now inherits from {self} not {config}
      - Tk-multi-workfiles2:
         - Builder for mastershots added
            - Camera Sequencer setter
               - Adapted from Carlos code
            - Load Assets to MasterShot as props
               - `loadRiggedProps` variable added to `_latest_approved_publishes_by_asset`
            - Import SETs instead reference them

## [1.7.8] - 2025-10-31

   - NOTHING ADDED - JUST TESTING NEW REPO

## [1.7.7] - 2025-10-31

   - NOTHING ADDED - JUST TESTING NEW REPO

## [1.7.6] - 2025-10-31

   - NOTHING ADDED - JUST TESTING NEW REPO

## [1.7.5] - 2025-10-23

### Fixed
- Tk-multi-publish2:
   -Tk-Maya:
      - Publish Session Geometry: Publish failed when no Root. Now fixed.

## [1.7.4] - 2025-10-23

### Changed
- Tk-multi-workfiles2:
   -Tk-Maya:
      - Avoid loading Rig on SET creation

## [1.7.3] - 2025-10-22

### Changed
- Tk-multi-publish2:
   -Tk-Maya:
      - Colletor:
         - Add `Movies template` to Collector settings
         - Force Collector to only collect Playblast of the openned scene
         - Show Version on Playblast Publish Item name
      - Publish session geometry:
         - Get frame range of animation only if any object within the root group is animated
         - Root now must be stictly equal to AssetName

## [1.7.2] - 2025-10-21

### Changed
- Tk-substancepainter engine version changed to v
   - Export presets `Gus UDIM` and `Gus no UDIM` updated

## [1.7.1] - 2025-10-20

### Changed
- Publish Session Geometry Publish Plugin:
   - Now only adds Custom Attributes to meshes within -root
   - Deleted -renderableOnly flag from AbcExport arguments due to hide meshes within root

### Fixed
- Loading logic for Assets on SET Builder (scene operation tk-maya):
   - Now group published files by `AssetType{AssetName{Step{Task{FileType{...}}}}}`
      - Order dict every groupby loop due to itertools.groupby() need an ordered input

## [1.7.0] - 2025-10-16

### Added
- Tk-substancepainter engine version changed to v1.3.7: 
   - 4 new export presets added:
      - Gus FxMask no UDIM
      - Gus PCMmask no UDIM
      - Gus IdMask no UDIM
      - Gus BWMask no UDIM
   
- Tk-multi-workfiles2 custom implementation for tk-Maya:
   - Avoid showing My Task on UI as we do not need it.
   - New File:
      - Resolve work template to save the scene
      - If the Asset is of type SET: 
         - Get the last publish of all its subAssets (from field `sg_link__asset__1`)
            - Load an the `Maya Scene` if it's a PROP or a CHARACTER. Otherwise, load `Alembic Cache`.
            - Load the last published shaders and connect it to its mesh through the mesh attribute `{mesh}.GUS_relatedShader`

- Tk-multi-publish2 custom implementation for tk-Maya:
   - Publish File plugin imports references before publishing scene file:
      - The scene is copied to the publish area and then we import assets via mayapy script located on `{config}/tk-multi-publish2/maya/utils` folder
   - Avoid publishing for SETs:
      - Publish Session Geometry plugin not accepted if `sg_asset_type` is SET
      - Publish USD plugin not accepted if `sg_asset_type` is SET
      - Publish Shaders plugin not accepted if `sg_asset_type` is SET

### Changed
- Scene operation hook for Maya moved to {config} folder for ALL envs
- Publish File plugin for Maya moved to {config} folder for asset_step env
- Publish Session Geometry plugin for Maya moved to {config} folder for asset_step env
- Publish Name of shaders changed to `Scene Shaders` for easily reconnect with its mesh

### Fixed
- Task folder created on schema for Shots (../seq/shot/step/task/...). It was missing in the schema.

## [1.6.0] - 2025-10-16

### Added
- Custom Maya loader action for Arnold aiImage nodes
  - New `arnold_image` action available for Texture type publishes in Maya
  - Creates Arnold `aiImage` shader nodes with texture path automatically set
  - Automatic Arnold plugin (mtoa) loading if not already loaded
  - Custom hook implementation at `config/hooks/tk-multi-loader2/maya/tk-maya_actions.py`
- Enhanced tk-multi-loader2 Maya configuration with custom actions hook

### Changed
- Updated tk-multi-loader2 Maya settings to use custom actions hook
- Extended Texture type action mappings to include `arnold_image` action

## [1.5.7] - 2025-10-15

### Changed
   - UDIM template key is now of type String due to we are not able to make Sequence keys optional.
   - New File for Maya when Step is Surfacing now creates an empty scene if no Model Approved Published Scenes are found.


## [1.5.6] - 2025-10-14

### Added
- `settings.tk-multi-workfiles2.maya` env added to be able to use hooks with no entity referred env
- Tk-multi-publish2:
   - Publish_session_geometry: 
      - Uses `-root` flag of AbcExport mel function for allowing us to export only the geo within the `{AssetName}` group.
      - Adds custom User Attributes to shapes with custom SG information:
         - "GUS_SG_assetName"
         - "GUS_SG_entityId"
         - "GUS_SG_assetType"
         - "GUS_SG_version"
         - "GUS_SG_workScene"
         - "GUS_relatedGroom"
         - "GUS_relatedShader"

### Changed
- Tk-multi-workfiles2:
   - Maya:
      - Scene operation Hook is now located on `{config}` folder
      - New File: 
         - When Step is SURFACING: Search in SG for the last approved Maya scene of MODEL Step and saves it as the first version for the new Step.


### Fixed
- Texture templates now have `{name}` field of scene

## [1.5.5] - 2025-10-09

### Changed
- Tk-substancepainter now choose which USD load on New File action based on `{name}` key os the Usda publishes
   - Prompts a Combo box for the user to choose `{name}` key if more than one published files wit different `{name}` key are found
      - Takes always the last published version
   - If only finds one `{name}` key for every published usd, do not prompt the user to choose

## [1.5.4] - 2025-10-09

### Changed
- Updated USD publish templates to include `{name}` token for better naming consistency
  - `maya_asset_scene_usd_publish`: Now uses `{Asset}_{name}_{Task}_v{version}.usda`
  - `maya_shot_scene_usd_publish`: Now uses `{Shot}_{name}_{Task}_v{version}.usda`
  - USD exports now inherit the `{name}` token from parent Maya work files, matching work file naming conventions

### Fixed
- Removed duplicate `maya_asset_scene_usd_publish` template definition in templates.yml

## [1.5.3] - 2025-10-08

### Added
- Tk-substancepainter engine version updated on git from v1.3.5 to v1.3.6:
   - Export presset `Gus LowUDIM` added.

### Fixed
- Delete Harcoded USD load for tests on tk-multi-workfiles2 for tk-substancepainter

## [1.5.2] - 2025-10-07

### Changed
- Tk-Substancepainter engine version changed on git from v1.3.4 to v1.3.5

## [1.5.1] - 2025-10-06

### Changed
- Updated Prerelease pipeline configuration with specific package paths:
  - Added prerelease sanitykit path
  - Added prerelease setup_turnaround path
- MAYA_SHELF_PATH environment variable now set for all Maya launches

## [1.5.0] - 2025-10-06

### Added
- Shader publishing system for Maya
  - Automatic detection and collection of all shaders used in the scene
  - All shaders published together in a single Maya file with complete networks (materials, textures, utilities)
  - Export selection workflow for clean shader files
  - Template-based versioning for shader publishes
  - Works in both asset_step and shot_step contexts
  - Supports face-level and component-level shader assignments
- Maya shader publish templates:
  - `maya_asset_shader_publish`: `{Asset}_{name}_shaders_v{version}.{maya_extension}`
  - `maya_shot_shader_publish`: `{Shot}_{name}_shaders_v{version}.{maya_extension}`

### Changed
- Enhanced Maya collector to detect and collect shaders from scene geometry
- Robust shader collection that properly handles:
  - Direct shape assignments
  - Component selections (faces, edges, vertices)
  - Transform-level assignments
  - Multiple shading engines per material
- Shader network traversal includes file nodes, placement nodes, bump maps, color correction, and utility nodes
- Only collects materials with actual geometry assignments (excludes unused materials)
- Single publish item created for all scene shaders (instead of individual items per shader)

## [1.4.3] - 2025-10-01

### Changed

- Tk-substancepainter:
   - Engine version chanded to v1.3.4
   - Change texture publish routine on tk-substancepainter from move to copy to publish area.

## [1.4.2] - 2025-10-06

### Added
- Pipeline configuration-specific PYTHONPATH setup for Maya launches
  - Primary configuration: Basic library paths
  - Prerelease configuration: Includes prerelease sanitykit and setup_turnaround packages
  - Dev configuration: Includes user-specific development packages
- MAYA_SHELF_PATH environment variable configuration for custom Maya shelves

### Changed
- Enhanced `before_app_launch.py` hook to detect pipeline configuration and apply environment variables accordingly

## [1.4.1] - 2025-10-01

### Changed
- Replaced Arnold USD export with Maya USD plugin export for better compatibility
- USD scene export now uses native `mayaUSDExport` command instead of `arnoldExportAss`
- Updated USD export configuration to use Maya USD plugin parameters and settings
- Enhanced USD export with additional options: UV export, color sets, visibility, and namespace handling

### Fixed
- USD export no longer requires Arnold plugin (MtoA) to be installed
- Improved USD export reliability across different Maya configurations

## [1.4.0] - 2025-09-25

### Added
- Substance Painter integration on FPT Toolkit from https://github.com/lola-post/tk-substancepainter.git

   - As the GitHub implementation mentioned above were not working with new versions of the software, we've made some changes on the code:
      - JavaScript plugin 'adapted' to Qt6
      - The JS plugin now is copied to {SubstancePainter_Installation}/javascript/plugins
      - Python engine code adapted to PySide6
      - Engine location is now on our Organization Git
      - Avoid showing Shots and My Tasks tab on tk-multi-workfiles dialog
      - Tk-multi-workfiles dialog is prompted on engine start up
      - Custom export presets added by copying {engine}/resources/exportPresets folder to user prefs on bootstrap
      - OCIO variable setted on bootstrap

   - Added NEW FILE implementation for tk-substancepainter:
      - Create project by loading last Shading USD published mesh
      - Save File to resolved template path
      - Export path setted based on project
      - Project Settings setted based on Pablo's template

   - Added new Publish routine:
      - Textures have to be exported before publishing in order the collector can see it
      - Each shadingGroup-textureLayer are independent Texture publishes
         - Shading groups should be filtered by "^[-A-Za-z0-9]+$"
      - Textures are moved from work to publish and texture version number is added

### Changed
- Adobe Framework version update to v1.2.11

### Issues
- In Substance Painter, collector and js connection do not work the first time so you should press Publish button twice to get it work. 
   - Seems the issue comes from the python-js websocket.
- Not an issue but an improvement... In Substance Painter Collector we should get the mesh name with the USD API, now is done "manually" with various template keys...

## [1.3.0] - 2025-08-22

### Added
- Simplified USD Publisher for Maya that duplicates native "Export As USD" functionality
- New scene-based USD export workflow with no special group requirements
- Automatic scene USD collection that exports all visible geometry, materials, and scene data

### Changed
- **BREAKING**: Replaced complex group-based USD publishing system (proxy/render groups) with simplified scene export
- USD Publisher now exports entire visible scene as single USDA file instead of separate group files
- Simplified USD templates from 4 complex templates to 2 simple ones:
  - `maya_asset_scene_usd_publish`: `@asset_root/publish/usd/{Asset}_{Task}_v{version}.usda`
  - `maya_shot_scene_usd_publish`: `@shot_root/publish/usd/{Shot}_{Task}_v{version}.usda`
- Updated Maya publisher configuration to use new simplified plugin settings

### Removed
- **BREAKING**: USD group validation system and naming requirements (no longer need "proxy"/"render" groups)
- Complex USD group detection logic from Maya collector
- Separate proxy/render export paths and templates
- Group validation utilities and complex export configuration options
=======
## [1.2.2] - 2025-09-09

### Fixed
- Downgrading tk-adobe-framework to 1.2.4 based on Autodesk reply:
```
Hi Alberto,
 
Our dev identify the issue here and indeed it's related to Creative Cloud update, they will have a permanent fix in the next tk-framework-adobe version as they will need to alter the current version to adhere to Adobe new requirment.

The current workaround is to downgrade the tk-framework-adobe to v1.2.4, we tested this internally and tk-framework-adobe v1.2.4 works with no issues.

Let me know how it go! Again thank you for your understanding and patience during the investigation process, and I look forward to hearing from you soon! 

Kind Regards,

Murad Abujaish
Customer Technical Success  
Autodesk
```

## [1.2.1] - 2025-07-23

### Fixed
- Photoshop published template changed to fit queried layer names
- Changed code order of "# Modify template to fit context #" to be able to use fields resolved from SG template
- Update Variation input window tittles for better artist understanding 

## [1.2.0] - 2025-07-15

### Added
- Improved New File logic on Photoshop:
   - Load template file and save it in the right path at once
   - Update Entity and Task status to IP

## [1.1.1] - 2025-07-09

### Fixed
- Enhanced ShotGrid query filtering in Photoshop template loading system
- Added specific code filtering for published files to improve template asset discovery
- Improved reliability of template file selection in scene_operation_tk-photoshopcc.py

## [1.1.0] - 2025-07-02

### Added
- Support for Template assets using asset_type "template"
- Dynamic ShotGrid query system for Photoshop template loading

### Changed
- Updated Photoshop scene operation hook to use ShotGrid API instead of hardcoded paths
- Template loading now queries for latest published PhotoshopTemplate asset from Art/Main task
- Enhanced error handling for missing template assets in ShotGrid

### Fixed
- Eliminated hardcoded template file paths in Photoshop integration
- Improved reliability of template loading system

## [1.0.0] - 2025-07-01

### Added
- Initial toolkit configuration for "gus" project
- Comprehensive pipeline setup for VFX/Animation workflows
- Support for Maya, Nuke, Photoshop, Houdini, 3ds Max, and other DCCs
- Asset and Shot pipeline templates with proper versioning
- Automated Shotgrid configuration sync system
- Custom hooks for Photoshop template auto-loading
- Background publishing system with UUID tracking
- Playblast publishing workflows for Maya
- Version control system with semantic versioning
- Automated ZIP creation and upload to Shotgrid
- ConfigurationBackup entity integration for version history

### Changed
- Updated core Toolkit version to v0.22.2
- Enhanced Maya workspace templates for playblast support
- Improved error handling in publish workflows

### Fixed
- Resolved template loading issues in Photoshop integration
- Fixed background publishing thumbnail generation
- Corrected path resolution in cross-platform environments

---

## Guidelines for Updating This Changelog

When making changes to the configuration:

1. **Add entries under [Unreleased]** section
2. **Use these categories:**
   - `Added` for new features
   - `Changed` for changes in existing functionality  
   - `Deprecated` for soon-to-be removed features
   - `Removed` for now removed features
   - `Fixed` for bug fixes
   - `Security` for vulnerability fixes

3. **When releasing a new version:**
   - Move entries from [Unreleased] to new version section
   - Update version in `config/version.py`
   - Create new [Unreleased] section

4. **Example entry format:**
   ```
   ### Added
   - New Maya 2024 integration with USD support
   - Custom validation rules for asset naming conventions
   
   ### Changed  
   - Updated Nuke templates for 4K rendering workflows
   - Enhanced error reporting in publisher
   
   ### Fixed
   - Bug in sequence folder creation hook
   - Template resolution issues on Windows
   ```

5. **Version numbering:**
   - **MAJOR**: Breaking changes, incompatible API changes
   - **MINOR**: New features, backwards compatible
   - **PATCH**: Bug fixes, backwards compatible