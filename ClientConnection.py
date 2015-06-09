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

"""This module provides the base class that the client handler must inherit
from. After the client connects, it should create an object of this type and
pass it the connection (socket) and remote host's address (IP/port tuple), and
use handleCommand to process each line or command of input."""

class ClientConnectionInterpreter:
	__slots__ = ("_connSock", "_remoteAddr")

	def __init__(self, connSock, remoteAddr):
		self._connSock = connSock
		self._remoteAddr = remoteAddr


	def handleCommand(self, command):
		raise NotImplementedError("Subclass must implement this abstract method.")
		
	def clientFinished(self):
		raise NotImplementedError("Subclass must implement this abstract method.")
	
	
	@property
	def remoteAddr(self):
		return "{ip}:{port}".format(
				ip=self._remoteAddr[0], port=self._remoteAddr[1])
	
	@remoteAddr.setter
	def remoteAddr(self, val):
		raise AttributeError("remoteAddr is immutable.")
