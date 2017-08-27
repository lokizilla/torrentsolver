#!/usr/bin/python

# ---------------------------------------------------------------------------
#
# Copyright (c) 2010 David Hanney
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# ---------------------------------------------------------------------------

# for py2.5:
from __future__ import division
from __future__ import with_statement

# ---------------------------------------------------------------------------

# imports
import sys
import re

# ---------------------------------------------------------------------------

FATAL    = 6
ERROR    = 5
WARN     = 4
INFO     = 3
PROGRESS = 2
DEBUG    = 1
TRACE    = 0

level_str_map = {
	FATAL:    "fatal",
	ERROR:    "error",
	WARN:     "warn",
	INFO:     "info",
	PROGRESS: "progress",
	DEBUG:    "debug",
	TRACE:    "trace",
}

#level_list = level_str_map.values()

debug = 0

if debug:
	def esc(s):
		s = re.sub('\n', r'\\n', s)
		s = re.sub('\r', r'\\r', s)
		s = '>' + s + '<'
		return s

class Logger(object):
	def __init__(self):
		self._on = set()
		self._in_progress = False
		self._progress_length = 0
		self._indent = 0
		self._bn = False
		self._bf = ""

	def switch_on(self, *levels):
		for level in levels:
			self._on.add(level)

	def switch_off(self, *levels):
		for level in levels:
			self._on.discard(level)

	def buffer_next(self):
		self._bn = True

	def unbuffer(self):
		self._bn = ""

	def log(self, level, t, *p, **d):
		if self.on(level) or self._bn:
			s = t.format(*p, **d)
			level_str = level_str_map[level]
			line = "{0:10}: {1}{2}".format(level_str, self._indent * "    ", s)
			if level==PROGRESS:
				self._in_progress = True
				ll = self._progress_length
				self._progress_length = len(line)
				line = line.ljust(ll)
				line += '\r'
			else:
				line += '\n'
				if self._in_progress:
					line = '\n' + line
					self._in_progress = False
					self._progress_length = 0
			if debug:
				line = esc(line)+'\n'
			if self._bn:
				self._bn = False
				self._bf = line
			else:
				sys.stdout.write(self._bf + line)
				sys.stdout.flush()
				self._bf = ""

	def on(self, level):
		return level in self._on

	def fatal(self, t, *p, **d):
		self.log(FATAL, t, *p, **d)

	def error(self, t, *p, **d):
		self.log(ERROR, t, *p, **d)

	def warn(self, t, *p, **d):
		self.log(WARN, t, *p, **d)

	def info(self, t, *p, **d):
		self.log(INFO, t, *p, **d)

	def progress(self, t, *p, **d):
		self.log(PROGRESS, t, *p, **d)

	def debug(self, t, *p, **d):
		self.log(DEBUG, t, *p, **d)

	def trace(self, t, *p, **d):
		self.log(TRACE, t, *p, **d)

	def indent(self, distance):
		self._indent += distance

	def indenter(self, level):
		if self.on(level):
			return Indenter(1, self)
		return Indenter(0, self)

# classes that MIGHT have a status line to output onto can mix-in this guy:
class LoggerConnectable(object):
	def __init__(self):
		self._logger = Logger()

	def set_logger(self, s):
		self._logger = s

	def get_logger(self):
		return self._logger

class Indenter:
	def __init__(self, distance, logger):
		self._d = distance
		self._l = logger

	def __enter__(self):
		self._l.indent(self._d)

	def __exit__(self, type, value, traceback):
		self._l.indent(-self._d)
		return False

if __name__ == "__main__":
	import time

	logger = Logger()
	logger.switch_on(INFO, PROGRESS)
	if logger.on(INFO):
		with logger.indenter(INFO):
			logger.info("hello!")
			logger.info("hello {0} {name}!", 'fish', name='chips')
	for x in xrange(1000, -1, -1):
		logger.progress("{0}% unfinished", x)
	logger.info("there")



