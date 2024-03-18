import time
from ctypes import byref, c_char_p, c_double, c_int, c_ulong, c_bool, cdll

from pylabnet.utils.logging.logger import LogHandler, LogClient

# Load DLL library
lib = cdll.LoadLibrary("C:\Program Files\IVI Foundation\VISA\Win64\Bin\TLPAX_64.dll")


class Driver():

    def __init__(self, dev_number=0, inst_mode=5, wavelength=1350, scanrate=60, autorange=True, logger=None):

        # Detect and initialize PAX1000 device
        self.instrumentHandle = c_ulong()
        IDQuery = True
        resetDevice = False
        resource = c_char_p(b"")
        deviceCount = c_int()

        self.log = LogHandler(logger=logger)

        # Check how many PAX1000 are connected
        lib.TLPAX_findRsrc(self.instrumentHandle, byref(deviceCount))
        if deviceCount.value < 1:
            self.log.error("No PAX1000 device found.")
        else:
            self.log.info(f"{deviceCount.value} PAX1000 device(s) found.")

        # Connect to the first available PAX1000
        lib.TLPAX_getRsrcName(self.instrumentHandle, dev_number, resource)
        if (0 == lib.TLPAX_init(resource.value, IDQuery, resetDevice, byref(self.instrumentHandle))):
            self.log.info("Connection to first PAX1000 initialized.")
        else:
            self.log.error("Error with initialization.")

        # Short break to make sure the device is correctly initialized
        time.sleep(2)

        # Default setup
        self.set_instrument_mode(inst_mode)
        self.set_wavelength(wavelength)
        self.set_scanrate(scanrate)
        self.set_autorange(autorange)

    def set_instrument_mode(self, modeint):
        lib.TLPAX_setMeasurementMode(self.instrumentHandle, modeint)
        self.log.info(f"Instrument mode set to {modeint}.")

    def get_instrument_mode(self):
        modeint = c_int()
        lib.TLPAX_getMeasurementMode(self.instrumentHandle, byref(modeint))
        return modeint.value

    def set_wavelength(self, wavelength):
        lib.TLPAX_setWavelength(self.instrumentHandle, c_double(wavelength * 1e-9))
        self.log.info(f"Wavelength set to {wavelength} nm.")

    def get_wavelength(self):
        wavelength = c_double()
        lib.TLPAX_getWavelength(self.instrumentHandle, byref(wavelength))
        return wavelength.value

    def set_scanrate(self, scanrate):
        lib.TLPAX_setBasicScanRate(self.instrumentHandle, c_double(scanrate))
        self.log.info(f"Scanrate set to {scanrate}.")

    def get_scanrate(self):
        scanrate = c_double()
        lib.TLPAX_getBasicScanRate(self.instrumentHandle, byref(scanrate))
        return scanrate.value

    def set_autorange(self, autorange):
        autorange_on = c_bool(autorange)
        lib.TLPAX_setPowerAutoRange(self.instrumentHandle, autorange_on)
        self.log.info(f"Power set to autorange.")

    def get_autorange(self):
        autorange_status = c_bool()
        lib.TLPAX_getPowerAutoRange(self.instrumentHandle, byref(autorange_status))
        return autorange_status.value

    def measure_polarization(self):

        scanID = c_int()
        lib.TLPAX_getLatestScan(self.instrumentHandle, byref(scanID))

        azimuth = c_double()
        ellipticity = c_double()

        lib.TLPAX_getPolarization(self.instrumentHandle, scanID.value, byref(azimuth), byref(ellipticity))

        lib.TLPAX_releaseScan(self.instrumentHandle, scanID)
        time.sleep(0.02)

        return azimuth.value, ellipticity.value

    def get_power(self):

        scanID = c_int()
        lib.TLPAX_getLatestScan(self.instrumentHandle, byref(scanID))
        totalpower = c_double()
        polarizedpower = c_double()
        unpolarizedpower = c_double()
        lib.TLPAX_getPower(self.instrumentHandle, scanID.value, byref(totalpower), byref(polarizedpower), byref(unpolarizedpower))
        lib.TLPAX_releaseScan(self.instrumentHandle, scanID)
        time.sleep(0.02)

        return totalpower.value, polarizedpower.value, unpolarizedpower.value


if __name__ == "__main__":

    logger = LogClient(
        host='192.168.50.101',
        port=38967,
        module_tag='Polarimeter'
    )

    pol = Driver(logger=logger)
