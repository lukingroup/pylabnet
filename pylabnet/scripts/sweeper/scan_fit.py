""" Class for fitting popup for scan_1d.py """
from pylabnet.gui.pyqt.external_gui import Popup, InternalPopup

class FitPopup(Popup):
    def __init__(self, ui, data, log):
        super().__init__(ui)
        self.log = log
        
    def load_lor(self):
    
        self.lor_pop = Popup(ui = 'lor_fit_params')

        #the below crashes the program for some reason....
        #self.lor_pop.main.setParent(None)
        #self.model_parameters.addLayout(self.lor_pop.main)
        #self.show()

        self.lor_pop.confirm.clicked.connect(self.fit_lor)
    
    def fit_lor(self):
        self.lor_params = {"center": float(self.lor_pop.center.text()), \
                            "fwhm": float(self.lor_pop.fwhm.text()), \
                            "amp": float(self.lor_pop.amp.text())}
        #print(str(self.lor_params["center"]))

    def fit_selection(self, index):
        #print(str(index))
        if index == 0:
            self.load_lor()
            self.close()

    def lorentzian(x, *params):
        """
        :param params: parameters for lorentzian in the order center, width, amp
        """
        cen = params[0]
        wid = params[1]
        amp = params[2]
        return amp*0.5*wid/((x - cen)**2 + (0.5*wid)**2)
    
    def doSomething(self):

        # If you're running in the console (e.g. in the vscode debugger)
        print("something")

        # If you're running thru pylabnet
        self.log.info("something")
    