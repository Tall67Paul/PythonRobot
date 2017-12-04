###########################################################################
#  Python Roomba Controller  
#  by Paul Schmitt.  March 2016.
#
#  Based upon the great Create 2 Tethered Driving Project code.  Thanks!  
#  To begin your Python Robot Controller program, go to the bottom of this 
#  program and look for "Start my Python Robot Controller below here".
#  
###########################################################################

from Tkinter import *
#import tkMessageBox
#import tkSimpleDialog
import math, numpy
import time
import thread
import socket
import select
import struct
import random
import sys, glob # for listing serial ports
import os  # to command the mp3 and wav player omxplayer

try:
    import serial
except ImportError:
    print "Import error.  Please install pyserial."
    raise

connection = None
global FAILURE
FAILURE = False

def toTwosComplement2Bytes( value ):
        """ returns two bytes (ints) in high, low order
        whose bits form the input value when interpreted in
        two's complement
        """
        # if positive or zero, it's OK
        if value >= 0:
            eqBitVal = value
            # if it's negative, I think it is this
        else:
            eqBitVal = (1<<16) + value
    
        return ( (eqBitVal >> 8) & 0xFF, eqBitVal & 0xFF )

# sendCommandASCII takes a string of whitespace-separated, ASCII-encoded base 10 values to send
def sendCommandASCII(command):
    cmd = ""
    for v in command.split():
        cmd += chr(int(v))
    sendCommandRaw(cmd)

# sendCommandRaw takes a string interpreted as a byte array
def sendCommandRaw(command):
    global connection
    try:
        if connection is not None:
            connection.write(command)
        else:
            print "Not connected."
    except serial.SerialException:
        print "Lost connection"
        connection = None
    #print ' '.join([ str(ord(c)) for c in command ])

# getDecodedBytes returns a n-byte value decoded using a format string.
# Whether it blocks is based on how the connection was set up.
def getDecodedBytes( n, fmt):
    global connection
        
    try:
        return struct.unpack(fmt, connection.read(n))[0]
    except serial.SerialException:
        print "Lost connection"
        tkMessageBox.showinfo('Uh-oh', "Lost connection to the robot!")
        connection = None
        return None
    except struct.error:
        print "Got unexpected data from serial port."
        return None

def bytesOfR( r ):
        """ for looking at the raw bytes of a sensor reply, r """
        print('raw r is', r)
        for i in range(len(r)):
            print('byte', i, 'is', ord(r[i]))
        print('finished with formatR')

def toBinary( val, numBits ):
        """ prints numBits digits of val in binary """
        if numBits == 0:  return
        toBinary( val>>1 , numBits-1 )
#        print((val & 0x01), end=' ')  # print least significant bit

def bitOfByte( bit, byte ):
    """ returns a 0 or 1: the value of the 'bit' of 'byte' """
    if bit < 0 or bit > 7:
        print('Your bit of', bit, 'is out of range (0-7)')
        print('returning 0')
        return 0
    return ((byte >> bit) & 0x01)

# get8Unsigned returns an 8-bit unsigned value.
def get8Unsigned():
    return getDecodedBytes(1, "B")

# get lowest bit from an unsigned byte
def getLowestBit():
    wheelsAndBumpsByte = getDecodedBytes(1, "B")
    print wheelsAndBumpsByte
    return bitOfByte(0, wheelsAndBumpsByte)

# get second lowest bit from an unsigned byte
def getSecondLowestBit():
    wheelsAndBumpsByte = getDecodedBytes(1, "B")
    print wheelsAndBumpsByte
    return bitOfByte(1, wheelsAndBumpsByte)

def bumped():
    sendCommandASCII('142 7') 
    time.sleep( 0.02 )
    bumpedByte = getDecodedBytes( 1, "B" )
    if bumpedByte == 0:
	return False
    elif bumpedByte > 3:
	print "CRAZY BUMPER SIGNAL!"
    else:
	return True

def cleanButtonPressed():
    sendCommandASCII('142 18') 
    buttonByte = getDecodedBytes( 1, "B" )
    if buttonByte == 0:
	return False
    elif buttonByte == 1:
	print "Clean Button Pressed!"
	return True
    elif buttonByte == 4:
	return False
    else:
	print "Some other button pressed!"
	FAILURE = True
	return False

def dockButtonPressed():
    sendCommandASCII('142 18') 
    buttonByte = getDecodedBytes( 1, "B" )
    if buttonByte <> 4:
	return False
    else:
	print "Dock button pressed!"
	return True

def shudder( period, magnitude, numberOfShudders):
    i = 0
    timestep = 0.02
    while i < numberOfShudders:
	i = i + 1
	#shake left
	t = 0
	while t < period:
	    driveDirectRot( 0, magnitude )
	    t = t + timestep
	    time.sleep( timestep )
	#Shake right
	t = 0
	while t < period:
	    driveDirectRot( 0, -magnitude )
	    t = t + timestep
	    time.sleep( timestep )
    driveDirect( 0, 0 )  # stop the previous motion command

def onConnect():
    global connection

    if connection is not None:
        print "Oops- You're already connected!"
        return

    try:
        ports = getSerialPorts()
	print "Available ports:\n" + '   '.join(ports)
        #port = raw_input("Port? Enter COM port to open.\nAvailable options:\n" + '\n'.join(ports))
	port = str( ports[0] )  # I'm guessing that the Roomba port is first in the list.  So far this works!  :)
    except EnvironmentError:
        port = raw_input("Port?  Enter COM port to open.")

    if port is not None:
        print "Trying " + str( port ) + "... "
    try:   #:tty
        #connection = serial.Serial('/dev/ttyUSB0', baudrate=115200, timeout=1)
        #connection = serial.Serial( str(port), baudrate=115200, timeout=1 )
        connection = serial.Serial( str(ports[0]), baudrate=115200, timeout=1 )
        print "Connected!"
    except:
        print "Failed.  Could not connect to " + str( port )

def getSerialPorts():
    """Lists serial ports
    From http://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python

    :raises EnvironmentError:
        On unsupported or unknown platforms
    :returns:
        A list of available serial ports
    """
    if sys.platform.startswith('win'):
        ports = ['COM' + str(i + 1) for i in range(256)]

    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this is to exclude your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')

    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')

    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result    

def driveDirectTime( left, right, duration ):
    print"driveDirectTime()"
    t = 0   # initialize timer
    while t < duration:
        driveDirect( left, right )
        time.sleep( 0.05 )
        t = t + .05
    driveDirect( 0, 0 )  # stop

def driveDirect( leftCmSec = 0, rightCmSec = 0 ):
    """ sends velocities of each wheel independently
           left_cm_sec:  left  wheel velocity in cm/sec (capped at +- 50)
           right_cm_sec: right wheel velocity in cm/sec (capped at +- 50)
    """
    print "driveDirect()"
    if leftCmSec < -50: leftCmSec = -50
    if leftCmSec > 50:  leftCmSec = 50
    if rightCmSec < -50: rightCmSec = -50
    if rightCmSec > 50: rightCmSec = 50
    # convert to mm/sec, ensure we have integers
    leftHighVal, leftLowVal = toTwosComplement2Bytes( int( leftCmSec * 10 ) )
    rightHighVal, rightLowVal = toTwosComplement2Bytes( int( rightCmSec * 10 ) )

    # send these bytes and set the stored velocities
    byteListRight = ( rightHighVal , rightLowVal )
    byteListLeft = ( leftHighVal , leftLowVal )
    sendCommandRaw(struct.pack( ">Bhh", 145, int(rightCmSec * 10), int(leftCmSec * 10) ))
    return

def driveDirectRot( robotCmSec = 0, rotation = 0 ):
    """ implements the driveDirect with a given rotation
        Positive rotation turns the robot CCW
        Negative rotation turns the robot CW
    """
    print "driveDirectRot()"
    vl = robotCmSec - rotation/2
    vr = robotCmSec + rotation/2
    driveDirect ( vl, vr )

def initiateRobotCommunication():
    print "Initiating Communications to the Create 2 Robot..."
    onConnect()
    time.sleep( 0.3 )
    sendCommandASCII('128')   # Start Open Interface in Passive
    time.sleep( 0.3 )
    sendCommandASCII('140 3 1 64 16 141 3')  # Beep
    time.sleep( 0.3 )
    #sendCommandASCII('131')   # Safe mode
    sendCommandASCII( '132' )   # Full mode 
    time.sleep( 0.3 )
    sendCommandASCII('140 3 1 64 16 141 3')  # Beep
    time.sleep( 0.1 )
    sendCommandASCII('139 4 0 255')  # Turn on Clean and Dock buttons
    time.sleep( 0.03 )

def closeRobotCommunication():
    print "Closing Communication to the Create 2 Robot..."
    driveDirect( 0, 0 )  # stop robot if moving
    time.sleep( 0.05 )
    sendCommandASCII('140 3 1 64 16 141 3')  # Beep
    time.sleep( 0.3 )
    #sendCommandASCII('139 0 0 0')  # Turn off Clean and Dock buttons
    time.sleep( 0.03 )
    sendCommandASCII('138 0')  # turn off vacuum, etractors, and side brush
    time.sleep( 0.03 )
    #sendCommandASCII( '7' )  # Resets the robot 	
    sendCommandASCII( '173' )  # Stops the Open Interface to Roomba
    time.sleep( 0.3 )
    connection.close()
    time.sleep( 0.1 )
    raise SystemExit	#  Exit program


##########################################################################
##########################################################################
#---------Start my Python Robot Controller Program below here!------------
#---------Change the code below
##########################################################################
##########################################################################

#Hello, world!
print "Hellooooooooooooo, world!"
print "Starting my Python Robot Controller Program.  This is so cool!"

#Set any variables here
#myVariable = 3

#Open the robot communication interface 
initiateRobotCommunication()


#---------------Start My robot program.----------------------
#---------------Change the code below.----------------
driveDirect( 50, 50 )     # Go Straight at 50 cm/sec
time.sleep( 3 )           # Wait 3 seconds
driveDirect( 0, 0 )       # Full stop!
#driveDirectTime( 10, 10, 2 )  # Go straight for two seconds at 10 cm/sec
driveDirectRot( 0, 100)   # Turns the robot counterclockwise.  Right wheel at 50cm/s.  Left wheel at -50cm/s.  
time.sleep( 5 )           # Wait 5 seconds
driveDirectRot( 0, -10)   # Slowly turns the robot clockwise.  Right wheel at -5cm/s.  Left wheel at 5cm/s.
driveDirect( 0, 0 )       # Full stop!
time.sleep( 1 )           # Wait one second 
shudder( 0.05, 45, 5 )    # This shakes the robot back and forth quickly five times
driveDirect( 0, 0 )       # Full stop! 
time.sleep( 1 )           # Wait one second
shudder( 0.05, 45, 3 )    # This shakes the robot back and forth quickly three times
driveDirect( 0, 0 )       # Full stop!

#if cleanButtonPressed(): driveDirect( 0, 0 )  # If CLEAN button is pressed stop robot.  
#if bumped(): driveDirect( -10, -10 )          # If the bumper is hit, go backwards
#  Note: The communication interface will become corrupt
#  once the robot goes to sleep after about a minute or so of inactivity.  
#  One workaround is to use the following command periodically to keep the robot awake.
#sendCommandASCII('139 4 0 255')  # Turn on Clean and Dock buttons, a harmless command to keep the robot serial link open, a heartbeat

#Close the robot communication interface.  Do not delete this line.  This is needed to keep the communications protocol happy.
closeRobotCommunication()



