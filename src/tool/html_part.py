# ---------------------------------------------------------------------------
# Small helpers shared by everything below.
# ---------------------------------------------------------------------------
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def trim(s):
    """JavaScript's String.prototype.trim (its whitespace set differs from Python's)."""
    return s.strip(_JSWS)


def fmt_size(n):
    M = 1048576
    if n >= M:
        if n >= 10 * M:
            q = (n * 20 + M) // (2 * M)
            return "%d.%d MB" % (q // 10, q % 10)
        q = (n * 200 + M) // (2 * M)
        return "%d.%02d MB" % (q // 100, q % 100)
    if n >= 1024:
        return "%d KB" % ((2 * n + 1024) // 2048)
    return "%d bytes" % n


def clean_type(t):
    t = trim(t or "").lower()
    return t if re.fullmatch(r"[A-Za-z0-9_.+-]+/[A-Za-z0-9_.+-]+", t) else "application/octet-stream"


def safe_href(u):
    u = trim(u or "")
    if not u:
        return ""
    if re.match(r"(https?:|mailto:)", u, re.I | re.A) or u[0] == "#":
        return u
    if re.match(r"[a-z][a-z0-9+.-]*:", u, re.I | re.A):
        return ""
    return "https://" + u


# ---------------------------------------------------------------------------
# HTML fragment parsing for text blocks. This follows the browser's rules for the
# constructs that appear in rich text (paragraphs, lists, bold, italic, links, line
# breaks, stray block tags, unclosed tags). It does not model tables or forms.
# ---------------------------------------------------------------------------
from html.parser import HTMLParser

_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr", "keygen", "basefont", "bgsound", "frame"}
_SPECIAL = set("address applet area article aside base basefont bgsound blockquote body br button caption center col colgroup dd details dir div dl dt embed fieldset figcaption figure footer form frame frameset h1 h2 h3 h4 h5 h6 head header hgroup hr html iframe img input keygen li link listing main marquee menu meta nav noembed noframes noscript object ol p param plaintext pre script search section select source style summary table tbody td template textarea tfoot th thead title tr track ul wbr xmp".split())
_CLOSE_P = set("address article aside blockquote center details dialog dir div dl fieldset figcaption figure footer form header hgroup hr li listing main menu nav ol p pre search section summary table ul xmp h1 h2 h3 h4 h5 h6 dd dt".split())
_FORMAT = {"a", "b", "big", "code", "em", "font", "i", "nobr", "s", "small", "strike", "strong", "tt", "u"}
_SCOPE = {"applet", "caption", "html", "table", "td", "th", "marquee", "object", "template"}
_RAWSKIP = {"script", "style"}


class _Node(object):
    __slots__ = ("tag", "attrs", "kids", "parent")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = attrs or {}
        self.kids = []
        self.parent = parent


_MARKERS = {"applet", "object", "marquee", "td", "th", "caption", "template"}
_RECONSTRUCT_VOID = {"br", "img", "input", "embed", "wbr", "area", "keygen"}
_BLOCK_END = {"div", "ul", "ol", "blockquote", "pre", "section", "article", "nav", "header", "footer", "main", "aside", "address", "center", "details", "dl", "fieldset", "figure", "figcaption",
              "form", "menu", "search", "summary", "hgroup", "listing", "dialog", "dir", "button"}
_HEADS = ("h1", "h2", "h3", "h4", "h5", "h6")


def _detach(n):
    if n.parent is not None:
        for i, k in enumerate(n.parent.kids):
            if k is n:
                del n.parent.kids[i]
                break
        n.parent = None


def _attach(parent, n):
    _detach(n)
    n.parent = parent
    parent.kids.append(n)


class _Builder(HTMLParser):
    """HTML5 tree construction, for the parts that matter in rich text (including the
    adoption agency algorithm that browsers use for mis-nested bold, italic and links)."""

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.root = _Node("body")
        self.stack = [self.root]
        self.active = []  # _Node or None (marker)

    def _cur(self):
        return self.stack[-1]

    def _is_special(self, n):
        return n.tag in _SPECIAL

    def _in_scope(self, tag, extra=()):
        for n in reversed(self.stack):
            if n.tag == tag:
                return True
            if n.tag in _SCOPE or n.tag in extra:
                return False
        return False

    def _node_in_scope(self, node):
        for n in reversed(self.stack):
            if n is node:
                return True
            if n.tag in _SCOPE:
                return False
        return False

    def _clear_to_marker(self):
        while self.active:
            if self.active.pop() is None:
                break

    def _pop(self):
        n = self.stack.pop()
        if n.tag in _MARKERS:
            self._clear_to_marker()
        return n

    def _pop_through(self, node):
        while self.stack:
            if self._pop() is node:
                break

    def _pop_through_tag(self, tags):
        while self.stack:
            if self._pop().tag in tags:
                break

    def _close_p(self):
        if self._in_scope("p", ("button",)):
            while self._cur().tag in ("dd", "dt", "li", "optgroup", "option", "p", "rb", "rp", "rt", "rtc") and self._cur().tag != "p":
                self._pop()
            self._pop_through_tag(("p",))

    def _push_active(self, n):
        same = []
        for x in reversed(self.active):
            if x is None:
                break
            if x.tag == n.tag and x.attrs == n.attrs:
                same.append(x)
        if len(same) >= 3:
            self.active.remove(same[-1])
        self.active.append(n)

    def _reconstruct(self):
        if not self.active:
            return
        last = self.active[-1]
        if last is None or last in self.stack:
            return
        k = len(self.active) - 1
        while True:
            if k == 0:
                break
            k -= 1
            e = self.active[k]
            if e is None or e in self.stack:
                k += 1
                break
        while k < len(self.active):
            old = self.active[k]
            new = _Node(old.tag, dict(old.attrs))
            _attach(self._cur(), new)
            self.stack.append(new)
            self.active[k] = new
            k += 1

    def _insert(self, tag, attrs):
        n = _Node(tag, attrs)
        _attach(self._cur(), n)
        return n

    def _adoption(self, subject):
        """Returns True if handled, False if the caller should treat it as an ordinary end tag."""
        cur = self._cur()
        if cur.tag == subject and cur not in self.active:
            self._pop()
            return True
        for _ in range(8):
            fe = None
            for x in reversed(self.active):
                if x is None:
                    break
                if x.tag == subject:
                    fe = x
                    break
            if fe is None:
                return False
            if fe not in self.stack:
                self.active.remove(fe)
                return True
            if not self._node_in_scope(fe):
                return True
            fi = self.stack.index(fe)
            fb = None
            for n in self.stack[fi + 1:]:
                if self._is_special(n):
                    fb = n
                    break
            if fb is None:
                while self.stack:
                    if self._pop() is fe:
                        break
                if fe in self.active:
                    self.active.remove(fe)
                return True
            common = self.stack[fi - 1]
            bookmark = self.active.index(fe)
            node = last = fb
            inner = 0
            ni = self.stack.index(node)
            while True:
                inner += 1
                ni -= 1
                node = self.stack[ni]
                if node is fe:
                    break
                if inner > 3 and node in self.active:
                    self.active.remove(node)
                    if self.active.index(fe) < bookmark:
                        bookmark -= 0
                if node not in self.active:
                    self.stack.remove(node)
                    continue
                new = _Node(node.tag, dict(node.attrs))
                self.active[self.active.index(node)] = new
                self.stack[self.stack.index(node)] = new
                node = new
                if last is fb:
                    bookmark = self.active.index(node) + 1
                _attach(node, last)
                last = node
            _attach(common, last)
            new = _Node(fe.tag, dict(fe.attrs))
            for kid in list(fb.kids):
                if isinstance(kid, str):
                    new.kids.append(kid)
                else:
                    _attach(new, kid)
            fb.kids = [k for k in fb.kids if not isinstance(k, str)]
            _attach(fb, new)
            bi = min(bookmark, len(self.active))
            if fe in self.active:
                ei = self.active.index(fe)
                self.active.remove(fe)
                if ei < bi:
                    bi -= 1
            self.active.insert(bi, new)
            self.stack.remove(fe)
            self.stack.insert(self.stack.index(fb) + 1, new)
        return True

    def handle_starttag(self, tag, attrs):
        a = {}
        for k, v in attrs:
            if k not in a:
                a[k] = "" if v is None else v
        if tag in _CLOSE_P:
            self._close_p()
        if tag == "li":
            for n in reversed(self.stack):
                if n.tag == "li":
                    while self._cur().tag != "li":
                        self._pop()
                    self._pop()
                    break
                if n.tag in _SPECIAL and n.tag not in ("address", "div", "p"):
                    break
        elif tag in ("dd", "dt"):
            for n in reversed(self.stack):
                if n.tag in ("dd", "dt"):
                    while self._cur() is not n:
                        self._pop()
                    self._pop()
                    break
                if n.tag in _SPECIAL and n.tag not in ("address", "div", "p"):
                    break
        if tag in _HEADS and self._cur().tag in _HEADS:
            self._pop()
        if tag == "a":
            for x in reversed(self.active):
                if x is None:
                    break
                if x.tag == "a":
                    self._adoption("a")
                    if x in self.active:
                        self.active.remove(x)
                    if x in self.stack:
                        self.stack.remove(x)
                    break
        if tag == "nobr":
            self._reconstruct()
            if self._in_scope("nobr"):
                self._adoption("nobr")
                self._reconstruct()
        elif tag in _FORMAT or tag not in _SPECIAL or tag in _RECONSTRUCT_VOID:
            self._reconstruct()
        n = self._insert(tag, a)
        if tag in _VOID:
            return
        self.stack.append(n)
        if tag in _FORMAT:
            self._push_active(n)
        if tag in _MARKERS:
            self.active.append(None)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == "br":
            self.handle_starttag("br", [])
            return
        if tag == "p":
            if not self._in_scope("p", ("button",)):
                self._insert("p", {})
                return
            self._close_p()
            return
        if tag == "li":
            if self._in_scope("li", ("ol", "ul", "button")):
                while self._cur().tag != "li":
                    self._pop()
                self._pop()
            return
        if tag in ("dd", "dt"):
            if self._in_scope(tag, ("button",)):
                while self._cur().tag != tag:
                    self._pop()
                self._pop()
            return
        if tag in _FORMAT:
            if not self._adoption(tag):
                self._any_other(tag)
            return
        if tag in _BLOCK_END:
            if self._in_scope(tag, ("button",)):
                while self._cur().tag != tag:
                    self._pop()
                self._pop()
            return
        if tag in _HEADS:
            for n in reversed(self.stack):
                if n.tag in _HEADS:
                    while self._cur() is not n:
                        self._pop()
                    self._pop()
                    break
                if n.tag in _SCOPE:
                    break
            return
        self._any_other(tag)

    def _any_other(self, tag):
        for n in reversed(self.stack):
            if n.tag == tag:
                while self._cur() is not n:
                    self._pop()
                self._pop()
                return
            if n.tag in _SPECIAL:
                return

    def handle_data(self, data):
        if not data:
            return
        self._reconstruct()
        k = self._cur().kids
        if k and isinstance(k[-1], str):
            k[-1] += data
        else:
            k.append(data)


def parse_fragment(html):
    b = _Builder()
    b.feed("" if html is None else html)
    b.close()
    return b.root


def _clean_node(node):
    out = []
    for n in node.kids:
        if isinstance(n, str):
            out.append(esc(n))
            continue
        tg = n.tag
        if tg in ("script", "style", "template"):
            continue
        t = {"p": "p", "div": "p", "br": "br", "strong": "strong", "b": "strong", "em": "em", "i": "em", "a": "a", "ul": "ul", "ol": "ol", "li": "li"}.get(tg)
        inner = _clean_node(n)
        if not t:
            out.append(inner)
        elif t == "br":
            out.append("<br>")
        elif t == "a":
            hr = safe_href(n.attrs.get("href"))
            if hr:
                out.append('<a href="' + esc(hr) + '"' + ("" if hr[0] == "#" else ' target="_blank" rel="noopener noreferrer"') + ">" + inner + "</a>")
            else:
                out.append(inner)
        elif t == "p" and not trim(inner.replace("<br>", "")):
            out.append("")
        else:
            out.append("<" + t + ">" + inner + "</" + t + ">")
    return "".join(out)


def sanitize(html):
    """Reduce rich text to paragraphs, line breaks, bold, italic, links and lists."""
    return _clean_node(parse_fragment(html))
