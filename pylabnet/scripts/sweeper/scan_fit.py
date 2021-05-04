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

def doubleGaussian(x, a1, a2, c1, c2, w1, w2,o):
    return a1*np.exp(-(x-c1)**2/(2*w1**2))+a2*np.exp(-(x-c2)**2/(2*w2**2))+o

def gaussian(x, a1,  c1,  w1, o):
    return a1*np.exp(-(x-c1)**2/(2*w1**2))+o

def Rabi(x, a1, p1, w1, o):
    return a1*np.sin(2*np.pi*(x/(2*w1))+ np.pi/180*p1)+o

def dbl_lorentzian(x, *params):
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
    return a*np.abs(reflection((Delta-406.64)*1000, Delta_ac, g, 0.1, kwg, k))**2 + offset


class FitPopup(Popup):
    def __init__(self, ui, x_fwd, data_fwd, x_bwd,
                 data_bwd, p0_fwd, p0_bwd, config, log):
        super().__init__(ui)
        self.log = log
        self.data_fwd = np.array(data_fwd)
        self.x_fwd = np.array(x_fwd)
        self.x_bwd = np.array(x_bwd)
        self.data_bwd = np.array(data_bwd)
        self.p0_fwd = p0_fwd
        self.p0_bwd = p0_bwd
        self.config = config
        self.fit_suc = True
        self.mod = None

    def fit_selection(self, index):
        if index == 0:
            self.mod = FitModel("Lorentzian fit", lorentzian,
            "Center", "FWHM", "Amp", "Ver. Offset")
        elif index == 1:
            self.mod = FitModel("Gaussian fit", gaussian,
            "Amp", "Center", "Width", "Ver. Offset")
        elif index == 2:
            self.mod = FitModel("Double Gaussian fit", doubleGaussian,
            "Amp 1", "Amp 2", "Center 1", "Center 2", "Width 1", "Width 2", "Ver. Offset")
        elif index == 3:
            self.mod = FitModel("Rabi fit", Rabi,
            "Amp", "phase (deg)", "pi time", "Ver. Offset")
        elif index == 4:
            self.mod = FitModel("cQED fit", ref_int,
            "Delta_ac", "g", "kwg", "k", "Amp", "Ver. Offset")

        self.mod.load_mod(config = self.config)
        self.close()

    def fit_mod(self):
        fit_fwd, fit_bwd, self.p0_fwd,\
            self.p0_bwd, self.fit_suc = self.mod.fit_mod(
                                        self.x_fwd,
                                        self.data_fwd,
                                        self.x_bwd,
                                        self.data_bwd,
                                        self.p0_fwd,
                                        self.p0_bwd)
        return fit_fwd, fit_bwd, self.p0_fwd, self.p0_bwd


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

    def fit_mod(self, x_fwd, data_fwd, x_bwd,
                data_bwd, p0_fwd = None, p0_bwd = None):
        if self.init_params is not None:
            p0 = list()
            for param in self.fit_params:
                p0.append(self.init_params[param])
            if p0_fwd is None or self.p0_updated:
                p0_fwd_f = p0
                p0_bwd_f = p0
                self.p0_updated = False
            else:
                p0_fwd_f = p0_fwd
                p0_bwd_f = p0_bwd
            try:
                popt1, pcov1 = curve_fit(self.func, x_fwd, data_fwd, p0 = p0_fwd_f)
                popt2, pcov2 = curve_fit(self.func, x_bwd, data_bwd, p0 = p0_bwd_f)
                p0_fwd_f = popt1
                p0_bwd_f = popt2
                #print(pcov1)
                fit_suc = True
            except:
                p0_fwd_f = p0
                p0_bwd_f = p0
                popt1 = np.zeros_like(p0)
                popt2 = np.zeros_like(p0)
                fit_suc = False
            for ind, param in enumerate(self.fit_params):
                self.pop.fparams[param].setText(str(popt1[ind]))
                self.pop.fparams2[param].setText(str(popt2[ind]))
            return self.func(x_fwd, *popt1), self.func(x_bwd, *popt2),\
                   p0_fwd_f, p0_bwd_f, fit_suc

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
    lor.load_mod()
    #lor.popup = QMainWindow()
    #lor.init_ui(lor.popup)
    app.exec_()
