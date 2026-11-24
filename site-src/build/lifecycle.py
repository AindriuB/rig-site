"""Turn a rig workflow preset into a Mermaid `stateDiagram-v2` fence."""
from __future__ import annotations

PREVIOUS = "$previous"


def _as_list(value) -> list[str]:
    return list(value) if isinstance(value, list) else [value]


def _routes(preset: dict) -> list[tuple[str, str, str | None]]:
    """(from, to, label) for every route after expanding `from` lists and `*`.

    `$previous` moves are not included; see `_previous_edges`.
    """
    states = preset["states"]
    out = []
    for t in preset.get("transitions", []):
        if t["to"] == PREVIOUS:
            continue
        sources = _as_list(t["from"])
        for src in sources:
            if src == "*":
                expanded = [s for s, d in states.items()
                            if not d.get("final") and s != t["to"]]
            else:
                expanded = [src]
            for s in expanded:
                out.append((s, t["to"], t.get("takes")))
    return out


def _previous_edges(preset: dict, routes) -> list[tuple[str, str, str | None]]:
    states = preset["states"]
    out = []
    for t in preset.get("transitions", []):
        if t["to"] != PREVIOUS:
            continue
        sources = []
        for src in _as_list(t["from"]):
            if src == "*":
                sources += [s for s, d in states.items() if not d.get("final")]
            else:
                sources.append(src)
        for s in sources:
            for origin in states:
                if any(f == origin and to == s for f, to, _ in routes):
                    out.append((s, origin, "previous"))
    return out


def _alt(preset: dict, edges, finals) -> str:
    states = preset["states"]
    parts = []
    for name, d in states.items():
        bits = []
        if d.get("action"):
            bits.append(f"action {d['action']}")
        if d.get("final"):
            bits.append("final")
        parts.append(name + (f" ({', '.join(bits)})" if bits else ""))
    routes = []
    for f, to, label in edges:
        if label == "previous":
            routes.append(f"{f} back to {to}, the state before")
        elif label:
            routes.append(f"{f} to {to}, taking a {label}")
        else:
            routes.append(f"{f} to {to}")
    text = (f"State diagram of the {preset.get('name', 'workflow')} preset. "
            f"A new task starts in {preset['initial']}. "
            f"States: {', '.join(parts)}. "
            f"Routes: {'; '.join(routes)}.")
    if finals:
        text += f" A task ends after {', '.join(finals)}."
    return text.replace("\n", " ")


def preset_to_mermaid(preset: dict) -> str:
    states = preset["states"]
    routes = _routes(preset)
    edges = routes + _previous_edges(preset, routes)
    finals = [s for s, d in states.items() if d.get("final")]
    lines = ["```mermaid", "%% alt: " + _alt(preset, edges, finals), "stateDiagram-v2"]
    for name, d in states.items():
        if d.get("action"):
            lines.append(f'    state "{name} ({d["action"]})" as {name}')
    lines.append(f"    [*] --> {preset['initial']}")
    for f, to, label in edges:
        lines.append(f"    {f} --> {to}" + (f" : {label}" if label else ""))
    for f in finals:
        lines.append(f"    {f} --> [*]")
    lines.append("```")
    return "\n".join(lines) + "\n"
