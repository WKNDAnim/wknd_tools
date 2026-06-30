import maya.cmds as mc
from PySide6 import QtWidgets, QtCore, QtGui

from ..blocks import StateBlock, TransitionBlock


STATE_COLORS = {
    "idle":    "#4a4a8a",
    "walking": "#2a7a2a",
    "sitting": "#8a6a2a",
    "custom":  "#8a2a2a",
}


class TimelineWidget(QtWidgets.QWidget):

    blocks_changed  = QtCore.Signal()
    block_selected  = QtCore.Signal(object)
    block_deselected = QtCore.Signal()

    def __init__(self, block_manager, parent=None):

        super().__init__(parent)
        self.block_manager = block_manager
        self.selected_block = None

        self.frame_start = block_manager.frame_start
        self.frame_end = block_manager.frame_end

        self.setMinimumHeight(80)
        self.setMinimumWidth(400)
        self.setMouseTracking(True)

    # -------------------------
    # Conversión frame <-> pixel
    # -------------------------

    def _frame_to_px(self, frame):

        total = self.frame_end - self.frame_start
        if total == 0:
            return 0
        return int((frame - self.frame_start) / total * self.width())

    def _px_to_frame(self, px):

        total = self.frame_end - self.frame_start
        frame = self.frame_start + px / self.width() * total
        return int(round(frame))

    # -------------------------
    # Paint
    # -------------------------

    def paintEvent(self, event):

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor("#1a1a1a"))
        self._draw_ruler(painter)

        # Primero StateBlocks
        for block in self.block_manager.blocks:
            if type(block).__name__ == "StateBlock":
                self._draw_state_block(painter, block)

        # Luego TransitionBlocks encima
        for block in self.block_manager.blocks:
            if type(block).__name__ == "TransitionBlock":
                self._draw_transition_block(painter, block)

        painter.end()

    def _draw_ruler(self, painter):

        painter.setPen(QtGui.QColor("#555"))
        total = self.frame_end - self.frame_start
        step = max(1, total // 10)

        for frame in range(self.frame_start, self.frame_end + 1, step):
            x = self._frame_to_px(frame)
            painter.drawLine(x, 0, x, 8)
            painter.setPen(QtGui.QColor("#888"))
            painter.drawText(x + 2, 16, str(frame))
            painter.setPen(QtGui.QColor("#555"))

    def _draw_state_block(self, painter, block):

        x1 = self._frame_to_px(block.start)
        x2 = self._frame_to_px(block.end)
        w = max(4, x2 - x1)
        h = self.height() - 22
        y = 20

        color = QtGui.QColor(STATE_COLORS.get(block.state, "#555"))
        if block == self.selected_block:
            color = color.lighter(140)

        painter.fillRect(x1, y, w, h, color)
        painter.setPen(QtGui.QColor("#fff") if block != self.selected_block else QtGui.QColor("#ff0"))
        painter.drawRect(x1, y, w, h)

        if w > 30:
            rect = QtCore.QRect(x1 + 4, y, w - 8, h)
            painter.setPen(QtGui.QColor("#fff"))
            painter.drawText(rect, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, block.state)

    def _draw_transition_block(self, painter, block):

        x1 = self._frame_to_px(block.start)
        x2 = self._frame_to_px(block.end)
        w = max(4, x2 - x1)
        h = self.height() - 22
        y = 20

        # Degradado entre los dos colores de estado
        color_from = QtGui.QColor(STATE_COLORS.get(block.state_from, "#555"))
        color_to = QtGui.QColor(STATE_COLORS.get(block.state_to, "#555"))

        if block == self.selected_block:
            color_from = color_from.lighter(140)
            color_to = color_to.lighter(140)

        gradient = QtGui.QLinearGradient(x1, y, x2, y)
        gradient.setColorAt(0, color_from)
        gradient.setColorAt(1, color_to)

        painter.fillRect(x1, y, w, h, gradient)

        pen = QtGui.QPen(QtGui.QColor("#ff0" if block == self.selected_block else "#fff"))
        pen.setStyle(QtCore.Qt.DashLine)
        painter.setPen(pen)
        painter.drawRect(x1, y, w, h)

        if w > 40:
            rect = QtCore.QRect(x1 + 4, y, w - 8, h)
            painter.setPen(QtGui.QColor("#fff"))
            painter.drawText(rect, QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft,
                            f"{block.frames_from}f + {block.frames_to}f")

    # -------------------------
    # Mouse
    # -------------------------

    def mousePressEvent(self, event):

        if event.button() == QtCore.Qt.LeftButton:
            block = self._block_at(event.position().x())

            if block:
                if block == self.selected_block:
                    self.selected_block = None
                    self.block_deselected.emit()
                    self.update()
                else:
                    self.selected_block = block
                    self.block_selected.emit(block)
                    self.update()
            else:
                if self.selected_block:
                    self.selected_block = None
                    self.block_deselected.emit()
                    self.update()

        elif event.button() == QtCore.Qt.RightButton:

            block = self._block_at(event.position().x())
            if block and type(block).__name__ == "StateBlock":
                if len(self.block_manager.get_state_blocks()) > 1:
                    if self.selected_block == block:
                        self.selected_block = None
                        self.block_deselected.emit()
                    self.block_manager._fill_gap(block.start, block.end)
                    self.block_manager.blocks.remove(block)
                    self.block_manager._rebuild_transitions()
                    self.blocks_changed.emit()
                    self.update()

    def _block_at(self, px):

        # Primero buscamos TransitionBlocks
        for block in self.block_manager.blocks:
            if type(block).__name__ == "TransitionBlock":
                x1 = self._frame_to_px(block.start)
                x2 = self._frame_to_px(block.end)
                if x1 <= px <= x2:
                    return block

        # Luego StateBlocks
        for block in self.block_manager.blocks:
            if type(block).__name__ == "StateBlock":
                x1 = self._frame_to_px(block.start)
                x2 = self._frame_to_px(block.end)
                if x1 <= px <= x2:
                    return block

        return None

    # -------------------------
    # API pública
    # -------------------------

    def refresh(self):
        self.update()
