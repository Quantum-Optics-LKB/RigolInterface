# -*- coding: utf-8 -*-
"""
Created on Tue Jan 26 10:47:25 2021

@author: Tangui ALADJIDI
"""

import numpy as np
import matplotlib.pyplot as plt
from time import sleep
import os
import sys

# Directory containing GenericDevice must be in path
# Add parent directory of current file to path
parent_directory = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, parent_directory)
# Add also directory two levels up
sys.path.insert(0, os.path.dirname(parent_directory))
from GenericDevice import _GenericDevice

plt.ioff()


class _Preamble:
    def __init__(self, s):
        elems = s.split(',')
        self.elems = elems
        self.points = int(elems[2])
        self.count = int(elems[3])
        self.x_inc = float(elems[4])
        self.x_orig = float(elems[5])
        self.x_ref = float(elems[6])
        self.y_inc = float(elems[7])
        self.y_orig = int(elems[8])
        self.y_ref = int(elems[9])

    def normalize(self, raw_y):
        yvals = raw_y.astype(np.float64)
        yvals -= (self.y_orig + self.y_ref)
        yvals *= self.y_inc
        return yvals

    def x_values(self):
        xvals = np.linspace(0, self.points-1, self.points)
        xvals *= self.x_inc
        xvals += self.x_ref
        # xvals += self.x_orig
        return xvals


class Scope(_GenericDevice):
    def get_waveform_raw(self, channels: list = [1], plot: bool = False,
                         memdepth: float = None, single = False) -> np.ndarray:
        """
        Gets the entire waveform data in the internal memory for a selection of channels
        (!) To retrieve long timescale waveforms, enable single trigger mode
        :param list channels: List of channels
        :param bool plot: Will plot the traces
        :param float memdepth: Memory depth (number of points) defaults to 
        None
        (does not modify)
        : param boolean single: Use single trigger mode
        :returns: Data, Time np.ndarrays containing the traces of shape
        (channels, nbr of points) if len(channels)>1
        """
        no_channels = len(channels)
        if len(channels) > 4:
            print("ERROR : Invalid channel list provided" +
                  " (List too long)")
            sys.exit()
        # Print message indicating from which channels waveforms are being retrieved
        if no_channels == 1: message = f'{self.short_name} | Getting raw waveform from'
        else: message = f'{self.short_name} | Getting raw waveforms from'
        for chan in channels:
            if chan > 4:
                print("ERROR : Invalid channel list provided" +
                    " (Channels are 1,2,3,4)")
                sys.exit()
            if no_channels==2 and chan == channels[-1]:
                message+= f' and Channel {chan}'
            elif no_channels>2:
                if chan != channels[-1]:
                    message+= f' Channel {chan},'
                if chan == channels[-1]:
                    message+= f' and Channel {chan}'
            else:
                message+= f' Channel {chan}'
        print(message)

        Data = []
        Time = []
        if plot:
            fig = plt.figure()
            ax = fig.add_subplot(111)
            leg = []
          
        if memdepth is not None:
            self.resource.write(f":ACQuire:MDEPth {int(memdepth)}")
        if single:
                trig_status = self.resource.query(':TRIGger:STATus?')
                self.resource.write(":SINGle")
                if trig_status == "STOP\n":
                    # Wait for trig status to change from "STOP" before while loop
                    sleep(1)
                while self.resource.query(':TRIGger:STATus?') != 'STOP\n':
                    pass
        else:
            self.resource.write(":STOP")
        # Select channels
        for chan in channels:
            self.resource.write(f":WAV:SOUR CHAN{chan}")
            # Y origin for wav data
            YORigin = self.resource.query_ascii_values(":WAV:YOR?")[0]
            # Y REF for wav data
            YREFerence = self.resource.query_ascii_values(":WAV:YREF?")[0]
            # Y INC for wav data
            YINCrement = self.resource.query_ascii_values(":WAV:YINC?")[0]

            # X REF for wav data
            XREFerence = self.resource.query_ascii_values(":WAV:XREF?")[0]
            # X INC for wav data
            XINCrement = self.resource.query_ascii_values(":WAV:XINC?")[0]
            memory_depth = int(
                self.resource.query_ascii_values(":ACQuire:MDEPth?")[0])
            # Set the waveform reading mode to RAW.
            self.resource.write(":WAV:MODE RAW")
            # Set return format to Byte.
            self.resource.write(":WAV:FORM BYTE")
            # Set waveform read start to 0.
            self.resource.write(":WAV:STAR 1")
            if (memory_depth > 250000):
                # Set waveform read stop to 250000.
                self.resource.write(":WAV:STOP 250000")
            else:
                self.resource.write(f":WAV:STOP {int(memory_depth)}")
            # Read data from the resource, excluding the first 9 bytes
            # (TMC header).
            rawdata = self.resource.query_binary_values(":WAV:DATA?",
                                                        datatype='B')
            sys.stdout.write(f"\rReading {len(rawdata)}/{memory_depth}")
            # Check if memory depth is bigger than the first data extraction.
            if (memory_depth > 250000):
                # Find the maximum number of loops required to loop through all
                # memory.
                loopmax = int(np.ceil(memory_depth/250000))
                for loopcount in range(1, loopmax):
                    # Calculate the next start of the waveform in the internal
                    # memory.
                    start = (loopcount*250000)+1
                    self.resource.write(f":WAV:STAR {start}")
                    # Calculate the next stop of the waveform in the internal
                    # memory
                    stop = (loopcount+1)*250000
                    sys.stdout.write(f"\rReading {stop}/{memory_depth}")
                    self.resource.write(f":WAV:STOP {stop}")
                    # Extent the rawdata variables with the new values.
                    rawdata.extend(self.resource.query_binary_values(":WAV:DATA?",
                                   datatype='B'))
            print()
            data = (np.asarray(rawdata) - YORigin - YREFerence) * YINCrement
            Data.append(data)
            # Calculate data size for generating time axis
            data_size = len(data)
            # Create time axis
            times = np.linspace(XREFerence, XINCrement*data_size, data_size)
            Time.append(times)
            if plot:
                leg.append(f"Channel {chan}")
                # See if we should use a different time axis
                if (times[-1] < 1e-3):
                    times *= 1e6
                    tUnit = "uS"
                elif (times[-1] < 1):
                    times *= 1e3
                    tUnit = "mS"
                else:
                    tUnit = "S"
                # Graph data with pyplot.
                ax.plot(times, data)
                ax.set_ylabel("Voltage (V)")
                ax.set_xlabel("Time (" + tUnit + ")")
                ax.set_xlim(times[0], times[-1])
        self.resource.write(":RUN")
        if plot:
            ax.legend(leg)
            plt.show()
        Data = np.asarray(Data)
        Time = np.asarray(Time)
        if len(channels) == 1:
            Data = Data[0, :]
            Time = Time[0, :]
        return Data, Time

    def get_waveform(self, channels: list = [1], plot: bool = False,
                     ndivs: int = None, memdepth: float = None, single = False) -> np.ndarray:
        """Retrieves the displayed waveform.
        Gets the waveform data in the internal memory for the time interval displayed on screen.
        From the displayed time scale and the sampling rate, will compute how many
        points of the memory correspond to the displayed signal.
        It will then retrieve the displayed signal (the part delimited by the 
        shaded area on top of the screen).
        See the :WAVeform Commands documentation for futher details.
        (!) To retrieve long timescale waveforms, enable single trigger mode

        Args:
            channels (list, optional): List of channels. Defaults to [1].
            plot (bool, optional): Whether to plot the result. Defaults to False.
            ndivs (int, optional): The number of time divisions on the screen.
                Defaults to None. Argument kept only for compatability reasons,
                ndivs is now set by query from oscilloscope
            memdepth (float, optional): Memory depth (number of points) defaults to None
            single (boolean, optional): Use single trigger mode
        Returns:
            np.ndarray: Data, Time
        """
        no_channels = len(channels)
        if len(channels) > 4:
            print("ERROR : Invalid channel list provided" +
                  " (List too long)")
            sys.exit()
        # Print message indicating from which channels waveforms are being retrieved
        if no_channels == 1: message = f'{self.short_name} | Getting waveform from'
        else: message = f'{self.short_name} | Getting waveforms from'
        for chan in channels:
            if chan > 4:
                print("ERROR : Invalid channel list provided" +
                    " (Channels are 1,2,3,4)")
                sys.exit()
            if no_channels==2 and chan == channels[-1]:
                message+= f' and Channel {chan}'
            elif no_channels>2:
                if chan != channels[-1]:
                    message+= f' Channel {chan},'
                if chan == channels[-1]:
                    message+= f' and Channel {chan}'
            else:
                message+= f' Channel {chan}'
        print(message)

        Data = []
        Time = []
        if plot:
            fig, ax = plt.subplots()
        if memdepth is not None:
            self.resource.write(f":ACQuire:MDEPth {int(memdepth)}")
        memory_depth = int(
            self.resource.query_ascii_values(":ACQuire:MDEPth?")[0])
        ndivs = int(self.resource.query_ascii_values(":SYSTem:GAMount?")[0])
        time_scale = float(self.resource.query_ascii_values(":TIM:SCAL?")[0])
        if single:
            trig_status = self.resource.query(':TRIGger:STATus?')
            self.resource.write(":SINGle")
            if trig_status == "STOP\n":
                # Wait for trig status to change from "STOP" before while loop
                sleep(1)
            while self.resource.query(':TRIGger:STATus?') != 'STOP\n':
                pass
        else:
            self.resource.write(":STOP")
        for chan in channels:
            self.resource.write(f':WAV:SOUR CHAN{chan}')
            self.resource.write(':WAV:MODE MAX')
            self.resource.write(':WAV:FORM BYTE')
            preamble = _Preamble(self.resource.query(':WAV:PRE?'))
            screen_points = np.floor(time_scale/preamble.x_inc)*ndivs
            # we look for the middle of the memory and take what's displayed
            # on the screen
            self.resource.write(
                f"WAV:STAR {memory_depth//2 - screen_points//2+1}")
            self.resource.write(
                f"WAV:STOP {memory_depth//2 + screen_points//2}")
            print(f'{self.short_name} | Transferring {int(screen_points)} data points from Channel {chan}')
            data = self.resource.query_binary_values(':WAV:DATA?', datatype='B',
                                                     container=np.array,
                                                     delay=0.5,
                                                     data_points=screen_points)
            data = preamble.normalize(data)
            times = np.arange(0, len(data)*preamble.x_inc, preamble.x_inc)
            Data.append(data)
            Time.append(times)
            if plot:
                if (times[-1] < 1e-3):
                    times *= 1e6
                    tUnit = "uS"
                elif (times[-1] < 1):
                    times *= 1e3
                    tUnit = "mS"
                else:
                    tUnit = "S"
                ax.plot(times, data, label=f"Channel {chan}")
                ax.set_ylabel("Voltage (V)")
                ax.set_xlabel("Time (" + tUnit + ")")
                ax.set_xlim(times[0], times[-1])
        self.resource.write(":RUN")
        if plot:
            ax.legend()
            plt.show()
        return np.asarray(Time), np.asarray(Data)
    
    def get_waveform_screen(self, channels: list = [1], plot: bool = False) -> np.ndarray:
        """Gets the waveform data currently displayed on the screen.
        Unlike reading waveform data from the internal memory, the oscilloscope does not need to be put into STOP state.

        Args:
            channels (list, optional): List of channels. Defaults to [1].
            plot (bool, optional): Whether to plot the result. Defaults to False.

        Returns:
            np.ndarray: Data, Time
        """
        Data = []
        Time = []
        if plot:
            fig, ax = plt.subplots()
        for chan in channels:
            # Set the channel source of waveform data
            self.resource.write(f':WAVeform:SOURce CHANnel{chan}')
            # Set the waveform data reading mode to NORMal
            self.resource.write(':WAVeform:MODE NORMal')
            # Set the return format of waveform data to BYTE
            self.resource.write(':WAVeform:FORMat BYTE')
            # Query and return ten different waveform parameters, see manual
            # Required to convert retrieved waveform data into time and volts below
            preamble = _Preamble(self.resource.query(':WAVeform:PREamble?'))
            # Obtain data from the buffer
            data = self.resource.query_binary_values(':WAVeform:DATA?', datatype='B',
                                            container=np.array,
                                            delay=0.5)
            data = preamble.normalize(data)
            times = np.arange(0, len(data)*preamble.x_inc, preamble.x_inc)
            Data.append(data)
            Time.append(times)
            if plot:
                if (times[-1] < 1e-3):
                    times *= 1e6
                    tUnit = "uS"
                elif (times[-1] < 1):
                    times *= 1e3
                    tUnit = "mS"
                else:
                    tUnit = "S"
                ax.plot(times, data, label=f"Channel {chan}")
                ax.set_ylabel("Voltage (V)")
                ax.set_xlabel("Time (" + tUnit + ")")
                ax.set_xlim(times[0], times[-1])
        if plot:
            ax.legend()
            plt.show()
        return np.asarray(Time), np.asarray(Data)

    def set_xref(self, ref: float):
        """
        Sets the x reference
        :param ref: Reference point
        :type ref: float
        :return: None
        :rtype: None

        """

        try:
            self.resource.write_ascii_values(":WAV:XREF", ref)
        except (ValueError or TypeError or AttributeError):
            print("Improper value for XREF !")
        self.xref = self.resource.query_ascii_values(":WAV:XREF?")[0]

    def set_yref(self, ref: float, channel: list = [1]):
        try:
            self.resource.write_ascii_values(":WAV:YREF", ref)
        except (ValueError or TypeError or AttributeError):
            print("Improper value for YREF !")
        self.xref = self.resource.query_ascii_values(":WAV:YREF?")[0]

    def set_yres(self, res: float):
        self.resource.write_ascii_values(":WAV:YINC", res)

    def set_xres(self, res: float):
        self.resource.write_ascii_values(":WAV:XINC", res)

    def measurement(self, channels: list = [1],
                    res: list = None):
        if list is not (None) and len(list) == 2:
            self.xres = self.set_xres(res[0])
            self.yres = self.set_yres(res[1])
        Data, Time = self.get_waveform(channels=channels)

    def get_screenshot(self, filename: str = None, format: str = 'png'):
        """
        Recovers a screenshot of the screen and returns the image
        :param filename: Location where the image will be saved
        :param format: Image format in ['jpg', 'png', 'tiff','bmp8', 'bmp24']
        """
        assert format in ('jpeg', 'png', 'bmp8', 'bmp24', 'tiff')
        self.resource.timeout = 60000
        self.resource.write(':disp:data? on,off,%s' % format)
        raw_img = self.resource.read()
        self.resource.timeout = 25000
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
        self.resource.write(":RUN")
        self.resource.close()
        self.rm.close()


class SpectrumAnalyzer(_GenericDevice):

    def zero_span(self, center: float = 1e6, rbw: int = 100,
                  vbw: int = 30, swt: float = 'auto', trig: bool = None):
        """Zero span measurement.
        :param float center: Center frequency in Hz, converted to int
        :param float rbw: Resolution bandwidth
        :param float vbw: Video bandwidth
        :param float swt: Total measurement time. Except if set to 'auto'
        :param bool trig: External trigger
        :return: data, time for data and time
        :rtype: np.ndarray

        """
        self.resource.write(':FREQuency:SPAN 0')
        self.resource.write(f':FREQuency:CENTer {center}')
        self.resource.write(f':BANDwidth:RESolution {int(rbw)}')
        self.resource.write(f':BANDwidth:VIDeo {int(vbw)}')
        if swt != 'auto':
            self.resource.write(f':SENSe:SWEep:TIME {swt}')  # in s.
        else:
            self.resource.write(':SENSe:SWEep:TIME:AUTO ON')
        self.resource.write(
            ':DISPlay:WINdow:TRACe:Y:SCALe:SPACing LOGarithmic')
        # self.resource.write(':POWer:ASCale')
        if trig is not None:
            trigstate = self.resource.query(':TRIGger:SEQuence:SOURce?')
            istrigged = trigstate != 'IMM'
            if trig and not (istrigged):
                self.resource.write(':TRIGger:SEQuence:SOURce EXTernal')
                self.resource.write(
                    ':TRIGger:SEQuence:EXTernal:SLOPe POSitive')
            elif not (trig) and istrigged:
                self.resource.write(':TRIGger:SEQuence:SOURce IMMediate')
        self.resource.write(':CONFigure:ACPower')
        self.resource.write(':TPOWer:LLIMit 0')
        self.resource.write(f':TPOWer:RLIMit {swt}')
        self.resource.write(':FORMat:TRACe:DATA ASCii')
        # if specAn was trigged before, put it back in the same state
        if trig is not None:
            if not (trig) and istrigged:
                self.resource.write(f":TRIGger:SEQuence:SOURce {trigstate}")
        data = self.query_data()
        sweeptime = float(self.resource.query(':SWEep:TIME?'))
        times = np.linspace(0, sweeptime, len(data))
        return data, times

    def span(self, center: float = 22.5e6, span: float = 45e6, rbw: int = 100,
             vbw: int = 30, swt: float = 'auto', trig: bool = None):
        """Arbitrary span measurement.
        :param float center: Center frequency in Hz
        :param float span: span
        :param float rbw: Resolution bandwidth
        :param float vbw: Video bandwidth
        :param float swt: Total measurement time
        :param bool trig: External trigger
        :return: data, freqs for data and frequencies
        :rtype: np.ndarray

        """
        self.resource.write(f':FREQuency:SPAN {span}')
        self.resource.write(f':FREQuency:CENTer {center}')
        self.resource.write(f':BANDwidth:RESolution {int(rbw)}')
        self.resource.write(f':BANDwidth:VIDeo {int(vbw)}')
        if swt != 'auto':
            self.resource.write(f':SENSe:SWEep:TIME {swt}')  # in s.
        else:
            self.resource.write(':SENSe:SWEep:TIME:AUTO ON')
        self.resource.write(
            ':DISPlay:WINdow:TRACe:Y:SCALe:SPACing LOGarithmic')
        # self.resource.write(':POWer:ASCale')
        if trig is not None:
            trigstate = self.resource.query(':TRIGger:SEQuence:SOURce?')
            istrigged = trigstate != 'IMM'
            if trig and not (istrigged):
                self.resource.write(':TRIGger:SEQuence:SOURce EXTernal')
                self.resource.write(
                    ':TRIGger:SEQuence:EXTernal:SLOPe POSitive')
            elif not (trig) and istrigged:
                self.resource.write(':TRIGger:SEQuence:SOURce IMMediate')
        self.resource.write(':CONFigure:ACPower')
        self.resource.write(':FORMat:TRACe:DATA ASCii')
        # if specAn was trigged before, put it back in the same state
        if trig is not None:
            if not (trig) and istrigged:
                self.resource.write(f":TRIGger:SEQuence:SOURce {trigstate}")
        data = self.query_data()
        # sweeptime = float(self.resource.query(':SWEep:TIME?'))
        freqs = np.linspace(center-span//2, center+span//2, len(data))
        return data, freqs

    def query_data(self):
        """Lower level function to grab the data from the SpecAnalyzer

        :return: data
        :rtype: list

        """
        self.resource.write(':INITiate:PAUSe')
        rawdata = self.resource.query(':TRACe? TRACE1')
        data = rawdata.split(', ')[1:]
        data = [float(i) for i in data]
        self.resource.write(':TRACe:AVERage:CLEar')
        self.resource.write(':INITiate:RESume')
        return np.asarray(data)


class ArbitraryFG(_GenericDevice):

    def get_waveform(self, output: int = 1) -> list:
        """
        Gets the waveform type as well as its specs
        :param int output: Description of parameter `output`.
        :return: List containing all the parameters
        :rtype: list

        """
        if output not in [1, 2]:
            print("ERROR : Invalid output specified")
            return None
        ison = self.resource.query(f"OUTPut{output}?")[:-1] == "ON"
        ret = self.resource.query(f"SOURce{output}:APPLy?")
        ret = ret[1:-2].split(",")
        type = ret[0]
        freq = float(ret[1])
        amp = float(ret[2])
        offset = float(ret[3])
        phase = float(ret[4])
        return [ison, type, freq, amp, offset, phase]

    def turn_on(self, output: int = 1):
        """
        Turns on an output channel on the last preset
        :param int output: Output channel
        :return: None
        """
        self.resource.write(f"OUTPut{output} ON")

    def turn_off(self, output: int = 1):
        """
        Turns off an output channel on the last preset
        :param int output: Output channel
        :return: None
        """
        self.resource.write(f"OUTPut{output} OFF")

    def set_impedance(self, output: int = 1, load: str = 'INF'):
        """
        Sets the output impedance to specified value. It doesn't actually
        change the physical impendance of the instrument, but changes the
        displayed voltage to match the actual voltage on the device under test.
        :param int output: Output channel
        :param str load: specified impedance value. {<ohms>|INFinity|MINimum|MAXimum}
        :return: None
        """
        if output not in [1, 2]:
            print("ERROR : Invalid output specified")
            return None
        self.resource.write(f':OUTP{output}:IMP ' + load) 
        print(f'Impedance OUTP{output} set to :', self.resource.query(f':OUTP{output}:IMP?'))

    def dc_offset(self, output: int = 1, offset: float = 2.0):
        """
        Applies a constant voltage on the specified output
        :param int output: Output channel
        :param float offset: Voltage applied in Volts
        :return: None
        """
        if output not in [1, 2]:
            print("ERROR : Invalid output specified")
            return None
        self.resource.write(f":SOURce{output}:FUNCtion DC")
        self.resource.write(f":SOURce{output}:APPLy:USER 1, 1, {offset}, 0")
        self.turn_on(output)

    def sine(self, output: int = 1, freq: float = 100.0, ampl: float = 2.0,
             offset: float = 0.0, phase: float = 0.0):
        """
        Sets a sine wave on specified output
        :param int output: Output channel
        :param float freq: Frequency of the signa in Hz
        :param float ampl: Amplitude of the wave in Volts
        :param float offset: Voltage offset in Volts
        :param float phase: Signal phase in degree
        :return: None
        """
        if output not in [1, 2]:
            print("ERROR : Invalid output specified")
            return None
        self.resource.write(f":SOURce{output}:APPLy:SINusoid {freq}, {ampl}, " +
                            f"{offset}, {phase}")
        self.turn_on(output)

    def square(self, output: int = 1, freq: float = 100.0, ampl: float = 2.0,
               offset: float = 0.0, phase: float = 0.0, duty: float = 50.0):
        """
        Sets a square wave on specified output
        :param int output: Output channel
        :param float freq: Frequency of the signa in Hz
        :param float ampl: Amplitude of the wave in Volts
        :param float offset: Voltage offset in Volts
        :param float phase: Signal phase in degree
        :param float duty: Duty cycle in percent
        :return: None
        """
        if output not in [1, 2]:
            print("ERROR : Invalid output specified")
            return None
        self.resource.write(f":SOURce{output}:APPLy:SQUare {freq}, {ampl}, " +
                            f"{offset}, {phase}")
        self.resource.write(f":SOURce{output}:FUNCtion:SQUare:DCYCle {duty}")
        self.turn_on(output)

    def ramp(self, output: int = 1, freq: float = 100.0, ampl: float = 2.0,
             offset: float = 0.0, phase: float = 0.0, symm: float = 50.0):
        """
        Sets a triangular wave on specified output
        :param int output: Output channel
        :param float freq: Frequency of the signa in Hz
        :param float ampl: Amplitude of the wave in Volts
        :param float offset: Voltage offset in Volts
        :param float phase: Signal phase in degree
        :param float symm: Symmetry factor in percent (equivalent to duty)
        :return: None
        """
        if output not in [1, 2]:
            print("ERROR : Invalid output specified")
            return None
        self.resource.write(f":SOURce{output}:APPLy:RAMP {freq}, {ampl}, " +
                            f"{offset}, {phase}")
        self.resource.write(f":SOURce{output}:FUNCtion:RAMP:SYMMetry {symm}")
        self.turn_on(output)

    def pulse(self, output: int = 1, freq: float = 100.0, ampl: float = 2.0,
              offset: float = 0.0, phase: float = 0.0, duty: float = 50.0,
              rise: float = 10e-9, fall: float = 10e-9):
        """
        Sets a triangular wave on specified output
        :param int output: Output channel
        :param float freq: Frequency of the signa in Hz
        :param float ampl: Amplitude of the wave in Volts
        :param float offset: Voltage offset in Volts
        :param float phase: Signal phase in degree
        :param float duty: Duty cycle in percent
        :param float rise: Rise time in seconds
        :param float fall: Fall time in seconds
        :return: None
        """
        if output not in [1, 2]:
            print("ERROR : Invalid output specified")
            return None
        self.resource.write(f":SOURce{output}:APPLy:PULSe {freq}, {ampl}, " +
                            f"{offset}, {phase}")
        self.resource.write(f":SOURce{output}:FUNCtion:PULSe:DCYCLe {duty}")
        self.resource.write(
            f":SOURce{output}:FUNCtion:TRANsition:LEADing {rise}")
        self.resource.write(
            f":SOURce{output}:FUNCtion:TRANsition:TRAiling {fall}")
        self.turn_on(output)

    def noise(self, output: int = 1, ampl: float = 5.0, offset: float = 0.0):
        """
        Sends noise on specified output
        :param int output: Output channel
        :param float ampl: Amplitude in Volts
        :param float offset: Voltage offset in Volts
        :return: None
        """
        self.resource.write(f":SOURce{output}:APPLy:NOISe {ampl}, {offset}")
        self.turn_on(output)

    def arbitrary(self, output: int = 1, freq: float = 100, ampl: float = 5.0,
                  offset: float = 0.0, phase: float = 0.0,
                  function: str = 'SINC'):
        """
        Arbitrary function signal
        :param int output: Output channel
        :param float freq: Frequency of the signa in Hz
        :param float ampl: Amplitude of the wave in Volts
        :param float offset: Voltage offset
        :param float phase: Signal phase in degree
        :param str function: Function type
        :return: Description of returned object.
        :rtype: type

        """
        # List of all possible functions
        funcnames = ["KAISER", "ROUNDPM", "SINC", "NEGRAMP", "ATTALT",
                     "AMPALT", "STAIRDN", "STAIRUP", "STAIRUD", "CPULSE",
                     "NPULSE", "TRAPEZIA", "ROUNDHALF", "ABSSINE",
                     "ABSSINEHALF", "SINETRA", "SINEVER", "EXPRISE", "EXPFALL",
                     "TAN", "COT", "SQRT", "X2DATA", "GAUSS", "HAVERSINE",
                     "LORENTZ", "DIRICHLET", "GAUSSPULSE", "AIRY", "CARDIAC",
                     "QUAKE", "GAMMA", "VOICE", "TV", "COMBIN", "BANDLIMITED",
                     "STEPRESP", "BUTTERWORTH", "CHEBYSHEV1", "CHEBYSHEV2",
                     "BOXCAR", "BARLETT", "TRIANG", "BLACKMAN", "HAMMING",
                     "HANNING", "DUALTONE", "ACOS", "ACOSH", "ACOTCON",
                     "ACOTPRO", "ACOTHCON", "ACOTHPRO", "ACSCCON", "ACSCPRO",
                     "ACSCHCON", "ACSCHPRO", "ASECCON", "ASECPRO", "ASECH",
                     "ASIN", "ASINH", "ATAN", "ATANH", "BESSELJ", "BESSELY",
                     "CAUCHY", "COSH", "COSINT", "COTHCON", "COTHPRO",
                     "CSCCON", "CSCPRO", "CSCHCON", "CSCHPRO", "CUBIC,", "ERF",
                     "ERFC", "ERFCINV", "ERFINV", "LAGUERRE", "LAPLACE",
                     "LEGEND", "LOG", "LOGNORMAL", "MAXWELL", "RAYLEIGH",
                     "RECIPCON", "RECIPPRO", "SECCON", "SECPRO", "SECH",
                     "SINH", "SININT", "TANH", "VERSIERA", "WEIBULL",
                     "BARTHANN", "BLACKMANH", "BOHMANWIN", "CHEBWIN",
                     "FLATTOPWIN", "NUTTALLWIN", "PARZENWIN", "TAYLORWIN",
                     "TUKEYWIN", "CWPUSLE", "LFPULSE", "LFMPULSE", "EOG",
                     "EEG", "EMG", "PULSILOGRAM", "TENS1", "TENS2", "TENS3",
                     "SURGE", "DAMPEDOSC", "SWINGOSC", "RADAR", "THREEAM",
                     "THREEFM", "THREEPM", "THREEPWM", "THREEPFM", "RESSPEED",
                     "MCNOSIE", "PAHCUR", "RIPPLE", "ISO76372TP1",
                     "ISO76372TP2A", "ISO76372TP2B", "ISO76372TP3A",
                     "ISO76372TP3B", "ISO76372TP4", "ISO76372TP5A",
                     "ISO76372TP5B", "ISO167502SP", "ISO167502VR", "SCR",
                     "IGNITION", "NIMHDISCHARGE", "GATEVIBR", "PPULSE"]
        if function not in funcnames:
            print("ERROR : Unknwown function specified")
            pass
        self.resource.write(f":SOURce{output}:FUNCtion {function}")
        self.resource.write(f":SOURce{output}:APPLy:USER {freq}, {ampl}, " +
                            f"{offset}, {phase}")
        self.turn_on(output)
