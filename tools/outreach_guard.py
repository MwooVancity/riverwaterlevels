"""One rule for outreach (owner 2026-11-13): an organisation is emailed once; after that only replies in its own thread.
python -I tools/outreach_guard.py <drafts.csv>   -> lists every draft row that would contact someone already contacted, exit 1 if any
python -I tools/outreach_guard.py --record <drafts.csv> <org name> [...]  -> after a send: stamps those rows into data/outreach.csv
A draft is blocked when its address (compared by sha256, so the public repo never holds full addresses), its address domain
or its website domain matches any row of data/outreach.csv that has sent_on. Free-mail domains (gmail.com...) match by address only.
A reply is not outreach: it goes in the existing email thread and is noted in that row's sent_via, never through this list."""
import csv, datetime, hashlib, os, sys
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "data", "outreach.csv")
FREE = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com", "comcast.net", "att.net", "msn.com", "live.com"}


def sha(addr):
    return hashlib.sha256(addr.strip().lower().encode()).hexdigest()[:16]


def dom(u):
    u = (u or "").strip().lower()
    if "@" in u:
        return u.rsplit("@", 1)[1]
    return (urlparse(u if "//" in u else "http://" + u).hostname or "").removeprefix("www.")


def sent_keys(rows):
    """Everything that identifies an organisation already contacted."""
    keys = set()
    for r in rows:
        if r.get("sent_on"):
            keys |= {("sha", r["email_sha"])} if r.get("email_sha") else set()
            keys |= {("dom", d) for d in (dom(r.get("website")), dom(r.get("contact_page_url"))) if d and d not in FREE}
            keys |= {("org", " ".join(r["org_name"].lower().split()))}
    return keys


def clashes(draft, keys):
    """Why this draft row would contact someone again ([] = it may go)."""
    why = []
    e = (draft.get("email") or "").strip()
    if "@" in e and ("sha", sha(e)) in keys:
        why.append("same address")
    for d in (dom(e) if "@" in e else "", dom(draft.get("website"))):
        if d and d not in FREE and ("dom", d) in keys:
            why.append("same domain " + d)
    if ("org", " ".join((draft.get("org_name") or "").lower().split())) in keys:
        why.append("same organisation name")
    return why


def selftest():
    log = [{"org_name": "Lake X Marina", "website": "https://www.lakexmarina.com/", "contact_page_url": "", "sent_on": "2026-11-12", "email_sha": sha("Info@LakeX.org")},
           {"org_name": "Guide Bob", "website": "", "contact_page_url": "", "sent_on": "2026-11-12", "email_sha": sha("bob@gmail.com")},
           {"org_name": "Not Sent Yet", "website": "https://notsent.com", "contact_page_url": "", "sent_on": ""}]
    k = sent_keys(log)
    assert clashes({"org_name": "Other", "email": " info@lakex.org ", "website": ""}, k), "same address in another case or with spaces not caught"
    assert clashes({"org_name": "Other", "email": "sales@lakexmarina.com", "website": ""}, k), "another address at a contacted domain not caught"
    assert clashes({"org_name": "lake x  MARINA", "email": "", "website": ""}, k), "same organisation by name not caught"
    assert not clashes({"org_name": "Sue Guide", "email": "sue@gmail.com", "website": ""}, k), "a free-mail domain blocked a different person"
    assert clashes({"org_name": "Bob", "email": "BOB@gmail.com", "website": ""}, k), "same free-mail address not caught"
    assert not clashes({"org_name": "New", "email": "a@notsent.com", "website": "https://notsent.com"}, k), "an org never sent to was blocked"
    print("outreach_guard selftest OK")


def main(a):
    if a[:1] == ["--selftest"]:
        return selftest()
    log = list(csv.DictReader(open(LOG, encoding="utf-8")))
    drafts = list(csv.DictReader(open(a[-1] if a[0] != "--record" else a[1], encoding="utf-8")))
    if a[0] == "--record":
        names, today = set(a[2:]), datetime.date.today().isoformat()
        cols = list(log[0].keys()) + (["email_sha"] if "email_sha" not in log[0] else [])
        for d in drafts:
            if d["org_name"] in names:
                why = clashes(d, sent_keys(log))
                assert not why, "%s already contacted: %s" % (d["org_name"], why)
                log.append({"lake": d.get("water", ""), "org_name": d["org_name"], "type": d.get("type", ""), "website": d.get("website", ""), "contact_page_url": d.get("form_url", ""),
                            "why_they_would_embed": d.get("why", "")[:200], "evidence_url": d.get("email_evidence_url", ""), "found_on": today, "sent_on": today,
                            "sent_via": "email %s@" % d["email"].split("@")[0][:3], "email_sha": sha(d["email"])})
        w = csv.DictWriter(open(LOG, "w", encoding="utf-8", newline=""), fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(log)
        return print("recorded", len(names))
    keys, bad = sent_keys(log), 0
    for d in drafts:
        why = clashes(d, keys)
        if why and "@" in (d.get("email") or ""):
            bad += 1
            print("BLOCKED", d["org_name"], "-", ", ".join(why))
    print("%d draft rows checked, %d blocked" % (len(drafts), bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1:])
