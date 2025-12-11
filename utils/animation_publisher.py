import maya.cmds as cmds
import maya.OpenMayaUI as omui
import sgtk
import maya.cmds as cmds
import maya.cmds as mc
from ..core import exporters

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
    """Retorna la ventana principal de Maya como QWidget."""
    mainWindowPointer = omui.MQtUtil.mainWindow()
    return wrapInstance(int(mainWindowPointer), qt.QWidget)


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
    descendants = cmds.listRelatives(node, allDescendents=True, fullPath=True) or []
    all_nodes = [node] + descendants

    # Buscar keyframes en cada nodo
    for check_node in all_nodes:
        # Verificar si el nodo tiene keyframes para ponerlo en la lista
        keyframes = cmds.keyframe(check_node, query=True, keyframeCount=True)
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

    # Buscar grupo CHAR
    if cmds.objExists('CHAR'):
        char_children = cmds.listRelatives('CHAR', children=True, type='transform') or []
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

                results['characters'].append({
                    'name': name,
                    'namespace': namespace,
                    'full_name': child,
                    'group': 'CHAR'
                })
                print(f"  ✓ {child} - ANIMADO")
            else:
                print(f"  ✗ {child} - sin animación (omitido)")
    else:
        print("⚠ Grupo 'CHAR' no existe en la escena")

    # Buscar grupo PROPS
    if cmds.objExists('PROPS'):
        prop_children = cmds.listRelatives('PROPS', children=True, type='transform') or []
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

                results['props'].append({
                    'name': name,
                    'namespace': namespace,
                    'full_name': child,
                    'group': 'PROPS'
                })
                print(f"  ✓ {child} - ANIMADO")
            else:
                print(f"  ✗ {child} - sin animación (omitido)")
    else:
        print("⚠ Grupo 'PROPS' no existe en la escena")

    print(f"\n📊 Total animados: {len(results['characters'])} characters, {len(results['props'])} props")

    return results


class AnimationPublisherUI(MayaQWidgetDockableMixin, qt.QDialog):
    """
    UI para seleccionar y publicar animaciones de characters y props.
    """

    def __init__(self, parent=mayaMainWindow()):
        super(AnimationPublisherUI, self).__init__(parent)

        self.setWindowTitle("Animation Publisher")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        # Datos
        self.assets_data = get_characters_and_props()
        self.checkboxes = []

        # Crear UI
        self.create_widgets()
        self.create_layout()
        self.create_connections()

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

    def create_layout(self):
        """Organiza los widgets en el layout."""
        main_layout = qt.QVBoxLayout(self)

        # Título
        main_layout.addWidget(self.title_label)

        # Scroll area con checkboxes
        main_layout.addWidget(self.scroll_area)

        # Botones de selección
        button_layout = qt.QHBoxLayout()
        button_layout.addWidget(self.select_all_btn)
        button_layout.addWidget(self.deselect_all_btn)
        main_layout.addLayout(button_layout)

        # Botón de publish
        main_layout.addWidget(self.publish_btn)

    def create_connections(self):
        """Conecta las señales de los botones."""
        self.select_all_btn.clicked.connect(self.select_all)
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        self.publish_btn.clicked.connect(self.publish)

    def select_all(self):
        """Selecciona todos los checkboxes."""
        for cb in self.checkboxes:
            cb.setChecked(True)

    def deselect_all(self):
        """Deselecciona todos los checkboxes."""
        for cb in self.checkboxes:
            cb.setChecked(False)

    def publish(self):
        """Publica los assets seleccionados (por ahora solo printea)."""
        selected_assets = []

        for cb in self.checkboxes:
            if cb.isChecked():
                selected_assets.append(cb.asset_data)

        if not selected_assets:
            print("\n⚠ No hay assets seleccionados para publicar")
            qt.QMessageBox.warning(self, "Advertencia", "No hay assets seleccionados para publicar")
            return

        print("\n" + "="*60)
        print("ASSETS SELECCIONADOS PARA PUBLICAR:")
        print("="*60)

        # /////////////////////////////////////////////////////////////////////////
        # //////////PUBLISH ASSETS/////////////////////////////////////////////////
        # /////////////////////////////////////////////////////////////////////////

        engine = sgtk.platform.current_engine()
        sg = engine.shotgun
        context = engine.context
        tk = engine.sgtk

        # Get templates
        if context.entity['type'].lower() == "asset":
            scene_work_template = tk.templates["maya_asset_work"]
            try:
                movie_template = tk.templates["maya_asset_playblast_publish"]
            except:
                movie_template = False
        else:
            scene_work_template = tk.templates["maya_shot_work"]
            movie_template = tk.templates["maya_shot_playblast_publish"]

        # Get fields from file
        file_path = cmds.file(q=1, sn=1)
        scene_fields = scene_work_template.get_fields(file_path)

        template = tk.templates["maya_shot_anim_assets_abc_publish"]

        for asset in selected_assets:
            ns = f"[{asset['namespace']}]" if asset['namespace'] else ""
            print(f"  • {asset['group']}: {asset['name']} {ns} (full: {asset['full_name']})")

            scene_fields['Asset'] = asset['name']

            ma_path = template.apply_fields(scene_fields)

            geo_to_export = (asset['namespace'] + ':geo')

            # GET FRAME RANGE FROM PLAYBACK ------- THIS SHOULD BE DONE USING SG DURATION ---------------!!!!!!!!!!!!!!!!!!!!!

            frame_in = 1000
            frame_out = int(mc.playbackOptions(q=1, max=1)) + 1

            exporters.export_alembic(geo_to_export , ma_path, frame_in, frame_out)

        print("="*60)
        print(f"Total: {len(selected_assets)} assets\n")

        # Aquí irá la lógica de export de alembic
        qt.QMessageBox.information(
            self, 
            "Publish", 
            f"Se publicarán {len(selected_assets)} assets.\n(Ver consola para detalles)"
        )


def showUI():
    """Muestra la ventana de publish."""
    global animation_publisher_ui
    try:
        animation_publisher_ui.close()
        animation_publisher_ui.deleteLater()
    except:
        pass
    animation_publisher_ui = AnimationPublisherUI()
    animation_publisher_ui.show(dockable=True)


# # Para ejecutar desde Maya:
# if __name__ == "__main__":
#     showUI()