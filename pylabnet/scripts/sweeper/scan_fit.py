""" Class for fitting popup for scan_1d.py """
from pylabnet.gui.pyqt.external_gui import Popup, InternalPopup

class FitPopup(Popup):
    def __init__(self, ui):
        super().__init__(ui)
        
    def load_lor(self):
        self.lor_pop = InternalPopup(ui = 'lor_fit_params')
        self.model_parameters.addLayout(self.lor_pop.main)
        self.setLayout(model_parameters)
        self.show()
    def doSomething(self):
        print("something")
    
