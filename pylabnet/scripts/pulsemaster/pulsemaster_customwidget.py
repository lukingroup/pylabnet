
from PyQt5.QtCore import QRect, Qt, QAbstractTableModel
from PyQt5.QtWidgets import QTableWidgetItem, QToolBox, QFileDialog,  QMessageBox, QPushButton, QGroupBox, QFormLayout, QErrorMessage, QComboBox, QMainWindow, QApplication, QWidget, QAction, QTableWidget,QTableWidgetItem,QVBoxLayout, QTableWidgetItem, QCompleter, QHBoxLayout, QLabel, QLineEdit

from PyQt5.QtCore import QVariant
import pyqtgraph as pg


class CustomViewBox(pg.ViewBox):
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        self.setMouseMode(self.RectMode)

    ## reimplement right-click to zoom out
    def mouseClickEvent(self, ev):
        if ev.button() == Qt.RightButton:
            self.autoRange()

    def mouseDragEvent(self, ev):
        if ev.button() == Qt.RightButton:
            ev.ignore()
        else:
            pg.ViewBox.mouseDragEvent(self, ev)


class MyPlotWidget(pg.PlotWidget):
    def __init__(self, parent=None):
        super(MyPlotWidget, self).__init__(parent, viewBox=CustomViewBox())


class DictionaryTableModel(QAbstractTableModel):
    """ Table Model with data which can be access and set via a python dictionary."""
    def __init__(self, data, header, editable=False):
        """Instanciating  TableModel

        :data: Dictionary which should fill table,
            The key will be used to populate the first column entry,
            the item will be used to populate the subsequent columns.
            If item is String, only one column will be added. If Item is List,
            one new colum for every list item will be added.
        """
        super(DictionaryTableModel, self).__init__()

        # Prepare data.
        data_ok, datadict = self.prepare_data(data)

        assert data_ok, "Input dictionary invalid."

        self.datadict = datadict
        self._header = header

        # Set editing mode.
        self.editable = editable

    def flags(self, index):
        """ Make table fields editable."""
        if self.editable:
            return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        else:
            return Qt.NoItemFlags

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Set header."""
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._header[section]
        return QAbstractTableModel.headerData(self, section, orientation, role)

    def _prepare_single_string_dict(self, datadict):
        """ Transform data dict into list of lists.

        To be used if dictionary values are strings.
        """

        data_list = []

        for key, item in datadict.items():
            data_list.append([key, item])


        if data_list == []:
            data_list = [["", ""]]

        return data_list

    def _prepare_list_dict(self, datadict):
        """ Transform data dict into list of lists.

        To be used if dictionary values are lists.
        TODO: Test this.
        """

        data_list = []

        for i, (key, item) in enumerate(datadict.items()):
            entry_list = []
            entry_list.append(key)
            for list_entry in item:
                entry_list.append(list_entry)

        return data_list

    def prepare_data(self, datadict):
        """Check if dictioanry is either containing strings as values,
        or lists of the same length.

        Generate list out of dictionary.
        """

        values = datadict.values()
        data_ok = False

        # Check if all values are one allowed datatype:
        allowed_datatypes = [str, int, float]
        if all([type(value) in allowed_datatypes for value in values]):
                data_ok = True
                datadict = self._prepare_single_string_dict(datadict)
                return data_ok, datadict

        # Check if values are all lists.
        if all(isinstance(value, list) for value in values):

            # Check if lists are of same length.
            it = iter(values)
            the_len = len(next(it))

            if not all(len(l) == the_len for l in it):
                data_ok = False
                return data_ok, None
            else:
                data_ok = True
                datadict = self._prepare_list_dict(datadict)
                return data_ok, datadict
        else:
            data_ok = False
            return data_ok, None

    def data(self, index, role):
        """ From https://stackoverflow.com/questions/28186118/how-to-make-qtableview-to-enter-the-editing-mode-only-on-double-click"""
        if not index.isValid(): return QVariant()
        row=index.row()
        column=index.column()

        if row>len(self.datadict): return QVariant()
        if column>len(self.datadict[row]): return QVariant()

        if role == Qt.EditRole or role == Qt.DisplayRole:
            return QVariant(self.datadict[row][column])

        return QVariant()

    def setData(self, index, value, role=Qt.EditRole):
        """ From https://stackoverflow.com/questions/28186118/how-to-make-qtableview-to-enter-the-editing-mode-only-on-double-click"""
        if index.isValid():
            if role == Qt.EditRole:
                row = index.row()
                column=index.column()
                if row>len(self.datadict) or column>len(self.datadict[row]):
                    return False
                else:
                    self.datadict[row][column]=value
                    self.dataChanged.emit(index, index)
                    return True
        return False

    def rowCount(self, index):
        # The length of the outer list.
        return len(self.datadict)

    def columnCount(self, index):
        # The following takes the first sub-list, and returns
        # the length (only works if all rows are an equal length)
        return len(self.datadict[0])


    def add_dict(self, data_dict):
        """Populate table from dictionary.

        :data_dict: Dictionary to populate table from.
        """
        for i, (key, item) in enumerate(data_dict.items()):
            key = QTableWidgetItem(key)
            item = QTableWidgetItem(item)
            self.setItem(i,0,key)
            self.setItem(i,1,str(item))
