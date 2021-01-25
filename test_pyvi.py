import pyvisa as visa
rm = visa.ResourceManager('@py')

instruments = rm.list_resources()

print(instruments)

for _ in instruments:

    if 'DS' in _:

        oscilloscope = rm.open_resource(_)

    if 'DG' in _:

        generator = rm.open_resource(_)
    if 'INSTR' in _:
        instrument = rm.open_resource(_)
# generator.query("*RST")
# oscilloscope.query("*RST")
instrument.query("*RST")
