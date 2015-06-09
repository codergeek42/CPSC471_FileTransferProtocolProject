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
"""This module provides the Timer type, a simple stopwatch-like way of timing
code segments through a context manager. """

# Example usage:
# >>> with Timer() as stopwatch:
# ...     doSomethingBig(foo, bar)
# ...
# >>> print("Function time: {}".format(stopwatch.elapsedTime()))"""

from timeit import default_timer as now

class Timer:
	"""Provides basic timing functionality as a context manager."""
	
	__slots__ = ("_start", "_stop")
	
	def __init__(self):
		self._start = 0
		self._stop = 0
	
	
	def __enter__(self):
		self._start = now()
		return self


	def __exit__(self, *exceptionArgs):
		self._stop = now()
		# Return False 
		return False

	
	def elapsedTime(self):
		"""Returns the elapsed time, in seconds."""
		
		return (self._stop - self._start)
	
	
