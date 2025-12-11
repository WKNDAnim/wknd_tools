import maya.cmds as mc
import maya.OpenMayaUI as omui
import os
import re
import tempfile
import shutil

try:
    from PySide6 import QtWidgets as qt
    from PySide6 import QtCore as qtc
    from PySide6 import QtGui as qtg
    from shiboken6 import wrapInstance
    from maya.app.general.mayaMixin import MayaQWidgetDockableMixin
except ImportError:
    from PySide2 import QtWidgets as qt
    from PySide2 import QtCore as qtc
    from PySide2 import QtGui as qtg
    from shiboken2 import wrapInstance
    from maya.app.general.mayaMixin import MayaQWidgetDockableMixin


def mayaMainWindow():
    mainWindowPointer = omui.MQtUtil.mainWindow()
    return wrapInstance(int(mainWindowPointer), qt.QWidget)


class SplitterUI(MayaQWidgetDockableMixin, qt.QWidget):
    """
    Ventana universal de publicación.
    Se adapta automáticamente al contexto (Asset/Shot + Task).
    """

    def __init__(self, parent=mayaMainWindow()):
        super(SplitterUI, self).__init__(parent)

        self.setWindowTitle("Splitter")
        self.setMinimumWidth(300)
        self.setMinimumHeight(500)

        # Variables
        self.context_info = None
        self.current_version = ''

        import sgtk
        self.engine = sgtk.platform.current_engine()
        self.context = self.engine.context
        self.tk = self.engine.sgtk
        self.sg = self.engine.shotgun
        self.asset_type = None
        self.context_info = {}

        self.shots = self.get_shots_from_sequencer()

        # Obtener contexto
        self.getContext()

        self.buildUI()

    def getContext(self):
        """Obtiene información del contexto actual de ShotGrid."""

        try:

            if self.context.entity:

                master_shot = self.sg.find_one(
                    'Shot',
                    [['id', 'is', self.context.entity['id']]],
                    ['code', 'sg_sequence', 'sg_sequence.Sequence.shots', 'shots']
                )
                if master_shot:
                    self.shots_in_sg_seq = [s["name"] for s in master_shot['sg_sequence.Sequence.shots'] if 'master' not in s["name"]]
                    self.shots_in_mastershot = [s["name"] for s in master_shot['shots'] if 'master' not in s["name"]]

            self.context_info |= {
                'entity_type': self.context.entity['type'] if self.context.entity else 'Unknown',
                'entity_name': self.context.entity['name'] if self.context.entity else 'Unknown',
                'task_name': self.context.task['name'] if self.context.task else 'Unknown',
                'step': self.context.step['name'] if self.context.step else 'Unknown',
                'project': self.context.project['name'] if self.context.project else 'Unknown'
            }

        except:

            self.context_info = {
                'entity_type': 'Unknown',
                'entity_name': 'Unknown',
                'task_name': 'Unknown',
                'step': 'Unknown',
                'project': 'Unknown'
            }

        self.current_file = mc.file(query=True, sceneName=True)

        # Get fields from file
        if self.context.entity['type'].lower() == "asset":
            self.scene_work_template = self.tk.templates["maya_asset_work"]
        else:
            self.scene_work_template = self.tk.templates["maya_shot_work"]

        self.scene_fields = self.scene_work_template.get_fields(self.current_file)
        self.current_version = int(self.scene_fields["version"])

    def buildUI(self):
        """Construye la interfaz."""
        main_layout = qt.QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        ##########
        # HEADER #
        ##########

        header_label = qt.QLabel("SPLITTER")
        header_font = qtg.QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(qtc.Qt.AlignCenter)
        main_layout.addWidget(header_label)

        ################
        # CONTEXT INFO #
        ################

        context_group = qt.QGroupBox("Context")
        context_layout = qt.QFormLayout()
        context_layout.setSpacing(8)

        self.project_label = qt.QLabel(self.context_info['project'])
        self.entity_label = qt.QLabel(f"{self.context_info['entity_type']}: {self.context_info['entity_name']}")
        self.task_label = qt.QLabel(f"{self.context_info['step']} - {self.context_info['task_name']}")
        self.version_label = qt.QLabel(str(self.current_version))

        # Estilo para labels de info
        info_style = "QLabel { color: #2196F3; font-weight: bold; }"
        self.project_label.setStyleSheet(info_style)
        self.entity_label.setStyleSheet(info_style)
        self.task_label.setStyleSheet(info_style)
        self.version_label.setStyleSheet(info_style)

        context_layout.addRow("Project:", self.project_label)
        context_layout.addRow("Entity:", self.entity_label)
        context_layout.addRow("Task:", self.task_label)
        context_layout.addRow("Version:", self.version_label)

        context_group.setLayout(context_layout)
        main_layout.addWidget(context_group)

        #########
        # SHOTS #
        #########

        media_group = qt.QGroupBox("Shots to split...")
        # Configuración de la cuadrícula
        media_layout = qt.QGridLayout()
        media_layout.setSpacing(5)
        max_rows = 4
        max_cols = 3

        self.checkboxes = {}

        # Create checkboxes
        for idx, shot in enumerate(self.shots_in_mastershot):

            checkbox = qt.QCheckBox(shot)
            checkbox.setChecked(True)
            if shot not in self.shots:
                checkbox.setStyleSheet("color: red;")
                checkbox.setChecked(False)
            
                
            # checkbox.stateChanged.connect(lambda state, texto=shot: self.on_checkbox_changed(state, texto))

            # Calcular posición en la cuadrícula
            row = idx // max_cols  # Primero horizontal
            col = idx % max_cols   # Luego baja de fila
            media_layout.addWidget(checkbox, row, col)

            self.checkboxes[shot] = checkbox

        media_group.setLayout(media_layout)
        main_layout.addWidget(media_group)

        #######
        # LOG #
        #######

        log_group = qt.QGroupBox("Publish Log")
        log_layout = qt.QVBoxLayout()

        self.log_text = qt.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: Consolas, Monaco, monospace;
                font-size: 9pt;
            }
        """)

        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        main_layout.addWidget(log_group)

        # === SPACER ===
        main_layout.addStretch()

        # === PUBLISH BUTTON ===
        self.publish_btn = qt.QPushButton("SPLIT!")
        self.publish_btn.setMinimumHeight(50)
        self.publish_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14pt;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.publish_btn.clicked.connect(self.onSplit)

        main_layout.addWidget(self.publish_btn)

    def on_checkbox_changed(self, state, texto):
        """Callback cuando un checkbox cambia de estado"""
        if state == 2:  # 2 = Checked
            print(f"Marcado: {texto}")
        else:  # 0 = Unchecked
            print(f"Desmarcado: {texto}")

    def obtener_seleccionados(self):
        """Obtiene todos los checkboxes seleccionados"""
        seleccionados = []
        for nombre, checkbox in self.checkboxes.items():
            if checkbox.isChecked():
                seleccionados.append(nombre)

        self.log(f"Shots seleccionados: {seleccionados}")
        return seleccionados

    def log(self, message):
        """Añade mensaje al log."""
        print(message)
        self.log_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())    
        # Force UI Update
        qt.QApplication.processEvents()

    def onSplit(self):
        """Ejecuta el publish según el contexto."""

        self.log_text.clear()
        self.log("=" * 60)
        self.log("STARTING SPLIT")
        self.log("=" * 60)

        # Deshabilitar botón durante publish
        self.publish_btn.setEnabled(False)
        self.publish_btn.setText("PUBLISHING...")

        scene_path = mc.file(q=True, sn=True)

        # Store a backup of the main file
        backup_file_path = _backup_current_scene_temp(scene_path)

        self.log(f"MASTER SCENE backupped to: {backup_file_path}")

        try:

            # Log de contexto
            self.log(f"📦 Entity: {self.context_info['entity_name']}")
            self.log(f"🎯 Task: {self.context_info['step']} - {self.context_info['task_name']}")
            self.log("")

            from wknd_tools.splitter import split_scene
            import importlib
            importlib.reload(split_scene)

            splitter = split_scene.split_scene_per_shot(self.context, self.engine, self.log, self.obtener_seleccionados())

            if not splitter:

                self.log("❌❌❌ SPLIT ERROR!")
                # Reopen original scene
                shutil.copy2(backup_file_path, scene_path)
                mc.file(scene_path, open=True, force=True)

            self.log("✅✅✅ SPLIT COMPLETE")

            # Mostrar resultado
            qt.QMessageBox.information(
                self,
                "Split Complete",
                f"Successfully splitted {self.context_info['entity_name']}\n"
            )

        except Exception as e:
            self.log(f"❌ ERROR: {str(e)}")
            qt.QMessageBox.critical(self, "Publish Failed", str(e))
            # Reopen original scene
            shutil.copy2(backup_file_path, scene_path)
            mc.file(scene_path, open=True, force=True)

        finally:
            # Re-habilitar botón
            self.publish_btn.setEnabled(True)
            self.publish_btn.setText("PUBLISH")
            self.close()

    def get_shots_from_sequencer(self):

        # get shots from sequencer
        seq_manager = mc.sequenceManager(q=True, node=True)
        sequencer = mc.listConnections(seq_manager, type='sequencer')[0]
        shots = mc.listConnections(sequencer, type="shot") or []  # Get a list of all shots from the sequencer.
        shotNames = []
        for shot in shots:
            shotName = mc.getAttr(f"{shot}.shotName")
            if shotName:
                shotNames.append(shotName)

        return shotNames


def showUI():
    """Muestra la ventana de publish."""
    global universal_publish_ui

    try:
        universal_publish_ui.close()
        universal_publish_ui.deleteLater()
    except:
        pass

    universal_publish_ui = SplitterUI()
    universal_publish_ui.show(dockable=True)


def _backup_current_scene_temp(scene_path):
    # Ruta actual de la escena en Maya

    if not scene_path:
        mc.error("La escena debe estar guardada antes de hacer el backup temporal.")

    # Carpeta temporal del sistema
    temp_dir = tempfile.gettempdir()

    # Nombre del archivo temporal basado en el nombre real
    base = os.path.basename(scene_path)
    temp_path = os.path.join(temp_dir, f"TMP_BACKUP_{base}")

    # Copia fiel del archivo (.ma o .mb)
    shutil.copy2(scene_path, temp_path)

    print("Backup temporal creado en:", temp_path)
    return temp_path
