""" Class for fitting popup for scan_1d.py """
from pylabnet.gui.pyqt.external_gui import Popup, InternalPopup

class FitPopup(Popup):
    def __init__(self, ui, log):
        super().__init__(ui)
        self.log = log
        
    def load_lor(self):
    
        self.lor_pop = InternalPopup(ui = 'lor_fit_params')
        self.model_parameters.addLayout(self.lor_pop.main)
        
        # This line was wrong, and I don't think it's necessary
        # self.setLayout(model_parameters)
        
        self.show()
    def doSomething(self):

        # If you're running in the console (e.g. in the vscode debugger)
        print("something")

        # If you're running thru pylabnet
        self.log.info("something")
    