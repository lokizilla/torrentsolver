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

import os
import re
import subprocess
import shutil
import itertools
import base64
import hashlib
import cgi
import time
import inspect

# ---------------------------------------------------------------------------
#
# Environment Introspection
#
# ---------------------------------------------------------------------------

def get_container():
	# google?
	try:
		from google.appengine.ext import webapp
		return "google"
	except ImportError:
		pass

	# default:
	return None

def get_linesep():
	c = get_container()
	if c=="google": return "\n"
	return os.linesep

# ---------------------------------------------------------------------------
#
# Tiny Utility Functions
#
# ---------------------------------------------------------------------------

def y_or_n(b, yes=True, no=False):
	if b: return yes
	return no

def pairs(x):
    xiter = iter(x)
    return itertools.izip(xiter,xiter)

def int_roundup(x, multiple):
	return ((x+multiple-1)//multiple)*multiple

def jzip(a, b):
	assert len(a)==len(b)
	return zip(a, b)

# ---------------------------------------------------------------------------
#
# Unicode Functions
#
# ---------------------------------------------------------------------------

# encapsulate our assumptions about the fastest way to build a string from parts
class StringBuilder(object):
	def __init__(self, start_with=None, sep=''):
		self.parts = [start_with] if start_with is not None else []
		self.sep = sep
	def append(self, part):
		self.parts.append(part)
	def extend(self, part):
		self.parts.extend(part)
	def get(self):
		return self.sep.join(self.parts)

def is_unicode(t):
	return type(t) == unicode

def is_bytestring(t):
	return type(t) == type("")

def assert_unicode(t):
	assert is_unicode(t)

def assert_bytestring(t):
	assert is_bytestring(t)

def unicode_to_utf8(s):
	assert_unicode(s)
	return s.encode("utf-8")

def upgrade_to_unicode(t):
	if is_bytestring(t):
		return unicode(t)
	return t

def pystr(s):
	# a single place to change this to str() when we go to python 3
	return unicode(s)

def multirepr(*things):
	answer = StringBuilder(sep=' ')
	for thing in things:
		answer.append(repr(thing))
	return answer.get()

def multistr(*things):
	answer = StringBuilder(sep=' ')
	for thing in things:
		#print thing
		answer.append(str(thing))
	return answer.get()

# ---------------------------------------------------------------------------
#
# File Functions
#
# ---------------------------------------------------------------------------

def get_ext(src):
	return re.sub(r"^.*\.", "", src)

def mtime_from_string(mtime):
	if os.stat_float_times():
		return float(mtime)
	return int(mtime)

def save_text(name, lines, newline=get_linesep()):
	with open(name, 'w') as f:
		for line in lines:
			f.write(line+newline)

def load_text(name):
	with open(name, 'r') as f:
		for line in f:
			line = re.sub(r'[\r\n]+$', "", line)
			yield line

def load_file(name):
	with open(name, 'r') as f:
		return f.read()

def save_file(name, data):
	with open(name, 'w') as f:
		f.write(data)

class ReadAndCallException(IOError):
	def __init__(*a):
		IOError.__init__(*a)

def read_and_call(file, start, length, function):
	use_mmap = False

	if use_mmap:
		CHUNK_SIZE = 1024*1024
		while length:
			start_position_in_block = start & (CHUNK_SIZE-1)
			offset_of_block = start - start_position_in_block
			remains_of_block = CHUNK_SIZE - start_position_in_block 
			readable = min(remains_of_block, length)
			end_position_in_block = start_position_in_block+readable
			map = mmap.mmap(file.fileno(), end_position_in_block, access=mmap.ACCESS_READ, offset=offset_of_block)
			function(map[start_position_in_block:end_position_in_block])
			map.close()
			start += readable
			length -= readable
	else:
		CHUNK_SIZE = 16*1024
		file.seek(start)
		if file.tell()!=start:
			raise ReadAndCallException, "mis-seek"
			
		while length:
			readable = min(CHUNK_SIZE, length)
			segment = file.read(readable)
			if len(segment)!=readable:
				raise ReadAndCallException, "under-read"
			function(segment)
			length -= readable

def mkdir_minus_p(path):
	if path and not os.path.exists(path): os.makedirs(path)

def rm_minus_r(path, ignore_not_found=False):
	if ignore_not_found and not os.path.exists(path): return
	if os.path.isdir(path):
		shutil.rmtree(path)
	else:
		os.remove(path)

def cp_minus_r(src, dest, create_dest_dir=False):
	if create_dest_dir: mkdir_minus_p(os.path.dirname(dest))
	if os.path.isdir(src):
		shutil.copytree(src, dest)
	else:
		shutil.copy(src, dest)
	assert os.path.exists(dest)

def remove_path(to_go, orig): 
	to_go = os.path.join(to_go, 'x')
	assert to_go[-1] == 'x'
	to_go = to_go[:-1]
	p = len(to_go)
	a, b = orig[0:p], orig[p:]
	assert a == to_go, multistr(orig, 'must start with', to_go)
	return b


# ---------------------------------------------------------------------------
#
# Subprocess Functions
#
# ---------------------------------------------------------------------------

def check_call_and_capture_output(cmd):
	#print "CALLING", cmd
	s = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	answer = s.communicate()
	if s.returncode: raise Exception(multistr("got returncode of ", s.returncode, " from ", cmd))
	return answer

def silent_check_call(cmd):
	#subprocess.check_call(cmd)
	check_call_and_capture_output(cmd)
	# except we don't return it

# ---------------------------------------------------------------------------
#
# String encoding functions
#
# ---------------------------------------------------------------------------

def hex_bytes(bytes):
	return "".join([hex_byte(byte, pad=True) for byte in bytes])

def opt_ord(a):
	if type(a)==str and len(a)==1:
		a = ord(a)
	return a

def plain_hex(a, z=0):
	a = opt_ord(a)
	a = hex(a)[2:]
	a = re.sub(r"L$", "", a)		# won't be needed in py3k
	if z: a = a[:z].zfill(z)
	return a

def hex_byte(x, pad=False):
	width = 2 if pad else 0
	return plain_hex(x, width)

def base64enc(s):
	s = base64.b64encode(s)
	s = re.sub(r"[\s=]+$", "", s)
	return s

def base64dec(s):
	s = re.sub(r"[\s=]+", "", s)
	pl = int_roundup(len(s), 4)
	s = s.ljust(pl, '=')
	return base64.b64decode(s)


# ---------------------------------------------------------------------------
#
# Internet functions
#
# ---------------------------------------------------------------------------

def http_get(host, path):
	import httplib
	conn = None
	try:
		conn = httplib.HTTPConnection(host)
		conn.request("GET", path)
		r1 = conn.getresponse()
		if r1.status!=200:
			raise Exception(multistr("Can't read from", host, "as i got http return code", r1.status, "reason", r1.reason))
		return r1.read()
	finally:
		if conn: conn.close()

def external_ip():
	data = http_get("checkip.dyndns.org", "/")
	g = re.search(r"\d+\.\d+\.\d+\.\d+", data)
	if not g:
		raise Exception(multistr("Can't parse IP from", data))
	return g.group()

def scrunch_ip(s):
	g = re.match(r"(\d+)\.(\d+)\.(\d+)\.(\d+)", s)
	if not g: raise Exception(s+" is not an IP")
	a = 0
	for x in range(0, 4):
		a += int(g.group(x+1))<<(8*(3-x))
	return a

# ---------------------------------------------------------------------------
#
# File Hashing functions
#
# ---------------------------------------------------------------------------


def compute_sha1sum_for_file(path):
	sha1_hasher = hashlib.sha1()
	with open(path, 'r') as f:
		read_and_call(f, 0, os.path.getsize(path), lambda data: sha1_hasher.update(data))
	return sha1_hasher.digest().encode('hex')

def safely_get_sha1hash_and_mtime(f):
	while True:
		time_before = os.path.getmtime(f)
		hash = compute_sha1sum_for_file(f)
		time_after = os.path.getmtime(f)
		if time_before==time_after:
			return (hash, time_before)

def sha1hash_of_string(s):
	sha1_hasher = hashlib.sha1()
	sha1_hasher.update(s)
	return sha1_hasher.digest().encode('hex')

# ---------------------------------------------------------------------------
#
# Misc
#
# ---------------------------------------------------------------------------

MEM_SIZES = [
	( "p", 1024*1024*1024*1024*1024 ),
	( "t", 1024*1024*1024*1024 ),
	( "g", 1024*1024*1024 ),
	( "m", 1024*1024 ),
	( "k", 1024 ),
	( "", 1 ),
	]

MEM_SIZES_DICT = dict(MEM_SIZES)

def get_memsize(s):
	r = r"([\d\.]+)([a-zA-Z]*)$"
	match = re.match(r, s)
	if match is None: raise RuntimeException(multistr("Bad memsize:", s))
	x = float(match.group(1))
	k = match.group(2)
	letter_value = MEM_SIZES_DICT.get(k.lower())
	if letter_value is None: raise RuntimeException(multistr("Bad memsize:", s))
	return int(x * letter_value)

def gen_memsize(x):
	use_letter_value = 1
	for letter, letter_value in MEM_SIZES:
		if x>=letter_value:
			use_letter_value = letter_value
			break

	s = (x*10)//use_letter_value
	a = str(s//10)
	s %= 10
	if s: a = a+"."+str(s)

	return a + letter

def ordinalth(n):
	# though use of this does rather lock us into English
	# let's not use it for user messages
	if n % 100 in (11, 12, 13): return str(n)+'th'
	t = 'th st nd rd th th th th th th'.split()
	return str(n)+t[n%10]

class AnyBase:
	def __init__(self, alphabet):
		self._alphabet = alphabet
		self._w = len(self._alphabet)
		self._map = {}
		for v, c in enumerate(alphabet):
			self._map[c] = v

	def write(self, x, width=1):
		answer = []
		while x!=0:
			q = x%self._w
			x //= self._w
			answer.append(self._alphabet[q])
		while len(answer)<width:
			answer.append(self._alphabet[0])
		answer.reverse()
		return ''.join(answer)

	def read(self, x):
		answer = 0
		for c in x:
			answer *= self._w
			answer += self._map[c]
		return answer

def char_range(*list):
	answer = StringBuilder()
	for s, e in pairs(list):
		s = opt_ord(s)
		e = opt_ord(e)
		answer.extend([ chr(x) for x in xrange(s, e-1) ])
	return answer.get()


def generate_progress(current, max, width):
	def progress_maths(current, max, width):
		current *= width
		current += max//2
		current //= max
		return current

	def progress_bar(current, width):
		s = ('=' * current).ljust(width)
		s = '[' + s + ']'
		return s

	return progress_bar(progress_maths(current, max, width), width)


class Doc(object):
	def __init__(self):
		self.content = StringBuilder()
	def write_raw(self, text):
		self.content.append(text)
	def write(self, text):
		self.content.append(cgi.escape(text))
	def get(self):
		return self.content.get()

def make_url(path, v=None):
	import urllib
	a = StringBuilder(path)
	if v:
		a.append('?')
		ks = v.keys()
		ks.sort()
		for e, k in enumerate(ks):
			if e: a.append('&')
			a.append(k)
			a.append('=')
			a.append(urllib.quote(v[k]))
	return a.get()


def curry(*args, **create_time_kwds):
	func = args[0]
	create_time_args = args[1:]
	def curried_function(*call_time_args, **call_time_kwds):
		args = create_time_args + call_time_args
		kwds = create_time_kwds.copy()
		kwds.update(call_time_kwds)
		return func(*args, **kwds)
	return curried_function

# ---------------------------------------------------------------------------
# a little protection system
# watch out though - it does not prevent replay attack

WRAPSIZE_SALT = 6
WRAPSIZE_HASH = 8
WRAPSIZE_BOTH = WRAPSIZE_SALT + WRAPSIZE_HASH

def wrap(s):
	salt = plain_hex(int(time.time()*100), z=WRAPSIZE_SALT)
	hash = sha1hash_of_string(s+salt)[:WRAPSIZE_HASH]
	#print salt, hash, s
	return s+hash+salt

def unwrap(s):
	salt = s[-WRAPSIZE_SALT:]
	hash = s[-WRAPSIZE_BOTH:-WRAPSIZE_SALT]
	s = s[:-WRAPSIZE_BOTH]
	#print salt, hash, s
	if len(salt)!=WRAPSIZE_SALT or len(hash)!=WRAPSIZE_HASH: return None
	actual_hash = sha1hash_of_string(s+salt)[:WRAPSIZE_HASH]
	#print actual_hash, hash
	if actual_hash==hash: return s
	return None


# ---------------------------------------------------------------------------

def lineno():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno

# ---------------------------------------------------------------------------

if __name__ == "__main__":




	assert unwrap(wrap("lard"))=="lard"
	assert unwrap(wrap("lard")+"!")==None

	# print (plain_hex(scrunch_ip(external_ip())))
	# print ('5245e36e')

	a = AnyBase( char_range('0', '9', 'A', 'Z', 'a', 'z') )
	for x in range(0, 1000):
		z = a.write(x)
		y = a.read(z)
		print(x, z, y)
		assert x == y

	assert get_memsize("10M")==10*1024*1024
	assert get_memsize("10m")==10*1024*1024
	assert get_memsize("13k")==13*1024
	assert get_memsize("0.5k")==512
	assert get_memsize("0.3")==0
	assert get_memsize("13")==13

	print gen_memsize(1)
	print gen_memsize(1500)
	print gen_memsize(1500*1024)
	print gen_memsize(1500*1024*1024)
	print gen_memsize(1500*1024*1024*1024)
	print gen_memsize(1500*1024*1024*1024*1024)

	print make_url("/h")
	print make_url("/h", {})
	print make_url("/h", { 'meal': "chips" })
	print make_url("/h", { 'meal': "chips", 'a': "yum" })

	print multistr(1, 2)

	print remove_path('a/b/c', 'a/b/c/d/e/f.txt')
