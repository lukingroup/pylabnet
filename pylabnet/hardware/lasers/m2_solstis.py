
# -*- coding: utf-8 -*-
"""
This module controls an M squared laser
Originally taken from:
https://github.com/AlexShkarin/pyLabLib/blob/master/pylablib/aux_libs/devices/M2.py
Modifications by Graham Joe, M. Chalupnik
"""

from pylabnet.utils.logging.logger import LogHandler
import time
import socket
import json
import websocket

BUFFERSIZE = 2048
MIN_WAVELENGTH = 650
MAX_WAVELENGTH = 1100


class Driver():

    def __init__(self, ip, port1, port2, timeout=5, logger=None):

        self.buffersize = BUFFERSIZE
        self._timeout = timeout
        self.address1 = (ip, port1)
        self.address2 = (ip, port2)
        self.transmission_id = 1
        self._last_status = {}
        self.connect_laser()

        self.log = logger

    def connect_laser(self):
        """ Connect to Instrument.
        @return bool: connection success
        """
        self.socket = socket.create_connection(self.address1, timeout=self._timeout)
        self.update_socket = socket.create_connection(self.address2, timeout=self._timeout)
        interface = self.socket.getsockname()[0]
        _, reply = self.send('start_link', {'ip_address': interface})
        _, reply2 = self.send('start_link', {'ip_address': interface}, socket=2)
        if reply['status'] == 'ok' and reply2['status'] == 'ok':
            pass
        else:
            raise Exception('Laser connection failed')

    def disconnect_laser(self):
        """ Close the connection to the instrument.
        """
        self.socket.close()
        self.update_socket.close()

    def ping_laser(self):
        """ Checks if the laser is connected.
        """
        _, reply = self.send('ping', {'text_in': 'check'})
        _, reply2 = self.send('ping', {'text_in': 'check'}, socket=2)
        return True

    def set_timeout(self, timeout):
        """ Sets the timeout in seconds for connecting or sending/receiving
        :param timeout: timeout in seconds
        """
        self._timeout = timeout
        self.socket.settimeout(timeout)

    def connect_wavemeter(self, timeout=None):
        """ Connect to the wavemeter via websocket
        :param timeout: time before operation quits
        """
        if self.is_wavemeter_connected():
            return
        self._send_websocket_request('{"message_type":"task_request","task":["start_wavemeter_link"]}')
        start_time = time.time()
        while not self.is_wavemeter_connected():
            time.sleep(0.02)
            try:
                if time.time() > start_time + timeout:
                    raise Exception('Wavemeter connection failed')
            except TypeError:
                pass

    def disconnect_wavemeter(self, timeout=None):
        """ Disconnect the wavemeter websocket, if sync==True wait until the connection is established
        :param timeout: time before operation quits
        """
        if not self.is_wavemeter_connected():
            return
        self._send_websocket_request('{"message_type":"task_request","task":["job_stop_wavemeter_link"]}')
        start_time = time.time()
        while self.is_wavemeter_connected():
            time.sleep(0.02)
            try:
                if time.time() > start_time + timeout:
                    self.log.error('Wavemeter disconnect failed')
                    return
            except TypeError:
                pass

    def is_wavemeter_connected(self):
        """ Checks if the wavemeter is connected via websocket
        :return bool: wavemeter connected via websocket
        """
        return bool(self._read_websocket_status(present_key="wlm_fitted")["wlm_fitted"])

    def send(self, op, parameters, transmission_id=None, report=False, socket=1):
        """ Send json message to laser
        :param op: operation to be performed
        :param parameters: dictionary of parameters associated with op
        :param transmission_id: optional transmission id integer
        :param report: request completion report (doesn't apply to all operations)
        :return: reply operation dictionary, reply parameters dictionary
        """
        if report:
            parameters["report"] = "finished"
            self._last_status[op] = {}
        message = self._build_message(op, parameters, transmission_id)
        if socket == 1:
            self.flush()
            self.socket.sendall(message.encode('utf-8'))
            reply = self.socket.recv(self.buffersize)
        elif socket == 2:
            self.update_socket.sendall(message.encode('utf-8'))
            reply = self.update_socket.recv(self.buffersize)
        op_replies, parameters_replies = self._parse_reply(reply)
        for op_reply, parameters_reply in zip(op_replies, parameters_replies):
            self._last_status[self._parse_report_op(op_reply)] = parameters_reply
        return op_replies[-1], parameters_replies[-1]

    def check_report(self, op):
        """Check and return the success latest report for the given operation
        :param op: operation to be performed
        return bool: 'success' if operation completed, 'fail' if operation failed and None if still in progress
        """
        self._update_reports()
        return self._get_last_report(op)

    def set(self, setting, value, key_name='setting'):
        """ Sets a laser parameter
        :param setting: string containing the setting to be set
        :param value: value of the setting
        :param key_name: optional keyword
        """
        parameters = {key_name: value}
        if key_name == 'setting':
            parameters[key_name] = [parameters[key_name]]
        _, parameters_reply = self.send(setting, parameters)
        if parameters_reply['status'] == 'ok':
            self.log.debug(parameters_reply)
        else:
            self.log.warn(parameters_reply)

    def get(self, setting):
        """ Gets a laser parameter
        :param setting: string containing the setting
        :return: instrument reply
        """
        _, parameters_reply = self.send(setting, {})
        if parameters_reply['status'] == 'ok':
            self.log.debug(parameters_reply)
        else:
            self.log.warn(parameters_reply)

    def flush(self, bits=100000, timeout=0):
        """ Flush read buffer, may cause socket timeout if used when laser isn't scanning
        """
        timeout = max(timeout, 0.001)
        self.socket.settimeout(timeout)
        try:
            return self.socket.recv(bits)
        except:
            pass
        self.socket.settimeout(self._timeout)

    tune_wavelength_commands = {"tune_wavelength": "set_wave_m", "tune_wavelength_table": "move_wave_t"}
    get_wavelength_tuning_status_commands = {"tune_wavelength": "poll_wave_m", "tune_wavelength_table": "poll_wave_t"}
    stop_tuning_wavelength_commands = {"tune_wavelength": "stop_wave_m", "tune_wavelength_table": "stop_move_wave_t"}
    tuning_wavelength_errors = {"tune_wavelength": ["tune wavelength successful",
                                                    "can't tune wavelength: no wavemeter link",
                                                    "can't tune wavelength: wavelength is out of range",
                                                    "Not sure what this error is"],
                                "tune_wavelength_table": ["tuning wavelength successful"
                                                          "can't tune wavelength: command failed",
                                                          "can't tune wavelength: wavelength is out of range"]}

    wavelength_tuning_states = {"tune_wavelength": ["idle",
                                                    "no wavemeter link",
                                                    "tuning wavelength",
                                                    "wavemeter locked"],
                                "tune_wavelength_table": ["tuning wavelength completed",
                                                          "tuning wavelength in progress",
                                                          "wavelength tuning operation failed"]}

    def tune_wavelength(self, tune_wavelength_type, wavelength, report=False):
        """
        Tune the wavelength. Only works if the wavemeter is connected.
        :param tune_wavelength_type: "tune_wavelength" if wavemeter is connected, "tune_wavelength_table" if not
        :param wavelength: wavelength (nm) to be tuned to
        :param report: request completion report
        """
        _, parameters_reply = self.send(self.tune_wavelength_commands[tune_wavelength_type],
                                        {"wavelength": [wavelength]}, report=report)
        reply_status = parameters_reply["status"][0]
        if reply_status != 0:
            self.log.warn(self.tuning_wavelength_errors[tune_wavelength_type][reply_status])

    def check_wavelength_tuning_report(self, tune_wavelength_type):
        """Checks for a wavelength tuning report
        :param tune_wavelength_type: "tune_wavelength" if wavemeter is connected, "tune_wavelength_table" if not
        return bool: 'success' if tuning completed, 'fail' if tuning failed and None if still in progress
        """
        return self.check_report(self.tune_wavelength_commands[tune_wavelength_type])

    def stop_tuning_wavelength(self, tune_wavelength_type):
        """Stop wavelength tuning
        :param tune_wavelength_type: "tune_wavelength" if wavemeter is connected, "tune_wavelength_table" if not
        """
        _, parameters_reply = self.send(self.stop_tuning_wavelength_commands[tune_wavelength_type], {})
        if parameters_reply["status"][0] == 1:
            self.log.warn("can't stop tuning: no wavemeter link")

    def get_full_tuning_status(self, tune_wavelength_type):
        """ Gets the current wavelength, lock_status, and extended zone of the laser
        :param tune_wavelength_type: "tune_wavelength" if wavemeter is connected, "tune_wavelength_table" if not
        :return dict: {"status": 0, 1, 2, or 3 (see wavelength_tuning_states above)
                       "current_wavelength": float,
                       "lock_status": 0 (wavelength lock is OFF) or 1 (wavelength lock is ON)
                       "extended_zone": 0 (current wavelength is not in an extended zone)
                                        1 (current wavelength is in an extended zone)
        """
        _, parameters_reply = self.send(self.get_wavelength_tuning_status_commands[tune_wavelength_type], {}, socket=2)
        return parameters_reply

    def get_wavelength(self, tune_wavelength_type):
        """Get wavelength
        :param tune_wavelength_type: "tune_wavelength" if wavemeter is connected, "tune_wavelength_table" if not
        :return float: current wavelength
        """
        return self.get_full_tuning_status(tune_wavelength_type)["current_wavelength"][0]

    tuning_commands = {"tune_etalon": "tune_etalon",
                       "tune_reference_cavity": "tune_cavity",
                       "fine_tune_reference_cavity": "fine_tune_cavity",
                       "tune_resonator": "tune_resonator",
                       "fine_tune_resonator": "fine_tune_resonator"}
    tuning_states = ["tuning operation completed", "tuning setting out of range", "tuning command failed"]

    def tune(self, tune_type, percent, report=False):
        """Tune the etalon to percent. Only works if the wavemeter is disconnected.
        :param tune_type: see tuning commands above
        :param percent: percent to tune etalon to
        :param report: request completion report
        """
        _, parameters_reply = self.send(self.tuning_commands[tune_type], {"setting": [percent]}, report=report)
        reply_status = parameters_reply["status"][0]
        if reply_status != 0:
            self.log.warn(self.tuning_states[reply_status])

    def check_tuning_report(self, tune_type):
        """Checks for a wavelength tuning report
        :param tune_type: see tuning commands above
        return bool: 'success' if tuning completed, 'fail' if tuning failed and None if still in progress
        """
        return self.check_report(self.tuning_commands[tune_type])

    lock_commands = {"lock_wavemeter": "lock_wave_m",
                     "lock_etalon": "etalon_lock",
                     "lock_reference_cavity": "cavity_lock",
                     "lock_ecd": "ecd_lock"}

    def lock(self, lock_type, operation="on"):
        """Causes SolsTiS to monitor the wavelength and automatically readjust the tuning to the currently set target
        :param lock_type: see lock commands above
        :param operation: "on" or "off
        """
        _, parameters_reply = self.send(self.lock_commands[lock_type], {"operation": operation})
        if parameters_reply['status'] != 0:
            self.log.warn("no link to wavemeter")

    terascan_rates = [50E3, 100E3, 200E3, 500E3, 1E6, 2E6, 5E6, 10E6, 20E6, 50E6, 100E6, 200E6, 500E6, 1E9, 2E9, 5E9,
                      10E9, 15E9, 20E9, 50E9, 100E9]
    terascan_setup_states = ["scan setup completed", "start out of range", "stop out of range", "rate out of range",
                             "TeraScan not available"]

    def setup_terascan(self, scan_type, scan_range, scan_rate, trunc_rate=True):
        """Setup terascan.
        :param scan_type: scan type
            'medium': BRF+etalon, rate from 100 GHz/s to 1 GHz/s
            'fine': All elements, rate from 20 GHz/s to 1 MHz/s
            'line': All elements, rate from 20 GHz/s to 50 kHz/s).
        :param scan_range: (start,stop) in nm
        :param rate: scan rate in Hz/s
        :param trunc_rate: Truncate rate
            True: Truncate the scan rate to the nearest available rate
            False: Incorrect rate would raise an error.
        """
        self._check_terascan_type(scan_type)
        if trunc_rate:
            scan_rate = self._trunc_terascan_rate(scan_rate)
        if scan_rate >= 1E9:
            fact, units = 1E9, "GHz/s"
        elif scan_rate >= 1E6:
            fact, units = 1E6, "MHz/s"
        else:
            fact, units = 1E3, "kHz/s"
        parameters = {"scan": scan_type, "start": [scan_range[0]], "stop": [scan_range[1]],
                      "rate": [scan_rate / fact], "units": units}
        _, parameters_reply = self.send("scan_stitch_initialise", parameters)
        if not parameters_reply.get("status"):
            self.log.warn("can't setup TeraScan: status not in reply")
        else:
            reply_status = parameters_reply["status"][0]
            if reply_status != 0:
                self.log.warn(self.terascan_setup_states[reply_status])

    terascan_update_states = ["TeraScan set up: operation successful",
                              "can't setup TeraScan updates: operation failed",
                              "can't setup TeraScan updates: incorrect update rate",
                              "can't setup TeraScan: TeraScan not available"]

    def enable_terascan_updates(self, enable=True, update_period=0):
        """Enable sending periodic terascan updates. Laser will send updates in the beginning and in the end of every
        terascan segment.
        :param enable: Enable terascan updates
        :param update_period: Does nothing (outdated parameter here to prevent ancient code from breaking)
        """
        _, parameters_reply = self.send("scan_stitch_output",
                                        {"operation": ("start" if enable else "stop"), "update": [update_period]})
        #reply_status = parameters_reply["status"][0]
        #if reply_status != 0:
        #    self.log.warning(self.terascan_update_states[reply_status])
        self._last_status[self._terascan_update_op] = {}

    advanced_terascan_update_states = ["TeraScan set up: operation completed",
                                       "can't setup TeraScan updates: operation failed",
                                       "can't setup TeraScan: delay period out of range",
                                       "can't setup TeraScan updates: update step out of range",
                                       "can't setup TeraScan: TeraScan not available"]

    #TODO: Test This function
    def enable_advanced_terascan_update(self, enable=True, delay_period=0, update_frequency=1, pause=False):
        """Enable sending periodic terascan updates. Laser will send updates in the beginning and in the end of every
        terascan segment.
        :param enable: Enable terascan updates
        :param delay_period: Scan delay after start transmission in 1/100s (range is 0 - 1000)
        :param update_frequency: Sends updates every update_period percents of the segment
        """
        _, parameters_reply = self.send("terascan_output",
                                        {"operation": ("start" if enable else "stop"), "delay": [delay_period],
                                         "update": update_frequency, "pause": pause})
        reply_status = parameters_reply["status"][0]
        if reply_status != 0:
            self.log.warning(advanced_terascan_update_states[reply_status])
        self._last_status[self._terascan_update_op] = {}

    terascan_op_states = ["TeraScan Started",
                          "can't start TeraScan: operation failed",
                          "can't start TeraScan: TeraScan not available"]

    def start_terascan(self, scan_type, report=False):
        """Start terascan.
        :param scan_type: scan type
            'medium': BRF + etalon, rate from 100 GHz/s to 1 GHz/s
            'fine': All elements, rate from 20 GHz/s to 1 MHz/s
            'line': All elements, rate from 20 GHz/s to 50 kHz/s
        :param report: request completion report
        """
        self._check_terascan_type(scan_type)
        _, parameters_reply = self.send("scan_stitch_op", {"scan": scan_type, "operation": "start"}, report=report)
        reply_status = parameters_reply["status"][0]
        if reply_status != 0:
            self.log.warn(self.start_terascan_op_states[reply_status])

    def stop_terascan(self, scan_type):
        """Stop terascan of the given type.
        :param scan_type: Scan type
            'medium': BRF+etalon, rate from 100 GHz/s to 1 GHz/s
            'fine': All elements, rate from 20 GHz/s to 1 MHz/s
            'line': All elements, rate from 20 GHz/s to 50 kHz/s
        """
        self._check_terascan_type(scan_type)
        self._send_websocket_request('{"stop_scan_stitching":1,"message_type":"page_update"}')
        self._send_websocket_request(
            '{"message_type":"task_request","task":["medium_scan_stop"]}')

    _terascan_update_op = "wavelength"
    scan_states = ["not active", "in progress", "TeraScan not available"]

    def get_terascan_update(self):
        """Check the latest terascan update.
        :return: Terascan report {'wavelength': current_wavelength, 'operation': op}
        where op is:
            'scanning': scanning in progress
            'stitching': stitching in progress
            'finished': scan is finished
            'repeat': segment is repeated
        """
        self._update_reports()
        report = self._last_status.get(self._terascan_update_op, {})
        self._last_status[self._terascan_update_op] = {}
        return report

    def check_terascan_report(self):
        """Check report on terascan start.
        :return: 'success' or 'fail' if the operation is complete, or {} if it is still in progress
        """
        return self.check_report("scan_stitch_op")

    def get_wavelength_web(self):
        """uses websocket instead of tcp socket to get wavelength. I'm not sure of the relative performancce of this
        method relative to the normal method
        :return float: current wavelength in nm
        """
        try:
            msg_data = self._read_websocket_status_leftpanel()
        except:
            return -1, 'complete'
        return msg_data['wlm_wavelength']

    continue_terascan_states = ["operation completed", "operationfailed, TeraScan was not paused",
                                "TeraScan not available"]

    def continue_terascan(self):
        """" Continues a paused TeraScan. Unused in gui"""
        _, parameters_reply = self.send("terascan_continue", {})
        reply_status = parameters_reply["status"][0]
        if reply_status != 0:
            self.log.warn(self.continue_terascan_states[reply_status])

    _web_scan_status_str = ['off', 'cont', 'single', 'flyback', 'on', 'fail']

    def get_terascan_status(self, scan_type):
        """Get status of a terascan of a given type. Do not use this function if terascan updates are enabled as the
        socket will timeout.

        :param scan_type: Scan type
            'medium': BRF+etalon, rate from 100 GHz/s to 1 GHz/s
            'fine': All elements, rate from 20 GHz/s to 1 MHz/s
            'line': All elements, rate from 20 GHz/s to 50 kHz/s
        :return dict: Dictionary with 4 items:
            'current': current laser frequency
            'range': tuple with the full scan range
            'status': Laser status
                'stopped': Scan is not in progress
                'scanning': Scan is in progress
                'stitching': Scan is in progress, but currently stitching
            'web': Where scan is running in web interface (some failure modes still report 'scanning' through the usual interface);
            only available if the laser web connection is on.
        """
        self._check_terascan_type(scan_type)
        _, reply = self.send("scan_stitch_status", {"scan": scan_type})
        return reply

    fast_scan_types = {"cavity_continuous", "cavity_single", "cavity_triangular", "resonator_continuous",
                       "resonator_single", "resonator_ramp", "resonator_triangular", "ect_continuous", "ecd_ramp",
                       "fringe_test"}
    fast_scan_start_states = ["successful, scan in progress",
                              "can't start fast scan: width too great for the current tuning position",
                              "can't start fast scan: reference cavity not fitted",
                              "can't start fast scan: ERC not fitted",
                              "can't start fast scan: invalid scan type",
                              "can't start fast scan: time >10000 seconds"]
    fast_scan_stop_states = ["successful, scan in progress",
                             "can't stop fast scan: width too great for the current tuning position",
                             "can't stop fast scan: operation failed",
                             "can't stop fast scan: ERC not fitted",
                             "can't stop fast scan: invalid scan type",
                             "can't stop fast scan: time >10000 seconds"]
    fast_scan_states = ["scan not in progress",
                        "scan in progress",
                        "reference cavity not fitted",
                        "ERC not fitted",
                        "invalid scan_type"]

    def start_fast_scan(self, scan_type, width, time, setup_locks=True):
        """Setup and start fast scan.
        :param scan_type: scan type, see above (see ICE manual for details)
        :param width: scan width (in GHz)
        :param time: scan time/period (in s)
        :param setup_locks: Automatically setup etalon and reference cavity locks in the appropriate states.
        """
        self._check_fast_scan_type(scan_type)
        if setup_locks:
            if scan_type.startswith("cavity"):
                self.lock("lock_etalon", "on")
                self.lock("reference_cavity", "on")
            elif scan_type.startswith("resonator"):
                self.lock("lock_etalon", "on")
                self.lock("reference_cavity", "off")
        _, parameters_reply = self.send("fast_scan_start", {"scan": scan_type, "width": [width], "time": [time]})
        reply_status = reply["status"][0]
        if reply_status != 0:
            self.log.warn(self.fast_scan_states[reply_status])

    def check_fast_scan_report(self):
        """Check fast scan report.
        :return: 'success' or 'fail' if the operation is complete, or {} if it is still in progress.
        """
        return self.check_report("fast_scan_start")

    def stop_fast_scan(self, scan_type, return_to_start=True):
        """Stop fast scan of the given type.
        :param scan_type: scan type, see above (see ICE manual for details)
        :param return_to_start: Return to start.
            True: Return to the center frequency after stopping
            False: Stay at the current instantaneous frequency.
        """
        self._check_fast_scan_type(scan_type)
        _, parameters_reply = self.send("fast_scan_stop" if return_to_start else "fast_scan_stop_nr",
                                        {"scan": scan_type})
        reply_status = parameters_reply["status"][0]
        if reply_status != 0:
            self.log.warn(self.fast_scan_stop_states[reply_status])

    def get_fast_scan_status(self, scan_type):
        """Get status of a fast scan of a given type.
        :param scan_type: scan type, see above (see ICE manual for details)
        """
        self._check_fast_scan_type(scan_type)
        _, parameters_reply = self.send("fast_scan_poll", {"scan": scan_type})
        reply_status = reply["status"][0]
        if reply_status > 1:
            self.log.warn(self.fast_scan_states[reply_status])

    _default_terascan_rates = {"line": 10E6, "fine": 100E6, "medium": 5E9}

    def _build_message(self, op, params, transmission_id=None):
        """ Builds a json message in standard format to be sent to the laser
        :param op: operation to be performed by the laser
        :param params: parameters dictionary associated with the operation
        :param transmission_id: optional transmission id integer
        :return: json byte string to be send to the laser
        """
        if transmission_id is None:
            self.transmission_id = self.transmission_id % 16383 + 1
        else:
            self.transmission_id = transmission_id
        message = {'message': {'transmission_id': [self.transmission_id], 'op': op, 'parameters': dict(params)}}
        return json.dumps(message)

    _parse_errors = ["unknown", "JSON parsing error", "'message' string missing",
                     "'transmission_id' string missing", "No 'transmission_id' value",
                     "'op' string missing", "No operation name",
                     "operation not recognized", "'parameters' string missing", "invalid parameter tag or value"]

    def _parse_reply(self, reply):
        """ Parses a json reply from the laser into lists of the two relevant dictionaries
        :param reply: json reply from laser
        :return: list of reply operation dictionaries, list of reply parameters dictionaries
        """
        # Initialize operation and reply dictionary lists
        op_reply = []
        parameters_reply = []

        # Decode the ICE-BLOC reply with the appropriate delimeters between individual messages
        reply = reply.decode("utf-8")
        preplies = self._parse_messages('[' + reply.replace('}{', '},{') + ']')

        # Log any parsing errors and append messages parsed into dictionaries to output lists
        for preply in preplies:
            if preply["op"] == "parse_fail":
                parameters = preply["parameters"]
                error = parameters["protocol_error"][0]
                error_description = "unknown" if error >= len(self._parse_errors) else self._parse_errors[error]
                error_message = "device parse error: transmission_id={}, error={}({}), error point='{}'".format(
                    parameters.get("transmission", ["NA"])[0], error, error_description,
                    parameters.get("JSON_parse_error", "NA"))
                self.log.warn(error_message)
            op_reply.append(preply["op"])
            parameters_reply.append(preply["parameters"])
        return op_reply, parameters_reply

    def _parse_messages(self, message):
        """ Parses a standard format json message into a dictionary
        :param message: json string
        :return: message dictionary
        """
        # Disregard partial messages cut off by the buffer size
        if len(message) >= self.buffersize:
            self.log.warn('Message size >= buffer size, increase buffer read rate and/or buffer size to avoid '
                          'missing information')
            # split from right
            msg = message.rsplit('},{', 1)
            message = msg[0]
            # split from left
            msg = message.split('},{', 1)
            message = msg[1]
            message = '[{' + message + '}]'

        # Parse message according to the json protocol, extract the useful part and log ICE-BLOC protocol violations
        parsed_messages = json.loads(message)
        for n, parsed_message in enumerate(parsed_messages):
            if 'message' not in parsed_message:
                self.log.warn("coudn't decode message: {}".format(message))
            parsed_message = parsed_message['message']
            parsed_messages[n] = parsed_message
            for key in ['transmission_id', 'op', 'parameters']:
                if key not in parsed_message:
                    self.log.warn("parameter '{}' not in the message {}".format(key, message))
        return parsed_messages

    def _is_report_op(self, op):
        """Check if returned operation is a final report
        :param op: operation to be checked
        :return bool: True of operation is a final report, False otherwise
        """
        return op.endswith("_f_r") or op == self._terascan_update_op

    def _make_report_op(self, op):
        """Make an operation a final report operation
        :param: original operation
        :return string: operation as a final report
        """
        return op if op == self._terascan_update_op else op + "_f_r"

    def _parse_report_op(self, op):
        """Remove the final report suffix from an operation
        :param op: original operation
        :return string: parsed operation
        """
        if op == self._terascan_update_op:
            return op
        elif op[-4:] == '_f_r':
            return op[:-4]
        else:
            return op[:-6]

    def _update_reports(self, timeout=0):
        """Check for fresh operation reports
        :param timeout: time before operation quits
        """
        timeout = max(timeout, 0.001)
        self.socket.settimeout(timeout)
        try:
            self._receive_reports()
        except:
            pass
        self.socket.settimeout(self._timeout)

    def _receive_reports(self):
        """Recieve reports from the socket, log any replies received"""
        reply = self.socket.recv(self.buffersize)
        op_replies, parameters_replies = self._parse_reply(reply)
        for op_reply, parameters_reply in zip(op_replies, parameters_replies):
            if self._is_report_op(op_reply):
                self._last_status[self._parse_report_op(op_reply)] = parameters_reply
            else:
                self.log.warn("received reply while waiting for a report: '{}'".format(
                    self._build_message(op_reply, parameters_reply)))
        return op_replies, parameters_replies

    def _get_last_report(self, op):
        """Get the latest report for the given operation
        :param op: operation to be performed
        """
        report = self._last_status.get(op, {})
        if "report" in report:
            return "fail" if report["report"][0] else "success"
        return {}

    def _send_websocket_request(self, message):
        """ Sends a websocket request
        :param message: message to be sent
        """
        ws = websocket.create_connection("ws://{}:8088/control.htm".format(self.address1[0]), timeout=self._timeout)
        try:
            self._wait_for_websocket_status(ws, present_key="wlm_fitted")
            self._wait_for_websocket_status(ws, present_key="wlm_fitted")
            ws.send(message)
        finally:
            ws.close()

    def _wait_for_websocket_status(self, ws, present_key=None, nmax=20):
        """ Waits for the websocket to respond and returns the status
        :param ws: websocket
        :param present_key: not sure, I think its the status that we are waiting or
        :param nmax: number of iterations to wait for
        :return: websocket status
        """
        full_data = {}
        for _ in range(nmax):
            data = ws.recv()
            full_data.update(json.loads(data))
            if present_key is None or present_key in data:
                return full_data

    def _read_websocket_status(self, present_key=None, nmax=20):
        """ Reads the websocket status
        :param present_key: not sure, I think its the status that we are waiting or
        :param nmax: number of iterations to wait for
        :return: websocket status
        """
        ws = websocket.create_connection("ws://{}:8088/control.htm".format(self.address1[0]), timeout=self._timeout)
        try:
            return self._wait_for_websocket_status(ws, present_key=present_key, nmax=nmax)
        finally:
            ws.recv()
            ws.close()

    def _read_websocket_status_leftpanel(self, present_key=None, nmax=20):
        """ Reads the websocket status
        :param present_key: not sure, I think its the status that we are waiting or
        :param nmax: number of iterations to wait for
        :return: websocket status
        """
        ws = websocket.create_connection("ws://{}:8088/control.htm".format(self.address1[0]), timeout=self._timeout)
        try:
            # first call gets first_page
            self._wait_for_websocket_status(ws, present_key=present_key, nmax=nmax)
            # second call gets left_panel
            return self._wait_for_websocket_status(ws, present_key=present_key, nmax=nmax)
        finally:
            ws.recv()
            ws.close()

    def _check_terascan_type(self, scan_type):
        """Checks that the terascan type is valid.
        :param scan_type: Terascan type
        """

        if scan_type not in {"coarse", "medium", "fine", "line"}:
            self.log.warn("unknown terascan type: {}".format(scan_type))
        if scan_type == "coarse":
            self.log.warn("coarse scan is not currently available")

    def _trunc_terascan_rate(self, rate):
        """Chooses the closest terascan rate
        :param rate: Input terascan rate
        :return: Closest terascan rate
        """

        for tr in self.terascan_rates[::-1]:
            if rate >= tr:
                return tr
        return self.terascan_rates[0]

    def _check_fast_scan_type(self, scan_type):
        """Check that fast scan type is valid
        :param scan_type: Fast scan type
        """
        if scan_type not in self.fast_scan_types:
            self.log.warn("unknown fast scan type: {}".format(scan_type))


def main():

    from pylabnet.utils.logging.logger import LogClient

    logger = LogClient(
        host='localhost',
        port=12351,
        module_tag='Spectrum Analyser'
    )

    ip = '140.247.189.230'
    port1 = '1111'
    port2 = '2222'
    tisa = Driver(
        ip,
        port1,
        port2,
        logger=logger
    )


if __name__ == '__main__':
    main()
