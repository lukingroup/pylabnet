import sys
from PyQt5 import QtCore, QtWidgets, QtGui
import qdarkstyle
from PyQt5.QtWidgets import QMainWindow, QLabel, QGridLayout, QWidget
from pylabnet.utils.helper_methods import load_config

class GUIWindowFromConfig(QMainWindow):

	def __init__(self, config=None):

		QMainWindow.__init__(self)

		self.config = load_config(config)
		self.N_staticlines = len(self.config)
		self.widgets = dict()
		self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

		#self.setMinimumSize(QSize(640, 480))
		self.setWindowTitle("Staticline window")

		self.centralWidget = QWidget(self)
		self.setCentralWidget(self.centralWidget)

		self.gridLayout = QGridLayout(self)
		self.centralWidget.setLayout(self.gridLayout)

		self.blockgridLayout = []

		self.unpack_config_file()

	def unpack_config_file(self):
		block_num  = 0

		for device_name, device in self.config.items():

			# Ignore non-device configs
			if type(device) != dict:
				continue

			# Label for the device name
			label = QtWidgets.QLabel("  " + device_name + "  ", self)
			label.setStyleSheet("color: white; background-color: #32414B; border-radius: 4px;")
			#label.setStyleSheet("border: 0.5px solid white; ")
			self.gridLayout.addWidget(label, block_num, 0)

			self.blockgridLayout.append(QGridLayout(self))
			self.gridLayout.addLayout(self.blockgridLayout[block_num], block_num, 1)

			self.widgets[device_name] = dict()

			row_num = 0

			# TODO: Check that staticline_types and staticline_names have same lengths
			# Iterate over all staticlines for the current device
			for staticline_idx, staticline_name in enumerate(device["staticline_names"]):

				staticline_type = device["staticline_configs"][staticline_idx]["type"]

				# Label for the staticline name
				label = QtWidgets.QLabel(staticline_name, self)
				label.setStyleSheet("color: white;")
				self.blockgridLayout[block_num].addWidget(label, row_num, 0)


				# Create the appropriate buttons for that device
				if staticline_type == "digital":
					self.widgets[device_name][staticline_name] = dict()
					self.make_digital_row(position=[block_num, row_num], device_name=device_name, staticline_name=staticline_name)
				elif staticline_type == "analog":
					self.widgets[device_name][staticline_name] = dict()
					self.make_analog_row(position=[block_num, row_num], device_name=device_name, staticline_name=staticline_name)
				elif staticline_type == "adjustable_digital":
					self.widgets[device_name][staticline_name + "_analog"] = dict()
					self.widgets[device_name][staticline_name + "_digital"] = dict()
					self.make_adjustable_digital_row(position=[block_num, row_num], device_name=device_name, staticline_name=staticline_name)
					row_num += 1 # Advance by 1 here so that overall it will advance by 2
				else:
					continue # TODO: Print error message?

				row_num += 1

			block_num +=1

	def make_digital_row(self, position=[0,0], device_name='', staticline_name=''):
		on_button = QtWidgets.QPushButton('I', self)
		on_button.setStyleSheet("color: black;  background-color: #C1C1C1")
		on_button.setFont(QtGui.QFont("Arial", weight=QtGui.QFont.Bold))
		self.widgets[device_name][staticline_name]["on"] = on_button
		self.blockgridLayout[position[0]].addWidget(on_button, position[1], 2)

		off_button = QtWidgets.QPushButton('O', self)
		off_button.setStyleSheet("color: white;  background-color: #FF4040")
		off_button.setFont(QtGui.QFont("Arial", weight=QtGui.QFont.Bold))
		self.widgets[device_name][staticline_name]["off"] = off_button
		self.blockgridLayout[position[0]].addWidget(off_button, position[1], 3)

		# enable/disable buttons depending on which one has last been clicked
		self.widgets[device_name][staticline_name]["on"].clicked.connect(lambda:
			self.enable_buttons(device_name=device_name, staticline_name=staticline_name, mode=True))
		self.widgets[device_name][staticline_name]["off"].clicked.connect(lambda:
			self.enable_buttons(device_name=device_name, staticline_name=staticline_name, mode=False))

		# Initially set the off button as disabled (since initially the staticline is off)
		self.widgets[device_name][staticline_name]["off"].setEnabled(False)

	def make_analog_row(self, position=[0,0], device_name='', staticline_name=''):
		ain_field = QtWidgets.QLineEdit('0.000', self)
		ain_field.setStyleSheet("color:  white;  background-color: black")
		self.widgets[device_name][staticline_name]["AIN"] = ain_field
		self.blockgridLayout[position[0]].addWidget(ain_field, position[1], 1)

		apply_button = QtWidgets.QPushButton('Apply', self)
		apply_button.setStyleSheet("color: black;  background-color: #AAD3E9")
		self.widgets[device_name][staticline_name]["apply"] = apply_button
		self.blockgridLayout[position[0]].addWidget(apply_button, position[1], 2)

		label = QtWidgets.QLabel("Current value: 0.00", self)
		label.setStyleSheet("color: white;")
		label.setMinimumSize(QtCore.QSize(200,0))
		self.widgets[device_name][staticline_name]["current_val"] = label
		self.blockgridLayout[position[0]].addWidget(label, position[1], 4)

		self.widgets[device_name][staticline_name]["apply"].clicked.connect(lambda:
			self.upd_cur_val(device_name=device_name, staticline_name=staticline_name))

	def make_adjustable_digital_row(self, position=[0,0], device_name='', staticline_name=''):
		block_num, row_num = position
		self.make_analog_row([block_num, row_num], device_name, staticline_name + "_analog")
		self.make_digital_row([block_num, row_num+1], device_name, staticline_name + "_digital")

	def enable_buttons(self, device_name='', staticline_name='', mode=True):
		self.widgets[device_name][staticline_name]["off"].setEnabled(mode)
		self.widgets[device_name][staticline_name]["on"].setEnabled(not mode)

		if mode:
			self.widgets[device_name][staticline_name]["on"].setStyleSheet(
				"color: white;  background-color: #3CD070")
			self.widgets[device_name][staticline_name]["off"].setStyleSheet(
				"color: black;  background-color: #C1C1C1")

		else:
			self.widgets[device_name][staticline_name]["on"].setStyleSheet(
				"color: black;  background-color: #C1C1C1")
			self.widgets[device_name][staticline_name]["off"].setStyleSheet(
				"color: white;  background-color: #FF4040")


	def upd_cur_val(self, device_name='', staticline_name=''):
		self.widgets[device_name][staticline_name]["current_val"].setText(
			"Current value: " + self.widgets[device_name][staticline_name]["AIN"].text()
		)

if __name__ == "__main__":
	app = QtWidgets.QApplication(sys.argv)
	mainWin = GUIWindowFromConfig(config='test_config_sl')
	mainWin.show()
	sys.exit( app.exec_() )
