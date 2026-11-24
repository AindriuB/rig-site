"""Rewrite relative links in a rig markdown page for the published site."""
from __future__ import annotations

import posixpath
import re
from urllib.parse import unquote

from context import BuildError

_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_REFDEF = re.compile(r"^( {0,3}\[[^\]]+\]:[ \t]*)(<[^>]*>|\S+)")
_REFDEF_ID = re.compile(r"^ {0,3}\[([^\]]+)\]:")
_IMG_REF = re.compile(r"!\[[^\]]*\]\[([^\]]*)\]|!\[([^\]]+)\](?![\[(])")


def _mask_code(line: str) -> str:
    """Blank out code spans so link scanning ignores them; length is kept."""
    out, i = [], 0
    while i < len(line):
        if line[i] == "`":
            j = i
            while j < len(line) and line[j] == "`":
                j += 1
            run = line[i:j]
            end = line.find(run, j)
            while end != -1 and end + len(run) < len(line) and line[end + len(run)] == "`":
                end = line.find(run, end + len(run) + 1)
            if end == -1:
                out.append(run)
                i = j
                continue
            out.append("\0" * (end + len(run) - i))
            i = end + len(run)
        else:
            out.append(line[i])
            i += 1
    return "".join(out)


def _is_relative(url: str) -> bool:
    return bool(url) and not url.startswith(("#", "//")) and not _SCHEME.match(url)


def _inline_dests(masked: str):
    """Yield (start, end, is_image) for each inline link destination."""
    pos = 0
    while True:
        k = masked.find("](", pos)
        if k == -1:
            return
        pos = k + 2
        # matching '[' of the link text
        depth, i = 0, k
        open_at = -1
        while i >= 0:
            c = masked[i]
            if i > 0 and masked[i - 1] == "\\":
                i -= 1
                continue
            if c == "]":
                depth += 1
            elif c == "[":
                depth -= 1
                if depth == 0:
                    open_at = i
                    break
            i -= 1
        if open_at == -1:
            continue
        is_image = open_at > 0 and masked[open_at - 1] == "!"
        s = pos
        while s < len(masked) and masked[s] in " \t":
            s += 1
        if s < len(masked) and masked[s] == "<":
            e = masked.find(">", s)
            if e == -1:
                continue
            yield s + 1, e, is_image
            continue
        e, depth = s, 0
        while e < len(masked):
            c = masked[e]
            if c in " \t":
                break
            if c == "(":
                depth += 1
            elif c == ")":
                if depth == 0:
                    break
                depth -= 1
            e += 1
        if e > s:
            yield s, e, is_image


def _convert(url: str, src_path: str, published: dict[str, str], blob_base: str,
             line_no: int) -> str:
    m = re.match(r"^([^#?]*)(.*)$", url)
    path, frag = m.group(1), m.group(2)
    if not path:
        return url
    path = unquote(path)
    if path.startswith("/"):
        target = posixpath.normpath(path.lstrip("/"))
    else:
        target = posixpath.normpath(posixpath.join(posixpath.dirname(src_path), path))
    if target == ".." or target.startswith("../"):
        raise BuildError(f"{src_path}:{line_no}: link {url!r} escapes the repository")
    if target in published:
        page = published[target]
        start = posixpath.dirname(published[src_path]) if src_path in published else ""
        return posixpath.relpath(page, start or ".") + frag
    return blob_base + target + frag


def rewrite_links(text: str, src_path: str, published: dict[str, str],
                  blob_base: str) -> str:
    lines = text.split("\n")
    in_fence = None
    masked_lines: list[str | None] = []
    for line in lines:
        fm = _FENCE.match(line)
        if in_fence:
            if fm and fm.group(1)[0] == in_fence[0] and len(fm.group(1)) >= len(in_fence) \
                    and line.strip() == fm.group(1):
                in_fence = None
            masked_lines.append(None)
        elif fm:
            in_fence = fm.group(1)
            masked_lines.append(None)
        else:
            masked_lines.append(_mask_code(line))

    image_ids = set()
    for masked in masked_lines:
        if masked is None:
            continue
        for m in _IMG_REF.finditer(masked):
            ident = m.group(1) or m.group(2) or ""
            image_ids.add(ident.strip().lower())

    out = []
    for n, (line, masked) in enumerate(zip(lines, masked_lines), start=1):
        if masked is None:
            out.append(line)
            continue
        edits: list[tuple[int, int, str]] = []
        for s, e, is_image in _inline_dests(masked):
            url = line[s:e]
            if not _is_relative(url):
                continue
            if is_image:
                raise BuildError(f"{src_path}:{n}: relative image reference {url!r}")
            edits.append((s, e, _convert(url, src_path, published, blob_base, n)))
        rd = _REFDEF.match(masked)
        if rd:
            s, e = len(rd.group(1)), len(rd.group(0))
            url = line[s:e]
            if url.startswith("<") and url.endswith(">"):
                s, e, url = s + 1, e - 1, url[1:-1]
            if _is_relative(url):
                ident = _REFDEF_ID.match(line).group(1).strip().lower()
                if ident in image_ids:
                    raise BuildError(f"{src_path}:{n}: relative image reference {url!r}")
                edits.append((s, e, _convert(url, src_path, published, blob_base, n)))
        for s, e, new in sorted(edits, reverse=True):
            line = line[:s] + new + line[e:]
        out.append(line)
    return "\n".join(out)
