
from PyQt5.QtCore import QRect, Qt, QAbstractTableModel
from PyQt5.QtCore import QVariant

import pyqtgraph as pg


class CustomViewBox(pg.ViewBox):
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.setMouseMode(self.RectMode)

    def mouseDragEvent(self, ev):
        if ev.button() == Qt.RightButton:
            ev.ignore()
        else:
            pg.ViewBox.mouseDragEvent(self, ev)


class MyPlotWidget(pg.PlotWidget):
    def __init__(self, parent=None):
        super(MyPlotWidget, self).__init__(parent, viewBox=CustomViewBox())