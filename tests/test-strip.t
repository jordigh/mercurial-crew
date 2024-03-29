  $ echo "[extensions]" >> $HGRCPATH
  $ echo "strip=" >> $HGRCPATH
  $ echo "graphlog=" >> $HGRCPATH

  $ restore() {
  >     hg unbundle -q .hg/strip-backup/*
  >     rm .hg/strip-backup/*
  > }
  $ teststrip() {
  >     hg up -C $1
  >     echo % before update $1, strip $2
  >     hg parents
  >     hg --traceback strip $2
  >     echo % after update $1, strip $2
  >     hg parents
  >     restore
  > }

  $ hg init test
  $ cd test

  $ echo foo > bar
  $ hg ci -Ama
  adding bar

  $ echo more >> bar
  $ hg ci -Amb

  $ echo blah >> bar
  $ hg ci -Amc

  $ hg up 1
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ echo blah >> bar
  $ hg ci -Amd
  created new head

  $ echo final >> bar
  $ hg ci -Ame

  $ hg log
  changeset:   4:443431ffac4f
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     e
  
  changeset:   3:65bd5f99a4a3
  parent:      1:ef3a871183d7
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     d
  
  changeset:   2:264128213d29
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     c
  
  changeset:   1:ef3a871183d7
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     b
  
  changeset:   0:9ab35a2d17cb
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     a
  

  $ teststrip 4 4
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved
  % before update 4, strip 4
  changeset:   4:443431ffac4f
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     e
  
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  saved backup bundle to $TESTTMP/test/.hg/strip-backup/*-backup.hg (glob)
  % after update 4, strip 4
  changeset:   3:65bd5f99a4a3
  tag:         tip
  parent:      1:ef3a871183d7
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     d
  
  $ teststrip 4 3
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  % before update 4, strip 3
  changeset:   4:443431ffac4f
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     e
  
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  saved backup bundle to $TESTTMP/test/.hg/strip-backup/*-backup.hg (glob)
  % after update 4, strip 3
  changeset:   1:ef3a871183d7
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     b
  
  $ teststrip 1 4
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved
  % before update 1, strip 4
  changeset:   1:ef3a871183d7
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     b
  
  saved backup bundle to $TESTTMP/test/.hg/strip-backup/*-backup.hg (glob)
  % after update 1, strip 4
  changeset:   1:ef3a871183d7
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     b
  
  $ teststrip 4 2
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  % before update 4, strip 2
  changeset:   4:443431ffac4f
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     e
  
  saved backup bundle to $TESTTMP/test/.hg/strip-backup/*-backup.hg (glob)
  % after update 4, strip 2
  changeset:   3:443431ffac4f
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     e
  
  $ teststrip 4 1
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  % before update 4, strip 1
  changeset:   4:264128213d29
  tag:         tip
  parent:      1:ef3a871183d7
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     c
  
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  saved backup bundle to $TESTTMP/test/.hg/strip-backup/*-backup.hg (glob)
  % after update 4, strip 1
  changeset:   0:9ab35a2d17cb
  tag:         tip
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     a
  
  $ teststrip null 4
  0 files updated, 0 files merged, 1 files removed, 0 files unresolved
  % before update null, strip 4
  saved backup bundle to $TESTTMP/test/.hg/strip-backup/*-backup.hg (glob)
  % after update null, strip 4

  $ hg log
  changeset:   4:264128213d29
  tag:         tip
  parent:      1:ef3a871183d7
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     c
  
  changeset:   3:443431ffac4f
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     e
  
  changeset:   2:65bd5f99a4a3
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     d
  
  changeset:   1:ef3a871183d7
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     b
  
  changeset:   0:9ab35a2d17cb
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     a
  

  $ hg up -C 2
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg merge 4
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved
  (branch merge, don't forget to commit)

before strip of merge parent

  $ hg parents
  changeset:   2:65bd5f99a4a3
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     d
  
  changeset:   4:264128213d29
  tag:         tip
  parent:      1:ef3a871183d7
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     c
  
  $ hg strip 4
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  saved backup bundle to $TESTTMP/test/.hg/strip-backup/*-backup.hg (glob)

after strip of merge parent

  $ hg parents
  changeset:   1:ef3a871183d7
  user:        test
  date:        Thu Jan 01 00:00:00 1970 +0000
  summary:     b
  
  $ restore

  $ hg up
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg glog
  @  changeset:   4:264128213d29
  |  tag:         tip
  |  parent:      1:ef3a871183d7
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     c
  |
  | o  changeset:   3:443431ffac4f
  | |  user:        test
  | |  date:        Thu Jan 01 00:00:00 1970 +0000
  | |  summary:     e
  | |
  | o  changeset:   2:65bd5f99a4a3
  |/   user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     d
  |
  o  changeset:   1:ef3a871183d7
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     b
  |
  o  changeset:   0:9ab35a2d17cb
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     a
  

2 is parent of 3, only one strip should happen

  $ hg strip "roots(2)" 3
  saved backup bundle to $TESTTMP/test/.hg/strip-backup/*-backup.hg (glob)
  $ hg glog
  @  changeset:   2:264128213d29
  |  tag:         tip
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     c
  |
  o  changeset:   1:ef3a871183d7
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     b
  |
  o  changeset:   0:9ab35a2d17cb
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     a
  
  $ restore
  $ hg glog
  o  changeset:   4:443431ffac4f
  |  tag:         tip
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     e
  |
  o  changeset:   3:65bd5f99a4a3
  |  parent:      1:ef3a871183d7
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     d
  |
  | @  changeset:   2:264128213d29
  |/   user:        test
  |    date:        Thu Jan 01 00:00:00 1970 +0000
  |    summary:     c
  |
  o  changeset:   1:ef3a871183d7
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     b
  |
  o  changeset:   0:9ab35a2d17cb
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     a
  

2 different branches: 2 strips

  $ hg strip 2 4
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  saved backup bundle to $TESTTMP/test/.hg/strip-backup/*-backup.hg (glob)
  $ hg glog
  o  changeset:   2:65bd5f99a4a3
  |  tag:         tip
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     d
  |
  @  changeset:   1:ef3a871183d7
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     b
  |
  o  changeset:   0:9ab35a2d17cb
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     a
  
  $ restore

2 different branches and a common ancestor: 1 strip

  $ hg strip 1 "2|4"
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  saved backup bundle to $TESTTMP/test/.hg/strip-backup/*-backup.hg (glob)
  $ restore

stripping an empty revset

  $ hg strip "1 and not 1"
  abort: empty revision set
  [255]

remove branchy history for qimport tests

  $ hg strip 3
  saved backup bundle to $TESTTMP/test/.hg/strip-backup/*-backup.hg (glob)


strip of applied mq should cleanup status file

  $ echo "mq=" >> $HGRCPATH
  $ hg up -C 3
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ echo fooagain >> bar
  $ hg ci -mf
  $ hg qimport -r tip:2

applied patches before strip

  $ hg qapplied
  2.diff
  3.diff
  4.diff

stripping revision in queue

  $ hg strip 3
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  saved backup bundle to $TESTTMP/test/.hg/strip-backup/*-backup.hg (glob)

applied patches after stripping rev in queue

  $ hg qapplied
  2.diff

stripping ancestor of queue

  $ hg strip 1
  1 files updated, 0 files merged, 0 files removed, 0 files unresolved
  saved backup bundle to $TESTTMP/test/.hg/strip-backup/*-backup.hg (glob)

applied patches after stripping ancestor of queue

  $ hg qapplied

Verify strip protects against stripping wc parent when there are uncommited mods

  $ echo b > b
  $ hg add b
  $ hg ci -m 'b'
  $ hg log --graph
  @  changeset:   1:7519abd79d14
  |  tag:         tip
  |  user:        test
  |  date:        Thu Jan 01 00:00:00 1970 +0000
  |  summary:     b
  |
  o  changeset:   0:9ab35a2d17cb
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     a
  

  $ echo c > b
  $ echo c > bar
  $ hg strip tip
  abort: local changes found
  [255]
  $ hg strip tip --keep
  saved backup bundle to $TESTTMP/test/.hg/strip-backup/*-backup.hg (glob)
  $ hg log --graph
  @  changeset:   0:9ab35a2d17cb
     tag:         tip
     user:        test
     date:        Thu Jan 01 00:00:00 1970 +0000
     summary:     a
  
  $ hg status
  M bar
  ? b

Strip adds, removes, modifies with --keep

  $ touch b
  $ hg add b
  $ hg commit -mb
  $ touch c

... with a clean working dir

  $ hg add c
  $ hg rm bar
  $ hg commit -mc
  $ hg status
  $ hg strip --keep tip
  saved backup bundle to $TESTTMP/test/.hg/strip-backup/*-backup.hg (glob)
  $ hg status
  ! bar
  ? c

... with a dirty working dir

  $ hg add c
  $ hg rm bar
  $ hg commit -mc
  $ hg status
  $ echo b > b
  $ echo d > d
  $ hg strip --keep tip
  saved backup bundle to $TESTTMP/test/.hg/strip-backup/*-backup.hg (glob)
  $ hg status
  M b
  ! bar
  ? c
  ? d
  $ cd ..

stripping many nodes on a complex graph (issue3299)

  $ hg init issue3299
  $ cd issue3299
  $ hg debugbuilddag '@a.:a@b.:b.:x<a@a.:a<b@b.:b<a@a.:a'
  $ hg strip 'not ancestors(x)'
  saved backup bundle to $TESTTMP/issue3299/.hg/strip-backup/*-backup.hg (glob)

test hg strip -B bookmark

  $ cd ..
  $ hg init bookmarks
  $ cd bookmarks
  $ hg debugbuilddag '..<2.*1/2:m<2+3:c<m+3:a<2.:b'
  $ hg bookmark -r 'a' 'todelete'
  $ hg bookmark -r 'b' 'B'
  $ hg bookmark -r 'b' 'nostrip'
  $ hg bookmark -r 'c' 'delete'
  $ hg up -C todelete
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved
  $ hg strip -B nostrip
  bookmark 'nostrip' deleted
  abort: empty revision set
  [255]
  $ hg strip -B todelete
  bookmark 'todelete' deleted
  0 files updated, 0 files merged, 0 files removed, 0 files unresolved
  saved backup bundle to $TESTTMP/bookmarks/.hg/strip-backup/*-backup.hg (glob)
  $ hg id -ir dcbb326fdec2
  abort: unknown revision 'dcbb326fdec2'!
  [255]
  $ hg id -ir d62d843c9a01
  d62d843c9a01
  $ hg bookmarks
     B                         9:ff43616e5d0f
     delete                    6:2702dd0c91e7
  $ hg strip -B delete
  bookmark 'delete' deleted
  saved backup bundle to $TESTTMP/bookmarks/.hg/strip-backup/*-backup.hg (glob)
  $ hg id -ir 6:2702dd0c91e7
  abort: unknown revision '2702dd0c91e7'!
  [255]

  $ cd ..
