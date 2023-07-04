import pyvisa as visa
import sys
import numpy as np
import matplotlib.pyplot as plt

class Spectrum_Analyzer:
    def __init__(self, addr: str = None):
        """
        Scans for USB devices
        """
        if sys.platform.startswith('linux'):
            self.rm = visa.ResourceManager('@py')
        elif sys.platform.startswith('win32'):
            self.rm = visa.ResourceManager()
        instruments = self.rm.list_resources()
        print(instruments)
        self.sa = self.rm.open_resource(addr)
        print(f"Connected to {self.sa.query('*IDN?')}")

    def get_max_point(self):
       self.sa.write(':CALCulate:MARKer1:MAXimum')
       return float(self.sa.query(':CALCulate:MARKer1:X?')) 
    
    def set_trace_parameters_and_get(self, center: float = 22.5e6, span: float = 45e6, rbw: int = 100,
            vbw: int = 30, swt: float = 'auto'):
        """Arbitrary span measurement.
        :param float center: Center frequency in Hz
        :param float span: span in Hz
        :param float rbw: Resolution bandwidth in Hz
        :param float vbw: Video bandwidth in Hz
        :param float swt: Total measurement time in s
        :return: data, freqs for data and frequencies
        :rtype: np.ndarray

        """
        self.sa.write(f':FREQuency:SPAN {span}')
        self.sa.write(f':FREQuency:CENTer {center}')
        self.sa.write(f':BANDwidth:RESolution {int(rbw)}')
        self.sa.write(f':BANDwidth:VIDeo {int(vbw)}')
        if swt != 'auto':
            self.sa.write(f':SENSe:SWEep:TIME {swt}')  # in s.
        else:
            self.sa.write(':SENSe:SWEep:TIME:AUTO ON')
        self.sa.write(':DISPlay:WINdow:TRACe:Y:SCALe:SPACing LOGarithmic')
        # self.sa.write(':POWer:ASCale')
        self.sa.write(':FORMat:TRACe:DATA ASCii')
        # if specAn was trigged before, put it back in the same state
        data = self.query_data()
        # sweeptime = float(self.sa.query(':SWEep:TIME?'))
        freqs = np.linspace(center-span//2, center+span//2, len(data))
        return data, freqs

    def get_trace(self):
        span = float(self.sa.query(f':FREQuency:SPAN?'))
        center = float(self.sa.query(f':FREQuency:CENTer?'))
        self.sa.write(':FORMat:TRACe:DATA ASCii')
        data = self.query_data()
        freqs = np.linspace(center-span/2, center+span/2, len(data))
        return data, freqs
    
    def query_data(self):
        """Lower level function to grab the data from the SpecAnalyzer

        :return: data
        :rtype: list

        """
        rawdata = self.sa.query(':TRACe:DATA? TRACE1')
        data = rawdata.split(',')[:]
        data = [float(i) for i in data]
        return np.asarray(data)
        
    def close(self):
        self.sa.close()
