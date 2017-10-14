"""
Demo using the ioHub Serial device, a generic interface to a serial port.

This demo is setup to read the serial output from the
MinIMU-9 v3 breakout board ( http://www.pololu.com/product/2468 )
via a Teensy 3.x ( https://www.pjrc.com/teensy/index.html ) running the
MinIMU-9 AHRS Arduino example.

The Teensy 3.x is connected to the ioHub computer using it's USB to Serial
connection.

The Teensy 3.x MUST BE programmed with the MinIMU-9 AHRS Arduino example
( https://github.com/pololu/minimu-9-ahrs-arduino ). The example sketch and
required libraries for the two chips used on the board are compatible with
Teensy 3.0 or 3.1.

The MinIMU-9 AHRS demo outputs a \r\n terminated string for each reading
generated by the sketch. Each line is in the form:

!ANG:0.01,-0.07,101.14

which represents the roll, pitch, and yaw angle calculated from the raw sensor
data read from the MinIMU-9 board.

By creating an ioHub serial.Serial device, and specifying appropriate
'event_parser' configuration settings, the serial data read is parsed into
SerialInput events. Each event contains all the standard iohub event fields as
well as a string data field containing the roll,pitch,yaw values.

Remember SerialInput events save parsed data in string format, so to do
analysis on the serial event data, each data string will likely
need to be parsed by the analysis program.  In this example, the data field of
each event would be parsed by the analysis program as follows:

roll, pitch, yaw = [float(v) for v in data.split(',')]

providing a float value for the roll, pitch, yaw reading sent.

Demo Created: April 16th, 2014.
By: Sol Simpson
"""
from __future__ import print_function
from __future__ import division
from past.utils import old_div
import time
from psychopy import core
from psychopy.iohub import launchHubServer

psychopy_mon_name = 'testMonitor'
exp_code = '9dof'
sess_code = 'S_{0}'.format(int(time.mktime(time.localtime())))
iohubkwargs = {'psychopy_monitor_name':psychopy_mon_name,
                'experiment_code': exp_code,
                'session_code': sess_code,
                'serial.Serial': dict(name='serial', port='COM6', baud=115200,
                                   event_parser=dict(prefix='!ANG:',
                                                     delimiter='\r\n'))
               }
io = launchHubServer(**iohubkwargs)
kb = io.devices.keyboard
ser = io.devices.serial
event_count = 0

io.clearEvents('all')
print("Saving Serial Port Events. Press any key to exit.")
ser.enableEventReporting(True)
stime = core.getTime()

while not kb.getEvents():
    event_count += len(ser.getEvents())
    print('Serial Event Count:', event_count, '\r', end=' ')
    core.wait(0.01, 0.0)

etime = core.getTime()
ser.enableEventReporting(False)
print()
print("Received approx. %.2f events / second."%(old_div(event_count,(etime-stime))))
io.quit()
## EOD

# Below code is from original 9DOF board demo, may be of interest for further
# conversion of angle data saved.
#
#    grad2rad = 3.141592/180.0
#    line = ser.readline()
#    print "%.3f\t[%s]"%(getTime()*1000.0,line)
#    if line.find("!ANG:") != -1:          # filter out incomplete (invalid) lines
#        line = line.replace("!ANG:","")   # Delete "!ANG:"
#        f.write(line)                     # Write to the output log file
#        words = string.split(line,",")    # Fields split
#        if len(words) > 2:
#            try:
#                roll = float(words[0])*grad2rad
#                pitch = float(words[1])*grad2rad
#                yaw = float(words[2])*grad2rad
#                print roll, pitch, yaw
#            except Exception:
#                print "Invalid line"

#            axis=(cos(pitch)*cos(yaw),-cos(pitch)*sin(yaw),sin(pitch))
#            up=(sin(roll)*sin(yaw)+cos(roll)*sin(pitch)*cos(yaw),sin(roll)*cos(yaw)-cos(roll)*sin(pitch)*sin(yaw),-cos(roll)*cos(pitch))
#            cil_roll.axis=(0.2*cos(roll),0.2*sin(roll),0)
#            cil_roll2.axis=(-0.2*cos(roll),-0.2*sin(roll),0)
#            cil_pitch.axis=(0.2*cos(pitch),0.2*sin(pitch),0)
#            cil_pitch2.axis=(-0.2*cos(pitch),-0.2*sin(pitch),0)
#            arrow_course.axis=(0.2*sin(yaw),0.2*cos(yaw),0)
#ser.close()
#f.close()
