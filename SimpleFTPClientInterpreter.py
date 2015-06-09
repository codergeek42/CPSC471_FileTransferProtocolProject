#!/bin/python3 -tt
# vim:set ts=4:
################################################################################
# Name:			Peter Gordon
# Email:		peter.gordon@csu.fullerton.edu
# Course:		CPSC 471, T/Th 11:30-12:45
# Instructor:	Dr. M. Gofman
# Assignment:	3 (FTP Server/Client)
################################################################################
# Copyright (c) 2014 Peter Gordon <peter.gordon@csu.fullerton.edu>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
################################################################################
"""This module provides the SimpleFTPClientInterpreter type."""

import re
import socket

from os.path import getsize, isdir, isfile
from utils import debugPrint, isError, recvAll, recvFile, recvLine, sendFile, sendStr

from ClientConnection import ClientConnectionInterpreter
from timer import Timer


class SimpleFTPClientInterpreter(ClientConnectionInterpreter):
	"""A subclass of the ClientConnectionInterpreter interface which implements
	a rudimentary file transfer client. The full protocol specification can be
	found in the included README file."""
	
	__slots__ = ("_dataSock", "_commandHandlers", "_config", "_isFinished")
	
	def __init__(self, connSock, remoteAddr):
		super().__init__(connSock, remoteAddr)
		self._dataSock = None
		self._commandHandlers = {}
		self._config = {
				"chunk_size": 65536,
				"passive": False,
				"persistent": False
				}
		self._isFinished = False
		
		# CHUNK <size>
		# Set the chunk size for file transfers. 
		self.registerCommandHandler(r"CHUNK (?P<size>\d+)",
				self._command_CHUNK, needData=False)
		
		# GET <filename>
		# Retrieve the specified file from the server.
		self.registerCommandHandler(r"GET (?P<filename>.+)",
				self._command_GET, needData=True, overwriteFlag=False)

		# GETF <filename>
		# Retrieve the specified file from the server, overwriting it if it already exists.
		self.registerCommandHandler(r"GETF (?P<filename>.+)",
				self._command_GET, needData=True, overwriteFlag=True)
		
		# LS
		# Get a file listing from the server.
		self.registerCommandHandler(r"LS", self._command_LS, needData=True)

		# HELP
		# HELP <command>
		# Prints the list of commands, or help on a specific command if given.
		self.registerCommandHandler(r"HELP( (?P<command>\w+))?",
				self._command_HELP, needData=False)

		# PASV YES
		# PASV NO
		# Enables or disables passive data transfer mode.
		self.registerCommandHandler(r"PASV (?P<option>YES|NO)",
				self._command_PASV, needData=False)
		
		# PERSIST YES
		# PERSIST NO
		self.registerCommandHandler(r"PERSIST (?P<option>YES|NO)",
				self._command_PERSIST, needData=False)
		
		# PUT <filename>
		# Send the specified file to the server.
		self.registerCommandHandler(r"PUT (?P<filename>.+)",
				self._command_PUT, needData=True)
		
		# QUIT
		# Exit the client.
		self.registerCommandHandler(r"QUIT",
				self._command_QUIT, needData=False)


	def handleCommand(self, command):
		"""The workhorse function of this client implementation. """

		if not command:
			return False # Stop 
		for (regex, handler) in self._commandHandlers.items():
			matchObj = re.match("^"+regex+"$", command)
			if matchObj:
				(handlerFunc, needData, args, kwargs) = handler
				if needData and not self._dataSock:
					if not self._openDataConnection():
						debugPrint("CLIENT FAILURE: Could not establish data connection.")
						return False
				handlerFunc(matchObj, *args, **kwargs)
				if not self._config["persistent"] and self._dataSock:
					self._dataSock.close()
					self._dataSock = None
				return True
		else:
			print("Error: Invalid command! Type 'HELP' for a list of commands.")
			return False
	
	
	def isFinished(self):
		"""Returns True if the client is should no longer process input; False
		otherwise. """
		
		return self._isFinished
		
		
	def _isSocketClosed(self, lastMsg):
		"""Given the most recent message received on a socket, checks if that
		was empty (EOF). If so, prints an error message, marks input as
		finished, and returns True. Returns False otherwise."""
		
		if not lastMsg:
			print("Server unexpectedly disconnected. (Socket EOF reached.)")
			self._isFinished = True
			return True
		return False
		
	
	def _openDataConnection(self):
		"""Opens a data connection to the server. The existing data connection
		(if any) is closed."""
		
		if self._dataSock:
			self._dataSock.close()
			self._dataSock = None
			
		if self._config["passive"]:
			sendStr(self._connSock, "DATA\n")
			result = recvLine(self._connSock).rstrip()
			if isError(result):
				return False
			
			getPort = re.match(r"^READY (?P<port>\d+)$", result)
			if not getPort:
				if not self._isSocketClosed(result):
					debugPrint("CLIENT FAILURE: Malformed DATA reply from server. 2")
				return False
			
			port = int(getPort.group("port"))
			try:
				self._dataSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				self._dataSock.connect((self._remoteAddr[0], port))
			except socket.error as err:
				debugPrint("CLIENT FAILURE: Socket error: {errmsg}".format(errmsg=err))
				self._dataSock = None
				return False
			else:
				result = recvLine(self._connSock).rstrip()
				if isError(result):
					self._dataSock = None
					return False
				elif result == "OK {port}".format(port=port):
					return True
				else:
					if not self._isSocketClosed(result):
						debugPrint("CLIENT FAILURE: Malformed DATA reply from server. 3")
					self._dataSock = None
					return False
		
		else: # Not passive
			dataConn = None
			try:
				dataConn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				dataConn.bind(("", 0))
				dataConn.settimeout(60)
				dataConn.listen(1)
				dataPort = dataConn.getsockname()[1]
				sendStr(self._connSock, "DATA {p}\n".format(p=dataPort))
				while True:	
					(serverDataSock, serverAddr) = dataConn.accept()
					if serverAddr[0] == self._remoteAddr[0]:
						result = recvLine(self._connSock).rstrip()
						if result == "OK {port}".format(port=dataPort):
							self._dataSock = serverDataSock
							return True
						else:
							if not self._isSocketClosed(result):
								debugPrint("CLIENT FAILURE: Malformed DATA reply from server. 1")
							self._dataSock = None
							serverDataSock.close()
							return False
					else:
						serverDataSock.close()						
			except socket.timeout as err:
				return False
			
		
	def registerCommandHandler(self, regex, handlerFunc, needData, *args, **kwargs):
		"""Register handlerFunc with the connection so that if a client command
		matches the given regex, that function is called with its appropriate
		re.match object and any other arguments. The needData flag denotes if
		the handler function needs a data connection. Attempting to add a regex
		which is already matched by an existing rule will fail with an error
		message."""
		
		for handler in self._commandHandlers.keys():
			if re.match("^"+handler+"$", regex):
				debugPrint("CLIENT: Invalid rule {rule}: Already matched by {old}.".format(
						rule=regex, old=handler))
				break
		else:
			self._commandHandlers[regex] = (handlerFunc, needData, args, kwargs)

			
	###
	# Command handlers...
	###
	def _command_CHUNK(self, matchObj):
		"""Handler for CHUNK command: sets the transfer chunk size (bytes)."""
		
		chunkSize = int(matchObj.group("size"))
		if chunkSize < 1:
			print("FAILURE: Chunk size must be positive!")
			return
		sendStr(self._connSock, "SETCONFIG CHUNKSIZE {size}\n".format(size=chunkSize))
		result = recvLine(self._connSock)
		if result == "OK CHUNKSIZE {size}".format(size=chunkSize):
			self._config["chunk_size"] = chunkSize
			print("SUCCESS: Chunk size is now {size} byte{s}.".format(
					size=chunkSize, s=("s" if chunkSize > 1 else "")))
		else:
			if not self._isSocketClosed(result):
				debugPrint("CLIENT FAILURE: Malformed CHUNK response from server.")
		

	def _command_GET(self, matchObj, overwriteFlag):
		"""Handler for GET command: Downloads a file from the server."""
		
		fileName = matchObj.group("filename")
		
		if isdir(fileName):
			print("FAILURE: A directory with that name already exists.")
			return
			
		if isfile(fileName) and not overwriteFlag:
			print("FAILURE: That file already exists.")
			return
			
		sendStr(self._connSock, "GET {name}\n".format(name=fileName))
		result = recvLine(self._connSock)
		if isError(result):
			return

		getSize = re.match("^READY (?P<size>\d+)$", result)
		if not getSize:
			if not self._isSocketClosed(result):
				debugPrint("CLIENT FAILURE: Malformed GET reply from server.")
			return
			
		fileSize = int(getSize.group("size"))
		chunkSize = self._config["chunk_size"]
		try:
			with Timer() as xferTime:
				numBytesWritten = recvFile(self._dataSock, fileSize, fileName, "wb", chunkSize)
		except (PermissionError, IOError):
			print("FAILURE: Cannot write to file.")
		else:
			if numBytesWritten < fileSize:
				print("FAILURE: Incomplete file data written.")
			else:
				isOK = recvLine(self._connSock)
				if isOK == "OK {size}".format(size=numBytesWritten):
					print("SUCCESS: {name} ({size} byte{s}) retrieved in {secs} seconds.".format(
							name=fileName, size=fileSize, secs=xferTime.elapsedTime(), 
							s=("s" if fileSize > 1 else "")))
				elif not self._isSocketClosed(isOK):
					print("CLIENT FAILURE: Malformed GET reply from server after transfer.")
		

	def _command_LS(self, matchObj):
		"""Handler for LS command: Retrieves a listing of file names and sizes
		on the server."""
		
		sendStr(self._connSock, "LS\n")
		result = recvLine(self._connSock)
		if isError(result):
			return
		
		getSize = re.match(r"^OK (?P<size>\d+)$", result)
		if not getSize:
			if not self._isSocketClosed(result):
				debugPrint("CLIENT FAILURE: Malformed LS reply from server.")
			return
		
		numBytes = int(getSize.group("size"))
		listing = recvAll(self._dataSock, numBytes).decode()
		if len(listing) < numBytes:
			if not self._isSocketClosed(listing):
				debugPrint("CLIENT FAILURE: Incomplete reply from server.")
			return

		theList = [fileLine.split(maxsplit=1) for fileLine in listing.splitlines()]
		dirs = [entry[1] for entry in theList if entry[0] == "DIR"]
		files = [entry for entry in theList if entry[0] != "DIR"]

		# Get the maximum field width of the file sizes, for alignment when printing.
		maxSizeWidth = len(max(next(zip(*files)), key=len))
		print("Directories:")
		for name in dirs:
			print(" "*maxSizeWidth, name)
		print("Files:")
		for (size, name) in files:
			print("{{fsize: >{width}}} {{fname}}".format(width=maxSizeWidth).format(
					fsize=("" if size == "DIR" else size), fname=name))
	
	
	def _command_HELP(self, matchObj):
		"""Handler for HELP command: Gives brief user documentation."""
		
		helpStrings = {
				"CHUNK": "Usage: CHUNK <integer>\nSets the chunk size for transferring files. A "
						"reasonably large power of 2, like 65536, is recommended. A smaller chunk "
						"size will result in less blocking (since the wait for recv() to return is"
						" shorter) at the expense of smaller and more frequent disk I/O, which "
						"could cause a decrease in transfer performance.",
				"GET":	"Usage: GET <filename>\nAttempts to download the named file from the "
						"remote system and save it locally, under the same file name. An error is "
						"displayed if this operation does not succeed.",
				"GETF": "Usage: GETF <filename>\nAttempts to download the named file, exactly like"
						" GET, except that GETF will forcibly overwrite the file of that name if "
						"it already exists on the client system.",
				"HELP":	"Usage: HELP or HELP <command>\nShow the list of commands, or help for a "
						"specific command.",
				"LS":	"Usage: LS\nPrints a listing of files and directories on the remote "
						"system. For files, the sizes (in bytes) are also given.",
				"PASV": "Usage: PASV YES or PASV NO\nEnables or disables passive data transfer "
						"mode. Normally when a data transfer is required, the server will attempt "
						"to connect to the client through an ephemeral port; but this can be "
						"problematic in client systems behind a NAT or firewall setup. Instead of "
						"this, passive mode causes the client to initiate connection requests, "
						"which works around these issues.",
				"PERSIST": "Usage: PERSIST YES or PERSIST NO\nEnables or disables a persistent "
						"data connection. Normally, a separate data connection is established and "
						"later torn down for each server request which requires it. But with this"
						" enabled, only one data connection will be made, and reused for any "
						"subsequent requests.",
				"PUT":	"Usage: PUT <filename>\nAttempts to store the local named file on the "
						"remote system under the same file name. An error is display if this "
						"operation does not succeed.",
				"QUIT": "Usage: EXIT\nExit this client."
				}
		command = matchObj.group("command")
		if not command:
			print("Available commands: {cmds}\nType 'HELP <command>' for more details about that "
					"command.".format(cmds=", ".join(sorted(helpStrings.keys()))))
		elif command in helpStrings:
			print(helpStrings[command])
		else:
			print("No documentation exists for this command. (Perhaps it is not valid?)")
	
		
	def _command_PASV(self, matchObj):
		"""Handler for PASV command: Enables or disables passive data transfer
		mode."""
		
		option = matchObj.group("option")
		if option == "YES":
			sendStr(self._connSock, "SETCONFIG PASSIVE YES\n")
			result = recvLine(self._connSock)
			if result != "OK PASSIVE ENABLED":
				if not self._isSocketClosed(result):
					debugPrint("CLIENT FAILURE: Malformed PASV reply from server.")
			else:
				self._config["passive"] = True
				print("Passive data transfer mode enabled.")
		else:
			sendStr(self._connSock, "SETCONFIG PASSIVE NO\n")
			result = recvLine(self._connSock)
			if result != "OK PASSIVE DISABLED":
				if not self._isSocketClosed(result):
					debugPrint("CLIENT FAILURE: Malformed PASV reply from server.")
			else:
				self._config["passive"] = False
				print("Passive data transfer mode disabled.")


	def _command_PERSIST(self, matchObj):
		"""Handler for PERSIST command: Enables or disables a persistent data
		connection."""
		
		option = matchObj.group("option")
		if option == "YES":
			sendStr(self._connSock, "SETCONFIG PERSISTENTDATA YES\n")
			result = recvLine(self._connSock)
			if result != "OK PERSISTENTDATA ENABLED":
				if not self._isSocketClosed(result):
					debugPrint("CLIENT FAILURE: Malformed PERSIST reply from server.")
			else:
				self._config["persistent"] = True
				print("Persistent data connection enabled.")
		else:
			sendStr(self._connSock, "SETCONFIG PERSISTENTDATA NO\n")
			result = recvLine(self._connSock)
			if result != "OK PERSISTENTDATA DISABLED":
				if not self._isSocketClosed(result):
					debugPrint("CLIENT FAILURE: Malformed PERSIST reply from server.")
			else:
				self._config["persistent"] = False
				print("Persistent data connection disabled.")
			

	def _command_PUT(self, matchObj):
		"""Handler for PUT command: Uploads a file to the server."""
		
		fileName = matchObj.group("filename")
		chunkSize = self._config["chunk_size"]
		
		if isdir(fileName):
			print("FAILURE: Cannot upload a directory.")
		elif not isfile(fileName):
			print("FAILURE: The file does not exist.")
		else:
			fileSize = getsize(fileName)
			sendStr(self._connSock, "PUT {size} {name}\n".format(size=fileSize, name=fileName))
			isReady = recvLine(self._connSock)
			if isError(isReady):
				return
			
			if isReady != "READY {size}".format(size=fileSize):
				if not self._isSocketClosed(isReady):
					debugPrint("CLIENT FAILURE: Malformed PUT reply from server.")
					return
			
			try:
				with Timer() as xferTime:
					sendFile(self._dataSock, fileName, chunkSize)
			except (PermissionError, IOError):
				print("CLIENT FAILURE: Cannot read from file.")
			else:
				isSent = recvLine(self._connSock)
				if isSent != "OK {size}".format(size=fileSize):
					if not self._isSocketClosed(isSent):
						debugPrint("CLIENT FAILURE: Malformed PUT reply from server.")
				else:
					print("SUCCESS: {name} ({size} byte{s}) uploaded in {secs:.4f} seconds.".format(
							name=fileName, size=fileSize, secs=xferTime.elapsedTime(), 
							s=("s" if fileSize > 1 else "")))
		

	def _command_QUIT(self, matchObj):
		"""Handler for the QUIT command: Signals the termination of the
		connection."""
		
		sendStr(self._connSock, "GO AWAY\n")
		result = recvLine(self._connSock)
		if result == "OK BYE":
			self._connSock.close()
			self._isFinished = True
		else:
			if not self._isSocketClosed(result):
				debugPrint("CLIENT FAILURE: Malformed QUIT reply from server.")
