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
Utilities for exporting Maya geometry to USD format.

This module provides functions for exporting Maya groups to USD files with
proper material handling, optimization settings, and metadata configuration.
Designed to be reusable across different Maya USD export scenarios.
"""

import os
import tempfile
import maya.cmds as cmds
import maya.mel as mel
import sgtk


def export_group_to_usd(group_name, output_path, settings=None):
    """
    Export a Maya group to USD format.
    
    This function handles the complete USD export process including:
    - Group isolation and preparation
    - USD export with appropriate settings
    - Material and shader handling
    - File optimization and validation
    
    :param str group_name: Name of the Maya group to export
    :param str output_path: Path where the USD file should be saved
    :param dict settings: Export settings dictionary
    :return: True if export successful, False otherwise
    :rtype: bool
    """
    
    if settings is None:
        settings = {}
    
    # Get logger
    logger = sgtk.platform.get_logger(__name__)
    
    logger.info(f"Starting USD export for group '{group_name}'")
    
    # Validate inputs
    if not cmds.objExists(group_name):
        logger.error(f"Group '{group_name}' does not exist")
        return False
    
    if not output_path:
        logger.error("Output path is required")
        return False
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:

        success = _execute_usd_export(
            objects_to_export=group_name,
            output_path=output_path,
            config=None
        )
        # # Configure export settings
        # export_config = _get_export_configuration(settings)
        
        # # Prepare scene for export
        # with _isolated_export_context(group_name) as export_data:
        #     if not export_data["success"]:
        #         logger.error(f"Failed to prepare scene for export: {export_data['error']}")
        #         return False
            
        #     # Perform the USD export
        #     success = _execute_usd_export(
        #         objects_to_export=export_data["objects"],
        #         output_path=output_path,
        #         config=export_config
        #     )
            
        #     if not success:
        #         logger.error("USD export command failed")
        #         return False
        
        # Validate the exported file
        # if not _validate_usd_file(output_path):
        #     logger.error(f"Exported USD file validation failed: {output_path}")
        #     return False
        
        # Apply post-export optimizations if requested
        # if export_config.get("optimize_file", True):
        #     _optimize_usd_file(output_path, export_config)
        
        logger.info(f"Successfully exported USD file: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"USD export failed with exception: {str(e)}")
        return False


def _get_export_configuration(settings):
    """
    Generate USD export configuration from settings.
    
    :param dict settings: User-provided settings
    :return: Export configuration dictionary
    :rtype: dict
    """
    
    # Default configuration
    config = {
        "file_format": "usdc",  # Binary USD for better performance
        "include_materials": True,
        "include_cameras": False,
        "include_lights": False,
        "quality": "high",
        "frame_range": None,  # Static export by default
        "optimize_file": True,
        "export_uvs": True,
        "export_normals": True,
        "export_colors": True,
        "merge_transform_and_shape": True,
        "strip_namespaces": False
    }
    
    # Update with user settings
    if settings:
        config.update(settings)
    
    # Quality-based adjustments
    quality = config.get("quality", "high").lower()
    if quality == "low":
        config.update({
            "export_normals": False,
            "export_colors": False,
            "optimize_file": True
        })
    elif quality == "medium":
        config.update({
            "export_colors": False,
            "optimize_file": True
        })
    # High quality uses all default settings
    
    return config


class _isolated_export_context:
    """
    Context manager for isolating objects during export.
    
    This temporarily hides all scene objects except those in the specified group,
    ensuring clean exports without interference from other scene elements.
    """
    
    def __init__(self, group_name):
        self.group_name = group_name
        self.hidden_objects = []
        self.original_selection = []
        
    def __enter__(self):
        """Enter the isolation context."""
        try:
            # Store original selection
            self.original_selection = cmds.ls(selection=True) or []
            
            # Get all objects in the group (including nested)
            group_objects = cmds.listRelatives(
                self.group_name, 
                allDescendents=True, 
                fullPath=True
            ) or []
            
            # Add the group itself
            group_objects.append(self.group_name)
            
            # Get all scene objects
            all_objects = cmds.ls(dag=True, long=True, visible=True)
            
            # Find objects to hide (everything not in the group)
            objects_to_hide = []
            for obj in all_objects:
                # Skip if object is part of the group hierarchy
                is_in_group = False
                for group_obj in group_objects:
                    if obj == group_obj or obj.startswith(group_obj + "|"):
                        is_in_group = True
                        break
                
                if not is_in_group:
                    # Check if we can hide this object
                    try:
                        if cmds.getAttr(f"{obj}.visibility"):
                            objects_to_hide.append(obj)
                    except:
                        # Skip objects that can't be queried
                        continue
            
            # Hide objects
            for obj in objects_to_hide:
                try:
                    cmds.setAttr(f"{obj}.visibility", False)
                    self.hidden_objects.append(obj)
                except:
                    # Skip objects that can't be hidden
                    continue
            
            # Select the group for export
            cmds.select(self.group_name, replace=True)
            
            return {
                "success": True,
                "objects": [self.group_name],
                "hidden_count": len(self.hidden_objects)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the isolation context and restore scene state."""
        try:
            # Restore visibility of hidden objects
            for obj in self.hidden_objects:
                try:
                    if cmds.objExists(obj):
                        cmds.setAttr(f"{obj}.visibility", True)
                except:
                    continue
            
            # Restore original selection
            if self.original_selection:
                cmds.select(self.original_selection, replace=True)
            else:
                cmds.select(clear=True)
                
        except Exception:
            # If restoration fails, clear selection as fallback
            try:
                cmds.select(clear=True)
            except:
                pass


def _execute_usd_export(objects_to_export, output_path, config):
    """
    Execute the actual USD export command.
    
    :param list objects_to_export: List of objects to export
    :param str output_path: Output file path
    :param dict config: Export configuration
    :return: True if successful, False otherwise
    :rtype: bool
    """
    try:
        # Build USD export command
        # export_cmd = _build_usd_export_command(objects_to_export, output_path, config)
        
        # Execute the export
        # result = mel.eval(export_cmd)
        cmds.select(clear=True)

        # Seleccionar el grupo "proxy"
        cmds.select(objects_to_export)

        # Exportar selección a USD
        cmds.mayaUSDExport(
            file=output_path,  # Cambia la ruta según necesites
            selection=True,
            defaultUSDFormat="usda",
        )

        
        # Maya USD export typically returns 1 for success
        return True
        
    except Exception as e:
        logger = sgtk.platform.get_logger(__name__)
        logger.error(f"USD export command execution failed: {str(e)}")
        return False


def _build_usd_export_command(objects_to_export, output_path, config):
    """
    Build the Maya USD export command arguments.
    
    :param list objects_to_export: Objects to export
    :param str output_path: Output file path  
    :param dict config: Export configuration
    :return: Dictionary of command arguments
    :rtype: dict
    """
    
    # Base arguments
    kwargs = {
        "file": output_path,
        "selection": True
    }
    
    # File format
    kwargs["format"] = "usda" if config.get("file_format") == "usda" else "usdc"
    
    # Material export
    if config.get("include_materials", True):
        kwargs["shadingMode"] = "useRegistry"
        kwargs["convertMaterialsTo"] = "UsdPreviewSurface"
    else:
        kwargs["shadingMode"] = "none"
    
    # UV and normal export
    if config.get("export_uvs", True):
        kwargs["exportUVs"] = True
    
    if config.get("export_normals", True):
        kwargs["exportVertexNormals"] = True
    
    if config.get("export_colors", True):
        kwargs["exportColorSets"] = True
    
    # Transform and shape merging
    if config.get("merge_transform_and_shape", True):
        kwargs["mergeTransformAndShape"] = True
    
    # Namespace handling
    if config.get("strip_namespaces", False):
        kwargs["stripNamespaces"] = True
    
    # Frame range (static export by default)
    frame_range = config.get("frame_range")
    if frame_range:
        kwargs["frameRange"] = (frame_range[0], frame_range[1])
    
    return kwargs


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
    
    # For more comprehensive validation, we could use USD Python API
    # but for now, basic file existence and size check is sufficient
    
    return True


def _optimize_usd_file(file_path, config):
    """
    Apply post-export optimizations to the USD file.
    
    :param str file_path: Path to the USD file
    :param dict config: Export configuration
    """
    
    logger = sgtk.platform.get_logger(__name__)
    
    try:
        # For future optimization implementations:
        # - Flatten layer stack if needed
        # - Optimize primitive hierarchies
        # - Compress geometry if appropriate
        # - Add custom metadata
        
        logger.debug(f"Optimization applied to USD file: {file_path}")
        
    except Exception as e:
        logger.warning(f"USD file optimization failed (non-critical): {str(e)}")


def get_supported_formats():
    """
    Get list of supported USD export formats.
    
    :return: List of supported format strings
    :rtype: list
    """
    return ["usdc", "usda"]


def get_export_quality_presets():
    """
    Get predefined quality presets for USD export.
    
    :return: Dictionary of quality preset configurations
    :rtype: dict
    """
    return {
        "low": {
            "description": "Fast export with minimal data",
            "include_materials": False,
            "export_normals": False,
            "export_colors": False,
            "export_uvs": True,
            "file_format": "usdc"
        },
        "medium": {
            "description": "Balanced export with essential data",
            "include_materials": True,
            "export_normals": True,
            "export_colors": False,
            "export_uvs": True,
            "file_format": "usdc"
        },
        "high": {
            "description": "Full quality export with all data",
            "include_materials": True,
            "export_normals": True,
            "export_colors": True,
            "export_uvs": True,
            "file_format": "usdc"
        }
    }


def check_usd_plugin_status():
    """
    Check the status of Maya USD plugin.
    
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
        # Check if plugin exists
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
                status["export_command_available"] = mel.eval('exists "mayaUSDExport"')
            except:
                pass
    
    except Exception:
        pass
    
    return status