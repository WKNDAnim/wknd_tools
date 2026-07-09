import nuke
import os

# Get root
root = nuke.root()
# file_root = os.path.dirname(__file__)
file_root = r"Z:/05Framework/packages/resources/nuketools"

#############
# Add Paths #
#############

nuke.pluginAddPath(f"{file_root}/nodes")
nuke.pluginAddPath(f"{file_root}/NukeSurvivalToolkit")
nuke.pluginAddPath(f"{file_root}/Stamps-1.2.0")
nuke.pluginAddPath(f"{file_root}/bokehBuilderRelease")
nuke.pluginAddPath(f"{file_root}/aeTools")

##############
# COLORSPACE #
##############

root["colorManagement"].setValue("OCIO")
root["OCIO_config"].setValue("fn-nuke_cg-config-v1.0.0_aces-v1.3_ocio-v2.1")  # 'fn-nuke_cg-config-v1.0.0_aces-v1.3_ocio-v2.1'
root["workingSpaceLUT"].setValue("scene_linear")
root["monitorLut"].setValue("ACES 1.0 - SDR Video (sRGB - Display)")
root["monitorOutLUT"].setValue("ACES 1.0 - SDR Video (sRGB - Display)")

#################
# Node defaults #
#################

nuke.knobDefault("Read.colorspace", "scene_linear")
nuke.knobDefault("Read.frame_mode", "start_at")
nuke.knobDefault("Read.frame", "1001")
