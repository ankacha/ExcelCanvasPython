import sys
import math
from PySide6.QtWidgets import (QApplication, QMainWindow, QToolBar,
                               QGraphicsView, QGraphicsScene, QGraphicsItem,
                               QStyleOptionGraphicsItem, QWidget, QGraphicsPathItem)
from PySide6.QtGui import QAction, QPen, QBrush, QPainter, QColor, QCursor, QTransform, QPainterPath
from PySide6.QtCore import Qt, QPoint, QRectF, QPointF
from typing import Optional

# --- 1. The ZoomPanView Class (our advanced "camera") ---
# This class is taken directly from our last example.
class ZoomPanView(QGraphicsView):
    def __init__(self, scene):
        super().__init__(scene)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self._is_panning = False
        self._last_pan_point = QPoint()

        # --- NEW: Define zoom limits ---
        self.min_zoom = 0.25 # Corresponds to 25% zoom
        self.max_zoom = 4.0  # Corresponds to 400% zoom
        # --- FIX FOR GRAPHICAL ARTIFACTS ---
        # This setting tells the view to redraw the entire viewport on every
        # single change. It is slightly less efficient than the default mode,
        # but it prevents rendering glitches, trails, and artifacts like the one you saw.
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        grid_size = 20
        major_line_every = 5

        pen_light = QPen(QColor(230, 230, 230))
        pen_dark = QPen(QColor(200, 200, 200))
        scene_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        left = int(math.floor(scene_rect.left() / grid_size)) * grid_size
        top = int(math.floor(scene_rect.top() / grid_size)) * grid_size

        x = left
        count_x = int(math.floor(scene_rect.left() / grid_size))
        while x < scene_rect.right():
            painter.setPen(pen_dark if count_x % major_line_every == 0 else pen_light)
            painter.drawLine(x, int(scene_rect.top()), x, int(scene_rect.bottom()))
            x += grid_size
            count_x += 1

        y = top
        count_y = int(math.floor(scene_rect.top() / grid_size))
        while y < scene_rect.bottom():
            painter.setPen(pen_dark if count_y % major_line_every == 0 else pen_light)
            painter.drawLine(int(scene_rect.left()), y, int(scene_rect.right()), y)
            y += grid_size
            count_y += 1

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        # Get the current transformation matrix of the view.
        # This matrix holds information about the current rotation, scale, and translation.
        transform = self.transform()

        # The 'm11()' method returns the horizontal scale factor, and 'm22()' the vertical.
        current_scale = transform.m11()

        # Determine the zoom factor based on scroll direction.
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
            # Check if zooming in would exceed the maximum limit.
            if current_scale * zoom_factor > self.max_zoom:
                return  # If it would, do nothing and exit the function.
        else:
            zoom_factor = zoom_out_factor
            # Check if zooming out would go below the minimum limit.
            if current_scale * zoom_factor < self.min_zoom:
                return  # If it would, do nothing and exit the function.

        # If we are within the limits, apply the scaling.
        self.scale(zoom_factor, zoom_factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._is_panning = True
            self._last_pan_point = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_panning:
            delta = event.position() - self._last_pan_point
            self.horizontalScrollBar().setValue(int(self.horizontalScrollBar().value() - delta.x()))
            self.verticalScrollBar().setValue(int(self.verticalScrollBar().value() - delta.y()))
            self._last_pan_point = event.position()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class ConnectionItem(QGraphicsPathItem):
    def __init__(self, start_item, end_item):
        super().__init__()
        # Store the start and end nodes this connection belongs to.
        self.start_item = start_item
        self.end_item = end_item

        # Set a Z-value to ensure lines are drawn behind nodes for a cleaner look.
        self.setZValue(-1)
        # Set the pen style for the connection line.
        self.setPen(QPen(QColor(20, 20, 20), 2))  # Dark gray, 2-pixel thick pen

    # This method calculates and sets the curved path of the line.
    def update_path(self):
        # Create a QPainterPath for our Bézier curve.
        path = QPainterPath()

        # Get the port positions in global scene coordinates using mapToScene.
        start_pos = self.start_item.mapToScene(self.start_item.output_pos)
        end_pos = self.end_item.mapToScene(self.end_item.input_pos)

        # Start the path at the starting port.
        path.moveTo(start_pos)

        # Calculate control points for a nice "S" shaped curve.
        dx = end_pos.x() - start_pos.x()
        ctrl1 = QPointF(start_pos.x() + dx * 0.5, start_pos.y())
        ctrl2 = QPointF(start_pos.x() + dx * 0.5, end_pos.y())

        # Add the cubic Bézier curve to the path.
        path.cubicTo(ctrl1, ctrl2, end_pos)

        # Set the calculated path for this item to draw.
        self.setPath(path)


class CustomNode(QGraphicsItem):
    def __init__(self):
        super().__init__()
        self.width, self.height = 150, 100
        self.port_radius = 6
        self.input_pos = QPointF(0, self.height / 2)
        self.output_pos = QPointF(self.width, self.height / 2)
        self.pen_default = QPen(QColor(0, 0, 0)); self.pen_default.setWidth(2)
        self.pen_selected = QPen(QColor(255, 165, 0)); self.pen_selected.setWidth(5)
        self.brush_default = QBrush(QColor(240, 255, 240))
        self.brush_selected = QBrush(QColor(255, 235, 180))
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        # NEW: This flag is important for the itemChange method to work correctly.
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)

        # NEW: A list to store all connection items attached to this node.
        self.connections = []

    def boundingRect(self):
        return QRectF(0 - self.port_radius, 0, self.width + 2 * self.port_radius, self.height)

    # --- NEW: The itemChange method ---
    # This special method is called by Qt whenever an item's state changes.
    def itemChange(self, change, value):
        # We are interested when the item's position has changed.
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Loop through all connections attached to this node.
            for conn in self.connections:
                # Tell the connection to update its path.
                conn.update_path()
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        body_path = QPainterPath()
        body_path.addRoundedRect(0, 0, self.width, self.height, 10, 10)
        if self.isSelected():
            painter.setBrush(self.brush_selected); painter.setPen(self.pen_selected)
        else:
            painter.setBrush(self.brush_default); painter.setPen(self.pen_default)
        painter.drawPath(body_path)
        painter.setPen(self.pen_default)
        painter.setBrush(QBrush(QColor(25, 180, 0)))
        painter.drawEllipse(self.input_pos, self.port_radius, self.port_radius)
        painter.drawEllipse(self.output_pos, self.port_radius, self.port_radius)


class NodeEditorScene(QGraphicsScene):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.line_in_progress, self.start_item, self.start_pos = None, None, None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            view = self.views()[0]
            item = self.itemAt(event.scenePos(), view.transform())
            if isinstance(item, CustomNode):
                output_port_pos = item.mapToScene(item.output_pos)
                if (event.scenePos() - output_port_pos).manhattanLength() < 15.0:
                    self.start_item = item
                    self.start_pos = output_port_pos
                    view.setDragMode(QGraphicsView.DragMode.NoDrag)
                    pen = QPen(Qt.GlobalColor.darkGreen, 2, Qt.PenStyle.DashLine)
                    self.line_in_progress = self.addLine(self.start_pos.x(), self.start_pos.y(), self.start_pos.x(),
                                                         self.start_pos.y(), pen)
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.line_in_progress:
            self.line_in_progress.setLine(self.start_pos.x(), self.start_pos.y(), event.scenePos().x(),
                                          event.scenePos().y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # If a line drawing was in progress...
        if self.line_in_progress:
            view = self.views()[0]
            view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            # Remove the temporary red line.
            self.removeItem(self.line_in_progress)

            # --- NEW: Logic to create a permanent connection ---
            # Check if the mouse was released over a valid target node.
            end_item = self.itemAt(event.scenePos(), view.transform())
            if isinstance(end_item, CustomNode) and self.start_item != end_item:
                # Check if the release point is close to the target node's input port.
                input_port_pos = end_item.mapToScene(end_item.input_pos)
                if (event.scenePos() - input_port_pos).manhattanLength() < 15.0:
                    # Create the permanent connection item.
                    conn = ConnectionItem(self.start_item, end_item)
                    # Add it to the scene.
                    self.addItem(conn)
                    # Register the connection with both nodes so they know about it.
                    self.start_item.connections.append(conn)
                    end_item.connections.append(conn)
                    # Update its path to draw the initial curve correctly.
                    conn.update_path()

            # Reset state variables regardless of success.
            self.line_in_progress, self.start_item, self.start_pos = None, None, None
            event.accept()
            return

        super().mouseReleaseEvent(event)


# --- 3. The MainWindow Class (with two small changes) ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Node Editor - Full Canvas")
        self.resize(1024, 768)

        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        add_node_action = QAction("Add Node", self)
        add_node_action.triggered.connect(self.on_add_node_clicked)
        toolbar.addAction(add_node_action)

        #set the scene pass self(the main window) as the parent
        self.scene = NodeEditorScene(self)
        self.scene.setBackgroundBrush(QColor(240, 240, 240)) # A light gray
        #instantiate the custom view
        self.view = ZoomPanView(self.scene)

        #set the central widget
        self.setCentralWidget(self.view)

    def on_add_node_clicked(self):
        node = CustomNode()
        import random
        node.setPos(random.randint(0, 500), random.randint(0, 200))
        self.scene.addItem(node)


# --- Standard boilerplate to run the application ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())