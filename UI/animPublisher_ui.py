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

ALLOW_SELECTED = ["cpuigdollers", "aferraz", "jmartinez", "rmadrid", "gbartlett", "ebatchelli"]
USER = os.getlogin()


def mayaMainWindow():
    mainWindowPointer = omui.MQtUtil.mainWindow()
    return wrapInstance(int(mainWindowPointer), qt.QWidget)


class AnimPubUI(MayaQWidgetDockableMixin, qt.QWidget):
    """
    Ventana universal de publicación.
    Se adapta automáticamente al contexto (Asset/Shot + Task).
    """

    def __init__(self, parent=mayaMainWindow()):
        super(AnimPubUI, self).__init__(parent)

        self.setWindowTitle("Animation Publisher")
        self.setMinimumWidth(300)
        self.setMinimumHeight(500)

        # Variables
        self.context_info = None
        self.current_version = ''
        self.scene_path = mc.file(q=True, sn=True)

        # Datos
        self.assets_data = get_characters_and_props()
        self.checkboxes = []

        import sgtk
        self.engine = sgtk.platform.current_engine()
        self.context = self.engine.context
        self.tk = self.engine.sgtk
        self.sg = self.engine.shotgun
        self.asset_type = None
        self.context_info = {}

        # self.shots = self.get_shots_from_sequencer()

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

        # Crear UI
        self.create_widgets()
        self.create_layout()
        self.create_connections()

        # Filtramos por user para poder publicar los assets seleccionados
        if not USER in ALLOW_SELECTED:
            self.disable_checkboxes()

    def create_widgets(self):
        """Crea todos los widgets de la UI."""

        # Título
        self.title_label = qt.QLabel("Selecciona los assets a publicar:")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 5px;")

        # Scroll area para los checkboxes
        self.scroll_area = qt.QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        # Widget contenedor para los checkboxes
        self.checkbox_widget = qt.QWidget()
        self.checkbox_layout = qt.QVBoxLayout(self.checkbox_widget)

        # Añadir checkboxes para characters
        if self.assets_data['characters']:
            char_label = qt.QLabel("CHARACTERS:")
            char_label.setStyleSheet("font-weight: bold; color: #4A90E2; margin-top: 10px;")
            self.checkbox_layout.addWidget(char_label)

            for char in self.assets_data['characters']:
                display_name = f"{char['name']}"
                if char['namespace']:
                    display_name += f" [{char['namespace']}]"

                cb = qt.QCheckBox(display_name)
                cb.setChecked(True)  # Por defecto clicado
                cb.asset_data = char  # Guardamos la data del asset
                self.checkboxes.append(cb)
                self.checkbox_layout.addWidget(cb)

        # Añadir checkboxes para props
        if self.assets_data['props']:
            props_label = qt.QLabel("PROPS:")
            props_label.setStyleSheet("font-weight: bold; color: #E2904A; margin-top: 10px;")
            self.checkbox_layout.addWidget(props_label)

            for prop in self.assets_data['props']:
                display_name = f"{prop['name']}"
                if prop['namespace']:
                    display_name += f" [{prop['namespace']}]"

                cb = qt.QCheckBox(display_name)
                cb.setChecked(True)  # Por defecto clicado
                cb.asset_data = prop  # Guardamos la data del asset
                self.checkboxes.append(cb)
                self.checkbox_layout.addWidget(cb)

        # Añadir stretch al final para que se alinee arriba
        self.checkbox_layout.addStretch()

        # Asignar el widget al scroll area
        self.scroll_area.setWidget(self.checkbox_widget)

        # Botones de selección
        self.select_all_btn = qt.QPushButton("Seleccionar Todo")
        self.deselect_all_btn = qt.QPushButton("Deseleccionar Todo")

        # Botón de publish
        self.publish_btn = qt.QPushButton("PUBLISH")
        self.publish_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 11pt;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

        # Logging label
        self.status_lbl = qt.QLabel("")
        self.status_lbl.setWordWrap(True)
        msg = f"Publishing {len(self.assets_data['characters'])} CHARACTERS and {len(self.assets_data['props'])} PROPS"
        self.status_lbl.setText(msg)

    def create_layout(self):
        """Organiza los widgets en el layout."""

        main_layout = qt.QVBoxLayout(self)

        # Título
        main_layout.addWidget(self.title_label)

        # Scroll area con checkboxes
        main_layout.addWidget(self.scroll_area)

        # Filtramos por user para poder publicar los assets seleccionados
        if USER in ALLOW_SELECTED:
            # Botones de selección
            button_layout = qt.QHBoxLayout()
            button_layout.addWidget(self.select_all_btn)
            button_layout.addWidget(self.deselect_all_btn)
            main_layout.addLayout(button_layout)

        # Estado / feedback
        main_layout.addWidget(self.status_lbl)

        # Botón de publish
        main_layout.addWidget(self.publish_btn)

    def create_connections(self):
        """Conecta las señales de los botones."""

        self.select_all_btn.clicked.connect(self.select_all)
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        self.publish_btn.clicked.connect(self.publish)

    def log(self, message):
        """Añade mensaje al log."""

        print(message)
        self._set_status(True, message)
        qt.QApplication.processEvents()

    def publish(self):
        """Ejecuta el publish según el contexto."""

        from wknd_tools.animPub import animation_publisher
        import importlib
        importlib.reload(animation_publisher)

        # Deshabilitar botón durante publish
        self.publish_btn.setEnabled(False)
        self.publish_btn.setText("Starting publish...")
        self.log("PUBLISHING...")
        # self._set_status(True, "PUBLISHING...")
        # qt.QApplication.processEvents()

        # First, check if last versions of CHAR Rigs are being used
        self.publish_btn.setText("Checking Rig version...")
        warnings = self._check_rigs()
        if warnings:
            warn = "You are using old versions of some Rigs, please update it:\n"
            for w in warnings:
                warn = warn + f"\t- {w}.\n"

            mc.confirmDialog(title='WARNING!', message=warn, button=['Okay'])

            self.publish_btn.setText("Please update CHAR Rigs before continue...")
            self._set_status(False, "ERROR: UPDATE RIGS")
            return

        self.publish_btn.setText("PUBLISHING...")

        # Cambiamos el modo de Evaluation a 'DG'
        mc.evaluationManager(mode='off')

        success, msg, abc_paths = animation_publisher.publish_animation(self.context, self.engine, self.log, self.get_selected())

        # Volvemos a 'Parallel'
        mc.evaluationManager(mode='off')

        if success:

            # Cargamos los alembics para check
            for p in abc_paths:
                ref_node = mc.file(
                    abc_paths[p],
                    reference=True,
                    loadReferenceDepth="all",
                    mergeNamespacesOnClash=False,
                    namespace=f"exported_{p}",
                )
            warn = "The exported abc files have been referenced in the scene, please check all is fine before continue :)"
            mc.confirmDialog(title='Finishing...', message=warn, button=['Okay'])

            self.publish_btn.setText(msg)

        self._set_status(success, msg)

    def get_animated_objects(self):
        """Devuelve transforms que tengan al menos una curva de anim conectada a T/R/S."""

        moving = []
        for t in mc.ls(type='transform', long=True) or []:

            # Excluimos las cámaras
            shapes = mc.listRelatives(t, shapes=True, fullPath=True) or []
            if any(mc.nodeType(s) == 'camera' for s in shapes):
                continue

            # Miramos si tiene curvas de animación
            curves = mc.listConnections(t, type='animCurve', s=True, d=False) or []
            if curves:
                moving.append(t)

        return sorted(set(moving))

    def select_all(self):
        """Selecciona todos los checkboxes."""
        for cb in self.checkboxes:
            cb.setChecked(True)

    def disable_checkboxes(self):
        """Selecciona todos los checkboxes."""
        for cb in self.checkboxes:
            cb.setEnabled(False)

    def deselect_all(self):
        """Deselecciona todos los checkboxes."""
        for cb in self.checkboxes:
            cb.setChecked(False)

    def get_selected(self):

        selected_assets = []

        for cb in self.checkboxes:
            if cb.isChecked():
                selected_assets.append(cb.asset_data)

        if not selected_assets:
            print("\n⚠ No hay assets seleccionados para publicar")
            qt.QMessageBox.warning(self, "Advertencia", "No hay assets seleccionados para publicar")
            return

        print("-"*70)
        print(f"SELECTED ASSETS --> {[i['namespace'] for i in selected_assets]}")
        return selected_assets

    def _set_status(self, ok, msg):
        self.status_lbl.setText(msg)

        # Verde si OK, rojo si FAIL (sin complicarte)
        if ok:
            self.status_lbl.setStyleSheet("QLabel { color: #2ecc71; }")
        else:
            self.status_lbl.setStyleSheet("QLabel { color: #e74c3c; }")

    def _check_rigs(self):
        "Check if the referenced rig is the last version"
        to_update = []

        for asset in self.get_selected():
            if asset["group"] == "CHAR":
                is_last, msg = self._is_last_version(asset["ref_node"], "maya_asset_publish")
                if not is_last:
                    to_update.append(msg)

        return to_update

    def _is_last_version(self, ref_node, template_name):

        # Get fields from path
        ref_path = mc.referenceQuery(ref_node, filename=True, wcn=True)
        template = self.tk.templates[template_name]
        fields = template.get_fields(ref_path)

        # Look for last version
        fields_no_version = fields.copy()
        fields_no_version.pop("version")
        paths = self.tk.paths_from_template(template, fields_no_version)
        paths.sort(reverse=True)

        # Compare versions
        fields_last = template.get_fields(paths[0])

        if fields["version"] != fields_last["version"]:
            msg = f"There is a newer version of - {fields['Asset']}_{fields['name']} ({fields['Task']})-, please update it to version {fields_last['version']}"
            return False, msg

        msg = f" Using right version for - {fields['Asset']}_{fields['name']} ({fields['Task']})- version({fields_last['version']})"
        return True, msg


def showUI():
    """Muestra la ventana de publish."""
    global universal_publish_ui

    try:
        universal_publish_ui.close()
        universal_publish_ui.deleteLater()
    except:
        pass

    universal_publish_ui = AnimPubUI()
    universal_publish_ui.show(dockable=True)


def has_animation(node):
    """
    Verifica si un nodo o cualquiera de sus hijos tiene al menos un keyframe.
    Se detiene en cuanto encuentra el primero para optimizar.

    Args:
        node (str): Nombre del nodo a verificar

    Returns:
        bool: True si encuentra al menos un keyframe, False en caso contrario
    """
    # Obtener el nodo y todos sus descendientes
    descendants = mc.listRelatives(node, allDescendents=True, fullPath=True) or []
    all_nodes = [node] + descendants

    # Buscar keyframes en cada nodo
    for check_node in all_nodes:
        # Verificar si el nodo tiene keyframes para ponerlo en la lista
        keyframes = mc.keyframe(check_node, query=True, keyframeCount=True)
        if keyframes and keyframes > 0:
            return True

    return False


def get_characters_and_props():
    """
    Lista todos los characters y props ANIMADOS de la escena basándose en la jerarquía.
    Solo incluye assets que tengan al menos un keyframe.

    Returns:
        dict: Diccionario con 'characters' y 'props', cada uno conteniendo una lista de assets
    """
    results = {
        'characters': [],
        'props': []
    }

    # Lo primero que hacemos es desbloquear las Anim Layers
    animLayers = mc.ls(type="animLayer")
    for layer in animLayers:
        mc.animLayer(layer, e=1, lock=0)

    # Buscar grupo CHAR
    if mc.objExists('CHAR'):
        char_children = mc.listRelatives('CHAR', children=True, type='transform') or []
        print(f"\n🔍 Analizando {len(char_children)} characters...")

        for child in char_children:
            if has_animation(child):
                if ':' in child:
                    parts = child.split(':')
                    namespace = ':'.join(parts[:-1])
                    name = parts[-1]
                else:
                    namespace = ''
                    name = child

                ref_node = mc.referenceQuery(child, referenceNode=True)
                name, variant, number = _get_instance_number(namespace)

                results['characters'].append({
                    'name': name,
                    'namespace': namespace,
                    'full_name': child,
                    'variant': variant,
                    'instance_num': number,
                    'ref_node': ref_node,
                    'group': 'CHAR'
                })
                print(f"  ✓ {child} - ANIMADO")
            else:
                print(f"  ✗ {child} - sin animación (omitido)")
    else:
        print("⚠ Grupo 'CHAR' no existe en la escena")

    # Buscar grupo PROPS
    if mc.objExists('PROPS'):
        prop_children = mc.listRelatives('PROPS', children=True, type='transform') or []
        print(f"\n🔍 Analizando {len(prop_children)} props...")

        for child in prop_children:
            if has_animation(child):
                if ':' in child:
                    parts = child.split(':')
                    namespace = ':'.join(parts[:-1])
                    name = parts[-1]
                else:
                    namespace = ''
                    name = child

                ref_node = mc.referenceQuery(child, referenceNode=True)
                name, variant, number = _get_instance_number(namespace)

                results['props'].append({
                    'name': name,
                    'namespace': namespace,
                    'full_name': child,
                    'variant': variant,
                    'instance_num': number,
                    'ref_node': ref_node,
                    'group': 'PROPS'
                })
                print(f"  ✓ {child} - ANIMADO")
            else:
                print(f"  ✗ {child} - sin animación (omitido)")
    else:
        print("⚠ Grupo 'PROPS' no existe en la escena")

    print(f"\n📊 Total animados: {len(results['characters'])} characters, {len(results['props'])} props")

    return results


def _backup_current_scene_temp(scene_path):
    # Ruta actual de la escena en Maya

    if not scene_path:
        mc.error("Scene must be saved before publishing...")

    # Carpeta temporal del sistema
    temp_dir = tempfile.gettempdir()

    # Nombre del archivo temporal basado en el nombre real
    base = os.path.basename(scene_path)
    temp_path = os.path.join(temp_dir, f"TMP_BACKUP_{base}")

    # Copia fiel del archivo (.ma o .mb)
    shutil.copy2(scene_path, temp_path)

    print("Backup temporal creado en:", temp_path)
    return temp_path


def _get_instance_number(namespace):
    "Dado un string del tipo 'cono_scene1' devuelve (cono, scene, 1)"

    if ":" in namespace:
        name = namespace.split(":")[-1]
    else:
        name = namespace

    pattern = re.compile(r"^(.*?)(\d+)?$")

    match = pattern.match(name)
    if not match:
        return f"ERROR: Pattern do not match with name '{name}'..."

    print(match)

    root, number = match.groups()

    print(root)

    name, variant = root.split("_")
    number = int(number) if number else None

    return name, variant, number
