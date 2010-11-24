# this is hack to make sure no escape characters are inserted into the output
import os
if 'TERM' in os.environ:
    del os.environ['TERM']
import doctest

import mercurial.changelog
doctest.testmod(mercurial.changelog)

import mercurial.dagparser
doctest.testmod(mercurial.dagparser, optionflags=doctest.NORMALIZE_WHITESPACE)

import mercurial.match
doctest.testmod(mercurial.match)

import mercurial.encoding
doctest.testmod(mercurial.encoding)

import hgext.convert.cvsps
doctest.testmod(hgext.convert.cvsps)
