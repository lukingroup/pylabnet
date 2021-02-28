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

class FitPopup(Popup):
    def __init__(self, ui, x_fwd, data_fwd, x_bwd, 
                 data_bwd, p0_fwd, p0_bwd, log):
        super().__init__(ui)
        self.log = log
        self.data_fwd = np.array(data_bwd)
        self.x_fwd = np.array(x_fwd)
        self.x_bwd = np.array(x_bwd)
        self.data_bwd = np.array(data_bwd)
        self.p0_fwd = p0_fwd
        self.p0_bwd = p0_bwd

    def load_lor(self):
    
        self.lor_pop = Popup(ui = 'lor_fit_params')

        #the below crashes the program for some reason....
        #self.lor_pop.main.setParent(None)
        #self.model_parameters.addLayout(self.lor_pop.main)
        #self.show()

        self.lor_pop.confirm.clicked.connect(self.set_lor)
    
    def set_lor(self):
        self.lor_params = {"center": float(self.lor_pop.center.text()), \
                            "fwhm": float(self.lor_pop.fwhm.text()), \
                            "amp": float(self.lor_pop.amp.text()), \
                            "offset": float(self.lor_pop.offset.text())}
        self.fit_method = 'fit_lor'
        #print(str(self.lor_params["center"]))
    
    def fit_lor(self):
        if self.lor_params is not None:
            p0 = [self.lor_params["center"], self.lor_params["fwhm"],\
                 self.lor_params["amp"], self.lor_params["offset"]]
            if self.p0_fwd is not None:
                p0_fwd = p0
                p0_bwd = p0
            else:
                p0_fwd = self.p0_fwd
                p0_bwd = self.p0_bwd
            #print(p0)
            # fit fwd and bwd
            try:
                popt1, pcov1 = curve_fit(lorentzian, self.x_fwd, self.data_fwd, p0 = p0_fwd)
                popt2, pcov2 = curve_fit(lorentzian, self.x_bwd, self.data_bwd, p0 = p0_bwd)
                p0_fwd = popt1
                p0_bwd = popt2
            except:
                p0_fwd = p0
                p0_bwd = p0
                popt1 = np.zeros_like(p0)
                popt2 = np.zeros_like(p0)
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

    def fit_selection(self, index):
        #print(str(index))
        if index == 0:
            self.load_lor()
            self.close()
    
    def doSomething(self):

        # If you're running in the console (e.g. in the vscode debugger)
        print("something")

        # If you're running thru pylabnet
        self.log.info("something")
    