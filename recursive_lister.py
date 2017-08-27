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

import os.path

def internal_recursive_lister(path, answer, files, dir_before, dir_after):
	if os.path.isfile(path):
		if files:
			answer.append(path)
	elif os.path.isdir(path):
		if dir_before:
			answer.append(path)
		c = os.listdir(path)
		c.sort()
		for x in c:
			y = os.path.join(path, x)
			internal_recursive_lister(y, answer, files, dir_before, dir_after)
		if dir_after:
			answer.append(path)
	else:
		raise Exception("Not found: "+path)

def recursive_lister(path, files=True, dir_before=False, dir_after=False):
	answer = []
	internal_recursive_lister(path, answer, files, dir_before, dir_after)
	return answer

def recursive_lister_clipped(path, files=True, dir_before=False, dir_after=False):
	path = os.path.realpath(path)
	for f in recursive_lister(path, files, dir_before, dir_after):
		yield f[len(path)+1:]

