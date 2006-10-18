# patch.py - patch file parsing routines
#
# Copyright 2006 Brendan Cully <brendan@kublai.com>
#
# This software may be used and distributed according to the terms
# of the GNU General Public License, incorporated herein by reference.

from demandload import demandload
from i18n import gettext as _
from node import *
demandload(globals(), "base85 cmdutil mdiff util")
demandload(globals(), "cStringIO email.Parser errno os popen2 re shutil sha")
demandload(globals(), "sys tempfile zlib")

# helper functions

def copyfile(src, dst, basedir=None):
    if not basedir:
        basedir = os.getcwd()

    abssrc, absdst = [os.path.join(basedir, n) for n in (src, dst)]
    if os.path.exists(absdst):
        raise util.Abort(_("cannot create %s: destination already exists") %
                         dst)

    targetdir = os.path.dirname(absdst)
    if not os.path.isdir(targetdir):
        os.makedirs(targetdir)
    try:
        shutil.copyfile(abssrc, absdst)
        shutil.copymode(abssrc, absdst)
    except shutil.Error, inst:
        raise util.Abort(str(inst))

# public functions

def extract(ui, fileobj):
    '''extract patch from data read from fileobj.

    patch can be normal patch or contained in email message.

    return tuple (filename, message, user, date). any item in returned
    tuple can be None.  if filename is None, fileobj did not contain
    patch. caller must unlink filename when done.'''

    # attempt to detect the start of a patch
    # (this heuristic is borrowed from quilt)
    diffre = re.compile(r'^(?:Index:[ \t]|diff[ \t]|RCS file: |' +
                        'retrieving revision [0-9]+(\.[0-9]+)*$|' +
                        '(---|\*\*\*)[ \t])', re.MULTILINE)

    fd, tmpname = tempfile.mkstemp(prefix='hg-patch-')
    tmpfp = os.fdopen(fd, 'w')
    try:
        hgpatch = False

        msg = email.Parser.Parser().parse(fileobj)

        message = msg['Subject']
        user = msg['From']
        # should try to parse msg['Date']
        date = None

        if message:
            message = message.replace('\n\t', ' ')
            ui.debug('Subject: %s\n' % message)
        if user:
            ui.debug('From: %s\n' % user)
        diffs_seen = 0
        ok_types = ('text/plain', 'text/x-diff', 'text/x-patch')

        for part in msg.walk():
            content_type = part.get_content_type()
            ui.debug('Content-Type: %s\n' % content_type)
            if content_type not in ok_types:
                continue
            payload = part.get_payload(decode=True)
            m = diffre.search(payload)
            if m:
                ui.debug(_('found patch at byte %d\n') % m.start(0))
                diffs_seen += 1
                cfp = cStringIO.StringIO()
                if message:
                    cfp.write(message)
                    cfp.write('\n')
                for line in payload[:m.start(0)].splitlines():
                    if line.startswith('# HG changeset patch'):
                        ui.debug(_('patch generated by hg export\n'))
                        hgpatch = True
                        # drop earlier commit message content
                        cfp.seek(0)
                        cfp.truncate()
                    elif hgpatch:
                        if line.startswith('# User '):
                            user = line[7:]
                            ui.debug('From: %s\n' % user)
                        elif line.startswith("# Date "):
                            date = line[7:]
                    if not line.startswith('# '):
                        cfp.write(line)
                        cfp.write('\n')
                message = cfp.getvalue()
                if tmpfp:
                    tmpfp.write(payload)
                    if not payload.endswith('\n'):
                        tmpfp.write('\n')
            elif not diffs_seen and message and content_type == 'text/plain':
                message += '\n' + payload
    except:
        tmpfp.close()
        os.unlink(tmpname)
        raise

    tmpfp.close()
    if not diffs_seen:
        os.unlink(tmpname)
        return None, message, user, date
    return tmpname, message, user, date

def readgitpatch(patchname):
    """extract git-style metadata about patches from <patchname>"""
    class gitpatch:
        "op is one of ADD, DELETE, RENAME, MODIFY or COPY"
        def __init__(self, path):
            self.path = path
            self.oldpath = None
            self.mode = None
            self.op = 'MODIFY'
            self.copymod = False
            self.lineno = 0
            self.binary = False

    # Filter patch for git information
    gitre = re.compile('diff --git a/(.*) b/(.*)')
    pf = file(patchname)
    gp = None
    gitpatches = []
    # Can have a git patch with only metadata, causing patch to complain
    dopatch = False

    lineno = 0
    for line in pf:
        lineno += 1
        if line.startswith('diff --git'):
            m = gitre.match(line)
            if m:
                if gp:
                    gitpatches.append(gp)
                src, dst = m.group(1,2)
                gp = gitpatch(dst)
                gp.lineno = lineno
        elif gp:
            if line.startswith('--- '):
                if gp.op in ('COPY', 'RENAME'):
                    gp.copymod = True
                    dopatch = 'filter'
                gitpatches.append(gp)
                gp = None
                if not dopatch:
                    dopatch = True
                continue
            if line.startswith('rename from '):
                gp.op = 'RENAME'
                gp.oldpath = line[12:].rstrip()
            elif line.startswith('rename to '):
                gp.path = line[10:].rstrip()
            elif line.startswith('copy from '):
                gp.op = 'COPY'
                gp.oldpath = line[10:].rstrip()
            elif line.startswith('copy to '):
                gp.path = line[8:].rstrip()
            elif line.startswith('deleted file'):
                gp.op = 'DELETE'
            elif line.startswith('new file mode '):
                gp.op = 'ADD'
                gp.mode = int(line.rstrip()[-3:], 8)
            elif line.startswith('new mode '):
                gp.mode = int(line.rstrip()[-3:], 8)
            elif line.startswith('GIT binary patch'):
                if not dopatch:
                    dopatch = 'binary'
                gp.binary = True
    if gp:
        gitpatches.append(gp)

    if not gitpatches:
        dopatch = True

    return (dopatch, gitpatches)

def dogitpatch(patchname, gitpatches, cwd=None):
    """Preprocess git patch so that vanilla patch can handle it"""
    def extractbin(fp):
        line = fp.readline().rstrip()
        while line and not line.startswith('literal '):
            line = fp.readline().rstrip()
        if not line:
            return
        size = int(line[8:])
        dec = []
        line = fp.readline().rstrip()
        while line:
            l = line[0]
            if l <= 'Z' and l >= 'A':
                l = ord(l) - ord('A') + 1
            else:
                l = ord(l) - ord('a') + 27
            dec.append(base85.b85decode(line[1:])[:l])
            line = fp.readline().rstrip()
        text = zlib.decompress(''.join(dec))
        if len(text) != size:
            raise util.Abort(_('binary patch is %d bytes, not %d') %
                             (len(text), size))
        return text

    pf = file(patchname)
    pfline = 1

    fd, patchname = tempfile.mkstemp(prefix='hg-patch-')
    tmpfp = os.fdopen(fd, 'w')

    try:
        for i in range(len(gitpatches)):
            p = gitpatches[i]
            if not p.copymod and not p.binary:
                continue

            # rewrite patch hunk
            while pfline < p.lineno:
                tmpfp.write(pf.readline())
                pfline += 1

            if p.binary:
                text = extractbin(pf)
                if not text:
                    raise util.Abort(_('binary patch extraction failed'))
                if not cwd:
                    cwd = os.getcwd()
                absdst = os.path.join(cwd, p.path)
                basedir = os.path.dirname(absdst)
                if not os.path.isdir(basedir):
                    os.makedirs(basedir)
                out = file(absdst, 'wb')
                out.write(text)
                out.close()
            elif p.copymod:
                copyfile(p.oldpath, p.path, basedir=cwd)
                tmpfp.write('diff --git a/%s b/%s\n' % (p.path, p.path))
                line = pf.readline()
                pfline += 1
                while not line.startswith('--- a/'):
                    tmpfp.write(line)
                    line = pf.readline()
                    pfline += 1
                tmpfp.write('--- a/%s\n' % p.path)

        line = pf.readline()
        while line:
            tmpfp.write(line)
            line = pf.readline()
    except:
        tmpfp.close()
        os.unlink(patchname)
        raise

    tmpfp.close()
    return patchname

def patch(patchname, ui, strip=1, cwd=None, files={}):
    """apply the patch <patchname> to the working directory.
    a list of patched files is returned"""

    # helper function
    def __patch(patchname):
        """patch and updates the files and fuzz variables"""
        fuzz = False

        patcher = util.find_in_path('gpatch', os.environ.get('PATH', ''),
                                    'patch')
        args = []
        if cwd:
            args.append('-d %s' % util.shellquote(cwd))
        fp = os.popen('%s %s -p%d < %s' % (patcher, ' '.join(args), strip,
                                           util.shellquote(patchname)))

        for line in fp:
            line = line.rstrip()
            ui.note(line + '\n')
            if line.startswith('patching file '):
                pf = util.parse_patch_output(line)
                printed_file = False
                files.setdefault(pf, (None, None))
            elif line.find('with fuzz') >= 0:
                fuzz = True
                if not printed_file:
                    ui.warn(pf + '\n')
                    printed_file = True
                ui.warn(line + '\n')
            elif line.find('saving rejects to file') >= 0:
                ui.warn(line + '\n')
            elif line.find('FAILED') >= 0:
                if not printed_file:
                    ui.warn(pf + '\n')
                    printed_file = True
                ui.warn(line + '\n')
        code = fp.close()
        if code:
            raise util.Abort(_("patch command failed: %s") %
                             util.explain_exit(code)[0])
        return fuzz

    (dopatch, gitpatches) = readgitpatch(patchname)
    for gp in gitpatches:
        files[gp.path] = (gp.op, gp)

    fuzz = False
    if dopatch:
        if dopatch in ('filter', 'binary'):
            patchname = dogitpatch(patchname, gitpatches, cwd=cwd)
        try:
            if dopatch != 'binary':
                fuzz = __patch(patchname)
        finally:
            if dopatch == 'filter':
                os.unlink(patchname)

    return fuzz

def diffopts(ui, opts={}):
    return mdiff.diffopts(
        text=opts.get('text'),
        git=(opts.get('git') or
                  ui.configbool('diff', 'git', None)),
        nodates=(opts.get('nodates') or
                  ui.configbool('diff', 'nodates', None)),
        showfunc=(opts.get('show_function') or
                  ui.configbool('diff', 'showfunc', None)),
        ignorews=(opts.get('ignore_all_space') or
                  ui.configbool('diff', 'ignorews', None)),
        ignorewsamount=(opts.get('ignore_space_change') or
                        ui.configbool('diff', 'ignorewsamount', None)),
        ignoreblanklines=(opts.get('ignore_blank_lines') or
                          ui.configbool('diff', 'ignoreblanklines', None)))

def updatedir(ui, repo, patches, wlock=None):
    '''Update dirstate after patch application according to metadata'''
    if not patches:
        return
    copies = []
    removes = []
    cfiles = patches.keys()
    cwd = repo.getcwd()
    if cwd:
        cfiles = [util.pathto(cwd, f) for f in patches.keys()]
    for f in patches:
        ctype, gp = patches[f]
        if ctype == 'RENAME':
            copies.append((gp.oldpath, gp.path, gp.copymod))
            removes.append(gp.oldpath)
        elif ctype == 'COPY':
            copies.append((gp.oldpath, gp.path, gp.copymod))
        elif ctype == 'DELETE':
            removes.append(gp.path)
    for src, dst, after in copies:
        if not after:
            copyfile(src, dst, repo.root)
        repo.copy(src, dst, wlock=wlock)
    if removes:
        repo.remove(removes, True, wlock=wlock)
    for f in patches:
        ctype, gp = patches[f]
        if gp and gp.mode:
            x = gp.mode & 0100 != 0
            dst = os.path.join(repo.root, gp.path)
            util.set_exec(dst, x)
    cmdutil.addremove(repo, cfiles, wlock=wlock)
    files = patches.keys()
    files.extend([r for r in removes if r not in files])
    files.sort()

    return files

def b85diff(fp, to, tn):
    '''print base85-encoded binary diff'''
    def gitindex(text):
        if not text:
            return '0' * 40
        l = len(text)
        s = sha.new('blob %d\0' % l)
        s.update(text)
        return s.hexdigest()

    def fmtline(line):
        l = len(line)
        if l <= 26:
            l = chr(ord('A') + l - 1)
        else:
            l = chr(l - 26 + ord('a') - 1)
        return '%c%s\n' % (l, base85.b85encode(line, True))

    def chunk(text, csize=52):
        l = len(text)
        i = 0
        while i < l:
            yield text[i:i+csize]
            i += csize

    # TODO: deltas
    l = len(tn)
    fp.write('index %s..%s\nGIT binary patch\nliteral %s\n' %
             (gitindex(to), gitindex(tn), len(tn)))

    tn = ''.join([fmtline(l) for l in chunk(zlib.compress(tn))])
    fp.write(tn)
    fp.write('\n')

def diff(repo, node1=None, node2=None, files=None, match=util.always,
         fp=None, changes=None, opts=None):
    '''print diff of changes to files between two nodes, or node and
    working directory.

    if node1 is None, use first dirstate parent instead.
    if node2 is None, compare node1 with working directory.'''

    if opts is None:
        opts = mdiff.defaultopts
    if fp is None:
        fp = repo.ui

    if not node1:
        node1 = repo.dirstate.parents()[0]

    clcache = {}
    def getchangelog(n):
        if n not in clcache:
            clcache[n] = repo.changelog.read(n)
        return clcache[n]
    mcache = {}
    def getmanifest(n):
        if n not in mcache:
            mcache[n] = repo.manifest.read(n)
        return mcache[n]
    fcache = {}
    def getfile(f):
        if f not in fcache:
            fcache[f] = repo.file(f)
        return fcache[f]

    # reading the data for node1 early allows it to play nicely
    # with repo.status and the revlog cache.
    change = getchangelog(node1)
    mmap = getmanifest(change[0])
    date1 = util.datestr(change[2])

    if not changes:
        changes = repo.status(node1, node2, files, match=match)[:5]
    modified, added, removed, deleted, unknown = changes
    if files:
        def filterfiles(filters):
            l = [x for x in filters if x in files]

            for t in files:
                if not t.endswith("/"):
                    t += "/"
                l += [x for x in filters if x.startswith(t)]
            return l

        modified, added, removed = map(filterfiles, (modified, added, removed))

    if not modified and not added and not removed:
        return

    def renamedbetween(f, n1, n2):
        r1, r2 = map(repo.changelog.rev, (n1, n2))
        src = None
        while r2 > r1:
            cl = getchangelog(n2)[0]
            m = getmanifest(cl)
            try:
                src = getfile(f).renamed(m[f])
            except KeyError:
                return None
            if src:
                f = src[0]
            n2 = repo.changelog.parents(n2)[0]
            r2 = repo.changelog.rev(n2)
        return src

    if node2:
        change = getchangelog(node2)
        mmap2 = getmanifest(change[0])
        _date2 = util.datestr(change[2])
        def date2(f):
            return _date2
        def read(f):
            return getfile(f).read(mmap2[f])
        def renamed(f):
            return renamedbetween(f, node1, node2)
    else:
        tz = util.makedate()[1]
        _date2 = util.datestr()
        def date2(f):
            try:
                return util.datestr((os.lstat(repo.wjoin(f)).st_mtime, tz))
            except OSError, err:
                if err.errno != errno.ENOENT: raise
                return _date2
        def read(f):
            return repo.wread(f)
        def renamed(f):
            src = repo.dirstate.copied(f)
            parent = repo.dirstate.parents()[0]
            if src:
                f = src[0]
            of = renamedbetween(f, node1, parent)
            if of:
                return of
            elif src:
                cl = getchangelog(parent)[0]
                return (src, getmanifest(cl)[src])
            else:
                return None

    if repo.ui.quiet:
        r = None
    else:
        hexfunc = repo.ui.debugflag and hex or short
        r = [hexfunc(node) for node in [node1, node2] if node]

    if opts.git:
        copied = {}
        for f in added:
            src = renamed(f)
            if src:
                copied[f] = src
        srcs = [x[1][0] for x in copied.items()]

    all = modified + added + removed
    all.sort()
    for f in all:
        to = None
        tn = None
        dodiff = True
        header = []
        if f in mmap:
            to = getfile(f).read(mmap[f])
        if f not in removed:
            tn = read(f)
        if opts.git:
            def gitmode(x):
                return x and '100755' or '100644'
            def addmodehdr(header, omode, nmode):
                if omode != nmode:
                    header.append('old mode %s\n' % omode)
                    header.append('new mode %s\n' % nmode)

            a, b = f, f
            if f in added:
                if node2:
                    mode = gitmode(mmap2.execf(f))
                else:
                    mode = gitmode(util.is_exec(repo.wjoin(f), None))
                if f in copied:
                    a, arev = copied[f]
                    omode = gitmode(mmap.execf(a))
                    addmodehdr(header, omode, mode)
                    op = a in removed and 'rename' or 'copy'
                    header.append('%s from %s\n' % (op, a))
                    header.append('%s to %s\n' % (op, f))
                    to = getfile(a).read(arev)
                else:
                    header.append('new file mode %s\n' % mode)
                    if util.binary(tn):
                        dodiff = 'binary'
            elif f in removed:
                if f in srcs:
                    dodiff = False
                else:
                    mode = gitmode(mmap.execf(f))
                    header.append('deleted file mode %s\n' % mode)
            else:
                omode = gitmode(mmap.execf(f))
                if node2:
                    nmode = gitmode(mmap2.execf(f))
                else:
                    nmode = gitmode(util.is_exec(repo.wjoin(f), mmap.execf(f)))
                addmodehdr(header, omode, nmode)
                if util.binary(to) or util.binary(tn):
                    dodiff = 'binary'
            r = None
            header.insert(0, 'diff --git a/%s b/%s\n' % (a, b))
        if dodiff == 'binary':
            fp.write(''.join(header))
            b85diff(fp, to, tn)
        elif dodiff:
            text = mdiff.unidiff(to, date1, tn, date2(f), f, r, opts=opts)
            if text or len(header) > 1:
                fp.write(''.join(header))
            fp.write(text)

def export(repo, revs, template='hg-%h.patch', fp=None, switch_parent=False,
           opts=None):
    '''export changesets as hg patches.'''

    total = len(revs)
    revwidth = max(map(len, revs))

    def single(node, seqno, fp):
        parents = [p for p in repo.changelog.parents(node) if p != nullid]
        if switch_parent:
            parents.reverse()
        prev = (parents and parents[0]) or nullid
        change = repo.changelog.read(node)

        if not fp:
            fp = cmdutil.make_file(repo, template, node, total=total,
                                   seqno=seqno, revwidth=revwidth)
        if fp not in (sys.stdout, repo.ui):
            repo.ui.note("%s\n" % fp.name)

        fp.write("# HG changeset patch\n")
        fp.write("# User %s\n" % change[1])
        fp.write("# Date %d %d\n" % change[2])
        fp.write("# Node ID %s\n" % hex(node))
        fp.write("# Parent  %s\n" % hex(prev))
        if len(parents) > 1:
            fp.write("# Parent  %s\n" % hex(parents[1]))
        fp.write(change[4].rstrip())
        fp.write("\n\n")

        diff(repo, prev, node, fp=fp, opts=opts)
        if fp not in (sys.stdout, repo.ui):
            fp.close()

    for seqno, cset in enumerate(revs):
        single(cset, seqno, fp)

def diffstat(patchlines):
    fd, name = tempfile.mkstemp(prefix="hg-patchbomb-", suffix=".txt")
    try:
        p = popen2.Popen3('diffstat -p1 -w79 2>/dev/null > ' + name)
        try:
            for line in patchlines: print >> p.tochild, line
            p.tochild.close()
            if p.wait(): return
            fp = os.fdopen(fd, 'r')
            stat = []
            for line in fp: stat.append(line.lstrip())
            last = stat.pop()
            stat.insert(0, last)
            stat = ''.join(stat)
            if stat.startswith('0 files'): raise ValueError
            return stat
        except: raise
    finally:
        try: os.unlink(name)
        except: pass
