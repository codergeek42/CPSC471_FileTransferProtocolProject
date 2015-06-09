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
"""This module provides the base class that any libserver-using connection
handler must inherit from. When a client connects, the server will create an
object of this type and pass it the connection (socket) and address
(IP/port tuple), then call its handleClientConnection function to process its
input."""


class ServerConnectionHandler:
	"""Base class for use with libserver functionality. To implement a server,
	subclass this and  implement its handleClientConnection method (at least),
	then pass that new type as the second argument to one of the listenForever
	functions.."""

	__slots__ = ("_connSock", "_clientAddr")

	def __init__(self, connSock, clientAddr):
		"""Constructor. Upon a client connecting, the object is created and
		passed the client's socket and address as an (IP, port) tuple."""
		
		self._connSock = connSock
		self._clientAddr = clientAddr


	def handleClientConnection(self):
		"""This is called to process the client connection, and should
		terminate only when the client is finished (however that might be
		defined for the protocol)."""
		
		raise NotImplementedError("Subclass must implement this abstract method.")
		
	
	@property
	def clientAddr(self):
		return "{ip}:{port}".format(ip=self._clientAddr[0], port=self._clientAddr[1])
	
	@clientAddr.setter
	def clientAddr(self, val):
		raise AttributeError("clientAddr is immutable.")
