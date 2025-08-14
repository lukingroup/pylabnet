"""
dacapi3
Detector Electronics Control Software Component -- DAC Comms
(c) 2022 Photon Spot Inc.

Author: Vikas Anant
Last update: 2023/01
"""

from pyftdi.spi import SpiController
from pyftdi.usbtools import UsbToolsError, UsbTools
from time import sleep
from numpy import arange
from re import match


class DAC:
    MaxVoltage = 4.981  # measured by setting dacvalue to 65535, i.e. dac.writedata(dac.dacunits_to_dacstr(dacchannel=8, value=65535))
    OffsetVoltage = 0.010  # measured by setting dacvalue to 0, i.e. dac.writedata(dac.dacunits_to_dacstr(dacchannel=8, value=0))
    Rseries = 10e3  # series resistance installed in electronics box
    channelmap = {
        '1A': 8,
        '1B': 7,
        '2A': 6,
        '2B': 5,
        '3A': 4,
        '3B': 3,
        '4A': 2,
        '4B': 1
    } # map of channel label to dac channel
    #dac = None
    biasvalue = 0  # keep track of what the current is

    def __init__(self, simulate=False):
        self.simulate = simulate

    def set_bias(self, channel, biascurrent, sleeptime=0.001):
        dacchannel = self.channelmap[channel]
        VoltageOut = biascurrent * self.Rseries * 1e-6  # in volts

        # convert to dac units
        value = round(65535 * (VoltageOut + self.OffsetVoltage) / (self.MaxVoltage + self.OffsetVoltage))
        #dac_int = (3 << 20) + (dacchannel - 1 << 16) + value
        # print(bin(dac_int))
        #dac_str = dac_int.to_bytes(3, 'big')
        dac_str = self.dacunits_to_dacstr(dacchannel, value)
        try:
            self.writedata(dac_str)         # write to dac
        except AttributeError:
            exit('dac not connected.  call connect() prior to writing to dac.')
        self.biasvalue = biascurrent
        sleep(sleeptime)

    def dacunits_to_dacstr(self, dacchannel, value):
        dac_int = (3 << 20) + (dacchannel - 1 << 16) + value
        # print(bin(dac_int))
        return dac_int.to_bytes(3, 'big')

    def ramp_up(self, channel, start, stop, step=0.01):
        if self.simulate:
            print('  ramp_up(channel=\'{0}\',start={1:.2f},stop={2:.2f})'.format(channel, start, stop))
        target_value = round(stop + float(step), 2)
        for val in arange(start, target_value, float(step)):
            self.set_bias(channel=channel, biascurrent=val)

    def ramp_down(self, channel, start, stop, step=0.01):
        if self.simulate:
            print('  ramp_down(channel=\'{0}\',start={1:.2f},stop={2:.2f})'.format(channel, start, stop))
        target_value = round(stop - float(step), 2)
        for val in arange(start, target_value, -float(step)):
            if val >= 0:
                self.set_bias(channel=channel, biascurrent=val)
            else:
                self.set_bias(channel=channel, biascurrent=0)

    def delatch(self, channel, step=0.01, sleeptime=0.1):
        original_biasvalue = self.biasvalue
        if self.simulate:
            print('delatching channel {0}'.format(channel))
        self.ramp_down(channel=channel, start=self.biasvalue, stop=0, step=step)
        sleep(sleeptime)
        self.ramp_up(channel=channel, start=0, stop=original_biasvalue, step=step)

    def connect(self, urllist, url_number=0, serial_number='any'):
        if self.simulate:
            print('simulating connection to DAC')
            return True
        self.sp = SpiController()
        try:
            if serial_number == 'any':
                print('connecting to {0}'.format(urllist[url_number][0]))
                self.sp.configure(urllist[url_number][0])
                self.dac = self.sp.get_port(cs=0, freq=1E6, mode=0)
            else:
                for urls in urllist:
                    sn = match(r"ftdi://ftdi:232h:(.+)/\d+", urls[0])[1]
                    if serial_number == sn:
                        print('connecting to {0}'.format(urls[0]))
                        self.sp.configure(urls[0])
                        self.dac = self.sp.get_port(cs=0, freq=1E6, mode=0)
        except UsbToolsError:
            exit('Could not connect to electronics. Check USB connection or device address.')

    def close(self):
        self.sp.close()

    def writedata(self, data):
        if self.simulate:
            print('    writing to dac {0}'.format(data))
        else:
            self.dac.write(data)


def find_devices(simulate=False):
    if simulate:
        seriallist = []
        i = 0
        print('simulating finding devices on USB')
        urllist = [('ftdi://ftdi:232h:1/1', '(USB <-> Serial Converter)'), ('ftdi://ftdi:232h:PS2023012301/1', '(USB <-> Serial Converter)')]
        for urls in urllist:
            serial_number = match(r"ftdi://ftdi:232h:(.+)/\d+", urls[0])[1]
            print('  ({0})          {1}   {2}\n'.format(i, urls[0], serial_number))
            seriallist.append(serial_number)
            i = i + 1
        return urllist, seriallist
    UsbTools.flush_cache()
    usbdevices = UsbTools.find_all(([[0x0403, 0x6014]]))
    #print(usbdevices)
    # convert to URL
    urllist = UsbTools.build_dev_strings(scheme='ftdi', vdict={'ftdi': 1027}, pdict={1027: {'232h': 24596}}, devdescs=usbdevices)
    if urllist == []:
        exit('no device found')
    else:
        seriallist = []
        i = 0
        print('devices found:')
        print('  (url_number) device-url                        serial number')
        for urls in urllist:
            serial_number = match(r"ftdi://ftdi:232h:(.+)/\d+", urls[0])[1]
            print('  ({0})          {1}   {2}\n'.format(i, urls[0], serial_number))
            seriallist.append(serial_number)
            i = i + 1
        return urllist, seriallist


if __name__ == "__main__":
    # initialize
    dac = DAC(simulate=True)
    # list devices
    urllist, seriallist = find_devices()
    # pick the device by url number as listed by find_devices
    dac.connect(urllist=urllist, url_number=0)
    # or pick the device by serial number
    # dac.connect(urllist=urllist, serial_number='PS2022110701')
    # send commands to dac
    print('set output for channel \'1A\' to 0uA, then 5uA')
    dac.set_bias(channel='1A', biascurrent=0)
    dac.set_bias(channel='1A', biascurrent=5)
    print('ramp up bias current from 0 to 10uA for channel \'1A\'')
    dac.ramp_up(channel='1A', start=0, stop=10, step=0.1)
    print('bias current is now:', dac.biasvalue)
    print('delatch channel \'1A\'')
    dac.delatch(channel='1A', step=0.1)

    print('done!')
