# hdawg_pulse_programs_using_eodmr_upload.py  # Suggested filename for this script.

import time  # Import time for simple polling loops (waiting for AWG to finish).
import textwrap  # Import textwrap so we can dedent multi-line SeqC program strings cleanly.
from typing import List, Tuple, Optional  # Import typing helpers for clearer function signatures.

import numpy as np  # Import NumPy to build inclusive sweeps robustly.

import EODMR_Si29 as eodmr  # Import the user-provided script as a Python module (must be on PYTHONPATH or same folder).
import pylabnet.hardware.awg.zi_hdawg as zi_hdawg  # Import the HDAWG driver wrapper used by EODMR_Si29.py.
from zhinst.toolkit import Session

unit_len = 16  # Use 16 samples to satisfy the device minimum waveform length.
# We use oscillator 2 as the reference (like EODMR_Si29.py), and step frequency using integer harmonic values.
base_osc = 0  # Choose oscillator 0 as the frequency reference for the sweep.
sine_gen = 0  # Use sine generator 0 for modulation.
base_f = 1e3 #base frequency at 0.1GHz


class _LogProxy:
    # Logger-like object that supports .info/.warning/.error and is also callable like a function.
    def info(self, msg: str) -> None:
        print(msg)

    def warn(self, msg: str) -> None:
        print(f"WARNING: {msg}")

    def error(self, msg: str) -> None:
        print(f"ERROR: {msg}")

    def __call__(self, msg: str) -> None:
        print(msg)


class _DummyDataset:
    def __init__(self) -> None:
        self.log = _LogProxy()      # supports dataset.log.info(...)
        self.dataset = self         # supports dataset.dataset.log.info(...)


def _round_up_to_multiple(x: int, base: int = 16) -> int:  # Helper: round sample counts up to a multiple of 16 (HDAWG-friendly).
    return int(base * int(np.ceil(float(x) / float(base))))  # Compute the smallest multiple of base >= x and return as int.

class HDAWGPulsePrograms:  # Main controller class that generates and runs ODMR/Rabi/Ramsey pulse sequences.
    def __init__(  # Define constructor arguments for configuring the connection and channel mapping.
        self,  # Standard Python instance reference.
        device_id: str,  # LabOne device id string like "dev8796".
        program_file_path: str,  #file path to the pulse program
        interface: str = "USB",  # Connection interface ("1GbE" or "USB").
        awg_index: int = 0,  # Which AWG core index to use (often 0).
        wave_output_index: int = 0,  # Which wave output inside that AWG (0 -> Wave Out 1, 1 -> Wave Out 2).
        oscillator_index: int = 0,  # Which internal oscillator to use for the carrier frequency (oscs/<index>/freq).
        modulation_mode: int = 1,  # Modulation mode enum (1 is commonly "Sine11" for the first output).
        lab_name: str = "HDAWG",  # Label used in log messages during compile/upload.
        sample_freq: int = 13, #define as an int n such that (2.4GHz)/2^n to get sampling frequecy (293kHz)
    ) -> None:  # Constructor returns None by convention.
        self.device_id = device_id  # Store the device id so we can set AWG module target device.
        self.program_file_path = program_file_path
        self.interface = interface  # Store interface to pass into the driver. 
        self.awg_index = int(awg_index)  # Store AWG index as int. 
        self.wave_output_index = int(wave_output_index)  # Store wave output index as int. 
        self.oscillator_index = int(oscillator_index)  # Store oscillator index as int. 
        self.modulation_mode = int(modulation_mode)  # Store modulation mode enum as int. 
        self.lab_name = str(lab_name)  # Store a readable lab name for logs. 
        self.sample_freq = sample_freq
        self.HDAWG = zi_hdawg.Driver(self.device_id, self.interface, None)  # Create the same driver object used by EODMR_Si29.py. 
        self.awgModule = self.HDAWG.daq.awgModule()  # Create an AWG module object (compiler + uploader). 
        self.awgModule.set("device", self.device_id)  # Point the AWG module at the correct hardware device id. 
        self.awgModule.set("index", self.awg_index)  # Select which AWG core we are programming. 
        self.awgModule.execute()  # Start the AWG module so it can accept compiler/uploader commands. 
        self.HDAWG.setd("system/clocks/sampleclock/freq", 2.4e9/(2^self.sample_freq)) #set sample frequency 
        self.fs_hz = float(self.HDAWG.getd("system/clocks/sampleclock/freq"))  # Read the active sample clock frequency in Hz from the device. 
        self._basic_device_setup()  # Apply a minimal baseline configuration similar in spirit to EODMR's configure(). 

    def _basic_device_setup(self) -> None:  # Set a minimal set of nodes so modulation + sequencer control work.
        self.HDAWG.seti("system/awg/channelgrouping", 0)  # force a known grouping
        self.HDAWG.seti("system/awg/oscillatorcontrol", 1)  # Allow the sequencer to control oscillator frequency (awg_sequencer mode).
        self.HDAWG.seti(f"awgs/{self.awg_index}/single", 1)  # Put the AWG core into single-shot mode so it stops when the program ends.
        self.HDAWG.seti(f"sigouts/{self.wave_output_index}/on", 1)  # Enable the physical analog output channel.
        self.HDAWG.seti(  # Configure digital modulation mode on the selected wave output so envelopes multiply internal sines.
            f"awgs/{self.awg_index}/outputs/{self.wave_output_index}/modulation/mode",  # Node path for modulation mode.
            self.modulation_mode,  # The chosen modulation mode enum (e.g., 1 == Sine11 for the first output in many setups).
        )
        self.HDAWG.setd(f"awgs/{self.awg_index}/outputs/{self.wave_output_index}/gains/0", 1.0)  # Set gain for AWG channel 0 contribution to 0 initially.
        self.HDAWG.setd(f"awgs/{self.awg_index}/outputs/{self.wave_output_index}/gains/1", 0.0)  # Set gain for AWG channel 1 contribution to 0 initially.
        self.HDAWG.setd(f"oscs/{self.oscillator_index}/freq", base_f)  # Set a safe default oscillator frequency (1 MHz) before any sequence runs.
        self.HDAWG.setd("sines/0/amplitudes/0", 1.0)

    def _seconds_to_samples_16(self, t_s: float) -> int:  # Convert seconds to samples and round up to a multiple of 16.
        raw = int(round(float(t_s) * self.fs_hz))  # Convert time in seconds to nearest integer sample count.
        return _round_up_to_multiple(max(raw, 16), 16)  # Enforce at least 16 samples and round up to a multiple of 16.

    def _run_awg_and_wait(self, timeout_s: float = 30.0) -> None:  # Start the AWG and block until it finishes (or timeout).
        self.HDAWG.seti(f"awgs/{self.awg_index}/enable", 1)  # Enable/run the AWG core (single-shot means it will stop at program end).
        t0 = time.time()  # Record start time for timeout tracking.
        while self.HDAWG.geti(f"awgs/{self.awg_index}/enable") == 1:  # Poll until the AWG core disables itself.
            if (time.time() - t0) > timeout_s:  # Check for timeout condition.
                raise TimeoutError("Timed out waiting for AWG to finish.")  # Raise if AWG did not stop in time.
            time.sleep(0.01)  # Sleep briefly between polls to reduce CPU load.

    def add_pulse(self, t: float, P: float, f: float):
        pulse_len = self._seconds_to_samples_16(float(t))  # Convert pulse duration to samples (multiple of 16).     

        
        self.program.append(f"// Pulse with frequency {float(f)}")  # SeqC comment.
        self.program.append(f"w_pulse = rect({pulse_len}, 1);")  # Define unit envelope waveform (length 16).
        self.program.append(f"h = {f/base_f};")
        self.program.append("resetOscPhase();")  # Reset oscillator phase at start of run.

        # Apply amplitude via output gain (like earlier).
        self.program.append(f"setDouble(\"awgs/{self.awg_index}/outputs/{self.wave_output_index}/gains/0\", {float(P)});")  # Set output gain to P.
        self.program.append(f"setInt(\"sines/{sine_gen}/harmonic\", h);")  # Set sine harmonic.
        self.program.append("playWave(1, w_pulse);")  # Play the pulse envelope.
        self.program.append("waitWave();")  # Wait for playback to finish.

        self.program.append(f"setDouble(\"awgs/{self.awg_index}/outputs/{self.wave_output_index}/gains/0\", 0.0);")  # Turn off output gain at end.
    
    def parse_program(self):
        
        # --- Configure a base oscillator frequency in Python so SeqC does NOT need to set oscs/.../freq at runtime ---
        self.HDAWG.setd(f"oscs/{base_osc}/freq", base_f)  # Set the base oscillator frequency.
        self.HDAWG.seti(f"sines/{sine_gen}/oscselect", base_osc)  # Make sine generator 0 reference oscillator 2. 
        self.program = []  # Build SeqC program lines.
        self.program.append(f"var h = {1};")    #placeholder=1
        self.program.append("wave w_pulse = rect(16, 1);")  # Define unit envelope waveform placeholder.

        with open(self.program_file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
        for line in lines[1:-1]:
            line = line.split(",")
            self.add_pulse(float(line[2]), float(line[1]), float(line[0]))
        
        seqc = textwrap.dedent("\n".join(self.program))  # Convert list of lines into SeqC source string.
        print(seqc)
        self.HDAWG.seti(f"awgs/{self.awg_index}/enable", 0)  # hard-disable AWG core before upload
        time.sleep(0.05)  # allow device state to settle
        eodmr.upload_sequence(_DummyDataset(), seqc, self.awgModule, lab_name=self.lab_name, to_compile=True)  # Call upload helper.
        self._run_awg_and_wait(timeout_s=30.0)  # Run sequence and wait for completion.
