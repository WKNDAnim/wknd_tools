import maya.cmds as mc
from . import constants
from .block_manager import BlockManager


class AnimationLayerManager:
    """Gestiona las animation layers y los clips de animación de un agente."""

    def __init__(self, agent):
        self.agent = agent

    # -------------------------
    # API pública
    # -------------------------
    def bake(self):
        """
        Genera todas las animation layers y keyframes de weights
        basándose en los bloques del agente.
        """
        if not self.agent.blocks:
            print(f"Agent {self.agent.id} no tiene bloques definidos.")
            return

        if not self.agent.is_referenced():
            print(f"Agent {self.agent.id} no tiene referencia cargada.")
            return

        # Reconstruimos el BlockManager
        frame_start = int(mc.playbackOptions(q=True, min=True))
        frame_end   = int(mc.playbackOptions(q=True, max=True))
        bm = BlockManager(frame_start, frame_end)
        bm.load(self.agent.blocks)

        # Limpiamos layers existentes del agente
        self._clear_layers()

        # Creamos una layer por estado único en los bloques
        states = list({b.state for b in bm.get_state_blocks()})
        for state in states:
            self._create_layer(state)

        # Inicializamos todos los weights a 0
        self._zero_all_weights(frame_start, frame_end, states)

        # Aplicamos weights por bloque
        for block in bm.get_state_blocks():
            self._apply_state_block(block)

        for block in bm.get_transition_blocks():
            self._apply_transition_block(block)

        print(f"Agent {self.agent.id} animation layers baked.")

    # -------------------------
    # Layers
    # -------------------------
    def _layer_name(self, state):
        return f"{self.agent.locator}_{state}_layer"

    def _create_layer(self, state):

        layer_name = self._layer_name(state)
        if mc.objExists(layer_name):
            return layer_name

        # Seleccionamos los controles del rig
        rig_controls = mc.ls(f"{self.agent.namespace}:*_CTL", type="transform")
        if rig_controls:
            mc.select(rig_controls)

        # Creamos la layer con los controles seleccionados
        mc.animLayer(layer_name, override=True)

        if rig_controls:
            mc.animLayer(layer_name, edit=True, addSelectedObjects=True)
            mc.select(clear=True)

        # Importamos el clip
        self._import_clip(state, layer_name)

        return layer_name

    def _clear_layers(self):
        """Elimina todas las animation layers del agente."""
        for state in constants.AGENT_STATES:
            layer_name = self._layer_name(state)
            if mc.objExists(layer_name):
                mc.delete(layer_name)

    # -------------------------
    # Clips
    # -------------------------
    def _import_clip(self, state, layer_name):
        """Importa el clip de animación del estado en la layer."""
        clip_path = constants.ANIMATION_CLIPS.get(state)
        if not clip_path:
            print(f"Warning: no hay clip definido para el estado '{state}'")
            return

        # Activamos la layer antes de importar
        mc.animLayer(layer_name, edit=True, selected=True)
        mc.animLayer(layer_name, edit=True, preferred=True)

        mc.file(
            clip_path,
            i            = True,       # import
            type         = "mayaAscii",
            namespace    = self.agent.namespace,
            mergeNamespacesOnClash = True
        )

        print(f"Clip '{state}' importado en layer '{layer_name}'")

    def _tile_clip(self, state, layer_name, start, end):
        """Repite el clip de animación para cubrir el rango del bloque."""
        clip_path = constants.ANIMATION_CLIPS.get(state)
        if not clip_path:
            return

        # Obtenemos la duración del clip
        clip_duration = self._get_clip_duration(clip_path)
        if not clip_duration:
            return

        # Calculamos cuántas repeticiones necesitamos
        block_duration = end - start
        repetitions    = int(block_duration / clip_duration) + 1

        # Keyframeamos el clip repetido
        for i in range(repetitions):
            clip_start = start + i * clip_duration
            if clip_start >= end:
                break
            # Offset de tiempo para cada repetición
            mc.keyframe(
                f"{self.agent.namespace}:*_CTL",
                edit        = True,
                relative    = True,
                timeChange  = clip_start,
                time        = (0, clip_duration)
            )

    def _get_clip_duration(self, clip_path):
        """Lee la duración del clip desde el archivo .ma."""
        try:
            with open(clip_path, "r") as f:
                for line in f:
                    if "playbackOptions" in line and "-max" in line:
                        parts = line.split("-max")
                        if len(parts) > 1:
                            return int(float(parts[1].strip().split()[0]))
        except:
            pass
        return None

    # -------------------------
    # Weights
    # -------------------------
    def _zero_all_weights(self, frame_start, frame_end, states):
        """Pone todos los weights a 0 en el rango completo."""
        for state in states:
            layer_name = self._layer_name(state)
            if mc.objExists(layer_name):
                mc.setKeyframe(layer_name + ".weight", time=frame_start, value=0)
                mc.setKeyframe(layer_name + ".weight", time=frame_end,   value=0)

    def _apply_state_block(self, block):
        """Pone el weight de la layer a 1 durante el bloque."""
        layer_name = self._layer_name(block.state)
        if not mc.objExists(layer_name):
            return

        mc.setKeyframe(layer_name + ".weight", time=block.start, value=1)
        mc.setKeyframe(layer_name + ".weight", time=block.end,   value=1)

    def _apply_transition_block(self, block):
        """Anima los weights de las dos layers durante la transición."""
        layer_from = self._layer_name(block.state_from)
        layer_to   = self._layer_name(block.state_to)

        # Calculamos los frames exactos de la transición
        t_start = block.start   # donde empieza a bajar layer_from
        t_end   = block.end     # donde termina de subir layer_to
        t_mid   = block.start + block.frames_from  # punto de cruce

        if mc.objExists(layer_from):
            mc.setKeyframe(layer_from + ".weight", time=t_start, value=1)
            mc.setKeyframe(layer_from + ".weight", time=t_mid,   value=0)

        if mc.objExists(layer_to):
            mc.setKeyframe(layer_to + ".weight", time=t_mid, value=0)
            mc.setKeyframe(layer_to + ".weight", time=t_end, value=1)