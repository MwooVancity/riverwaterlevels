import re, sys, html, os, json
D = "C:/Users/mwoo7/Desktop/riverwaterlevels/runs/quarter/live/"


def text(f):
    h = open(D + f, encoding="utf-8").read()
    h = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", h, flags=re.S)
    h = re.sub(r"</(div|p|li|h\d|tr|section|summary|details)>", "\n", h)
    t = html.unescape(re.sub(r"<[^>]+>", " ", h))
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t]+", " ", t))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    fs = os.listdir(D)
    print(len(fs), [f for f in fs if "river_" not in f][:30])
    for f in sys.argv[1:]:
        print("=====", f)
        print(text(f)[:int(9000)])
