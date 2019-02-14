#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 10 15:21:38 2019
neck idle function

@author: ustyui
"""

import rospy
from silva_beta.msg import Evans

import threading
import numpy as np
from numpy import random as rd
from math import *

import time

from sensor_msgs.msg import Joy


_RATE = 50

class neck():
    
    ### initialization ###
    def __init__(self):
        
        self._neck = [0, 0, 0, 0, 0]
        self._neck_slave = [0, 0, 0]
        self._count = 0
        self._ct = [1, 1, 1, 1, 1]
        self._timebias = 0
        self._payload = [0,0,0,0,0]
        

        # random variables
        self._length = [0, 0, 0, 0, 0]
        self._startpos = [0.0, 0.0, 0.0, 0.0, 0.0]
        self._starttime = [0.0, 0.0, 0.0, 0.0, 0.0]
        self._sinscope = [0.0, 0.0, 0.0, 0.0, 0.0]
        self._nextpos = [0.0, 0.0, 0.0, 0.0, 0.0]
        self._gototime = [0.0, 0.0, 0.0, 0.0, 0.0]
        self._sinscopeB = [0.0, 0.0, 0.0, 0.0, 0.0]
        
        # values
        self._rel = [0.0, 0.0, 0.0, 0.0, 0.0]
        
        #message publish
        self._pub_msg = Evans()
        
        # publishers
        self.pub = rospy.Publisher('/silva/idle_local/intention', Evans, queue_size=10)
        # subscribers
        self.sub_joy = rospy.Subscriber('/joy', Joy, self.joy_cb)
        
    ### callback functions ###
        
    def joy_cb(self, msg):
        axes = msg.axes
        self._neck_slave = [axes[1],axes[2],axes[3]]
        
    
    ### threading functions ###
    # _amp: time base , _sn: serial number 
    def neck_idle(self, _amp, _sn, run_event):
        # create a random for time
        rate = rospy.Rate(_RATE)
        while run_event.is_set() and not rospy.is_shutdown():
            # add counter
        
            self._ct[_sn] += 1           
            
            # judge
            "VARIABLE GENERATION, UPDATE EVERY PERIOD"
            if self._ct[_sn] > self._length[_sn]:
                
                # count to zero
                self._ct[_sn] = 0
                
                _amp = 3 # for debug
                _interval = _amp + _amp * rd.rand()
                _randval = _interval - _amp
                
                self._length[_sn] = _interval * _RATE # period length
                
                # generate start time, between 0 to _amp
                self._starttime[_sn] = _amp * rd.rand() * _RATE
                
                # generate sin scope, small 
                self._sinscope[_sn] = 0.2 * rd.rand()
                "SIGN, CONTROLED BY REL"
                sgn = np.sign(rd.rand()-0.5 - self._rel[_sn]*0.5)
                
                # generate goto position
                self._nextpos[_sn] = rd.rand()
                
                # generate goto time
                self._gototime[_sn] = (0.2 * _randval + 0.8*_randval*rd.rand())*_RATE
                # goto time -> 8 factor
                _tanhf = 8.0/self._gototime[_sn]
                # generate next sin scope
                self._sinscopeB[_sn] = 0.2 * rd.rand()
                
                # init start position with rel
                self._startpos[_sn] = self._rel[_sn]
                
            "WAVE GENERATION, UPDATE EVERY RATE"
            # do cal
            # if counter is below start time
            if self._ct[_sn] < self._starttime[_sn]:
                ## do flat
                self._rel[_sn] = self._startpos[_sn] + sgn * self._sinscope[_sn] * \
                                sin(float(self._ct[_sn])/_RATE)
                                
            # if counter is between starttime and goto time
            elif self._ct[_sn] > self._starttime[_sn] and self._ct[_sn] < (self._starttime[_sn]+self._gototime[_sn]):
                ## do tanh
                _phase = self._ct[_sn] - self._starttime[_sn] 
                ## when enter, transfer value
                if _phase <= 1:
                    self._startpos[_sn] = self._rel[_sn]
                    #print 'sp',self._startpos[_sn]
                else:
                
                    self._rel[_sn] = self._startpos[_sn] + sgn * \
                    0.5*self._nextpos[_sn]*(1 + np.tanh(_tanhf*_phase - 4))
                    #print 'rl',self._rel[_sn]
            elif self._ct[_sn] >= (self._starttime[_sn]+self._gototime[_sn]):
                _phase = self._ct[_sn] - self._starttime[_sn]-self._gototime[_sn]
                if _phase <= 1:
                    self._startpos[_sn] = self._rel[_sn]
                else:
                    self._rel[_sn] = self._startpos[_sn] + sgn * self._sinscopeB[_sn] * \
                                sin(float(self._ct[_sn])/_RATE)
                
            ## check the board
            if self._rel[_sn] >= 1.05:
                self._rel[_sn] = 1.0
            if self._rel[_sn] <= -1.05:
                self._rel[_sn] = -1.0
                
            self._neck[_sn] = 50*self._rel[_sn]
            rate.sleep()
        
    ### make message ###
    def make_message(self, msgid, seq, payload):
        # make message
        self._pub_msg.header.stamp = rospy.Time.now()
        self._pub_msg.seq = seq # neck motion
        self._pub_msg.name = 'arml'
        self._pub_msg.msgid = msgid
        self._pub_msg.payload = payload
        
    def start(self):
        rospy.loginfo("ARMR")
        
        loop_rate = rospy.Rate(_RATE)
        
        # signal flag for running threads
        run_event = threading.Event()
        run_event.set()
        
        # thread open
    
        move_shoulderr = threading.Thread(target = self.neck_idle, args = \
        (3, 0, run_event))
        move_shoulderl = threading.Thread(target = self.neck_idle, args = \
        (3, 1, run_event))
        move_yaw = threading.Thread(target = self.neck_idle, args = \
        (3, 2, run_event))
        move_roll = threading.Thread(target = self.neck_idle, args = \
        (3, 3, run_event))
        move_pitch = threading.Thread(target = self.neck_idle, args = \
        (3, 4, run_event))
        
        move_shoulderr.start()
        move_shoulderl.start()
        move_yaw.start()
        move_roll.start()
        move_pitch.start()
        
        
        while not rospy.is_shutdown():
            
            
            ### main function ###
            # if no input for neck , activate slave
#            if sum(self._neck) == 0:
#                # go joy
#                self.joy_slave()
#                self.make_message(3,3,self._payload)            
#            
#                self.pub_s.publish(self._pub_msg)
            
            self._payload[0] = int(1.5*self._neck[0])
            self._payload[1] = int(2*self._neck[1])
            self._payload[2] = int(2*self._neck[2])+40
            self._payload[3] = int(2*self._neck[2])
            self._payload[4] = int(2*self._neck[4])
            
            self.make_message(1,1,self._payload)
            self.pub.publish(self._pub_msg)                
            # else, do tanh/ sin move
            print self._payload
            
            loop_rate.sleep()
            
if __name__ == "__main__":
    neckmotion = neck()
    
    nh = rospy.init_node("arml_idlemotion")
    
    neckmotion.start()
            
            