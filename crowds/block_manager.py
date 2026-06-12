import math

from . import constants
from .blocks import StateBlock, TransitionBlock


class BlockManager:
    """Gestiona la secuencia de bloques de un agente."""

    def __init__(self, frame_start, frame_end):
        self.frame_start = frame_start
        self.frame_end = frame_end
        self.blocks = []

    # -------------------------
    # Inicialización
    # -------------------------
    def initialize(self, default_state):
        """Crea el bloque inicial que cubre todo el rango."""
        self.blocks = [StateBlock(default_state, self.frame_start, self.frame_end)]

    def load(self, blocks_data):
        """Reconstruye la secuencia desde datos serializados."""
        self.blocks = []
        for data in blocks_data:
            if data["type"] == "state":
                self.blocks.append(StateBlock.from_dict(data))
            elif data["type"] == "transition":
                self.blocks.append(TransitionBlock.from_dict(data))

    # -------------------------
    # Crear bloque
    # -------------------------
    def add_block(self, state, start, end):
        """
        Inserta un StateBlock en el rango dado.
        - Divide bloques existentes
        - Crea transiciones automáticas si estados distintos
        - Fusiona si mismo estado
        """
        # Clamp al rango del timeline
        start = max(self.frame_start, start)
        end   = min(self.frame_end,   end)

        if start >= end:
            return

        # 1. Dividimos los bloques existentes para hacer hueco
        self._split_for_range(start, end)

        # 2. Eliminamos todo lo que quede dentro del rango
        self.blocks = [b for b in self.blocks if not self._is_inside(b, start, end)]

        # 3. Insertamos el nuevo bloque
        new_block = StateBlock(state, start, end)
        self.blocks.append(new_block)

        # 4. Ordenamos
        self._sort()

        # 5. Fusionamos bloques adyacentes del mismo estado
        self._merge_same_state()

        # 6. Recalculamos transiciones
        self._rebuild_transitions()

    # -------------------------
    # Split
    # -------------------------
    def _split_for_range(self, start, end):
        """Divide bloques que se solapen con el rango dado."""
        new_blocks = []
        for block in self.blocks:
            if isinstance(block, TransitionBlock):
                continue  # las transiciones se reconstruyen después

            if block.end <= start or block.start >= end:
                new_blocks.append(block)
                continue

            # Bloque empieza antes del rango -- conservamos la parte izquierda
            if block.start < start:
                new_blocks.append(StateBlock(block.state, block.start, start))

            # Bloque termina después del rango -- conservamos la parte derecha
            if block.end > end:
                new_blocks.append(StateBlock(block.state, end, block.end))

        self.blocks = new_blocks

    # -------------------------
    # Merge
    # -------------------------
    def _merge_same_state(self):
        """Fusiona StateBlocks adyacentes del mismo estado."""
        changed = True
        while changed:
            changed = False
            state_blocks = [b for b in self.blocks if isinstance(b, StateBlock)]
            state_blocks.sort(key=lambda b: b.start)

            for i in range(len(state_blocks) - 1):
                a = state_blocks[i]
                b = state_blocks[i + 1]
                if a.state == b.state and a.end == b.start:
                    merged = StateBlock(a.state, a.start, b.end)
                    self.blocks.remove(a)
                    self.blocks.remove(b)
                    self.blocks.append(merged)
                    changed = True
                    break

        self._sort()

    # -------------------------
    # Transiciones
    # -------------------------
    def _rebuild_transitions(self):
        """Reconstruye todas las transiciones entre StateBlocks adyacentes."""
        # Eliminamos transiciones existentes
        self.blocks = [b for b in self.blocks if isinstance(b, StateBlock)]
        self._sort()

        state_blocks = self.blocks[:]
        transitions  = []

        for i in range(len(state_blocks) - 1):
            a = state_blocks[i]
            b = state_blocks[i + 1]

            if a.state == b.state:
                continue  # mismo estado, no hay transición

            # Calculamos duración: 10% de cada bloque adyacente
            frames_from = max(1, math.floor(a.duration * constants.TRANSITION_PERCENT))
            frames_to   = max(1, math.floor(b.duration * constants.TRANSITION_PERCENT))

            t_start = a.end - frames_from
            t_end   = b.start + frames_to

            transitions.append(TransitionBlock(
                start      = t_start,
                end        = t_end,
                state_from = a.state,
                state_to   = b.state
            ))

        self.blocks.extend(transitions)
        self._sort()

    def update_transition(self, block, frames_from, frames_to):

        state_blocks = self.get_state_blocks()

        left  = next((b for b in reversed(state_blocks) if b.state == block.state_from), None)
        right = next((b for b in state_blocks if b.state == block.state_to), None)

        if not left or not right:
            return None, "No adjacent blocks found."

        # Checks
        if frames_from >= left.duration:
            return None, f"frames_from ({frames_from}) must be less than left block duration ({left.duration})"
        if frames_to >= right.duration:
            return None, f"frames_to ({frames_to}) must be less than right block duration ({right.duration})"

        # Actualizamos
        cut           = left.end
        block.frames_from = frames_from
        block.frames_to   = frames_to
        block.start       = cut - frames_from
        block.end         = cut + frames_to

        self._sort()
        return True, None

    # -------------------------
    # Editar bloque
    # -------------------------
    def update_block(self, block, new_start, new_end):
        """Actualiza el rango de un StateBlock y recalcula todo."""
        if not isinstance(block, StateBlock):
            return

        new_start = max(self.frame_start, new_start)
        new_end   = min(self.frame_end,   new_end)

        if new_start >= new_end:
            return

        state = block.state
        self.blocks.remove(block)

        # Rellenamos el hueco que deja con bloques adyacentes
        self._fill_gap(block.start, block.end, exclude=None)

        # Insertamos con la nueva posición
        self.add_block(state, new_start, new_end)

    def _fill_gap(self, start, end, exclude):
        """
        Rellena un hueco expandiendo los bloques adyacentes.
        El bloque de la izquierda se expande hacia la derecha,
        si no hay bloque a la izquierda se expande el de la derecha.
        """
        state_blocks = [b for b in self.blocks if isinstance(b, StateBlock)]
        state_blocks.sort(key=lambda b: b.start)

        # Bloque a la izquierda del hueco
        left  = next((b for b in reversed(state_blocks) if b.end <= start), None)
        # Bloque a la derecha del hueco
        right = next((b for b in state_blocks if b.start >= end), None)

        if left:
            left.end = end
        elif right:
            right.start = start

        self._rebuild_transitions()

    # -------------------------
    # Utilidades
    # -------------------------
    def _sort(self):
        self.blocks.sort(key=lambda b: b.start)

    def _is_inside(self, block, start, end):
        return block.start >= start and block.end <= end

    def get_state_blocks(self):
        return [b for b in self.blocks if isinstance(b, StateBlock)]

    def get_transition_blocks(self):
        return [b for b in self.blocks if isinstance(b, TransitionBlock)]

    def serialize(self):
        return [b.to_dict() for b in self.blocks]

    def __repr__(self):
        return "\n".join(str(b) for b in self.blocks)
