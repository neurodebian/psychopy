 # -*- coding: utf-8 -*-
"""
Simple example of how to enable ioSync digital input events. The demo starts
the iosync with digital input events enabled. An ioSync DigitalInputEvent is 
created each time one of the eight digital input lines changes state. The
event returns a 'state' byte, giving the value of all input lines when 
the event occurred. 

ioSync supports 8 digital inputs. Digital inputs are sampled at 1000 Hz.
 
A state of 0 indicates no input lines are high. If DI_0
is high, state will equal 1, DI_1 = 2,  DI_2 = 4 etc. 

So digital input state = sum(2**di), where di is the index of an input that
is high, bound by 0 <= di <= 7.

Digital inputs which have a open ended wire connected to it (i.e. the input 
wire is not also connected to a stable digital input source) will 'float'; 
which will cause rapid random toggling of the digital input state. Only connect
a lead to a digital input if it is also connected to a stable digital input 
source.

IMPORTANT: Input voltage to a digital input pin must be between 0.0 V and 3.3 V 
or you may damage the Teensy 3. The Teensy 3.1 supports digital inputs up to
5 V. 

"""

import numpy as np    
import time
from psychopy import core
from psychopy.iohub import launchHubServer,Computer
getTime=core.getTime

io=None
mcu=None

try:
    psychopy_mon_name='testMonitor'
    exp_code='events'
    sess_code='S_{0}'.format(long(time.mktime(time.localtime())))
    
    iohub_config={
    "psychopy_monitor_name":psychopy_mon_name,
    "mcu.iosync.MCU":dict(serial_port='COM8',monitor_event_types=['DigitalInputEvent',]),
    "experiment_code":exp_code, 
    "session_code":sess_code
    }
    
    io=launchHubServer(**iohub_config)
    
    display=io.devices.display
    mcu=io.devices.mcu
    kb=io.devices.keyboard
    experiment=io.devices.experiment
        
    mcu.enableEventReporting(True)
    
    io.clearEvents("all")   
    i=0
    while not kb.getEvents():   
        mcu_events=  mcu.getEvents()  
        for mcu_evt in mcu_events:
            print'{0}\t{1}\t{2}'.format(mcu_evt.time,mcu_evt.device_time,
                                                                 mcu_evt.state
                                                                 )
            
    io.clearEvents('all')
except:
    import traceback
    traceback.print_exc()    
finally:
    if mcu:    
        mcu.enableEventReporting(False)   
    if io:
        io.quit() 
