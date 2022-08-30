# strings_bin_converter.py (c) 2006 Stefan Reutter (alias alpaca)
# Version 0.72
# A script to convert a number of MTW2 .strings.bin files to their .txt counterparts

import sys
import codecs
import struct
import os

def convertFile(filepath):
    """
    Takes a type 2 .strings.bin file and converts it to a text file
    """
    f = open(filepath+'.strings.bin', 'rb')
    (style1,) = struct.unpack('h',f.read(2))
    (style2,) = struct.unpack('h', f.read(2))
    if style1 == 2 and style2 == 2048:
        fw = codecs.open(filepath, encoding='UTF-16', mode='w')
        fw.write(unicode(struct.pack('HH',0xFFFE,0xAC00),'UTF-16')+'\r\n')
        (length,) = struct.unpack('i',f.read(4))
        for string in range(length):
            (strlen,) = struct.unpack('h', f.read(2))
            tagstr = ''
            for i in range(strlen):
                tagstr += unicode(f.read(2), 'UTF-16')
            (strlen,) = struct.unpack('h', f.read(2))
            screenstr = ''
            for i in range(strlen):
                tempstr = f.read(2)
                (e,) = struct.unpack('H',tempstr)
                if e == 10:
                    screenstr += '\\n'
                else:
                    screenstr += unicode(tempstr, 'UTF-16')
            fw.write('{'+tagstr+'}'+screenstr+'\r\n')
        fw.close()
    f.close()

if sys.argv[1] == 'all':
    arr = []
    i = 1
    for filepath in os.listdir(''):
        if filepath.find('.strings.bin') > -1:
            arr.append(filepath.split('.strings.bin')[0])
    for filepath in arr:
        print 'Converting file '+filepath+'('+str(i)+' of '+str(len(arr))+')'
        convertFile(filepath)
        i+=1
else:
    for i in range(len(sys.argv)-1):
        path = sys.argv[i+1]
        convertFile(path)