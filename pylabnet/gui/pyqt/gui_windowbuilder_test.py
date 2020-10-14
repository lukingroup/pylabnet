import sys
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QMainWindow, QLabel, QGridLayout, QWidget
#from PyQt5.QtCore import QSize
from pylabnet.utils.helper_methods import load_config   

class GUIWindowFromConfig(QMainWindow):

    
    def __init__(self, config=None):
        
        QMainWindow.__init__(self)
        
        self.config = load_config(config)
        self.N_staticlines = len(self.config)
        self.widgets = dict()
        self.setStyleSheet("background-color: black;")

        #self.setMinimumSize(QSize(640, 480))    
        self.setWindowTitle("Staticline window") 

        self.centralWidget = QWidget(self)          
        self.setCentralWidget(self.centralWidget)   

        self.gridLayout = QGridLayout(self)     
        self.centralWidget.setLayout(self.gridLayout)  

        self.unpack_config_file()

    def unpack_config_file(self):
        row_num  = 0

        for device in self.config.values():

            device_name = device["name"]

            # Label for the device name
            label = QtWidgets.QLabel(device_name, self)
            label.setStyleSheet("color: white;")
            self.gridLayout.addWidget(label, row_num, 0)

            self.widgets[device_name] = dict()

            # TODO: Check that staticline_types and staticline_names have same lengths
            # Iterate over all staticlines for the current device
            for staticline_idx, staticline_name in enumerate(device["staticline_names"]):

                staticline_type = device["staticline_configs"][staticline_idx]["type"]
                
                # Label for the staticline name
                label = QtWidgets.QLabel(staticline_name, self)
                label.setStyleSheet("color: white;")
                self.gridLayout.addWidget(label, row_num, 1)

                self.widgets[device_name][staticline_name] = dict()

                # Create the appropriate buttons for that device
                if staticline_type == "digital":
                    self.make_digital_row(position=row_num, device_name=device_name, staticline_name=staticline_name)
                elif staticline_type == "analog":
                    self.make_analog_row(position=row_num, device_name=device_name, staticline_name=staticline_name)
                else:
                    continue # TODO: Print error message?
            
                row_num += 1

    def make_digital_row(self, position=0, device_name='', staticline_name=''):
        on_button = QtWidgets.QPushButton('I', self)
        on_button.setStyleSheet("color: white;  background-color: #17F02E")
        on_button.setFont(QtGui.QFont("Arial", weight=QtGui.QFont.Bold))
        self.widgets[device_name][staticline_name]["on"] = on_button
        self.gridLayout.addWidget(on_button, position, 3)

        off_button = QtWidgets.QPushButton('O', self)
        off_button.setStyleSheet("color: white;  background-color: #A4A4A4")
        off_button.setFont(QtGui.QFont("Arial", weight=QtGui.QFont.Bold))
        self.widgets[device_name][staticline_name]["off"] = off_button
        self.gridLayout.addWidget(off_button, position, 4)

    def make_analog_row(self, position=0, device_name='', staticline_name=''):
        ain_field = QtWidgets.QLineEdit('0.000', self)
        ain_field.setStyleSheet("color:  white;  background-color: black")
        self.widgets[device_name][staticline_name]["AIN"] = ain_field
        self.gridLayout.addWidget(ain_field, position, 2)

        apply_button = QtWidgets.QPushButton('Apply', self)
        apply_button.setStyleSheet("color: white;  background-color: #2A6BFF")
        self.widgets[device_name][staticline_name]["apply"] = apply_button
        self.gridLayout.addWidget(apply_button, position, 3)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainWin = GUIWindowFromConfig(config='test_config_sl')
    mainWin.show()
    sys.exit( app.exec_() )
