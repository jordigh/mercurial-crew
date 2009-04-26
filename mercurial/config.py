from i18n import _
import re, error, os

class sortdict(dict):
    'a simple sorted dictionary'
    def __init__(self, data=None):
        self._list = []
        if data:
            self.update(data)
    def copy(self):
        return sortdict(self)
    def __setitem__(self, key, val):
        if key in self:
            self._list.remove(key)
        self._list.append(key)
        dict.__setitem__(self, key, val)
    def __iter__(self):
        return self._list.__iter__()
    def update(self, src):
        for k in src:
            self[k] = src[k]
    def items(self):
        return [(k,self[k]) for k in self._list]
    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self._list.remove(key)

class config(object):
    def __init__(self, data=None):
        self._data = {}
        self._source = {}
        if data:
            for k in data._data:
                self._data[k] = data[k].copy()
            self._source = data._source.copy()
    def copy(self):
        return config(self)
    def __contains__(self, section):
        return section in self._data
    def __getitem__(self, section):
        return self._data.get(section, {})
    def __iter__(self):
        for d in self.sections():
            yield d
    def update(self, src, sections=None):
        if not sections:
            sections = src.sections()
        for s in sections:
            if s not in src:
                continue
            if s not in self:
                self._data[s] = sortdict()
            for k in src._data[s]:
                self._data[s][k] = src._data[s][k]
                self._source[(s, k)] = src._source[(s, k)]
    def get(self, section, item, default=None):
        return self._data.get(section, {}).get(item, default)
    def getsource(self, section, item):
        return self._source.get((section, item), "")
    def sections(self):
        return sorted(self._data.keys())
    def items(self, section):
        return self._data.get(section, {}).items()
    def set(self, section, item, value, source=""):
        if section not in self:
            self._data[section] = sortdict()
        self._data[section][item] = value
        self._source[(section, item)] = source

    def read(self, path, fp=None):
        sectionre = re.compile(r'\[([^\[]+)\]')
        itemre = re.compile(r'([^=\s]+)\s*=\s*(.*\S|)')
        contre = re.compile(r'\s+(\S.*\S)')
        emptyre = re.compile(r'(;|#|\s*$)')
        unsetre = re.compile(r'%unset\s+(\S+)')
        includere = re.compile(r'%include\s+(\S.*\S)')
        section = ""
        item = None
        line = 0
        cont = 0

        if not fp:
            fp = open(path)

        for l in fp:
            line += 1
            if cont:
                m = contre.match(l)
                if m:
                    v = self.get(section, item) + "\n" + m.group(1)
                    self.set(section, item, v, "%s:%d" % (path, line))
                    continue
                item = None
            m = includere.match(l)
            if m:
                inc = m.group(1)
                base = os.path.dirname(path)
                inc = os.path.normpath(os.path.join(base, inc))
                incfp = open(inc)
                self.read(inc, incfp)
                continue
            if emptyre.match(l):
                continue
            m = sectionre.match(l)
            if m:
                section = m.group(1)
                if section not in self:
                    self._data[section] = sortdict()
                continue
            m = itemre.match(l)
            if m:
                item = m.group(1)
                self.set(section, item, m.group(2), "%s:%d" % (path, line))
                cont = 1
                continue
            m = unsetre.match(l)
            if m:
                name = m.group(1)
                if self.get(section, name) != None:
                    del self._data[section][name]
                continue

            raise error.ConfigError(_('config error at %s:%d: \'%s\'')
                                    % (path, line, l.rstrip()))
