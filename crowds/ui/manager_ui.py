import maya.cmds as mc
from PySide6 import QtWidgets, QtCore
from maya.app.general.mayaMixin import MayaQWidgetBaseMixin

from .. import constants
from . import detail_ui

import importlib
importlib.reload(detail_ui)

from .detail_ui import DetailUI

from wknd_tools.crowds.ui.timeline_widget import STATE_COLORS


class ManagerUI(MayaQWidgetBaseMixin, QtWidgets.QWidget):

    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.setWindowTitle("Agent Manager")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(600)
        self._build_ui()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # -- Header
        header = QtWidgets.QLabel("AGENT MANAGER")
        header.setAlignment(QtCore.Qt.AlignCenter)
        header.setStyleSheet("background-color: #333; padding: 8px; font-weight: bold;")
        main_layout.addWidget(header)

        # -- Formulario nuevo agente
        form_group = QtWidgets.QGroupBox("New Agent")
        form_layout = QtWidgets.QGridLayout(form_group)
        form_layout.setColumnStretch(0, 0)  # labels -- ancho fijo
        form_layout.setColumnStretch(1, 3)  # scene combo -- más ancho
        form_layout.setColumnStretch(2, 0)  # label default state -- ancho fijo
        form_layout.setColumnStretch(3, 1)  # default state combo -- más estrecho

        form_layout.addWidget(QtWidgets.QLabel("Locator name:"), 0, 0)
        self.field_locator = QtWidgets.QLineEdit()
        self.field_locator.setPlaceholderText("Ej: Manolo")
        form_layout.addWidget(self.field_locator, 0, 1, 1, 3)

        form_layout.addWidget(QtWidgets.QLabel("Scene:"), 1, 0)
        self.field_scene = QtWidgets.QComboBox()
        for name in constants.AGENT_SCENES.keys():
            self.field_scene.addItem(name)
        form_layout.addWidget(self.field_scene, 1, 1)

        form_layout.addWidget(QtWidgets.QLabel("Default state:"), 1, 2, 
                            alignment=QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.field_default_state = QtWidgets.QComboBox()
        for state in constants.AGENT_STATES:
            self.field_default_state.addItem(state)
        form_layout.addWidget(self.field_default_state, 1, 3)

        btn_add = QtWidgets.QPushButton("Add Agent")
        btn_add.setStyleSheet("background-color: #2a5e2a; padding: 6px;")
        btn_add.clicked.connect(self._on_add_agent)
        form_layout.addWidget(btn_add, 2, 0, 1, 4)

        main_layout.addWidget(form_group)

        # -- Lista de agentes
        agents_group = QtWidgets.QGroupBox("Agents")
        agents_group_layout = QtWidgets.QVBoxLayout(agents_group)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)

        scroll_widget = QtWidgets.QWidget()
        self.agents_layout = QtWidgets.QVBoxLayout(scroll_widget)
        self.agents_layout.setAlignment(QtCore.Qt.AlignTop)
        scroll.setWidget(scroll_widget)

        agents_group_layout.addWidget(scroll)
        main_layout.addWidget(agents_group)

        # -- Botón limpiar
        btn_clear = QtWidgets.QPushButton("Clear All Agents")
        btn_clear.setStyleSheet("background-color: #5e2a2a; padding: 6px;")
        btn_clear.clicked.connect(self._on_clear_agents)
        main_layout.addWidget(btn_clear)

    def _refresh_agent_list(self):

        while self.agents_layout.count():
            item = self.agents_layout.takeAt(0)
            if item.widget():
                # Matamos el callback antes de destruir el widget
                if hasattr(item.widget(), '_kill_callback'):
                    item.widget()._kill_callback()
                item.widget().deleteLater()

        if not self.manager.agents:
            self.agents_layout.addWidget(QtWidgets.QLabel("No agents yet."))
            return

        for agent in self.manager.agents:
            row = AgentRowWidget(agent, self.manager, parent_ui=self)
            self.agents_layout.addWidget(row)

    def _open_detail(self, agent):

        self.detail_win = DetailUI(agent, self.manager, self)
        self.detail_win.agent_updated.connect(self._refresh_agent_list)
        self.detail_win.show()

    # -- Callbacks
    def _on_add_agent(self):

        locator_name = self.field_locator.text().strip()
        scene_name = self.field_scene.currentText()
        scene = constants.AGENT_SCENES[scene_name]
        state = self.field_default_state.currentText()
        try:
            self.manager.add_agent(locator_name, scene, state)
            self.field_locator.clear()
            self._refresh_agent_list()
        except ValueError as e:
            QtWidgets.QMessageBox.warning(self, "Error", str(e))

    def _on_remove_agent(self, agent_id):

        self.manager.remove_agent(agent_id)
        self._refresh_agent_list()

    def _on_clear_agents(self):

        self.manager.clear_agents()
        self._refresh_agent_list()

    def show(self):

        print(f"Agents in manager: {self.manager.agents}")
        self._refresh_agent_list()
        super().show()



class AgentRowWidget(QtWidgets.QWidget):

    def __init__(self, agent, manager, parent_ui, parent=None):

        super().__init__(parent)
        self.agent     = agent
        self.manager   = manager
        self.parent_ui = parent_ui
        self._job_id   = None
        self._build()
        self._register_time_callback()

    def _build(self):

        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QtWidgets.QLabel(f"#{self.agent.id}"))
        row.addWidget(QtWidgets.QLabel(self.agent.locator))

        # Dropdown scene
        scene_combo = QtWidgets.QComboBox()
        for name in constants.AGENT_SCENES.keys():
            scene_combo.addItem(name)
        current_name = next(k for k, v in constants.AGENT_SCENES.items() if v == self.agent.scene)
        scene_combo.setCurrentText(current_name)
        scene_combo.currentTextChanged.connect(self._on_change_scene)
        row.addWidget(scene_combo)

        # Estado
        self.state_label = QtWidgets.QLabel(self.agent.state)
        color = STATE_COLORS.get(self.agent.state, "#555")
        self.state_label.setStyleSheet(f"background-color: {color}; padding: 4px; color: #fff;")
        row.addWidget(self.state_label)

        # Botón Edit
        btn_edit = QtWidgets.QPushButton("Edit")
        btn_edit.setStyleSheet("background-color: #2a3a5e;")
        btn_edit.clicked.connect(self._on_edit)
        row.addWidget(btn_edit)

        # Botón X
        btn_remove = QtWidgets.QPushButton("X")
        btn_remove.setStyleSheet("background-color: #5e2a2a;")
        btn_remove.clicked.connect(self._on_remove)
        row.addWidget(btn_remove)

    def _on_change_scene(self, name):
        self.manager.change_scene(self.agent, constants.AGENT_SCENES[name])

    def _on_edit(self):
        self.detail_win = DetailUI(self.agent, self.manager)
        self.detail_win.agent_updated.connect(self._on_agent_updated)
        self.detail_win.show()

    def _on_remove(self):
        self.manager.remove_agent(self.agent.id)
        self.parent_ui._refresh_agent_list()

    def _on_agent_updated(self):
        self.state_label.setText(self.agent.state)

    def _register_time_callback(self):
        """Registra un scriptJob que actualiza el estado al cambiar el frame."""
        self._job_id = mc.scriptJob(
            event=["timeChanged", self._on_time_changed],
            protected=False
        )

    def _on_time_changed(self):
        current_frame = int(mc.currentTime(q=True))
        state = self._get_state_at_frame(current_frame)
        if state:
            color = STATE_COLORS.get(state, "#555")
            self.state_label.setText(state)
            self.state_label.setStyleSheet(f"background-color: {color}; padding: 4px; color: #fff;")

    def _get_state_at_frame(self, frame):
        """Devuelve el estado activo en un frame dado según los bloques del agente."""
        import json
        from wknd_tools.crowds.blocks import StateBlock
        from wknd_tools.crowds.block_manager import BlockManager

        if not self.agent.blocks:
            return self.agent.state

        bm = BlockManager(0, 99999)
        bm.load(self.agent.blocks)

        for block in bm.get_state_blocks():
            if block.start <= frame <= block.end:
                return block.state
        return None

    def closeEvent(self, event):
        self._kill_callback()
        super().closeEvent(event)

    def _kill_callback(self):
        if self._job_id and mc.scriptJob(exists=self._job_id):
            mc.scriptJob(kill=self._job_id, force=True)
        self._job_id = None
