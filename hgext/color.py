# color.py color output for the status and qseries commands
#
# Copyright (C) 2007 Kevin Christen <kevin.christen@gmail.com>
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

'''colorize output from some commands

This extension modifies the status and resolve commands to add color
to their output to reflect file status, the qseries command to add
color to reflect patch status (applied, unapplied, missing), and to
diff-related commands to highlight additions, removals, diff headers,
and trailing whitespace.

Other effects in addition to color, like bold and underlined text, are
also available. Effects are rendered with the ECMA-48 SGR control
function (aka ANSI escape codes).

Default effects may be overridden from your configuration file::

  [color]
  status.modified = blue bold underline red_background
  status.added = green bold
  status.removed = red bold blue_background
  status.deleted = cyan bold underline
  status.unknown = magenta bold underline
  status.ignored = black bold

  # 'none' turns off all effects
  status.clean = none
  status.copied = none

  qseries.applied = blue bold underline
  qseries.unapplied = black bold
  qseries.missing = red bold

  diff.diffline = bold
  diff.extended = cyan bold
  diff.file_a = red bold
  diff.file_b = green bold
  diff.hunk = magenta
  diff.deleted = red
  diff.inserted = green
  diff.changed = white
  diff.trailingwhitespace = bold red_background

  resolve.unresolved = red bold
  resolve.resolved = green bold

  bookmarks.current = green

  branches.active = none
  branches.closed = black bold
  branches.current = green
  branches.inactive = none

The color extension will try to detect whether to use ANSI codes or
Win32 console APIs, unless it is made explicit::

  [color]
  mode = ansi

Any value other than 'ansi', 'win32', or 'auto' will disable color.

'''

import os

from mercurial import commands, dispatch, extensions, ui as uimod, util
from mercurial.i18n import _

# start and stop parameters for effects
_effects = {'none': 0, 'black': 30, 'red': 31, 'green': 32, 'yellow': 33,
            'blue': 34, 'magenta': 35, 'cyan': 36, 'white': 37, 'bold': 1,
            'italic': 3, 'underline': 4, 'inverse': 7,
            'black_background': 40, 'red_background': 41,
            'green_background': 42, 'yellow_background': 43,
            'blue_background': 44, 'purple_background': 45,
            'cyan_background': 46, 'white_background': 47}

_styles = {'grep.match': 'red bold',
           'bookmarks.current': 'green',
           'branches.active': 'none',
           'branches.closed': 'black bold',
           'branches.current': 'green',
           'branches.inactive': 'none',
           'diff.changed': 'white',
           'diff.deleted': 'red',
           'diff.diffline': 'bold',
           'diff.extended': 'cyan bold',
           'diff.file_a': 'red bold',
           'diff.file_b': 'green bold',
           'diff.hunk': 'magenta',
           'diff.inserted': 'green',
           'diff.trailingwhitespace': 'bold red_background',
           'diffstat.deleted': 'red',
           'diffstat.inserted': 'green',
           'ui.prompt': 'yellow',
           'log.changeset': 'yellow',
           'resolve.resolved': 'green bold',
           'resolve.unresolved': 'red bold',
           'status.added': 'green bold',
           'status.clean': 'none',
           'status.copied': 'none',
           'status.deleted': 'cyan bold underline',
           'status.ignored': 'black bold',
           'status.modified': 'blue bold',
           'status.removed': 'red bold',
           'status.unknown': 'magenta bold underline'}


def render_effects(text, effects):
    'Wrap text in commands to turn on each effect.'
    if not text:
        return text
    start = [str(_effects[e]) for e in ['none'] + effects.split()]
    start = '\033[' + ';'.join(start) + 'm'
    stop = '\033[' + str(_effects['none']) + 'm'
    return ''.join([start, text, stop])

def extstyles():
    for name, ext in extensions.extensions():
        _styles.update(getattr(ext, 'colortable', {}))

def configstyles(ui):
    for status, cfgeffects in ui.configitems('color'):
        if '.' not in status:
            continue
        cfgeffects = ui.configlist('color', status)
        if cfgeffects:
            good = []
            for e in cfgeffects:
                if e in _effects:
                    good.append(e)
                else:
                    ui.warn(_("ignoring unknown color/effect %r "
                              "(configured in color.%s)\n")
                            % (e, status))
            _styles[status] = ' '.join(good)

class colorui(uimod.ui):
    def popbuffer(self, labeled=False):
        if labeled:
            return ''.join(self.label(a, label) for a, label
                           in self._buffers.pop())
        return ''.join(a for a, label in self._buffers.pop())

    _colormode = 'ansi'
    def write(self, *args, **opts):
        label = opts.get('label', '')
        if self._buffers:
            self._buffers[-1].extend([(str(a), label) for a in args])
        elif self._colormode == 'win32':
            for a in args:
                win32print(a, super(colorui, self).write, **opts)
        else:
            return super(colorui, self).write(
                *[self.label(str(a), label) for a in args], **opts)

    def write_err(self, *args, **opts):
        label = opts.get('label', '')
        if self._colormode == 'win32':
            for a in args:
                win32print(a, super(colorui, self).write_err, **opts)
        else:
            return super(colorui, self).write_err(
                *[self.label(str(a), label) for a in args], **opts)

    def label(self, msg, label):
        effects = []
        for l in label.split():
            s = _styles.get(l, '')
            if s:
                effects.append(s)
        effects = ''.join(effects)
        if effects:
            return '\n'.join([render_effects(s, effects)
                              for s in msg.split('\n')])
        return msg


def uisetup(ui):
    if ui.plain():
        return
    mode = ui.config('color', 'mode', 'auto')
    if mode == 'auto':
        if os.name == 'nt' and 'TERM' not in os.environ:
            # looks line a cmd.exe console, use win32 API or nothing
            mode = w32effects and 'win32' or 'none'
        else:
            mode = 'ansi'
    if mode == 'win32':
        if w32effects is None:
            # only warn if color.mode is explicitly set to win32
            ui.warn(_('warning: failed to set color mode to %s\n') % mode)
            return
        _effects.update(w32effects)
    elif mode != 'ansi':
        return
    def colorcmd(orig, ui_, opts, cmd, cmdfunc):
        coloropt = opts['color']
        auto = coloropt == 'auto'
        always = util.parsebool(coloropt)
        if (always or
            (always is None and
             (auto and (os.environ.get('TERM') != 'dumb' and ui_.formatted())))):
            colorui._colormode = mode
            colorui.__bases__ = (ui_.__class__,)
            ui_.__class__ = colorui
            extstyles()
            configstyles(ui_)
        return orig(ui_, opts, cmd, cmdfunc)
    extensions.wrapfunction(dispatch, '_runcommand', colorcmd)

def extsetup(ui):
    commands.globalopts.append(
        ('', 'color', 'auto',
         # i18n: 'always', 'auto', and 'never' are keywords and should
         # not be translated
         _("when to colorize (boolean, always, auto, or never)"),
         _('TYPE')))

if os.name != 'nt':
    w32effects = None
else:
    import re, ctypes

    _kernel32 = ctypes.windll.kernel32

    _WORD = ctypes.c_ushort

    _INVALID_HANDLE_VALUE = -1

    class _COORD(ctypes.Structure):
        _fields_ = [('X', ctypes.c_short),
                    ('Y', ctypes.c_short)]

    class _SMALL_RECT(ctypes.Structure):
        _fields_ = [('Left', ctypes.c_short),
                    ('Top', ctypes.c_short),
                    ('Right', ctypes.c_short),
                    ('Bottom', ctypes.c_short)]

    class _CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
        _fields_ = [('dwSize', _COORD),
                    ('dwCursorPosition', _COORD),
                    ('wAttributes', _WORD),
                    ('srWindow', _SMALL_RECT),
                    ('dwMaximumWindowSize', _COORD)]

    _STD_OUTPUT_HANDLE = 0xfffffff5L # (DWORD)-11
    _STD_ERROR_HANDLE = 0xfffffff4L  # (DWORD)-12

    _FOREGROUND_BLUE = 0x0001
    _FOREGROUND_GREEN = 0x0002
    _FOREGROUND_RED = 0x0004
    _FOREGROUND_INTENSITY = 0x0008

    _BACKGROUND_BLUE = 0x0010
    _BACKGROUND_GREEN = 0x0020
    _BACKGROUND_RED = 0x0040
    _BACKGROUND_INTENSITY = 0x0080

    _COMMON_LVB_REVERSE_VIDEO = 0x4000
    _COMMON_LVB_UNDERSCORE = 0x8000

    # http://msdn.microsoft.com/en-us/library/ms682088%28VS.85%29.aspx
    w32effects = {
        'none': -1,
        'black': 0,
        'red': _FOREGROUND_RED,
        'green': _FOREGROUND_GREEN,
        'yellow': _FOREGROUND_RED | _FOREGROUND_GREEN,
        'blue': _FOREGROUND_BLUE,
        'magenta': _FOREGROUND_BLUE | _FOREGROUND_RED,
        'cyan': _FOREGROUND_BLUE | _FOREGROUND_GREEN,
        'white': _FOREGROUND_RED | _FOREGROUND_GREEN | _FOREGROUND_BLUE,
        'bold': _FOREGROUND_INTENSITY,
        'black_background': 0x100,                  # unused value > 0x0f
        'red_background': _BACKGROUND_RED,
        'green_background': _BACKGROUND_GREEN,
        'yellow_background': _BACKGROUND_RED | _BACKGROUND_GREEN,
        'blue_background': _BACKGROUND_BLUE,
        'purple_background': _BACKGROUND_BLUE | _BACKGROUND_RED,
        'cyan_background': _BACKGROUND_BLUE | _BACKGROUND_GREEN,
        'white_background': (_BACKGROUND_RED | _BACKGROUND_GREEN |
                             _BACKGROUND_BLUE),
        'bold_background': _BACKGROUND_INTENSITY,
        'underline': _COMMON_LVB_UNDERSCORE,  # double-byte charsets only
        'inverse': _COMMON_LVB_REVERSE_VIDEO, # double-byte charsets only
    }

    passthrough = set([_FOREGROUND_INTENSITY,
                       _BACKGROUND_INTENSITY,
                       _COMMON_LVB_UNDERSCORE,
                       _COMMON_LVB_REVERSE_VIDEO])

    stdout = _kernel32.GetStdHandle(
                  _STD_OUTPUT_HANDLE)  # don't close the handle returned
    if stdout is None or stdout == _INVALID_HANDLE_VALUE:
        w32effects = None
    else:
        csbi = _CONSOLE_SCREEN_BUFFER_INFO()
        if not _kernel32.GetConsoleScreenBufferInfo(
                    stdout, ctypes.byref(csbi)):
            # stdout may not support GetConsoleScreenBufferInfo()
            # when called from subprocess or redirected
            w32effects = None
        else:
            origattr = csbi.wAttributes
            ansire = re.compile('\033\[([^m]*)m([^\033]*)(.*)',
                                re.MULTILINE | re.DOTALL)

    def win32print(text, orig, **opts):
        label = opts.get('label', '')
        attr = origattr

        def mapcolor(val, attr):
            if val == -1:
                return origattr
            elif val in passthrough:
                return attr | val
            elif val > 0x0f:
                return (val & 0x70) | (attr & 0x8f)
            else:
                return (val & 0x07) | (attr & 0xf8)

        # determine console attributes based on labels
        for l in label.split():
            style = _styles.get(l, '')
            for effect in style.split():
                attr = mapcolor(w32effects[effect], attr)

        # hack to ensure regexp finds data
        if not text.startswith('\033['):
            text = '\033[m' + text

        # Look for ANSI-like codes embedded in text
        m = re.match(ansire, text)
        while m:
            for sattr in m.group(1).split(';'):
                if sattr:
                    attr = mapcolor(int(sattr), attr)
            _kernel32.SetConsoleTextAttribute(stdout, attr)
            orig(m.group(2), **opts)
            m = re.match(ansire, m.group(3))

        # Explicity reset original attributes
        _kernel32.SetConsoleTextAttribute(stdout, origattr)
