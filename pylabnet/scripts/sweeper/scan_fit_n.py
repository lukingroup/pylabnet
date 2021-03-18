from pylabnet.gui.pyqt.external_gui import Popup, InternalPopup
import sys
from PyQt5 import (QtCore, QtGui, QtWidgets)
from PyQt5.QtWidgets import  (
    QApplication, QDialog, QMainWindow, QMessageBox)
from scipy.optimize import curve_fit # is not automatically installed?
import numpy as np

def lorentzian(x, *params):
    """
    :param params: parameters for lorentzian in the order center, width, amp
    """
    cen = params[0]
    wid = params[1]
    amp = params[2]
    off = params[3]
    return off + amp*0.5*wid/((x - cen)**2 + (0.5*wid)**2)

def reflection(Delta, Delta_ac, g, gamma, kwg, k):
    return (1j*Delta + (g**2/(1j*(Delta-Delta_ac) + gamma/2)) \
        - kwg + k/2)/(1j*Delta + (g**2/(1j*(Delta-Delta_ac) + gamma/2)) + k/2)

def ref_int(Delta, Delta_ac, g, kwg, k, a, offset):
    return a*np.abs(reflection(Delta, Delta_ac, g, 0.1, kwg, k))**2 + offset

class FitModel():
    def __init__(self, name, func, *fit_params):
        self.func = func
        self.name = name
        self.fit_params = fit_params
    
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
        obj.fparams_lab2 = dict()
        obj.fparams2 = dict()

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

        for param in self.fit_params:
            obj.fparams_lab2[param] = QtWidgets.QLabel(obj.formLayoutWidget)
            obj.fparams_lab2[param].setObjectName("f" + param + "_lab_2")
            obj.fparams_lab2[param].setText(_translate("Form", "Bwd Fitted " + param + ":"))
            obj.gridlayout.addWidget(obj.fparams_lab2[param],
                                            row, col, 1, 1)

            obj.fparams2[param] = QtWidgets.QLabel(obj.formLayoutWidget)
            obj.fparams2[param].setText("")
            obj.fparams2[param].setObjectName("fit_" + param + "_2")
            obj.gridlayout.addWidget(obj.fparams2[param], 
                                            row, col + 1, 1, 1)
            row = row + 1
        obj.main.setLayout(lab_ct + 1, QtWidgets.QFormLayout.FieldRole, obj.gridlayout)
        QtCore.QMetaObject.connectSlotsByName(obj)
        obj.show()

if __name__ == "__main__":
    lor = FitModel("Lorentzian",lorentzian, "Center","FWHM","Amp","Offset", "Bab")
    app = QApplication(sys.argv)
    lor.popup = QMainWindow()
    lor.init_ui(lor.popup)
    app.exec_()