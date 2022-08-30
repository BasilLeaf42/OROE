# texture_converter.py version 0.1 (c) 2006 Stefan Reutter (alpaca)

import sys
import struct
import os
import math

def convertTextureToDDS(path):
    f = open(path+'.texture', 'rb')
    fw = open(path+'.dds','wb')
    content = f.read()
    fw.write(content[48:])
    f.close()
    fw.close()
    
def convertDDSToTexture(path):
    f = open(path+'.dds', 'rb')
    content = f.read()
    
    init = [0x01000000, 0x30000000, 0x00000000]
    
    # note: attachment sets don't seem to be used
    normHeader = [0x0044E212, 0x00986212, 0x03C0DA12]
    fill = [0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x65, 0x56, 0x3A, 0x7C, 0x03, 0x00, 0x00, 0x00]
    
    dxt = -1
    
    size = content[12:16]
    if content[84:88] == 'DXT5':
        dxt = 16384
    elif content[84:88] == 'DXT1':
        dxt = 4096
    
    if dxt == -1:
        print 'File '+path+' could not be converted'
    else:
        fw = open(path+'.texture','wb')
        for i in init:
            fw.write(struct.pack('>i', i))
        fw.write('dds')
    
        for i in normHeader:
            fw.write(struct.pack('>i', i))
        fw.write(struct.pack('h',dxt))
        for i in fill:
            fw.write(struct.pack('>b', i))
        fw.write(size)
        fw.write(content)
        fw.close()
    f.close()
    
    
    
    
    
    
# Main script code

convertAll = False
subdirectories = False
verbose = False

files = []

for i in sys.argv[1:]:
    if i.startswith('-'):
        i = i.strip('-')
        if i.lower().find('type') > -1:
            type = i.lower().split('=')[1]
        elif i.lower() == 'all' > -1:
            convertAll = True
        elif i.lower() == 'sub' > -1:
            subdirectories = True
        elif i.lower() == 't' or i.lower() == 'texture':
            type = 'texture'
        elif i.lower() == 'd' or i.lower() == 'dds':
            type = 'dds'
        elif i.lower() == 'v' or i.lower() == 'verbose':
            verbose = True
        elif i.lower() == 'h' or i.lower() == 'help':
            print """alpaca''s MTW2 .texture converter, version 0.1
            
            usage: texture_converter.py [options] files
            
            options:
            -all: Converts all files, if this option is supplied, filenames can be omitted
            -d,--dds: Convert .dds to .texture
            -h,--help: Display this page
            -sub: Also convert all files in all subfolders, can only be used with -all
            -t,--texture: Convert .texture to .dds (default, can be omitted)
            -v: Verbose option, extra output"""
    else:
        files.append(i)
        
if type == 'dds' or type == 'd':
    if convertAll:
        if subdirectories:
            for tup in os.walk(''):
                for filepath in tup[2]:
                    if filepath.find('.dds') > -1:
                        files.append(os.path.join(tup[0], filepath.split('.dds')[0]))
        else:
            for filepath in os.listdir(''):
                if filepath.find('.dds') > -1:
                    files.append(filepath.split('.dds')[0])
        i = 0
        perc = 0
        perc2 = 0
        for filepath in files:
            if math.floor(i*100/len(files)) > perc:
                perc = math.floor(i*100/len(files))
            if verbose:
                print 'Converting file '+filepath+'.dds('+str(i+1)+' of '+str(len(files))+') - '+str(perc)+'%'
            elif perc > perc2:
                print str(perc)+'% done'
                perc2 = perc
            convertDDSToTexture(filepath)
            i += 1
    else:
        i = 0
        perc = 0
        perc2 = 0
        x = 0
        for filepath in files:
            if math.floor(i*100/len(files)) > perc:
                perc = math.floor(i*100/len(files))
            if verbose:
                print 'Converting file '+filepath+'.dds('+str(i+1)+' of '+str(len(files))+') - '+str(perc)+'%'
            elif perc > perc2:
                print str(perc)+'% done'
                perc2 = perc
            convertDDSToTexture(filepath)
            i += 1          
else:
    if convertAll:
        if subdirectories:
            for tup in os.walk(''):
                for filepath in tup[2]:
                    if filepath.find('.texture') > -1:
                        files.append(os.path.join(tup[0], filepath.split('.texture')[0]))
        else:
            for filepath in os.listdir(''):
                if filepath.find('.texture') > -1:
                    files.append(filepath.split('.texture')[0])
        i = 0
        perc = 0
        perc2 = 0
        for filepath in files:
            if math.floor(i*100/len(files)) > perc:
                perc = math.floor(i*100/len(files))
            if verbose:
                print 'Converting file '+filepath+'.texture('+str(i+1)+' of '+str(len(files))+') - '+str(perc)+'%'
            elif perc > perc2:
                print str(perc)+'% done'
                perc2 = perc
            convertTextureToDDS(filepath)
            i += 1
    else:
        i = 0
        perc = 0
        perc2 = 0
        x = 0
        for filepath in files:
            if math.floor(i*100/len(files)) > perc:
                perc = math.floor(i*100/len(files))
            if verbose:
                print 'Converting file '+filepath+'.texture('+str(i+1)+' of '+str(len(files))+') - '+str(perc)+'%'
            elif perc > perc2:
                print str(perc)+'% done'
                perc2 = perc
            convertTextureToDDS(filepath)
            i += 1
print 'Done'