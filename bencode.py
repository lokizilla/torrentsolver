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

import StringIO
import re
from dlib import *
import types
from inputstreams import FileInputStream

# ---------------------------------------------------------------------------

def get_number(stream, e):
	return int(stream.get_until(e))

# ---------------------------------------------------------------------------

class CodingException(Exception):
	def __init__(*a):
		Exception.__init__(*a)

class CodableType:
	def __init__(self, ef, df, et, dc):
		self.ef = ef # function for encoding
		self.df = df # function for decoding
		self.et = et # encode type e.g. str
		self.dc = dc # decode characters e.g. '0123456789'

def encode_unicode(root, stream, value):
	value = value.encode('utf-8')
	stream.write('u'+str(len(value))+':')
	stream.write(value)

def decode_unicode(root, stream):
	stream.skip()
	len = get_number(stream, ':')
	return stream.get(len).decode("utf-8")

ct_unicode = CodableType(encode_unicode, decode_unicode, unicode, "u")

def encode_none(root, stream, value):
	stream.write('n')

def decode_none(root, stream):
	stream.skip()
	return None
			
ct_none = CodableType(encode_none, decode_none, types.NoneType, "n")

def encode_float(root, stream, value):
	stream.write('f'+str(value)+'e')

def decode_float(root, stream):
	stream.skip()
	m = stream.get_until('e')
	return float(m)

ct_float = CodableType(encode_float, decode_float, float, "f")

def encode_list(root, stream, value):
	stream.write('l')
	for item in value:
		root.encode(item)
	stream.write('e')

def decode_list(root, stream):
	stream.skip()
	answer = []
	while not stream.consume_if_possible('e'):
		v = root.decode()
		answer.append(v)
	return answer
			
ct_list = CodableType(encode_list, decode_list, list, "l")

def encode_str(root, stream, value):
	stream.write(str(len(value))+':')
	stream.write(value)

def decode_str(root, stream):
	s = get_number(stream, ':')
	return stream.get(s)

ct_string = CodableType(encode_str, decode_str, str, "0123456789")

def encode_int(root, stream, value):
	stream.write('i'+str(value)+'e')

def decode_int(root, stream):
	stream.skip()
	answer = get_number(stream, 'e')
	return answer

ct_int = CodableType(encode_int, decode_int, int, "i")

#
# a value that passes raw binary data directly through into the bencoded output stream
# you can produce an invalid bencoded stream if you are not careful with this!
#
class DirectValue(object):
	def __init__(self, content):
		self.content = content

def encode_direct(root, stream, value):
	stream.write(value.content)

ct_direct = CodableType(encode_direct, None, DirectValue, "")

def validate_dict_keys(root, value):
	keys = value.keys()
	key_types = set([ type(k) for k in keys ])
	if len(key_types)>1:
		raise CodingException("All keys must be the same type: "+repr(value))
	if len(key_types)!=0:
		#print root
		t = key_types.pop()
		root.must_be_permissible_dict_key(t)
	return keys

def encode_dict(root, stream, value):
	keys = validate_dict_keys(root, value)
	keys.sort()
	stream.write('d')
	for key in keys:
		root.encode(key)
		root.encode(value[key])
	stream.write('e')

def decode_dict(root, stream):
	stream.skip()
	value = {}
	first = True
	while not stream.consume_if_possible('e'):
		k = root.decode()
		if first:
			last_k = k
			first = False
		elif k<=last_k:
			# http://wiki.theory.org/BitTorrentSpecification#dictionaries says:
			#		Keys must be strings and appear in sorted order (sorted as raw strings, not alphanumerics).
			#		The strings should be compared using a binary comparison, not a culture-specific "natural" comparison.
			root.warning("Keys must be in order but {1!r} (the last key) and {0!r} (this key) are not.", k, last_k)
		v = root.decode()
		value[k] = v
	if not root.config_get("decorate"):
		validate_dict_keys(root, value)
	return value

ct_dict = CodableType(encode_dict, decode_dict, dict, "d")

class Encoder:
	def __init__(self):
		def encode_default(root, stream, value):
			raise CodingException(multistr('Unknown type:', type(value), ":", repr(value)))
		self.default = encode_default
		self.m = {}

	def register(self, f, t):
		self.m[t] = f

	def encode(self, root, stream, value):
		self.m.get(type(value), self.default)(root, stream, value)

			
class Decoder:
	def __init__(self):
		def decode_default(root, stream):
			raise CodingException(multistr("Don't know how to proceed with decode: ", stream.peek(), stream.tell()))
		self.default = decode_default
		self.m = {}
		
	def register(self, f, cs):
		for c in cs:
			self.m[c] = f

	def decode(self, root, stream):
		return self.m.get(stream.peek(), self.default)(root, stream)


class Instance(object):
	def __init__(self, root, stream):
		self.root = root
		self.stream = stream
		self.warnings = []

	def decode(self):
		start_offset = self.stream.tell()
		answer = self.root.d.decode(self, self.stream)
		end_offset = self.stream.tell()
		if self.config_get("decorate"):
			answer = (start_offset, end_offset, answer)
		return answer

	def encode(self, value):
		self.root.e.encode(self, self.stream, value)

	def must_be_permissible_dict_key(self, t):
		p = self.root.permissible_dict_keys
		if t not in p:
			raise CodingException("Key must of type "+str(list(p))+" but is "+str(t)+": "+repr(value))

	def config_get(self, word, default=None):
		return self.root.config.get(word, default)

	def warning(self, t, *a, **b):
		self.warnings.append(t.format(*a, **b))

class Coder:
	def __init__(self, **config):
		self.config = config
		self.e = Encoder()
		self.d = Decoder()

		self.permissible_dict_keys = set(config.get("permissible_dict_keys", [str] ))

		self.register(ct_direct)
		self.register(ct_list)
		self.register(ct_string)
		self.register(ct_int)
		self.register(ct_dict)
		if config.get("unicode"):
			self.register(ct_unicode)
		if config.get("float"):
			self.register(ct_float)
		if config.get("none"):
			self.register(ct_none)

	def register(self, ct):
		self.e.register(ct.ef, ct.et)
		self.d.register(ct.df, ct.dc)

	def encode_to_stream(self, stream, value):
		Instance(self, stream).encode(value)

	def decode_from_stream_with_messages(self, stream):
		i = Instance(self, stream)
		answer = i.decode()
		messages = i.warnings
		return (answer, messages)

	def decode_from_stream(self, stream):
		return self.decode_from_stream_with_messages(stream)[0]

	def encode_to_file(self, file, value):
		return self.encode_to_stream(file, value)

	def decode_from_file(self, file):
		return self.decode_from_stream(FileInputStream(file))

	def decode_from_file_with_messages(self, file):
		return self.decode_from_stream_with_messages(FileInputStream(file))

	def encode_to_string(self, value):
		file = StringIO.StringIO()
		self.encode_to_file(file, value)
		return file.getvalue()
		
	def decode_from_string(self, string):
		return self.decode_from_file(StringIO.StringIO(string))
		
	def decode_from_string_with_messages(self, string):
		return self.decode_from_file_with_messages(StringIO.StringIO(string))


# ---------------------------------------------------------------------------


legacy_coder = Coder()

def bencode(value):
	return legacy_coder.encode_to_string(value)

def bdecode(value):
	return legacy_coder.decode_from_string(value)

coder = Coder(unicode=True, float=True, none=True, permissible_dict_keys=[ int, str, unicode ])

if __name__ == "__main__":
	from example_bencoded import *


	def test_roundtrip(value):
		print "Trying", value
		rvalue = repr(value)
		encoded = coder.encode_to_string(value)
		print "Encoded to", encoded
		back = coder.decode_from_string(encoded)
		print "Decoded to", back
		bvalue = repr(back)
		assert rvalue == bvalue, multistr("Started with", rvalue, "but got back", bvalue)
		print

	divider = "-" * 75

	print divider

	test_roundtrip({ u"fish": 5, u"cheese": [7, 8] })
	test_roundtrip({ 3: 5, 2: [7, 8.3] })
	test_roundtrip(["hello", [{ "alfred": "trashbat", "wombat": [7, 8] }]])
	test_roundtrip(["hello", [{ "alfred": u"trashbat", "lard": [7, 8] }]])
	print "round trips work"

	print divider

	value, messages = coder.decode_from_string_with_messages(elliot_torrent)
	assert len(messages)==1
	message = messages[0]
	print message
	assert message=="Keys must be in order but 'created by' (the last key) and 'announce' (this key) are not."
	print "messages work"

	print divider

	decorating_coder = Coder(unicode=True, float=True, none=True, permissible_dict_keys=[ int, str, unicode ], decorate=True)
	d = decorating_coder.decode_from_string(flash_torrent)
	#print repr(v)
	assert type(d[2])==dict
	answer = None
	for k, v in d[2].iteritems():
		if k[2]=='info':
			s, e = v[0], v[1]
			print "info dict runs from {0} to {1}".format(s, e)
			info_content = flash_torrent[s:e]
			answer = sha1hash_of_string(info_content)
	assert answer=='ae31bd358f2b851756793fe4e375ec0f5aa4c359'
	print "decoration works"

	print divider

	x = coder.decode_from_string(flash_torrent)
	x['info'] = DirectValue(info_content)
	flash_torrent2 = coder.encode_to_string(x)
	assert flash_torrent==flash_torrent2
	print "round trips using DirectValue work"

	print divider

# ---------------------------------------------------------------------------

