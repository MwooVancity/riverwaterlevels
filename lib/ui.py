"""Small visual widgets for the gauge page: line icons, the percentile dial, stat tiles. Pure strings, no data access."""
import math

_I = '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>'
ICONS = {
    "flow": _I % '<path d="M2 8c3-3 5-3 8 0s5 3 8 0 3-2 4-1"/><path d="M2 14c3-3 5-3 8 0s5 3 8 0 3-2 4-1"/><path d="M2 20c3-3 5-3 8 0s5 3 8 0 3-2 4-1"/>',
    "stage": _I % '<path d="M12 3v18"/><path d="M8 6h8M9 10h6M8 14h8M9 18h6"/>',
    "up": _I % '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "down": _I % '<path d="M3 7l6 6 4-4 8 8"/><path d="M15 17h6v-6"/>',
    "steady": _I % '<path d="M4 12h16"/><path d="M15 7l5 5-5 5"/>',
    "crest": _I % '<path d="M3 19c3 0 3-12 6-12s3 12 6 12 3-6 6-6"/>',
    "bell": _I % '<path d="M6 17V11a6 6 0 1 1 12 0v6l2 2H4z"/><path d="M10 21h4"/>',
    "drop": _I % '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
    "thermo": _I % '<path d="M10 14V5a2 2 0 1 1 4 0v9a4 4 0 1 1-4 0z"/>',
    "map": _I % '<path d="M9 4L3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/>',
    "link": _I % '<path d="M10 14a4 4 0 0 0 6 0l3-3a4 4 0 0 0-6-6l-1 1"/><path d="M14 10a4 4 0 0 0-6 0l-3 3a4 4 0 0 0 6 6l1-1"/>',
    "download": _I % '<path d="M12 4v11"/><path d="M7 11l5 5 5-5"/><path d="M5 20h14"/>',
    "star": _I % '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
    "wind": _I % '<path d="M3 8h11a3 3 0 1 0-3-3"/><path d="M3 12h16a3 3 0 1 1-3 3"/><path d="M3 16h7"/>',
    "search": _I % '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4-4"/>',
}


def icon(name):
    return ICONS.get(name, "")


def dial_legend():
    return '<p class="dleg"><span><i class="la"></i>Below normal</span><span><i class="lb"></i>Normal range</span><span><i class="lp"></i>Above normal</span></p>'


def dial(p):
    """Semicircle scale: below 25th amber, 25th to 75th blue, above 75th purple (the same colours as the map dots). p is a percentile 0 to 100, -1 below the 5th, 101 above the 95th, None unknown."""
    cx, cy, r = 100, 96, 78

    def pt(frac, rad):
        a = math.pi * (1 - frac)
        return cx + rad * math.cos(a), cy - rad * math.sin(a)

    def arc(f0, f1, cls):
        x0, y0 = pt(f0, r)
        x1, y1 = pt(f1, r)
        return '<path d="M%.1f %.1f A%d %d 0 0 1 %.1f %.1f" class="%s"/>' % (x0, y0, r, r, x1, y1, cls)

    ticks = ""
    for v in (5, 25, 50, 75, 95):
        x0, y0 = pt(v / 100, r - 7)
        x1, y1 = pt(v / 100, r + 7)
        tx, ty = pt(v / 100, r + 17)
        ticks += '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" class="dt"/><text x="%.1f" y="%.1f" class="dl" text-anchor="middle">%d</text>' % (x0, y0, x1, y1, tx, ty + 3, v)
    needle = ""
    if p is not None:
        f = 0.0 if p == -1 else 1.0 if p == 101 else max(0.0, min(1.0, p / 100))
        nx, ny = pt(f, r - 10)
        needle = '<line x1="%d" y1="%d" x2="%.1f" y2="%.1f" class="dn"/><circle cx="%d" cy="%d" r="6" class="dc"/>' % (cx, cy, nx, ny, cx, cy)
    return ('<svg class="dial" viewBox="0 -8 200 126" role="img" aria-label="%s">%s%s%s%s%s</svg>' % (
        "Percentile position on a 0 to 100 scale" if p is not None else "No percentile available",
        arc(0, 0.25, "da"), arc(0.25, 0.75, "db"), arc(0.75, 1, "dp"), ticks, needle))


def tile(kind, ico, label, value_html, sub_html, cls=""):
    """One stat tile. The label and value keep the exact `<span>label</span><b>value</b>` shape that check.py and the live script read."""
    return '<div class="tile %s%s"><i class="ic">%s</i><span>%s</span><b>%s</b>%s</div>' % (kind, (" " + cls) if cls else "", icon(ico), label, value_html, sub_html)


def spark(values, w=150, h=34):
    """Tiny line of the last 24 hours inside a tile: no axes, the end point marked. Values are plain numbers in time order."""
    v = [x for x in values if x is not None]
    if len(v) < 6:
        return ""
    step = max(1, len(v) // 80)
    v = v[::step] + [v[-1]]
    lo, hi = min(v), max(v)
    span = (hi - lo) or 1.0
    pts = ["%.1f,%.1f" % (2 + i * (w - 4) / (len(v) - 1), 3 + (1 - (x - lo) / span) * (h - 6)) for i, x in enumerate(v)]
    ex, ey = pts[-1].split(",")
    return '<svg class="spark" viewBox="0 0 %d %d" width="%d" height="%d" aria-hidden="true"><polyline points="%s" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/><circle cx="%s" cy="%s" r="2.6" fill="currentColor"/></svg>' % (w, h, w, h, " ".join(pts), ex, ey)


def ladder(cats, cur, fc=None):
    """Horizontal flood-stage scale: grey below action stage, then yellow, orange, red, purple for action, minor, moderate and major (NWS thresholds), with the latest stage and the forecast high marked. cats = {name: ft}, cur and fc in feet."""
    order = [(k, cats[k]) for k in ("action", "minor", "moderate", "major") if k in cats]
    if not order:
        return ""
    cols = {"action": "#d6a300", "minor": "#e07b00", "moderate": "#c8341f", "major": "#7a2fa0"}
    top = max([order[-1][1] * 1.08, cur or 0, fc or 0]) or 1
    lo = min(0.0, cur or 0, fc or 0)
    span = (top - lo) or 1.0
    W, H, L, R_ = 760, 86, 14, 14
    X = lambda v: L + (v - lo) / span * (W - L - R_)
    seg = '<rect x="%.1f" y="34" width="%.1f" height="14" rx="3" class="lg"/>' % (X(lo), X(order[0][1]) - X(lo))
    for i, (k, v) in enumerate(order):
        end = order[i + 1][1] if i + 1 < len(order) else top
        seg += '<rect x="%.1f" y="34" width="%.1f" height="14" fill="%s"/>' % (X(v), X(end) - X(v), cols[k])
    lab = ""
    for k, v in order:
        lab += '<line x1="%.1f" y1="30" x2="%.1f" y2="52" class="lt"/><text x="%.1f" y="68" class="ll" text-anchor="middle">%s</text><text x="%.1f" y="80" class="ll2" text-anchor="middle">%.1f ft</text>' % (X(v), X(v), X(v), k.capitalize(), X(v), v)
    mk = ""
    if cur is not None:
        mk += '<path d="M%.1f 32 l-6 -12 h12 z" class="mk"/><text x="%.1f" y="12" class="ml" text-anchor="%s">Now %.2f ft</text>' % (X(cur), X(cur), "start" if X(cur) < 70 else "end" if X(cur) > W - 90 else "middle", cur)
    if fc is not None and cur is not None and abs(X(fc) - X(cur)) > 3:
        mk += '<path d="M%.1f 50 l-5 10 h10 z" class="mf"/>' % X(fc)
    txt = "Flood stage scale: latest stage %.2f ft%s; action, minor, moderate and major flood stages at %s." % (cur or 0, ("; forecast high %.1f ft" % fc) if fc is not None else "", ", ".join("%.1f ft" % v for _, v in order))
    return '<svg class="ladder" viewBox="0 0 %d %d" width="100%%" role="img" aria-label="%s">%s%s%s</svg>' % (W, H, txt, seg, lab, mk)
