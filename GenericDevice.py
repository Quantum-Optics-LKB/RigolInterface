import sys
import pyvisa as visa


class _GenericDevice:
    """A class to handle connection logic through PyVisa for all
    devices.
    Not meant to use "as is" rather it is subclassed by each instrument
    class.
    """

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
            usb = list(filter(lambda x: 'ASRL' not in x, instruments))
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
                    except Exception:
                        print(f"Could not open device : {Exception}")
                answer = input("\n Choice (number between 0 and " +
                               f"{len(usb)-1}) ? ")
                answer = int(answer)
                self.resource = self.rm.open_resource(usb[answer])
            else:
                self.resource = self.rm.open_resource(usb[0])
                print(f"Connected to {self.resource.query('*IDN?')}")
        else:
            try:
                self.resource = self.rm.open_resource(addr)
                print(f"Connected to {self.resource.query('*IDN?')}")
            except Exception:
                print("ERROR : Could not connect to specified device")

    def close(self):
        self.resource.close()
        self.rm.close()

    def print_error(self):
        ''' Print eventual errors occurred. '''
        print('Errors: ' + self.resource.query('SYST:ERR?'), end = '')

    def reset(self):
        ''' Reset instrument to factory default state. Does not clear volatile memory. '''
        self.resource.write('*RST')
        self.resource.write('*WAI')

    def clear(self):
        ''' Clear event register, error queue -when power is cycled-. '''
        self.resource.write('*CLS')
        self.resource.write('*WAI')
