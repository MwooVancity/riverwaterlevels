"""Spain reservoir pages, in Spanish (Spain): /es/ and /es/embalse/<slug>/ for ranks 1-50 of data/es-reservoirs.csv. Rendering only: figures come from
lib/es_data.py, the data from cache/_es.json (collect.py --es). Its own shell: no English chrome, no ad code. Weekly data is never called current when old."""
import csv
import datetime
import email.utils
import os
import re
import statistics
import unicodedata

from lib import es_data
from lib.charts import river_svg
from lib.common import ANALYTICS, BRAND, DATA, SITE_URL, esc
from lib.core import CSS_LINK, PWA_HEAD
from lib.directory import DIR_LINK
from lib.page import HEAD_EXTRA, crumb_ld, og_tags, robots_meta

TOP = 50
NEAR_USUAL = 5.0  # percentage points from the median that we still call "about usual"; our own cut, said on the page
MONTHS = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()
OFFICIAL_URL = "https://www.miteco.gob.es/es/agua/temas/evaluacion-de-los-recursos-hidricos/boletin-hidrologico.html"
TERMS_URL = "https://www.miteco.gob.es/es/atencion-al-ciudadano/aviso-legal.html"
HUB = "/es/"


def display(name):
    """The file's 'Viñuela, La' -> 'La Viñuela'; 'Porma-(Juan Benet)' -> 'Porma (Juan Benet)'."""
    m = re.match(r"^(.*), (El|La|Los|Las)$", name)
    return (m.group(2) + " " + m.group(1) if m else name).replace("-(", " (")


def full_name(name):
    d = display(name)
    return "Embalse del " + d[3:] if d.startswith("El ") else "Embalse de " + d


def slug(name):
    a = unicodedata.normalize("NFKD", display(name)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", a.lower()).strip("-")


def url_of(name):
    return "/es/embalse/%s/" % slug(name)


def top_names():
    with open(os.path.join(DATA, "es-reservoirs.csv"), encoding="utf-8", newline="") as f:
        names = [r["name"] for r in csv.DictReader(f) if int(r["rank"]) <= TOP]
    if len({slug(n) for n in names}) != len(names):
        raise ValueError("two Spain reservoirs share one address")
    return names


def all_urls():
    return [url_of(n) for n in top_names()] + [HUB]


def num(v, d=1):
    """Spanish figures: 1.505,5. A value that rounds to zero never carries a minus sign."""
    if v is None:
        return "Desconocido"
    s = "{:,.{}f}".format(round(v, d) + 0.0, d)
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def pc(v):
    return "Desconocido" if v is None else num(v) + "&nbsp;%"


def day(d):
    return "%d de %s de %d" % (d.day, MONTHS[d.month - 1], d.year)


def short(d):
    return "%02d/%02d/%d" % (d.day, d.month, d.year)


def moved(delta, since):
    if delta is None:
        return "Cambio %s: desconocido (no hay dato publicado cerca de esa fecha)." % since
    r = round(delta, 1)
    if r == 0:
        return "Cambio %s: ninguno (menos de 0,1 puntos porcentuales)." % since
    return "%s: %s %s puntos porcentuales de llenado." % (since[0].upper() + since[1:], "ha subido" if r > 0 else "ha bajado", num(abs(r)))


def usual(f):
    """'above' | 'below' | 'near' | None against the median of the same week, on the rounded figures the page prints."""
    if f["median"] is None:
        return None
    d = round(round(f["pct"], 1) - round(f["median"], 1), 1)
    return "near" if abs(d) < NEAR_USUAL else "above" if d > 0 else "below"


def sentence(f, today):
    k, v = usual(f), "estaba" if f["stale"] else "está"
    if k is None:
        s = "Solo hay %d años anteriores con dato para esta semana: con menos de 10 no calculamos qué es lo habitual." % f["years"]
    else:
        s = "%s %s para esta semana del año: %s, frente a una mediana del %s en %d años anteriores." % (
            v[0].upper() + v[1:], {"above": "más lleno de lo habitual", "below": "más vacío de lo habitual", "near": "cerca de lo habitual"}[k], pc(f["pct"]), pc(f["median"]), f["years"])
    if f["stale"]:
        s = "Dato antiguo: el último publicado es del %s, hace %d días; el llenado de esta semana es desconocido. Con aquel dato: %s" % (day(f["date"]), (today - f["date"]).days, s[0].lower() + s[1:])
    return s


def source_line(updated):
    return ('<p class="src">Fuente: <a href="%s" rel="noopener">MITECO, Boletín Hidrológico</a> (datos semanales y provisionales). Archivo actualizado por la fuente el %s. '
            'Los porcentajes, cambios y comparaciones son cálculos propios.</p>' % (OFFICIAL_URL, day(updated)))


def section(bid, heading, body, updated):
    return '<section class="card blk" id="%s"><h2>%s</h2>%s%s</section>' % (bid, heading, body, source_line(updated))


def table(head, rows):
    return '<div class="scroll"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (
        "".join('<th scope="col">%s</th>' % h for h in head), "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in r) for r in rows))


def chart(sec_id, heading, rows, since, xfmt, name, updated):
    """Percent-full line, 0 to at least 100. A run of missing weeks breaks the line instead of being drawn across."""
    pts = [(r[0], es_data.pct(r[1], r[2])) for r in rows if r[0] >= since and es_data.pct(r[1], r[2]) is not None]
    if len(pts) < 8:
        return ""
    utc = datetime.timezone.utc
    runs = [[]]
    for i, (d, v) in enumerate(pts):
        if i and (d - pts[i - 1][0]).days > 21:
            runs.append([])
        runs[-1].append((datetime.datetime(d.year, d.month, d.day, 12, tzinfo=utc), v))
    lo, hi = min(pts, key=lambda p: p[1]), max(pts, key=lambda p: p[1])
    say = "Entre el %s y el %s, el llenado se movió entre el %s (%s) y el %s (%s)." % (day(pts[0][0]), day(pts[-1][0]), pc(lo[1]), short(lo[0]), pc(hi[1]), short(hi[0]))
    aria = "Porcentaje de llenado del %s entre %s y %s" % (full_name(name).lower(), short(pts[0][0]), short(pts[-1][0]))
    svgs = "".join(river_svg([("", r) for r in runs], utc, w, h, fs, nx, cls, aria=aria, xfmt=xfmt, yr=(0, max(100.0, hi[1])), one=True) for w, h, fs, nx, cls in ((860, 260, 13, 6, "cw"), (360, 220, 12, 3, "cn")))
    return section(sec_id, heading, "<p>%s</p>%s<p class=\"sub\">Eje vertical: porcentaje de llenado.</p>" % (say, svgs), updated)


def shell(title, desc, url, crumbs, body):
    visible = " / ".join('<a href="%s">%s</a>' % (u, esc(n)) if u else esc(n) for n, u in crumbs)
    og = re.sub(r'(property="og:image:alt" content=")[^"]*', lambda m: m.group(1) + "River Water Levels: niveles de ríos y embalses", og_tags(title, desc, SITE_URL + url))
    # ANALYTICS = consent defaults (cookies denied in the EEA, UK and Switzerland, lib/common.py CONSENT) + Google Analytics. No AdSense loader, no ad slot.
    return ('<!doctype html><html lang="es" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title><meta name="description" content="%s">'
            '<link rel="canonical" href="%s">%s</head><body><a class="skip" href="#main">Saltar al contenido</a><nav class="nav" aria-label="Sitio"><a class="brand" href="/es/"><span class="logo"></span>%s</a>'
            '<span class="tabs"><a href="/es/">Embalses de España</a></span></nav><main id="main"><div class="crumb">%s</div>%s</main>'
            '<footer><span>%s &middot; Web independiente, no oficial. Datos: MITECO.</span><span><a href="/data-sources/" hreflang="en">Fuentes (en inglés)</a><a href="/privacy/" hreflang="en">Privacidad (en inglés)</a>'
            '<a href="/terms/" hreflang="en">Condiciones (en inglés)</a></span></footer></body></html>') % (
        esc(title), esc(desc), SITE_URL + url, ANALYTICS + HEAD_EXTRA + PWA_HEAD + og + crumb_ld(crumbs) + robots_meta(url) + CSS_LINK + DIR_LINK,
        esc(BRAND), visible, body, esc(BRAND))


def credit_block(updated):
    return ('<section class="card blk" id="es_fuente"><h2>De dónde salen los datos</h2><p>Los volúmenes embalsados y las capacidades proceden del Boletín Hidrológico del Ministerio para la Transición Ecológica y el Reto Demográfico (MITECO). '
            'Se publican cada semana y son datos provisionales: la fuente puede corregirlos. No son una medida en directo ni un aviso oficial. '
            'El porcentaje de cada fecha se calcula con la capacidad que la fuente da para esa fecha. El MITECO no participa en esta web, no la patrocina ni la apoya.</p>'
            '<p><a href="%s" rel="noopener">Boletín Hidrológico oficial</a> &middot; <a href="%s" rel="noopener">Condiciones de reutilización</a></p>%s</section>' % (OFFICIAL_URL, TERMS_URL, source_line(updated)))


def related(name, basin, found):
    """Up to 5 other reservoirs of the same basin, in search-rank order. The file has no coordinates, so no distance is claimed."""
    same = [(n, x) for n, x in found.items() if n != name and x["basin"] == basin][:5]
    if not same:
        return ""
    return '<section class="card" id="es_cuenca"><h2>Otros embalses de la cuenca: %s</h2><ul>%s</ul></section>' % (
        esc(basin), "".join('<li><a href="%s">%s: %s</a> (%s)</li>' % (url_of(n), esc(full_name(n)), pc(x["f"]["pct"]), short(x["f"]["date"])) for n, x in same))


def reservoir(name, found, updated, today):
    x = found[name]
    f, rows, basin, title_name = x["f"], x["rows"], x["basin"], full_name(name)
    vol, cap = num(f["volume"]), num(f["capacity"])
    head = ('<h1>%s</h1><p class="sub">Cuenca: %s</p><p class="answer"><span>%s</span></p>'
            '<div class="card"><p class="sub">%s</p><p style="font-size:2.4rem;font-weight:700;margin:0">%s</p><p><b>%s hm³ embalsados de %s hm³ de capacidad</b></p>'
            '<p>Dato semanal del %s%s.</p></div>') % (
        esc(title_name), esc(basin), sentence(f, today), "Último porcentaje de llenado publicado" if f["stale"] else "Porcentaje de llenado", pc(f["pct"]), vol, cap, day(f["date"]),
        " (dato antiguo: hace %d días)" % (today - f["date"]).days if f["stale"] else "")
    body = section("es_cambios", "Cambio en 1 y 4 semanas",
                   "<p>%s</p><p>%s</p><p class=\"sub\">Contado hacia atrás desde el dato del %s.</p>" % (moved(f["week_change"], "en 1 semana"), moved(f["month_change"], "en 4 semanas"), day(f["date"])), updated)
    ly = "La misma semana del año anterior (%d) estaba al %s." % (f["date"].year - 1, pc(f["last_year"])) if f["last_year"] is not None else "No hay dato publicado de la misma semana del año anterior."
    if f["median"] is None:
        past = "<p>%s</p><p>Hay %d años anteriores con dato para esta semana; hacen falta 10 para compararla.</p>" % (ly, f["years"])
    else:
        past = ("<p>%s</p><p>En esta misma semana de %d años anteriores con dato, el llenado fue desde el %s hasta el %s. En %d de esos %d años el porcentaje era menor que el del %s.</p>"
                '<p class="sub">Habitual significa a menos de %d puntos de la mediana (criterio propio). La mediana es el valor central de esos años.</p>%s') % (
            ly, f["years"], pc(f["low"]), pc(f["high"]), f["below"], f["years"], day(f["date"]), NEAR_USUAL,
            table(("Misma semana, años anteriores", "Llenado"), (("Mínimo", pc(f["low"])), ("Mediana", pc(f["median"])), ("Máximo", pc(f["high"])))))
    body += section("es_anos", "La misma semana en otros años", past, updated)
    body += chart("es_grafico_1", "Último año", rows, f["date"] - datetime.timedelta(days=366), "%m/%Y", name, updated)
    body += chart("es_grafico_10", "Últimos 10 años", rows, es_data.year_back(f["date"], 10), "%Y", name, updated)
    last = [r for r in rows if r[0] <= today][-8:][::-1]
    body += section("es_historial", "Últimas semanas publicadas", "<p>Las %d últimas fechas del archivo, de la más reciente a la más antigua. Si falta un valor, figura como Desconocido.</p>%s" % (
        len(last), table(("Fecha", "Llenado", "Volumen (hm³)", "Capacidad (hm³)"), [(short(d), pc(es_data.pct(c, v)), num(v) if es_data.pct(c, v) is not None else "Desconocido", num(c)) for d, c, v in last])), updated)
    body = head + body + related(name, basin, found) + '<p><a href="/es/">Ver los demás embalses de España de esta web</a></p>' + credit_block(updated)
    title = "%s: porcentaje y volumen embalsado | dato semanal" % title_name
    desc = "%s: %s%s de llenado, %s de %s hm³. Dato semanal del %s. Cambios y años anteriores. Fuente: MITECO." % (
        title_name, "último dato, " if f["stale"] else "", pc(f["pct"]).replace("&nbsp;", " "), vol, cap, day(f["date"]))
    if len(desc) > 200:
        desc = desc.replace(" Cambios y años anteriores.", "")
    return shell(title, desc, url_of(name), [("Inicio (en inglés)", "/"), ("Embalses de España", HUB), (title_name, None)], body)


def hub(found, updated, today):
    newest = max(x["f"]["date"] for x in found.values())
    fresh = [x["f"] for x in found.values() if not x["f"]["stale"]]
    kinds = [usual(f) for f in fresh]
    if fresh:
        say = "De %d embalses con dato reciente, %d están más llenos de lo habitual para esta semana, %d más vacíos y %d cerca de lo habitual%s. Último dato: %s." % (
            len(fresh), kinds.count("above"), kinds.count("below"), kinds.count("near"), "; %d sin comparación" % kinds.count(None) if None in kinds else "", day(newest))
    else:
        say = "No hay dato reciente: el último publicado es del %s, hace %d días." % (day(newest), (today - newest).days)
    body = ('<h1>Embalses de España: porcentaje de llenado</h1><p class="answer"><span>%s</span></p><p class="sub">Dato semanal. Es una selección de %d embalses, no el total de España. '
            'Habitual: a menos de %d puntos de la mediana de la misma semana en años anteriores (cálculo propio).</p>') % (say, len(found), NEAR_USUAL)
    word = {"above": "más lleno", "below": "más vacío", "near": "habitual", None: "sin comparación"}
    for i, basin in enumerate(sorted({x["basin"] for x in found.values()})):
        here = sorted((n for n, x in found.items() if x["basin"] == basin), key=slug)
        rows = [('<a href="%s">%s</a>' % (url_of(n), esc(display(n))), pc(found[n]["f"]["pct"]), "%s de %s" % (num(found[n]["f"]["volume"]), num(found[n]["f"]["capacity"])),
                 "dato antiguo: " + short(found[n]["f"]["date"]) if found[n]["f"]["stale"] else "%s (%s)" % (word[usual(found[n]["f"])], short(found[n]["f"]["date"]))) for n in here]
        med = statistics.median(found[n]["f"]["pct"] for n in here)
        lead = "<p>%d embalses en esta lista; la mitad está al %s o más (último dato de cada uno).</p>" % (len(here), pc(med)) if len(here) > 2 else ""
        body += section("cuenca_%d" % i, esc(basin), lead + table(("Embalse", "Llenado", "hm³", "Esta semana"), rows), updated)
    desc = "Porcentaje de llenado y volumen embalsado de %d embalses de España, por cuenca, con dato semanal del %s. Fuente: MITECO." % (len(found), day(newest))
    return shell("Embalses de España: porcentaje de llenado por cuenca | dato semanal", desc, HUB, [("Inicio (en inglés)", "/"), ("Embalses de España", None)], body + credit_block(updated))


def pages(cache, today):
    """({url: html}, [(url, reason)]) from the cache object. A reservoir with no usable reading, or whose render raises, is left out and named."""
    data, basins = es_data.unpack(cache)
    try:
        updated = email.utils.parsedate_to_datetime(cache["modified"]).date()
    except (KeyError, TypeError, ValueError):
        updated = datetime.date.fromisoformat(cache["newest"])
    found, bad = {}, []
    for n in top_names():  # rank order: related() relies on it
        f = es_data.figures(data.get(n, []), today)
        if f:
            found[n] = {"f": f, "rows": data[n], "basin": basins[n]}
        else:
            bad.append((url_of(n), "no usable reading"))
    out, ok = {}, {}
    for n in found:
        try:
            out[url_of(n)] = reservoir(n, found, updated, today)
            ok[n] = found[n]
        except Exception as e:  # one reservoir never stops the other 49
            bad.append((url_of(n), "%s: %s" % (type(e).__name__, str(e)[:100])))
    if ok:
        out[HUB] = hub(ok, updated, today)
    return out, bad
