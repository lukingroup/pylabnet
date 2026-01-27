###
# SET MIN MAX FREQUENCIES IN MHZ
###
import sys
# caution: path[0] is reserved for script path (or '' in REPL)
sys.path.insert(1, '/Users/reneegeorge/Documents/Documents - renee’s MacBook Pro/Loncar Lab/Hu_Fridge/pylabnet_loncar')

import numpy as np
import time
import pylabnet.hardware.awg.zi_hdawg as zi_hdawg
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import textwrap
from pylabnet.utils.helper_methods import load_config

def upload_sequence(dataset, program, awgModule, lab_name, to_compile=True):

    dataset.log.info(f"Uploading to {lab_name} HDAWG...")
    awgModule.set("compiler/sourcestring", textwrap.dedent(program))

    if(not to_compile): return

    # While uploading
    while awgModule.getInt('compiler/status') == -1:
        dataset.log.info(f"Waiting for {lab_name} HDAWG compiler...")
        time.sleep(1)

    status = awgModule.getInt('compiler/status')
    # Compilation failed
    if status == 1:
        dataset.log.warn(f"Compilation failed: {awgModule.getString('compiler/statusstring')}")
        return
    # No warnings
    elif status == 0:
        dataset.log.info(f"{lab_name} Compilation successful with no warnings, will upload the program to the instrument.")
    # Warnings
    elif status == 2:
        dataset.log.warn(f"{lab_name} Compilation successful with warnings, will upload the program to the instrument.")
        dataset.log.warn(f"{lab_name} Compiler warning: {awgModule.getString('compiler/statusstring')}")
    else:
        dataset.log.warn(f"Unknown status. {lab_name} Compiler warning: {awgModule.getString('compiler/statusstring')}")

    # Wait for the waveform upload to finish
    while (awgModule.getDouble('progress') < 1.0) and (awgModule.getInt('elf/status') != 1):
        dataset.log.info(f"Progress: {awgModule.getDouble('progress'):.2f}")
        time.sleep(0.2)

    elf_status = awgModule.getInt('elf/status')
    if elf_status == 0:
        dataset.log.info(f"Upload to {lab_name} successful.")
    elif elf_status == 1:
        dataset.log.warn(f"Upload to {lab_name} failed.")