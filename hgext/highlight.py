"""
This is Mercurial extension for syntax highlighting in the file
revision view of hgweb.

It depends on the pygments syntax highlighting library:
http://pygments.org/

To enable the extension add this to hgrc:

[extensions]
hgext.highlight =

There is a single configuration option:

[web]
pygments_style = <style>

The default is 'colorful'.  If this is changed the corresponding CSS
file should be re-generated by running

# pygmentize -f html -S <newstyle>


-- Adam Hupp <adam@hupp.org>


"""

from mercurial import demandimport
demandimport.ignore.extend(['pkgutil',
                            'pkg_resources',
                            '__main__',])

from mercurial.hgweb.hgweb_mod import hgweb
from mercurial import util
from mercurial.templatefilters import filters

from pygments import highlight
from pygments.util import ClassNotFound
from pygments.lexers import guess_lexer, guess_lexer_for_filename, TextLexer
from pygments.formatters import HtmlFormatter

SYNTAX_CSS = ('\n<link rel="stylesheet" href="#staticurl#highlight.css" '
              'type="text/css" />')

def pygmentize(self, tmpl, fctx, field):
    # append a <link ...> to the syntax highlighting css
    old_header = ''.join(tmpl('header'))
    if SYNTAX_CSS not in old_header:
        new_header =  old_header + SYNTAX_CSS
        tmpl.cache['header'] = new_header

    text = fctx.data()
    if util.binary(text):
        return

    style = self.config("web", "pygments_style", "colorful")
    # To get multi-line strings right, we can't format line-by-line
    try:
        lexer = guess_lexer_for_filename(fctx.path(), text,
                                         encoding=util._encoding)
    except ClassNotFound:
        try:
            lexer = guess_lexer(text, encoding=util._encoding)
        except ClassNotFound:
            lexer = TextLexer(encoding=util._encoding)

    formatter = HtmlFormatter(style=style, encoding=util._encoding)

    colorized = highlight(text, lexer, formatter)
    # strip wrapping div
    colorized = colorized[:colorized.find('\n</pre>')]
    colorized = colorized[colorized.find('<pre>')+5:]
    coloriter = iter(colorized.splitlines())

    filters['colorize'] = lambda x: coloriter.next()

    oldl = tmpl.cache[field]
    newl = oldl.replace('line|escape', 'line|colorize')
    tmpl.cache[field] = newl

def filerevision_highlight(self, tmpl, fctx):
    pygmentize(self, tmpl, fctx, 'fileline')

    return realrevision(self, tmpl, fctx)

def fileannotate_highlight(self, tmpl, fctx):
    pygmentize(self, tmpl, fctx, 'annotateline')

    return realannotate(self, tmpl, fctx)

# monkeypatch in the new version
# should be safer than overriding the method in a derived class
# and then patching the class
realrevision = hgweb.filerevision
hgweb.filerevision = filerevision_highlight
realannotate = hgweb.fileannotate
hgweb.fileannotate = fileannotate_highlight
