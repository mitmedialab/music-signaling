########################################
# Music Signaling Pipeline Prototype
#	Global Settings: shared global
#	variables
#
# Author: Ishwarya Ananthabhotla
#########################################

from collections import deque

def init():
	global audio_buffer
	global sr
	sr = 22050
	global ptr
	ptr = 0L
	global song_index
	song_index = None
	global pop_alert
	pop_alert = False
	global pop_subtlety
	global msg_q
	msg_q = deque()
	print "Finished initializing."