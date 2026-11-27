"""Spain reservoir pages, in Spanish (Spain): /es/ and /es/embalse/<slug>/ for ranks 1-50 of data/es-reservoirs.csv. Rendering only: figures come from
lib/es_data.py, the data from cache/_es.json (collect.py --es). Its own shell: no English chrome, no ad code. Weekly data is never called current when old."""
import csv
import datetime
import email.utils
import json
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


def hm(v):
    """Volumes as the source publishes them: whole hm3 stay whole (no invented decimal)."""
    return num(v, 0 if v is not None and v == int(v) else 1)


def coarse(f):
    """1 hm3 is over NEAR_USUAL points of this reservoir: too coarse to call it fuller or emptier than usual."""
    return 100.0 / f["capacity"] > NEAR_USUAL


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
        return "Cambio %s: ninguno (sin cambio apreciable en las cifras publicadas)." % since
    return "%s: %s %s puntos porcentuales de llenado." % (since[0].upper() + since[1:], "ha subido" if r > 0 else "ha bajado", num(abs(r)))


def usual(f):
    """'above' | 'below' | 'near' | None against the median of the same week, on the rounded figures the page prints."""
    if f["median"] is None or coarse(f):
        return None
    d = round(round(f["pct"], 1) - round(f["median"], 1), 1)
    return "near" if abs(d) < NEAR_USUAL else "above" if d > 0 else "below"


def comparable_words(f):
    """Appended to "años anteriores con dato" when weeks on another capacity were left out: the record is longer than the count."""
    return " y capacidad comparable" if f["other_capacity"] else ""


def sentence(f, today):
    """Always dated: a static copy must never say "this week"."""
    k, when = usual(f), "En la semana del %s" % day(f["date"])
    if k is not None:
        s = "%s estaba %s para esas fechas del año: %s, frente a una mediana del %s en %d años anteriores." % (
            when, {"above": "más lleno de lo habitual", "below": "más vacío de lo habitual", "near": "cerca de lo habitual"}[k], pc(f["pct"]), pc(f["median"]), f["years"])
    elif f["median"] is None:
        s = "%s estaba al %s. Solo hay %d años anteriores con dato%s para esas fechas: con menos de 10 no calculamos qué es lo habitual." % (when, pc(f["pct"]), f["years"], comparable_words(f))
    else:
        s = "%s estaba al %s. Es un embalse pequeño: 1 hm³ son %s puntos de llenado, así que no lo calificamos frente a lo habitual." % (when, pc(f["pct"]), num(100.0 / f["capacity"]))
    if f["week_change"] is not None and abs(f["week_change"]) > es_data.SPIKE:
        s += " Es un cambio muy grande para una semana; la fuente puede corregirlo."
    if f["stale"]:
        s = "Dato antiguo: el último publicado es del %s, hace %d días; el llenado posterior es desconocido. %s" % (day(f["date"]), (today - f["date"]).days, s)
    return s


OLD_ID = 'id="es_antiguo"'


def mark_old(html, today):
    """A carried live copy is never rebuilt, so it cannot turn old by itself: past STALE_DAYS it gets a banner and an old-data headline label."""
    found = [datetime.date(int(y), MONTHS.index(m) + 1, int(d)) for d, m, y in
             re.findall(r"(?:Dato semanal del|Último dato:|el último publicado es del) (\d{1,2}) de (%s) de (\d{4})" % "|".join(MONTHS), html)]
    if OLD_ID in html or not found or (today - max(found)).days <= es_data.STALE_DAYS:
        return html
    note = '<p class="answer" %s><span>Dato antiguo: esta copia no se ha renovado. Su último dato es del %s; el llenado posterior es desconocido.</span></p>' % (OLD_ID, day(max(found)))
    return html.replace('<p class="sub">Porcentaje de llenado</p>', '<p class="sub">Último porcentaje de llenado publicado</p>').replace("</h1>", "</h1>" + note, 1)


def source_line(updated):
    """The full credit, once a page (credit_block). `updated` is None when the source sent no file date: it is then said, never invented."""
    when = "Archivo actualizado por la fuente el %s." % day(updated[0]) if updated[0] else "La fuente no indica la fecha de actualización del archivo; último dato: %s." % day(updated[1])
    return ('<p class="src">Fuente: <a href="%s" rel="noopener">MITECO, Boletín Hidrológico</a> (Histórico de embalses, BD-Embalses; datos semanales y provisionales). %s '
            'Los porcentajes, cambios y comparaciones son cálculos propios.</p>' % (OFFICIAL_URL, when))


SHORT_SOURCE = '<p class="src">Fuente: <a href="%s" rel="noopener">MITECO, Boletín Hidrológico</a>, dato semanal. Cálculos propios.</p>' % OFFICIAL_URL


def section(bid, heading, body, updated):
    return '<section class="card blk" id="%s"><h2>%s</h2>%s%s</section>' % (bid, heading, body, SHORT_SOURCE)


def table(head, rows):
    return '<div class="scroll"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (
        "".join('<th scope="col">%s</th>' % h for h in head), "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in r) for r in rows))


def chart(sec_id, heading, rows, since, xfmt, name, updated, cap):
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
    window = [r for r in rows if r[0] >= since and es_data.pct(r[1], r[2]) is not None]
    if len(es_data.comparable(window, cap)) < len(window):
        say = "La fuente cambió la capacidad de este embalse dentro de este periodo: los porcentajes de antes y de después no se pueden comparar, así que no damos un mínimo ni un máximo del gráfico."
    aria = "Porcentaje de llenado del %s entre %s y %s" % (full_name(name).lower(), short(pts[0][0]), short(pts[-1][0]))
    svgs = "".join(river_svg([("", r) for r in runs], utc, w, h, fs, nx, cls, aria=aria, xfmt=xfmt, yr=(0, max(100.0, hi[1])), one=True) for w, h, fs, nx, cls in ((860, 260, 13, 6, "cw"), (360, 220, 12, 3, "cn")))
    return section(sec_id, heading, "<p>%s</p>%s<p class=\"sub\">Eje vertical: porcentaje de llenado.</p>" % (say, svgs), updated)


def shell(title, desc, url, crumbs, body):
    visible = " / ".join('<a href="%s">%s</a>' % (u, esc(n)) if u else esc(n) for n, u in crumbs)
    og = og_tags(title, desc, SITE_URL + url).replace("/og.png", "/og-es.png")  # /og.png is English and credits USGS
    og = re.sub(r'(property="og:image:alt" content=")[^"]*', lambda m: m.group(1) + "Embalses de España: porcentaje de llenado, dato semanal. Fuente: MITECO", og)
    og += '<meta property="og:locale" content="es_ES">'
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
    return '<section class="card" id="es_cuenca"><h2>Más embalses · %s</h2><ul>%s</ul></section>' % (
        esc(basin), "".join('<li><a href="%s">%s: %s</a> (%s)</li>' % (url_of(n), esc(full_name(n)), pc(x["f"]["pct"]), short(x["f"]["date"])) for n, x in same))


ACCESS_DAYS = 365  # an older map reading is not shown
ACCESS = (("ramp", "Rampas para embarcaciones", "Rampa", "rampa para embarcaciones", "rampas para embarcaciones"),
          ("bathing", "Lugares de baño en el mapa", "Lugar de baño", "lugar de baño", "lugares de baño"),
          ("beach", "Playas", "Playa", "playa", "playas"),
          ("boats", "Náutica: puertos, clubes y alquiler", "Instalación náutica", "punto de náutica", "puntos de náutica"),
          ("camp", "Campings y áreas de acampada cercanas", "Acampada", "camping o área de acampada", "campings o áreas de acampada"))
SERVICES = (("parking", "Aparcamiento"), ("water", "Fuente de agua"), ("toilets", "Aseos"), ("motorhome", "Área de autocaravanas"))
SHOWN = 6  # per group; the rest are counted
ACCESS_NOTE = {"customers": "solo clientes", "permit": "con permiso"}


def access_data():
    """data/es-access.json (tools/es_access.py); unreadable means no block, never "there is none"."""
    try:
        with open(os.path.join(DATA, "es-access.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def access_section(name, today, data):
    try:
        read = datetime.date.fromisoformat(data["read_on"])
        places = data["reservoirs"][name]
    except (KeyError, TypeError, ValueError):
        return ""
    if not places or (today - read).days > ACCESS_DAYS:
        return ""
    counts, lists = [], ""
    for kind, heading, label, one, many in ACCESS:
        here = [p for p in places if p["kind"] == kind]
        if not here:
            continue
        counts.append("%d %s" % (len(here), one if len(here) == 1 else many))
        unnamed = [p for p in here[:SHOWN] if not p["name"]]
        items = "".join('<li><a href="https://www.openstreetmap.org/%s" rel="noopener">%s</a>%s</li>' % (
            esc(p["osm"]), esc(p["name"] or "%s sin nombre (%d)" % (label, unnamed.index(p) + 1)), " &middot; " + ACCESS_NOTE[p["access"]] if p.get("access") in ACCESS_NOTE else "")
            for p in here[:SHOWN])
        lists += "<h3>%s</h3><ul>%s</ul>%s" % (heading, items, '<p class="sub">Y %d más marcados en el mapa.</p>' % (len(here) - SHOWN) if len(here) > SHOWN else "")
    items, kinds = "", []
    for kind, label in SERVICES:
        here = [p for p in places if p["kind"] == kind]
        if here:
            kinds.append(label.lower())
        unnamed = [p for p in here if not p["name"]]
        for p in here:
            what = "%s: %s" % (label, p["name"]) if p["name"] else "%s sin nombre (%d)" % (label, unnamed.index(p) + 1)
            items += '<li><a href="https://www.openstreetmap.org/%s" rel="noopener">%s</a>, %s en línea recta del contorno del agua en el mapa%s</li>' % (
                esc(p["osm"]), esc(what), "a unos %d m" % p["m"] if p["m"] >= 10 else "a menos de 10 m", " &middot; " + ACCESS_NOTE[p["access"]] if p.get("access") in ACCESS_NOTE else "")
    if items:
        lists += ('<h3>Servicios cerca del agua</h3><ul>%s</ul><p class="sub">Como mucho 3 de cada tipo, los más cercanos entre los editados en el mapa desde 2021. El camino real puede ser más largo.%s%s</p>') % (
            items, " Una fuente puede estar seca o no ser potable." if "fuente de agua" in kinds else "",
            " Que figure en el mapa no indica que sea gratis ni que se permita pernoctar." if {"aparcamiento", "área de autocaravanas"} & set(kinds) else "")
    if not lists:
        return ""

    def joined(v):
        return " y ".join([", ".join(v[:-1]), v[-1]] if len(v) > 1 else v)

    lead = "Junto a este embalse o cerca de él, el mapa marca: %s. " % joined(counts) if counts else "Cerca del agua, el mapa marca estos tipos de servicio: %s. " % joined(kinds)
    low = " Con el embalse bajo, una rampa o una orilla puede quedar lejos del agua." if counts else " Con el embalse bajo, el agua puede quedar más lejos."
    return ('<section class="card blk" id="es_acceso"><h2>Para ir al agua: lo que marca el mapa</h2><p>%sCada enlace abre el sitio en el mapa.</p>%s'
            '<p class="sub">Que un sitio esté en el mapa no indica que esté abierto, que tenga acceso público ni que se permita bañarse o navegar: compruébalo antes de ir.%s '
            'La lista puede estar incompleta.</p>'
            '<p class="src">Fuente: <a href="https://www.openstreetmap.org/copyright" rel="noopener">© colaboradores de OpenStreetMap</a> (licencia ODbL). Mapa consultado el %s.</p></section>') % (
        lead, lists, low, day(read))


def capacity_note(f):
    """Said wherever a comparison dropped weeks measured against another capacity."""
    if not f["other_capacity"]:
        return ""
    lo, hi = hm(f["other_capacity"][0]), hm(f["other_capacity"][-1])
    was = "de %s hm³" % lo if lo == hi else "de entre %s y %s hm³" % (lo, hi)
    return ('<p class="sub">En otras fechas la fuente ha dado a este embalse una capacidad %s (la actual es de %s hm³). Las comparaciones entre fechas usan solo las semanas con una capacidad '
            'a menos del %d %% de la actual. Los gráficos muestran cada fecha con su propia capacidad.</p>') % (was, hm(f["capacity"]), round(es_data.CAP_TOL * 100))


def later_section(f, rows, today, updated):
    """What followed these dates in past years. No count of ups and downs: shifting the start week changes it, and past starts can be far from today's."""
    lt = None if f["stale"] or coarse(f) else es_data.later(rows, today)
    if not lt:
        return ""
    starts = [r[1] for r in lt]
    say = ("Así evolucionó el embalse en las 8 semanas siguientes a estas fechas en %d de los 10 años anteriores. Aquellos años partían de entre el %s y el %s; "
           "esta vez se parte del %s (%s). No es una previsión.") % (len(lt), pc(min(starts)), pc(max(starts)), pc(f["pct"]), day(f["date"]))
    return section("es_despues", "Qué pasó después, otros años", "<p>%s</p>%s%s" % (
        say, table(("Año de partida", "Esa semana", "4 semanas después", "8 semanas después"), [(str(y), pc(a), pc(b), pc(c)) for y, a, b, c in lt]), ""), updated)


def boat_data():
    """data/es-boat.json, transcribed from the basin authority and BOE; unreadable means no block."""
    try:
        with open(os.path.join(DATA, "es-boat.json"), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def boat_section(name, today, data):
    try:
        read = datetime.date.fromisoformat(data["read_on"])
        r = data["reservoirs"][name]
        lines = r["lines"] + data["common"][r["basin"]]
        src = [data["sources"][k] for k in r["src"]]
    except (KeyError, TypeError, ValueError):
        return ""
    if (today - read).days > ACCESS_DAYS:
        return ""
    return ('<section class="card blk" id="es_navegar"><h2>Navegar aquí: normas oficiales</h2><p>Esto dicen las normas de navegación publicadas para este embalse (resumen propio; lo que vale es el texto oficial).</p>'
            '<ul>%s</ul><p class="sub">Las normas pueden cambiar, y la Confederación puede cerrar zonas o suspender la navegación: consulta la fuente antes de ir. No indica que se pueda navegar en este momento.</p>'
            '<p class="src">Fuente: %s. Leído el %s.%s</p></section>') % (
        "".join("<li>%s</li>" % esc(x) for x in lines), " &middot; ".join('<a href="%s" rel="noopener">%s</a>' % (esc(u), esc(t)) for t, u in src), day(read),
        ' Basado en datos de la Agencia Estatal Boletín Oficial del Estado (<a href="https://www.boe.es" rel="noopener">https://www.boe.es</a>), texto resumido.' if any(k.startswith("boe") for k in r["src"]) else "")


def month_section(f, rows, updated):
    mo = es_data.monthly(rows, f["date"].year, f["capacity"])
    if not mo:
        return ""
    hi, lo = max(mo, key=lambda r: r[1]), min(mo, key=lambda r: r[1])
    span = "%d–%d" % (f["date"].year - 10, f["date"].year - 1)
    if coarse(f):
        say = "Cifras de %s. Es un embalse pequeño: no destacamos un mes frente a otro." % span
    elif round(hi[1] - lo[1], 1) < 3:
        say = "En %s el llenado habitual cambió poco de un mes a otro: la mediana mensual fue de %s a %s." % (span, pc(lo[1]), pc(hi[1]))
    else:
        say = "En %s, el mes con la mediana más alta fue %s (%s) y el de la más baja, %s (%s)." % (span, MONTHS[hi[0] - 1], pc(hi[1]), MONTHS[lo[0] - 1], pc(lo[1]))
    key = ("Mediana: el valor central de las cifras de ese mes en cada año. Mínimo y máximo: la lectura semanal más baja y la más alta de ese mes entre %s." % span)
    return section("es_meses", "El llenado mes a mes", '<p>%s No es una previsión.</p><p class="sub">%s</p>%s' % (
        say, key, table(("Mes", "Mediana", "Mínimo", "Máximo"), [(MONTHS[m - 1].capitalize(), pc(md), pc(a), pc(b)) for m, md, a, b, _ in mo])), updated)


def reservoir(name, found, updated, today):
    x = found[name]
    f, rows, basin, title_name = x["f"], x["rows"], x["basin"], full_name(name)
    vol, cap = hm(f["volume"]), hm(f["capacity"])
    head = ('<h1>%s</h1><p class="sub">Cuenca: %s</p><p class="answer"><span>%s</span></p>'
            '<div class="card"><p class="sub">%s</p><p style="font-size:2.4rem;font-weight:700;margin:0">%s</p><p><b>%s hm³ embalsados de %s hm³ de capacidad</b></p>'
            '<p>Dato semanal del %s%s.</p></div>') % (
        esc(title_name), esc(basin), sentence(f, today), "Último porcentaje de llenado publicado" if f["stale"] else "Porcentaje de llenado", pc(f["pct"]), vol, cap, day(f["date"]),
        " (dato antiguo: hace %d días)" % (today - f["date"]).days if f["stale"] else "")
    body = section("es_cambios", "Cambio en 1 y 4 semanas",
                   "<p>%s</p><p>%s</p><p class=\"sub\">Contado hacia atrás desde el dato del %s.</p>" % (moved(f["week_change"], "en 1 semana"), moved(f["month_change"], "en 4 semanas"), day(f["date"])), updated)
    body += access_section(name, today, access_data())
    body += boat_section(name, today, boat_data())
    ly = "En la misma semana de %d estaba al %s." % (f["date"].year - 1, pc(f["last_year"])) if f["last_year"] is not None else "No hay dato publicado de la misma semana del año anterior."
    if f["median"] is None:
        past = "<p>%s</p><p>Hay %d años anteriores con dato%s para esas fechas; hacen falta 10 para comparar.</p>" % (ly, f["years"], comparable_words(f))
    else:
        past = ("<p>%s</p><p>En esta misma semana de %d años anteriores con dato%s, el llenado osciló entre el %s y el %s. En %d de esos %d años había un porcentaje menor que el del %s.</p>"
                '<p class="sub">%sLa mediana es el valor central de esos años.</p>%s') % (
            ly, f["years"], comparable_words(f), pc(f["low"]), pc(f["high"]), f["below"], f["years"], day(f["date"]),
            "" if coarse(f) else "Habitual significa a menos de %d puntos de la mediana (criterio propio). " % NEAR_USUAL,
            table(("Misma semana, años anteriores", "Llenado"), (("Mínimo", pc(f["low"])), ("Mediana", pc(f["median"])), ("Máximo", pc(f["high"])))))
    body += section("es_anos", "La misma semana en otros años", past + capacity_note(f), updated)
    body += later_section(f, rows, today, updated)
    body += chart("es_grafico_1", "Último año", rows, f["date"] - datetime.timedelta(days=366), "%m/%Y", name, updated, f["capacity"])
    body += chart("es_grafico_10", "Últimos 10 años", rows, es_data.year_back(f["date"], 10), "%Y", name, updated, f["capacity"])
    body += month_section(f, rows, updated)
    last = [r for r in rows if r[0] <= today][-8:][::-1]
    body += section("es_historial", "Últimas semanas publicadas", "<p>Las %d últimas fechas del archivo, de la más reciente a la más antigua. Si un valor falta o no lo mostramos por incoherente (supera la capacidad en más de un 5 %%, o salta más de 25 puntos y vuelve a la semana siguiente), figura como Desconocido.</p>%s" % (
        len(last), table(("Fecha", "Llenado", "Volumen (hm³)", "Capacidad (hm³)"), [(short(d), pc(es_data.pct(c, v)), hm(v) if es_data.pct(c, v) is not None else "Desconocido", hm(c)) for d, c, v in last])), updated)
    body = head + body + related(name, basin, found) + '<p><a href="/es/">Ver todos los embalses de esta web</a></p>' + credit_block(updated)
    title = "%s (pantano): agua embalsada y llenado | dato semanal" % title_name
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
        say = "De %d embalses con dato reciente al preparar esta página, %d estaban más llenos de lo habitual para esas fechas, %d más vacíos y %d cerca de lo habitual%s. Último dato: %s." % (
            len(fresh), kinds.count("above"), kinds.count("below"), kinds.count("near"), "; %d sin comparación" % kinds.count(None) if None in kinds else "", day(newest))
    else:
        say = "No hay dato reciente: el último publicado es del %s, hace %d días." % (day(newest), (today - newest).days)
    body = ('<h1>Embalses de España: porcentaje de llenado</h1><p class="answer"><span>%s</span></p><p class="sub">Dato semanal. Es una selección de %d embalses, no el total de España. '
            'Habitual: a menos de %d puntos de la mediana de la misma semana en años anteriores (cálculo propio).</p>') % (say, len(found), NEAR_USUAL)
    word = {"above": "más lleno", "below": "más vacío", "near": "habitual", None: "sin comparación"}
    for i, basin in enumerate(sorted({x["basin"] for x in found.values()})):
        here = sorted((n for n, x in found.items() if x["basin"] == basin), key=slug)
        rows = [('<a href="%s">%s</a>' % (url_of(n), esc(display(n))), pc(found[n]["f"]["pct"]), "%s de %s" % (hm(found[n]["f"]["volume"]), hm(found[n]["f"]["capacity"])),
                 "dato antiguo: " + short(found[n]["f"]["date"]) if found[n]["f"]["stale"] else "%s (%s)" % (word[usual(found[n]["f"])], short(found[n]["f"]["date"]))) for n in here]
        recent = [found[n]["f"]["pct"] for n in here if not found[n]["f"]["stale"]]
        lead = "<p>Mediana de los %d embalses de esta lista con dato reciente: %s. No es el nivel de la cuenca.</p>" % (len(recent), pc(statistics.median(recent))) if len(recent) > 2 else ""
        body += section("cuenca_%d" % i, esc(basin), lead + table(("Embalse", "Llenado", "hm³", "Frente a lo habitual (fecha)"), rows), updated)
    desc = "Porcentaje de llenado y volumen embalsado de %d embalses de España, por cuenca, con dato semanal del %s. Fuente: MITECO." % (len(found), day(newest))
    return shell("Embalses de España: porcentaje de llenado por cuenca | dato semanal", desc, HUB, [("Inicio (en inglés)", "/"), ("Embalses de España", None)], body + credit_block(updated))


def checked(cache, today, check, has_old):
    """pages(), then the gate's one-page rules on each (build.py passes check.page_checks): a bad new page must never stop the release.
    A failing page with a live copy is left out here (build.py carries that copy). One with no live copy is rendered away, so no link points at it."""
    skip = set()
    while True:
        out, bad = pages(cache, today, skip)
        fail = {u: f for u, f in ((u, check(u, h)) for u, h in out.items()) if f}
        why = [(u, "; ".join(f)[:200]) for u, f in fail.items()]
        for u, w in why:
            print("SPAIN PAGE FAILED %s: %s" % (u, w))
        gone = {u for u in fail if not has_old(u)}
        if HUB in gone:  # every reservoir links the hub
            return {}, bad + why
        if not gone:
            return {u: h for u, h in out.items() if u not in fail}, bad + why
        skip |= gone


def short_report(s, today):
    """Why the Spain pages need a look, or "": data older than two missed weeks, or fewer than the 50 reservoirs and their hub built."""
    if not s.get("es_newest") or (today - datetime.date.fromisoformat(s["es_newest"])).days > es_data.STALE_DAYS:
        return "Spain reservoir data is old or missing (newest %s): see the 'Spain reservoirs' step log" % s.get("es_newest")
    return "" if s.get("es_pages") == 51 else "Spain: %s of 51 pages built" % s.get("es_pages")


def pages(cache, today, skip=()):
    """({url: html}, [(url, reason)]) from the cache object. A reservoir with no usable reading, or whose render raises, is left out and named."""
    data, basins = es_data.unpack(cache)
    try:
        modified = email.utils.parsedate_to_datetime(cache["modified"]).date()
    except (KeyError, TypeError, ValueError):
        modified = None
    updated = (modified, datetime.date.fromisoformat(cache["newest"]))  # (file date or None, newest reading)
    found, bad = {}, []
    for n in top_names():  # rank order: related() relies on it
        f = es_data.figures(data.get(n, []), today)
        if url_of(n) in skip:
            bad.append((url_of(n), "failed the page rules"))
        elif f:
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
