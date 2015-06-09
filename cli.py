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
"""This module provides the command-line client for my file transfer protocol.
It can be invoked with a host and port number as follows:
$ python3 cli.py <host> <port>
"""

# Use GNU Readline library, if available, for more input features like history
# and editing.
try:
	import readline
except ImportError:
	pass

import socket
import sys

from SimpleFTPClientInterpreter import SimpleFTPClientInterpreter
from utils import checkNumArgs, convertToInt, debugPrint
from utils import recvAll, recvFile, recvLine, sendStr,  sendFile


if __name__ == "__main__":
	checkNumArgs(3)
	hostName = sys.argv[1]
	port = convertToInt(sys.argv[2])
		
	try:
		hostIP = socket.gethostbyname(hostName)
		ctrlSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		ctrlSock.connect((hostIP, port))
	except socket.gaierror:
		print("CLIENT: Cannot resolve hostname \"{host}\"".format(host=hostName))
	except socket.error:
		print("CLIENT: Cannot connect to {host}:{port}".format(host=hostName, port=port))
	else:
		print("CLIENT: Connected to {host}:{port}.".format(host=hostName, port=port))
		print("Welcome to Peter's Simple File Transfer Client. Enter commands below, or HELP.")
		
		shell = SimpleFTPClientInterpreter(ctrlSock, (hostIP, port))
		while not shell.isFinished():
			command = input("ftp> ")	
			shell.handleCommand(command)		
		ctrlSock.close()
