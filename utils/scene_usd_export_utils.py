# Copyright (c) 2024 ShotGrid Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the ShotGrid Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the ShotGrid Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by ShotGrid Software Inc.

"""
Simplified utilities for exporting Maya scenes to USD format.

This module provides functions for exporting entire Maya scenes to USD files,
duplicating Maya's native "Export As USD" functionality. No complex group
handling - just export everything visible in the scene.
"""

import os
import maya.cmds as cmds
import maya.mel as mel
import sgtk


def export_scene_to_usd(output_path, settings=None):
    """
    Export the entire Maya scene to USD format (simplified approach).
    
    This function replicates Maya's native "Export As USD" functionality,
    exporting all visible geometry, materials, and scene data to a single file.
    
    :param str output_path: Path where the USD file should be saved
    :param dict settings: Export settings dictionary
    :return: True if export successful, False otherwise
    :rtype: bool
    """
    
    if settings is None:
        settings = {}
    
    # Get logger
    logger = sgtk.platform.get_logger(__name__)
    
    logger.info(f"Starting simplified USD scene export to: {output_path}")
    
    # First check if Maya USD plugin is available and loaded
    if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
        logger.warning("mayaUsdPlugin not loaded, attempting to load...")
        try:
            cmds.loadPlugin("mayaUsdPlugin")
            logger.info("Successfully loaded mayaUsdPlugin")
        except Exception as e:
            logger.error(f"Failed to load mayaUsdPlugin: {str(e)}")
            logger.error("Maya USD plugin is required for USD export. Please ensure mayaUsdPlugin is installed.")
            return False
    
    # Validate output path
    if not output_path:
        logger.error("Output path is required")
        return False
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Check if there's anything to export
    geometry_nodes = cmds.ls(geometry=True, noIntermediate=True)
    if not geometry_nodes:
        logger.warning("No geometry found in scene to export")
        return False
    
    logger.info(f"Found {len(geometry_nodes)} geometry nodes to export")
    
    try:
        # Configure export settings
        export_config = _get_scene_export_configuration(settings)
        
        # Log the configuration for debugging
        logger.debug(f"Export configuration: {export_config}")
        
        # Perform the USD export (entire scene)
        success = _execute_scene_usd_export(
            output_path=output_path,
            config=export_config
        )
        
        if not success:
            logger.error("USD scene export command failed")
            # Check common failure reasons
            if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
                logger.error("mayaUsdPlugin is not loaded! Attempting to load...")
                try:
                    cmds.loadPlugin("mayaUsdPlugin")
                    logger.info("Successfully loaded mayaUsdPlugin, please try export again")
                except:
                    logger.error("Failed to load mayaUsdPlugin - plugin may not be installed")
            return False
        
        # Validate the exported file
        if not _validate_usd_file(output_path):
            logger.error(f"Exported USD file validation failed: {output_path}")
            logger.error(f"File exists: {os.path.exists(output_path)}")
            if os.path.exists(output_path):
                logger.error(f"File size: {os.path.getsize(output_path)} bytes")
            return False
        
        logger.info(f"Successfully exported scene USD file: {output_path}")
        logger.info(f"File size: {os.path.getsize(output_path)} bytes")
        return True
        
    except Exception as e:
        logger.error(f"USD scene export failed with exception: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False


def _get_scene_export_configuration(settings):
    """
    Generate USD export configuration from settings (simplified).
    
    :param dict settings: User-provided settings
    :return: Export configuration dictionary
    :rtype: dict
    """
    
    # Simplified default configuration
    config = {
        "file_format": "usda",  # ASCII USD for readability
        "include_materials": True,
        "include_cameras": False,
        "include_lights": False,
        "export_visible_only": True,
        "frame_range": None,  # Static export by default
        "export_uvs": True,
        "export_normals": True,
        "export_colors": True,
        "merge_transform_and_shape": True,
        "strip_namespaces": False,
        "selection": False  # Export all (not selection)
    }
    
    # Update with user settings
    if settings:
        config.update(settings)
    
    # Normalize format setting
    file_format = config.get("format", "usda").lower()
    if file_format in ["usda", "usdc"]:
        config["file_format"] = file_format
    else:
        config["file_format"] = "usda"  # default to ASCII
    
    return config


def _execute_scene_usd_export(output_path, config):
    """
    Execute the actual USD export command for the entire scene using Maya USD.

    Uses mayaUSDExport to export directly to USD format.

    :param str output_path: Output file path
    :param dict config: Export configuration
    :return: True if successful, False otherwise
    :rtype: bool
    """
    try:
        logger = sgtk.platform.get_logger(__name__)

        # Build Maya USD export arguments
        export_kwargs = {
            "file": output_path,
            "selection": config.get("selection", False),
            "defaultUSDFormat": config.get("file_format", "usda"),
        }

        # Material export
        if config.get("include_materials", True):
            export_kwargs["shadingMode"] = "useRegistry"
            export_kwargs["materialsScopeName"] = "Looks"

        # UV and normal export
        if config.get("export_uvs", True):
            export_kwargs["exportUVs"] = True

        if config.get("export_normals", True):
            export_kwargs["exportSkels"] = "auto"

        if config.get("export_colors", True):
            export_kwargs["exportColorSets"] = True

        # Visibility settings
        if config.get("export_visible_only", True):
            export_kwargs["exportVisibility"] = True

        # Transform and shape merging
        if config.get("merge_transform_and_shape", True):
            export_kwargs["mergeTransformAndShape"] = True

        # Namespace handling
        if config.get("strip_namespaces", False):
            export_kwargs["stripNamespaces"] = True

        # Handle frame range for animation
        frame_range = config.get("frame_range")
        if frame_range:
            export_kwargs["frameRange"] = (frame_range[0], frame_range[1])
            logger.info(f"Exporting frame range: {frame_range[0]} to {frame_range[1]}")

        # Log export settings
        logger.info(f"Executing Maya USD export with settings: {export_kwargs}")

        # Log Maya and plugin version info
        maya_version = cmds.about(version=True)
        logger.info(f"Maya version: {maya_version}")

        # Check if Maya USD plugin is loaded
        if not cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
            logger.warning("mayaUsdPlugin not loaded, attempting to load...")
            try:
                cmds.loadPlugin("mayaUsdPlugin")
                logger.info("Successfully loaded mayaUsdPlugin")
            except Exception as e:
                logger.error(f"Failed to load mayaUsdPlugin: {str(e)}")
                return False

        if cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
            plugin_version = cmds.pluginInfo("mayaUsdPlugin", query=True, version=True)
            logger.info(f"mayaUsdPlugin version: {plugin_version}")

        # Execute the export using Maya USD export command
        logger.info("Calling cmds.mayaUSDExport for USD export...")
        result = cmds.mayaUSDExport(**export_kwargs)

        # Check if result indicates success
        if result:
            logger.info(f"Maya USD export command returned: {result}")
        else:
            logger.warning(f"Maya USD export command returned: {result}")

        return True

    except RuntimeError as e:
        logger = sgtk.platform.get_logger(__name__)
        logger.error(f"Maya USD export runtime error: {str(e)}")
        # Try to provide more specific error information
        if "mayaUsdPlugin" in str(e):
            logger.error("Maya USD plugin may not be loaded. Ensure mayaUsdPlugin is available.")
        elif "selection" in str(e).lower():
            logger.error("Export failed due to selection issues. Check scene has exportable geometry.")
        return False
    except Exception as e:
        logger = sgtk.platform.get_logger(__name__)
        logger.error(f"USD export command execution failed: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False


def _validate_usd_file(file_path):
    """
    Validate that the exported USD file is valid and accessible.
    
    :param str file_path: Path to the USD file
    :return: True if file is valid, False otherwise
    :rtype: bool
    """
    
    # Check if file exists
    if not os.path.exists(file_path):
        return False
    
    # Check if file has content
    if os.path.getsize(file_path) == 0:
        return False
    
    # For USDA files, do a basic text validation
    if file_path.lower().endswith('.usda'):
        try:
            with open(file_path, 'r') as f:
                content = f.read(100)  # Read first 100 chars
                # Check for basic USD header
                if "#usda" not in content:
                    return False
        except:
            return False
    
    return True


def get_supported_formats():
    """
    Get list of supported USD export formats (simplified).
    
    :return: List of supported format strings
    :rtype: list
    """
    return ["usda", "usdc"]


def check_usd_plugin_status():
    """
    Check the status of Maya USD plugin for USD export.

    :return: Dictionary with plugin status information
    :rtype: dict
    """

    status = {
        "available": False,
        "loaded": False,
        "version": None,
        "export_command_available": False
    }

    try:
        # Check if mayaUsdPlugin exists
        if cmds.pluginInfo("mayaUsdPlugin", query=True, registered=True):
            status["available"] = True

            # Check if loaded
            if cmds.pluginInfo("mayaUsdPlugin", query=True, loaded=True):
                status["loaded"] = True

                # Check version if possible
                try:
                    version = cmds.pluginInfo("mayaUsdPlugin", query=True, version=True)
                    status["version"] = version
                except:
                    pass

            # Check export command availability
            try:
                # Check if mayaUSDExport command exists
                status["export_command_available"] = mel.eval('exists "mayaUSDExport"')
            except:
                pass

    except Exception:
        pass

    return status


def get_scene_export_info():
    """
    Get information about the current scene for USD export.
    
    :return: Dictionary with scene information
    :rtype: dict
    """
    
    info = {
        "geometry_count": 0,
        "material_count": 0,
        "camera_count": 0,
        "light_count": 0,
        "scene_name": "",
        "has_animation": False
    }
    
    try:
        # Count geometry nodes
        geometry_nodes = cmds.ls(geometry=True, noIntermediate=True)
        info["geometry_count"] = len(geometry_nodes) if geometry_nodes else 0
        
        # Count materials (shading engines)
        materials = cmds.ls(type="shadingEngine")
        info["material_count"] = len(materials) if materials else 0
        
        # Count cameras
        cameras = cmds.ls(type="camera")
        info["camera_count"] = len(cameras) if cameras else 0
        
        # Count lights
        lights = cmds.ls(lights=True)
        info["light_count"] = len(lights) if lights else 0
        
        # Get scene name
        scene_path = cmds.file(query=True, sceneName=True)
        if scene_path:
            info["scene_name"] = os.path.basename(scene_path)
        
        # Check for animation (simplified - check if timeline has more than 1 frame)
        start_time = cmds.playbackOptions(query=True, minTime=True)
        end_time = cmds.playbackOptions(query=True, maxTime=True)
        info["has_animation"] = (end_time > start_time)
        
    except Exception as e:
        logger = sgtk.platform.get_logger(__name__)
        logger.debug(f"Error getting scene export info: {str(e)}")
    
    return info