import maya.cmds as mc
from functools import partial
from PySide6 import QtWidgets, QtCore
from maya.app.general.mayaMixin import MayaQWidgetBaseMixin

from .. import constants

from .. import blocks
from .. import block_manager
from . import timeline_widget

import importlib
importlib.reload(blocks)
importlib.reload(block_manager)
importlib.reload(timeline_widget)

from .timeline_widget import TimelineWidget, STATE_COLORS
from ..block_manager import BlockManager
from ..animation_layer_manager import AnimationLayerManager


class DetailUI(MayaQWidgetBaseMixin, QtWidgets.QWidget):

    agent_updated = QtCore.Signal()

    def __init__(self, agent, manager, parent=None):

        super().__init__(parent)
        self.agent = agent
        self.manager = manager
        self._active_state = "idle"

        # Creamos el BlockManager
        frame_start = int(mc.playbackOptions(q=True, min=True))
        frame_end = int(mc.playbackOptions(q=True, max=True))
        self.block_manager = BlockManager(frame_start, frame_end)

        # Cargamos bloques existentes o inicializamos
        if self.agent.blocks:
            self.block_manager.load(self.agent.blocks)
        else:
            self.block_manager.initialize(self.agent.state)

        self.setWindowTitle(f"Agent {agent.id} — {agent.locator}")
        self.setMinimumWidth(700)
        self._build_ui()

    def _build_ui(self):

        main_layout = QtWidgets.QVBoxLayout(self)

        # -- Header
        header = QtWidgets.QLabel(f"Agent #{self.agent.id}  |  {self.agent.locator}")
        header.setAlignment(QtCore.Qt.AlignCenter)
        header.setStyleSheet("background-color: #333; padding: 8px; font-weight: bold;")
        main_layout.addWidget(header)

        # -- Selector de estado
        state_group = QtWidgets.QGroupBox("State")
        state_layout = QtWidgets.QHBoxLayout(state_group)
        self.state_buttons = {}
        for state in constants.AGENT_STATES:
            btn = QtWidgets.QPushButton(state)
            btn.setCheckable(True)
            color = STATE_COLORS.get(state, "#555")
            btn.setStyleSheet(f"background-color: {color}; padding: 4px 8px;")
            btn.clicked.connect(partial(self._on_select_state, state))
            state_layout.addWidget(btn)
            self.state_buttons[state] = btn
        main_layout.addWidget(state_group)

        # -- Formulario crear/editar bloque
        self.form_stack = QtWidgets.QStackedWidget()

        # Página 0 -- StateBlock
        state_form_widget = QtWidgets.QWidget()
        state_form_layout = QtWidgets.QHBoxLayout(state_form_widget)
        state_form_layout.addWidget(QtWidgets.QLabel("Frame in:"))
        self.input_start = QtWidgets.QSpinBox()
        self.input_start.setRange(0, 99999)
        self.input_start.setValue(self.block_manager.frame_start)
        state_form_layout.addWidget(self.input_start)
        state_form_layout.addWidget(QtWidgets.QLabel("Frame out:"))
        self.input_end = QtWidgets.QSpinBox()
        self.input_end.setRange(0, 99999)
        self.input_end.setValue(self.block_manager.frame_start + 10)
        state_form_layout.addWidget(self.input_end)
        self.btn_add = QtWidgets.QPushButton("Add Block")
        self.btn_add.setStyleSheet("background-color: #2a5e2a; padding: 4px 12px;")
        self.btn_add.clicked.connect(self._on_add_block)
        state_form_layout.addWidget(self.btn_add)
        self.btn_update = QtWidgets.QPushButton("Update Block")
        self.btn_update.setStyleSheet("background-color: #5e5e2a; padding: 4px 12px;")
        self.btn_update.clicked.connect(self._on_update_block)
        self.btn_update.setEnabled(False)
        state_form_layout.addWidget(self.btn_update)

        # Página 1 -- TransitionBlock
        trans_form_widget = QtWidgets.QWidget()
        trans_form_layout = QtWidgets.QHBoxLayout(trans_form_widget)
        trans_form_layout.addWidget(QtWidgets.QLabel("Frames from:"))
        self.input_frames_from = QtWidgets.QSpinBox()
        self.input_frames_from.setRange(1, 99999)
        self.input_frames_from.setValue(5)
        trans_form_layout.addWidget(self.input_frames_from)
        trans_form_layout.addWidget(QtWidgets.QLabel("Frames to:"))
        self.input_frames_to = QtWidgets.QSpinBox()
        self.input_frames_to.setRange(1, 99999)
        self.input_frames_to.setValue(5)
        trans_form_layout.addWidget(self.input_frames_to)
        self.btn_update_transition = QtWidgets.QPushButton("Update Transition")
        self.btn_update_transition.setStyleSheet("background-color: #5e5e2a; padding: 4px 12px;")
        self.btn_update_transition.clicked.connect(self._on_update_transition)
        trans_form_layout.addWidget(self.btn_update_transition)

        self.form_stack.addWidget(state_form_widget)   # índice 0
        self.form_stack.addWidget(trans_form_widget)   # índice 1

        form_group = QtWidgets.QGroupBox("Block")
        form_group_layout = QtWidgets.QVBoxLayout(form_group)
        form_group_layout.addWidget(self.form_stack)
        main_layout.addWidget(form_group)

        # -- Timeline
        self.timeline = TimelineWidget(self.block_manager)
        self.timeline.setMinimumHeight(80)
        self.timeline.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed
        )
        self.timeline.blocks_changed.connect(self._on_blocks_changed)
        self.timeline.block_selected.connect(self._on_block_selected)
        self.timeline.block_deselected.connect(self._on_block_deselected)
        main_layout.addWidget(self.timeline)
        self.timeline.update()

        # -- Info bloques
        self.blocks_label = QtWidgets.QLabel("")
        self.blocks_label.setStyleSheet("color: #888; font-size: 10px;")
        main_layout.addWidget(self.blocks_label)
        self._refresh_blocks_label()

        # -- Seleccionamos idle por defecto
        self._on_select_state("idle")

        # -- Botón cerrar
        btn_close = QtWidgets.QPushButton("Close")
        btn_close.clicked.connect(self.close)
        main_layout.addWidget(btn_close)

    def _on_select_state(self, state):

        self._active_state = state
        for s, btn in self.state_buttons.items():
            btn.setChecked(s == state)

    def _on_add_block(self):

        self.block_manager.add_block(
            state=self._active_state,
            start=self.input_start.value(),
            end=self.input_end.value()
        )
        self.timeline.refresh()
        self._on_blocks_changed()

    def _on_update_block(self):

        if self.timeline.selected_block:
            self.block_manager.update_block(
                block=self.timeline.selected_block,
                new_start=self.input_start.value(),
                new_end=self.input_end.value(),
                new_state=self._active_state
            )
            self.timeline.selected_block = None
            self.timeline.refresh()
            self._on_blocks_changed()
            self.btn_update.setEnabled(False)
            self.btn_add.setEnabled(True)

    def _on_block_selected(self, block):

        block_type = type(block).__name__

        if block_type == "StateBlock":
            self.form_stack.setCurrentIndex(0)
            self.input_start.setValue(block.start)
            self.input_end.setValue(block.end)
            self.btn_update.setEnabled(True)
            self.btn_add.setEnabled(False)
            self._on_select_state(block.state)

        elif block_type == "TransitionBlock":
            self.form_stack.setCurrentIndex(1)
            self.input_frames_from.setValue(block.frames_from)
            self.input_frames_to.setValue(block.frames_to)

    def _on_block_deselected(self):

        self.form_stack.setCurrentIndex(0)
        self.input_start.setValue(self.block_manager.frame_start)
        self.input_end.setValue(self.block_manager.frame_start + 10)
        self.btn_update.setEnabled(False)
        self.btn_add.setEnabled(True)

    def _on_blocks_changed(self):

        self.agent.save_blocks(self.block_manager.serialize())
        self._refresh_blocks_label()
        self.agent_updated.emit()

        # Bake automático si tiene referencia cargada
        if self.agent.is_referenced():
            alm = AnimationLayerManager(self.agent)
            alm.bake()

    def _refresh_blocks_label(self):

        blocks = self.block_manager.blocks
        if blocks:
            self.blocks_label.setText("  |  ".join(str(b) for b in blocks))
        else:
            self.blocks_label.setText("No blocks.")

    def _on_update_transition(self):

        block = self.timeline.selected_block
        if block and type(block).__name__ == "TransitionBlock":
            success, error = self.block_manager.update_transition(
                block=block,
                frames_from=self.input_frames_from.value(),
                frames_to=self.input_frames_to.value()
            )
            if not success:
                QtWidgets.QMessageBox.warning(self, "Invalid transition", error)
                return

            self.timeline.selected_block = None
            self.timeline.repaint()
            self._on_blocks_changed()
            self.form_stack.setCurrentIndex(0)
            self.btn_update.setEnabled(False)
            self.btn_add.setEnabled(True)
