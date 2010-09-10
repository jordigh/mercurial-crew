  $ mkdir t
  $ cd t
  $ hg init
  $ echo 0 > a
  $ echo 0 > b
  $ echo 0 > t.h
  $ mkdir t
  $ echo 0 > t/x
  $ echo 0 > t/b
  $ echo 0 > t/e.h
  $ mkdir dir.h
  $ echo 0 > dir.h/foo

  $ hg ci -A -m m
  adding a
  adding b
  adding dir.h/foo
  adding t.h
  adding t/b
  adding t/e.h
  adding t/x

  $ touch nottracked

  $ hg locate a && echo locate succeeded || echo locate failed
  a
  locate succeeded

  $ hg locate NONEXISTENT && echo locate succeeded || echo locate failed
  locate failed

  $ hg locate
  a
  b
  dir.h/foo
  t.h
  t/b
  t/e.h
  t/x

  $ hg rm a
  $ hg ci -m m

  $ hg locate a
  $ hg locate NONEXISTENT
  $ hg locate relpath:NONEXISTENT
  $ hg locate
  b
  dir.h/foo
  t.h
  t/b
  t/e.h
  t/x
  $ hg locate -r 0 a
  a
  $ hg locate -r 0 NONEXISTENT
  $ hg locate -r 0 relpath:NONEXISTENT
  $ hg locate -r 0
  a
  b
  dir.h/foo
  t.h
  t/b
  t/e.h
  t/x

-I/-X with relative path should work:

  $ cd t
  $ hg locate
  b
  dir.h/foo
  t.h
  t/b
  t/e.h
  t/x
  $ hg locate -I ../t
  t/b
  t/e.h
  t/x

Test issue294:

  $ cd ..
  $ rm -r t

  $ hg locate 't/**'
  t/b
  t/e.h
  t/x

  $ mkdir otherdir
  $ cd otherdir

  $ hg locate b
  ../b
  ../t/b
  $ hg locate '*.h'
  ../t.h
  ../t/e.h
  $ hg locate path:t/x
  ../t/x
  $ hg locate 're:.*\.h$'
  ../t.h
  ../t/e.h
  $ hg locate -r 0 b
  ../b
  ../t/b
  $ hg locate -r 0 '*.h'
  ../t.h
  ../t/e.h
  $ hg locate -r 0 path:t/x
  ../t/x
  $ hg locate -r 0 're:.*\.h$'
  ../t.h
  ../t/e.h

