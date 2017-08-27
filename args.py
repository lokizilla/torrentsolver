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


# ---------------------------------------------------------------------------

class BadOptions(Exception):
	def __init__(*a):
		Exception.__init__(*a)

# ---------------------------------------------------------------------------

class Args:
	def __init__(self, a=None):
		from sys import argv
		if not a: a = argv[1:]
		self._a = a

	@staticmethod
	def _parse_int(s, min_value=None, max_value=None):
		try:
			value = int(s)
		except ValueError:
			raise BadOptions
		else:
			if max_value is not None:
				if value>max_value: raise BadOptions
			if min_value is not None:
				if value<min_value: raise BadOptions
		return value

	@staticmethod
	def fail():
		raise BadOptions

	def _peek(self):
		return self._a[0] if self._a else None

	def _opt(self):
		f = self._peek()
		if f:
			if f.startswith('--'): return f[2:]
		return None

	@staticmethod
	def unknown_option():
		raise BadOptions

	def get_str(self):
		if not self._a: raise BadOptions
		return self._a.pop(0)

	def remaining(self):
		return len(self._a)

	def require_remaining(self, m):
		if self.remaining()<m: raise BadOptions

	def tail(self):
		return self._a

	def on_an_option(self):
		return bool(self._opt())

	def option_is(self, n, once=False):
		o = self._opt()
		if o is None: raise BadOptions
		if o==n:
			self.get_str()
			return True
		return False

	@staticmethod
	def one_of(s, options):
		try:
			if type(options)==list:
				options = dict([ (name, count) for count, name in enumerate(options)])
			#print s, options
			return options[s]
		except KeyError:
			fail()

	def get_one_of(self, options):
		return Args.one_of(self.get_str(), options)

	def get_int(self, min_value=None, max_value=None):
		return Args._parse_int(self.get_str(), min_value, max_value)

# ---------------------------------------------------------------------------

if __name__ == "__main__":
	a = Args([ '--ab', '--cd', '5', 'x', 'y',  'z' ])

	while a.on_an_option():
		if a.option_is('ab'):
			print 'ab'
		elif a.option_is('cd'):
			print 'cd', a.get_int()
		else:
			a.unknown_option()

# ---------------------------------------------------------------------------
