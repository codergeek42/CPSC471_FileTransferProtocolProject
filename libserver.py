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
"""This module (libserver) provides server functionality. Any server class can
be used if it subclasses the ServerConnectionHandler interface. For each
connected client, an instance of this type is created with the connected
client's socket and a tuple of its (IP, port), then its handleClientConnection
function is called in the child thread or process (depending on which
listenForever function is used) to process the client, while the main loop
continues to listen for more client connections. The server can be stopped with
a keyboard break (such as Ctrl+C on Linux/Unix systems)."""


import re
import socket
import threading

from os import _exit, fork, waitpid
from utils import debugPrint
from ServerConnection import ServerConnectionHandler
from sys import exit
	

def threadingServer_listenForever(servPort, connHandlerType):
	"""Given a ServerConnectionHandler type, uses threading to implement a
	parallel server which listens for (possibly concurrent) client connections
	and process them in child threads."""
	
	assert issubclass(connHandlerType, ServerConnectionHandler)
	
	workerThreads = []
	try:
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servSock:
			servSock.bind(("", servPort))
			debugPrint("SERVER ({addr}) : Listening for incoming connections on port {p}.".format(
					addr=servSock.getsockname()[0], p=servPort))
			debugPrint("SERVER: Press Ctrl+C to quit.")
			servSock.listen(2)
			while True:		
				(clientSock, clientAddr) = servSock.accept()
				handler = connHandlerType(clientSock, clientAddr)
				clientThread = threading.Thread(target=handler.handleClientConnection)
				workerThreads.append(clientThread)
				debugPrint("SERVER: Client ({addr}) connected -- handler thread {tid}...".format(
						addr=clientAddr, tid=clientThread.name))
				clientThread.start()
				debugPrint("SERVER: Main loop running, accepting more connections...")
	except socket.error as socketError:
		debugPrint("SERVER: Could not creating listening socket. Reason: {err}".format(
				err=socketError))
		exit(1)
	except (KeyboardInterrupt, SystemExit):
		debugPrint("SERVER: Received exit signal. Waiting for workers to finish...")
		for childThread in workerThreads:
			childThread.join()
		debugPrint("SERVER: Shutting down.")
		servSock.close()
		exit(0)


def forkingServer_listenForever(servPort, connHandlerType):
	"""Given a ServerConnectionHandler type, uses forking to implement a
	parallel server which listens for (possibly concurrent) client connections
	and handle them in child processes."""

	assert issubclass(connHandlerType, ServerConnectionHandler)
	
	workerProcs = []
	try:
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servSock:
			servSock.bind(("", servPort))
			debugPrint("SERVER ({addr}) : Listening for incoming connections on port {p}.".format(
					addr=servSock.getsockname()[0], p=servPort))
			debugPrint("SERVER: Press Ctrl+C to quit.")
			servSock.listen(2)
			while True:		
				try:
					(clientSock, clientAddr) = servSock.accept()
				except KeyboardInterrupt:
					debugPrint("SERVER: Received exit signal. Waiting for workers to finish...")
					for workerPID in workerProcs:
						waitpid(workerPID, 0)
					debugPrint("SERVER: Shutting down.")
					servSock.close()
					exit(0)
				childPID = fork()
				# NB: fork() returns 0 to child; and the child PID to the parent.
				if childPID == 0:
					try:
						handler = connHandlerType(clientSock, clientAddr)
						handler.handleClientConnection()
					except KeyboardInterrupt:
						# The break will be handled by the main server process.
						pass
					finally:
						_exit(0)
				else:
					debugPrint("SERVER: Client ({addr}) connected -- handler PID {pid}...".format(
						addr=clientAddr, pid=childPID))
					workerProcs.append(childPID)
					debugPrint("SERVER: Main loop running, accepting more connections...")
	except socket.error as socketError:
		debugPrint("SERVER: Could not creating listening socket. Reason: {err}".format(
				err=socketError))
		exit(1)
