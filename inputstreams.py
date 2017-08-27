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

import re

# ---------------------------------------------------------------------------

class FileInputStream(object):
	def __init__(self, f):
		self.f = f
		self.putback = ''

	def get(self, amount=1, stay=False):
		answer = self.putback
		remains = amount-len(answer)
		fgot = self.f.read(remains)
		if len(fgot)<remains:
			raise Exception("Overread")
		answer += fgot
		r = answer[:amount]
		if stay:
			self.putback = answer
		else:
			self.putback = answer[amount:]
		return r

	def skip(self, amount=1):
		self.get(amount)

	def peek(self, amount=1):
		return self.get(amount, stay=True)

	def tell(self):
		return self.f.tell()

	def consume_if_possible(self, required_bytes):
		l = len(required_bytes)
		if self.peek(l)!=required_bytes: return False
		self.skip(l)
		return True

	# --- these methods are specific to this kind of stream

	def get_until(self, e):
		a = ''
		while not self.consume_if_possible(e):
			a = a + self.get()
		return a

# ---------------------------------------------------------------------------

class StringInputStream:
	def __init__(self, s, p=0):
		self.s = s
		self.p = p

	def get(self, amount=1):
		n = self.p + amount
		if n>len(self.s):
			raise Exception("Overread")
		answer = self.s[self.p:n]
		self.p = n
		return answer

	def skip(self, amount=1):
		self.get(amount)

	def peek(self, amount=1):
		n = self.p + amount
		answer = self.s[self.p:n]
		return answer

	def tell(self):
		return self.p

	def consume_if_possible(self, required_bytes):
		l = len(required_bytes)
		if self.peek(l)!=required_bytes: return False
		self.skip(l)
		return True

	# --- these methods are specific to this kind of stream

	def more(self):
		return self.p!=len(self.s)

	def match(self, r):
		answer = re.compile(r, re.DOTALL).match(self.s, self.p)
		if answer is None: return None
		#print "matched", r.ljust(10), "in", self.peek(20)
		self.p = answer.end()
		return answer

	def must_match(self, r):
		answer = self.match(r)
		if not answer: raise Exception(multistr("cannot match", r, "at", self.peek(20)))
		return answer

	def pos(self):
		"""return a description of where we are in the string"""
		x = self.s[:self.p]
		x = re.sub(r"[^\n]", "", x)
		x = len(x)+1
		x = "line"+str(x)
		return x

	def cut(self, start):
		return self.s[start:self.p]

# ---------------------------------------------------------------------------


