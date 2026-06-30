AGENT_SCENES = {
    "Hombre01": r"Z:\02Proyectos\Gus\assets\CHS\marty\RIG\RigAnimation\work\maya\marty_crowd_RigAnimation_v004.ma",
    "Mujer02":  r"Z:\02Proyectos\Gus\assets\CHE\mujer02\RIG\RigAnimation\publish\maya\mujer02_scene_RigAnimation_v005.ma",
}
# AGENT_SCENES = {
#     "Hombre01": r"Z:\02Proyectos\Gus\assets\CHE\hombre01\RIG\RigAnimation\publish\maya\hombre01_scene_RigAnimation_v006.ma",
#     "Mujer01":  r"Z:\02Proyectos\Gus\assets\CHE\mujer01\RIG\RigAnimation\publish\maya\mujer01_scene_RigAnimation_v003.ma",
#     "Mujer02":  r"Z:\02Proyectos\Gus\assets\CHE\mujer02\RIG\RigAnimation\publish\maya\mujer02_scene_RigAnimation_v005.ma",
# }

ANIMATION_CLIPS = {
    "idle":    r"Z:\05Framework\vendors\studio_library\ANIM\WIP\CYCLES\IdleSeatedSpeaking_Mujer02.anim\animation.ma",
    # "walking": r"Z:\ruta\a\walking\animation.ma",
    # "sitting": r"Z:\ruta\a\sitting\animation.ma",
    "cheering":  r"Z:\05Framework\vendors\studio_library\ANIM\WIP\CYCLES\CheeringAction_Mujer02.anim\animation.ma",
    "cheering_standing":  r"Z:\05Framework\vendors\studio_library\ANIM\WIP\CYCLES\CheeringActionStanding_Mujer02.anim\animation.ma",
}
AGENT_STATES = ANIMATION_CLIPS.keys()

TRANSITION_PERCENT = 0.1

MASTER_CTRL = "C_master_CTL"
CROWDS_GROUP = "CROWDS"
CROWDS_RIGS_GROUP = "CROWDS_RIGS"
