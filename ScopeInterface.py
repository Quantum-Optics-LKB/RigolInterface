# -*- coding: utf-8 -*-
"""
Created on Tue Jan 26 10:47:25 2021

@author: Tangui ALADJIDI
"""

import numpy as np
import matplotlib.pyplot as plt
import sys
import os
# if sys.platform.startswith('linux'):
#     import pyvisa as visa
# elif sys.platform.startswith('win32'):
#     import visa
import pyvisa as visa

plt.ioff()


class USBScope:
    def __init__(self, addr: str = None):
        """
        Scans for USB devices
        """
        if sys.platform.startswith('linux'):
            self.rm = visa.ResourceManager('@py')
        elif sys.platform.startswith('win32'):
            self.rm = visa.ResourceManager()
        if addr is None:
            instruments = self.rm.list_resources()
            # usb = list(filter(lambda x: 'USB' in x, instruments))
            usb = list(filter(lambda x: 'ASRL1' not in x, instruments))
            # usb = instruments
            if len(usb) == 0:
                print('Could not find any device !')
                print(f"\n Instruments found : {instruments}")
                sys.exit(-1)
            elif len(usb) > 1:
                print('More than one USB instrument connected' +
                      ' please choose instrument')
                for counter, dev in enumerate(usb):
                    instr = self.rm.open_resource(dev)
                    try:
                        print(f"{dev} : {counter} (" +
                              f"{instr.query('*IDN?')})")
                        instr.close()
                    except:
                        print("Could not open device :'(")
                answer = input("\n Choice (number between 0 and " +
                               f"{len(usb)-1}) ? ")
                answer = int(answer)
                self.scope = self.rm.open_resource(usb[answer])
            else:
                self.scope = self.rm.open_resource(usb[0])
                print(f"{self.scope.manufacturer_name}" +
                      f", {self.scope.model_name}")
        else:
            try:
                self.scope = self.rm.open_resource(addr)
                print(f"Connected to {self.scope.query('*IDN?')}")
            except Exception:
                print("ERROR : Could not connect to specified device")

        # Get one waveform to retrieve metrics
        self.scope.write(":STOP")
        self.sample_rate = float(self.scope.query(':ACQuire:SRATe?'))
        self.scope.write(":RUN")

    def get_waveform(self, channels: list = [1], plot: bool = False,
                     memdepth: float = 10e3):
        """
        Gets the waveform of a selection of channels
        :param list channels: List of channels
        :param bool plot: Will plot the traces
        :param float memdepth: Memory depth (number of points)
        :returns: Data, Time np.ndarrays containing the traces of shape
        (channels, nbr of points) if len(channels)>1
        """
        Data = []
        Time = []
        if plot:
            fig = plt.figure()
            ax = fig.add_subplot(111)
            leg = []
        if len(channels) > 4:
            print("ERROR : Invalid channel list provided" +
                  " (List too long)")
            sys.exit()
        for chan in channels:
            if chan > 4:
                print("ERROR : Invalid channel list provided" +
                      " (Channels are 1,2,3,4)")
                sys.exit()
        self.scope.write(f":ACQuire:MDEPth {int(memdepth)}")
        self.scope.write(":STOP")
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
            # memory_depth = (time_base*12) * self.sample_rate
            memory_depth = self.scope.query_ascii_values(":ACQuire:MDEPth?")[0]

            # Set the waveform reading mode to RAW.
            self.scope.write(":WAV:MODE RAW")
            # Set return format to Byte.
            self.scope.write(":WAV:FORM BYTE")

            # Set waveform read start to 0.
            self.scope.write(":WAV:STAR 1")
            # Set waveform read stop to 250000.
            self.scope.write(":WAV:STOP 250000")

            # Read data from the scope, excluding the first 9 bytes
            # (TMC header).
            rawdata = self.scope.query_binary_values(":WAV:DATA?",
                                                     datatype='B')

            # Check if memory depth is bigger than the first data extraction.
            if (memory_depth > 250000):
                loopcount = 1
                # Find the maximum number of loops required to loop through all
                # memory.
                loopmax = np.ceil(memory_depth/250000)
                while (loopcount < loopmax):
                    # Calculate the next start of the waveform in the internal
                    # memory.
                    start = (loopcount*250000)+1
                    self.scope.write(":WAV:STAR {0}".format(start))
                    # Calculate the next stop of the waveform in the internal
                    # memory
                    stop = (loopcount+1)*250000
                    if plot:
                        print(stop)
                    self.scope.write(":WAV:STOP {0}".format(stop))
                    # Extent the rawdata variables with the new values.
                    rawdata.extend(self.scope.query_binary_values(":WAV:DATA?",
                                   datatype='B'))
                    loopcount = loopcount+1
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
        self.scope.write(":RUN")
        Data = np.asarray(Data)
        Time = np.asarray(Time)
        if len(channels) == 1:
            Data = Data[0, :]
            Time = Time[0, :]
        return Data, Time

    def set_xref(self, ref: float):
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

    def set_yref(self, ref: float, channel: list = [1]):
        try:
            self.scope.write_ascii_values(":WAV:YREF", ref)
        except (ValueError or TypeError or AttributeError):
            print("Improper value for YREF !")
        self.xref = self.scope.query_ascii_values(":WAV:YREF?")[0]

    def set_yres(self, res: float):
        self.scope.write_ascii_values(":WAV:YINC", res)

    def set_xres(self, res: float):
        self.scope.write_ascii_values(":WAV:XINC", res)

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
        self.scope.timeout = 60000
        self.scope.write(':disp:data? on,off,%s' % format)
        raw_img = self.scope.read()
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


class USBSpectrumAnalyzer:

    def __init__(self, addr: str = None):
        """Instantiates a SpecAnalyzer. By default, search through the
        available USB devices and ask the user to select the desired device.

        :param str addr: Physical address of SpecAnalyzer
        :return: Instance of class USBSpectrumAnalyzer
        :rtype: USBSpectrumAnalyzer

        """

        if sys.platform.startswith('linux'):
            self.rm = visa.ResourceManager('@py')
        elif sys.platform.startswith('win32'):
            self.rm = visa.ResourceManager()
        if addr is None:
            instruments = self.rm.list_resources()
            # usb = list(filter(lambda x: 'USB' in x, instruments))
            usb = list(filter(lambda x: 'ASRL1' not in x, instruments))
            if len(usb) == 0:
                print('Could not find any device !')
                print(f"\n Instruments found : {instruments}")
                sys.exit(-1)
            elif len(usb) > 1:
                print('More than one USB instrument connected' +
                      ' please choose instrument')
                for counter, dev in enumerate(usb):
                    instr = self.rm.open_resource(dev)
                    print(f"{dev} : {counter} (" +
                          f"{instr.query('*IDN?')})")
                    instr.close()
                answer = input("\n Choice (number between 0 and " +
                               f"{len(usb)-1}) ? ")
                answer = int(answer)
                self.sa = self.rm.open_resource(usb[answer])
                print(f"Connected to {self.sa.query('*IDN?')}")
            else:
                self.sa = self.rm.open_resource(usb[0])
                print(f"Connected to {self.sa.query('*IDN?')}")
        else:
            try:
                self.sa = self.rm.open_resource(addr)
                print(f"Connected to {self.sa.query('*IDN?')}")
            except Exception:
                print("ERROR : Could not connect to specified device")

    def zero_span(self, center: float = 1e6, rbw: int = 100,
                  vbw: int = 30, swt: float = 100e-6, trig: bool = None):
        """Zero span measurement.
        :param float center: Center frequency in Hz, converted to int
        :param float rbw: Resolution bandwidth
        :param float vbw: Video bandwidth
        :param float swt: Total measurement time. Except if set to 'auto'
        :param bool trig: External trigger
        :return: data, time for data and time
        :rtype: np.ndarray

        """
        self.sa.write(':FREQuency:SPAN 0')
        self.sa.write(f':FREQuency:CENTer {center}')
        self.sa.write(f':BANDwidth:RESolution {int(rbw)}')
        self.sa.write(f':BANDwidth:VIDeo {int(vbw)}')
        if swt != 'auto':
            self.sa.write(f':SENSe:SWEep:TIME {swt}')  # in s.
        else:
            self.sa.write(f':SENSe:SWEep:TIME:AUTO ON')
        self.sa.write(':DISPlay:WINdow:TRACe:Y:SCALe:SPACing LOGarithmic')
        # self.sa.write(':POWer:ASCale')
        if trig is not None:
            trigstate = self.sa.query(':TRIGger:SEQuence:SOURce?')
            istrigged = trigstate != 'IMM'
            if trig and not (istrigged):
                self.sa.write(':TRIGger:SEQuence:SOURce EXTernal')
                self.sa.write(':TRIGger:SEQuence:EXTernal:SLOPe POSitive')
            elif not (trig) and istrigged:
                self.sa.write(':TRIGger:SEQuence:SOURce IMMediate')
        self.sa.write(':CONFigure:ACPower')
        self.sa.write(':TPOWer:LLIMit 0')
        self.sa.write(f':TPOWer:RLIMit {swt}')
        self.sa.write(':FORMat:TRACe:DATA ASCii')
        # if specAn was trigged before, put it back in the same state
        if trig is not None:
            if not (trig) and istrigged:
                self.sa.write(f":TRIGger:SEQuence:SOURce {trigstate}")
        data = self.query_data()
        sweeptime = float(self.sa.query(':SWEep:TIME?'))
        time = np.linspace(0, sweeptime, len(data))
        return data, time

    def query_data(self):
        """Lower level function to grab the data from the SpecAnalyzer

        :return: data
        :rtype: list

        """
        self.sa.write(':INITiate:PAUSe')
        rawdata = self.sa.query(':TRACe? TRACE1')
        data = rawdata.split(', ')[1:]
        data = [float(i) for i in data]
        self.sa.write(':TRACe:AVERage:CLEar')
        self.sa.write(':INITiate:RESume')
        return np.asarray(data)

    def close(self):
        self.sa.close()


class USBArbitraryFG:

    def __init__(self, addr: str = None):
        """Instantiates a SpecAnalyzer. By default, search through the
        available USB devices and ask the user to select the desired device.

        :param str addr: Physical address of SpecAnalyzer
        :return: Instance of class USBSpectrumAnalyzer
        :rtype: USBSpectrumAnalyzer

        """

        if sys.platform.startswith('linux'):
            self.rm = visa.ResourceManager('@py')
        elif sys.platform.startswith('win32'):
            self.rm = visa.ResourceManager()
        if addr is None:
            instruments = self.rm.list_resources()
            # usb = list(filter(lambda x: 'USB' in x, instruments))
            # usb = instruments
            usb = list(filter(lambda x: 'ASRL1' not in x, instruments))
            if len(usb) == 0:
                print('Could not find any device !')
                print(f"\n Instruments found : {instruments}")
                sys.exit(-1)
            elif len(usb) > 1:
                print(usb)
                print('More than one USB instruments connected' +
                      ' please choose instrument')
                for counter, dev in enumerate(usb):
                    instr = self.rm.open_resource(dev)
                    print(f"{dev} : {counter} (" +
                          f"{instr.query('*IDN?')})")
                    instr.close()
                answer = input("\n Choice (number between 0 and " +
                               f"{len(usb)-1}) ? ")
                answer = int(answer)
                self.afg = self.rm.open_resource(usb[answer])
                print(f"Connected to {self.afg.query('*IDN?')}")
            else:
                self.afg = self.rm.open_resource(usb[0])
                print(f"Connected to {self.afg.query('*IDN?')}")
        else:
            try:
                self.afg = self.rm.open_resource(addr)
                print(f"Connected to {self.afg.query('*IDN?')}")
            except Exception:
                print("ERROR : Could not connect to specified device")
        self.afg.write(":STOP")

    def get_waveform(self, output: int = 1) -> [bool, str, float, float, float,
                                                float]:
        """
        Gets the waveform type as well as its specs
        :param int output: Description of parameter `output`.
        :return: List containing all the parameters
        :rtype: list [ison, typ, freq, amp, offset, phase]

        """
        if output not in [1, 2]:
            print("ERROR : Invalid output specified")
            return None
        ison = self.afg.query(f"OUTPut{output}?")[:-1] == "ON"
        ret = self.afg.query(f"SOURce{output}:APPLy?")
        ret = ret[1:-2].split(",")
        typ = ret[0]
        if typ == 'DC':
            offset = float(ret[3])
            freq = 0
            amp = 0
            phase = 0
        else:
            freq = float(ret[1])
            amp = float(ret[2])
            offset = float(ret[3])
            phase = float(ret[4])
        return [ison, typ, freq, amp, offset, phase]

    def turn_on(self, output: int = 1):
        """
        Turns on an output channel on the last preset
        :param int output: Output channel
        :return: None
        """
        self.afg.write(f"OUTPut{output} ON")

    def turn_off(self, output: int = 1):
        """
        Turns off an output channel on the last preset
        :param int output: Output channel
        :return: None
        """
        self.afg.write(f"OUTPut{output} OFF")

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
        self.afg.write(f":SOURce{output}:APPLy:DC {offset}")
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
        self.afg.write(f":SOURce{output}:APPLy:SINusoid {freq}, {ampl}, " +
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
        self.afg.write(f":SOURce{output}:APPLy:SQUare {freq}, {ampl}, " +
                       f"{offset}, {phase}")
        self.afg.write(f":SOURce{output}:FUNCtion:SQUare:DCYCle {duty}")
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
        self.afg.write(f":SOURce{output}:APPLy:RAMP {freq}, {ampl}, " +
                       f"{offset}, {phase}")
        self.afg.write(f":SOURce{output}:FUNCtion:RAMP:SYMMetry {symm}")
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
        self.afg.write(f":SOURce{output}:APPLy:PULSe {freq}, {ampl}, " +
                       f"{offset}, {phase}")
        self.afg.write(f":SOURce{output}:FUNCtion:PULSe:DCYCLe {duty}")
        self.afg.write(f":SOURce{output}:FUNCtion:TRANsition:LEADing {rise}")
        self.afg.write(f":SOURce{output}:FUNCtion:TRANsition:TRAiling {fall}")
        self.turn_on(output)

    def noise(self, output: int = 1, ampl: float = 5.0, offset: float = 0.0):
        """
        Sends noise on specified output
        :param int output: Output channel
        :param float ampl: Amplitude in Volts
        :param float offset: Voltage offset in Volts
        :return: None
        """
        self.afg.write(f":SOURce{output}:APPLy:NOISe {ampl}, {offset}")
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
        self.afg.write(f":SOURce{output}:APPLy:USER {freq}, {ampl}, " +
                       f"{offset}, {phase}")
        self.afg.write(f":SOURce{output}:FUNCtion {function}")
        self.turn_on(output)

    def close(self):
        self.afg.close()
