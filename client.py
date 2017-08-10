###########################################
# Music Signaling Pipeline Prototype
#   Client: Simple interface to write 
#		modification messages in realtime
#
# Author: Ishwarya Ananthabhotla
###########################################

import socket

class Client:
	def __init__(self, host='localhost', port=8089): 
		self.clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.clientsocket.connect((host, port))

	# add other parameters here eventually
	def send_message(self, level, header='msg'):
		msg_length = self.clientsocket.send(header + ':' + str(level))
		return msg_length

	def end(self):
		self.clientsocket.close()



