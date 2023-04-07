import pyvisa as visa
import numpy
import matplotlib.pyplot as plot
import sys
import math
rm = visa.ResourceManager('@py')

instruments = rm.list_resources()
print(instruments)
usb = list(filter(lambda x: 'USB' in x, instruments))
if (len(usb) != 1):
    print('Bad instrument list', instruments)
    sys.exit(-1)

scope = rm.open_resource(usb[0])
# generator.query("*RST")
# oscilloscope.query("*RST")
scope.write(":STOP")

# This is the part that extracts the waveform from the scope.
# Query the sample rate
sample_rate = scope.query_ascii_values(':ACQ:SRAT?')[0]
# Select CH1
scope.write(":WAV:SOUR CHAN1")

# Y origin for wav data
YORigin = scope.query_ascii_values(":WAV:YOR?")[0]
# Y REF for wav data
YREFerence = scope.query_ascii_values(":WAV:YREF?")[0]
# Y INC for wav data
YINCrement = scope.query_ascii_values(":WAV:YINC?")[0]

# X origin for wav data
XORigin = scope.query_ascii_values(":WAV:XOR?")[0]
# X REF for wav data
XREFerence = scope.query_ascii_values(":WAV:XREF?")[0]
# X INC for wav data
XINCrement = scope.query_ascii_values(":WAV:XINC?")[0]

# Get time base to calculate memory depth.
time_base = scope.query_ascii_values(":TIM:SCAL?")[0]
# Calculate memory depth for later use.
memory_depth = (time_base*12) * sample_rate

# Set the waveform reading mode to RAW.
scope.write(":WAV:MODE RAW")
# Set return format to Byte.
scope.write(":WAV:FORM BYTE")

# Set waveform read start to 0.
scope.write(":WAV:STAR 1")
# Set waveform read stop to 250000.
scope.write(":WAV:STOP 250000")

# Read data from the scope, excluding the first 9 bytes (TMC header).
rawdata = scope.query_binary_values(":WAV:DATA?", datatype='B')

# Check if memory depth is bigger than the first data extraction.
if (memory_depth > 250000):
    loopcount = 1
    # Find the maximum number of loops required to loop through all memory.
    loopmax = math.ceil(memory_depth/250000)
    while (loopcount < loopmax):
        # Calculate the next start of the waveform in the internal memory.
        start = (loopcount*250000)+1
        scope.write(":WAV:STAR {0}".format(start))
        # Calculate the next stop of the waveform in the internal memory
        stop = (loopcount+1)*250000
        print(stop)
        scope.write(":WAV:STOP {0}".format(stop))
        # Extent the rawdata variables with the new values.
        rawdata.extend(scope.query_binary_values(":WAV:DATA?", datatype='B'))
        loopcount = loopcount+1


# This is the part that extracts the measurements from the scope.
# Measure on channel 1.
scope.write(":MEAS:SOUR CHAN1")
# Grab VMAX
v_max = scope.query_ascii_values(":MEAS:ITEM? VMAX")
v_min = scope.query_ascii_values(":MEAS:ITEM? VMIN")
v_pp = scope.query_ascii_values(":MEAS:ITEM? VPP")
v_rms = scope.query_ascii_values(":MEAS:ITEM? VRMS")
v_avg = scope.query_ascii_values(":MEAS:ITEM? VAVG")
freq = scope.query_ascii_values(":MEAS:ITEM? FREQ")

# print ('Vmax: {0}\nVmin: {1}\nVpp: {2}\nVrms: {3}\nVavg: {4}\nFreq: {5}'.format(v_max[0],v_min[0],v_pp[0],v_rms[0],v_avg[0],freq[0]))

# This is the part that handles all the data and presents it nicely.
# Close connection to scope.
scope.close()

# Convert byte to actual voltage using Rigol data
data = (numpy.asarray(rawdata) - YORigin - YREFerence) * YINCrement
# Calcualte data size for generating time axis
data_size = len(data)
# Create time axis
time = numpy.linspace(XREFerence, XINCrement*data_size, data_size)

# See if we should use a different time axis
if (time[-1] < 1e-3):
    time = time * 1e6
    tUnit = "uS"
elif (time[-1] < 1):
    time = time * 1e3
    tUnit = "mS"
else:
    tUnit = "S"

# Inform about the data size, sample rate and scope setings. Mostly used for debugging.
print('Data size:', data_size, "Sample rate:", sample_rate)
print('YORigin:', YORigin, 'YREFerence:',
      YREFerence, 'YINCrement:', YINCrement)
print('XORigin:', XORigin, 'XREFerence:',
      XREFerence, 'XINCrement:', XINCrement)

# Graph data with pyplot.
plot.plot(time, data)
# plot.title("Oscilloscope Channel 1")
plot.ylabel("Voltage (V)")
plot.xlabel("Time (" + tUnit + ")")
plot.xlim(time[0], time[-1])
plot.subplots_adjust(left=0.1, top=0.98, bottom=0.1, right=0.8)
plot.text(0.81, 0.5, 'Vmax: {0}V\nVmin: {1}V\nVpp: {2}V\nVrms: {3}V\nVavg: {4}V\nFreq: {5}Hz'.format(
    v_max[0], v_min[0], v_pp[0], v_rms[0], v_avg[0], freq[0]), style='italic', bbox={'facecolor': 'white', 'alpha': 0.1, 'pad': 0}, transform=plot.gcf().transFigure)
plot.show()
