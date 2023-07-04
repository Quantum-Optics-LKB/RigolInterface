from GenericDevice import _GenericDevice
import numpy as np


class Spectrum_Analyzer(_GenericDevice):
    def get_max_point(self) -> float:
        self.resource.write(':CALCulate:MARKer1:MAXimum')
        return float(self.resource.query(':CALCulate:MARKer1:X?'))

    def set_trace_parameters_and_get(self, center: float = 22.5e6, span: float = 45e6,
                                     rbw: int = 100,
                                     vbw: int = 30, swt: float = 'auto') -> np.ndarray:
        """Arbitrary span measurement.
        :param float center: Center frequency in Hz
        :param float span: span in Hz
        :param float rbw: Resolution bandwidth in Hz
        :param float vbw: Video bandwidth in Hz
        :param float swt: Total measurement time in s
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
        self.resource.write(':FORMat:TRACe:DATA ASCii')
        # if specAn was trigged before, put it back in the same state
        data = self.query_data()
        # sweeptime = float(self.resource.query(':SWEep:TIME?'))
        freqs = np.linspace(center-span//2, center+span//2, len(data))
        return data, freqs

    def get_trace(self) -> np.ndarray:
        """Retrieves the trace as displayed on the screen

        Returns:
            np.ndarray: 2 numpy arrays data and frequencies
        """
        span = float(self.resource.query(':FREQuency:SPAN?'))
        center = float(self.resource.query(':FREQuency:CENTer?'))
        self.resource.write(':FORMat:TRACe:DATA ASCii')
        data = self.query_data()
        freqs = np.linspace(center-span/2, center+span/2, len(data))
        return data, freqs

    def query_data(self) -> np.ndarray:
        """Lower level function to grab the data from the SpecAnalyzer

        :return: data
        :rtype: list

        """
        rawdata = self.resource.query(':TRACe:DATA? TRACE1')
        data = rawdata.split(',')[:]
        data = [float(i) for i in data]
        return np.asarray(data)
