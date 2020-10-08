import sys
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtWidgets import QMainWindow, QLabel, QGridLayout, QWidget
#from PyQt5.QtCore import QSize
from pylabnet.utils.helper_methods import load_config   

class GUIWindowFromConfig(QMainWindow):

    
    def __init__(self, config=None):
        
        QMainWindow.__init__(self)
        
        self.config = load_config(config)
        self.N_staticlines = len(self.config) #N_staticlines

        self.labels = []

        self.all_widgets = dict()

        self.setStyleSheet("background-color: black;")

        #self.setMinimumSize(QSize(640, 480))    
        self.setWindowTitle("Staticline window") 

        self.centralWidget = QWidget(self)          
        self.setCentralWidget(self.centralWidget)   

        self.gridLayout = QGridLayout(self)     
        self.centralWidget.setLayout(self.gridLayout)  

        self.unpack_config_file()

    def unpack_config_file(self):
        for ii in range(self.N_staticlines):

            device_name = self.config["{}".format(ii+1)]["name"]

            self.labels.append(QtWidgets.QLabel(device_name, self))
            self.labels[ii].setStyleSheet("color: white;")
            self.gridLayout.addWidget(self.labels[ii], ii, 0)

            self.all_widgets[device_name] = dict()

            if self.config["{}".format(ii+1)]["type"] == "digital":
                self.make_digital_row(position=ii, device_name=device_name)
            if self.config["{}".format(ii+1)]["type"] == "analog":
                self.make_analog_row(position=ii, device_name=device_name)

    def make_digital_row(self, position=0, device_name=''):
        self.all_widgets[device_name]["on"] = QtWidgets.QPushButton('I', self)
        self.all_widgets[device_name]["on"].setStyleSheet("color: white;  background-color: #17F02E")
        self.all_widgets[device_name]["on"].setFont(QtGui.QFont("Arial", weight=QtGui.QFont.Bold))
        self.gridLayout.addWidget(self.all_widgets[device_name]["on"], position, 2)
        self.all_widgets[device_name]["off"] = QtWidgets.QPushButton('O', self)
        self.all_widgets[device_name]["off"].setStyleSheet("color: white;  background-color: #A4A4A4")
        self.all_widgets[device_name]["off"].setFont(QtGui.QFont("Arial", weight=QtGui.QFont.Bold))
        self.gridLayout.addWidget(self.all_widgets[device_name]["off"], position, 3)

    def make_analog_row(self, position=0, device_name=''):
        self.all_widgets[device_name]["AIN"] = QtWidgets.QLineEdit('0.000', self)
        self.all_widgets[device_name]["AIN"].setStyleSheet("color:  white;  background-color: black")
        self.gridLayout.addWidget(self.all_widgets[device_name]["AIN"], position, 1)
        self.all_widgets[device_name]["apply"] = QtWidgets.QPushButton('Apply', self)
        self.all_widgets[device_name]["apply"].setStyleSheet("color: white;  background-color: #2A6BFF")
        self.gridLayout.addWidget(self.all_widgets[device_name]["apply"], position, 2)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    mainWin = GUIWindowFromConfig(config='test_config_sl')
    mainWin.show()
    sys.exit( app.exec_() )