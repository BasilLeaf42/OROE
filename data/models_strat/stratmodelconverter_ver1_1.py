# ===================================================================================
#                            stratmodelconverter.py                                 |
# ===================================================================================
#                                                                                   |
# Programmer:     Sandy Wilson (KnightErrant)                                       |
#                                                                                   |
# Creation Date:  10 December 2007                                                  |
# Revision Dates:                                                                   |
#                                                                                   |
# ----------------------------------------------------------------------------------|
#                                                                                   |
#    This is a script mostly taken from the Python animation library for reading    |
# a .cas model file.  These are RTW models which aren't mesh files but the old way  |
# of holding mesh data.  They start off looking just like animations but they only  |
# have bone data and then big chunks of mesh data, usually just two meshes.         |
#                                                                                   |
# ===================================================================================

# Imports.
import array                   # The 1D array class, has fast reads and writes for binary files.
import struct                  # This is for reading and writing binary files. It packs and unpacks the data.
import math                    # Need this trig functions to do quat to euler conversions.

# Imports and variables for the file chooser.
from Tkinter import *
from Dialog import Dialog
from tkMessageBox import showwarning

import os
import os.path                 # Needed for full filename path splitting.
import fnmatch

dialogstates = {}

# ===================================================================================
#                            File operations.                                       |
# ===================================================================================
def iseof( fidin ) :
    val                    = fidin.read( 1 )
    if val == '' :
        return True

    # Rewind the file 1 byte.
    fidin.seek( -1, 1 )                 
    return False


# ===================================================================================
#                            Getters for binary files.                              |
# ===================================================================================

# -----------------------------------------------------------------------------------
def getbyte( fidin ) :
    (thebyte,)             = struct.unpack( 'b', fidin.read(1) ) # 'b' is signed byte.
    return thebyte

# -----------------------------------------------------------------------------------
def getubyte( fidin ) :
    (thebyte,)             = struct.unpack( 'B', fidin.read(1) ) # 'B' is unsigned byte.
    return thebyte

# -----------------------------------------------------------------------------------
def getshort( fidin ) :
    (theshort,)            = struct.unpack( 'h', fidin.read(2) ) # 'h' is signed short.
    return theshort

# -----------------------------------------------------------------------------------
def getushort( fidin ) :
    (theshort,)            = struct.unpack( 'H', fidin.read(2) ) # 'H' is unsigned short.
    return theshort

# -----------------------------------------------------------------------------------
def getint( fidin ) :
    (theint,)              = struct.unpack( 'i', fidin.read(4) ) # 'i' is signed int.
    return theint

# -----------------------------------------------------------------------------------
def getuint( fidin ) :
    (theint,)              = struct.unpack( 'I', fidin.read(4) ) # 'I' is unsigned int.
    return theint

# -----------------------------------------------------------------------------------
def getfloat( fidin ) :
    (thefloat,)            = struct.unpack( 'f', fidin.read(4) ) # 'f' is float.
    return thefloat

# -----------------------------------------------------------------------------------
def getstring( fidin, nchar ) :
    thestring              = fidin.read( nchar )                 # Direct binary string read.
    return thestring



# ===================================================================================
#                            Putters for binary files.                              |
# ===================================================================================

# -----------------------------------------------------------------------------------
def putbyte( thebyte, fidout ) :
    fidout.write( struct.pack( 'b', thebyte ) )            # 'b' is signed byte.
    return  

# -----------------------------------------------------------------------------------
def putubyte( thebyte, fidout ) :
    fidout.write( struct.pack( 'B', thebyte ) )            # 'B' is unsigned byte.
    return  

# -----------------------------------------------------------------------------------
def putshort( theshort, fidout ) :
    fidout.write( struct.pack( 'h', theshort ) )           # 'h' is signed short.
    return  

# -----------------------------------------------------------------------------------
def putushort( theshort, fidout ) :
    fidout.write( struct.pack( 'H', theshort ) )           # 'H' is unsigned short.
    return  

# -----------------------------------------------------------------------------------
def putint( theint, fidout ) :
    fidout.write( struct.pack( 'i', theint ) )             # 'i' is signed int.
    return  

# -----------------------------------------------------------------------------------
def putuint( theint, fidout ) :
    fidout.write( struct.pack( 'I', theint ) )             # 'I' is unsigned int.
    return  

# -----------------------------------------------------------------------------------
def putfloat( thefloat, fidout ) :
    fidout.write( struct.pack( 'f', thefloat ) )           # 'f' is float.
    return  

# -----------------------------------------------------------------------------------
def putstring( thestring, fidout ) :
    fidout.write( thestring )
    return  

# -----------------------------------------------------------------------------------
def putzerobytes( n, fidout ) :
    for ii in range(n) :
        putubyte( 0, fidout )
    return  


# ===================================================================================
#                            Formatters.                                            |
# ===================================================================================


# -----------------------------------------------------------------------------------
#    Strips trailing \0's. (Mete's fault.)  Used for fixed length comments that     |
# have null bytes padding them out to a fixed byte length.                          |
# -----------------------------------------------------------------------------------
def zipstrip( string ) :
    nch                    = len( string )
    for ii in range( nch ) :
        (val,)             = struct.unpack( 'b', string[ii] ) # Read each byte and break on a null.
        if val == 0 :
            break

    stripstring            = string[0:ii]

    return stripstring

# -----------------------------------------------------------------------------------
#    Format float into a string with nfield.ndecimal fixed output.                  |
# -----------------------------------------------------------------------------------
def formatfloat( x, nfield, ndecimal ) :

    formatstring           = '%+' + str( nfield ) + '.' + str( ndecimal ) + 'f'

    xstr                   = formatstring % x
    return xstr       

# -----------------------------------------------------------------------------------
#    Splits a full path name into path, filename with no extension, and extension.  |
# -----------------------------------------------------------------------------------
def splitpath( fullfilename ) :

    ( fpath, ftemp )       = os.path.split( fullfilename )
    ( fname, fext  )       = os.path.splitext( ftemp )

    fileparts              = [ fpath, fname, fext ]
    return fileparts


# ===================================================================================
#                                                                                   |
#    Utility for reading a full format .cas file (full format means with headers    |
# and footers, the type of files we got from Caliban's animations directory).  This |
# is highly modularized for ease of maintenance and, hopefully, extendability.      |
#                                                                                   |
# ----------------------------------------------------------------------------------|
#                                                                                   |
# Functions: computeeulers( quatfloats )                                            |
#            computequats(  eulers )                                                |
#            readandwritecasheader(        fidcas, fidtxt )                         |
#            readandwritecashierarchytree( fidcas, fidtxt )                         |
#            readandwritecastimeticks(     fidcas, fidtxt )                         |
#            readandwritecasbonesection(   fidcas, fidtxt, nbones )                 |
#            writecasdatatotext(           fidtxt, bonedata, quatfloats,            |
#                                          animfloats, posefloats, eulers )         |
#            readandwritecasfooter(        fidcas, fidtxt )                         |
#            readcasfile(                  fncas,  fntxt )                          |
#                                                                                   |
# ===================================================================================

# -----------------------------------------------------------------------------------
#    Computes Euler angles from quaternions.                                        |
# -----------------------------------------------------------------------------------
def computeeulers( quatfloats ) :

    nfloats                = len( quatfloats )
    nvecs                  = nfloats / 4              
    eulers                 = array.array( 'f' )

    for ivec in range( nvecs ) :
        idx                = ivec * 4
        q1                 = quatfloats[idx+0]
        q2                 = quatfloats[idx+1]
        q3                 = quatfloats[idx+2]
        q4                 = quatfloats[idx+3]
                           
        Q11                = 1 - 2 * ( q2*q2 + q3*q3 )
        Q12                =     2 * ( q1*q2 - q3*q4 )
        Q13                =     2 * ( q1*q3 + q2*q4 )
        Q21                =     2 * ( q1*q2 + q3*q4 )
        Q22                = 1 - 2 * ( q1*q1 + q3*q3 )
        Q23                =     2 * ( q2*q3 - q1*q4 )
        Q31                =     2 * ( q1*q3 - q2*q4 )
        Q32                =     2 * ( q2*q3 + q1*q4 )
        Q33                = 1 - 2 * ( q1*q1 + q2*q2 )
                           
#        # 231 method.      
#        spsi               = Q21
#        cpsi               = ( 1 - spsi*spsi )**0.5
#        stheta             = -Q31 / cpsi
#        ctheta             = +Q11 / cpsi
#        sphi               = -Q23 / cpsi
#        cphi               = +Q22 / cpsi
#                           
#        phi_rad            = math.atan2( sphi,   cphi )       
#        theta_rad          = math.atan2( stheta, ctheta )     
#        psi_rad            = math.atan2( spsi,   cpsi )       
#                           
#        # Try.             
#        eulers.append( phi_rad )
#        eulers.append( -theta_rad )
#        eulers.append( -psi_rad )
#                           
#        # Hey! this way  works!

        # GrumpyOldMan's code.
        sint               = 2 * ( q2 * q4 - q1 * q3 )
        cost_tmp           = 1.0 - sint*sint
        if abs( cost_tmp ) > 0.0001 :
            cost           = cost_tmp**0.5
        else :
            cost           = 0.0

        if abs( cost ) > 0.01 :
            sinv           = 2 * ( q2 * q3 + q1 * q4 )     / cost
            cosv           = ( 1 - 2 * ( q1*q1 + q2*q2 ) ) / cost
            sinf           = 2 * ( q1 * q2 + q3 * q4 )     / cost
            cosf           = ( 1 - 2 * ( q2*q2 + q3*q3 ) ) / cost
        else:
            sinv           = 2 * ( q1 * q4 - q2 * q3 )     
            cosv           = 1 - 2 * ( q1*q1 + q3*q3 )  
            sinf           = 0.0
            cosf           = 1.0

        roll               = math.atan2( sinv, cosv )
        pitch              = math.atan2( sint, cost )
        yaw                = math.atan2( sinf, cosf )

        eulers.append( roll )
        eulers.append(-pitch )
        eulers.append(-yaw )  

    return eulers


# -----------------------------------------------------------------------------------
#    Computes quaternions from Milkshape's x, y, z Euler angles.                    |
# -----------------------------------------------------------------------------------
def computequats( eulers ) :

    nfloats                = len( eulers )
    nvecs                  = nfloats / 3 
    quatfloats             = array.array( 'f' )

    for ivec in range( nvecs ) :
        idx                = ivec * 3
        phi_rad            = +eulers[idx+0]                # NOTE: These are the signs that worked in animmerge.py
        theta_rad          = -eulers[idx+1]
        psi_rad            = -eulers[idx+2]
                         
        sphi               = math.sin( phi_rad )
        cphi               = math.cos( phi_rad )
        stheta             = math.sin( theta_rad )
        ctheta             = math.cos( theta_rad )
        spsi               = math.sin( psi_rad )
        cpsi               = math.cos( psi_rad )
                         
#        # 231 method (or 132 if you follow that naming convention).
#        R11                = ctheta * cpsi       
#        R12                = -ctheta * spsi * cphi + stheta * sphi
#        R13                =  ctheta * spsi * sphi + stheta * cphi
#        R21                = spsi
#        R22                = cpsi * cphi
#        R23                = -cpsi * sphi
#        R31                = -stheta * cpsi
#        R32                =  stheta * spsi * cphi + ctheta * sphi
#        R33                = -stheta * spsi * sphi + ctheta * cphi
                         
        # 321 method (or 123 if you follow that naming convention).
        R11                = cpsi * ctheta       
        R12                = cpsi * stheta * sphi - spsi * cphi 
        R13                = cpsi * stheta * cphi + spsi * sphi
        R21                = spsi * ctheta
        R22                = spsi * stheta * sphi + cpsi * cphi
        R23                = spsi * stheta * cphi - cpsi * sphi
        R31                = -stheta
        R32                = ctheta * sphi
        R33                = ctheta * cphi
                         
        q4                 = 0.5 * ( 1 + R11 + R22 + R33 )**0.5
        q1                 = 0.25 * ( R32 - R23 ) / q4
        q2                 = 0.25 * ( R13 - R31 ) / q4
        q3                 = 0.25 * ( R21 - R12 ) / q4

        quatfloats.append( q1 )
        quatfloats.append( q2 )
        quatfloats.append( q3 )
        quatfloats.append( q4 )

    return quatfloats


# -----------------------------------------------------------------------------------
#    Reads binary full .cas files header. Also writes it to an ASCII txt file if    |
# fidtxt is not empty.  This has exactly 42 bytes of data for all .cas files.  It   |
# stops reading right before the filesize sans the header and footer number.        |
# -----------------------------------------------------------------------------------
def readandwritecasheader( fidcas, fidtxt, flags ) :

    # This is the return value.
    headerdata             = []

    # Check if text output is desired.
    if fidtxt == [] :
        WRITECASTXTFILE    = False
    else :
        WRITECASTXTFILE    = True

    # Allocate byte arrays to hold the two signature triples. 
    signaturebytetriple1   = array.array( 'B' )            
    signaturebytetriple2   = array.array( 'B' )            

    # 42 bytes of header here.
    float_version          = getfloat(  fidcas )           #  4 bytes.
    if abs( float_version - 3.02 ) < 0.001 :
        float_version      = 3.02                          # Make it exactly 3.02 for comparisons.
    if abs( float_version - 3.0 ) < 0.001 :
        float_version      = 3.0                           # Make it exactly 3.0 for comparisons.
    if abs( float_version - 2.23 ) < 0.001 :
        float_version      = 2.23                          # Make it exactly 2.23 for comparisons.
    if abs( float_version - 2.22 ) < 0.001 :
        float_version      = 2.22                          # Make it exactly 2.22 for comparisons.
    if abs( float_version - 3.12 ) < 0.001 :
        float_version      = 3.12                          # Make it exactly 3.12 for comparisons.
    if abs( float_version - 3.05 ) < 0.001 :
        float_version      = 3.05                          # Make it exactly 3.05 for comparisons.
    if abs( float_version - 2.19 ) < 0.001 :
        float_version      = 2.19                          # Make it exactly 2.19 for comparisons.

    int_thirtyeight        = getuint(   fidcas )           #  8 bytes.
    int_nine               = getuint(   fidcas )           # 12 bytes.
    int_zero1              = getuint(   fidcas )           # 16 bytes. 
    float_animtime         = getfloat(  fidcas )           # 20 bytes. 
    int_one1               = getuint(   fidcas )           # 24 bytes. 
    int_zero2              = getuint(   fidcas )           # 28 bytes. 
    signaturebytetriple1.append( getubyte( fidcas ) )      # 29 bytes. 
    signaturebytetriple1.append( getubyte( fidcas ) )      # 30 bytes. 
    signaturebytetriple1.append( getubyte( fidcas ) )      # 31 bytes. 
    int_one2               = getuint(   fidcas )           # 35 bytes. 
    int_zero3              = getuint(   fidcas )           # 39 bytes. 
    signaturebytetriple2.append( getubyte(  fidcas ) )     # 40 bytes. 
    signaturebytetriple2.append( getubyte(  fidcas ) )     # 41 bytes. 
    signaturebytetriple2.append( getubyte(  fidcas ) )     # 42 bytes. 

    # Form into list.
    headerdata.append( float_version )                     # Index 0.
    headerdata.append( int_thirtyeight )                   # Index 1. 
    headerdata.append( int_nine )                          # Index 2. 
    headerdata.append( int_zero1 )                         # Index 3. 
    headerdata.append( float_animtime )                    # Index 4. 
    headerdata.append( int_one1 )                          # Index 5. 
    headerdata.append( int_zero2 )                         # Index 6. 
    headerdata.append( signaturebytetriple1[0] )           # Index 7. 
    headerdata.append( signaturebytetriple1[1] )           # Index 8. 
    headerdata.append( signaturebytetriple1[2] )           # Index 9. 
    headerdata.append( int_one2 )                          # Index 10.
    headerdata.append( int_zero3 )                         # Index 11.
    headerdata.append( signaturebytetriple2[0] )           # Index 12. 
    headerdata.append( signaturebytetriple2[1] )           # Index 13. 
    headerdata.append( signaturebytetriple2[2] )           # Index 14. 

    # Write the fields.
    if ( WRITECASTXTFILE == True ) & ( flags.header == 1 ) :
        string1            = formatfloat(float_version, 5, 3) + ' ' + str(int_thirtyeight).ljust(3) + ' ' + str(int_nine).ljust(3) + ' '
        string1            = string1 + str(int_zero1).ljust(3) + ' ' + formatfloat(float_animtime, 5, 3) + ' '
        string1            = string1 + str(int_one1).ljust(3) + ' ' + str(int_zero2).ljust(3) + '    ' 
        string1            = string1 + str(signaturebytetriple1[0]).ljust(3) + ' ' + str(signaturebytetriple1[1]).ljust(3) + ' ' + str(signaturebytetriple1[2]).ljust(3) + '    ' 
        string1            = string1 + str(int_one2).ljust(3) + ' ' + str(int_zero3).ljust(3) + '    '
        string1            = string1 + str(signaturebytetriple2[0]).ljust(3) + ' ' + str(signaturebytetriple2[1]).ljust(3) + ' ' + str(signaturebytetriple2[2]).ljust(3) + '\n' 
        fidtxt.write( string1 )

    return headerdata


# -----------------------------------------------------------------------------------
#    Reads binary full .cas files hierarchy tree. Also writes it to an ASCII txt    |
# file if fidtxt is not empty.                                                      |
# -----------------------------------------------------------------------------------
def readandwritecashierarchytree( fidcas, fidtxt, version_float, flags ) :

    # This is the return value.
    hierarchydata          = array.array( 'I' )            # Unsigned int array for hierarchy tree.

    # Check if text output is desired.
    if fidtxt == [] :
        WRITECASTXTFILE    = False
    else :
        WRITECASTXTFILE    = True

    # Usually this is 21 ints. (Bones plus Scene_Root). This is the hierarchy tree.
    # FORMAT NOTE: If an old version float then nbones is a byte.  If version 3.21 or 3.20 its a short.
    if ( version_float == 3.02 ) | ( version_float == 2.23 ) | ( version_float == 3.0 ) | ( version_float == 2.22 ) | ( version_float == 2.19 ) :
        nbones             = getubyte( fidcas )
        for ii in range( nbones ) :
            hierarchydata.append( getuint( fidcas ) )
    else :
        nbones             = getushort( fidcas )
        for ii in range( nbones ) :
            hierarchydata.append( getuint( fidcas ) )

    if ( WRITECASTXTFILE == True ) & ( flags.hierarchy == 1 ) :
        fidtxt.write( str( nbones ).ljust(20) + ' ' )
        for ii in range( nbones ) :
            fidtxt.write( str( hierarchydata[ii] ).ljust(3) + ' ' )

        fidtxt.write( '\n' )
        fidtxt.flush()

    return hierarchydata


# -----------------------------------------------------------------------------------
#    Reads binary full .cas files time ticks. Also writes it to an ASCII txt file   |
# if fidtxt is not empty.                                                           |
# -----------------------------------------------------------------------------------
def readandwritecastimeticks( fidcas, fidtxt, version_float, flags ) :

    # This is the return value.
    timetickdata           = array.array( 'f' )            # Float array for time ticks.

    # Check if text output is desired.
    if fidtxt == [] :
        WRITECASTXTFILE    = False
    else :
        WRITECASTXTFILE    = True

    # Now read the number of frames and then the time ticks.
    nframes                = getuint( fidcas )
    if abs( nframes ) > 800 :
        print 'Bad nframes, exiting...'
        exit()
    for ii in range( nframes ) :
        timetick           = getfloat( fidcas ) 
        timetickdata.append( timetick )

    # Write it out if desired.
    if ( WRITECASTXTFILE == True ) & ( flags.timeticks == 1 ) :
        fidtxt.write( str( nframes ).ljust(20) + ' ' )
        for ii in range( nframes ) :
            fidtxt.write( formatfloat( timetickdata[ii], 5, 3 ) + ' ' )

        fidtxt.write( '\n' )
        fidtxt.flush()            

    return timetickdata


# -----------------------------------------------------------------------------------
#    Reads binary full .cas file bone section. Also writes it to an ASCII txt file  |
# if fidtxt is not empty.                                                           |
# -----------------------------------------------------------------------------------
def readandwritecasbonesection( fidcas, fidtxt, nbones, version_float, flags ) :

    # This is the return value.
    bonedata               = []

    # Allocate arrays.
    bonenames              = []
    quatframesperbone      = array.array( 'I' )            # Unsigned int array.
    animframesperbone      = array.array( 'I' )            # Unsigned int array.
    quatoffsetperbone      = array.array( 'I' )            # Unsigned int array.
    animoffsetperbone      = array.array( 'I' )            # Unsigned int array.
    zerosperbone           = array.array( 'I' )            # Unsigned int array.
    onesperbone            = array.array( 'I' )            # Unsigned int array.

    # Check if text output is desired.
    if fidtxt == [] :
        WRITECASTXTFILE    = False
    else :
        WRITECASTXTFILE    = True

    for ii in range( nbones ) :
        nch                = getuint(   fidcas )
        bonename           = fidcas.read( nch-1 )
        dummy              = getubyte(  fidcas )           # Null terminator byte. 

        quatframes         = getuint(   fidcas )
        animframes         = getuint(   fidcas )
        quatoffset         = getuint(   fidcas )
        animoffset         = getuint(   fidcas )
        zero               = getuint(   fidcas )                                            
       
        # FORMAT NOTE: If version 3.21 or 3.20 there's an extra uint and ubyte in the bones data section.
        if ( version_float != 3.02 ) & ( version_float != 2.23 ) & ( version_float != 3.0 ) & ( version_float != 2.22 ) & ( version_float != 3.12 ) & ( version_float != 3.05 ) & ( version_float != 2.19 ) :
            one            = getuint(   fidcas )
            byte1          = getubyte(  fidcas )
        else:
            one            = 1

        # Save.
        bonenames.append( bonename )
        quatframesperbone.append( quatframes )
        animframesperbone.append( animframes )
        quatoffsetperbone.append( quatoffset )
        animoffsetperbone.append( animoffset )
        zerosperbone.append( zero )
        onesperbone.append( one )

        # Write if desired.
        if ( WRITECASTXTFILE == True ) & ( flags.bones == 1 ) :
            fidtxt.write( bonename.ljust(20) + ' ' )
            string1        = str(quatframes).ljust(6) + ' ' + str(animframes).ljust(6) + ' ' 
            string1        = string1 + str(quatoffset).ljust(6) + ' ' + str(animoffset).ljust(6) + ' ' 
            string1        = string1 + str(zero).ljust(6) + ' '
            # FORMAT NOTE: If version 3.21 or 3.20 there's an extra uint and ubyte in the bones data section.
            if ( version_float != 3.02 ) & ( version_float != 2.23 ) & ( version_float != 3.0 ) & ( version_float != 2.22 ) & ( version_float != 3.12 ) & ( version_float != 3.05 ) & ( version_float != 2.19 ) :
                string1    = string1 + str(one).ljust(6) + ' ' + str(byte1).ljust(6) + '\n'
            else:
                string1    = string1 + '\n'
            fidtxt.write( string1 )
            fidtxt.flush()

    bonedata.append( bonenames )
    bonedata.append( quatframesperbone )
    bonedata.append( animframesperbone )
    bonedata.append( quatoffsetperbone )
    bonedata.append( animoffsetperbone )
    bonedata.append( zerosperbone )
    bonedata.append( onesperbone )

    return bonedata


# -----------------------------------------------------------------------------------
#    Writes the cas data to the text file separating the bones sections with a bone |
# number.                                                                           |
# -----------------------------------------------------------------------------------
def writecasdatatotext( fidtxt, bonedata, quatfloats, animfloats, posefloats, eulers ) :
    
    bonenames              = bonedata[0]
    quatframesperbone      = bonedata[1]
    animframesperbone      = bonedata[2]
    onesperbone            = bonedata[6]

    nbones                 = len( bonenames )              # Number of bones with Scene_Root.
    NBONES                 = nbones - 1                    # Number of bones EXCLUDING Scene_Root.

    # Do quatfloats and corresponding eulers.
    iquat                  = 0
    ieuler                 = 0
    for ii in range( nbones ) :
        nqframes           = quatframesperbone[ii]
        if nqframes == 0 :
            continue

        fidtxt.write( str(ii-1) + ' ' + bonenames[ii] + '  quaternion data and Milkshape euler angles\n' )
        for jj in range( nqframes ) :
            fidtxt.write( formatfloat( quatfloats[iquat+0], 12, 10 ) + ' ' )
            fidtxt.write( formatfloat( quatfloats[iquat+1], 12, 10 ) + ' ' )
            fidtxt.write( formatfloat( quatfloats[iquat+2], 12, 10 ) + ' ' )
            fidtxt.write( formatfloat( quatfloats[iquat+3], 12, 10 ) + '     ' )
            iquat          = iquat + 4
            fidtxt.write( formatfloat( 180.0 * eulers[ieuler+0] / math.pi, 14, 10 ) + ' ' )
            fidtxt.write( formatfloat( 180.0 * eulers[ieuler+1] / math.pi, 14, 10 ) + ' ' )
            fidtxt.write( formatfloat( 180.0 * eulers[ieuler+2] / math.pi, 14, 10 ) + '\n' )
            ieuler         = ieuler + 3

    # Do animfloats (bone_pelvis movements followed by deltas for other bones).
    ianim                  = 0
    for ii in range( nbones ) :
        naframes           = animframesperbone[ii]
        if naframes == 0 :
            continue

        fidtxt.write( str(ii-1) + ' ' + bonenames[ii] + '  animation data and deltas\n' )
        for jj in range( naframes ) :
            fidtxt.write( formatfloat( animfloats[ianim+0], 12, 10 ) + ' ' )
            fidtxt.write( formatfloat( animfloats[ianim+1], 12, 10 ) + ' ' )
            fidtxt.write( formatfloat( animfloats[ianim+2], 12, 10 ) + '\n' )
            ianim          = ianim + 3

    # Do posefloats (note that Scene_Root is included here).
    ipose                  = 0
    fidtxt.write( '0    skeleton pose data, all bones including Scene_Root\n' )
    for ii in range( nbones ) :
        npframes           = onesperbone[ii]
        if npframes == 0 :
            continue

        for jj in range( npframes ) :
            fidtxt.write( formatfloat( posefloats[ipose+0], 12, 10 ) + ' ' )
            fidtxt.write( formatfloat( posefloats[ipose+1], 12, 10 ) + ' ' )
            fidtxt.write( formatfloat( posefloats[ipose+2], 12, 10 ) + '\n' )
            ipose          = ipose + 3

    return


# -----------------------------------------------------------------------------------
#    Reads binary full .cas file footer. Also writes it to an ASCII txt file if     |
# fidtxt is not empty.  There are four footer types we have to contend with:        |
#                                                                                   |
# (1) No footer at all.  Do a tentative read and if you get back empty string ''    |
#     return an empty list to signal this.                                          |
#                                                                                   |
# (2) Regular footer of 192 bytes.  This is our standard footer with regular        |
#     fields.                                                                       |
#                                                                                   |
# (3) Short footer by 12 bytes.  The final three ints, 12 12 0, are missing so the  |
#     footer is 180 bytes long.  This is fairly common.  Just make int_vec2 into    |
#     an empty list and take care not to try to write it out.                       |
#                                                                                   |
# (4) Long footer.  This occurs with fs_horse directory .cas files.  Indicated by   |
#     int_104 actually being equal to 170.  There's a lot of extra float fields to  |
#     contend with here so the footerdata list gets more complicated.               |
#                                                                                   |
# -----------------------------------------------------------------------------------
def readandwritecasfooter( fidcas, fidtxt, flags ) :

    # HORSEFLAG is used for doing long footers in fs_horse.
    HORSEFLAG              = False
    CAMELFLAG              = False

    # This is the return value.
    footerdata             = []

    # Check if text output is desired.
    if fidtxt == [] :
        WRITECASTXTFILE    = False
    else :
        WRITECASTXTFILE    = True

    # Test for anomalous cas file.
    if iseof( fidcas ) == True :
        print 'ANOMALOUS CAS FILE DETECTED: NO FOOTER DATA AT ALL...' 
        if ( WRITECASTXTFILE == True ) & ( flags.isdir == 1 ) :
            fidtxt.write( 'ANOMALOUS CAS FILE DETECTED: NO FOOTER DATA AT ALL...\n' )
        return footerdata  

    # Read the ints up to the CaozAttrib string, then read the string.
    int_104                = getuint(   fidcas )

    # Check to see if int_104 is equal to 170.  If so, we are doing a long fs_horse footer
    # with lots of extra float data.
    if int_104 == 170 :
        HORSEFLAG          = True

    # Check to see if int_104 is equal to 18.  If so, we are doing a very short camel footer.
    if int_104 == 18 :
        CAMELFLAG          = True

    # If CAMELFLAG is True, process it now because it's short and we can return it and be done.
    if CAMELFLAG == True :
        int_one1           = getuint(   fidcas )
        int_zero1          = getuint(   fidcas )
        int_zero2          = getuint(   fidcas )
        short_zero1        = getushort( fidcas )
        int_vec1           = array.array( 'I' )
        int_vec1.fromfile( fidcas, 4 )
        int_vec2           = array.array( 'I' )
        int_vec2.fromfile( fidcas, 4 )
        int_vec3           = array.array( 'I' )
        int_vec3.fromfile( fidcas, 4 )
        int_vec4           = array.array( 'I' )
        int_vec4.fromfile( fidcas, 4 )
        # MAYBE read 3 ints if not a bad file.
        if iseof( fidcas ) == True :
            if ( WRITECASTXTFILE == True ) & ( flags.footer == 1 ) & ( flags.isdir == 1 ) :
                fidtxt.write( 'ANOMALOUS CAS FILE DETECTED: BAD FOOTER DATA...MISSING 24 BYTES, THE INTS 12 5 0  12 12 0\n' )
            int_vec5       = []
        else :
            int_vec5       = array.array( 'I' )
            int_vec5.fromfile( fidcas, 3 )
        footerdata.append( int_104 )
        footerdata.append( int_one1 )
        footerdata.append( int_zero1 )
        footerdata.append( int_zero2 )
        footerdata.append( short_zero1 )
        footerdata.append( int_vec1 )
        footerdata.append( int_vec2 )
        footerdata.append( int_vec3 )
        footerdata.append( int_vec4 )
        footerdata.append( int_vec5 )

        # Write the footer as for a summary file if flags.isdir == 1.
        if ( WRITECASTXTFILE == True ) & ( flags.footer == 1 ) & ( flags.isdir == 1 ) :
            bytesum        = int_104 + int_vec1[0] + int_vec2[0] + int_vec3[0] + int_vec4[0] 
            if int_vec5 != [] :
                bytesum    = bytesum + int_vec5[0]
            fidtxt.write( str(int_104).ljust(3) + ' ' + str(int_one1).ljust(2) + ' ' + str(int_zero1).ljust(2) + ' ' + str(int_zero2).ljust(2) + ' ' + str(short_zero1).ljust(2) + '\n' )
            for ii in range( len(int_vec1) ):
                fidtxt.write( str(int_vec1[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )
            for ii in range( len(int_vec2) ):
                fidtxt.write( str(int_vec2[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )
            for ii in range( len(int_vec3) ):
                fidtxt.write( str(int_vec3[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )
            for ii in range( len(int_vec4) ):
                fidtxt.write( str(int_vec4[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )
            for ii in range( len(int_vec5) ):
                fidtxt.write( str(int_vec5[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )
            fidtxt.write( '-------\n' )
            fidtxt.write( str( bytesum ).ljust(4) + '\n' )

        # Write the footer as one line for a cas to text conversion.
        if ( WRITECASTXTFILE == True ) & ( flags.footer == 1 ) & ( flags.isdir == 0 ) :
            fidtxt.write( str(int_104).ljust(3) + ' ' + str(int_one1).ljust(2) + ' ' + str(int_zero1).ljust(2) + ' ' + str(int_zero2).ljust(2) + ' ' + str(short_zero1).ljust(2) + ' ' )

            for ii in range( len(int_vec1) ):
                fidtxt.write( str(int_vec1[ii]).ljust(2) + ' ' )
            for ii in range( len(int_vec2) ):
                fidtxt.write( str(int_vec2[ii]).ljust(2) + ' ' )
            for ii in range( len(int_vec3) ):
                fidtxt.write( str(int_vec3[ii]).ljust(2) + ' ' )
            for ii in range( len(int_vec4) ):
                fidtxt.write( str(int_vec4[ii]).ljust(2) + ' ' )
            for ii in range( len(int_vec5) ):
                fidtxt.write( str(int_vec5[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )
        
        return footerdata

    # Continue regular processing.
    int_one1               = getuint(   fidcas )
    int_one2               = getuint(   fidcas )
    
    # A check for an old style variant.
    if ( int_104 == 16 ) & ( int_one1 == 1 ) & ( int_one2 == 0 ) :
        int_zero1          = getuint(   fidcas )
        int_vec1           = array.array( 'I' )
        int_vec1.fromfile( fidcas, 4 )
        int_vec2           = array.array( 'I' )
        int_vec2.fromfile( fidcas, 4 )
        int_vec3           = array.array( 'I' )
        int_vec3.fromfile( fidcas, 4 )
        int_vec4           = array.array( 'I' )
        int_vec4.fromfile( fidcas, 4 )

        # Write the footer as for a summary file if flags.isdir == 1.
        if ( WRITECASTXTFILE == True ) & ( flags.footer == 1 ) & ( flags.isdir == 1 ) :
            bytesum        = int_104 + int_vec1[0] + int_vec2[0] + int_vec3[0] + int_vec4[0] 
            fidtxt.write( str(int_104).ljust(3) + ' ' + str(int_one1).ljust(2) + ' ' + str(int_one2).ljust(2) + ' ' + str(int_zero1).ljust(2) + '\n' )
            for ii in range( len(int_vec1) ):
                fidtxt.write( str(int_vec1[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )
            for ii in range( len(int_vec2) ):
                fidtxt.write( str(int_vec2[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )
            for ii in range( len(int_vec3) ):
                fidtxt.write( str(int_vec3[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )
            for ii in range( len(int_vec4) ):
                fidtxt.write( str(int_vec4[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )
            fidtxt.write( '-------\n' )
            fidtxt.write( str( bytesum ).ljust(4) + '\n' )

        # Write the footer as one line for a cas to text conversion.
        if ( WRITECASTXTFILE == True ) & ( flags.footer == 1 ) & ( flags.isdir == 0 ) :
            fidtxt.write( str(int_104).ljust(3) + ' ' + str(int_one1).ljust(2) + ' ' + str(int_one2).ljust(2) + ' ' + str(int_zero1).ljust(2) + ' ' )

            for ii in range( len(int_vec1) ):
                fidtxt.write( str(int_vec1[ii]).ljust(2) + ' ' )
            for ii in range( len(int_vec2) ):
                fidtxt.write( str(int_vec2[ii]).ljust(2) + ' ' )
            for ii in range( len(int_vec3) ):
                fidtxt.write( str(int_vec3[ii]).ljust(2) + ' ' )
            for ii in range( len(int_vec4) ):
                fidtxt.write( str(int_vec4[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )

        footerdata.append( int_104 )                       # Index 0.
        footerdata.append( int_one1 )                      # Index 1.
        footerdata.append( int_one2 )                      # Index 2.
        footerdata.append( int_zero1 )                     # Index 3.
        footerdata.append( int_vec1 )                      # Index 4.
        footerdata.append( int_vec2 )                      # Index 5.
        footerdata.append( int_vec3 )                      # Index 6.
        footerdata.append( int_vec4 )                      # Index 7.
        return footerdata
        
    # Back to regular processing.
    nch                    = getuint(   fidcas )
    AttribString           = getstring( fidcas, nch-1 )
    dummy                  = getubyte(  fidcas )           # Null termination byte.


    # Now read an int and a byte, then two ints and a byte.
    int_one3               = getuint(   fidcas )
    byte_zero1             = getubyte(  fidcas )
    int_one4               = getuint(   fidcas )
    int_zero1              = getuint(   fidcas )
    byte_zero2             = getubyte(  fidcas )

    # Now read 7 floats.
    float_vec1             = array.array( 'f' )
    float_vec1.fromfile( fidcas, 7 )

    # Now read an int and a short.
    int_zero2              = getuint(   fidcas )
    short_zero1            = getushort( fidcas )

    # Now read a -1 int and another int zero.
    int_minus1             = getint(    fidcas )
    int_zero3              = getuint(   fidcas )

    # Save off the common data.
    footerdata.append( int_104 )                           # Index 0.
    footerdata.append( int_one1 )                          # Index 1.
    footerdata.append( int_one2 )                          # Index 2.
    footerdata.append( AttribString )                      # Index 3. (Remember the null terminator byte.)
    footerdata.append( int_one3 )                          # Index 4.
    footerdata.append( byte_zero1 )                        # Index 5.
    footerdata.append( int_one4 )                          # Index 6.
    footerdata.append( int_zero1 )                         # Index 7.
    footerdata.append( byte_zero2 )                        # Index 8.
                                             
    footerdata.append( float_vec1 )                        # Index 9.
                                             
    footerdata.append( int_zero2 )                         # Index 10.
    footerdata.append( short_zero1 )                       # Index 11.
    footerdata.append( int_minus1 )                        # Index 12.
    footerdata.append( int_zero3 )                         # Index 13.

    # Write the common data to the txt file if desired.  If flags.isdir == 1
    if ( WRITECASTXTFILE == True ) & ( flags.footer == 1 ) & ( flags.isdir == 1 ) :                                                                                                                                                                       
        fidtxt.write( str(int_104).ljust(2) + ' ' + str(int_one1).ljust(2) + ' ' + str(int_one2).ljust(2) + ' ' + AttribString + '   ' )                                                                
        fidtxt.write( str(int_one3).ljust(2) + ' ' + str(byte_zero1).ljust(2) + ' ' + str(int_one4).ljust(2) + ' ' + str(int_zero1).ljust(2) + ' ' + str(byte_zero2).ljust(2) + '\n' )                 
                                                                                                                                                                                                       
        fidtxt.write( '          ' )
        # 7 floats here.                                                                                                                                                                               
        for ii in range( len(float_vec1) ) :                                                                                                                                                           
            fidtxt.write( formatfloat( float_vec1[ii], 7, 5 ) + ' ' )                                                                                                                                      
                                                                                                                                                                                                       
        fidtxt.write( str(int_zero2).ljust(2) + ' ' + str(short_zero1).ljust(2) + ' ' )                                                                                                                
        fidtxt.write( str(int_minus1).ljust(2) + ' ' + str(int_zero3).ljust(2) + ' ' )                                                                                                                

    # Write the common data to the txt file if desired.  If flags.isdir == 0 write in a single line.
    if ( WRITECASTXTFILE == True ) & ( flags.footer == 1 ) & ( flags.isdir == 0 ) :                                                                                                                                                                       
        fidtxt.write( str(int_104).ljust(2) + ' ' + str(int_one1).ljust(2) + ' ' + str(int_one2).ljust(2) + ' ' + AttribString + '   ' )                                                                
        fidtxt.write( str(int_one3).ljust(2) + ' ' + str(byte_zero1).ljust(2) + ' ' + str(int_one4).ljust(2) + ' ' + str(int_zero1).ljust(2) + ' ' + str(byte_zero2).ljust(2) + ' ' )                 
                                                                                                                                                                                                       
        # 7 floats here.                                                                                                                                                                               
        for ii in range( len(float_vec1) ) :                                                                                                                                                           
            fidtxt.write( formatfloat( float_vec1[ii], 7, 5 ) + ' ' )                                                                                                                                      
                                                                                                                                                                                                       
        fidtxt.write( str(int_zero2).ljust(2) + ' ' + str(short_zero1).ljust(2) + ' ' )                                                                                                                
        fidtxt.write( str(int_minus1).ljust(2) + ' ' + str(int_zero3).ljust(2) + ' ' )                                                                                                                

    # Must split processing depending on if its a fs_horse file or not.
    if HORSEFLAG == False :
        short_zero2        = getushort( fidcas )
        int_something      = getuint(   fidcas )

        # Now read a long bit of 19 ints.
        int_vec1           = array.array( 'I' )
        int_vec1.fromfile( fidcas, 4 )
        int_vec2           = array.array( 'I' )
        int_vec2.fromfile( fidcas, 4 )
        int_vec3           = array.array( 'I' )
        int_vec3.fromfile( fidcas, 4 )
        int_vec4           = array.array( 'I' )
        int_vec4.fromfile( fidcas, 4 )
        # MAYBE read 3 ints if not a bad file.
        if iseof( fidcas ) == True :
            if ( WRITECASTXTFILE == True ) & ( flags.footer == 1 ) & ( flags.isdir == 1 ) :
                fidtxt.write( 'ANOMALOUS CAS FILE DETECTED: BAD FOOTER DATA...MISSING 24 BYTES, THE INTS 12 5 0  12 12 0\n' )
            int_vec5       = []
        else :
            int_vec5       = array.array( 'I' )
            int_vec5.fromfile( fidcas, 3 )

        # MAYBE read 3 ints if not a bad file.
        if iseof( fidcas ) == True :
            if ( WRITECASTXTFILE == True ) & ( flags.footer == 1 ) & ( flags.isdir == 1 ) :
                fidtxt.write( 'ANOMALOUS CAS FILE DETECTED: BAD FOOTER DATA...MISSING 12 BYTES, THE INTS 12 12 0\n' )
            int_vec6       = []
        else :
            int_vec6       = array.array( 'I' )
            int_vec6.fromfile( fidcas, 3 )

        # Save off the data pertaining to non fs_horse.
        footerdata.append( short_zero2 )                   # Index 14.
        footerdata.append( int_something )                 # Index 15.
        footerdata.append( int_vec1 )                      # Index 16.
        footerdata.append( int_vec2 )                      # Index 17.
        footerdata.append( int_vec3 )                      # Index 18.
        footerdata.append( int_vec4 )                      # Index 19.
        footerdata.append( int_vec5 )                      # Index 20.
        footerdata.append( int_vec6 )                      # Index 21.

        # Write it to the txt file if desired. On separate lines if flags.isdir == 1.
        if ( WRITECASTXTFILE == True ) & ( flags.footer == 1 ) & ( flags.isdir == 1 ) :                                                                                                                                                                       
            bytesum        = int_104 + int_vec1[0] + int_vec2[0] + int_vec3[0] + int_vec4[0] 
            if int_vec5 != [] :
                bytesum    = bytesum + int_vec5[0]
            if int_vec6 != [] :
                bytesum    = bytesum + int_vec6[0]

            fidtxt.write( '        ' + str(short_zero2).ljust(2) + ' ' + str(int_something).ljust(2) + '\n' )
        
            for ii in range( len(int_vec1) ):
                fidtxt.write( str(int_vec1[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )
        
            for ii in range( len(int_vec2) ):
                fidtxt.write( str(int_vec2[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )
        
            for ii in range( len(int_vec3) ):
                fidtxt.write( str(int_vec3[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )
        
            for ii in range( len(int_vec4) ):
                fidtxt.write( str(int_vec4[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )
        
            if int_vec5 != [] :
                for ii in range( len(int_vec5) ):
                    fidtxt.write( str(int_vec5[ii]).ljust(2) + ' ' )
                fidtxt.write( '\n' )
        
            if int_vec6 != [] :
                for ii in range( len(int_vec6) ):
                    fidtxt.write( str(int_vec6[ii]).ljust(2) + ' ' )
                fidtxt.write( '\n' )

            fidtxt.write( '-------\n' )
            fidtxt.write( str( bytesum ).ljust(4) + '\n' )

        # Write it to the txt file if desired. All on one line if flags.isdir == 0.
        if ( WRITECASTXTFILE == True ) & ( flags.footer == 1 ) & ( flags.isdir == 0 ) :                                                                                                                                                                       

            fidtxt.write( '        ' + str(short_zero2).ljust(2) + ' ' + str(int_something).ljust(2) + ' ' )
        
            for ii in range( len(int_vec1) ):
                fidtxt.write( str(int_vec1[ii]).ljust(2) + ' ' )
        
            for ii in range( len(int_vec2) ):
                fidtxt.write( str(int_vec2[ii]).ljust(2) + ' ' )
        
            for ii in range( len(int_vec3) ):
                fidtxt.write( str(int_vec3[ii]).ljust(2) + ' ' )
        
            for ii in range( len(int_vec4) ):
                fidtxt.write( str(int_vec4[ii]).ljust(2) + ' ' )
        
            for ii in range( len(int_vec5) ):
                fidtxt.write( str(int_vec5[ii]).ljust(2) + ' ' )
        
            if int_vec6 != [] :
                for ii in range( len(int_vec6) ):
                    fidtxt.write( str(int_vec6[ii]).ljust(2) + ' ' )
        
            fidtxt.write( '\n' )
    else :
        # Doing the horsies. 
        nch                = getuint(   fidcas )           # Number of chars plus null byte for plane string.
        string2            = getstring( fidcas, nch-1 )
        dummy              = getubyte(  fidcas )           # Get the null terminator.
        int_one5           = getuint(   fidcas )
        byte_zero3         = getubyte(  fidcas )
        int_one6           = getuint(   fidcas )
        int_zero4          = getuint(   fidcas )
        byte_zero4         = getubyte(  fidcas )
        float_vec2         = array.array( 'f' )
        float_vec2.fromfile( fidcas, 7 )
        int_vec1           = array.array( 'I' )
        int_vec1.fromfile( fidcas, 5 )
        int_vec2           = array.array( 'I' )
        int_vec2.fromfile( fidcas, 4 )
        int_vec3           = array.array( 'I' )
        int_vec3.fromfile( fidcas, 4 )
        int_vec4           = array.array( 'I' )
        int_vec4.fromfile( fidcas, 4 )
        int_vec5           = array.array( 'I' )
        int_vec5.fromfile( fidcas, 4 )
        int_count          = getuint(   fidcas )           # Byte count of what is coming.
        int_five           = getuint(   fidcas )
        int_one7           = getuint(   fidcas )
        int_zero5          = getuint(   fidcas )
        float_vec3         = array.array( 'f' )
        float_vec3.fromfile( fidcas, 7 )
        int_vec6           = array.array( 'I' )
        int_vec6.fromfile( fidcas, 7 )
        byte_zero5         = getubyte(  fidcas )
        int_vec7           = array.array( 'I' )
        int_vec7.fromfile( fidcas, 3 )

        # Save off the data.
        footerdata.append( string2 )                       # Index 14.
        footerdata.append( int_one5 )                      # Index 15.
        footerdata.append( byte_zero3 )                    # Index 16.
        footerdata.append( int_one6 )                      # Index 17.
        footerdata.append( int_zero4 )                     # Index 18.
        footerdata.append( byte_zero4 )                    # Index 19.
        footerdata.append( float_vec2 )                    # Index 20.
        footerdata.append( int_vec1 )                      # Index 21.
        footerdata.append( int_vec2 )                      # Index 22.
        footerdata.append( int_vec3 )                      # Index 23.
        footerdata.append( int_vec4 )                      # Index 24.
        footerdata.append( int_vec5 )                      # Index 25.
        footerdata.append( int_count )                     # Index 26.
        footerdata.append( int_five )                      # Index 27.
        footerdata.append( int_one7 )                      # Index 28.
        footerdata.append( int_zero5 )                     # Index 29.
        footerdata.append( float_vec3 )                    # Index 30.
        footerdata.append( int_vec6 )                      # Index 31.
        footerdata.append( byte_zero5 )                    # Index 32.
        footerdata.append( int_vec7 )                      # Index 33.

        # Write it to the txt file if desired. Split on multiple lines if flags.isdir == 1.
        if ( WRITECASTXTFILE == True ) & ( flags.footer == 1 ) & ( flags.isdir == 1 ) :                                                                                                                                                                       
            bytesum        = int_104 + int_vec2[0] + int_vec3[0] + int_vec4[0] + int_vec5[0] + int_count + int_vec7[0]
            fidtxt.write( '          ' + string2 + ' ' + str(int_one5).ljust(2) + ' ' + str(byte_zero3).ljust(2) + ' ' + str(int_one6).ljust(2) + ' ' + str(int_zero4).ljust(2) + ' ' + str(byte_zero4).ljust(2) + '\n' )
        
            fidtxt.write( '          ' )
            for ii in range( len(float_vec2) ):
                fidtxt.write( formatfloat(float_vec2[ii],7,5) + '  ' )

            for ii in range( len(int_vec1) ):
                fidtxt.write( str(int_vec1[ii]).ljust(2) + ' ' )

            fidtxt.write( '\n' )

            for ii in range( len(int_vec2) ):
                fidtxt.write( str(int_vec2[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )

            for ii in range( len(int_vec3) ):
                fidtxt.write( str(int_vec3[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )

            for ii in range( len(int_vec4) ):
                fidtxt.write( str(int_vec4[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )

            for ii in range( len(int_vec5) ):
                fidtxt.write( str(int_vec5[ii]).ljust(2) + ' ' )
            fidtxt.write( '\n' )

            fidtxt.write( str(int_count).ljust(2) + ' ' + str(int_five).ljust(2) + ' ' + str(int_one7).ljust(2) + ' ' + str(int_zero5).ljust(2) + ' ' )

            for ii in range( len(float_vec3) ):
                fidtxt.write( formatfloat(float_vec3[ii],5,3) + ' ' )
             
            for ii in range( len(int_vec6) ):
                fidtxt.write( str(int_vec6[ii]).ljust(2) + ' ' )

            fidtxt.write( '  ' + str(byte_zero5) + '\n' )
        
            for ii in range( len(int_vec7) ):
                fidtxt.write( str(int_vec7[ii]).ljust(2) + ' ' )
        
            fidtxt.write( '\n' )
            fidtxt.write( '-------\n' )
            fidtxt.write( str( bytesum ).ljust(4) + '\n' )

        # Write it to the txt file if desired. All on one line if flags.isdir == 0.
        if ( WRITECASTXTFILE == True ) & ( flags.footer == 1 ) & ( flags.isdir == 0 ) :                                                                                                                                                                       

            fidtxt.write( ' ' + string2 + ' ' + str(int_one5).ljust(2) + ' ' + str(byte_zero3).ljust(2) + ' ' + str(int_one6).ljust(2) + ' ' + str(int_zero4).ljust(2) + ' ' + str(byte_zero4).ljust(2) + ' ' )
        
            for ii in range( len(float_vec2) ):
                fidtxt.write( formatfloat(float_vec2[ii],7,5) + '  ' )

            for ii in range( len(int_vec1) ):
                fidtxt.write( str(int_vec1[ii]).ljust(2) + ' ' )

            for ii in range( len(int_vec2) ):
                fidtxt.write( str(int_vec2[ii]).ljust(2) + ' ' )

            for ii in range( len(int_vec3) ):
                fidtxt.write( str(int_vec3[ii]).ljust(2) + ' ' )

            for ii in range( len(int_vec4) ):
                fidtxt.write( str(int_vec4[ii]).ljust(2) + ' ' )

            for ii in range( len(int_vec5) ):
                fidtxt.write( str(int_vec5[ii]).ljust(2) + ' ' )

            fidtxt.write( str(int_count).ljust(2) + ' ' + str(int_five).ljust(2) + ' ' + str(int_one7).ljust(2) + ' ' + str(int_zero5).ljust(2) + ' ' )

            for ii in range( len(float_vec3) ):
                fidtxt.write( formatfloat(float_vec3[ii],5,3) + ' ' )
             
            for ii in range( len(int_vec6) ):
                fidtxt.write( str(int_vec6[ii]).ljust(2) + ' ' )

            fidtxt.write( '  ' + str(byte_zero5) + ' ' )
        
            for ii in range( len(int_vec7) ):
                fidtxt.write( str(int_vec7[ii]).ljust(2) + ' ' )
        
            fidtxt.write( '\n' )
        
        
    return footerdata

# -----------------------------------------------------------------------------------
#    Reads the resource chunk header.                                               |
# -----------------------------------------------------------------------------------
def readresourcechunkheader( fidcas ) :
    chunkdata              = []

    chunkstr               = str( getuint( fidcas ) )                   # This is the 2nd chunk length.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )  # This is 1.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )  # This is 2.
    nummeshes              = 1

    # Check for the AttribNode variant.
    numchars               = getuint( fidcas )
    if numchars == 26 :
        chunkstr           = chunkstr + ' ' + str( numchars )
        chunkstr           = chunkstr + ' ' + getstring( fidcas, 25 )
        getubyte( fidcas )
        chunkstr           = chunkstr + ' ' + str( getuint( fidcas ) )  # This is 1.
        getubyte( fidcas )
        chunkstr           = chunkstr + ' ' + str( getuint( fidcas ) )  # This is 1.
        getubyte( fidcas )
        # Nine floats?
        chunkstr           = chunkstr + ' ' + str( getfloat( fidcas ) )
        chunkstr           = chunkstr + ' ' + str( getfloat( fidcas ) )
        chunkstr           = chunkstr + ' ' + str( getfloat( fidcas ) )
        chunkstr           = chunkstr + ' ' + str( getfloat( fidcas ) )
        chunkstr           = chunkstr + ' ' + str( getfloat( fidcas ) )
        chunkstr           = chunkstr + ' ' + str( getfloat( fidcas ) )
        chunkstr           = chunkstr + ' ' + str( getfloat( fidcas ) )
        chunkstr           = chunkstr + ' ' + str( getfloat( fidcas ) )
        chunkstr           = chunkstr + ' ' + str( getfloat( fidcas ) )
        # 1 Short.
        chunkstr           = chunkstr + ' ' + str( getushort( fidcas ) )
        # 1 -1 int.
        chunkstr           = chunkstr + ' ' + str( getint( fidcas ) )
        # 1 0 int.
        chunkstr           = chunkstr + ' ' + str( getuint( fidcas ) )   # Nineteen entries.
    else:
        # Have to back up.
        fidcas.seek( -4, 1 )               


    chunkdata.append( nummeshes )
    chunkdata.append( chunkstr )

    return chunkdata

# -----------------------------------------------------------------------------------
#    Reads the navy chunk header.                                                   |
# -----------------------------------------------------------------------------------
def readnavychunkheader( fidcas ) :
    chunkdata              = []

    chunkstr               = str( getuint( fidcas ) )                   # Index 0, the 2nd chunk length.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )  # Index 1.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )  # Index 2.
    nch                    = getuint( fidcas )                          # Num chars.
    attribstring           = getstring( fidcas, nch-1 )
    getubyte( fidcas )
    chunkstr               = chunkstr + ' ' + str( nch )                # Index 3.
    chunkstr               = chunkstr + ' ' + attribstring              # Index 4.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )  # Index 5.
    getubyte( fidcas )
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )  # Index 6.
    getubyte( fidcas )
    float_vec              = array.array( 'f' )
    float_vec.fromfile( fidcas, 9 )
    for ii in range( 9 ) :
        chunkstr           = chunkstr + ' ' + str( float_vec[ii] )      # Index 7-15.
    chunkstr               = chunkstr + ' ' + str( getushort( fidcas ) )# Index 16.
    chunkstr               = chunkstr + ' ' + str( getint( fidcas ) )   # Index 17.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )  # Index 18.
    nummeshes              = 1

    chunkdata.append( nummeshes )
    chunkdata.append( chunkstr )

    return chunkdata

# -----------------------------------------------------------------------------------
#    Reads the regular chunk header.                                                |
# -----------------------------------------------------------------------------------
def readchunkheader( fidcas ) :
    chunkdata              = []

    chunkstr               = str( getuint( fidcas ) )                     # This is 18, the short chunk.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )    # This is 1.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )    # This is 0.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )    # This is 0.
    chunkstr               = chunkstr + ' ' + str( getushort( fidcas ) )  # This is 0.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )    # This is chunk offset.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )    # This is 2.
    nummeshes              = getuint( fidcas )
    chunkstr               = chunkstr + ' ' + str( nummeshes )

    chunkdata.append( nummeshes )
    chunkdata.append( chunkstr )

    return chunkdata

# -----------------------------------------------------------------------------------
#    Reads the attribnode chunk header for regular units.                           |
# -----------------------------------------------------------------------------------
def readattribnodechunkheader( fidcas ) :
    chunkdata              = []

    chunkstr               = str( getuint( fidcas ) )                     # Index 0, this is the 104 chunk length.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )    # Index 1.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )    # Index 2.
    nch                    = getuint( fidcas )
    attribnode             = getstring( fidcas, nch-1 )
    dummy                  = getubyte( fidcas )
    chunkstr               = chunkstr + ' ' + str( nch )                  # Index 3.
    chunkstr               = chunkstr + ' ' + attribnode                  # Index 4.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )    # Index 5.
    dummy                  = getubyte( fidcas )
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )    # Index 6.
    dummy                  = getubyte( fidcas )
    float_vec              = array.array( 'f' )
    float_vec.fromfile( fidcas, 9 )
    for ii in range( 9 ):
        chunkstr           = chunkstr + ' ' + str( float_vec[ii] )        # Index 7-15.
    chunkstr               = chunkstr + ' ' + str( getushort( fidcas ) )  # Index 16.
    chunkstr               = chunkstr + ' ' + str( getint( fidcas ) )     # Index 17, this is -1.
    chunkstr               = chunkstr + ' ' + str( getushort( fidcas ) )  # Index 18.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )    # Index 19, this is 0.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )    # Index 20, this is 1.        
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )    # Index 21, this is chunk size.
    chunkstr               = chunkstr + ' ' + str( getuint( fidcas ) )    # Index 22, this is 2.
    nummeshes              = getuint( fidcas )
    chunkstr               = chunkstr + ' ' + str( nummeshes )            # Index 23, this is number of meshes.

    chunkdata.append( nummeshes )
    chunkdata.append( chunkstr )

    return chunkdata

# -----------------------------------------------------------------------------------
#    Reads the middle part of a cas mesh file between anim data and the mesh data.  |
# -----------------------------------------------------------------------------------
def readandwritecasmeshmiddle( fidcas, fidtxt, FLAGRESOURCE, FLAGNAVY ) :

    # This is the return value.
    middledata             = []
    middlemeshdata         = []

    # Check if text output is desired.
    if fidtxt == [] :
        WRITECASTXTFILE    = False
    else :
        WRITECASTXTFILE    = True

    # Test for anomalous cas file.
    if iseof( fidcas ) == True :
        print 'ANOMALOUS CAS FILE DETECTED: NO FOOTER DATA AT ALL...' 
        return []

    # Decide how to read the header on this part.
    if FLAGNAVY == True :
        chunkdata          = readnavychunkheader( fidcas )
    elif FLAGRESOURCE == True :
        chunkdata          = readresourcechunkheader( fidcas )
    else :
        chunklength        = getuint( fidcas )
        print( 'chunklength = ' + str( chunklength ) )
        fidcas.seek( -4, 1 )
        if chunklength == 104 :
            chunkdata      = readattribnodechunkheader( fidcas )
        else:
            chunkdata      = readchunkheader( fidcas )

    nummeshes              = int( chunkdata[0] )
    chunkstr               = chunkdata[1]
    print( 'nummeshes = ' + str( nummeshes ) )
    print( 'chunkstr  = ' + chunkstr )

    groupnames             = []
    grouptris              = []
    groupmatId             = []
    groupindex             = []
    groupcomments          = []

    pos                    = fidcas.tell()
    print( 'tell says ' + str( pos ) )
    # Now read nch, mesh names, and a null byte.
    nch                    = getuint(   fidcas )
    meshname               = getstring( fidcas, nch-1 )
    dummy                  = getubyte(  fidcas )           # Null termination byte.
    groupnames.append(meshname ) 

    comment                = str( getuint( fidcas ) )
    dummy                  = getubyte(  fidcas )           # Null termination byte.
    if ( FLAGRESOURCE == True ) or ( FLAGNAVY == True ) :
        comment            = comment + ' ' + str( getuint( fidcas ) )
        getubyte( fidcas )
        comment            = comment + ' ' + str( getuint( fidcas ) )

    # Now read seven floats..
    float_vec1             = array.array( 'f' )
    float_vec1.fromfile( fidcas, 7 )
    for ii in range( 7 ) :
        comment            = comment + ' ' + str( float_vec1[ii] )

    groupcomments.append( comment )

    # Now read numverts, numfaces, flagTVerts, flagVColors.
    pos                    = fidcas.tell()
    print( 'tell says ' + str( pos ) )
    numverts               = getushort( fidcas )
    numfaces               = getushort( fidcas )
    flagTVerts             = getubyte(  fidcas )
    flagVColors            = getubyte(  fidcas )

    print( "numverts = " + str( numverts ) + ", numfaces = " + str( numfaces ) + ", flagTVerts = " + str( flagTVerts ) + ", flagVColors = " + str( flagVColors ) )

    # Get bone assignments.
    if ( FLAGRESOURCE == True ) or ( FLAGNAVY == True ) :
        boneIds            = array.array( 'i' )
        for ii in range( numverts ) :
            boneIds.append( -1 )
    else:
        boneIds            = array.array( 'i' )
        boneIds.fromfile( fidcas, numverts )

    # Get vertices.
    verts                  = array.array( 'f' )
    verts.fromfile( fidcas, 3*numverts )

    # Get normals. 
    normals                = array.array( 'f' )
    normals.fromfile( fidcas, 3*numverts )

    # Get faces. 
    faces                  = array.array( 'H' )
    faces.fromfile( fidcas, 3*numfaces )
    triarr                 = array.array( 'H' )
    for ii in range( numfaces ) :
        groupindex.append( 0 )
        triarr.append( ii )
    grouptris.append( triarr )

    # Get texture Id.
    textureId              = getuint( fidcas )
    groupmatId.append( textureId )

    # uv texture vertices.
    if flagTVerts == 1 :
        tverts             = array.array( 'f' )
        tverts.fromfile( fidcas, 2*numverts )
    else:
        tverts             = []
    
    # Vertex colors.
    if flagVColors == 1 :
        vcolors            = array.array( 'b' )
        vcolors.fromfile( fidcas, 4*numverts )
    else:
        vcolors            = []

    # The terminating int 0.
    int_zero11         = getuint(  fidcas )


    for imesh in range( 1, nummeshes ) :

        # Now read nch, mesh names, and a null byte.
        nch                = getuint(   fidcas )
        meshname           = getstring( fidcas, nch-1 )
        dummy              = getubyte(  fidcas )           # Null termination byte.
        groupnames.append( meshname )
                           
        # Now a null byte and eight floats.
        comment            = str( getuint( fidcas ) )
        byte_zero1         = getubyte(  fidcas )
        float_vec1         = array.array( 'f' )
        float_vec1.fromfile( fidcas, 7 )
        for ii in range( 7 ) :
            comment        = comment + ' ' + str( float_vec1[ii] )

        groupcomments.append( comment )
                           
        # Now read numverts, numfaces, flagTVerts, flagVColors.
        numverts2          = getushort( fidcas )
        numfaces2          = getushort( fidcas )
        flagTVerts2        = getubyte(  fidcas )
        flagVColors2       = getubyte(  fidcas )

        print( "numverts2 = " + str( numverts2 ) + ", numfaces2 = " + str( numfaces2 ) + ", flagTVerts2 = " + str( flagTVerts2 ) + ", flagVColors2 = " + str( flagVColors2 ) )

        # Get bone assignments.
        boneIds2           = array.array( 'I' )
        boneIds2.fromfile( fidcas, numverts2 )
                           
        # Get vertices.    
        verts2             = array.array( 'f' )
        verts2.fromfile( fidcas, 3*numverts2 )
                           
        # Get normals.     
        normals2           = array.array( 'f' )
        normals2.fromfile( fidcas, 3*numverts2 )
                           
        # Get faces.       
        faces2              = array.array( 'H' )
        faces2.fromfile( fidcas, 3*numfaces2 )
        triarr             = array.array( 'H' )
        for ii in range( len(faces)/3, len(faces)/3+numfaces2 ) :
            groupindex.append( imesh )
            triarr.append( ii )
        grouptris.append( triarr )
                           
        # Get texture Id.
        textureId          = getuint( fidcas )
        groupmatId.append( textureId )

        # uv texture vertices.
        if flagTVerts2 == 1 :
            tverts2        = array.array( 'f' )
            tverts2.fromfile( fidcas, 2*numverts2 )
        else:
            tverts2        = []
        
        # Vertex colors.
        if flagVColors2 == 1 :
            vcolors2       = array.array( 'b' )
            vcolors2.fromfile( fidcas, 4*numverts2 )
        else:
            vcolors2       = []

        # The terminating int 0.
        int_zero11         = getuint(  fidcas )

        # Make big table of faces.  Remember to offset the vertex indices by current number of verts.
        nvcur              = len(verts)/3                 
        for ii in range( numfaces2 ) :
            faces.append( faces2[3*ii+0]+nvcur )
            faces.append( faces2[3*ii+1]+nvcur )
            faces.append( faces2[3*ii+2]+nvcur )

        # Make big table of verts, normals, tverts, and vcolors.
        for ii in range( numverts2 ) :
            boneIds.append( boneIds2[ii] )
            verts.append( verts2[3*ii+0] )
            verts.append( verts2[3*ii+1] )
            verts.append( verts2[3*ii+2] )
            normals.append( normals2[3*ii+0] )
            normals.append( normals2[3*ii+1] )
            normals.append( normals2[3*ii+2] )
            tverts.append( tverts2[2*ii+0] )
            tverts.append( tverts2[2*ii+1] )
            if ( flagVColors == 1 ) and ( flagVColors2 == 1 ) :
                vcolors.append( vcolors2[4*ii+0] )
                vcolors.append( vcolors2[4*ii+1] )
                vcolors.append( vcolors2[4*ii+2] )
                vcolors.append( vcolors2[4*ii+3] )




    # Now correct the 3D geometry by x -> -x.  Also the boneIds are too high by 1.
    for ii in range( len(verts)/3 ) :
        verts[3*ii] = -verts[3*ii]
        normals[3*ii] = -normals[3*ii]

    # Now flip two indices for the faces.
    for ii in range( len(faces)/3 ) :
        tmp        = faces[3*ii+1]
        faces[3*ii+1] = faces[3*ii+2]
        faces[3*ii+2] = tmp
               
    # Package return value.
    meshdata               = []
    meshdata.append( FLAGRESOURCE )                        # Index 0.
    meshdata.append( chunkstr )                            # Index 1.
    meshdata.append( boneIds )                             # Index 2.
    meshdata.append( verts )                               # Index 3.
    meshdata.append( normals )                             # Index 4.
    meshdata.append( faces )                               # Index 5.
    meshdata.append( textureId )                           # Index 6.
    meshdata.append( tverts )                              # Index 7.
    meshdata.append( vcolors )                             # Index 8.
    meshdata.append( groupnames )                          # Index 9.
    meshdata.append( grouptris )                           # Index 10.
    meshdata.append( groupmatId )                          # Index 11.
    meshdata.append( groupindex )                          # Index 12.
    meshdata.append( groupcomments )                       # Index 13.

    return meshdata


# -----------------------------------------------------------------------------------
#                            getcasmeshfooter()                                     |
# -----------------------------------------------------------------------------------
def readcasmeshfooter( fidcas, fidtxt, flags ):

    # Return value.
    footerdata             = []

    int_vec1               = array.array( 'I' )
    int_vec1.fromfile( fidcas, 13 )
    footerstr              = str( int_vec1[0] )                      # Index 0.
    for ii in range( 1, 13 ) :
        footerstr          = footerstr + ' ' + str( int_vec1[ii] )   # Index 1-12.

    int_footsize           = getuint(   fidcas )
    footerstr              = footerstr + ' ' + str( int_footsize )   # Index 13.
    

    int_vec2               = array.array( 'I' )
    int_vec2.fromfile( fidcas, 3 )
    for ii in range( 3 ) :
        footerstr          = footerstr + ' ' + str( int_vec2[ii] )   # Index 14-16.

    getubyte(  fidcas )

    # This weirdity is because the islamic_merchant has a space in its texture filename.
    nch                    = int_footsize-75
    tmpstring              = getstring( fidcas, nch )
    tokens                 = tmpstring.split()
    if len( tokens ) > 1 :
        texturefilestring  = tokens[0]
        for ii in range( 1, len( tokens ) ) :
            texturefilestring = texturefilestring + '%' + tokens[ii]
    else:
        texturefilestring  = tmpstring

    footerstr              = footerstr + ' ' + texturefilestring     # Index 17.

    getubyte(  fidcas )

    float_vec1             = array.array( 'f' )
    float_vec1.fromfile( fidcas, 14 )
    for ii in range( 14 ) :
        footerstr          = footerstr + ' ' + str( float_vec1[ii] ) # Index 18-31.
    
    lastbyte               = getubyte(  fidcas )
  
    footerdata.append( footerstr )                         # Index 0.
    
    return footerdata

# -----------------------------------------------------------------------------------
#                            getcasnavymeshfooter()                                 |
# -----------------------------------------------------------------------------------
def readcasnavymeshfooter( fidcas, fidtxt, flags ):

    # Return value.
    footerdata             = []

    footerstr              = str( getushort( fidcas ) )              # Index 0.

    int_vec1               = array.array( 'I' )
    int_vec1.fromfile( fidcas, 17 )
    for ii in range( 17 ) :
        footerstr          = footerstr + ' ' + str( int_vec1[ii] )   # Index 1-17.

    int_footsize           = getuint(   fidcas )
    footerstr              = footerstr + ' ' + str( int_footsize )   # Index 18.

    int_vec2               = array.array( 'I' )
    int_vec2.fromfile( fidcas, 3 )
    for ii in range( 3 ) :
        footerstr          = footerstr + ' ' + str( int_vec2[ii] )   # Index 19-21.

    getubyte(  fidcas )

    nch                    = int_footsize-75
    texturefilestring      = getstring( fidcas, nch )
    footerstr              = footerstr + ' ' + texturefilestring     # Index 22.

    getubyte(  fidcas )

    float_vec1             = array.array( 'f' )
    float_vec1.fromfile( fidcas, 14 )
    for ii in range( 14 ) :
        footerstr          = footerstr + ' ' + str( float_vec1[ii] ) # Index 23-36.

    getubyte(  fidcas )

    footerdata.append( footerstr )      

    return footerdata

# -----------------------------------------------------------------------------------
#                            getcasresourcemeshfooter()                             |
# -----------------------------------------------------------------------------------
def readcasresourcemeshfooter( fidcas, fidtxt, flags ):

    # Return value.
    nch                    = getuint( fidcas )                              # Index 0.
    footerstr              = str( nch )                 

    AttribString           = getstring( fidcas, nch-1 )                     # Index 1.
    dummy                  = getubyte(  fidcas )           # Null termination byte.
    footerstr              = footerstr + ' ' + AttribString              

    footerstr              = footerstr + ' ' + str( getuint( fidcas ) )     # Index 2.
    byte_zero1             = getubyte(  fidcas )
    footerstr              = footerstr + ' ' + str( getuint( fidcas ) )     # Index 3.
    byte_zero2             = getubyte(  fidcas )

    float_vec0             = array.array( 'f' )
    float_vec0.fromfile( fidcas, 9 )
    for ii in range( 9 ) :
        footerstr          = footerstr + ' ' + str( float_vec0[ii] )        # Index 4 through 12.

    footerstr              = footerstr + ' ' + str( getushort( fidcas ) )   # Index 13.
    footerstr              = footerstr + ' ' + str( getint( fidcas ) )      # Index 14.
    footerstr              = footerstr + ' ' + str( getushort( fidcas ) )   # Index 15.

    int_vec0               = array.array( 'I' )
    int_vec0.fromfile( fidcas, 18 )
    for ii in range( 18 ) :
        footerstr          = footerstr + ' ' + str( int_vec0[ii] )          # Index 16 through 33.

    footsize               = getuint( fidcas )                              # Index 34.
    nch                    = footsize - 75
    footerstr              = footerstr + ' ' + str( footsize )

    footerstr              = footerstr + ' ' + str( getint( fidcas ) )      # Index 35.
    footerstr              = footerstr + ' ' + str( getint( fidcas ) )      # Index 36.
    footerstr              = footerstr + ' ' + str( getint( fidcas ) )      # Index 37.
    getubyte( fidcas )
    texturefilename        = getstring( fidcas, nch )                       # Index 38.
    footerstr              = footerstr + ' ' + texturefilename
    byte_zero2             = getubyte(  fidcas )

    float_vec1             = array.array( 'f' )
    float_vec1.fromfile( fidcas, 14 )
    for ii in range( 14 ) :
        footerstr          = footerstr + ' ' + str( float_vec1[ii] )        # Index 39 through 52.
    
    lastbyte               = getubyte(  fidcas )
  
    footerdata             = []
    footerdata.append( footerstr )

    return footerdata

# -----------------------------------------------------------------------------------
#                            getcasvariantresourcemeshfooter()                      |
# -----------------------------------------------------------------------------------
def readcasvariantresourcemeshfooter( fidcas, fidtxt, flags ):

    # Return value.
    footerstr              = str( getushort( fidcas ) )                     # Index 0. 

    for ii in range( 17 ) :
        footerstr          = footerstr + ' ' + str( getuint( fidcas ) )     # Index 1 to 17.

    footsize               = getuint( fidcas )                              # Index 18.
    nch                    = footsize - 75
    footerstr              = footerstr + ' ' + str( footsize )

    footerstr              = footerstr + ' ' + str( getint( fidcas ) )      # Index 19.
    footerstr              = footerstr + ' ' + str( getint( fidcas ) )      # Index 20.
    footerstr              = footerstr + ' ' + str( getint( fidcas ) )      # Index 21.
    getubyte(  fidcas )

    texturefilename        = getstring( fidcas, nch )                       # Index 38.
    footerstr              = footerstr + ' ' + texturefilename
    getubyte(  fidcas )

    float_vec1             = array.array( 'f' )
    float_vec1.fromfile( fidcas, 14 )
    for ii in range( 14 ) :
        footerstr          = footerstr + ' ' + str( float_vec1[ii] )        # Index 39 through 52.
    
    lastbyte               = getubyte(  fidcas )
  
    footerdata             = []
    footerdata.append( footerstr )

    return footerdata


# -----------------------------------------------------------------------------------
#    Reads a binary full format .cas file and extracts all the information into the |
# list casfiledatalist which it returns.  This is my attempt at making the most     |
# general cas file reader to date.                                                  |
# -----------------------------------------------------------------------------------
def readcasfile( fncas, fntxt, flags ) :

    # If fntxt is empty we don't write out a txt file.
    if fntxt == [] :
        WRITECASTXTFILE    = False
    else :
        WRITECASTXTFILE    = True

    casfiledatalist        = []
    fidtxt                 = []

    fidcas                 = open( fncas, 'rb' )

    if ( WRITECASTXTFILE == True ) & ( flags.isdir == 1 ) :
        fidtxt             = open( fntxt, 'a' )
    elif ( WRITECASTXTFILE == True ) & ( flags.isdir == 0 ) :
        fidtxt             = open( fntxt, 'w' )

    if fidcas == -1 :
        print 'Failed to open file: ' + fnin 
        print 'Exiting from the function readcasfile in animationlibrary.py...'
        exit()

    if WRITECASTXTFILE == True :
        if fidtxt == -1 :
            print 'Failed to open file: ' + fntxt
            print 'Exiting from the function readcasfile in animationlibrary.py...'
            exit()

    # Allocate arrays for the data.
    quatfloats             = array.array( 'f' )
    animfloats             = array.array( 'f' )
    posefloats             = array.array( 'f' )

    # Reading the header of the full .cas file.
    nnavy                  = fncas.find( 'navy' )
    nresource              = fncas.find( 'resource' )
    nsymbol                = fncas.find( 'symbol' )
    headerdata             = readandwritecasheader( fidcas, fidtxt, flags ) 
    version_float          = headerdata[0]
    signaturebyte          = headerdata[12]                
    FLAGRESOURCE           = False
    FLAGNAVY               = False
    if ( signaturebyte == 99 ) or ( nresource > -1 ) or ( nsymbol > -1 ) :
        FLAGRESOURCE       = True
    if nnavy > -1 :
        FLAGNAVY           = True
    casfiledatalist.append( headerdata )                   # Index 0.

    # Read the file size sans header/footer and the zero int.
    filesizesans           = getuint( fidcas )
    int_zero               = getuint( fidcas )
    casfiledatalist.append( filesizesans )                 # Index 1.
    casfiledatalist.append( int_zero )                     # Index 2.
    if ( WRITECASTXTFILE == True ) & ( flags.filesize == 1 ) :
        string1            = str(filesizesans).ljust(3) + ' ' + str(int_zero).ljust(3) + '\n'
        fidtxt.write( string1 )

    # Read the hierarchytree.
    hierarchydata          = readandwritecashierarchytree( fidcas, fidtxt, version_float, flags ) 
    nbones                 = len( hierarchydata )
    casfiledatalist.append( hierarchydata )                # Index 3.

    # Read the time ticks data.
    timeticksdata          = readandwritecastimeticks( fidcas, fidtxt, version_float, flags ) 
    casfiledatalist.append( timeticksdata )                # Index 4.

    # Reading the bone section of the full .cas file.
    bonedata               = readandwritecasbonesection( fidcas, fidtxt, nbones, version_float, flags )   
    casfiledatalist.append( bonedata )                     # Index 5.
     
    # Must process the bonedata to get correct frame counts for irregular .cas files
    # like the flailing one.
    nquatframes            = 0
    nanimframes            = 0
    nposeframes            = 0
    quatframesperbone      = bonedata[1]
    animframesperbone      = bonedata[2]
    onesperbone            = bonedata[6]
    for ii in range( nbones ) :
        nquatframes        = nquatframes + quatframesperbone[ii]
        nanimframes        = nanimframes + animframesperbone[ii]
        nposeframes        = nposeframes + onesperbone[ii]

    # Get quaternion data.
    nquats                 = nquatframes * 4
    quatfloats.fromfile( fidcas, nquats )
    casfiledatalist.append( quatfloats )                   # Index 6.

    # Get anim data.
    nanims                 = nanimframes * 3
    animfloats.fromfile( fidcas, nanims )                  # Index 7.
    casfiledatalist.append( animfloats )

    # Get bone pose data (including Scene_Root so nbones = NBONES + 1).
    nposes                 = nposeframes * 3
    posefloats.fromfile( fidcas, nposes )   
    casfiledatalist.append( posefloats )                   # Index 8.

    # Compute the Euler angles for Milkshape.
    eulers                 = computeeulers( quatfloats )
    casfiledatalist.append( eulers )                       # Index 9.

    # Now we need to write out the data if text output is desired.
    if ( WRITECASTXTFILE == True ) & ( flags.alldata == 1 ) :
        writecasdatatotext( fidtxt, bonedata, quatfloats, animfloats, posefloats, eulers )

    # Read the mesh data.
    meshdata               = readandwritecasmeshmiddle( fidcas, fidtxt, FLAGRESOURCE, FLAGNAVY ) 

    # Here's the weird part.  The vertices are relative to the absolute bone
    # positions.  So we have to compute those from the posefloats.  We will need
    # the hierarchy data for this.  (It has what I call the parent_array indices.)
    bonenames              = bonedata[0]
    poseabs                = []
    ib                     = 0            # Scene_Root.
    poseabs.append( -posefloats[3*ib+0] )              
    poseabs.append(  posefloats[3*ib+1] )
    poseabs.append(  posefloats[3*ib+2] )

    nbones                 = len( posefloats ) / 3
    for ib in range( 1, nbones) :
        idx                = hierarchydata[ib]
        poseabs.append( -posefloats[3*ib+0] + poseabs[3*(idx)+0] )
        poseabs.append(  posefloats[3*ib+1] + poseabs[3*(idx)+1] )
        poseabs.append(  posefloats[3*ib+2] + poseabs[3*(idx)+2] )

    boneIds                = meshdata[2]
    verts                  = meshdata[3]
    for iv in range( len(boneIds) ) :
        Id                 = boneIds[iv]
        verts[3*iv+0]      = verts[3*iv+0] + poseabs[3*Id+0]
        verts[3*iv+1]      = verts[3*iv+1] + poseabs[3*Id+1]
        verts[3*iv+2]      = verts[3*iv+2] + poseabs[3*Id+2]

    meshdata[3]            = verts                         # Now the verts are correct!

    for iv in range( len(boneIds) ) :
        boneIds[iv]        = boneIds[iv] - 1

    meshdata[2]            = boneIds                       # Now the boneIds are correct for Milkshape.

    casfiledatalist.append( meshdata )                     # Index 10.

    # Read the footer data.
    if FLAGRESOURCE == True :
        intchoice          = getuint( fidcas )
        fidcas.seek( -4, 1 )
        if intchoice == 26 :
            footerdata     = readcasresourcemeshfooter( fidcas, fidtxt, flags )  
        else:
            footerdata     = readcasvariantresourcemeshfooter( fidcas, fidtxt, flags )  
        casfiledatalist.append( footerdata )               # Index 11.
    elif FLAGNAVY == True :
        footerdata         = readcasnavymeshfooter( fidcas, fidtxt, flags )  
        casfiledatalist.append( footerdata )               # Index 11.
    else:
        footerdata         = readcasmeshfooter( fidcas, fidtxt, flags )  
        casfiledatalist.append( footerdata )               # Index 11.

    # We've read the whole cas file, close out any open files.
    fidcas.close()
    if WRITECASTXTFILE == True :
        fidtxt.close()

    return casfiledatalist    


# ===================================================================================
#                                                                                   |
#    Utility for writing a full format .cas file (full format means with headers    |
# and footers, the type of files we got from Caliban's animations directory).  This |
# is highly modularized for ease of maintenance and, hopefully, extendibility.      |
#                                                                                   |
# ----------------------------------------------------------------------------------|
#                                                                                   |
# Functions: computefilesizesan(    casfiledatalist )                               |
#            writecasheader(        headerdata )                                    |
#            writecashierarchydata( fidcas, hierarchydata )                         |
#            writecastimeticksdata( fidcas, timeticksdata )                         |
#            writecasbonedata(      fidcas, bonedata )                              |
#            writecasfooterdata(    fidcas, footerdata )                            |
#            writecasfile(          fncas, casfiledatalist )                        |
#                                                                                   |
# ===================================================================================


# -----------------------------------------------------------------------------------
#    Computes the file size of the cas file sans header and footer.                 |
# -----------------------------------------------------------------------------------
def computefilesizesans( casfiledatalist ) :

    # Extract all the data sections from the list.
    headerdata             = casfiledatalist[0]
    filesizesans           = casfiledatalist[1]
    int_zero               = casfiledatalist[2]
    hierarchydata          = casfiledatalist[3]
    timeticksdata          = casfiledatalist[4]
    bonedata               = casfiledatalist[5]
    quatfloats             = casfiledatalist[6]
    animfloats             = casfiledatalist[7]
    posefloats             = casfiledatalist[8]
    eulers                 = casfiledatalist[9]
    footerdata             = casfiledatalist[10]

    # Size of 2 ints for filesize sans header/footer plus the zero. 
    filesizesans           = 8                             

    # Bytes for hierarchy data plus the 2 bytes of a short for the number of entries. 
    filesizesans           = filesizesans + 4 * len( hierarchydata ) + 2 

    # Bytes for time ticks data plus the int for the number of entries. 
    filesizesans           = filesizesans + 4 * ( len( timeticksdata ) + 1 ) 

    # Bone section has names plus a null bytes, an int for number of chars, 6 data ints, plus a final null byte.
    bonenames              = bonedata[0]
    nbones                 = len( bonenames )
    for ii in range( nbones ) :
        filesizesans       = filesizesans + len( bonenames[ii] ) + 1 + 7 * 4 + 1

    # quatfloats size.
    nquats                 = len( quatfloats )
    filesizesans           = filesizesans + 4 * nquats

    # animfloats size.
    nanims                 = len( animfloats )
    filesizesans           = filesizesans + 4 * nanims

    # animfloats size.
    nposes                 = len( posefloats )
    filesizesans           = filesizesans + 4 * nposes

    # Don't need length of footer because its file size sans header/footer.
    return filesizesans


# -----------------------------------------------------------------------------------
#    Writes binary full .cas file header.                                           |
# -----------------------------------------------------------------------------------
def writecasheader( fidcas, headerdata ) :

    # Extract fields from headerdata list.
    float_version          = headerdata[0]
    int_thirtyeight        = headerdata[1]
    int_nine               = headerdata[2]
    int_zero1              = headerdata[3]
    float_animtime         = headerdata[4]
    int_one1               = headerdata[5]
    int_zero2              = headerdata[6]
    signaturebytetriple1   = headerdata[7]
    int_one2               = headerdata[8]
    int_zero3              = headerdata[9]
    signaturebytetriple2   = headerdata[10]

    # So write already! Do I have to ask you twice?
    putfloat( float_version,  fidcas )
    putuint( int_thirtyeight, fidcas )
    putuint( int_nine,        fidcas )
    putuint( int_zero1,       fidcas )
    putfloat( float_animtime, fidcas )
    putuint( int_one1,        fidcas )
    putuint( int_zero2,       fidcas )
    putubyte( signaturebytetriple1[0], fidcas )
    putubyte( signaturebytetriple1[1], fidcas )
    putubyte( signaturebytetriple1[2], fidcas )
    putuint( int_one2,        fidcas )
    putuint( int_zero3,       fidcas )
    putubyte( signaturebytetriple2[0], fidcas )
    putubyte( signaturebytetriple2[1], fidcas )
    putubyte( signaturebytetriple2[2], fidcas )

    return 


# -----------------------------------------------------------------------------------
#    Writes binary full .cas file hierarchy data.                                   |
# -----------------------------------------------------------------------------------
def writecashierarchydata( fidcas, hierarchydata ) :

    # Extract number of entries from length of hierarchy array.
    nentries               = len( hierarchydata )

    # Output count and then dump integer array.         
    putushort( nentries,    fidcas )
    hierarchydata.tofile( fidcas )

    return 


# -----------------------------------------------------------------------------------
#    Writes binary full .cas file time ticks data.                                  |
# -----------------------------------------------------------------------------------
def writecastimeticksdata( fidcas, timeticksdata ) :

    # Extract number of entries from length of timeticksdata array.
    nentries               = len( timeticksdata )

    # Output count and then dump float array.        
    putuint( nentries,    fidcas )
    timeticksdata.tofile( fidcas )

    return 


# -----------------------------------------------------------------------------------
#    Writes binary full .cas file bone data.                                        |
# -----------------------------------------------------------------------------------
def writecasbonedata( fidcas, bonedata, version_float ) :

    # Extract number of bones from length of bonenames list.
    bonenames              = bonedata[0]
    quatframesperbone      = bonedata[1]
    animframesperbone      = bonedata[2]
    quatoffsetperbone      = bonedata[3]
    animoffsetperbone      = bonedata[4]
    zerosperbone           = bonedata[5]
    onesperbone            = bonedata[6]
    nbones                 = len( bonenames )

    # Output.                                       
    for ii in range( nbones ) :
        nch                = len( bonenames[ii] )
        putuint( nch+1, fidcas )
        putstring( bonenames[ii], fidcas )
        putubyte( 0,    fidcas )                           # Remember to null terminate the string.
        putuint( quatframesperbone[ii], fidcas )
        putuint( animframesperbone[ii], fidcas )
        putuint( quatoffsetperbone[ii], fidcas )
        putuint( animoffsetperbone[ii], fidcas )
        putuint( zerosperbone[ii],      fidcas )
        if ( version_float != 3.02 ) & ( version_float != 2.23 ) & ( version_float != 3.0 ) & ( version_float != 2.22 ) :
            putuint( onesperbone[ii],   fidcas )
            putubyte( 0,                fidcas )           # Final null byte.

    return 


# -----------------------------------------------------------------------------------
#    Writes binary full .cas file footer data.                                      |
# -----------------------------------------------------------------------------------
def writecasfooterdata( fidcas, footerdata ) :

    # Get the first int field to decide what type of footer to write.
    int_104                = footerdata[0]
    putuint( int_104,    fidcas )

    if int_104 == 18 :
        # Unpack camel footer data.
        int_one1           = footerdata[1]
        int_zero1          = footerdata[2]
        int_zero2          = footerdata[3]
        short_zero1        = footerdata[4]
        int_vec1           = footerdata[5]
        int_vec2           = footerdata[6]
        int_vec3           = footerdata[7]
        int_vec4           = footerdata[8]
        int_vec5           = footerdata[9]
        
        # Write camel footer.
        putuint( int_one1,      fidcas )
        putuint( int_zero1,     fidcas )
        putuint( int_zero2,     fidcas )
        putushort( short_zero1, fidcas )
        int_vec1.tofile( fidcas )
        int_vec2.tofile( fidcas )
        int_vec3.tofile( fidcas )
        int_vec4.tofile( fidcas )
        int_vec5.tofile( fidcas )

        return

    # Unpack the common data.
    int_one1               = footerdata[1]
    int_one2               = footerdata[2]

    # A check for an old style variant.
    if ( int_104 == 16 ) & ( int_one1 == 1 ) & ( int_one2 == 0 ) :
        int_zero1          = footerdata[3]       
        int_vec1           = footerdata[4]     
        int_vec2           = footerdata[5]     
        int_vec3           = footerdata[6]     
        int_vec4           = footerdata[7]     
        putuint( int_104,   fidcas )
        putuint( int_one1,  fidcas )
        putuint( int_one2,  fidcas )
        putuint( int_zero1, fidcas )
        int_vec1.tofile(    fidcas )
        int_vec2.tofile(    fidcas )
        int_vec3.tofile(    fidcas )
        int_vec4.tofile(    fidcas )
        return

    # Resume regular processing.
    AttribString           = footerdata[3]
    int_one3               = footerdata[4]
    byte_zero1             = footerdata[5]
    int_one4               = footerdata[6]
    int_zero1              = footerdata[7]
    byte_zero2             = footerdata[8]
    float_vec1             = footerdata[9]
    int_zero2              = footerdata[10]
    short_zero1            = footerdata[11]
    int_minus1             = footerdata[12]
    int_zero3              = footerdata[13]

    # Write the common data.
    putuint( int_one1,      fidcas )
    putuint( int_one2,      fidcas )
    nch                    = len( AttribString )
    putuint( nch+1,         fidcas )
    putstring( AttribString, fidcas )
    putubyte( 0,            fidcas )                        # Remember to null terminate the string!
    putuint( int_one3,      fidcas )
    putubyte( byte_zero1,   fidcas )                        # Remember to null terminate the string!
    putuint( int_one4,      fidcas )
    putuint( int_zero1,     fidcas )
    putubyte( byte_zero2,   fidcas )                        # Remember to null terminate the string!

    float_vec1.tofile( fidcas ) 

    putuint( int_zero2,     fidcas )
    putushort( short_zero1, fidcas )
    putint( int_minus1,     fidcas )
    putuint( int_zero3,     fidcas )
    
    if int_104 == 170 :
        # Unpack the data.
        string2            = footerdata[14]
        int_one5           = footerdata[15]
        byte_zero3         = footerdata[16]
        int_one6           = footerdata[17]
        int_zero4          = footerdata[18]
        byte_zero4         = footerdata[19]
        float_vec2         = footerdata[20]
        int_vec1           = footerdata[21]
        int_vec2           = footerdata[22]
        int_vec3           = footerdata[23]
        int_vec4           = footerdata[24]
        int_vec5           = footerdata[25]
        int_count          = footerdata[26]
        int_five           = footerdata[27]
        int_one7           = footerdata[28]
        int_zero5          = footerdata[29]
        float_vec3         = footerdata[30]
        int_vec6           = footerdata[31]
        byte_zero5         = footerdata[32]
        int_vec7           = footerdata[33]

        # Write rest of fs_horse type footer.
        nchars             = len( string2 )
        putuint( nchars+1,    fidcas )
        putstring( string2,   fidcas )
        putubyte( 0,          fidcas )                     # Remember to null terminate!
        putuint( int_one5,    fidcas )
        putubyte( byte_zero3, fidcas )
        putuint( int_one6,    fidcas )
        putuint( int_zero4,   fidcas )
        putubyte( byte_zero4, fidcas )

        float_vec2.tofile( fidcas )
        int_vec1.tofile( fidcas )
        int_vec2.tofile( fidcas )
        int_vec3.tofile( fidcas )
        int_vec4.tofile( fidcas )
        int_vec5.tofile( fidcas )

        putuint( int_count,   fidcas )
        putuint( int_five,    fidcas )
        putuint( int_one7,    fidcas )
        putuint( int_zero5,   fidcas )

        float_vec3.tofile( fidcas )
        int_vec6.tofile( fidcas )

        putubyte( byte_zero5, fidcas )

        int_vec7.tofile( fidcas )

    else:
        # Unpack regular unit data.
        short_zero2        = footerdata[14]
        int_something      = footerdata[15]
        int_vec1           = footerdata[16]
        int_vec2           = footerdata[17]
        int_vec3           = footerdata[18]
        int_vec4           = footerdata[19]
        int_vec5           = footerdata[20]
        int_vec6           = footerdata[21]

        # Write regular footer.
        putushort( short_zero2, fidcas )
        putuint( int_something, fidcas )
        int_vec1.tofile( fidcas )
        int_vec2.tofile( fidcas )
        int_vec3.tofile( fidcas )
        int_vec4.tofile( fidcas )
        int_vec5.tofile( fidcas )
        if int_vec6 != [] :
            int_vec6.tofile( fidcas )


    return


# -----------------------------------------------------------------------------------
#    Writes a binary full format .cas file using the information in the list        |
# casfiledatalist.                                                                  |
# -----------------------------------------------------------------------------------
def writecasfile( fncas, casfiledatalist ) :

    fidcas                 = open( fncas, 'wb' )

    if fidcas == -1 :
        print 'Failed to open file: ' + fncas
        print 'Exiting from the function writecasfile in animationlibrary.py...'
        exit()

    # Extract all the data sections from the list.
    headerdata             = casfiledatalist[0]
    filesizesans           = casfiledatalist[1]
    int_zero               = casfiledatalist[2]
    hierarchydata          = casfiledatalist[3]
    timeticksdata          = casfiledatalist[4]
    bonedata               = casfiledatalist[5]
    quatfloats             = casfiledatalist[6]
    animfloats             = casfiledatalist[7]
    posefloats             = casfiledatalist[8]
    eulers                 = casfiledatalist[9]
    footerdata             = casfiledatalist[10]
    version_float          = headerdata[0] 

    # Write header information.
    writecasheader( fidcas, headerdata ) 

    # Write file size sans header and footer size.
    filesizesans           = computefilesizesans( casfiledatalist )
    putuint( filesizesans, fidcas ) 
    putuint( int_zero,     fidcas )

    # Write the hierarchydata.
    writecashierarchydata( fidcas, hierarchydata )

    # Write the timeticksdata. 
    writecastimeticksdata( fidcas, timeticksdata )

    # Write the bones data.
    writecasbonedata( fidcas, bonedata, version_float )

    # Dump quats.
    quatfloats.tofile( fidcas )

    # Dump anims.
    animfloats.tofile( fidcas )

    # Dump poses.
    posefloats.tofile( fidcas )

    # Write footer if there is one.
    if footerdata != [] :
        writecasfooterdata( fidcas, footerdata )

    # Done! Close file.
    fidcas.close()

    return



# ===================================================================================
#                                                                                   |
#    Milkshape .ms3d binary file reader and associated functions.                   |
#                                                                                   |
# ----------------------------------------------------------------------------------|
#                                                                                   |
# Functions: readvertices(         fidms3d, fout )                                  |
#            readtriangles(        fidms3d, fout, nvert )                           |
#            readgroups(           fidms3d, fout )                                  |
#            readmaterials(        fidms3d, fout )                                  |
#            readkeyframer(        fidms3d, fout )                                  |
#            readjoints(           fidms3d, fout )                                  |
#            readgroupcomments(    fidms3d, fout )                                  |
#            readmaterialcomments( fidms3d, fout )                                  |
#            readjointcomments(    fidms3d, fout )                                  |
#            readmodelcomments(    fidms3d, fout )                                  |
#            readboneIdandweights( fidms3d, fout, nvert, subversionnum2 )           |
#            readms3dfile(         fnin, fnouttxt )                                 |
#                                                                                   |
# ===================================================================================


# -----------------------------------------------------------------------------------
#    Reads the vertex vector section block of a Milkshape .ms3d file.               |
# -----------------------------------------------------------------------------------
def readvertices( fidms3d, fout ) :

    nvert                  = getushort( fidms3d )

    if fout != [] :
        string             = 'Number of vertices = ' + str( nvert )
        fout.write( string + '\n' )
        fout.flush()
        print string

    # Allocate arrays.
    vflags                 = array.array( 'B' )
    vrefs                  = array.array( 'B' )
    vbonesPrimary          = array.array( 'b' )
    vvecs                  = array.array( 'f' )
    vnorms                 = array.array( 'f' )

    # Initialize.
    for ii in range( nvert ) :
        vflags.append( 0 )
        vrefs.append( 0 )
        vbonesPrimary.append( 0 )

    # Initialize.
    for ii in range( 3 * nvert ) :
        vvecs.append( 0.0 )
        vnorms.append( 0.0 )

    # Read in vertex data. This includes flags, boneId, and reference count.
    for ii in range( nvert ) :
        vflags[ii]         = getubyte( fidms3d )           
        vvecs[3*ii]        = getfloat( fidms3d )           # Vertex vector, x, y, and z
        vvecs[3*ii+1]      = getfloat( fidms3d )
        vvecs[3*ii+2]      = getfloat( fidms3d )
        vbonesPrimary[ii]  = getbyte( fidms3d )            # Primary bone Id.
        vrefs[ii]          = getubyte( fidms3d )           # Reference count.
    
    # Save the vertex data.
    vertexdata             = []
    vertexdata.append( vflags )
    vertexdata.append( vvecs )
    vertexdata.append( vbonesPrimary )
    vertexdata.append( vrefs )

    return vertexdata

# -----------------------------------------------------------------------------------
#    Reads the triangles section block of a Milkshape .ms3d file.                   |
# -----------------------------------------------------------------------------------
def readtriangles( fidms3d, fout, nvert ) :

    ntriangles             = getushort( fidms3d )

    if fout != [] :
        string             = 'Number of triangle = ' + str( ntriangles )
        fout.write( string + '\n' )
        fout.flush()
        print string

    # Allocate arrays.
    triflags               = array.array( 'H' )
    tris                   = array.array( 'H' )
    vnorms                 = array.array( 'f' )
    s                      = array.array( 'f' )
    t                      = array.array( 'f' )
    smoothingGroup         = array.array( 'B' )
    groupidx               = array.array( 'B' )

    # Initialize.
    for ii in range( ntriangles ) :
        triflags.append( 0 )
        tris.append( 0 )
        tris.append( 0 )
        tris.append( 0 )
        s.append( 0.0 )
        s.append( 0.0 )
        s.append( 0.0 )
        t.append( 0.0 )
        t.append( 0.0 )
        t.append( 0.0 )
        smoothingGroup.append( 0 )
        groupidx.append( 0 )

    for ii in range( 3 * nvert ) :
        vnorms.append( 0.0 )

    # Read data.
    for ii in range( ntriangles ) :
        triflags[ii]       = getushort( fidms3d )
        tris[3*ii]         = getushort( fidms3d )
        tris[3*ii+1]       = getushort( fidms3d )     
        tris[3*ii+2]       = getushort( fidms3d )
        idx1               = tris[3*ii]
        idx2               = tris[3*ii+1]
        idx3               = tris[3*ii+2]
        vnorms[3*idx1]     = getfloat(  fidms3d )
        vnorms[3*idx1+1]   = getfloat(  fidms3d )
        vnorms[3*idx1+2]   = getfloat(  fidms3d )
        vnorms[3*idx2]     = getfloat(  fidms3d )
        vnorms[3*idx2+1]   = getfloat(  fidms3d )
        vnorms[3*idx2+2]   = getfloat(  fidms3d )
        vnorms[3*idx3]     = getfloat(  fidms3d )
        vnorms[3*idx3+1]   = getfloat(  fidms3d )
        vnorms[3*idx3+2]   = getfloat(  fidms3d )
        s[3*ii]            = getfloat(  fidms3d )          
        s[3*ii+1]          = getfloat(  fidms3d )
        s[3*ii+2]          = getfloat(  fidms3d )
        t[3*ii]            = getfloat(  fidms3d )
        t[3*ii+1]          = getfloat(  fidms3d )
        t[3*ii+2]          = getfloat(  fidms3d )
        smoothingGroup[ii] = getubyte(  fidms3d )
        groupidx[ii]       = getubyte(  fidms3d )

    # Save the triangle data.
    triangledata           = []

    triangledata.append( triflags )
    triangledata.append( tris     )
    triangledata.append( vnorms   )
    triangledata.append( s        )
    triangledata.append( t        )
    triangledata.append( smoothingGroup )
    triangledata.append( groupidx )

    return triangledata

# -----------------------------------------------------------------------------------
#    Reads the groups section block of a Milkshape .ms3d file.                      |
# -----------------------------------------------------------------------------------
def readgroups( fidms3d, fout ) :

    num_groups             = getushort( fidms3d )

    if fout != [] :
        string             = 'Number of groups = ' + str( num_groups )
        fout.write( string + '\n' )
        fout.flush()
        print string

    gflags                 = []
    group_names            = []
    tri_groups             = []
    materialindex          = []
    for ii in range( num_groups ) :
        gflags.append( getubyte(  fidms3d ) )
        tempname           = fidms3d.read( 32 )
        groupname          = zipstrip( tempname )
        group_names.append( groupname )

        ntris              = getushort( fidms3d )
        triidx             = array.array( 'H' )
        for jj in range( ntris ) :
            triidx.append( getushort( fidms3d ) )

        materialindex.append( getbyte( fidms3d ) )
        tri_groups.append( triidx )

    # Save out group data.
    groupdata              = []
    groupdata.append( gflags )
    groupdata.append( group_names )
    groupdata.append( tri_groups  )
    groupdata.append( materialindex )

    return groupdata

# -----------------------------------------------------------------------------------
#    Reads the materials section block of a Milkshape .ms3d file.                   |
# -----------------------------------------------------------------------------------
def readmaterials( fidms3d, fout ) :

    nMaterials             = getushort( fidms3d )

    if fout != [] :
        string             = 'Number of materials = ' + str( nMaterials )
        fout.write( string + '\n' )
        fout.flush()
        print string

    # Initialize a list.
    materialdata           = []
    if nMaterials > 0 :
        for jj in range( nMaterials ) :
            material       = []                            # Initialize material list for a single block.
            ambient        = array.array( 'f' )
            diffuse        = array.array( 'f' )
            specular       = array.array( 'f' )
            emissive       = array.array( 'f' )
            texture        = array.array( 'b' )
            alphamap       = array.array( 'b' )

            name           = fidms3d.read( 32 )            # Name.
            ambient.fromfile(  fidms3d, 4 )
            diffuse.fromfile(  fidms3d, 4 )
            specular.fromfile( fidms3d, 4 )
            emissive.fromfile( fidms3d, 4 )
            shininess      = getfloat( fidms3d )
            transparency   = getfloat( fidms3d )
            mode           = getubyte( fidms3d )
            texture        = fidms3d.read( 128 )
            alphamap       = fidms3d.read( 128 )
            material.append( name         )
            material.append( ambient      )
            material.append( diffuse      )
            material.append( specular     )
            material.append( emissive     )
            material.append( shininess    )
            material.append( transparency )
            material.append( mode         )
            material.append( texture      )
            material.append( alphamap     )
            materialdata.append( material )

    return materialdata

# -----------------------------------------------------------------------------------
#    Reads the keyframer section block of a Milkshape .ms3d file.                   |
# -----------------------------------------------------------------------------------
def readkeyframer( fidms3d, fout ) :

    fAnimationFPS          = getfloat(  fidms3d )
    fCurrentTime           = getfloat(  fidms3d )
    iTotalFrames           = getuint(   fidms3d )
    if fout != [] :
        string             = 'fAnimationFPS = ' + str( fAnimationFPS )
        fout.write( string + '\n' )
        fout.flush()
        print string
        string             = 'fCurrentTime  = ' + str( fCurrentTime )
        fout.write( string + '\n' )
        fout.flush()
        print string
        string             = 'iTotalFrames  = ' + str( iTotalFrames )
        fout.write( string + '\n' )
        fout.flush()
        print string

    # Save onto keyframerdata list.
    keyframerdata          = []
    keyframerdata.append( fAnimationFPS )
    keyframerdata.append( fCurrentTime  )
    keyframerdata.append( iTotalFrames  )

    return keyframerdata

# -----------------------------------------------------------------------------------
#    Reads the joints section block of a Milkshape .ms3d file.                      |
# -----------------------------------------------------------------------------------
def readjoints( fidms3d, fout ) :

    njoints                = getushort( fidms3d )

    if fout != [] :
        string             = 'Number of joints = ' + str( njoints )
        fout.write( string + '\n' )
        fout.flush()
        print string

    jointdata              = []
    for ii in range( njoints ) :
        flags              = getubyte(  fidms3d )
        tbone              = fidms3d.read( 32 )
        bonename           = zipstrip( tbone )
        pbone              = fidms3d.read( 32 )
        parentname         = zipstrip( pbone )
        if fout != [] :
            string             = bonename + ' from ' + parentname
            fout.write( string + '\n' )
            fout.flush()
            print string
        # rotation[3] float.
        localrotation      = array.array( 'f' )
        localrotation.append( getfloat(  fidms3d ) )
        localrotation.append( getfloat(  fidms3d ) )
        localrotation.append( getfloat(  fidms3d ) )
        # position[3] float.
        localposition      = array.array( 'f' )
        localposition.append( getfloat(  fidms3d ) )
        localposition.append( getfloat(  fidms3d ) )
        localposition.append( getfloat(  fidms3d ) )
        # numKeyFramesRot.
        numKeyFramesRot    = getshort(  fidms3d )
        rotationframes     = array.array( 'f' )
        # numKeyFramesTrans
        numKeyFramesTrans  = getshort(  fidms3d )
        positionframes     = array.array( 'f' )
        for ii in range( numKeyFramesRot ) :
            rotationframes.append( getfloat(  fidms3d ) )
            rotationframes.append( getfloat(  fidms3d ) )
            rotationframes.append( getfloat(  fidms3d ) )
            rotationframes.append( getfloat(  fidms3d ) )

        for ii in range( numKeyFramesTrans ) :
            positionframes.append( getfloat(  fidms3d ) )
            positionframes.append( getfloat(  fidms3d ) )
            positionframes.append( getfloat(  fidms3d ) )
            positionframes.append( getfloat(  fidms3d ) )

        # Save out the data.
        joint          = []
        joint.append( flags )
        joint.append( bonename )
        joint.append( parentname )
        joint.append( localrotation )
        joint.append( localposition )
        joint.append( rotationframes )
        joint.append( positionframes )

        jointdata.append( joint )

    return jointdata

# -----------------------------------------------------------------------------------
#    Reads the group comments section block of a Milkshape .ms3d file.              |
# -----------------------------------------------------------------------------------
def readgroupcomments( fidms3d, fout ) :

    num_comments           = getuint(   fidms3d )

    if fout != [] :
        string             = 'Number of group comments = ' + str( num_comments )
        fout.write( string + '\n' )
        fout.flush()
        print string

    groupindices           = []
    groupcomments          = []
    for ii in range( num_comments ) :
        groupindices.append( getuint( fidms3d ) )
        nchars             = getuint( fidms3d )
        comment            = fidms3d.read( nchars )
        groupcomments.append( comment )

    # Save out the comment data.
    groupcommentdata       = []
    groupcommentdata.append( groupindices )   
    groupcommentdata.append( groupcomments )

    return groupcommentdata

# -----------------------------------------------------------------------------------
#    Reads the material comments section block of a Milkshape .ms3d file.           |
# -----------------------------------------------------------------------------------
def readmaterialcomments( fidms3d, fout ) :

    nNumMaterialComments   = getuint(   fidms3d )

    if fout != [] :
        string             = 'Number of material comments = ' + str( nNumMaterialComments )
        fout.write( string + '\n' )
        fout.flush()
        print string

    materialcommentdata    = []
    if nNumMaterialComments > 0 :
        materialindices    = []
        materialcomments   = []
        for ii in range( nNumMaterialComments ) :
            materialindices.append( getuint( fidms3d ) )
            nchars         = getuint( fidms3d )
            comment        = fidms3d.read( nchars )
            materialcomments.append( comment )

        materialcommentdata.append( materialindices )
        materialcommentdata.append( materialcomments )

    return materialcommentdata

# -----------------------------------------------------------------------------------
#    Reads the joint comments section block of a Milkshape .ms3d file.              |
# -----------------------------------------------------------------------------------
def readjointcomments( fidms3d, fout ) :

    nNumJointComments      = getuint(   fidms3d )

    if fout != [] :
        string             = 'Number of joint comments = ' + str( nNumJointComments )
        fout.write( string + '\n' )
        fout.flush()
        print string

    jointcommentdata       = []
    if nNumJointComments > 0 :
        jointindices       = []
        jointcomments      = []
        for ii in range( nNumJointComments ) :
            jointindices.append( getuint( fidms3d ) )
            nchars         = getuint( fidms3d )
            comment        = fidms3d.read( nchars )
            jointcomments.append( comment )

        jointcommentdata.append( jointindices )
        jointcommentdata.append( jointcomments )

    return jointcommentdata

# -----------------------------------------------------------------------------------
#    Reads the model comment section block of a Milkshape .ms3d file.               |
# -----------------------------------------------------------------------------------
def readmodelcomments( fidms3d, fout ) :

    nHasModelComment       = getuint(   fidms3d )

    if fout != [] :
        string             = 'Number of model comments = ' + str( nHasModelComment )
        fout.write( string + '\n' )
        fout.flush()
        print string

    modelcommentdata       = []
    if nHasModelComment > 0 :
        modelcomments      = []
        for ii in range( nHasModelComment ) :
            nchars         = getuint( fidms3d )
            comment        = fidms3d.read( nchars )
            modelcomments.append( comment )

        modelcommentdata.append( modelcomments )

    return modelcommentdata

# -----------------------------------------------------------------------------------
#    Reads the secondary bone Id and vertex weights section block of a Milkshape    |
# .ms3d file.                                                                       |
# -----------------------------------------------------------------------------------
def readboneIdandweights( fidms3d, fout, nvert, subversionnum2 ) :

    # Allocate arrays.
    vwts                   = array.array( 'B' )
    vbonesSecondary        = array.array( 'b' )
    vbonesThird            = array.array( 'b' )
    vbonesFourth           = array.array( 'b' )
    extra                  = array.array( 'I' )
    vthirdweight           = array.array( 'B' )

    # Read data.
    for ii in range( nvert ) :
        vbonesSecondary.append( getbyte( fidms3d ) ) 
        vbonesThird.append(     getbyte( fidms3d ) )
        vbonesFourth.append(    getbyte( fidms3d ) )
        wtprim             = getubyte( fidms3d ) 
        wtsecond           = getubyte( fidms3d )    
        vwts.append( wtprim )
        vwts.append( wtsecond )
        vthirdweight.append( getubyte( fidms3d ) )
        if subversionnum2 == 2 :
            extra.append( getuint( fidms3d ) )             # Vital to read the "extra" int field.

    # Save data.
    weightdata             = []
    weightdata.append( vbonesSecondary )                   # correct convention.
    weightdata.append( vbonesThird     )                   # correct convention.
    weightdata.append( vbonesFourth    )                   # correct convention.
    weightdata.append( vwts            )
    weightdata.append( vthirdweight    )
    weightdata.append( extra           )

    return weightdata

# -----------------------------------------------------------------------------------
#    Reads a Milkshape .ms3d file.                                                  |
# -----------------------------------------------------------------------------------
def readms3dfile( fnin, fnouttxt ) :

    VARIANTMESHFLAG        = False                         # Variant is for siege engines, haven't got there yet.
    TANGENTSPACEFLAG       = 2                             # 2 or 4 depending on full tangent space in mesh.  Leftover.

    # This is the return value, a list with all the data in the .ms3d file.
    ms3dfiledatalist       = []

    # Debugging output.
    if fnouttxt != [] :
        fout               = open( fnouttxt, 'w' )
    else :
        fout               = []

    # ------------------------------------------------------
    # Header data.                                         |
    # ------------------------------------------------------
    fidms3d                = open( fnin, 'rb' )
    header                 = fidms3d.read( 10 )
    versionnum             = getuint( fidms3d )               

    headerdata             = []
    headerdata.append( header )
    headerdata.append( versionnum )
    ms3dfiledatalist.append( headerdata )                  # Index 0.

    if fout != [] :
        string             = header + ', version number ' + str( versionnum )
        fout.write( string + '\n' )
        fout.flush()
        print string

    # ------------------------------------------------------
    # Vertex data.                                         |
    # ------------------------------------------------------
    vertexdata             = readvertices( fidms3d, fout )
    ms3dfiledatalist.append( vertexdata )                  # Index 1.
    vflags                 = vertexdata[0]
    nvert                  = len( vflags )                 # We will need nvert for later calls.

    # ------------------------------------------------------
    # Triangle data.                                       |
    # ------------------------------------------------------
    triangledata           = readtriangles( fidms3d, fout, nvert ) 
    ms3dfiledatalist.append( triangledata )                # Index 2.

    # ------------------------------------------------------
    # Group data.                                          |
    # ------------------------------------------------------
    groupdata              = readgroups( fidms3d, fout )
    ms3dfiledatalist.append( groupdata )                   # Index 3. 

    # ------------------------------------------------------
    # Material data.                                       |
    # ------------------------------------------------------
    materialdata           = readmaterials( fidms3d, fout )# Index 4.
    ms3dfiledatalist.append( materialdata )

    # ------------------------------------------------------
    # Keyframer data.                                      |
    # ------------------------------------------------------
    keyframerdata          = readkeyframer( fidms3d, fout )# Index 5.
    ms3dfiledatalist.append( keyframerdata )

    # ------------------------------------------------------
    # Joints or bone data.                                 |
    # ------------------------------------------------------
    jointdata              = readjoints( fidms3d, fout )   # Index 6.
    ms3dfiledatalist.append( jointdata )

    # ------------------------------------------------------
    # Subversion number (always 1).                        |
    # ------------------------------------------------------
    subversionnum1         = getuint(   fidms3d )

    if fout != [] :
        string             = 'First subversion number = ' + str( subversionnum1 )
        fout.write( string + '\n' )
        fout.flush()
        print string

    ms3dfiledatalist.append( subversionnum1 )              # Index 7.

    # ------------------------------------------------------
    # Group comments.                                      |
    # ------------------------------------------------------
    groupcommentdata       = readgroupcomments( fidms3d, fout ) 
    ms3dfiledatalist.append( groupcommentdata )            # Index 8.

    # ------------------------------------------------------
    # Material comments.                                   |
    # ------------------------------------------------------
    materialcommentdata    = readmaterialcomments( fidms3d, fout ) 
    ms3dfiledatalist.append( materialcommentdata )         # Index 9.

    # ------------------------------------------------------
    # Joint comments.                                      |
    # ------------------------------------------------------
    jointcommentdata       = readjointcomments( fidms3d, fout ) 
    ms3dfiledatalist.append( jointcommentdata )            # Index 10.

    # ------------------------------------------------------
    # Model comments.                                      |
    # ------------------------------------------------------
    modelcommentdata       = readmodelcomments( fidms3d, fout ) 
    ms3dfiledatalist.append( modelcommentdata )            # Index 11.

    # ------------------------------------------------------
    # Second subversion number.  Can be 1 or 2.            |
    # ------------------------------------------------------
    subversionnum2         = getuint(   fidms3d )

    if fout != [] :
        string             = 'Second subversion number = ' + str( subversionnum2 )
        fout.write( string + '\n' )
        fout.flush()
        print string

    ms3dfiledatalist.append( subversionnum2 )              # Index 12.

    # ------------------------------------------------------
    # Vertex weighting data.                               |
    # ------------------------------------------------------
    weightdata             = readboneIdandweights( fidms3d, fout, nvert, subversionnum2 ) 
    ms3dfiledatalist.append( weightdata )                  # Index 13.

    # We ignore the joint extra data, usually colors.
    fidms3d.close()
    if fout != [] :
        fout.close()

    return ms3dfiledatalist


# ===================================================================================
#                                                                                   |
#    Milkshape .ms3d binary file writer and associated functions.                   |
#                                                                                   |
# ----------------------------------------------------------------------------------|
#                                                                                   |
# Functions: writevertices(         fidms3d, vertexdata )                           |
#            writetriangles(        fidms3d, triangledata )                         |
#            writegroups(           fidms3d, groupdata )                            |
#            writematerials(        fidms3d, materialdata )                         |
#            writekeyframer(        fidms3d, keyframerdata )                        |
#            writejoints(           fidms3d, jointdata )                            |
#            writegroupcomments(    fidms3d, groupcommentdata )                     |
#            writematerialcomments( fidms3d, materialcommentdata )                  |
#            writejointcomments(    fidms3d, jointcommentdata )                     |
#            writemodelcomment(     fidms3d, modelcommentdata )                     |
#            writeboneIdandweights( fidms3d, weightdata, subversionnum2 )           |
#            writems3dfile(         fn, ms3dfiledatalist )                          |
#                                                                                   |
# ===================================================================================


# -----------------------------------------------------------------------------------
#    Writes the vertex data for a binary ms3d (1.8.0) format.                       |
# -----------------------------------------------------------------------------------
def writevertices( fidms3d, vertexdata ) :

    # Unpack the data structure.
    vflags                 = vertexdata[0]
    vvecs                  = vertexdata[1]
    vbonesPrimary          = vertexdata[2]
    vrefs                  = vertexdata[3]

    nvert                  = len( vflags )

    # Write data.
    putushort( nvert, fidms3d )                            # Write number of vertices. 

    for ii in range(nvert) :
        putubyte( vflags[ii],        fidms3d )             # Flag byte.
        putfloat( vvecs[3*ii+0],     fidms3d )             # Vertex vector: x 
        putfloat( vvecs[3*ii+1],     fidms3d )             # y
        putfloat( vvecs[3*ii+2],     fidms3d )             # z
        putbyte(  vbonesPrimary[ii], fidms3d )             # Primary bone Id.
        putbyte(  vrefs[ii],         fidms3d )             # Reference count.

    return

# -----------------------------------------------------------------------------------
#    Writes the triangle data for a binary ms3d (1.8.0) format.                     |
# -----------------------------------------------------------------------------------
def writetriangles( fidms3d, triangledata ) :

    # Unpack the data structure.
    triflags               = triangledata[0]
    tris                   = triangledata[1]
    vnorms                 = triangledata[2]
    s                      = triangledata[3]
    t                      = triangledata[4]
    smoothingGroup         = triangledata[5]
    groupidx               = triangledata[6]

    ntriangles             = len( triflags )
    putushort( ntriangles, fidms3d )                       # Write out number of triangles.

    for ii in range( ntriangles ) :
        idx1               = tris[3*ii]                    # Index of triangle's first vertex.
        idx2               = tris[3*ii+1]                  # Index of triangle's second vertex.
        idx3               = tris[3*ii+2]                  # Index of triangle's third vertex.
                                                           
        putushort( triflags[ii],      fidms3d )               
        putushort( idx1,              fidms3d )                       
        putushort( idx2,              fidms3d )                       
        putushort( idx3,              fidms3d )                       
        putfloat( vnorms[3*idx1],     fidms3d )            # x value of first vertex normal vector.
        putfloat( vnorms[3*idx1+1],   fidms3d )            # y value of first vertex normal vector.
        putfloat( vnorms[3*idx1+2],   fidms3d )            # z value of first vertex normal vector.
        putfloat( vnorms[3*idx2],     fidms3d )            # x value of second vertex normal vector.
        putfloat( vnorms[3*idx2+1],   fidms3d )            # y value of second vertex normal vector.
        putfloat( vnorms[3*idx2+2],   fidms3d )            # z value of second vertex normal vector.
        putfloat( vnorms[3*idx3],     fidms3d )            # x value of third vertex normal vector.
        putfloat( vnorms[3*idx3+1],   fidms3d )            # y value of third vertex normal vector.
        putfloat( vnorms[3*idx3+2],   fidms3d )            # z value of third vertex normal vector.
        putfloat( s[3*ii+0],          fidms3d )            # u or s value for first vertex.     
        putfloat( s[3*ii+1],          fidms3d )            # u or s value for second vertex.
        putfloat( s[3*ii+2],          fidms3d )            # u or s value for third vertex.
        putfloat( t[3*ii+0],          fidms3d )            # v or t value for first vertex.
        putfloat( t[3*ii+1],          fidms3d )            # v or t value for second vertex.
        putfloat( t[3*ii+2],          fidms3d )            # v or t value for third vertex.
        putubyte( smoothingGroup[ii], fidms3d )            # Smoothing group.
        putubyte( groupidx[ii],       fidms3d )            # Group index.
                                                           
    return

# -----------------------------------------------------------------------------------
#    Writes the group data for a binary ms3d (1.8.0) format.                        |
# -----------------------------------------------------------------------------------
def writegroups( fidms3d, groupdata ) :

    # Unpack the data structure.
    gflags                 = groupdata[0]
    group_names            = groupdata[1]
    tri_groups             = groupdata[2]
    materialindex          = groupdata[3]

    num_groups             = len( tri_groups )

    # Write a short with the number of groups.
    putushort( num_groups, fidms3d ) 

    ntriidx                = 0
    for ii in range( num_groups ) :
        groupname          = group_names[ii]
        nname              = len( groupname )
        triidx             = tri_groups[ii]                # 1D array of indices into the big triangle block.
        ntris              = len( triidx )                 # This is number of tris in this group.
        matindex           = materialindex[ii]             # Material index for group.

        putubyte( gflags[ii],   fidms3d )                  # Flag, 1 for selected.
        putstring( groupname,   fidms3d )
        putzerobytes( 32-nname, fidms3d )                  # Pad with nulls out to 32 bytes for group name.
        putushort( ntris,       fidms3d )                  # Write a short with the number of triangle indices. 

        for jj in range( ntris ) :
            putushort( triidx[jj], fidms3d )               # Index.

        putbyte( matindex, fidms3d )                       # 0 for Figure, 1 for Attachment.

    return

# -----------------------------------------------------------------------------------
#    Writes the material data for a binary ms3d (1.8.0) format.                     |
# -----------------------------------------------------------------------------------
def writematerials( fidms3d, materialdata ) :

    nmaterials             = len( materialdata )
    putushort( nmaterials, fidms3d )                       # Write out short with number of materials.

    for kk in range( nmaterials ) :
        # Unpack data.
        material           = materialdata[kk]
        name               = material[0]
        ambient            = material[1]
        diffuse            = material[2]
        specular           = material[3]
        emissive           = material[4]
        shininess          = material[5]
        transparency       = material[6]
        mode               = material[7]
        texture            = material[8]
        alphamap           = material[9]

        # Write data.
        putstring( name,        fidms3d )
        ambient.tofile(         fidms3d )
        diffuse.tofile(         fidms3d )
        specular.tofile(        fidms3d )
        emissive.tofile(        fidms3d )
        putfloat( shininess,    fidms3d )
        putfloat( transparency, fidms3d )
        putubyte( mode,         fidms3d )
        putstring( texture,     fidms3d )
        putstring( alphamap,    fidms3d )

    return

# -----------------------------------------------------------------------------------
#    Writes the keyframer data for a binary ms3d (1.8.0) format.                    |
# -----------------------------------------------------------------------------------
def writekeyframer( fidms3d, keyframerdata ) :

    # Unpack data.
    fAnimationFPS          = keyframerdata[0]
    fCurrentTime           = keyframerdata[1]
    iTotalFrames           = keyframerdata[2]

    # Write data.
    putfloat( fAnimationFPS, fidms3d )
    putfloat( fCurrentTime,  fidms3d )
    putuint(  iTotalFrames,  fidms3d )
    
    return

# -----------------------------------------------------------------------------------
#    Writes the joints data for a binary ms3d (1.8.0) format.                       |
# -----------------------------------------------------------------------------------
def writejoints( fidms3d, jointdata ) :

    nbones                 = len( jointdata )
    putushort( nbones, fidms3d )                           # Write short with the number of joints or bones.

    for ii in range( nbones ) :
        # Unpack data.
        joint              = jointdata[ii]
        flags              = joint[0]
        bonename           = joint[1]
        parentname         = joint[2]
        localrotation      = joint[3]
        localposition      = joint[4]
        rotationframes     = joint[5]
        positionframes     = joint[6]

        # Write data
        putubyte( flags,       fidms3d )                   # Flag.
        putstring( bonename,   fidms3d )
        putzerobytes( 32-len( bonename ), fidms3d )        # Null pad to 32 bytes.
        putstring( parentname, fidms3d )
        putzerobytes( 32-len( parentname), fidms3d )       # Null pad to 32 bytes.

        localrotation.tofile(  fidms3d )
        localposition.tofile(  fidms3d )
        nframesrot         = len( rotationframes ) / 4     # Number of frames for a framenumber and 3 rotation angles.
        putushort( nframesrot, fidms3d )
        nframespos         = len( positionframes ) / 4     # Number of frames for a framenumber and 3 position values.
        putushort( nframespos, fidms3d )
        rotationframes.tofile( fidms3d )
        positionframes.tofile( fidms3d )

    return

# -----------------------------------------------------------------------------------
#    Writes the group comments data for a binary ms3d (1.8.0) format.               |
# -----------------------------------------------------------------------------------
def writegroupcomments( fidms3d, groupcommentdata ) :

    if groupcommentdata == [] :
        putuint( 0, fidms3d )                              # No comments, so return.
        return

    # Unpack data.
    groupindices           = groupcommentdata[0]
    groupcomments          = groupcommentdata[1]

    num_comments           = len( groupindices )
    putuint( num_comments, fidms3d )                       # Write int with the number of group comments.

    for ii in range( num_comments ) :
        putuint( groupindices[ii],  fidms3d )
        comment            = groupcomments[ii]
        nch                = len( comment )
        putuint( nch,       fidms3d ) 
        putstring( comment, fidms3d )

    return

# -----------------------------------------------------------------------------------
#    Writes the material comments data for a binary ms3d (1.8.0) format.            |
# -----------------------------------------------------------------------------------
def writematerialcomments( fidms3d, materialcommentdata ) :

    if materialcommentdata == [] :
        putuint( 0, fidms3d )                              # No comments, so return.
        return

    # Unpack data.
    materialindices        = materialcommentdata[0]
    materialcomments       = materialcommentdata[1]

    num_comments           = len( materialindices )
    putuint( num_comments, fidms3d )                       # Write int with the number of material comments.

    for ii in range( num_comments ) :
        putuint( materialindices[ii],  fidms3d )
        comment            = materialcomments[ii]
        nch                = len( comment )
        putuint( nch,       fidms3d ) 
        putstring( comment, fidms3d )

    return

# -----------------------------------------------------------------------------------
#    Writes the joint comments data for a binary ms3d (1.8.0) format.               |
# -----------------------------------------------------------------------------------
def writejointcomments( fidms3d, jointcommentdata ) :

    if jointcommentdata == [] :
        putuint( 0, fidms3d )                              # No comments, so return.
        return

    # Unpack data.
    jointindices           = jointcommentdata[0]
    jointcomments          = jointcommentdata[1]

    num_comments           = len( jointindices )
    putuint( num_comments, fidms3d )                       # Write int with the number of joint comments.

    for ii in range( num_comments ) :
        putuint( jointindices[ii],  fidms3d )
        comment            = jointcomments[ii]
        nch                = len( comment )
        putuint( nch,       fidms3d ) 
        putstring( comment, fidms3d )

    return

# -----------------------------------------------------------------------------------
#    Writes the model comment data for a binary ms3d (1.8.0) format.                |
# -----------------------------------------------------------------------------------
def writemodelcomment( fidms3d, modelcommentdata ) :

    print( "Writing model comment..." )
    if modelcommentdata == [] :
        putuint( 0, fidms3d )                              # No comments, so return.
        return

    # Unpack data.
    modelcomment           = modelcommentdata[0]

    putuint( 1, fidms3d )                                  # Write int with the number of model comments.

    nch                    = len( modelcomment )
    putuint( nch,           fidms3d ) 
    putstring( modelcomment, fidms3d )

    return

# -----------------------------------------------------------------------------------
#    Writes the secondary bone Id and vertex weighting data for a binary ms3d       |
# (1.8.0) format.                                                                   |
# -----------------------------------------------------------------------------------
def writeboneIdandweights( fidms3d, weightdata, subversionnum2 ) :

    # Unpack data.
    vbonesSecondary        = weightdata[0]
    vbonesThird            = weightdata[1]
    vbonesFourth           = weightdata[2]
    vwts                   = weightdata[3]
    vthirdweight           = weightdata[4]
    extra                  = weightdata[5]

    # Write data.
    nvert                  = len( vbonesSecondary )
    for ii in range( nvert ) :
        putbyte( vbonesSecondary[ii], fidms3d )
        putbyte( vbonesThird[ii],     fidms3d )
        putbyte( vbonesFourth[ii],    fidms3d )
        putubyte( vwts[2*ii+0],       fidms3d )
        putubyte( vwts[2*ii+1],       fidms3d )
        putubyte( vthirdweight[ii],   fidms3d )
        if subversionnum2 == 2 :
            putuint( extra[ii],       fidms3d )

    return

# -----------------------------------------------------------------------------------
#    This def writes data out in binary ms3d (1.8.0) format.                        |
# -----------------------------------------------------------------------------------
def writems3dfile( fn, ms3dfiledatalist ) :

    # Open up all the data in ms3dfiledatalist.
    headerdata             = ms3dfiledatalist[0]
    vertexdata             = ms3dfiledatalist[1]
    triangledata           = ms3dfiledatalist[2]
    groupdata              = ms3dfiledatalist[3]
    materialdata           = ms3dfiledatalist[4]
    keyframerdata          = ms3dfiledatalist[5]
    jointdata              = ms3dfiledatalist[6]
    subversionnum1         = ms3dfiledatalist[7]
    groupcommentdata       = ms3dfiledatalist[8]
    materialcommentdata    = ms3dfiledatalist[9]
    jointcommentdata       = ms3dfiledatalist[10]
    modelcommentdata       = ms3dfiledatalist[11]
    subversionnum2         = ms3dfiledatalist[12]
    weightdata             = ms3dfiledatalist[13]

    # Open filename for writing binary.
    fidms3d                = open( fn, 'wb' )
    print 'Open file to output ms3d file.'

    # ------------------------------------------------------
    # Header data.                                         |
    # ------------------------------------------------------
    header                 = headerdata[0]
    versionnum             = headerdata[1]
    print 'header = ' + header
    print 'versionnum = ' + str( versionnum )
    fidms3d.write( header )        
    putuint( versionnum, fidms3d )
    print 'Wrote header data.'

    # ------------------------------------------------------
    # Vertex data.                                         |
    # ------------------------------------------------------
    writevertices( fidms3d, vertexdata ) 
    print 'Wrote vertex data.'

    # ------------------------------------------------------
    # Triangle data.                                       |
    # ------------------------------------------------------
    writetriangles( fidms3d, triangledata ) 
    print 'Wrote triangle data.'

    # ------------------------------------------------------
    # Group data.                                          |
    # ------------------------------------------------------
    writegroups( fidms3d, groupdata ) 
    print 'Wrote group data.'

    # ------------------------------------------------------
    # Material data.                                       |
    # ------------------------------------------------------
    writematerials( fidms3d, materialdata ) 
    print 'Wrote material data.'

    # ------------------------------------------------------
    # Animation data.  This is where we start merging.     |
    # ------------------------------------------------------
    writekeyframer( fidms3d, keyframerdata )  
    print 'Wrote keyframer data.'

    # ------------------------------------------------------
    # Joint data.                                          |
    # ------------------------------------------------------
    writejoints( fidms3d, jointdata )  
    print 'Wrote joint data.'

    # ------------------------------------------------------
    # First subversion entry.                              |
    # ------------------------------------------------------
    putuint( subversionnum1 , fidms3d )

    # ------------------------------------------------------
    # Group comments.                                      |
    # ------------------------------------------------------
    writegroupcomments( fidms3d, groupcommentdata )
    print 'Wrote group comments.'

    # ------------------------------------------------------
    # Material comments.                                   |
    # ------------------------------------------------------
    writematerialcomments( fidms3d, materialcommentdata )
    print 'Wrote material comments.'

    # ------------------------------------------------------
    # Joint comments.                                      |
    # ------------------------------------------------------
    writejointcomments( fidms3d, jointcommentdata )
    print 'Wrote joint comments.'

    # ------------------------------------------------------
    # Model comments.                                      |
    # ------------------------------------------------------
    writemodelcomment( fidms3d, modelcommentdata )
    print 'Wrote model comment.'

    # ------------------------------------------------------
    # Second subversion number.                            |
    # ------------------------------------------------------
    putuint( subversionnum2, fidms3d )                                  

    # ------------------------------------------------------
    # Vertex weight data.                                  |
    # ------------------------------------------------------
    writeboneIdandweights( fidms3d, weightdata, subversionnum2 )
    print 'Wrote weights.'      

    # ------------------------------------------------------
    # Second subversion number, must be 2.                 |
    # ------------------------------------------------------
#    putuint( 2, fidms3d )                                  

    # ------------------------------------------------------
    # Joint colors.                                        |
    # ------------------------------------------------------
#    nNumJoints             = len( jointdata )   
#    for ii in range(nNumJoints) :
#        putfloat( 0.0, fidms3d )
#        putfloat( 0.0, fidms3d )
#        putfloat( 1.0, fidms3d )
     

    fidms3d.close()

    return


# -----------------------------------------------------------------------------------
#                            convertcastoms3d()                                     |
# -----------------------------------------------------------------------------------
def convertcastoms3d( fncas, fntxt, flags ):

    casfiledatalist        = readcasfile( fncas, fntxt, flags )
    nch                    = fncas.find( '.cas' )
    tmp                    = fncas[0:nch]
    fnms3d                 = tmp + '.ms3d'
    print( 'fnms3d = ' + fnms3d )
    nnavy                  = fncas.find( 'navy' )
    FLAGNAVY               = False
    if nnavy > -1:
        FLAGNAVY           = True

    # Unpack data.
    headerdata             = casfiledatalist[0]            # Index 0.
    filesizesans           = casfiledatalist[1]            # Index 1.
    int_zero               = casfiledatalist[2]            # Index 2.
    hierarchydata          = casfiledatalist[3]            # Index 3.
    timeticksdata          = casfiledatalist[4]            # Index 4.
    bonedata               = casfiledatalist[5]            # Index 5.
    quatfloats             = casfiledatalist[6]            # Index 6.
    animfloats             = casfiledatalist[7]            # Index 7.
    posefloats             = casfiledatalist[8]            # Index 8.
    eulers                 = casfiledatalist[9]            # Index 9.
    meshdata               = casfiledatalist[10]           # Index 10.
    footerdata             = casfiledatalist[11]           # Index 11.

    print( "footerdata[0] = " + str( footerdata[0] ) )

    # Repack for an ms3d file.
    FLAGRESOURCE           = meshdata[0]
    chunkstr               = meshdata[1]
    boneIds                = meshdata[2]
    verts                  = meshdata[3]
    normals                = meshdata[4]
    faces                  = meshdata[5]
    textureId              = meshdata[6]
    tverts                 = meshdata[7]
    vcolors                = meshdata[8]
    groupnames             = meshdata[9]
    grouptris              = meshdata[10]
    groupmatIds            = meshdata[11]
    groupindex             = meshdata[12]
    groupcomments          = meshdata[13]

    # Header.
    header                 = 'MS3D000000'
    versionnum             = 4
    msheaderdata           = []
    msheaderdata.append( header )
    msheaderdata.append( versionnum )

    # Vertex data.
    numverts               = len( boneIds )
    vflags                 = []
    vrefs                  = []
    for ii in range( numverts ) :
        vflags.append( 1 )
        vrefs.append( 1 )
    vertexdata             = []
    vertexdata.append( vflags )
    vertexdata.append( verts )
    vertexdata.append( boneIds )
    vertexdata.append( vrefs )

    # Face data.
    numfaces               = len( faces ) / 3
    triflags               = []
    s_array                = []
    t_array                = []
    smoothingGroup         = []
    groupidx               = []
    for ii in range( numfaces ) :
        triflags.append( 1 )
        idx1               = faces[3*ii+0]
        idx2               = faces[3*ii+1]
        idx3               = faces[3*ii+2]
        s_array.append( tverts[2*idx1+0] )
        s_array.append( tverts[2*idx2+0] )
        s_array.append( tverts[2*idx3+0] )
        t_array.append( tverts[2*idx1+1] )
        t_array.append( tverts[2*idx2+1] )
        t_array.append( tverts[2*idx3+1] )
        smoothingGroup.append( 1 )

    triangledata           = []
    triangledata.append( triflags )
    triangledata.append( faces )   
    triangledata.append( normals )
    triangledata.append( s_array )
    triangledata.append( t_array )
    triangledata.append( smoothingGroup )
    triangledata.append( groupindex )         

    # Group data.
    nummeshes              = len( groupnames )
    gflags                 = []                 
    for ii in range( nummeshes ) :
        gflags.append( 1 ) 
    
    groupdata              = []
    groupdata.append( gflags )
    groupdata.append( groupnames )
    groupdata.append( grouptris ) 
    groupdata.append( groupmatIds )

    # Material data.
    nullname               = '\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0'
    figname                = 'Figure\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0'
    attachname             = 'Attachments\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0'
    ambient                = array.array( 'f' )
    diffuse                = array.array( 'f' )
    specular               = array.array( 'f' )
    emissive               = array.array( 'f' )
    ambient.append( 1.0 )
    ambient.append( 1.0 )
    ambient.append( 1.0 )
    ambient.append( 1.0 )
    diffuse.append( 0.8 )
    diffuse.append( 0.8 )
    diffuse.append( 0.8 )
    diffuse.append( 1.0 )
    specular.append( 0.0 )
    specular.append( 0.0 )
    specular.append( 0.0 )
    specular.append( 1.0 )
    emissive.append( 0.0 )
    emissive.append( 0.0 )
    emissive.append( 0.0 )
    emissive.append( 1.0 )
    shininess              = 0.0
    transparency           = 1.0
    mode                   = 0  
    material0              = []
    material0.append( figname )
    material0.append( ambient )
    material0.append( diffuse )
    material0.append( specular )
    material0.append( emissive )
    material0.append( shininess )
    material0.append( transparency )
    material0.append( mode ) 
    material0.append( nullname )
    material0.append( nullname )
    material1              = []
    material1.append( attachname )
    material1.append( ambient )
    material1.append( diffuse )
    material1.append( specular )
    material1.append( emissive )
    material1.append( shininess )
    material1.append( transparency )
    material1.append( mode ) 
    material1.append( nullname )
    material1.append( nullname )
    materialdata           = []
    materialdata.append( material0 )
    materialdata.append( material1 )

    # Keyframer data.
    keyframerdata          = []
    keyframerdata.append( 5.0 )                            # Frames per second.
    keyframerdata.append( 0.0 )                            # Current time.     
    keyframerdata.append( 1 )                              # Number of frames. 

    # Joints data.
    bonenames              = bonedata[0]
    nbones                 = len( bonenames )              # Includes Scene_Root.
    parentnames            = []
    parentnames.append( '' )                               # For bone_pelvis.
    for ib in range( 2, nbones ) :
        parentnames.append( bonenames[hierarchydata[ib]] )

    localrot               = array.array( 'f' )
    localrot.append( 0.0 )
    localrot.append( 0.0 )
    localrot.append( 0.0 )
    rotframes              = array.array( 'f' )
    posframes              = array.array( 'f' )
    jointdata              = []
    for ib in range( 1, nbones ) :
        flags              = 8
        localpos           = array.array( 'f' )
        localpos.append( -posefloats[3*ib+0] )             # Sign change on x component.
        localpos.append(  posefloats[3*ib+1] )
        localpos.append(  posefloats[3*ib+2] )
        joint              = []
        joint.append( flags )
        joint.append( bonenames[ib] )
        joint.append( parentnames[ib-1] )
        joint.append( localrot )        
        joint.append( localpos )        
        joint.append( rotframes )       
        joint.append( posframes )       
        jointdata.append( joint )
    
    # First subversion number.
    subversionnum1         = 1

    # Group comments.
    groupindices           = []
    for ii in range( nummeshes ) :
        groupindices.append( ii )
    groupcommentdata       = []
    groupcommentdata.append( groupindices )
    groupcommentdata.append( groupcomments )

    # Material comments.
    headerstr              = ''
    for kk in range( len(headerdata) ) :
        headerstr          = headerstr + ' ' + str( headerdata[kk] )

    hierarchystr           = ''
    for kk in range( len(hierarchydata) ) :
        hierarchystr       = hierarchystr + ' ' + str( hierarchydata[kk] )

    timeticksstr           = ''
    for kk in range( len(timeticksdata) ) :
        timeticksstr       = timeticksstr + ' ' + str( timeticksdata[kk] )

    firstmatcomment        = headerstr + '%%' + hierarchystr + '%%' + timeticksstr

    materialindices        = []
    materialindices.append( 0 )
    materialindices.append( 1 )
    materialcomments       = []
    materialcomments.append( firstmatcomment )
    materialcomments.append( chunkstr )
    materialcommentdata    = []
    materialcommentdata.append( materialindices )
    materialcommentdata.append( materialcomments )

    # Joint comments.
    jointcommentdata       = []


    # Model comment.
    modelcommentdata       = []
    footerstr              = footerdata[0]
    modelcommentdata.append( footerstr )
    
    # Second subversion number.
    subversionnum2         = 2

    # Weighting data.
    vbonessecondary        = array.array( 'b' )
    vbonesthird            = array.array( 'b' )
    vbonesfourth           = array.array( 'b' )
    vwts                   = array.array( 'b' )
    vthirdwt               = array.array( 'b' )
    extra                  = array.array( 'b' )
    for ii in range( numverts ) :
        vbonessecondary.append( -1 )
        vbonesthird.append( -1 )
        vbonesfourth.append( -1 )
        vwts.append( 100 )
        vwts.append( 0 )
        vthirdwt.append( 0 )
        extra.append( 0 )

    weightdata             = []
    weightdata.append( vbonessecondary )
    weightdata.append( vbonesthird )
    weightdata.append( vbonesfourth )
    weightdata.append( vwts )
    weightdata.append( vthirdwt )
    weightdata.append( extra )

    # Package and return.
    ms3dfiledatalist       = []
    ms3dfiledatalist.append( msheaderdata )
    ms3dfiledatalist.append( vertexdata )
    ms3dfiledatalist.append( triangledata )
    ms3dfiledatalist.append( groupdata )
    ms3dfiledatalist.append( materialdata )
    ms3dfiledatalist.append( keyframerdata )
    ms3dfiledatalist.append( jointdata )
    ms3dfiledatalist.append( subversionnum1 )
    ms3dfiledatalist.append( groupcommentdata )
    ms3dfiledatalist.append( materialcommentdata )
    ms3dfiledatalist.append( jointcommentdata )
    ms3dfiledatalist.append( modelcommentdata )
    ms3dfiledatalist.append( subversionnum2 )
    ms3dfiledatalist.append( weightdata )

    # Write that puppy out.
    writems3dfile( fnms3d, ms3dfiledatalist )


# -----------------------------------------------------------------------------------
#                            convertms3dtocas()                                     |
# -----------------------------------------------------------------------------------
def convertms3dtocas( fnms3d, fncas ):

    ms3dfiledatalist       = readms3dfile( fnms3d, [] )

    # Unpack the data.
    headerdata             = ms3dfiledatalist[0]
    vertexdata             = ms3dfiledatalist[1]
    triangledata           = ms3dfiledatalist[2]
    groupdata              = ms3dfiledatalist[3]
    materialdata           = ms3dfiledatalist[4]
    keyframerdata          = ms3dfiledatalist[5]
    jointdata              = ms3dfiledatalist[6]
    subversionnum1         = ms3dfiledatalist[7]
    groupcommentdata       = ms3dfiledatalist[8]
    materialcommentdata    = ms3dfiledatalist[9]
    jointcommentdata       = ms3dfiledatalist[10]
    modelcommentdata       = ms3dfiledatalist[11]
    subversionnum2         = ms3dfiledatalist[12]
    weightdata             = ms3dfiledatalist[13]

    # Unpack groupdata.

    # Find out if it is a resource.
    materialindices        = materialcommentdata[0]
    materialcomments       = materialcommentdata[1]

    firstmaterialcomment   = materialcomments[0]
    chunkstr               = materialcomments[1]
    tokens                 = firstmaterialcomment.split( '%%' )
    headerstr              = tokens[0]
    hierarchystr           = tokens[1]
    timeticksstr           = tokens[2]
    header                 = headerstr.split()
    FLAGRESOURCE           = False
    nresource              = fnms3d.find( 'resource' )
    nsymbol                = fnms3d.find( 'symbol' )
    if ( int( header[12] ) == 99 ) or ( nresource > -1 ) or ( nsymbol > -1 ) :
        FLAGRESOURCE       = True
        print( 'Converting a resource model.' )
    else:
        print( 'Converting a non-resource model.' )

    nnavy                  = fnms3d.find( 'navy' )
    FLAGNAVY               = False
    if nnavy > -1 :
        FLAGNAVY           = True


    # Convert hierarchy and timeticks back to numbers.
    hierarchy              = []
    timeticks              = []
    hiertokens             = hierarchystr.split()
    for ii in range( len( hiertokens ) ) :
        hierarchy.append( int( hiertokens[ii] ) )
    timetokens             = timeticksstr.split()
    for ii in range( len( timetokens ) ) :
        timeticks.append( float( timetokens[ii] ) )

    # Unpack jointdata to get bonenames.
    bonenames              = []
    for ii in range( len(jointdata) ) :
        joint              = jointdata[ii]
        bonename           = joint[1]
        bonenames.append( bonename )

    # Compute the first chunk offset or filesizesans header/footer.
    filesizesans           = 8                             # filesizesans plus 0 int.
    filesizesans           = filesizesans + 4 * len( hierarchy ) + 2       # Bytes for hierarchy data plus the 2 bytes of a short for the number of entries. 
    filesizesans           = filesizesans + 4 * ( len( timeticks ) + 1 )   # Bytes for time ticks data plus the int for the number of entries. 
    nbones                 = len( bonenames )
    filesizesans           = filesizesans + 10 + 1 + 7 * 4 + 1             # This is Scene_Root.
    filesizesans           = filesizesans + 12                             # Pose floats for Scene_Root.
    for ii in range( nbones ) :
        filesizesans       = filesizesans + len( bonenames[ii] ) + 1 + 7 * 4 + 1

    filesizesans           = filesizesans + 4 * 3 * nbones                 # No quatfloats or animfloats but we do have pose data (the skeleton).
    

    # Open a cas file for output.
    fid                    = open( fncas, 'wb' )

    if fid < 0 :
        print( 'Failed to open cas file for output.' )
        return

    # Write header.
#    interval               = timeticks[len(timeticks)-1]
    putfloat(  float(header[0]),   fid )
    putuint(   int(header[1]),     fid )
    putuint(   int(header[2]),     fid )
    putuint(   int(header[3]),     fid )
    putfloat(  float(header[4]),   fid )
    putuint(   int(header[5]),     fid )
    putuint(   int(header[6]),     fid )
    putubyte(  int(header[7]),     fid )                   # First signature triplet.
    putubyte(  int(header[8]),     fid )
    putubyte(  int(header[9]),     fid )
    putuint(   int(header[10]),    fid )
    putuint(   int(header[11]),    fid )
    putubyte(  int(header[12]),    fid )                   # Second signature triplet.
    putubyte(  int(header[13]),    fid )
    putubyte(  int(header[14]),    fid )

    # Write filesizesans plus a zero int.
    putuint(   filesizesans,       fid )
    putuint(   0,                  fid )

    # Write hierarchy.
    putushort( len(hierarchy),     fid )
    for ii in range( len( hierarchy ) ) :
        putuint( int(hierarchy[ii]), fid )

    # Write timeticks.
    putuint( len(timeticks),       fid )
    for ii in range( len( timeticks ) ) :
        putfloat( float(timeticks[ii]), fid )

    # Write bone section.
    putuint( 11,                   fid )
    putstring( "Scene_Root",       fid )
    putubyte(  0,                  fid )
    putuint(   0,                  fid )
    putuint(   0,                  fid )
    putuint(   0,                  fid )
    putuint(   0,                  fid )
    putuint(   0,                  fid )
    putuint(   1,                  fid )
    putubyte(  0,                  fid )
    for ii in range( nbones ) :
        nch                = len( bonenames[ii] )
        putuint( nch+1,            fid )
        putstring( bonenames[ii],  fid )
        putubyte(  0,              fid )                   # Null byte terminator.
        putuint(   0,              fid )                   # Number of quat frames - 0.
        putuint(   0,              fid )                   # Number of anim frames - 0.
        putuint(   0,              fid )                   # Offset to quat frames - 0.
        putuint(   0,              fid )                   # Offset to anim frames - 0.
        putuint(   0,              fid )                   # Unknown, always 0.           
        putuint(   1,              fid )                   # Number of pose frames, always 1.
        putubyte(  0,              fid )                   # Null byte.

    # Write pose floats.
    putfloat(  0.0,                fid )                   # Scene_Root.
    putfloat(  0.0,                fid )                   # Scene_Root.
    putfloat(  0.0,                fid )                   # Scene_Root.
    if len( jointdata ) > 0 :
        joint              = jointdata[0]                  # bone_pelvis.
        localposition      = joint[4]
        putfloat(-localposition[0], fid )                  # Remember the minus sign on x!
        putfloat( localposition[1], fid )        
        putfloat( localposition[2], fid )        
        poseabs                = []
        poseabs.append(-localposition[0] )
        poseabs.append( localposition[1] )
        poseabs.append( localposition[2] )
        print( "poseabs[0,1,2] = (" + str(poseabs[0]) + ", " + str(poseabs[1]) + ", " + str(poseabs[2]) + ")" )
        for ii in range( 1, len(jointdata) ) :
            joint          = jointdata[ii]
            localposition  = joint[4]
            putfloat(-localposition[0], fid )              # Remember the minus sign on x!
            putfloat( localposition[1], fid )
            putfloat( localposition[2], fid )
            idx                = hierarchy[ii+1]-1
            print( "For ii = " + str(ii) + ", hierarchy idx = " + str( idx ) )
            poseabs.append( -localposition[0] + poseabs[3*(idx)+0] )
            poseabs.append(  localposition[1] + poseabs[3*(idx)+1] )
            poseabs.append(  localposition[2] + poseabs[3*(idx)+2] )
            print( "poseabs[0,1,2] = (" + str(poseabs[3*ii+0]) + ", " + str(poseabs[3*ii+1]) + ", " + str(poseabs[3*ii+2]) + ")" )

    # Write second chunk offset.
    verts                  = vertexdata[1]
    boneIds                = vertexdata[2]
    nverts                 = len( boneIds )
    faces                  = triangledata[1]
    normals                = triangledata[2]
    s_array                = triangledata[3]
    t_array                = triangledata[4]
    groupnames             = groupdata[1]
    grouptris              = groupdata[2]
    groupmatId             = groupdata[3]
    groupcomments          = groupcommentdata[1]
    nummeshes              = len( groupnames )
    print( "Size of s_array = " + str( len(s_array) ) + ", size of t_array = " + str( len(t_array) ) )
    nfaces                 = len( faces ) / 3
    tokens                 = chunkstr.split()
    nchunktoks             = len( tokens )
    if FLAGRESOURCE == True :
        modelcomments      = modelcommentdata[0]
        footerstr          = modelcomments[0]
        tokens             = footerstr.split()
        if ( int(tokens[0]) == 26 ) or ( nchunktoks == 19 ) :
            offset         = 110
        else:
            offset         = 24
        offset             = offset + 32 * nverts + 6 * nfaces          # Resources don't have bone Ids.
        for imesh in range( nummeshes ):
            offset         = offset + len( groupnames[imesh] ) + 47 + 8
    elif FLAGNAVY  == True :
        offset             = 110
        offset             = offset + 32 * nverts + 6 * nfaces              # Navy doesn't have bone Ids either.
        for imesh in range( nummeshes ):
            offset         = offset + len( groupnames[imesh] ) + 47 + 8
    else:
        offset             = 16
        offset             = offset + 36 * nverts + 6 * nfaces
        for imesh in range( nummeshes ):
            offset         = offset + len( groupnames[imesh] ) + 44 + 8

    # Write chunk data header.
    tokens                 = chunkstr.split()
    nchunktoks             = len( tokens )
    if ( FLAGRESOURCE == False ) and ( FLAGNAVY == False ) and ( nchunktoks == 8 ) :
        # Regular chunk.
        putuint(  int(tokens[0]),    fid )
        putuint(  int(tokens[1]),    fid )
        putuint(  int(tokens[2]),    fid )
        putuint(  int(tokens[3]),    fid )
        putushort(int(tokens[4]),    fid )
        putuint(  int( offset),      fid )                     # Chunk offset.
        putuint(  int(tokens[6]),    fid )
        putuint(  nummeshes,         fid )
    elif ( FLAGRESOURCE == False ) and ( FLAGNAVY == False ) and ( nchunktoks == 24 ) :
        # Regular chunk but with an attribnode thrown in to be a pain in the ass.
        print( 'DDDDDDDDDDDDDDDDDoing attrib node' )
        putuint(  int(tokens[0]),    fid )          
        putuint(  int(tokens[1]),    fid )
        putuint(  int(tokens[2]),    fid )
        putuint(  int(tokens[3]),    fid )
        putstring( tokens[4],        fid )
        putubyte(  0,                fid )
        putuint(  int(tokens[5]),    fid )
        putubyte(  0,                fid )
        putuint(  int(tokens[6]),    fid )
        putubyte(  0,                fid )
        putfloat(float(tokens[7]),   fid )
        putfloat(float(tokens[8]),   fid )
        putfloat(float(tokens[9]),   fid )
        putfloat(float(tokens[10]),  fid )
        putfloat(float(tokens[11]),  fid )
        putfloat(float(tokens[12]),  fid )
        putfloat(float(tokens[13]),  fid )
        putfloat(float(tokens[14]),  fid )
        putfloat(float(tokens[15]),  fid )
        putushort(int(tokens[16]),   fid )
        putint(   int(tokens[17]),   fid )
        putushort(int(tokens[18]),   fid )

        putuint(  int(tokens[19]),   fid )
        putuint(  int(tokens[20]),   fid )
        putuint(  offset,            fid )
        putuint(  int(tokens[22]),   fid )
        putuint(  nummeshes,         fid )
    elif ( FLAGRESOURCE == True ) and ( nchunktoks == 3 ) :
        # Resource chunk.
        putuint(  offset,            fid )
        putuint(  int(tokens[1]),    fid )
        putuint(  int(tokens[2]),    fid )
    elif ( FLAGNAVY == True ) or ( ( FLAGRESOURCE == True ) and ( nchunktoks > 3 ) ) :
        # Navy chunk.
        putuint(  offset,            fid )
        putuint(  int(tokens[1]),    fid )
        putuint(  int(tokens[2]),    fid )
        putuint(  int(tokens[3]),    fid )
        putstring(    tokens[4],     fid )
        putubyte( 0,                 fid )
        putuint(  int(tokens[5]),    fid )
        putubyte( 0,                 fid )
        putuint(  int(tokens[6]),    fid )
        putubyte( 0,                 fid )
        putfloat(float(tokens[7]),   fid )
        putfloat(float(tokens[8]),   fid )
        putfloat(float(tokens[9]),   fid )
        putfloat(float(tokens[10]),  fid )
        putfloat(float(tokens[11]),  fid )
        putfloat(float(tokens[12]),  fid )
        putfloat(float(tokens[13]),  fid )
        putfloat(float(tokens[14]),  fid )
        putfloat(float(tokens[15]),  fid )
        putushort( int(tokens[16]),  fid )
        putint(    int(tokens[17]),  fid )
        putuint(   int(tokens[18]),  fid )


    # Loop over the chunks.
    nv                     = 0
    for imesh in range( nummeshes ) :
        textureId          = groupmatId[imesh]
        nch                = len( groupnames[imesh] )
        putuint(   nch+1,          fid )
        putstring( groupnames[imesh], fid )
        putubyte(  0,              fid )
        if ( FLAGRESOURCE == True ) or ( FLAGNAVY == True ) :
            comment        = groupcomments[imesh]
            tokens         = comment.split()
            putuint(  int(tokens[0]),   fid )
            putubyte( 0,                fid )
            putuint(  int(tokens[1]),   fid )
            putubyte( 0,                fid )
            putuint(  int(tokens[2]),   fid )
            putfloat( float(tokens[3]), fid )
            putfloat( float(tokens[4]), fid )
            putfloat( float(tokens[5]), fid )
            putfloat( float(tokens[6]), fid )
            putfloat( float(tokens[7]), fid )
            putfloat( float(tokens[8]), fid )
            putfloat( float(tokens[9]), fid )
        else:
            putuint(    1,              fid )
            putubyte(   0,              fid )
            putfloat( 0.0,              fid )
            putfloat( 0.0,              fid )
            putfloat( 0.0,              fid )
            putfloat( 0.0,              fid )
            putfloat( 0.0,              fid )
            putfloat( 0.0,              fid )
            putfloat( 0.0,              fid )
#            comment        = groupcomments[imesh]
#            tokens         = comment.split()
#            putuint(  int(tokens[0]),   fid )
#            putubyte( 0,                fid )
#            putfloat( float(tokens[1]), fid )
#            putfloat( float(tokens[2]), fid )
#            putfloat( float(tokens[3]), fid )
#            putfloat( float(tokens[4]), fid )
#            putfloat( float(tokens[5]), fid )
#            putfloat( float(tokens[6]), fid )
#            putfloat( float(tokens[7]), fid )

        # Now we have to break apart our big tables into small ones.
        imin               = 100000
        imax               = -10000
        triarr             = grouptris[imesh]
        ntris              = len( triarr )
        for itri in range( ntris ) :
            idx            = triarr[itri]
            idx1           = faces[3*idx+0]
            idx2           = faces[3*idx+1]
            idx3           = faces[3*idx+2]
            if idx1 > imax :
                imax       = idx1
            if idx2 > imax :
                imax       = idx2
            if idx3 > imax :
                imax       = idx3
            if idx1 < imin :
                imin       = idx1
            if idx2 < imin :
                imin       = idx2
            if idx3 < imin :
                imin       = idx3

        print( "For mesh " + str(imesh) + ", imin = " + str(imin) + ", imax = " + str(imax) )
        putushort( imax+1-imin,     fid )
        putushort( ntris,           fid )
        putubyte(  1,               fid )                  # Texture verts true.
        putubyte(  0,               fid )                  # Vertex colors false.

        if boneIds[0] > -1 :
            for ii in range( imin, imax+1 ) :
                putuint(  boneIds[ii]+1, fid )             # Change to 0-based on Scene_Root! 

        for ii in range( imin, imax+1 ) :
            Id             = boneIds[ii]
            if Id > -1 :
                putfloat(-verts[3*ii+0]-poseabs[3*Id+0], fid )
                putfloat( verts[3*ii+1]-poseabs[3*Id+1], fid )
                putfloat( verts[3*ii+2]-poseabs[3*Id+2], fid )
            else:
                putfloat(-verts[3*ii+0], fid )
                putfloat( verts[3*ii+1], fid )
                putfloat( verts[3*ii+2], fid )

        for ii in range( imin, imax+1 ) :
            putfloat(-normals[3*ii+0], fid )
            putfloat( normals[3*ii+1], fid )
            putfloat( normals[3*ii+2], fid )

        for itri in range( ntris ) :
            idx            = triarr[itri]
            putushort( faces[3*idx+0]-nv, fid )
            putushort( faces[3*idx+2]-nv, fid )            # NOTE: We switch indicies here.
            putushort( faces[3*idx+1]-nv, fid )

        svert              = array.array( 'f' )
        tvert              = array.array( 'f' )
        for ii in range( imin, imax+1 ) :
            svert.append( 0.0 )
            tvert.append( 0.0 )

        for itri in range( ntris ) :
            idx            = triarr[itri]
            idx1           = faces[3*idx+0]-nv
            idx2           = faces[3*idx+1]-nv
            idx3           = faces[3*idx+2]-nv
            svert[idx1]    = s_array[3*idx+0]
            svert[idx2]    = s_array[3*idx+1]
            svert[idx3]    = s_array[3*idx+2]
            tvert[idx1]    = t_array[3*idx+0]
            tvert[idx2]    = t_array[3*idx+1]
            tvert[idx3]    = t_array[3*idx+2]

        putuint( textureId, fid )
        for ii in range( imax+1-imin ) :
            putfloat( svert[ii],       fid )
            putfloat( tvert[ii],       fid )

        # Termination zero int.
        putuint( 0,            fid )                   
        nv                 = nv + imax + 1 - imin
        print( "nv = " + str( nv ) )
        # End of loop over imesh.

    # Now do the footer.
    modelcomments          = modelcommentdata[0]
    footerstr              = modelcomments[0]
    print( 'footer = ' + footerstr )
    tokens                 = footerstr.split()
    ntoks                  = len( tokens )
    print( 'ntoks  = ' + str( ntoks ) )
    if ( FLAGRESOURCE == True ) and ( int(tokens[0]) == 26 ) :
        attribstr          = tokens[1]
        texturefilename    = tokens[38]
        footsize           = 75 + len( texturefilename )
        nch                = len( attribstr )

        putuint( nch+1,                 fid )              # Index 0.
        putstring( attribstr,           fid )              # Index 1.
        putubyte(  0,                   fid )
        putuint( int( tokens[2] ),      fid )              # Index 2.
        putubyte(  0,                   fid )
        putuint( int( tokens[3] ),      fid )              # Index 3.
        putubyte(  0,                   fid )
        # 9 floats.
        putfloat( float( tokens[4] ),   fid )              # Index 4.
        putfloat( float( tokens[5] ),   fid )              # Index 5. 
        putfloat( float( tokens[6] ),   fid )              # Index 6. 
        putfloat( float( tokens[7] ),   fid )              # Index 7. 
        putfloat( float( tokens[8] ),   fid )              # Index 8. 
        putfloat( float( tokens[9] ),   fid )              # Index 9. 
        putfloat( float( tokens[10] ),  fid )              # Index 10.
        putfloat( float( tokens[11] ),  fid )              # Index 11.
        putfloat( float( tokens[12] ),  fid )              # Index 12.
        # Short 0, int -1, short 0.
        putushort( int( tokens[13] ),   fid )              # Index 13.
        putint(    int( tokens[14] ),   fid )              # Index 14.
        putushort( int( tokens[15] ),   fid )              # Index 15.
        # 18 ints.
        putuint(   int( tokens[16] ),   fid )              # Index 16. 
        putuint(   int( tokens[17] ),   fid )              # Index 17. 
        putuint(   int( tokens[18] ),   fid )              # Index 18. 
        putuint(   int( tokens[19] ),   fid )              # Index 19. 
        putuint(   int( tokens[20] ),   fid )              # Index 20. 
        putuint(   int( tokens[21] ),   fid )              # Index 21. 
        putuint(   int( tokens[22] ),   fid )              # Index 22. 
        putuint(   int( tokens[23] ),   fid )              # Index 23. 
        putuint(   int( tokens[24] ),   fid )              # Index 24. 
        putuint(   int( tokens[25] ),   fid )              # Index 25. 
        putuint(   int( tokens[26] ),   fid )              # Index 26. 
        putuint(   int( tokens[27] ),   fid )              # Index 27. 
        putuint(   int( tokens[28] ),   fid )              # Index 28. 
        putuint(   int( tokens[29] ),   fid )              # Index 29. 
        putuint(   int( tokens[30] ),   fid )              # Index 30. 
        putuint(   int( tokens[31] ),   fid )              # Index 31. 
        putuint(   int( tokens[32] ),   fid )              # Index 32. 
        putuint(   int( tokens[33] ),   fid )              # Index 33. 

        # Print the footsize.
        putuint(   footsize,            fid )              # Index 34.
        putuint(   int( tokens[35] ),   fid )              # Index 35. 
        putuint(   int( tokens[36] ),   fid )              # Index 36. 
        putuint(   int( tokens[37] ),   fid )              # Index 37. 
        putubyte(  0,                   fid )
        putstring( tokens[38],          fid )              # Index 38. 
        putubyte(  0,                   fid )
       
        # 14 floats.
        putfloat( float( tokens[39] ),  fid )              # Index 39. 
        putfloat( float( tokens[40] ),  fid )              # Index 40. 
        putfloat( float( tokens[41] ),  fid )              # Index 41. 
        putfloat( float( tokens[42] ),  fid )              # Index 42. 
        putfloat( float( tokens[43] ),  fid )              # Index 43. 
        putfloat( float( tokens[44] ),  fid )              # Index 44. 
        putfloat( float( tokens[45] ),  fid )              # Index 45. 
        putfloat( float( tokens[46] ),  fid )              # Index 46. 
        putfloat( float( tokens[47] ),  fid )              # Index 47. 
        putfloat( float( tokens[48] ),  fid )              # Index 48. 
        putfloat( float( tokens[49] ),  fid )              # Index 49. 
        putfloat( float( tokens[50] ),  fid )              # Index 50. 
        putfloat( float( tokens[51] ),  fid )              # Index 51. 
        putfloat( float( tokens[52] ),  fid )              # Index 52. 
                                                           
        putubyte( 1,                    fid )

    elif ( FLAGRESOURCE == True ) and ( int(tokens[0]) == 0 ) :
        putushort(   int( tokens[0] ),  fid )
        for ii in range( 1, 18 ) :
            putuint(   int( tokens[ii] ), fid )
        footsize           = len( tokens[22] ) + 75
        putuint( footsize,              fid )
        putuint(   int( tokens[19] ),   fid )
        putuint(   int( tokens[20] ),   fid )
        putuint(   int( tokens[21] ),   fid )
        putubyte(  0,                   fid )
        putstring( tokens[22],          fid )
        putubyte(  0,                   fid )
        for ii in range( 23, 37 ) :
            putfloat(float(tokens[ii]), fid )
        putubyte(  1,                   fid )

    elif FLAGNAVY == True :
        texturefilestring  = tokens[22]
        footsize           = 75 + len( texturefilestring )
        putushort( int(tokens[0]),      fid )
        for ii in range( 1, 18 ) :
            putuint( int(tokens[ii]),   fid )
        putuint( footsize,              fid )   
        putuint( int(tokens[19]),       fid )
        putuint( int(tokens[20]),       fid )
        putuint( int(tokens[21]),       fid )
        putubyte( 0,                    fid )
        putstring( tokens[22],          fid )
        putubyte( 0,                    fid )
        for ii in range( 23, 37 ) :
            putfloat( float(tokens[ii]),fid )
        putubyte( 1,                    fid )

    else:
        texturefilestring  = tokens[17]
        texturefilestring  = texturefilestring.replace( '%', ' ' )
        footsize           = 75 + len( texturefilestring )
        putuint( nummeshes,             fid )
        for ii in range( 1, 13 ) :
            putuint( int(tokens[ii]),   fid )
        putuint( footsize,              fid )   
        putuint( int(tokens[14]),       fid )
        putuint( int(tokens[15]),       fid )
        putuint( int(tokens[16]),       fid )
        putubyte( 0,                    fid )
        putstring( texturefilestring,   fid )
        putubyte( 0,                    fid )
        for ii in range( 18, 32 ) :
            putfloat( float(tokens[ii]),fid )
        putubyte( 1,                    fid )

    fid.close()

# -----------------------------------------------------------------------------------
#                            dataflags() - Equivalent to a C struct.                |
# -----------------------------------------------------------------------------------
class dataflags() :

    def __init__(self) :
        self.header        = 0
        self.filesize      = 0
        self.hierarchy     = 0
        self.timeticks     = 0
        self.bones         = 0
        self.alldata       = 0
        self.footer        = 0
        self.isdir         = 0

        return


# ===================================================================================
#                                                                                   |
#    The following is a file chooser taken directly from the Python distribution.   |
#                                                                                   |
# To use in a script do the following:                                              |
#                                                                                   |
#     root = Tk()                                                                   |
#     root.withdraw()                                                               |
#     d                          = FileDialog(root)                                 |
#     fncas                      = d.go(os.curdir, "*.cas")                         |
#                                                                                   |
# Note that you can use any SINGLE filter, like "*.cas" or "*.*".  Haven't found    |
# a way to do multiple filters.                                                     |
#                                                                                   |
# ===================================================================================

class FileDialog:

    """Standard file selection dialog -- no checks on selected file.

    Usage:

        d = FileDialog(master)
        fname = d.go(dir_or_file, pattern, default, key)
        if fname is None: ...canceled...
        else: ...open file...

    All arguments to go() are optional.

    The 'key' argument specifies a key in the global dictionary
    'dialogstates', which keeps track of the values for the directory
    and pattern arguments, overriding the values passed in (it does
    not keep track of the default argument!).  If no key is specified,
    the dialog keeps no memory of previous state.  Note that memory is
    kept even when the dialog is canceled.  (All this emulates the
    behavior of the Macintosh file selection dialogs.)

    """

    title = "File Selection Dialog"

    def __init__(self, master, title=None):
        if title is None: title = self.title
        self.master = master
        self.directory = None

        self.top = Toplevel(master)
        self.top.title(title)
        self.top.iconname(title)

        self.botframe = Frame(self.top)
        self.botframe.pack(side=BOTTOM, fill=X)

        self.selection = Entry(self.top)
        self.selection.pack(side=BOTTOM, fill=X)
        self.selection.bind('<Return>', self.ok_event)

        self.filter = Entry(self.top)
        self.filter.pack(side=TOP, fill=X)
        self.filter.bind('<Return>', self.filter_command)

        self.midframe = Frame(self.top,width=800,height=600)
        self.top.geometry("800x600")
        self.midframe.pack(expand=YES, fill=BOTH)

        self.filesbar = Scrollbar(self.midframe)
        self.filesbar.pack(side=RIGHT, fill=Y)
        self.files = Listbox(self.midframe, exportselection=0,
                             yscrollcommand=(self.filesbar, 'set'))
        self.files.pack(side=RIGHT, expand=YES, fill=BOTH)
        btags = self.files.bindtags()
        self.files.bindtags(btags[1:] + btags[:1])
        self.files.bind('<ButtonRelease-1>', self.files_select_event)
        self.files.bind('<Double-ButtonRelease-1>', self.files_double_event)
        self.filesbar.config(command=(self.files, 'yview'))

        self.dirsbar = Scrollbar(self.midframe)
        self.dirsbar.pack(side=LEFT, fill=Y)
        self.dirs = Listbox(self.midframe, exportselection=0,
                            yscrollcommand=(self.dirsbar, 'set'))
        self.dirs.pack(side=LEFT, expand=YES, fill=BOTH)
        self.dirsbar.config(command=(self.dirs, 'yview'))
        btags = self.dirs.bindtags()
        self.dirs.bindtags(btags[1:] + btags[:1])
        self.dirs.bind('<ButtonRelease-1>', self.dirs_select_event)
        self.dirs.bind('<Double-ButtonRelease-1>', self.dirs_double_event)

        self.ok_button = Button(self.botframe,
                                 text="OK",
                                 command=self.ok_command)
        self.ok_button.pack(side=LEFT)
        self.filter_button = Button(self.botframe,
                                    text="Filter",
                                    command=self.filter_command)
        self.filter_button.pack(side=LEFT, expand=YES)
        self.cancel_button = Button(self.botframe,
                                    text="Cancel",
                                    command=self.cancel_command)
        self.cancel_button.pack(side=RIGHT)

        self.top.protocol('WM_DELETE_WINDOW', self.cancel_command)
        # XXX Are the following okay for a general audience?
        self.top.bind('<Alt-w>', self.cancel_command)
        self.top.bind('<Alt-W>', self.cancel_command)

    def go(self, dir_or_file=os.curdir, pattern="*", default="", key=None):
        if key and dialogstates.has_key(key):
            self.directory, pattern = dialogstates[key]
        else:
            dir_or_file = os.path.expanduser(dir_or_file)
            if os.path.isdir(dir_or_file):
                self.directory = dir_or_file
            else:
                self.directory, default = os.path.split(dir_or_file)
        self.set_filter(self.directory, pattern)
        self.set_selection(default)
        self.filter_command()
        self.selection.focus_set()
        self.top.wait_visibility() # window needs to be visible for the grab
        self.top.grab_set()
        self.how = None
        self.master.mainloop()          # Exited by self.quit(how)
        if key:
            directory, pattern = self.get_filter()
            if self.how:
                directory = os.path.dirname(self.how)
            dialogstates[key] = directory, pattern
        self.top.destroy()
        return self.how

    def quit(self, how=None):
        self.how = how
        self.master.quit()              # Exit mainloop()

    def dirs_double_event(self, event):
        self.filter_command()

    def dirs_select_event(self, event):
        dir, pat = self.get_filter()
        subdir = self.dirs.get('active')
        dir = os.path.normpath(os.path.join(self.directory, subdir))
        self.set_filter(dir, pat)

    def files_double_event(self, event):
        self.ok_command()

    def files_select_event(self, event):
        file = self.files.get('active')
        self.set_selection(file)

    def ok_event(self, event):
        self.ok_command()

    def ok_command(self):
        self.quit(self.get_selection())

    def filter_command(self, event=None):
        dir, pat = self.get_filter()
        try:
            names = os.listdir(dir)
        except os.error:
            self.master.bell()
            return
        self.directory = dir
        self.set_filter(dir, pat)
        names.sort()
        subdirs = [os.pardir]
        matchingfiles = []
        for name in names:
            fullname = os.path.join(dir, name)
            if os.path.isdir(fullname):
                subdirs.append(name)
            elif fnmatch.fnmatch(name, pat):
                matchingfiles.append(name)
        self.dirs.delete(0, END)
        for name in subdirs:
            self.dirs.insert(END, name)
        self.files.delete(0, END)
        for name in matchingfiles:
            self.files.insert(END, name)
        head, tail = os.path.split(self.get_selection())
        if tail == os.curdir: tail = ''
        self.set_selection(tail)

    def get_filter(self):
        filter = self.filter.get()
        filter = os.path.expanduser(filter)
        if filter[-1:] == os.sep or os.path.isdir(filter):
            filter = os.path.join(filter, "*")
        return os.path.split(filter)

    def get_selection(self):
        file = self.selection.get()
        file = os.path.expanduser(file)
        return file

    def cancel_command(self, event=None):
        self.quit()

    def set_filter(self, dir, pat):
        if not os.path.isabs(dir):
            try:
                pwd = os.getcwd()
            except os.error:
                pwd = None
            if pwd:
                dir = os.path.join(pwd, dir)
                dir = os.path.normpath(dir)
        self.filter.delete(0, END)
        self.filter.insert(END, os.path.join(dir or os.curdir, pat or "*"))

    def set_selection(self, file):
        self.selection.delete(0, END)
        self.selection.insert(END, os.path.join(self.directory, file))


class LoadFileDialog(FileDialog):

    """File selection dialog which checks that the file exists."""

    title = "Load File Selection Dialog"

    def ok_command(self):
        file = self.get_selection()
        if not os.path.isfile(file):
            self.master.bell()
        else:
            self.quit(file)


class SaveFileDialog(FileDialog):

    """File selection dialog which checks that the file may be created."""

    title = "Save File Selection Dialog"

    def ok_command(self):
        file = self.get_selection()
        if os.path.exists(file):
            if os.path.isdir(file):
                self.master.bell()
                return
            d = Dialog(self.top,
                       title="Overwrite Existing File Question",
                       text="Overwrite existing file %r?" % (file,),
                       bitmap='questhead',
                       default=1,
                       strings=("Yes", "Cancel"))
            if d.num != 0:
                return
        else:
            head, tail = os.path.split(file)
            if not os.path.isdir(head):
                self.master.bell()
                return
        self.quit(file)


def test():
    """Simple test program."""
    root = Tk()
    root.withdraw()
    fd = LoadFileDialog(root)
    loadfile = fd.go(key="test")
    fd = SaveFileDialog(root)
    savefile = fd.go(key="test")
    print loadfile, savefile


#if __name__ == '__main__':
#    test()


# ===================================================================================
#                            main()  for testing.
# ===================================================================================

# Set the flags to write all the data and set flags.isdir = 0.
flags                      = dataflags()
flags.header               = 1
flags.filesize             = 1
flags.hierarchy            = 1
flags.timeticks            = 1
flags.bones                = 1
flags.alldata              = 1
flags.footer               = 1
flags.isdir                = 0

# Get a filename via a GUI.
root = Tk()
root.withdraw()
d                          = FileDialog(root)
fn                         = d.go(os.curdir, "*.*")
print 'file name = ' + fn     
if fn == None :
    exit()

# Error checks for files I can't process.
(head, tail)               = os.path.split( fn )
if tail == 'resource_wool.cas' :
    showwarning( 'Bad File', 'Can not process resource_wool, must terminate script.' )
    exit()
elif tail == 'navy_eastern.cas' :
    showwarning( 'Bad File', 'Can not process navy_eastern, must terminate script.' )
    exit()
elif tail == 'navy_egypt.cas' :
    showwarning( 'Bad File', 'Can not process navy_egypt, must terminate script.' )
    exit()
elif tail == 'navy_greek.cas' :
    showwarning( 'Bad File', 'Can not process navy_greek, must terminate script.' )
    exit()
elif tail == 'navy_roman.cas' :
    showwarning( 'Bad File', 'Can not process navy_roman, must terminate script.' )
    exit()
elif tail == 'navy_roman_shadow.cas' :
    showwarning( 'Bad File', 'Can not process navy_roman_shadow, must terminate script.' )
    exit()
elif tail == 'late_captain_northern_shadow.cas' :
    showwarning( 'Bad File', 'Can not process late_captain_northern_shadow, must terminate script.' )
    exit()
elif tail == 'spy.cas' :
    showwarning( 'Bad File', 'Can not process spy, must terminate script.' )
    exit()
elif tail == 'princess.cas' :
    showwarning( 'Bad File', 'Can not process princess, must terminate script.' )
    exit()
elif tail == 'priest.cas' :
    showwarning( 'Bad File', 'Can not process priest, must terminate script.' )
    exit()
elif tail == 'diplomat.cas' :
    showwarning( 'Bad File', 'Can not process diplomat, must terminate script.' )
    exit()
elif tail == 'barb_strat_map_captain.cas' :
    showwarning( 'Bad File', 'Can not process barb_strat_map_captain, must terminate script.' )
    exit()
elif tail == 'bishop.cas' :
    showwarning( 'Bad File', 'Can not process bishop, must terminate script.' )
    exit()
elif tail == 'captain_drag_model.cas' :
    showwarning( 'Bad File', 'Can not process captain_drag_model, must terminate script.' )
    exit()
elif tail == 'cardinal.cas' :
    showwarning( 'Bad File', 'Can not process cardinal, must terminate script.' )
    exit()
elif tail == 'carthage_strat_captain.cas' :
    showwarning( 'Bad File', 'Can not process carthage_strat_captain, must terminate script.' )
    exit()
elif tail == 'character_pontus.cas' :
    showwarning( 'Bad File', 'Can not process character_pontus, must terminate script.' )
    exit()
elif tail == 'crossed_swords.cas' :
    showwarning( 'Bad File', 'Can not process crossed_swords, must terminate script.' )
    exit()
elif tail == 'flood_water.cas' :
    showwarning( 'Bad File', 'Can not process flood_water, must terminate script.' )
    exit()
elif tail == 'general_pontus.cas' :
    showwarning( 'Bad File', 'Can not process general_pontus, must terminate script.' )
    exit()
elif tail == 'good_old_blue.cas' :
    showwarning( 'Bad File', 'Can not process good_old_blue, must terminate script.' )
    exit()
elif tail == 'inquisitor.cas' :
    showwarning( 'Bad File', 'Can not process inquisitor, must terminate script.' )
    exit()
elif tail == 'resource_chocolate.cas' :
    showwarning( 'Bad File', 'Can not process resource_chocolate, must terminate script.' )
    exit()
elif tail == 'resource_mine.cas' :
    showwarning( 'Bad File', 'Can not process resource_mine, must terminate script.' )
    exit()

(root, ext)                = os.path.splitext( fn )
if ext == ".cas" :
    fntxt                  = []
    convertcastoms3d( fn, fntxt, flags )
elif ext == ".ms3d" :
    fncas                  = root + "_converted.cas"
    convertms3dtocas( fn, fncas )


