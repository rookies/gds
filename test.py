#!/usr/bin/python3
import serial, struct, time, marshal
from matplotlib import pyplot

useScope = False
marshalFile = 'savedData.dat'
port = '/dev/ttyACM3'

def idn(dso):
    dso.write(b'*idn?\n')
    idn = dso.readline().decode()[:-1]
    if idn.find('GW,GDS-') != 0:
        raise Exception('No GW Instek scope at {}?'.format(port))
    return idn

def acq_mem(dso, channel, longmem=False, debug=False):
    ## Send command:
    if longmem:
        cmd = ':acq{}:lmem?\n'.format(channel)
    else:
        cmd = ':acq{}:mem?\n'.format(channel)
    dso.write(bytes(cmd, 'ascii'))
    ## Check for start character:
    if dso.read(1).decode() != '#':
        raise Exception('No start character (#) found!')
    ## Read data size digits:
    dataSizeDigits = int(dso.read(1).decode())
    if debug: print('dataSizeDigits={}'.format(dataSizeDigits))
    if dataSizeDigits > 7:
        raise Exception('Data size digits should be <= 7, not {}!'.format(dataSizeDigits))
    ## Read data size:
    dataSize = int(dso.read(dataSizeDigits).decode())
    if debug: print('dataSize={}'.format(dataSize))
    if dataSize > 4000008:
        raise Exception('Data size should be <= 4000008, not {}!'.format(dataSize))
    ## Read rest of the data:
    data = bytearray(dataSize)
    dso.readinto(data)
    ## Parse time interval:
    timeInterval = struct.unpack('<f', data[:4])[0]
    if debug: print('timeInterval={}'.format(timeInterval))
    ## Parse channel indicator:
    channelIndicator = data[4]
    if debug: print('channelIndicator={}'.format(channelIndicator))
    ## Parse waveform data (after 3 unused bytes):
    waveformData = []
    for i in range(0, len(data[8:]), 2):
        val = (data[8+i] << 8) + data[9+i]
        waveformData.append(val)
    ## Return result:
    return (channelIndicator, timeInterval, waveformData)

def chan_offs(dso, channel):
    dso.write(bytes(':chan{}:offs?\n'.format(channel), 'ascii'))
    return float(dso.readline().decode()[:-1])

def chan_scal(dso, channel):
    dso.write(bytes(':chan{}:scal?\n'.format(channel), 'ascii'))
    return float(dso.readline().decode()[:-1])

def lrn(dso):
    dso.write(b'*lrn?\n')
    response = dso.readline().decode()[:-1]
    response = response.lower()
    response = response.replace('window:', ':window:')
    if response[0] == ':':
        response = response[1:]
    level1 = response.split(';:')
    data = {}
    for item in level1:
        parts = item.split(':', 1)
        if len(parts) != 2:
            continue
        key, val = parts
        values = val.split(';')
        if not key in data:
            data[key] = {}
        for val2 in values:
            key2, val3 = val2.split(' ')
            if key2 == 'math':
                key = 'math'
                data[key] = {}
            elif key == 'trigger' and key2 == 'pulse:mode:':
                key2 = 'pulsemode'
            elif key == 'trigger' and key2 == 'time':
                key2 = 'pulsetime'
            try:
                data[key][key2] = int(val3)
            except ValueError:
                data[key][key2] = float(val3)
    return data

if useScope:
    with serial.Serial(port, timeout=10) as dso:
        idnData = idn(dso)
        offs1 = chan_offs(dso, 1)
        offs2 = chan_offs(dso, 2)
        scal1 = chan_scal(dso, 1)
        scal2 = chan_scal(dso, 2)
        config = lrn(dso)
        data1 = acq_mem(dso, 1)
        time.sleep(.5)
        data2 = acq_mem(dso, 2)
    data = (idnData, offs1, offs2, scal1, scal2, config, data1, data2)
    with open(marshalFile, 'wb') as f:
        marshal.dump(data, f)
else:
    with open(marshalFile, 'rb') as f:
        data = marshal.load(f)
    idnData, offs1, offs2, scal1, scal2, config, data1, data2 = data

print('IDN: {}'.format(idnData))
print('Offsets: {} V, {} V'.format(offs1, offs2))
print('Scales: {} V/div, {} V/div'.format(scal1, scal2))
print('Time intervals: {} s, {} s'.format(data1[1], data2[1]))
for k1, v1 in config.items():
    print(k1)
    for k2, v2 in v1.items():
        print('  {}: {}'.format(k2, v2))

pyplot.subplot(2, 1, 1)
pyplot.plot(data1[2])
pyplot.subplot(2, 1, 2)
pyplot.plot(data2[2])
pyplot.show()
