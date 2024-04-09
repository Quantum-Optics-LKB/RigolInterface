import os
import sys

# Directory containing GenericDevice must be in path
# Add parent directory of current file to path
parent_directory = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, parent_directory)
# Add also directory two levels up
sys.path.insert(0, os.path.dirname(parent_directory))
from GenericDevice import _GenericDevice

import numpy as np
from time import sleep


class SpectrumAnalyzer(_GenericDevice):
    def get_max_point(self) -> float:
        self.resource.write(':CALCulate:MARKer1:MAXimum')
        return float(self.resource.query(':CALCulate:MARKer1:X?'))

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

    def span(self, center: float = 22.5e6, span: float = 45e6,
                                     rbw: int = 100,
                                     vbw: int = 30, swt: float = 'auto',
                                     trig: bool = None, single = False) -> np.ndarray:
        """Configure and execute measurement of noise power spectrum

        THIS FUNCTION REPLACES NOW DEPRECATED FUNCTION <set_trace_parameters_and_get>

        This function should work identically to the <span> function defined in
        SpectrumAnalyzer class of RigolInterface.py

        (!) For long sweep times, use single sweep mode
        
        :param float center: Center frequency in Hz
        :param float span: span in Hz
        :param float rbw: Resolution bandwidth in Hz
        :param float vbw: Video bandwidth in Hz
        :param float swt: Total measurement time in s
        :param bool trig: External trigger
        :param bool single: Set True for single sweep mode,
            defaults to False for continuous sweep mode
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

        if trig is not None:
            trigstate = self.resource.query(':TRIGger:SEQuence:SOURce?').replace('\n','')
            istrigged = trigstate != 'IMM' # whether SA is initially triggered
            # If trigger true and initial trigger type IMMediate, then set to EXTernal
            if trig and not (istrigged): 
                self.resource.write(':TRIGger:SEQuence:SOURce EXTernal')
                self.resource.write(
                    ':TRIGger:SEQuence:EXTernal:SLOPe POSitive')
            # If trigger false and initial trigger type not IMMediate, set to IMMediate
            elif not (trig) and istrigged:
                self.resource.write(':TRIGger:SEQuence:SOURce IMMediate')
        set_trigstate = self.resource.query(':TRIGger:SEQuence:SOURce?').replace('\n','')

        # Query current instrument sweep state
        sweep_state = int(self.resource.query(':INITiate:CONTinuous?'))
        if single == False:
            if sweep_state == 1: 
                # Already in continuous
                pass
            elif sweep_state == 0:
                # Put into continous
                self.resource.write(':INITiate:CONTinuous 1')
            triginfo_msg = ' with trigger' if set_trigstate == 'EXT' else ''
            print(f'{self.short_name} | Getting power spectrum (continuous sweep mode' +
                  triginfo_msg + ')')
        elif single == True:
            # In following conditional blocks, *OPC command (operation complete)
            # is sent subsequent to command intializing scan so that operation 
            # complete status can be polled (must wait for scan completion).
            self.resource.write('*CLS') # Reset status registers, clear error queue
            if sweep_state == 1:
                # Put into single
                self.resource.write(':INITiate:CONTinuous 0')
                self.resource.write(':INITiate:IMMediate; *OPC')
            elif sweep_state == 0:
                if trig is None or trig == False:
                    self.resource.write(':INITiate:IMMediate; *OPC')
                elif trig == True:
                    # Must reset trigger just before initiating scan, otherwise
                    # it seems trigger success condition is stored, because scan
                    # starts immediately instead of waiting for next trigger
                    self.resource.write(':TRIGger:SEQuence:SOURce EXTernal')
                    self.resource.write(':INITiate:IMMediate; *OPC')
            triginfo_msg = ' on trigger' if set_trigstate == 'EXT' else ''
            print(f'{self.short_name} | Getting power spectrum (single sweep' +
                  triginfo_msg + ')')
            # Poll the operation complete status in the event status 
            # register (ESR). (Once all commands before *OPC have been executed, 
            # the operation complete bit in the ESR is set to 1)
            while int(self.resource.query('*ESR?')) != 1:
                sleep(0.1)
        self.resource.write(':FORMat:TRACe:DATA ASCii')
        data = self.query_data()
        # If SA was trigged before, put it back in the same state
        if trig is not None:
            if not (trig) and istrigged:
                self.resource.write(f":TRIGger:SEQuence:SOURce {trigstate}")
        # Put SA back into the state it started in
        if sweep_state != int(self.resource.query(':INITiate:CONTinuous?')):
            self.resource.write(f':INITiate:CONTinuous {int(sweep_state)}')
        freqs = np.linspace(center-span//2, center+span//2, len(data))
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
