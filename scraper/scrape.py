#!/usr/bin/env python3
"""
Dohvaća sportski TV raspored za danas i iduća dva dana sa sporter.com.hr
i sprema ga u data/schedule.json, koji čita index.html.

Pokretanje lokalno:
    pip install requests beautifulsoup4
    python scraper/scrape.py

Ako dohvat današnjeg rasporeda ne uspije, stari podaci ostaju netaknuti,
a skripta završava s greškom (GitHub ti tada pošalje mail).
"""
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

BASE = "https://sporter.com.hr/prijenos-uzivo/"
SLUGS = ["pon", "uto", "sri", "cet", "pet", "sub", "ned"]  # ponedjeljak = 0
DAYS_AHEAD = 3
OUT = Path(__file__).resolve().parent.parent / "data" / "schedule.json"
HEADERS = {
    "User-Agent": "SportNaTV/1.0 (osobni projekt, dohvat dvaput dnevno)",
    "Accept-Language": "hr,en;q=0.5",
}
MONTHS = {"sij": 1, "velj": 2, "ožu": 3, "tra": 4, "svi": 5, "lip": 6,
          "srp": 7, "kol": 8, "ruj": 9, "lis": 10, "stu": 11, "pro": 12}

# Redoslijed je bitan: "američki nogomet" mora pasti u "ostalo" prije provjere za "nogomet".
SPORT_RULES = [
    ("američki", "ostalo"), ("futsal", "ostalo"),
    ("nogomet", "nogomet"), ("košark", "kosarka"), ("rukomet", "rukomet"),
    ("tenis", "tenis"), ("hokej", "hokej"), ("vaterpolo", "vaterpolo"),
    ("odbojk", "odbojka"), ("motošport", "motosport"), ("formula", "motosport"),
    ("mma", "borbe"), ("boks", "borbe"), ("ufc", "borbe"),
]

DAY_HEADER = re.compile(r"(\d{1,2})\.\s*([a-zčćžšđ]+)\s*\|", re.I)
TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")


def sport_id(text: str) -> str:
    t = text.lower()
    for key, sid in SPORT_RULES:
        if key in t:
            return sid
    return "ostalo"


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def title_from_desc(d: str) -> str:
    d = clean(d)
    if " | " in d:
        d = d.split(" | ")[0]
    elif ":" in d:
        d = d.rsplit(":", 1)[1]
    d = d.split(", ")[0].strip()
    return re.sub(r"\s+-\s+", " – ", d)


def finish(ev: dict) -> dict | None:
    if not ev or not ev["ch"]:
        return None
    title = title_from_desc(ev["desc"]) if ev["desc"] else ""
    if (not title or len(title) > 70) and len(ev["teams"]) >= 2:
        title = " – ".join(ev["teams"][:2])
    if not title:
        title = ev["h6"] or ev["comp"] or "Prijenos"
    t = ev["t"].zfill(5)
    return {
        "t": t,
        "s": ev["s"],
        "title": title,
        "comp": ev["comp"] or "",
        "cro": ", ".join(dict.fromkeys(ev["cro"])),
        "ch": list(dict.fromkeys(ev["ch"])),
    }


def parse(html: str, day: dt.date) -> list | None:
    """Vraća listu prijenosa ili None ako stranica nije za traženi dan."""
    soup = BeautifulSoup(html, "html.parser")
    started = False
    date_ok = False
    sport, comp = "ostalo", ""
    cur = None
    events = []

    for node in soup.body.descendants if soup.body else []:
        if isinstance(node, NavigableString):
            if started:
                txt = node.strip()
                if TIME_RE.match(txt) and node.parent.name not in ("i", "em", "b", "strong"):
                    done = finish(cur)
                    if done:
                        events.append(done)
                    cur = {"t": txt, "s": sport, "comp": comp, "teams": [], "cro": [],
                           "desc": "", "h6": "", "ch": []}
            continue
        if not isinstance(node, Tag):
            continue

        name = node.name
        if name == "h2":
            m = DAY_HEADER.search(node.get_text(" ", strip=True))
            if m:
                started = True
                d, mon = int(m.group(1)), MONTHS.get(m.group(2).lower().rstrip("."))
                date_ok = (d == day.day and mon == day.month)
            continue
        if not started:
            continue
        if name == "h3":
            text = clean(node.get_text(" ", strip=True))
            if "adblock" in text.lower():
                break
            done = finish(cur)
            if done:
                events.append(done)
            cur = None
            sport, comp = sport_id(text), ""
        elif name == "img":
            src = node.get("src", "")
            alt = clean(node.get("alt", ""))
            title = clean(node.get("title", ""))
            if "liga-uzivo-tv" in src:
                comp = alt or title
                if cur is not None and not cur["ch"]:
                    cur["comp"] = comp
            elif cur is not None and title.lower().startswith("uživo na"):
                cur["ch"].append(clean(title[8:]))
            elif cur is not None and "momcad" in src and alt:
                cur["teams"].append(alt)
        elif cur is not None and name in ("i", "em"):
            text = clean(node.get_text(" ", strip=True))
            if len(text) > 3:
                cur["desc"] = text
        elif cur is not None and name in ("b", "strong") and not cur["ch"]:
            text = clean(node.get_text(" ", strip=True))
            if text and not TIME_RE.match(text) and len(text) < 80:
                cur["cro"].append(text)
        elif cur is not None and name == "h6":
            cur["h6"] = clean(node.get_text(" ", strip=True))

    done = finish(cur)
    if done:
        events.append(done)

    if not date_ok:
        return None
    seen, unique = set(), []
    for e in events:
        key = (e["t"], e["title"], tuple(e["ch"]))
        if key not in seen:
            seen.add(key)
            unique.append(e)
    unique.sort(key=lambda e: e["t"])
    return unique


def fetch(url: str) -> str:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    r.encoding = r.encoding or "utf-8"
    return r.text


def main() -> int:
    today = dt.datetime.now(ZoneInfo("Europe/Zagreb")).date()
    days = []
    for i in range(DAYS_AHEAD):
        day = today + dt.timedelta(days=i)
        url = BASE + SLUGS[day.weekday()]
        try:
            events = parse(fetch(url), day)
        except Exception as exc:  # mreža, promjena stranice...
            print(f"{day}: greška pri dohvatu {url}: {exc}")
            continue
        if events is None:
            print(f"{day}: stranica {url} nije za ovaj datum, preskačem.")
            continue
        print(f"{day}: {len(events)} prijenosa")
        days.append({"date": day.isoformat(), "events": events})
        time.sleep(3)

    if not days or days[0]["date"] != today.isoformat() or not days[0]["events"]:
        print("Nisam dobio današnji raspored. Stari podaci ostaju.")
        return 1

    data = {
        "generated": dt.datetime.now(ZoneInfo("Europe/Zagreb")).isoformat(timespec="minutes"),
        "source": "https://sporter.com.hr/",
        "days": days,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Spremljeno u {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
