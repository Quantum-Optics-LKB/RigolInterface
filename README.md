# RigolInterface
Python interface for Rigol scopes. USB or TCPIP or anything.

## PyVisa install

You need to install PyVisa and PyVisa-py in order for this software to work on any platform !

Both can be readily `pip` / `conda` / `mamba` installed.

The package names are `pyvisa` and `pyvisa-py`.

- https://pyvisa.readthedocs.io/en/latest/
- https://pyvisa.readthedocs.io/projects/pyvisa-py/en/latest/index.html

## Usage

If you don't know the adress of your device, you can just instantiate an object and you will get a prompt to chose between the detected devices (if any are detected):
```python
from ScopeInterface import USBScope
scope = USBScope()
scope.get_waveform(channels = [1],plot=True)
scope.close()
```
[!toto](device_choice.png)
This will yield the resulting plot:

[!tototo](plot.png)
