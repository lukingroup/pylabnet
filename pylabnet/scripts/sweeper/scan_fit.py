""" Class for fitting popup for scan_1d.py """
from pylabnet.gui.pyqt.external_gui import Popup, InternalPopup
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

class FitPopup(Popup):
    def __init__(self, ui, x_fwd, data_fwd, x_bwd, 
                 data_bwd, p0_fwd, p0_bwd, config, log):
        super().__init__(ui)
        self.log = log
        self.data_fwd = np.array(data_bwd)
        self.x_fwd = np.array(x_fwd)
        self.x_bwd = np.array(x_bwd)
        self.data_bwd = np.array(data_bwd)
        self.p0_fwd = p0_fwd
        self.p0_bwd = p0_bwd
        self.p0_updated = False
        self.fit_suc = True
        self.fit_method = None
        self.config = config

    def load_lor(self):
    
        self.lor_pop = Popup(ui = 'lor_fit_params')

        #the below crashes the program for some reason....
        #self.lor_pop.main.setParent(None)
        #self.model_parameters.addLayout(self.lor_pop.main)
        #self.show()

        self.lor_pop.confirm.clicked.connect(self.set_lor)
    
    def load_cqed(self):
        self.cqed_pop = Popup(ui = 'cqed_fit_params')
        try:
            self.cqed_pop.Delta_ac.setText(str(self.config["cQED params"]["Delta_ac"]))
            self.cqed_pop.g.setText(str(self.config["cQED params"]["g"]))
            self.cqed_pop.k_wg.setText(str(self.config["cQED params"]["k_wg"]))
            self.cqed_pop.k.setText(str(self.config["cQED params"]["k"]))
            self.cqed_pop.confirm.clicked.connect(str(self.set_cqed))
        except:
            pass
        self.cqed_pop.confirm.clicked.connect(self.set_cqed)
    
    def set_lor(self):
        self.lor_params = {"center": float(self.lor_pop.center.text()), \
                            "fwhm": float(self.lor_pop.fwhm.text()), \
                            "amp": float(self.lor_pop.amp.text()), \
                            "offset": float(self.lor_pop.offset.text())}
        self.fit_method = 'fit_lor'
        self.p0_updated = True
        #print(str(self.lor_params["center"]))
    
    def set_cqed(self):
        self.cqed_params = {"Delta_ac": float(self.cqed_pop.Delta_ac.text()), \
                            "g": float(self.cqed_pop.g.text()), \
                            "k_wg": float(self.cqed_pop.k_wg.text()), \
                            "k": float(self.cqed_pop.k.text()), \
                            "amp": float(self.cqed_pop.amp.text()),
                            "offset": float(self.cqed_pop.offset.text())}
                            #"gamma": float(self.cqed_pop.gamma.text()),
        self.fit_method = 'fit_cqed'
        self.p0_updated = True
    
    def fit_lor(self):
        if self.lor_params is not None:
            p0 = [self.lor_params["center"], self.lor_params["fwhm"],\
                 self.lor_params["amp"], self.lor_params["offset"]]
            if self.p0_fwd is None or self.p0_updated:
                p0_fwd = p0
                p0_bwd = p0
                self.p0_updated = False
            else:
                p0_fwd = self.p0_fwd
                p0_bwd = self.p0_bwd
            #print(p0)
            # fit fwd and bwd
            #print(p0_fwd)
            try:
                popt1, pcov1 = curve_fit(lorentzian, self.x_fwd, self.data_fwd, p0 = p0_fwd)
                popt2, pcov2 = curve_fit(lorentzian, self.x_bwd, self.data_bwd, p0 = p0_bwd)
                p0_fwd = popt1
                p0_bwd = popt2
                #print(pcov1)
                self.fit_suc = True
            except:
                p0_fwd = p0
                p0_bwd = p0
                popt1 = np.zeros_like(p0)
                popt2 = np.zeros_like(p0)
                self.fit_suc = False
            # display fit parameters
            self.lor_pop.fit_cen.setText(str(popt1[0]))
            self.lor_pop.fit_fwhm.setText(str(popt1[1]))
            self.lor_pop.fit_amp.setText(str(popt1[2]))
            self.lor_pop.fit_off.setText(str(popt1[3]))
            self.lor_pop.fit_cen_2.setText(str(popt2[0]))
            self.lor_pop.fit_fwhm_2.setText(str(popt2[1]))
            self.lor_pop.fit_amp_2.setText(str(popt2[2]))
            self.lor_pop.fit_off_2.setText(str(popt2[3]))
            return lorentzian(self.x_fwd, *popt1), lorentzian(self.x_bwd, *popt2),\
                   p0_fwd, p0_bwd
        else:
            self.fit_error = Popup(ui = 'fit_error')
            self.fit_error.error.setText('ERROR: You have no initial guesses.')
    
    def fit_cqed(self):
        if self.cqed_params is not None:
            p0 = [self.cqed_params["Delta_ac"], self.cqed_params["g"],
                 self.cqed_params["k_wg"],
                 self.cqed_params["k"], self.cqed_params["amp"],
                 self.cqed_params["offset"]]
                 # self.cqed_params["gamma"],
            if self.p0_fwd is None or self.p0_updated:
                p0_fwd = p0
                p0_bwd = p0
                self.p0_updated = False
            else:
                p0_fwd = self.p0_fwd
                p0_bwd = self.p0_bwd
            #print(p0)
            # fit fwd and bwd
            #print(p0_fwd)
            try:
                popt1, pcov1 = curve_fit(ref_int, self.x_fwd, self.data_fwd, p0 = p0_fwd) #, diff_step = 0.1)
                popt2, pcov2 = curve_fit(ref_int, self.x_bwd, self.data_bwd, p0 = p0_bwd) #, diff_step = 0.1)
                p0_fwd = popt1
                p0_bwd = popt2
                #print(pcov1)
                self.fit_suc = True
            except:
                p0_fwd = p0
                p0_bwd = p0
                popt1 = np.zeros_like(p0)
                popt2 = np.zeros_like(p0)
                self.fit_suc = False
            # display fit parameters
            self.cqed_pop.fit_delta_ac.setText(str(popt1[0]))
            self.cqed_pop.fit_g.setText(str(popt1[1]))
            #self.cqed_pop.fit_gamma.setText(str(popt1[2]))
            self.cqed_pop.fit_k.setText(str(popt1[2]))
            self.cqed_pop.fit_k_wg.setText(str(popt1[3]))
            self.cqed_pop.fit_ampl.setText(str(popt1[4]))
            self.cqed_pop.fit_offs.setText(str(popt1[5]))

            self.cqed_pop.fit_delta_ac_2.setText(str(popt2[0]))
            self.cqed_pop.fit_g_2.setText(str(popt2[1]))
            #self.cqed_pop.fit_gamma_2.setText(str(popt1[2]))
            self.cqed_pop.fit_k_2.setText(str(popt2[2]))
            self.cqed_pop.fit_k_wg_2.setText(str(popt2[3]))
            self.cqed_pop.fit_ampl_2.setText(str(popt2[4]))
            self.cqed_pop.fit_offs_2.setText(str(popt2[5]))

            return ref_int(self.x_fwd, *popt1), ref_int(self.x_bwd, *popt2),\
                   p0_fwd, p0_bwd
        else:
            self.fit_error = Popup(ui = 'fit_error')
            self.fit_error.error.setText('ERROR: You have no initial guesses.')


    def fit_selection(self, index):
        #print(str(index))
        if index == 0:
            self.load_lor()
            self.close()
        elif index == 1:
            self.load_cqed()
            self.close()
    
    def doSomething(self):

        # If you're running in the console (e.g. in the vscode debugger)
        print("something")

        # If you're running thru pylabnet
        self.log.info("something")
    