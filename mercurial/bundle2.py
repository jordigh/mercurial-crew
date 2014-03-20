# bundle2.py - generic container format to transmit arbitrary data.
#
# Copyright 2013 Facebook, Inc.
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.
"""Handling of the new bundle2 format

The goal of bundle2 is to act as an atomically packet to transmit a set of
payloads in an application agnostic way. It consist in a sequence of "parts"
that will be handed to and processed by the application layer.


General format architecture
===========================

The format is architectured as follow

 - magic string
 - stream level parameters
 - payload parts (any number)
 - end of stream marker.

the Binary format
============================

All numbers are unsigned and big endian.

stream level parameters
------------------------

Binary format is as follow

:params size: (16 bits integer)

  The total number of Bytes used by the parameters

:params value: arbitrary number of Bytes

  A blob of `params size` containing the serialized version of all stream level
  parameters.

  The blob contains a space separated list of parameters. parameter with value
  are stored in the form `<name>=<value>`. Both name and value are urlquoted.

  Empty name are obviously forbidden.

  Name MUST start with a letter. If this first letter is lower case, the
  parameter is advisory and can be safefly ignored. However when the first
  letter is capital, the parameter is mandatory and the bundling process MUST
  stop if he is not able to proceed it.

  Stream parameters use a simple textual format for two main reasons:

  - Stream level parameters should remains simple and we want to discourage any
    crazy usage.
  - Textual data allow easy human inspection of a the bundle2 header in case of
    troubles.

  Any Applicative level options MUST go into a bundle2 part instead.

Payload part
------------------------

Binary format is as follow

:header size: (16 bits inter)

  The total number of Bytes used by the part headers. When the header is empty
  (size = 0) this is interpreted as the end of stream marker.

:header:

    The header defines how to interpret the part. It contains two piece of
    data: the part type, and the part parameters.

    The part type is used to route an application level handler, that can
    interpret payload.

    Part parameters are passed to the application level handler.  They are
    meant to convey information that will help the application level object to
    interpret the part payload.

    The binary format of the header is has follow

    :typesize: (one byte)
    :typename: alphanumerical part name
    :option: we do not support option yet this denoted by two 16 bites zero.

:payload:

    The current payload is a 32bit integer with a value of 0. This is
    considered an "empty" payload.
"""

import util
import struct
import urllib
import string

import changegroup
from i18n import _

_pack = struct.pack
_unpack = struct.unpack

_magicstring = 'HG20'

_fstreamparamsize = '>H'
_fpartheadersize = '>H'
_fparttypesize = '>B'

class bundle20(object):
    """represent an outgoing bundle2 container

    Use the `addparam` method to add stream level parameter. and `addpart` to
    populate it. Then call `getchunks` to retrieve all the binary chunks of
    datathat compose the bundle2 container."""

    def __init__(self, ui):
        self.ui = ui
        self._params = []
        self._parts = []

    def addparam(self, name, value=None):
        """add a stream level parameter"""
        if not name:
            raise ValueError('empty parameter name')
        if name[0] not in string.letters:
            raise ValueError('non letter first character: %r' % name)
        self._params.append((name, value))

    def addpart(self, part):
        """add a new part to the bundle2 container

        Parts contains the actuall applicative payload."""
        self._parts.append(part)

    def getchunks(self):
        self.ui.debug('start emission of %s stream\n' % _magicstring)
        yield _magicstring
        param = self._paramchunk()
        self.ui.debug('bundle parameter: %s\n' % param)
        yield _pack(_fstreamparamsize, len(param))
        if param:
            yield param

        self.ui.debug('start of parts\n')
        for part in self._parts:
            self.ui.debug('bundle part: "%s"\n' % part.type)
            for chunk in part.getchunks():
                yield chunk
        self.ui.debug('end of bundle\n')
        yield '\0\0'

    def _paramchunk(self):
        """return a encoded version of all stream parameters"""
        blocks = []
        for par, value in self._params:
            par = urllib.quote(par)
            if value is not None:
                value = urllib.quote(value)
                par = '%s=%s' % (par, value)
            blocks.append(par)
        return ' '.join(blocks)

class unbundle20(object):
    """interpret a bundle2 stream

    (this will eventually yield parts)"""

    def __init__(self, ui, fp):
        self.ui = ui
        self._fp = fp
        header = self._readexact(4)
        magic, version = header[0:2], header[2:4]
        if magic != 'HG':
            raise util.Abort(_('not a Mercurial bundle'))
        if version != '20':
            raise util.Abort(_('unknown bundle version %s') % version)
        self.ui.debug('start processing of %s stream\n' % header)

    def _unpack(self, format):
        """unpack this struct format from the stream"""
        data = self._readexact(struct.calcsize(format))
        return _unpack(format, data)

    def _readexact(self, size):
        """read exactly <size> bytes from the stream"""
        return changegroup.readexactly(self._fp, size)

    @util.propertycache
    def params(self):
        """dictionnary of stream level parameters"""
        self.ui.debug('reading bundle2 stream parameters\n')
        params = {}
        paramssize = self._unpack(_fstreamparamsize)[0]
        if paramssize:
            for p in self._readexact(paramssize).split(' '):
                p = p.split('=', 1)
                p = [urllib.unquote(i) for i in p]
                if len(p) < 2:
                    p.append(None)
                self._processparam(*p)
                params[p[0]] = p[1]
        return params

    def _processparam(self, name, value):
        """process a parameter, applying its effect if needed

        Parameter starting with a lower case letter are advisory and will be
        ignored when unknown.  Those starting with an upper case letter are
        mandatory and will this function will raise a KeyError when unknown.

        Note: no option are currently supported. Any input will be either
              ignored or failing.
        """
        if not name:
            raise ValueError('empty parameter name')
        if name[0] not in string.letters:
            raise ValueError('non letter first character: %r' % name)
        # Some logic will be later added here to try to process the option for
        # a dict of known parameter.
        if name[0].islower():
            self.ui.debug("ignoring unknown parameter %r\n" % name)
        else:
            raise KeyError(name)


    def __iter__(self):
        """yield all parts contained in the stream"""
        # make sure param have been loaded
        self.params
        self.ui.debug('start extraction of bundle2 parts\n')
        part = self._readpart()
        while part is not None:
            yield part
            part = self._readpart()
        self.ui.debug('end of bundle2 stream\n')

    def _readpart(self):
        """return None when an end of stream markers is reach"""

        headersize = self._unpack(_fpartheadersize)[0]
        self.ui.debug('part header size: %i\n' % headersize)
        if not headersize:
            return None
        headerblock = self._readexact(headersize)
        # some utility to help reading from the header block
        self._offset = 0 # layer violation to have something easy to understand
        def fromheader(size):
            """return the next <size> byte from the header"""
            offset = self._offset
            data = headerblock[offset:(offset + size)]
            self._offset = offset + size
            return data
        typesize = _unpack(_fparttypesize, fromheader(1))[0]
        parttype = fromheader(typesize)
        self.ui.debug('part type: "%s"\n' % parttype)
        current = part(parttype)
        assert fromheader(2) == '\0\0' # no option for now
        del self._offset # clean up layer, nobody saw anything.
        self.ui.debug('part parameters: 0\n')
        assert self._readexact(4) == '\0\0\0\0' #empty payload
        self.ui.debug('payload chunk size: 0\n')
        return current


class part(object):
    """A bundle2 part contains application level payload

    The part `type` is used to route the part to the application level
    handler.
    """

    def __init__(self, parttype, data=''):
        self.type = parttype
        self.data = data

    def getchunks(self):
        ### header
        header = [_pack(_fparttypesize, len(self.type)),
                  self.type,
                  '\0\0', # No option support for now.
                 ]
        headerchunk = ''.join(header)
        yield _pack(_fpartheadersize, len(headerchunk))
        yield headerchunk
        # force empty part for now
        yield '\0\0\0\0'


