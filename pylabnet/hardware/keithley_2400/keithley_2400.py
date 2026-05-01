from pyvisa import VisaIOError, ResourceManager
from pylabnet.utils.logging.logger import LogHandler


class Driver:
    """ Keithley 2400 SourceMeter.
    """

    def __init__(self, gpib_address, logger=None, reset_on_init=False, timeout_ms=10000):
        self.log = LogHandler(logger=logger)
        self.rm = ResourceManager()

        try:
            self.device = self.rm.open_resource(gpib_address)
            self.device.timeout = timeout_ms
            self.device.write_termination = "\n"
            self.device.read_termination = "\n"
            self.device_id = self.device.query("*IDN?").strip()
            self.log.info(f"Successfully connected to {self.device_id}.")

            if reset_on_init:
                self.reset()
            else:
                self.clear_status()

        except VisaIOError as err:
            self.log.error(f"Connection to {gpib_address} failed: {err}")
            raise

    def reset(self):
        """Reset to GPIB defaults and clear status."""
        self.device.write("*RST")
        self.clear_status()
        self.log.info("Keithley 2400 reset to factory GPIB defaults.")

    def clear_status(self):
        """Clear status and error queues."""
        self.device.write("*CLS")

    def close(self):
        """Close VISA connection."""
        try:
            self.output_off()
        except Exception:
            pass
        self.device.close()
        self.rm.close()

    def identify(self):
        """Return instrument identification string."""
        return self.device.query("*IDN?").strip()

    def get_error(self):
        """Return next instrument error from error queue."""
        return self.device.query(":SYST:ERR?").strip()

    def output_on(self):
        """Turn source output on."""
        self.device.write(":OUTP ON")
        self.log.info(f"Output of {self.device_id} turned on.")

    def output_off(self):
        """Turn source output off."""
        self.device.write(":OUTP OFF")
        self.log.info(f"Output of {self.device_id} turned off.")

    def is_output_on(self):
        """Return True if output is enabled."""
        return bool(int(self.device.query(":OUTP?")))

    def wait_complete(self):
        """Wait until all pending commands are complete."""
        return bool(int(self.device.query("*OPC?")))

    def set_voltage_source(self):
        """Configure fixed voltage source mode."""
        self.device.write(":SOUR:FUNC VOLT")
        self.device.write(":SOUR:VOLT:MODE FIXED")
        self.log.info("Keithley 2400 set to voltage source mode.")

    def set_current_source(self):
        """Configure fixed current source mode."""
        self.device.write(":SOUR:FUNC CURR")
        self.device.write(":SOUR:CURR:MODE FIX")
        self.log.info("Keithley 2400 set to current source mode.")

    def get_source_function(self):
        """Return source function, usually VOLT or CURR."""
        return self.device.query(":SOUR:FUNC?").strip()

    def set_voltage(self, voltage):
        """Set source voltage in volts."""
        voltage_range = 2
        if voltage > voltage_range: voltage_range = 20
        if voltage > voltage_range: voltage_range = 200

        self.device.write(f":SOUR:VOLT:RANG {voltage_range}")
        self.device.write(f":SOUR:VOLT:LEV {voltage}")
        self.log.info(f"Keithley 2400 voltage set to {voltage} V.")

    def get_voltage(self):
        """Return programmed source voltage in volts."""
        return float(self.device.query(":SOUR:VOLT:LEV?"))

    def set_current(self, current):
        """Set source current in amps."""
        self.device.write(f":SOUR:CURR:LEV {current}")
        self.log.info(f"Keithley 2400 current set to {current} A.")

    def get_current(self):
        """Return programmed source current in amps."""
        return float(self.device.query(":SOUR:CURR:LEV?"))

    def set_current_compliance(self, current):
        """Set current compliance in amps. Use when sourcing voltage."""
        self.device.write(f":SENS:CURR:PROT {current}")
        self.log.info(f"Keithley 2400 current compliance set to {current} A.")

    def get_current_compliance(self):
        """Return current compliance in amps."""
        return float(self.device.query(":SENS:CURR:PROT?"))

    def set_voltage_compliance(self, voltage):
        """Set voltage compliance in volts. Use when sourcing current."""
        self.device.write(f":SENS:VOLT:PROT {voltage}")
        self.log.info(f"Keithley 2400 voltage compliance set to {voltage} V.")

    def get_voltage_compliance(self):
        """Return voltage compliance in volts."""
        return float(self.device.query(":SENS:VOLT:PROT?"))

    def is_in_current_compliance(self):
        """Return True if current compliance is tripped."""
        return bool(int(self.device.query(":SENS:CURR:PROT:TRIP?")))

    def is_in_voltage_compliance(self):
        """Return True if voltage compliance is tripped."""
        return bool(int(self.device.query(":SENS:VOLT:PROT:TRIP?")))

    def is_in_compliance(self):
        """Return True if source-mode compliance is tripped."""
        source = self.get_source_function().upper()
        if "VOLT" in source:
            return self.is_in_current_compliance()
        if "CURR" in source:
            return self.is_in_voltage_compliance()
        return False

    def set_4wire_sense(self, state):
        """Enable or disable 4-wire remote sense."""
        self.device.write(f":SYST:RSEN {'ON' if state else 'OFF'}")
        self.log.info(f"Keithley 2400 4-wire sense set to {state}.")

    def get_4wire_sense(self):
        """Return True if 4-wire remote sense is enabled."""
        return bool(int(self.device.query(":SYST:RSEN?")))

    def set_measure_current(self):
        """Select current measurement function with autorange."""
        self.device.write(':SENS:FUNC "CURR"')
        self.device.write(":SENS:CURR:RANG:AUTO ON")

    def set_measure_voltage(self):
        """Select voltage measurement function with autorange."""
        self.device.write(':SENS:FUNC "VOLT"')
        self.device.write(":SENS:VOLT:RANG:AUTO ON")

    def read_current(self):
        """Take one current reading in amps."""
        self.device.write(':SENS:FUNC "CURR"')
        self.device.write(":SENS:CURR:RANG:AUTO ON")
        self.device.write(":FORM:ELEM CURR")
        return float(self.device.query(":READ?"))

    def read_voltage(self):
        """Take one voltage reading in volts."""
        self.device.write(':SENS:FUNC "VOLT"')
        self.device.write(":SENS:VOLT:RANG:AUTO ON")
        self.device.write(":FORM:ELEM VOLT")
        return float(self.device.query(":READ?"))

    def read_voltage_current(self):
        """Take one reading and return {'voltage': V, 'current': A}."""
        self.device.write(":FORM:ELEM VOLT,CURR")
        voltage, current = self.device.query(":READ?").strip().split(",")[:2]
        return {"voltage": float(voltage), "current": float(current)}