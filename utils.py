#!/bin/python3 -tt
################################################################################
# Name:			Peter Gordon
# Email:		peter.gordon@csu.fullerton.edu
# Course:		CPSC 223P, T/Th 11:30-12:45
# Instructor:	Dr. M. Gofman
# Assignment:	10 (FTP Server/Client)
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

"""This module provides some common functions such as network I/O, used in both
the server and client."""


import re
import sys
import threading

from datetime import datetime
from os import listdir, getpid
from os.path import isdir, isfile, getsize


def checkNumArgs(num):
	"""Checks if the number of command-line arguments given (including the
	script name, itslf) is at least the number given (num)."""
	if len(sys.argv) < num:
		print("Not enough arguments given!")
		sys.exit(1)


def convertToInt(arg):
	"""Attempts to convert the given argument (arg) to an integer, and returns
	it if succesful."""
	try:
		return int(arg)
	except:
		print("Could not convert {num} to an integer!".format(num=arg))
		sys.exit(1)


def debugPrint(debugStr):
	"""A simple function to output the given string with some verbosity
	(timestamp, thread, and process IDs)."""
	
	# Change this conditional to False to remove all debugging output.
	if True:
		print("[{ts}] (TID {tid}) (PID {pid}) {output}".format(
				tid=threading.current_thread().name, pid=getpid(),
				ts=datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"),
				output=debugStr))


def isError(line):
	"""If the given reply line is an error, returns True and prints its
	message; otherwise returns False."""
	
	checkErr = re.match(r"^ERR (?P<msg>.+)$", line)
	if checkErr:
		debugPrint("FAILURE: {errormsg}".format(errormsg=checkErr.group("msg")))
		return True
	return False


def listFiles(dirName):
	"""Returns a listing of the given directory"""
	retStr = ""
	try:
		files = listdir(dirName)	
	except FileNotFoundError:
		return ""
	else:
		for fileName in sorted(files):
			if isdir(fileName):
				retStr += "DIR {name}\n".format(name=fileName)
			else:
				retStr += "{size} {name}\n".format(size=getsize(fileName), name=fileName)
		return retStr				


def recvAll(sock, numBytes):
	"""Receives and returns at most the specified number of bytes from the
	socket. (Returned data may be less than this if client closes the
	socket early.) This is copied from the example given as part of the
	problem statement, except using Python3 bytearray objects instead of strings."""
	
	recvBuff = bytearray()
	tmpBuff = bytearray()
	while len(recvBuff) < numBytes:
		tmpBuff = sock.recv(numBytes)
		if not tmpBuff:
			break
		recvBuff.extend(tmpBuff)
	return recvBuff


def recvLine(sock):
	"""Receives and returns the next line of bytes from the socket as a string;
	that is, all data until (not including) the first newline character. (If
	the socket is disconnected before that, all read data is returned.) """
	
	tmpBuff = bytearray()
	recvBuff = bytearray()
	while tmpBuff != b"\n":
		tmpBuff = sock.recv(1)
		if not tmpBuff:
			break
		recvBuff.extend(tmpBuff)
	# Don't return the final newline character. 
	return recvBuff[:-1].decode()
	
	
def recvFile(sock, fileSize, fileName, fileMode, chunkSize):
	"""Assuming the given socket is ready for reading, and the given file name
	is ready to be written, reads <fileSize> bytes from the given socket and
	stores them into <fileName>, using the given fileMode."""
	
	numBytesWritten = 0
	with open(fileName, fileMode) as outFile:
		while numBytesWritten < fileSize:
			nextChunkSize = min(chunkSize, fileSize - numBytesWritten)
			recvBuff = recvAll(sock, nextChunkSize)
			debugPrint("recvFile: recv {n} bytes of data".format(n=(len(recvBuff),numBytesWritten)))
			if not recvBuff:
				break
			numBytesWritten += outFile.write(recvBuff)
	return numBytesWritten
			

def sendStr(sock, data):
	"""Assuming the given socket is ready for writing, sends the given data
	(bytes or string) over that socket and returns a count of bytes transmitted.
	If the given data is not a string or bytes object, nothing is transmitted
	and None is returned. """

	if isinstance(data, str):
		data = data.encode()
	if isinstance(data, bytes):
		numBytesSent = 0	
		while len(data) > numBytesSent:
			numBytesSent += sock.send(data[numBytesSent:])
		return numBytesSent
	return None
		

def sendFile(sock, fileName, chunkSize):
	"""Assuming the given socket is ready for writing, and the given file name
	exists and is readable, transmits the contents of the file over the socket.
	This is copied almost verbatim from the example given as part of the
	problem statement."""

	with open(fileName, "rb") as dataFile:
		while True:
			data = dataFile.read(chunkSize)
			debugPrint("sendFile: send {n} bytes of data".format(n=len(data)))
			if not data:
				break
			if sendStr(sock, data) < len(data):
				break
