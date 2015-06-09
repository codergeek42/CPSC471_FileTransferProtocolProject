#!/bin/python3 -tt
# vim:set ts=4:
################################################################################
# Name:			Peter Gordon
# Email:		peter.gordon@csu.fullerton.edu
# Course:		CPSC 471, T/Th 11:30-12:45
# Instructor:	Dr. M. Gofman
# Assignment:	3 (FTP Server/Client)
################################################################################
"""This module provides the SimpleFTPServerConnectionHandler type."""

import re
import socket

from os.path import getsize, isdir, isfile
from ServerConnection import ServerConnectionHandler
from utils import debugPrint, listFiles, recvAll, recvFile, recvLine, sendFile, sendStr


class SimpleFTPServerConnectionHandler(ServerConnectionHandler):
	"""A subclass of the ServerConnectionHandler interface which implements a
	rudimentary file transfer server. The full protocol specification can be
	found in the included README file."""

	# This uses a dictionary to manage protocol command handlers. Each key is a
	# regular expression defining the one-line pattern for the command, and the
	# value is a tuple containing the function to call (which will be passed
	# the re.match object), a boolean flag if that handler needs a data channel
	# established, another to mark if the data channel should be torn down
	# after that function is called, as well as any additional parameters
	# (which will be passed to that function as-is, AFTER the re.match object).
	#
	# NB: _connSock and _clientAddr members are inherited from ServerConnection.
	
	__slots__ = ("_continueHandling", "_dataSock", "_protocolHandlers", "_config")

	def __init__(self, connSock, clientAddr):
		super().__init__(connSock, clientAddr)
		self._dataSock = None
		self._config = {
				"chunk_size": 65536,
				"passive":	False,
				"persistent": False,
				"put_behavior": "ERROR",
				"timeout": 10
				}
		self._continueHandling = True
		self._protocolHandlers = {}

		# DATA -- Opens an ephemeral data connection. (Specifying the port and
		# ID is needed if passive mode is not enabled.)
		self.registerProtocolHandler(r"DATA( (?P<port>\d+))?",
				self._protocol_DATA, needData=False, closeData=False)
	
		# GET <filename>
		# Sends the contents of the requested file to the client.
		self.registerProtocolHandler(r"GET (?P<filename>.+)",
				self._protocol_GET, needData=True, closeData=True)
		
		# GETCONFIG
		# Invoked by the client to get the current transfer settings, listed
		# under SETCONFIG below.
		self.registerProtocolHandler(r"GETCONFIG",
				self._protocol_GETCONFIG, needData=False, closeData=False)		
		
		# GO AWAY
		# Instructs the server to stop processing input from the client socket,
		# then close the control and data connections.
		# "Do you wanna build a protocol?..." ;)
		self.registerProtocolHandler(r"GO AWAY",
				self._protocol_GO_AWAY, needData=False, closeData=True)

		# LS
		# Sends a file listing to the client.
		self.registerProtocolHandler(r"LS",
				self._protocol_LS, needData=True, closeData=True)

		# PUT <size> <filename>
		# Instructs the server to read <size> bytes from the data connection
		# and store the data locally in the file named <filename>.
		self.registerProtocolHandler(r"PUT (?P<size>\d+) (?P<filename>.+)",
				self._protocol_PUT, needData=True, closeData=True)
		
		# SETCONFIG <option> <value>
		# Invoked by the client to modify transfer settings.
		# <option> is one of:
		#	CHUNKSIZE -- (integer, default 65536)
		#		The chunk size (bytes) used for reading and writing file data
		#		in GET/PUT requests.
		#
		#	PASSIVE -- (YES/No string, default NO)
		#		Normally when a data connection is requested, the client
		#		listens on an ephemeral port for a connection initiated by the
		#		server. If enabled, passive mode will instead cause the server
		#		to listen on the ephemeral port, and the connection will then
		#		be initiated by the client. (This becomes useful for passing
		#		through NAT systems.)
		#
		#	PERSISTENTDATA -- (YES/NO string, default NO)
		#		Whether the data connection should be persistent (that is,
		#		created once and used for all subsequent data transfters,
		#		instead of per-command). If it is changed from YES to NO and a
		#		data connection is already established, then that data
		#		connection will be closed after the next transfer which uses it
		#		(or when the connection is terminated via the GO AWAY command.)
		#
		#	PUTBEHAVIOR -- (string, default ERROR)
		#		What to do when a PUT request attempts to write to a file that
		#		already exists. This can be one of:
		#		* APPEND -- Append the data to the existing file
		#		* ERROR -- Return an error to the client; 
		#		* OVERWRITE -- Forcibly overwrite the file.
		#
		#	SOCKETTIMEOUT -- (integer, default 10)
		#		Time (seconds) to wait for socket connections when requesting a
		#		data channel.
		#
		# (NB: if you add a config option here, you also need to update
		#		the GETCONFIG handler accordingly.)
		self.registerProtocolHandler(r"SETCONFIG CHUNKSIZE (?P<value>\d+)",
				self._protocol_SETCONFIG_CHUNKSIZE, needData=False, closeData=False)

		self.registerProtocolHandler(r"SETCONFIG PASSIVE (?P<value>YES|NO)",
				self._protocol_SETCONFIG_PASSIVE, needData=False, closeData=False)

		self.registerProtocolHandler(r"SETCONFIG PERSISTENTDATA (?P<value>YES|NO)",
				self._protocol_SETCONFIG_PERSISTENTDATA, needData=False, closeData=False)

		self.registerProtocolHandler(r"SETCONFIG PUTBEHAVIOR (?P<value>APPEND|ERROR|OVERWRITE)",
				self._protocol_SETCONFIG_PUTBEHAVIOR, needData=False, closeData=False)

		self.registerProtocolHandler(r"SETCONFIG SOCKETTIMEOUT (?P<value>\d+)",
				self._protocol_SETCONFIG_SOCKETTIMEOUT, needData=False, closeData=False)

		
	def handleClientConnection(self):
		"""The workhorse function of this server implementation.
		Repeatedly processes client commands one-by-one until the client
		exits."""
		
		while self._continueHandling:
			try:
				ctrlLine = recvLine(self._connSock)
			except socket.error:
				ctrlLine = None
							
			if not ctrlLine:
				debugPrint("SERVER: EOF from client socket.")
				break # Stop 
			for (regex, handler) in self._protocolHandlers.items():
				matchObj = re.match("^"+regex+"$", ctrlLine)
				if matchObj:
					(handlerFunc, needData, closeData, args, kwargs) = handler
					if needData and not self._dataSock:
						sendStr(self._connSock, "ERR NO DATA CONNECTION\n")
						break
					handlerFunc(matchObj, *args, **kwargs)
					if not self._config["persistent"] and closeData and self._dataSock:
						self._dataSock.close()
						self._dataSock = None
					break
			else:
				sendStr(self._connSock, "ERR BAD REQUEST\n")
		self._connSock.close()
		if self._dataSock:
			self._dataSock.close()
		debugPrint("SERVER: Client disconnected.")
		
		
	def registerProtocolHandler(self, regex, handlerFunc, needData, closeData, *args, **kwargs):
		"""Register handlerFunc with the connection so that if a client command
		matches the given regex, that function is called with its appropriate
		re.match object and any other arguments. The needData and closeData
		flags denote, respectively, if the handler function needs a data
		connection, and whether that data connection should be closed when it
		isfinished. Attempting to add a regex which is already matched by an
		existing rule will fail with an error message.)"""
		
		for handler in self._protocolHandlers.keys():
			if re.match("^"+handler+"$", regex):
				debugPrint("SERVER: Invalid rule {rule}: Already matched by {old}.".format(
						rule=regex, old=handler))
				break
		else:
			self._protocolHandlers[regex] = (handlerFunc, needData, closeData, args, kwargs)

	###
	# The protocol handlers....
	###
	def _protocol_DATA(self, matchObj):
		"""Handler for DATA command: Opens a data connection.  """
		
		if self._dataSock:
			if self._config["persistent"]:
				sendStr(self._connSock, "ERR DATA ALREADY CONNECTED\n")
				return
			else:
				self._dataSock.close()
				self._dataSock = None
			
		if self._config["passive"]:	
			dataConn = None
			try:
				dataConn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				dataConn.bind(("", 0))
				dataConn.settimeout(self._config["timeout"])
				dataConn.listen(1)
				dataPort = dataConn.getsockname()[1]
				sendStr(self._connSock, "READY {p}\n".format(p=dataPort))
				while True:	
					(clientDataSock, clientAddr) = dataConn.accept()
					if clientAddr[0] == self._clientAddr[0]:
						sendStr(self._connSock, "OK {p}\n".format(p=dataPort))
						self._dataSock = clientDataSock
						return
					else:
						clientDataSock.close()		
			except socket.timeout as err:
				sendStr(self._connSock, "ERR DATA SOCKET TIMEOUT\n")
		else: # Not passive
			dataPort = matchObj.group("port")
			if not dataPort: 
				sendStr(self._connSock, "ERR NO PORT SPECIFIED\n")
				return
			dataPort = int(dataPort)
			dataSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			dataSock.settimeout(self._config["timeout"])
			try:
				dataSock.connect((self._clientAddr[0], dataPort))
			except socket.timeout as err:
				sendStr(self._connSock, "ERR DATA SOCKET TIMEOUT\n")
			except socket.error as err:
				sendStr(self._connSock, "ERR SOCKET ERROR")
			else:
				self._dataSock = dataSock
				sendStr(self._connSock, "OK {port}\n".format(port=dataPort))
				return
				

	def _protocol_GO_AWAY(self, matchObj):
		"""Handler for GO AWAY command: Closes the control connection."""
		
		# Disabling persistence ensures that the calling protocol handler will
		# close the data connection upon finishing (due to its closeData flag
		# being set).
		self._config["persistent"] = False
		self._continueHandling = False
		sendStr(self._connSock, "OK BYE\n")
		self._connSock.close()
		
		
	def _protocol_GETCONFIG(self, matchObj):
		"""Handler for GETCONFIG command: Retrieves some configuration data."""
		
		conf = "OK 5\n"
		conf += "CHUNKSIZE {size}\n".format(size=self._config["chunk_size"])
		conf += "PASSIVE {yn}\n".format(yn="YES" if self._config["persistent"] else "NO")
		conf += "PERSISTENTDATA {yn}\n".format(yn="YES" if self._config["persistent"] else "NO")
		conf += "PUTBEHAVIOR {put}\n".format(put=self._config["put_behavior"])
		conf += "SOCKETTIMEOUT {timeout}\n".format(timeout=self._config["timeout"])
		sendStr(self._connSock, conf)


	def _protocol_GET(self, matchObj):
		"""Handler for the GET command: Downloads a file from the server."""
		
		fileName = matchObj.group("filename")
		if isdir(fileName):
			sendStr(self._connSock, "ERR FILE IS A DIRECTORY\n")
		elif not isfile(fileName):
			sendStr(self._connSock, "ERR FILE DOES NOT EXIST\n")
		else:
			fileSize = getsize(fileName)
			debugPrint("SERVER: Sending {fname}".format(fname=fileName))
			try:
				sendStr(self._connSock, "READY {size}\n".format(size=fileSize))
				sendFile(self._dataSock, fileName, self._config["chunk_size"])
			except (PermissionError, IOError):
				sendStr(self._connSock, "ERR CANNOT READ FILE\n")
			else:
				sendStr(self._connSock, "OK {size}\n".format(size=fileSize))



	def _protocol_LS(self, matchObj):
		"""Handler for the LS command: Retrieves a listing of file names/sizes
		from the server."""
		
		listing = listFiles(".")
		if not len(listing):
			sendStr(self._connSock, "ERR NO FILES\n")
		else:
			sendStr(self._connSock, "OK {size}\n".format(size=len(listing)))
			sendStr(self._dataSock,  listFiles("."))

		
	def _protocol_PUT(self, matchObj):
		"""Handler for the PUT command: Uploads a file to the server."""
		
		behavior = self._config["put_behavior"]
		fileName = matchObj.group("filename")
		fileSize = int(matchObj.group("size"))
		fileMode = "wb"
		
		if isdir(fileName):
			sendStr(self._connSock, "ERR FILE IS A DIRECTORY\n")
			return
		elif isfile(fileName):
			if behavior == "ERROR":
				sendStr(self._connSock, "ERR FILE EXISTS\n")
				return
			elif behavior == "APPEND":
				fileMode = "ab"
		
		sendStr(self._connSock, "READY {size}\n".format(size=fileSize, name=fileName))
		chunkSize = self._config["chunk_size"]
		try:
			numBytesWritten = recvFile(self._dataSock, fileSize, fileName, fileMode, chunkSize)
		except (PermissionError, IOError):
			sendStr(self._connSock, "ERR CANNOT WRITE TO FILE\n")
		else:
			if numBytesWritten < fileSize:
				sendStr(self._connSock, "ERR INCOMPLETE DATA\n")
			else:
				sendStr(self._connSock, "OK {size}\n".format(size=fileSize))


	def _protocol_SETCONFIG_CHUNKSIZE(self, matchObj):
		"""Handler for the SETCONFIG CHUNKSIZE command: Changes the transfer
		chunk size (bytes)."""
		
		value = int(matchObj.group("value"))
		if value < 1:
			sendStr(self._connSock, "ERR CHUNKSIZE MUST BE POSITIVE")
		else:
			self._config["chunk_size"] = value
			sendStr(self._connSock, "OK CHUNKSIZE {size}\n".format(size=value))
	
	
	def _protocol_SETCONFIG_PASSIVE(self, matchObj):
		"""Handler for the SETCONFIG PASSIVE command: Enables/disables passive
		data transfer mode."""
		
		value = matchObj.group("value")
		self._config["passive"] = (value == "YES")
		sendStr(self._connSock, "OK PASSIVE {option}\n".format(
				option="ENABLED" if value == "YES" else "DISABLED"))


	def _protocol_SETCONFIG_PERSISTENTDATA(self, matchObj):
		"""Handler for the SETCONFIG PERSISTENTDATA command: Enables/disables a
		persistent data connection."""
		
		value = matchObj.group("value")
		self._config["persistent"] = (value == "YES")
		sendStr(self._connSock, "OK PERSISTENTDATA {option}\n".format(
				option="ENABLED" if value == "YES" else "DISABLED"))
		
		
	def _protocol_SETCONFIG_PUTBEHAVIOR(self, matchObj):
		"""Handler for the SETCONFIG PUTBEHAVIOR command: Changes the PUT
		behavior when a file with the same name already exists on the server."""
				
		value = matchObj.group("value")
		self._config["put_behavior"] = value
		sendStr(self._connSock, "OK PUTBEHAVIOR {action}\n".format(action=value))
		
		
	def _protocol_SETCONFIG_SOCKETTIMEOUT(self, matchObj):
		"""Handler for the SETCONFIG SOCKETTIMEOUT command: Changes the socket
		timeout."""
		
		value = matchObj.group("value")
		self._config["timeout"] = value
		sendStr(self._connSock, "OK TIMEOUT {timeout}\n".format(timeout=value))
