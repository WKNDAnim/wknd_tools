import maya.cmds as cmds
import maya.OpenMayaUI as omui
import os
import re

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


class UniversalPublishUI(MayaQWidgetDockableMixin, qt.QWidget):
    """
    Ventana universal de publicación.
    Se adapta automáticamente al contexto (Asset/Shot + Task).
    """

    def __init__(self, parent=mayaMainWindow()):
        super(UniversalPublishUI, self).__init__(parent)

        self.setWindowTitle("Publish")
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)

        # Variables
        self.context_info = None
        self.media_folder = None
        self.current_version = ''

        import sgtk
        self.engine = sgtk.platform.current_engine()
        self.context = self.engine.context
        self.tk = self.engine.sgtk
        self.sg = self.engine.shotgun
        self.asset_type = None
        self.context_info = {}

        # Obtener contexto
        self.getContext()
        print(f"--------------------------{self.context_info}")

        self.buildUI()

    def getContext(self):
        """Obtiene información del contexto actual de ShotGrid."""

        try:

            # import sgtk
            # engine = sgtk.platform.current_engine()
            # self.context = engine.context
            # self.tk = self.engine.sgtk
            # sg = engine.shotgun
            # self.asset_type = None
            # self.context_info = {}

            if self.context.entity and self.context.entity['type'] == 'Asset':

                # GUARRADA!! O LO PONEMOS TODO EN SELF.CONTEXT_INFO, O DEJAMOS SELF.ASSET_TYPE, PERO NO LOS DOS!!---------------------------------------------------
                asset = self.sg.find_one(
                    'Asset',
                    [['id', 'is', self.context.entity['id']]],
                    ['sg_asset_type']
                )
                if asset:
                    self.context_info |= {"asset_type": asset['sg_asset_type']}
                    self.asset_type = asset['sg_asset_type']  # TODO --> AVOID THIS!

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

        current_file = cmds.file(query=True, sceneName=True)

        # Get fields from file
        if self.context.entity['type'].lower() == "asset":
            self.scene_work_template = self.tk.templates["maya_asset_work"]
        else:
            self.scene_work_template = self.tk.templates["maya_shot_work"]

        self.scene_fields = self.scene_work_template.get_fields(current_file)
        self.current_version = int(self.scene_fields["version"])

    def buildUI(self):
        """Construye la interfaz."""
        main_layout = qt.QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # === HEADER ===
        header_label = qt.QLabel("PUBLISH")
        header_font = qtg.QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(qtc.Qt.AlignCenter)
        main_layout.addWidget(header_label)

        # === CONTEXT INFO ===
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

        # === MEDIA / THUMBNAIL ===
        media_group = qt.QGroupBox("Media for Thumbnail")
        media_layout = qt.QVBoxLayout()
        media_layout.setSpacing(10)

        # Radio buttons para tipo de media
        self.media_playblast_radio = qt.QRadioButton("Playblast (current viewport)")
        self.media_images_radio = qt.QRadioButton("Images from folder")
        self.media_playblast_radio.setChecked(True)

        media_layout.addWidget(self.media_playblast_radio)
        media_layout.addWidget(self.media_images_radio)

        # Folder selector (solo visible si se selecciona images)
        folder_layout = qt.QHBoxLayout()
        self.folder_path_label = qt.QLabel("No folder selected")
        self.folder_path_label.setStyleSheet("QLabel { color: #999; font-style: italic; }")
        self.folder_browse_btn = qt.QPushButton("Browse...")
        self.folder_browse_btn.setEnabled(False)
        self.folder_browse_btn.clicked.connect(self.browseThumbnailFolder)

        folder_layout.addWidget(self.folder_path_label, 1)
        folder_layout.addWidget(self.folder_browse_btn)
        media_layout.addLayout(folder_layout)

        # Conectar radio buttons
        self.media_playblast_radio.toggled.connect(self.onMediaTypeChanged)
        self.media_images_radio.toggled.connect(self.onMediaTypeChanged)

        media_group.setLayout(media_layout)
        main_layout.addWidget(media_group)

        # === DESCRIPTION ===
        desc_group = qt.QGroupBox("Description")
        desc_layout = qt.QVBoxLayout()

        self.description_text = qt.QTextEdit()
        self.description_text.setPlaceholderText("Describe what you've done in this version...")
        self.description_text.setMaximumHeight(100)

        desc_layout.addWidget(self.description_text)
        desc_group.setLayout(desc_layout)
        main_layout.addWidget(desc_group)

        # === LOG ===
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
        self.publish_btn = qt.QPushButton("PUBLISH")
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
        self.publish_btn.clicked.connect(self.onPublish)

        main_layout.addWidget(self.publish_btn)

    def onMediaTypeChanged(self):
        """Activa/desactiva el botón de browse según el tipo de media."""
        is_folder = self.media_images_radio.isChecked()
        self.folder_browse_btn.setEnabled(is_folder)
        
        if not is_folder:
            self.media_folder = None
            self.folder_path_label.setText("No folder selected")
            self.folder_path_label.setStyleSheet("QLabel { color: #999; font-style: italic; }")

    def browseThumbnailFolder(self):
        """Abre diálogo para seleccionar carpeta de imágenes."""
        folder = qt.QFileDialog.getExistingDirectory(
            self,
            "Select Images Folder",
            cmds.workspace(q=True, rootDirectory=True)
        )
        
        if folder:
            self.media_folder = folder
            self.folder_path_label.setText(folder)
            self.folder_path_label.setStyleSheet("QLabel { color: #4CAF50; }")
            self.log(f"📁 Folder selected: {folder}")

    def log(self, message):
        """Añade mensaje al log."""
        print(message)
        self.log_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())    
        # Force UI Update
        qt.QApplication.processEvents()

    def onPublish(self):
        """Ejecuta el publish según el contexto."""
        self.log_text.clear()
        self.log("=" * 60)
        self.log("STARTING PUBLISH")
        self.log("=" * 60)
        
        # Deshabilitar botón durante publish
        self.publish_btn.setEnabled(False)
        self.publish_btn.setText("PUBLISHING...")
        
        try:
            # Obtener datos
            description = self.description_text.toPlainText()
            use_playblast = self.media_playblast_radio.isChecked()
            
            # Log de contexto
            self.log(f"📦 Entity: {self.context_info['entity_name']}")
            self.log(f"🎯 Task: {self.context_info['step']} - {self.context_info['task_name']}")
            self.log(f"📝 Description: {description if description else '(none)'}")
            self.log("")
            
            from wknd_tools.core import publish_version
            import importlib
            importlib.reload(publish_version)

            publisher = publish_version.Publisher(self.context, self.current_version, description, self.asset_type, use_playblast, self.media_folder, self.log)
            publish_result = publisher.publish()
            
            self.log("✅ PUBLISH COMPLETE")
            
            # Mostrar resultado
            qt.QMessageBox.information(
                self,
                "Publish Complete",
                f"Successfully published {self.context_info['entity_name']}\n"
                f"Task: {self.context_info['task_name']}\n"
                f"Version: {self.version_label.text()}"
            )
        
        except Exception as e:
            self.log(f"❌ ERROR: {str(e)}")
            qt.QMessageBox.critical(self, "Publish Failed", str(e))
        
        finally:
            # Re-habilitar botón
            self.publish_btn.setEnabled(True)
            self.publish_btn.setText("PUBLISH")
            self.close()


def showUI():
    """Muestra la ventana de publish."""
    global universal_publish_ui

    try:
        universal_publish_ui.close()
        universal_publish_ui.deleteLater()
    except:
        pass

    universal_publish_ui = UniversalPublishUI()
    universal_publish_ui.show(dockable=True)
