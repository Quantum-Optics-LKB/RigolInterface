# -*- coding: utf-8 -*-
"""
Created on Tue Jan 26 10:47:25 2021

@author: Tangui ALADJIDI
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
import os
if sys.platform.startswith('linux'):
    import pyvisa as visa
elif sys.platform.startswith('win32'):
    import visa

plt.ioff()

class USBScope:
    def __init__(self):
        """
        Scans for USB devices
        """
        if sys.platform.startswith('linux'):
            self.rm = visa.ResourceManager('@py')
        elif sys.platform.startswith('win32'):
            self.rm = visa.ResourceManager()
        instruments = self.rm.list_resources()
        usb = list(filter(lambda x: 'USB' in x, instruments))
        if len(usb) == 0:
            print('Could not find any device !')
            print(f"\n Instruments found : {instruments}")
            sys.exit(-1)
        elif len(usb) > 1:
            print('More than one USB instrument connected' +
                  ' please choose instrument')
            for counter, dev in enumerate(usb):
                instr = self.rm.open_resource(dev)
                print(f"{dev} : {counter} ("+
                      f"{instr.manufacturer_name}, {instr.model_name})")
                instr.close()
            answer = input(f"\n Choice (number between 0 and {len(usb)-1}) ? ")
            answer = int(answer)
            self.scope = self.rm.open_resource(usb[answer])
        else:
            self.scope = self.rm.open_resource(usb[0])
        # Get one waveform to retrieve metrics
        self.scope.write(":STOP")
        # Query the sample rate
        self.sample_rate = self.scope.query_ascii_values(':ACQ:SRAT?')[0]
        self.yorigin = self.scope.query_ascii_values(":WAV:YOR?")[0]
        self.yref = self.scope.query_ascii_values(":WAV:YREF?")[0]
        self.yres = self.scope.query_ascii_values(":WAV:YINC?")[0]
        self.xref = self.scope.query_ascii_values(":WAV:XREF?")[0]
        self.xres = self.scope.query_ascii_values(":WAV:XINC?")[0]

    def get_waveform(self, channels: list = [1], plot: bool = False):
        """
        Gets the waveform of a selection of channels
        :param channels: List of channels
        :param plot: Will plot the traces
        :returns: Data, Time np.ndarrays containing the traces
        """
        Data = []
        Time = []
        if plot:
            fig = plt.figure()
            ax = fig.add_subplot(111)
            leg = []
        # Select channels
        for chan in channels:
            self.scope.write(f":WAV:SOUR CHAN{chan}")
            # Y origin for wav data
            YORigin = self.scope.query_ascii_values(":WAV:YOR?")[0]
            # Y REF for wav data
            YREFerence = self.scope.query_ascii_values(":WAV:YREF?")[0]
            # Y INC for wav data
            YINCrement = self.scope.query_ascii_values(":WAV:YINC?")[0]

            # X REF for wav data
            XREFerence = self.scope.query_ascii_values(":WAV:XREF?")[0]
            # X INC for wav data
            XINCrement = self.scope.query_ascii_values(":WAV:XINC?")[0]
            # Get time base to calculate memory depth.
            time_base = self.scope.query_ascii_values(":TIM:SCAL?")[0]
            # Calculate memory depth for later use.
            memory_depth = (time_base*12) * self.sample_rate

            # Set the waveform reading mode to RAW.
            self.scope.write(":WAV:MODE RAW")
            # Set return format to Byte.
            self.scope.write(":WAV:FORM BYTE")

            # Set waveform read start to 0.
            self.scope.write(":WAV:STAR 1")
            # Set waveform read stop to 250000.
            self.scope.write(":WAV:STOP 250000")

            # Read data from the scope, excluding the first 9 bytes (TMC header).
            rawdata = self.scope.query_binary_values(":WAV:DATA?", datatype='B')

            # Check if memory depth is bigger than the first data extraction.
            if (memory_depth > 250000):
                loopcount = 1
                # Find the maximum number of loops required to loop through all memory.
                loopmax = np.ceil(memory_depth/250000)
                while (loopcount < loopmax):
                    # Calculate the next start of the waveform in the internal memory.
                    start = (loopcount*250000)+1
                    self.scope.write(":WAV:STAR {0}".format(start))
                    # Calculate the next stop of the waveform in the internal memory
                    stop = (loopcount+1)*250000
                    print(stop)
                    self.scope.write(":WAV:STOP {0}".format(stop))
                    # Extent the rawdata variables with the new values.
                    rawdata.extend(self.scope.query_binary_values(":WAV:DATA?",
                                                                  datatype='B'))
                    loopcount = loopcount+1
            # This is the part that extracts the measurements from the scope.
            # Measure on channel 1.
            # self.scope.write(":MEAS:SOUR CHAN1")
            # Grab VMAX
            # v_max = self.scope.query_ascii_values(":MEAS:ITEM? VMAX")
            # v_min = self.scope.query_ascii_values(":MEAS:ITEM? VMIN")
            # v_pp = self.scope.query_ascii_values(":MEAS:ITEM? VPP")
            # v_rms = self.scope.query_ascii_values(":MEAS:ITEM? VRMS")
            # v_avg = self.scope.query_ascii_values(":MEAS:ITEM? VAVG")
            # freq = self.scope.query_ascii_values(":MEAS:ITEM? FREQ")

            # This is the part that handles all the data and presents it nicely.
            # Convert byte to actual voltage using Rigol data
            data = (np.asarray(rawdata) - YORigin - YREFerence) * YINCrement
            Data.append(data)
            # Calcualte data size for generating time axis
            data_size = len(data)
            # Create time axis
            time = np.linspace(XREFerence, XINCrement*data_size, data_size)
            Time.append(time)
            if plot:
                leg.append(f"Channel {chan}")
                # See if we should use a different time axis
                if (time[-1] < 1e-3):
                    time = time * 1e6
                    tUnit = "uS"
                elif (time[-1] < 1):
                    time = time * 1e3
                    tUnit = "mS"
                else:
                    tUnit = "S"
                # Graph data with pyplot.
                ax.plot(time, data)
                ax.set_ylabel("Voltage (V)")
                ax.set_xlabel("Time (" + tUnit + ")")
                ax.set_xlim(time[0], time[-1])
        if plot:
            ax.legend(leg)
            plt.show()
        Data = np.asarray(Data)
        Time = np.asarray(Time)
        return Data, Time

    def _set_xref(self, ref: float):
        """
        Sets the x reference
        :param ref: Reference point 
        :type ref: float
        :return: None
        :rtype: None

        """
        
        
        
        try:
            self.scope.write_ascii_values(":WAV:XREF", ref)
        except (ValueError or TypeError or AttributeError):
            print("Improper value for XREF !")
        self.xref = self.scope.query_ascii_values(":WAV:XREF?")[0]

    def _set_yref(self, ref: float):
        try:
            self.scope.write_ascii_values(":WAV:YREF", ref)
        except (ValueError or TypeError or AttributeError):
            print("Improper value for YREF !")
        self.xref = self.scope.query_ascii_values(":WAV:YREF?")[0]

    def _set_yres(self, res: float):
        self.scope.write_ascii_values(":WAV:YINC", res)

    def _set_xres(self, res: float):
        self.scope.write_ascii_values(":WAV:XINC", res)

    def measurement(self, channels: list = [1],
                    res: list = None):
        if list is not(None) and len(list) == 2:
            self.xres = self._set_xres(res[0])
            self.yres = self._set_yres(res[1])
        Data, Time = self.get_waveform(channels=channels)

    def get_screenshot(self, filename: str = None, format: str = 'png'):
        """
        Recovers a screenshot of the screen and returns the image
        :param filename: Location where the image will be saved
        :param format: Image format in ['jpg', 'png', 'tiff','bmp8', 'bmp24']
        """
        assert format in ('jpeg', 'png', 'bmp8', 'bmp24', 'tiff')
        self.scope.timeout = 60000
        self.scope.write(':disp:data? on,off,%s' % format)
        raw_img = self.scope.read_raw(614400)
        self.scope.timeout = 25000
        img = np.asarray(raw_img).reshape((600, 1024))
        if filename:
            try:
                os.remove(filename)
            except OSError:
                pass
            with open(filename, 'wb') as fs:
                fs.write(raw_img)
        return img

    def close(self):
        self.scope.write(":RUN")
        self.scope.close()
