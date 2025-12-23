"""
Ventana simple para mostrar actualizaciones en Maya
"""

import maya.cmds as cmds

try:
    from PySide6 import QtWidgets, QtCore
except ImportError:
    from PySide2 import QtWidgets, QtCore


class ProgressWindow(QtWidgets.QDialog):
    """Ventana con barra de progreso"""
    
    def __init__(self, total_items, parent=None):
        super(ProgressWindow, self).__init__(parent)
        
        self.setWindowTitle("Actualizando Referencias")
        self.setFixedSize(400, 120)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowTitleHint | QtCore.Qt.CustomizeWindowHint)
        
        self.total_items = total_items
        self.current_item = 0
        
        self.setup_ui()
    
    def setup_ui(self):
        """Crea la interfaz"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Label de progreso
        self.progress_label = QtWidgets.QLabel("Preparando actualización...")
        self.progress_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.progress_label)
        
        # Barra de progreso
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(self.total_items)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Label de contador
        self.counter_label = QtWidgets.QLabel(f"0 / {self.total_items}")
        self.counter_label.setAlignment(QtCore.Qt.AlignCenter)
        self.counter_label.setStyleSheet("color: gray;")
        layout.addWidget(self.counter_label)
    
    def update_progress(self, current, message=""):
        """
        Actualiza la barra de progreso
        
        Args:
            current (int): Item actual
            message (str): Mensaje a mostrar
        """
        self.current_item = current
        self.progress_bar.setValue(current)
        self.counter_label.setText(f"{current} / {self.total_items}")
        
        if message:
            self.progress_label.setText(message)
        
        # Forzar actualización de la UI
        QtWidgets.QApplication.processEvents()
    
    def finish(self):
        """Marca como completado"""
        self.progress_bar.setValue(self.total_items)
        self.progress_label.setText("✓ Actualización completada")
        self.counter_label.setText(f"{self.total_items} / {self.total_items}")


class SimpleUpdateWindow(QtWidgets.QDialog):
    """Ventana simple que muestra qué se actualizó"""
    
    def __init__(self, updates_list, parent=None):
        """
        Args:
            updates_list: Array de arrays [[old, new], [old, new], ...]
        """
        super(SimpleUpdateWindow, self).__init__(parent)
        
        self.updates_list = updates_list
        
        self.setWindowTitle("Referencias Actualizadas")
        self.setMinimumSize(500, 300)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Crea la interfaz"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Título
        title = QtWidgets.QLabel(f"Se actualizaron {len(self.updates_list)} referencias:")
        title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Área de texto scrollable
        text_area = QtWidgets.QTextEdit()
        text_area.setReadOnly(True)
        
        # Construir el mensaje
        message = ""
        for old, new in self.updates_list:
            message += f"• {old}\n"
            message += f"  ➜ {new}\n\n"
        
        text_area.setPlainText(message)
        layout.addWidget(text_area)
        
        # Botón OK
        ok_btn = QtWidgets.QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setFixedWidth(100)
        
        btn_layout = QtWidgets.QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)


def show_updates(updates_list):
    """
    Muestra la ventana con las actualizaciones
    
    Args:
        updates_list: Array como [["ref_old_v001.ma", "ref_new_v002.ma"], ...]
    """
    window = SimpleUpdateWindow(updates_list)
    window.exec_()


def create_progress_window(total_items):
    """
    Crea y muestra una ventana de progreso
    
    Args:
        total_items (int): Número total de items a procesar
        
    Returns:
        ProgressWindow: Instancia de la ventana de progreso
    """
    progress = ProgressWindow(total_items)
    progress.show()
    QtWidgets.QApplication.processEvents()
    return progress


# ============================================================================
# Ejemplo de uso completo con progreso
# ============================================================================

def example_with_progress():
    """Ejemplo de cómo usar la ventana de progreso"""
    import time
    
    # Lista de cosas a actualizar
    updates_to_do = [
        ["character_rig_v001.ma", "character_rig_v003.ma"],
        ["prop_table_v002.abc", "prop_table_v005.abc"],
        ["environment_v001.ma", "environment_v002.ma"],
        ["fx_particle_v001.abc", "fx_particle_v004.abc"]
    ]
    
    # Crear ventana de progreso
    progress = create_progress_window(len(updates_to_do))
    
    completed_updates = []
    
    try:
        # Procesar cada update
        for i, (old, new) in enumerate(updates_to_do, 1):
            # Actualizar progreso
            progress.update_progress(i, f"Actualizando: {old}")
            
            # AQUÍ VA TU CÓDIGO DE ACTUALIZACIÓN
            # Por ejemplo: tool.update_reference(ref_data, latest)
            time.sleep(0.5)  # Simula el proceso
            
            completed_updates.append([old, new])
        
        # Marcar como completado
        progress.finish()
        time.sleep(0.5)  # Pausa breve para que vean el 100%
        
    finally:
        # Cerrar ventana de progreso
        progress.close()
    
    # Mostrar resultado final
    if completed_updates:
        show_updates(completed_updates)


# ============================================================================
# Ejemplo de uso
# ============================================================================

# if __name__ == "__main__":
#     # Ejemplo simple sin progreso
#     updates = [
#         ["character_rig_v001.ma", "character_rig_v003.ma"],
#         ["prop_table_v002.abc", "prop_table_v005.abc"],
#         ["environment_v001.ma", "environment_v002.ma"]
#     ]
    
#     show_updates(updates)
    
#     # O con progreso
#     # example_with_progress()