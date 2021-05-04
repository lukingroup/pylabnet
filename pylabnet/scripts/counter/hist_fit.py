from pylabnet.gui.pyqt.external_gui import Popup, InternalPopup
import sys
from PyQt5 import (QtCore, QtGui, QtWidgets)
from PyQt5.QtWidgets import  (
    QApplication, QDialog, QMainWindow, QMessageBox)
from scipy.optimize import curve_fit # is not automatically installed?
import numpy as np

def exp_decay(t, a, b, T1):
    return a - (a-b)*np.exp(-t/T1)

class FitPopup(Popup):
    def __init__(self, ui, x, data, p0, config, log):
        super().__init__(ui)
        self.log = log
        self.data = np.array(data)
        self.x = np.array(x)
        self.p0 = p0
        self.config = config
        self.fit_suc = True
        self.mod = None

    def fit_selection(self, index):
        if index == 0:
            self.mod = FitModel("Exponential Decay", exp_decay,
            "Midpoint", " Lowpoint", "T")

        self.mod.load_mod(config = self.config)
        self.close()

    def fit_mod(self):
        fit, self.p0, self.fit_suc = self.mod.fit_mod(
            self.x,
            self.data,
            self.p0)
        return fit, self.p0


class FitModel():
    def __init__(self, name, func, *fit_params):
        self.func = func
        self.name = name
        self.fit_params = fit_params
        self.p0_updated = False
        self.init_params = None
        self.pop = None

    def load_mod(self, config = None):
        self.pop = QMainWindow()
        self.init_ui(self.pop)
        try:
            for param in self.fit_params:
                self.pop.params[param].setText(str(config[self.name + "params"][param]))
        except:
            pass
        self.pop.confirm.clicked.connect(self.set_mod)

    def set_mod(self):
        self.init_params = dict()
        for param in self.fit_params:
            self.init_params[param] = float(self.pop.params[param].text())
        self.p0_updated = True

    def fit_mod(self, x, data, p0 = None):
        if self.init_params is not None:
            p = list()
            for param in self.fit_params:
                p.append(self.init_params[param])
            if p0 is None or self.p0_updated:
                p0_f = p
                self.p0_updated = False
            else:
                p0_f = p0
            try:
                popt, pcov = curve_fit(self.func, x, data, p0 = p0_f)
                p0_f = popt
                #print(pcov1)
                fit_suc = True
            except:
                p0_f = p
                popt = np.zeros_like(p)
                fit_suc = False
            for ind, param in enumerate(self.fit_params):
                self.pop.fparams[param].setText(str(popt[ind]))
                #self.pop.fparams2[param].setText(str(popt2[ind]))
            return self.func(x, *popt), p0_f, fit_suc

    def init_ui(self, obj):
        obj.setObjectName("Form")
        obj.resize(982, 793)
        _translate = QtCore.QCoreApplication.translate
        obj.setWindowTitle(_translate("Form", "Form"))

        obj.formLayoutWidget = QtWidgets.QWidget(obj)
        obj.formLayoutWidget.setGeometry(QtCore.QRect(10, 10, 961, 781))
        obj.formLayoutWidget.setObjectName("formLayoutWidget")
        obj.main = QtWidgets.QFormLayout(obj.formLayoutWidget)
        obj.main.setContentsMargins(0, 0, 0, 0)
        obj.main.setObjectName("main")
        obj.title = QtWidgets.QLabel(obj.formLayoutWidget)
        obj.title.setAlignment(QtCore.Qt.AlignCenter)
        obj.title.setObjectName("title")
        obj.main.setWidget(0, QtWidgets.QFormLayout.SpanningRole, obj.title)
        obj.title.setText(_translate("Form", self.name + " Fit Parameters: Initial Guesses"))

        obj.param_labs = dict()
        obj.params = dict()
        obj.fparams_lab = dict()
        obj.fparams = dict()

        lab_ct = 2
        for param in self.fit_params:
            obj.param_labs[param] = QtWidgets.QLabel(obj.formLayoutWidget)
            obj.param_labs[param].setObjectName(param + "_lab")
            obj.main.setWidget(lab_ct, QtWidgets.QFormLayout.LabelRole,
                                       obj.param_labs[param])
            obj.param_labs[param].setText(_translate("Form", param + ":"))

            obj.params[param] = QtWidgets.QLineEdit(obj.formLayoutWidget)
            obj.params[param].setObjectName(param)
            obj.main.setWidget(lab_ct, QtWidgets.QFormLayout.FieldRole,
                                obj.params[param])
            lab_ct = lab_ct + 1

        obj.confirm = QtWidgets.QPushButton(obj.formLayoutWidget)
        obj.confirm.setObjectName("confirm")
        obj.confirm.setText(_translate("Form", "OK"))
        obj.main.setWidget(lab_ct, QtWidgets.QFormLayout.FieldRole, obj.confirm)
        obj.gridlayout = QtWidgets.QGridLayout()
        obj.gridlayout.setObjectName("gridlayout")

        row = 0
        col = 0
        for param in self.fit_params:
            obj.fparams_lab[param] = QtWidgets.QLabel(obj.formLayoutWidget)
            obj.fparams_lab[param].setObjectName("f" + param + "_lab")
            obj.fparams_lab[param].setText(_translate("Form", "Fwd Fitted " + param + ":"))
            obj.gridlayout.addWidget(obj.fparams_lab[param],
                                            row, col, 1, 1)

            obj.fparams[param] = QtWidgets.QLabel(obj.formLayoutWidget)
            obj.fparams[param].setText("")
            obj.fparams[param].setObjectName("fit_" + param)
            obj.gridlayout.addWidget(obj.fparams[param],
                                            row, col + 1, 1, 1)
            row = row + 1

        row = 0
        col = 2

        obj.main.setLayout(lab_ct + 1, QtWidgets.QFormLayout.FieldRole, obj.gridlayout)
        QtCore.QMetaObject.connectSlotsByName(obj)
        obj.show()

if __name__ == "__main__":
    lor = FitModel("Exponential Decay", exp_decay, "Midpoint", " Lowpoint", "T")
    app = QApplication(sys.argv)
    lor.load_mod()
    #lor.popup = QMainWindow()
    #lor.init_ui(lor.popup)
    app.exec_()
