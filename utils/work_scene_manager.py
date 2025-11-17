import maya.cmds as mc
import maya.OpenMayaUI as omui
import re
import os

# Detectar versión de Maya y usar PySide correspondiente
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
    """Obtiene la ventana principal de Maya."""
    mainWindowPointer = omui.MQtUtil.mainWindow()
    return wrapInstance(int(mainWindowPointer), qt.QWidget)


class AssetWorkSceneUI(MayaQWidgetDockableMixin, qt.QWidget):
    """
    UI para crear y abrir escenas de trabajo de assets.
    """
    
    # Asset types
    ASSET_TYPES = ['CHE', 'CHM', 'CHS', 'ELEM', 'LIB', 'PRP', 'SET']
    
    TASKS = ['MODEL', 'Surfacing', 'RIG']
    
    def __init__(self, parent=mayaMainWindow()):
        super(AssetWorkSceneUI, self).__init__(parent)
        
        self.setWindowTitle("Asset Work Scene Creator")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        
        # Guardar template y fields actuales
        self.current_template = None
        self.current_fields = None
        
        # Inicializar SG
        try:
            import sgtk
            self.engine = sgtk.platform.current_engine()
            self.sg = self.engine.shotgun
            self.tk = self.engine.sgtk
            self.context = self.engine.context
        except:
            self.engine = None
            self.sg = None
            self.tk = None
            print("⚠ ShotGrid no disponible")
        
        self.myUI()
        self.connectSignals()
        self.updateAssetList()
        self.updateExistingScenes()
    
    def myUI(self):
        """Construye la interfaz."""
        main_layout = qt.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # === TÍTULO ===
        title_label = qt.QLabel("Create/Open Asset Work Scene")
        title_font = qtg.QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(qtc.Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        main_layout.addSpacing(10)
        
        # === ASSET TYPE ===
        type_layout = qt.QHBoxLayout()
        type_label = qt.QLabel("Asset Type:")
        type_label.setFixedWidth(100)
        self.type_combo = qt.QComboBox()
        self.type_combo.addItems(self.ASSET_TYPES)
        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        main_layout.addLayout(type_layout)
        
        # === ASSET NAME ===
        asset_layout = qt.QHBoxLayout()
        asset_label = qt.QLabel("Asset:")
        asset_label.setFixedWidth(100)
        self.asset_combo = qt.QComboBox()
        asset_layout.addWidget(asset_label)
        asset_layout.addWidget(self.asset_combo)
        main_layout.addLayout(asset_layout)
        
        # === TASK ===
        task_layout = qt.QHBoxLayout()
        task_label = qt.QLabel("Task:")
        task_label.setFixedWidth(100)
        self.task_combo = qt.QComboBox()
        self.task_combo.addItems(self.TASKS)
        task_layout.addWidget(task_label)
        task_layout.addWidget(self.task_combo)
        main_layout.addLayout(task_layout)
        
        # === SCENE NAME (TEXT INPUT) ===
        name_layout = qt.QHBoxLayout()
        name_label = qt.QLabel("Scene Name:")
        name_label.setFixedWidth(100)
        self.name_input = qt.QLineEdit()
        self.name_input.setText("scene")
        self.name_input.setPlaceholderText("scene")
        
        # Validator para solo A-Z, a-z, 0-9 (compatible PySide2 y PySide6)
        try:
            # PySide6
            regex = qtc.QRegularExpression("[A-Za-z0-9]+")
            validator = qtg.QRegularExpressionValidator(regex)
        except AttributeError:
            # PySide2
            regex = qtc.QRegExp("[A-Za-z0-9]+")
            validator = qtg.QRegExpValidator(regex)
        
        self.name_input.setValidator(validator)
        
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        main_layout.addLayout(name_layout)
        
        # === SEPARATOR ===
        line = qt.QFrame()
        line.setFrameShape(qt.QFrame.HLine)
        line.setFrameShadow(qt.QFrame.Sunken)
        main_layout.addWidget(line)
        
        # === EXISTING SCENES ===
        existing_label = qt.QLabel("Existing Scenes:")
        main_layout.addWidget(existing_label)
        
        self.scenes_combo = qt.QComboBox()
        self.scenes_combo.setMinimumHeight(30)
        main_layout.addWidget(self.scenes_combo)
        
        # Botón refresh
        refresh_btn = qt.QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.updateExistingScenes)
        main_layout.addWidget(refresh_btn)
        
        # === SPACER ===
        main_layout.addStretch()
        
        # === BOTONES PRINCIPALES ===
        buttons_layout = qt.QHBoxLayout()
        
        self.create_btn = qt.QPushButton("Create New Scene")
        self.create_btn.setMinimumHeight(40)
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.open_btn = qt.QPushButton("Open Selected Scene")
        self.open_btn.setMinimumHeight(40)
        self.open_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        
        buttons_layout.addWidget(self.create_btn)
        buttons_layout.addWidget(self.open_btn)
        main_layout.addLayout(buttons_layout)
        
        # === PREVIEW DEL NOMBRE ===
        self.preview_label = qt.QLabel("")
        self.preview_label.setAlignment(qtc.Qt.AlignCenter)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                padding: 8px;
                border-radius: 3px;
                font-family: Courier;
                color: #333;
            }
        """)
        main_layout.addWidget(self.preview_label)
        
        self.updatePreview()
    
    def connectSignals(self):
        """Conecta señales de los widgets."""
        self.type_combo.currentIndexChanged.connect(self.updateAssetList)
        self.type_combo.currentIndexChanged.connect(self.updateExistingScenes)
        self.asset_combo.currentIndexChanged.connect(self.updateExistingScenes)
        self.task_combo.currentIndexChanged.connect(self.updateExistingScenes)
        self.name_input.textChanged.connect(self.updateExistingScenes)
        
        self.create_btn.clicked.connect(self.createScene)
        self.open_btn.clicked.connect(self.openScene)
    
    def updateAssetList(self):
        """Actualiza la lista de assets según el tipo seleccionado en SG."""
        asset_type = self.type_combo.currentText()
        
        self.asset_combo.clear()
        
        if not self.sg:
            print("⚠ ShotGrid no disponible")
            return
        
        try:
            # Buscar assets del tipo seleccionado
            assets_of_type = self.sg.find(
                'Asset',
                [
                    ['project', 'is', self.context.project],
                    ['sg_asset_type', 'is', asset_type]
                ],
                ['code'],
                order=[{'field_name': 'code', 'direction': 'asc'}]
            )
            
            # Extraer nombres
            asset_names = [asset['code'] for asset in assets_of_type]
            
            if asset_names:
                self.asset_combo.addItems(asset_names)
                print(f"✓ {len(asset_names)} assets de tipo {asset_type}")
            else:
                print(f"⚠ No hay assets de tipo {asset_type}")
        
        except Exception as e:
            print(f"❌ Error buscando assets: {e}")
        
        self.updatePreview()
    
    def updateExistingScenes(self):
        """Busca work scenes en el filesystem usando templates de SG."""
        import os
        import glob
        
        asset_type = self.type_combo.currentText()
        asset_name = self.asset_combo.currentText()
        task_name = self.task_combo.currentText()
        scene_name = self.name_input.text() or "scene"
        
        self.scenes_combo.clear()
        
        if not asset_name or not self.tk:
            self.open_btn.setEnabled(False)
            return
        
        try:
            # 1. Buscar el Asset en SG
            asset = self.sg.find_one(
                'Asset',
                [
                    ['project', 'is', self.context.project],
                    ['code', 'is', asset_name],
                    ['sg_asset_type', 'is', asset_type]
                ],
                ['id', 'code']
            )
            
            if not asset:
                print(f"⚠ Asset no encontrado: {asset_type}/{asset_name}")
                self.open_btn.setEnabled(False)
                return
            
            # 2. Buscar el Task del asset
            task = self.sg.find_one(
                'Task',
                [
                    ['entity', 'is', asset],
                    ['step.Step.code', 'is', task_name]
                ],
                ['id', 'content', 'Step', 'Task']
            )
            
            if not task:
                print(f"⚠ Task no encontrado: {task_name} para {asset_name}")
                self.open_btn.setEnabled(False)
                return
            
            # 3. Crear contexto del task
            context = self.tk.context_from_entity('Task', task['id'])
            
            # 4. Obtener template de work file
            # Intentar varios nombres comunes de template
            template = None
            for template_name in ['maya_asset_work', 'asset_work_area_maya', 'maya_work_file']:
                template = self.tk.templates.get(template_name)
                if template:
                    print(f"✓ Usando template: {template_name}")
                    break
            
            if not template:
                print("⚠ No se encontró template de work file")
                print("Templates disponibles:")
                for name in self.tk.templates.keys():
                    if 'maya' in name.lower() and 'work' in name.lower():
                        print(f"  - {name}")
                self.open_btn.setEnabled(False)
                return
            
            # 5. Construir fields para el template
            fields = context.as_template_fields(template)
            fields['name'] = scene_name
            # ADDING TASK NAME TO MAKE DIFFERENCE BETWEEN SURFACING STEP, SHADING TASK, AND TEXTURE TASK...MODEL WORKS, SHADING WITH THAT WORKS, LET'S SEE GROOM-----------------------------------------------------
            if task_name == 'Surfacing':
                fields['Task'] = 'Shading'
            
            # 6. Obtener el directorio de trabajo
            # Si el template tiene version, temporalmente poner v001 para construir el path
            if 'version' in template.keys:
                fields['version'] = 1
            
            work_path_example = template.apply_fields(fields)
            work_dir = os.path.dirname(work_path_example)
            
            # Guardar template y fields para usar después
            self.current_template = template
            self.current_fields = fields
            
            # 7. Buscar archivos que coincidan (wildcard en versión)
            pattern = work_path_example.replace('_v001.ma', '_v*.ma')
            
            matching_files = glob.glob(pattern)
            matching_files.sort()
            
            if matching_files:
                for file_path in matching_files:
                    file_name = os.path.basename(file_path).replace('.ma', '')
                    self.scenes_combo.addItem(file_name, file_path)
                
                # Seleccionar última versión
                self.scenes_combo.setCurrentIndex(self.scenes_combo.count() - 1)
                self.open_btn.setEnabled(True)
                print(f"✓ Encontradas {len(matching_files)} escenas en: {work_dir}")
            else:
                print(f"⚠ No se encontraron escenas en: {work_dir}")
                print(f"   Pattern buscado: {pattern}")
                self.open_btn.setEnabled(False)
            
            # Actualizar preview
            self.updatePreview()
        
        except Exception as e:
            import traceback
            print(f"❌ Error buscando escenas: {e}")
            print(traceback.format_exc())
            self.open_btn.setEnabled(False)
    
    def updatePreview(self):
        """Actualiza el preview del nombre de escena."""
        if not self.current_template or not self.current_fields:
            self.preview_label.setText("")
            return
        
        # Calcular siguiente versión
        next_version = self.getNextVersion()
        
        # Construir preview con template
        fields = self.current_fields.copy()
        fields['version'] = next_version
        
        try:
            preview_path = self.current_template.apply_fields(fields)
            preview_name = os.path.basename(preview_path)
            self.preview_label.setText(f"New scene: {preview_name}")
        except Exception as e:
            self.preview_label.setText(f"Preview error: {e}")
    
    def createScene(self):
        """Crea una nueva escena de trabajo."""
        import os
        
        if not self.current_template or not self.current_fields:
            qt.QMessageBox.warning(self, "Warning", "Please select asset and task first")
            return
        
        # Obtener siguiente versión
        next_version = self.getNextVersion()
        
        # Actualizar fields con la versión correcta
        fields = self.current_fields.copy()
        fields['version'] = next_version
        
        # Construir path completo con el template
        full_path = self.current_template.apply_fields(fields)
        
        # Verificar que el directorio existe
        work_dir = os.path.dirname(full_path)
        if not os.path.exists(work_dir):
            os.makedirs(work_dir)
            print(f"✓ Directorio creado: {work_dir}")
        
        # Crear escena nueva
        mc.file(new=True, force=True)
        mc.file(rename=full_path)
        mc.file(save=True, type='mayaAscii')
        
        print(f"✓ Escena creada: {full_path}")
        
        # Actualizar lista
        self.updateExistingScenes()
        
        file_name = os.path.basename(full_path)
        qt.QMessageBox.information(self, "Success", f"Scene created:\n{file_name}")
    
    def getNextVersion(self):
        """Obtiene el siguiente número de versión."""
        import re
        
        if self.scenes_combo.count() > 0:
            # Obtener última escena
            last_scene = self.scenes_combo.itemText(self.scenes_combo.count() - 1)
            
            # Extraer versión (ej: "chm_dog_model_scene_v003" → 3)
            match = re.search(r'_v(\d+)', last_scene)
            if match:
                return int(match.group(1)) + 1
        
        return 1
    
    def openScene(self):
        """Abre la escena seleccionada."""
        selected_scene = self.scenes_combo.currentText()
        
        if not selected_scene:
            qt.QMessageBox.warning(self, "Warning", "No scene selected")
            return
        
        # Obtener el path completo desde userData
        scene_path = self.scenes_combo.currentData()
        
        if not scene_path or not os.path.exists(scene_path):
            qt.QMessageBox.critical(self, "Error", f"Scene file not found:\n{scene_path}")
            return
        
        # Verificar si hay cambios sin guardar
        if mc.file(q=True, modified=True):
            reply = qt.QMessageBox.question(
                self,
                "Unsaved Changes",
                "Current scene has unsaved changes. Continue?",
                qt.QMessageBox.Yes | qt.QMessageBox.No
            )
            
            if reply == qt.QMessageBox.No:
                return
        
        # Abrir escena
        try:
            mc.file(scene_path, open=True, force=True)
            print(f"✓ Escena abierta: {scene_path}")
        except Exception as e:
            qt.QMessageBox.critical(self, "Error", f"Could not open scene:\n{str(e)}")


def showUI():
    """Muestra la UI dockable."""
    global asset_work_ui
    
    try:
        asset_work_ui.close()
        asset_work_ui.deleteLater()
    except:
        pass
    
    asset_work_ui = AssetWorkSceneUI()
    asset_work_ui.show(dockable=True)

"""
# Para ejecutar
if __name__ == "__main__":
    showUI()
"""