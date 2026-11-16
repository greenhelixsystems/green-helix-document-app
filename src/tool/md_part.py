# ---------------------------------------------------------------------------
# Markdown subset converter. A line-for-line port of the editor's mdRender, so
# a Markdown block renders identically whether the editor or this script made it.
# Strings are processed as UTF-16 code units (like JavaScript) so that length
# limits and character tests agree exactly, including for emoji.
# ---------------------------------------------------------------------------
MD_SPAN = 5000
MD_ESC = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
_JSWS = "\t\n\x0b\x0c\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
_NOTNL = "[^\\n\\r\\u2028\\u2029]"
_RE = re.ASCII
MD_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,}) *([^`]*)\Z", _RE)
MD_HEAD = re.compile(r"^ {0,3}(#{1,6})(?: +(" + _NOTNL + r"*?))?(?: +#+)? *\Z", _RE)
MD_HR = re.compile(r"^ {0,3}([-*_])(?: *\1){2,} *\Z", _RE)
MD_ITEM = re.compile(r"^( *)([-*+]|[0-9]{1,9}[.)])(?: +(" + _NOTNL + r"*))?\Z", _RE)
MD_QUOTE = re.compile(r"^ {0,3}> ?(" + _NOTNL + r"*)\Z", _RE)
MD_TDELIM = re.compile(r"^ *\|? *:?-+:? *(?:\| *:?-+:? *)*\|? *\Z", _RE)
MD_TASK = re.compile(r"^\[([ xX])\](?: +(" + _NOTNL + r"*))?\Z", _RE)
_ALNUM = re.compile(r"[A-Za-z0-9]")


def _u16(s):
    """Python text to a string of UTF-16 code units (astral characters become two surrogates)."""
    if all(ord(c) < 0x10000 for c in s):
        return s
    return "".join(c if ord(c) < 0x10000 else chr(0xD800 + ((ord(c) - 0x10000) >> 10)) + chr(0xDC00 + ((ord(c) - 0x10000) & 0x3FF)) for c in s)


def _from_u16(s):
    if not any(0xD800 <= ord(c) <= 0xDFFF for c in s):
        return s
    return s.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


def _at(s, i):
    return s[i] if 0 <= i < len(s) else ""


def _trim(s):
    return s.strip(_JSWS)


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _alnum(c):
    return c != "" and _ALNUM.fullmatch(c) is not None


def _space(c):
    return c == "" or c == " " or c == "\n"


def _indent(l):
    k = 0
    while _at(l, k) == " ":
        k += 1
    return k


def _all(t, ch):
    return all(c == ch for c in t)


def _ticks(s, i):
    k = 0
    while _at(s, i + k) == "`":
        k += 1
    return k


def _code_end(s, i, k):
    j = i
    n = min(len(s), i + MD_SPAN)
    while j < n:
        if s[j] == "`":
            r = _ticks(s, j)
            if r == k:
                return j
            j += r
        else:
            j += 1
    return -1


def _close(s, frm, d):
    j = frm
    n = min(len(s), frm + MD_SPAN)
    L = len(d)
    c0 = d[0]
    while j < n:
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "`":
            k = _ticks(s, j)
            e = _code_end(s, j + k, k)
            j = j + k if e < 0 else e + k
            continue
        if c == c0:
            if L == 1 and _at(s, j + 1) == c0:
                e = -1 if _space(_at(s, j + 2)) else _close(s, j + 2, d + d)
                j = j + 2 if e < 0 else e + 2
                continue
            if L == 2 and _at(s, j + 1) != c0:
                j += 1
                continue
            if j > frm and not _space(_at(s, j - 1)):
                if L == 2:
                    while _at(s, j + 2) == c0:
                        j += 1
                if c0 != "_" or not _alnum(_at(s, j + L)):
                    return j
            j += L
            continue
        j += 1
    return -1


def _bracket(s, i):
    j = i + 1
    n = min(len(s), i + MD_SPAN)
    d = 1
    while j < n:
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "`":
            k = _ticks(s, j)
            e = _code_end(s, j + k, k)
            j = j + k if e < 0 else e + k
            continue
        if c == "[":
            d += 1
        elif c == "]":
            d -= 1
            if d == 0:
                break
        j += 1
    if j >= n or _at(s, j + 1) != "(":
        return None
    text = s[i + 1:j]
    p = j + 2
    depth = 1
    url = ""
    while p < n:
        c = s[p]
        if c == "\n":
            return None
        if c == "\\" and p + 1 < n:
            url += s[p + 1]
            p += 2
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                break
        url += c
        p += 1
    if p >= n:
        return None
    url = _trim(url)
    k = url.find(" ")
    if k >= 0:
        url = url[:k]
    if url[:1] == "<" and url[-1:] == ">":
        url = url[1:-1]
    return {"text": text, "url": url, "end": p + 1}


def _href(u):
    u = _trim(u)
    if not u:
        return ""
    if re.match(r"(https?:|mailto:)", u, re.I | re.A) or u[0] == "#":
        return u
    if re.match(r"[a-z][a-z0-9+.-]*:", u, re.I | re.A) or u[0] == "/" or u[0] == ".":
        return ""
    return "https://" + u


def _link(hr, inner):
    return '<a href="' + _esc(hr) + '"' + ("" if hr[0] == "#" else ' target="_blank" rel="noopener noreferrer"') + ">" + inner + "</a>"


_AUTOLINK = re.compile(r"<((?:https?://|mailto:)[^" + re.escape(_JSWS) + r"<>]+)>", re.I | re.A)
_BAREURL = re.compile(r"https?://[^" + re.escape(_JSWS) + r"<>]+", re.I | re.A)


def _inline(s, depth):
    if depth > 12:
        return _esc(s).replace("\n", "<br>")
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n and s[i + 1] in MD_ESC:
            out.append(_esc(s[i + 1]))
            i += 2
            continue
        if c == "`":
            k = _ticks(s, i)
            j = _code_end(s, i + k, k)
            if j < 0:
                out.append(s[i:i + k])
                i += k
                continue
            t = s[i + k:j].replace("\n", " ")
            if len(t) > 2 and t[0] == " " and t[-1] == " ":
                t = t[1:-1]
            out.append("<code>" + _esc(t) + "</code>")
            i = j + k
            continue
        if c == "[" or (c == "!" and _at(s, i + 1) == "["):
            m = _bracket(s, i + 1 if c == "!" else i)
            if m:
                hr = _href(m["url"])
                t = _esc(_trim(m["text"]) or m["url"]) if c == "!" else _inline(m["text"], depth + 1)
                out.append(_link(hr, t) if hr else t)
                i = m["end"]
                continue
            out.append(_esc(c))
            i += 1
            continue
        if c == "<":
            m = _AUTOLINK.match(s[i:i + 2100])
            if m:
                out.append(_link(m.group(1), _esc(re.sub(r"^mailto:", "", m.group(1), flags=re.I | re.A))))
                i += len(m.group(0))
                continue
            out.append("&lt;")
            i += 1
            continue
        if (c == "h" or c == "H") and not _alnum(_at(s, i - 1)):
            m = _BAREURL.match(s[i:i + 2100])
            if m:
                t = m.group(0)
                while len(t) > 8:
                    k = t[-1]
                    if k in ".,;:!?'\"*_~" or (k == ")" and "(" not in t):
                        t = t[:-1]
                    else:
                        break
                out.append(_link(t, _esc(t)))
                i += len(t)
                continue
        if c == "*" or c == "_" or c == "~":
            two = _at(s, i + 1) == c
            if c == "~" and not two:
                out.append(c)
                i += 1
                continue
            if not (c == "_" and _alnum(_at(s, i - 1))):
                k = 2 if two else 1
                if not _space(_at(s, i + k)):
                    j = _close(s, i + k, c + c if two else c)
                    if j >= 0:
                        t = "del" if c == "~" else ("strong" if two else "em")
                        out.append("<" + t + ">" + _inline(s[i + k:j], depth + 1) + "</" + t + ">")
                        i = j + k
                        continue
            out.append(c * 2 if two else c)
            i += 2 if two else 1
            continue
        if c == "\n":
            out.append("<br>")
            i += 1
            continue
        out.append(_esc(c))
        i += 1
    return "".join(out)


def _row(line):
    s = _trim(line)
    cells = []
    cell = []
    if s[:1] == "|":
        s = s[1:]
    if s[-1:] == "|" and _at(s, len(s) - 2) != "\\":
        s = s[:-1]
    i = 0
    while i < len(s):
        c = s[i]
        if c == "\\" and _at(s, i + 1) == "|":
            cell.append("|")
            i += 1
        elif c == "|":
            cells.append(_trim("".join(cell)))
            cell = []
        else:
            cell.append(c)
        i += 1
    cells.append(_trim("".join(cell)))
    return cells


def _start(lines, i, in_para):
    l = lines[i]
    if MD_FENCE.match(l):
        return "fence"
    if MD_HEAD.match(l):
        return "head"
    if MD_HR.match(l):
        return "hr"
    if MD_QUOTE.match(l):
        return "quote"
    m = MD_ITEM.match(l)
    if m:
        if not in_para:
            return "item"
        if m.group(3) and _trim(m.group(3)) and (not re.search(r"[0-9]", m.group(2)) or m.group(2)[:-1] == "1"):
            return "item"
    if "|" in l and i + 1 < len(lines) and "-" in lines[i + 1] and MD_TDELIM.match(lines[i + 1]) and len(_row(l)) == len(_row(lines[i + 1])):
        return "table"
    return ""


def _join(bl, wrap):
    return "".join("<p>" + x["h"] + "</p>" if x.get("p") and wrap else x["h"] for x in bl)


_NUM = re.compile(r"[-+]?([0-9]+\.?[0-9]*|\.[0-9]+)%?", re.A)


def _is_num(s):
    s = _trim(s)
    s = re.sub(r"^[-+]?\$", "", s).replace(",", "")
    return s != "" and _NUM.fullmatch(s) is not None


def _table(lines, i):
    n = len(lines)
    head = _row(lines[i])
    rows = []
    al = []
    for c in _row(lines[i + 1]):
        L = c[:1] == ":"
        R = c[-1:] == ":"
        al.append(("ctr" if L else "num") if R else ("left" if L else ""))
    i += 2
    while i < n and _trim(lines[i]) and "|" in lines[i]:
        rows.append(_row(lines[i]))
        i += 1
    fixed = []
    for k, a in enumerate(al):
        if a:
            fixed.append("" if a == "left" else a)
            continue
        any_ = False
        all_ = True
        for r in rows:
            v = _trim((r[k] if k < len(r) else "").replace("**", ""))
            if v:
                any_ = True
                if not _is_num(v):
                    all_ = False
        fixed.append("num" if any_ and all_ else "")
    al = fixed

    def cell(tag, v, k, extra):
        a = al[k] if k < len(al) else ""
        return "<" + tag + (' class="' + a + '"' if a else "") + extra + ">" + _inline(v, 0) + "</" + tag + ">"
    h = ('<div class="scroll"><table><thead><tr>' + "".join(cell("th", v, k, ' scope="col"') for k, v in enumerate(head)) + "</tr></thead>"
         + ("<tbody>" + "".join("<tr>" + "".join(cell("td", r[k] if k < len(r) else "", k, "") for k in range(len(head))) + "</tr>" for r in rows) + "</tbody>" if rows else "")
         + "</table></div>")
    return i, h


def _list(lines, i, depth):
    n = len(lines)
    m = MD_ITEM.match(lines[i])
    base = len(m.group(1))
    ord_ = re.search(r"[0-9]", m.group(2)) is not None
    start = int(re.match(r"[0-9]+", m.group(2)).group(0)) if ord_ else 1
    items = []

    def sibling(k):
        x = MD_ITEM.match(lines[k]) if k < n else None
        return bool(x) and len(x.group(1)) <= base + 1 and (re.search(r"[0-9]", x.group(2)) is not None) == ord_ and not MD_HR.match(lines[k])
    while i < n and sibling(i):
        m = MD_ITEM.match(lines[i])
        w = len(m.group(1)) + len(m.group(2)) + 1
        buf = [m.group(3) or ""]
        i += 1
        while i < n:
            if not _trim(lines[i]):
                j = i
                while j < n and not _trim(lines[j]):
                    j += 1
                if j < n and _indent(lines[j]) >= base + 2:
                    while i < j:
                        buf.append("")
                        i += 1
                    continue
                break
            ind = _indent(lines[i])
            if ind < base + 2:
                break
            buf.append(lines[i][min(ind, w):])
            i += 1
        items.append(buf)
        j = i
        while j < n and not _trim(lines[j]):
            j += 1
        if j > i:
            if sibling(j):
                i = j
            else:
                break
    tasks = (not ord_) and all(MD_TASK.match(b[0]) for b in items)
    parts = []
    for b in items:
        done = False
        if tasks:
            tm = MD_TASK.match(b[0])
            done = tm.group(1) != " "
            b = [tm.group(2) or ""] + b[1:]
        bl = _blocks(b, depth + 1)
        pc = len([x for x in bl if x.get("p")])
        parts.append("<li" + (' class="done"><span class="vh">Done: </span>' if done else ">") + _join(bl, pc > 1) + "</li>")
    html = "".join(parts)
    head = ("<ol" + (' start="%d"' % start if start != 1 else "") + ">") if ord_ else ("<ul" + (' class="checks"' if tasks else "") + ">")
    return i, head + html + ("</ol>" if ord_ else "</ul>")


def _blocks(lines, depth):
    out = []
    i = 0
    n = len(lines)
    while i < n:
        l = lines[i]
        if not _trim(l):
            i += 1
            continue
        k = "" if depth > 8 else _start(lines, i, False)
        if k == "fence":
            m = MD_FENCE.match(l)
            ch = m.group(1)[0]
            ln = len(m.group(1))
            lang = (_trim(m.group(2)).split(" ") or [""])[0]
            buf = []
            i += 1
            while i < n:
                t = _trim(lines[i])
                if len(t) >= ln and _all(t, ch):
                    i += 1
                    break
                buf.append(lines[i])
                i += 1
            out.append({"h": "<pre" + (' data-lang="' + lang + '"' if re.fullmatch(r"[A-Za-z0-9_+#.-]{1,24}", lang) else "") + "><code>" + _esc("\n".join(buf)) + "</code></pre>"})
            continue
        if k == "head":
            m = MD_HEAD.match(l)
            t = min(6, len(m.group(1)) + 2)
            out.append({"h": "<h%d>" % t + _inline(_trim(m.group(2) or ""), 0) + "</h%d>" % t})
            i += 1
            continue
        if k == "hr":
            out.append({"h": "<hr>"})
            i += 1
            continue
        if k == "quote":
            buf = []
            while i < n:
                m = MD_QUOTE.match(lines[i])
                if not m:
                    break
                buf.append(m.group(1))
                i += 1
            out.append({"h": "<blockquote>" + _join(_blocks(buf, depth + 1), True) + "</blockquote>"})
            continue
        if k == "item":
            i, h = _list(lines, i, depth)
            out.append({"h": h})
            continue
        if k == "table":
            i, h = _table(lines, i)
            out.append({"h": h})
            continue
        buf = []
        while i < n and _trim(lines[i]) and (not buf or depth > 8 or not _start(lines, i, True)):
            t = _trim(lines[i])
            if t[-1:] == "\\":
                t = t[:-1]
            buf.append(t)
            i += 1
        out.append({"p": True, "h": _inline("\n".join(buf), 0)})
    return out


def md_render(src):
    """Markdown text to the HTML the editor produces for a Markdown block."""
    s = _u16("" if src is None else str(src)).replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
    return _from_u16(_join(_blocks(s.split("\n"), 0), True))
