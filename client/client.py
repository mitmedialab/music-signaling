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
	def signal(self, level, header='msg'):
		msg_length = self.clientsocket.send(header + ':' + str(level))
		return msg_length

	def end_server(self, header='end'):
		try:
			msg_length = self.clientsocket.send(header + ':' + str(0))
		except socket.error:
			print "Server already closed."		

	def end_client(self):
		self.clientsocket.close()



