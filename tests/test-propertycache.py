"""test behavior of propertycache and unfiltered propertycache

The repoview overlay is quite complexe. We test the behavior of
property cache of both localrepo and repoview to prevent
regression."""

import os, subprocess
import mercurial.localrepo
import mercurial.repoview
import mercurial.util
import mercurial.hg
import mercurial.ui as uimod


# create some special property cache that trace they call

calllog = []
@mercurial.util.propertycache
def testcachedfoobar(repo):
    name = repo.filtername
    if name is None:
        name = ''
    val = len(name)
    calllog.append(val)
    return val

unficalllog = []
@mercurial.localrepo.unfilteredpropertycache
def testcachedunfifoobar(repo):
    name = repo.filtername
    if name is None:
        name = ''
    val = 100 + len(name)
    unficalllog.append(val)
    return val

#plug them on repo
mercurial.localrepo.localrepository.testcachedfoobar = testcachedfoobar
mercurial.localrepo.localrepository.testcachedunfifoobar = testcachedunfifoobar


# create an empty repo. and instanciate it. It is important to run
# those test on the real object to detect regression.
repopath = os.path.join(os.environ['TESTTMP'], 'repo')
assert subprocess.call(['hg', 'init', repopath]) == 0
ui = uimod.ui()
repo = mercurial.hg.repository(ui, path=repopath).unfiltered()


print ''
print '=== property cache ==='
print ''
print 'calllog:', calllog
print 'cached value (unfiltered):',
print vars(repo).get('testcachedfoobar', 'NOCACHE')

print ''
print '= first access on unfiltered, should do a call'
print 'access:', repo.testcachedfoobar
print 'calllog:', calllog
print 'cached value (unfiltered):',
print vars(repo).get('testcachedfoobar', 'NOCACHE')

print ''
print '= second access on unfiltered, should not do call'
print 'access', repo.testcachedfoobar
print 'calllog:', calllog
print 'cached value (unfiltered):',
print vars(repo).get('testcachedfoobar', 'NOCACHE')

print ''
print '= first access on "visible" view, should do a call'
visibleview = repo.filtered('visible')
print 'cached value ("visible" view):',
print vars(visibleview).get('testcachedfoobar', 'NOCACHE')
print 'access:', visibleview.testcachedfoobar
print 'calllog:', calllog
print 'cached value (unfiltered):',
print vars(repo).get('testcachedfoobar', 'NOCACHE')
print 'cached value ("visible" view):',
print vars(visibleview).get('testcachedfoobar', 'NOCACHE')

print ''
print '= second access on "visible view", should not do call'
print 'access:', visibleview.testcachedfoobar
print 'calllog:', calllog
print 'cached value (unfiltered):',
print vars(repo).get('testcachedfoobar', 'NOCACHE')
print 'cached value ("visible" view):',
print vars(visibleview).get('testcachedfoobar', 'NOCACHE')

print ''
print '= no effect on other view'
immutableview = repo.filtered('immutable')
print 'cached value ("immutable" view):',
print vars(immutableview).get('testcachedfoobar', 'NOCACHE')
print 'access:', immutableview.testcachedfoobar
print 'calllog:', calllog
print 'cached value (unfiltered):',
print vars(repo).get('testcachedfoobar', 'NOCACHE')
print 'cached value ("visible" view):',
print vars(visibleview).get('testcachedfoobar', 'NOCACHE')
print 'cached value ("immutable" view):',
print vars(immutableview).get('testcachedfoobar', 'NOCACHE')

# unfiltered property cache test
print ''
print ''
print '=== unfiltered property cache ==='
print ''
print 'unficalllog:', unficalllog
print 'cached value (unfiltered):      ',
print vars(repo).get('testcachedunfifoobar', 'NOCACHE')
print 'cached value ("visible" view):  ',
print vars(visibleview).get('testcachedunfifoobar', 'NOCACHE')
print 'cached value ("immutable" view):',
print vars(immutableview).get('testcachedunfifoobar', 'NOCACHE')

print ''
print '= first access on unfiltered, should do a call'
print 'access (unfiltered):', repo.testcachedunfifoobar
print 'unficalllog:', unficalllog
print 'cached value (unfiltered):      ',
print vars(repo).get('testcachedunfifoobar', 'NOCACHE')

print ''
print '= second access on unfiltered, should not do call'
print 'access (unfiltered):', repo.testcachedunfifoobar
print 'unficalllog:', unficalllog
print 'cached value (unfiltered):      ',
print vars(repo).get('testcachedunfifoobar', 'NOCACHE')

print ''
print '= access on view should use the unfiltered cache'
print 'access (unfiltered):      ', repo.testcachedunfifoobar
print 'access ("visible" view):  ', visibleview.testcachedunfifoobar
print 'access ("immutable" view):', immutableview.testcachedunfifoobar
print 'unficalllog:', unficalllog
print 'cached value (unfiltered):      ',
print vars(repo).get('testcachedunfifoobar', 'NOCACHE')
print 'cached value ("visible" view):  ',
print vars(visibleview).get('testcachedunfifoobar', 'NOCACHE')
print 'cached value ("immutable" view):',
print vars(immutableview).get('testcachedunfifoobar', 'NOCACHE')

print ''
print '= even if we clear the unfiltered cache'
del repo.__dict__['testcachedunfifoobar']
print 'cached value (unfiltered):      ',
print vars(repo).get('testcachedunfifoobar', 'NOCACHE')
print 'cached value ("visible" view):  ',
print vars(visibleview).get('testcachedunfifoobar', 'NOCACHE')
print 'cached value ("immutable" view):',
print vars(immutableview).get('testcachedunfifoobar', 'NOCACHE')
print 'unficalllog:', unficalllog
print 'access ("visible" view):  ', visibleview.testcachedunfifoobar
print 'unficalllog:', unficalllog
print 'cached value (unfiltered):      ',
print vars(repo).get('testcachedunfifoobar', 'NOCACHE')
print 'cached value ("visible" view):  ',
print vars(visibleview).get('testcachedunfifoobar', 'NOCACHE')
print 'cached value ("immutable" view):',
print vars(immutableview).get('testcachedunfifoobar', 'NOCACHE')
print 'access ("immutable" view):', immutableview.testcachedunfifoobar
print 'unficalllog:', unficalllog
print 'cached value (unfiltered):      ',
print vars(repo).get('testcachedunfifoobar', 'NOCACHE')
print 'cached value ("visible" view):  ',
print vars(visibleview).get('testcachedunfifoobar', 'NOCACHE')
print 'cached value ("immutable" view):',
print vars(immutableview).get('testcachedunfifoobar', 'NOCACHE')
print 'access (unfiltered):      ', repo.testcachedunfifoobar
print 'unficalllog:', unficalllog
print 'cached value (unfiltered):      ',
print vars(repo).get('testcachedunfifoobar', 'NOCACHE')
print 'cached value ("visible" view):  ',
print vars(visibleview).get('testcachedunfifoobar', 'NOCACHE')
print 'cached value ("immutable" view):',
print vars(immutableview).get('testcachedunfifoobar', 'NOCACHE')
