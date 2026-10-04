import re
import json
import html
import requests
from datetime import datetime, timezone

# Configuration
TELEGRAM_BOT_TOKEN = "8805233054:AAHhDleg5SjHIismgXbsW-fCYN9791w1E2Y"
TELEGRAM_CHAT_ID = "6494109304"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DailyDigestBot/1.0)",
    "Accept": "application/json",
}
MAX_PER_SECTION = 5

# Words used to pick out Delhi NCR / Haryana / UP events
REGION_WORDS = [
    "delhi", "ncr", "gurugram", "gurgaon", "noida", "faridabad", "ghaziabad",
    "haryana", "rohtak", "kurukshetra", "sonipat", "panipat", "hisar",
    "uttar pradesh", "lucknow", "kanpur", "agra", "varanasi", "prayagraj",
    "meerut", "aktu", "mdu", "amity",
]
DEBATE_WORDS = ["debate", "mun", "model united", "parliament", "youth parliament", "elocution", "panel"]


# ---------- helpers ----------
def esc(text):
    return html.escape(str(text or ""), quote=True)


def parse_date(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def fmt_date(dt):
    return dt.strftime("%d %b %Y") if dt else "Check page"


def strip_tags(text):
    return re.sub(r"<[^>]+>", "", str(text or "")).strip()


def get_json(url, params=None):
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=25)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[warn] fetch failed for {url}: {e}")
        return None


# ---------- sources ----------
def fetch_devpost():
    """International hackathons from Devpost's public JSON endpoint."""
    data = get_json(
        "https://devpost.com/api/hackathons",
        {"status[]": ["open", "upcoming"], "order_by": "deadline", "per_page": 30},
    )
    items = []
    for h in (data or {}).get("hackathons", []):
        loc = (h.get("displayed_location") or {}).get("location", "")
        themes = ", ".join(t.get("name", "") for t in (h.get("themes") or [])[:3])
        items.append({
            "title": h.get("title"),
            "url": h.get("url"),
            "org": h.get("organization_name"),
            "mode": loc,
            "deadline": h.get("submission_period_dates") or h.get("time_left_to_submission"),
            "prize": strip_tags(h.get("prize_amount")),
            "extra": themes,
            "raw_deadline_is_text": True,
        })
    return items


def fetch_unstop(opportunity, pages=2):
    """Indian opportunities from Unstop's public search endpoint."""
    items = []
    for page in range(1, pages + 1):
        data = get_json(
            "https://unstop.com/api/public/opportunity/search-result",
            {"opportunity": opportunity, "oppstatus": "open", "per_page": 30, "page": page},
        )
        if not data:
            break
        rows = data.get("data", {})
        rows = rows.get("data", []) if isinstance(rows, dict) else rows
        if not rows:
            break
        for o in rows:
            reg = o.get("regnRequirements") or {}
            deadline = parse_date(reg.get("end_regn_dt") or o.get("end_date"))
            if deadline and deadline < datetime.now(timezone.utc):
                continue
            url = o.get("public_url") or ""
            if url and not url.startswith("http"):
                url = "https://unstop.com/" + url.lstrip("/")
            if not url and o.get("seo_url"):
                url = "https://unstop.com/" + o["seo_url"].lstrip("/")
            prize = ""
            prizes = o.get("prizes") or []
            if prizes and isinstance(prizes, list) and isinstance(prizes[0], dict):
                prize = prizes[0].get("cash") or prizes[0].get("others") or ""
            items.append({
                "title": o.get("title"),
                "url": url,
                "org": (o.get("organisation") or {}).get("name"),
                "mode": o.get("region") or "",
                "deadline": deadline,
                "prize": str(prize) if prize else "",
                "extra": "",
                "blob": json.dumps(o, default=str).lower(),
                "type": opportunity,
            })
    return items


# ---------- formatting ----------
def sort_key(item):
    d = item.get("deadline")
    return d if isinstance(d, datetime) else datetime.max.replace(tzinfo=timezone.utc)


NUM = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
DIVIDER = "▬▬▬▬▬▬▬▬▬▬▬▬▬▬"


def clean_prize(item):
    p = str(item.get("prize") or "").strip()
    if not p:
        return ""
    digits = re.sub(r"[^\d]", "", p)
    if digits and int(digits) == 0:
        return ""
    if p.isdigit():
        return "₹" + f"{int(p):,}"
    return p


def days_left(dl):
    if not isinstance(dl, datetime):
        return ""
    n = (dl.date() - datetime.now(timezone.utc).date()).days
    if n <= 0:
        return " 🔥 <b>closes today</b>"
    if n == 1:
        return " 🔥 <b>1 day left</b>"
    if n <= 3:
        return f" ⚠️ <b>{n} days left</b>"
    return f" ({n} days left)"


def format_item(item, idx=0):
    title = esc(item.get("title") or "Untitled").strip()
    url = item.get("url")
    num = NUM[idx] if idx < len(NUM) else "▪️"
    head = f'{num} <b><a href="{esc(url)}">{title}</a></b>' if url else f"{num} <b>{title}</b>"

    lines = []
    if item.get("org"):
        lines.append(f"🏢 {esc(item['org'])}")

    when = []
    if item.get("mode"):
        mode = str(item["mode"]).strip().title()
        icon = "💻" if mode.lower() == "online" else "📍"
        when.append(f"{icon} {esc(mode)}")
    dl = item.get("deadline")
    if dl:
        if isinstance(dl, datetime):
            when.append(f"⏳ Closes <b>{esc(fmt_date(dl))}</b>{days_left(dl)}")
        else:
            when.append(f"🗓 {esc(dl)}")
    if when:
        lines.append("  •  ".join(when))

    prize = clean_prize(item)
    if prize:
        lines.append(f"🏆 {esc(prize)}")
    if item.get("extra"):
        lines.append(f"🏷 <i>{esc(item['extra'])}</i>")

    body = "\n".join(lines)
    return f"{head}\n<blockquote>{body}</blockquote>" if body else head


def section(title, items):
    items = items[:MAX_PER_SECTION]
    header = f"<b>{title}</b>\n{DIVIDER}"
    if not items:
        return f"{header}\n<i>No open listings today.</i>"
    body = "\n".join(format_item(i, n) for n, i in enumerate(items))
    return f"{header}\n{body}"


def build_digest():
    today = datetime.now().strftime("%A, %d %B %Y")
    seen = set()

    def unique(items):
        out = []
        for i in items:
            key = i.get("url") or i.get("title")
            if key and key not in seen:
                seen.add(key)
                out.append(i)
        return out

    devpost = fetch_devpost()
    hacks = sorted(fetch_unstop("hackathons"), key=sort_key)
    quizzes = sorted(fetch_unstop("quizzes"), key=sort_key)
    comps = sorted(fetch_unstop("competitions"), key=sort_key)
    confs = sorted(fetch_unstop("conferences"), key=sort_key)

    everything = hacks + quizzes + comps + confs
    regional = [i for i in everything if any(w in i["blob"] for w in REGION_WORDS)]
    regional = unique(sorted(regional, key=sort_key))

    debates = [i for i in comps if any(w in (i.get("title") or "").lower() for w in DEBATE_WORDS)]
    debates = unique(debates)

    parts = [
        f"✨ <b>DAILY EVENT DIGEST</b> ✨\n🗓 <i>{today}</i>\n<i>Hackathons • Quizzes • Debates • E-Summits</i>",
        section("🌐 INTERNATIONAL HACKATHONS", unique(devpost)),
        section("🏛 DELHI NCR • HARYANA • UP", regional),
        section("💻 NATIONAL HACKATHONS", unique(hacks)),
        section("🧠 NATIONAL QUIZZES", unique(quizzes)),
        section("🎤 DEBATES • MUN • PARLIAMENT", debates),
        section("🚀 E-SUMMITS &amp; CONFERENCES", unique(confs)),
        "<b>📍 LOCAL / BLOCK LEVEL</b>\n" + DIVIDER + "\n"
        "Check <a href=\"https://nyks.nic.in/\">NYKS</a> and your district youth office for local events.",
        "<b>🔗 EXPLORE MORE</b>\n" + DIVIDER + "\n"
        "<a href=\"https://unstop.com/\">Unstop</a>  •  <a href=\"https://devpost.com/hackathons\">Devpost</a>  •  <a href=\"https://devfolio.co/hackathons\">Devfolio</a>\n\n"
        "<i>Good luck, go win something! 🏅</i>",
    ]
    return parts


def chunk_messages(parts, limit=3800):
    messages, current = [], ""
    for p in parts:
        if len(current) + len(p) + 2 > limit and current:
            messages.append(current)
            current = ""
        current += ("\n\n" if current else "") + p
    if current:
        messages.append(current)
    return messages


# ---------- telegram ----------
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    response = requests.post(url, json=payload, timeout=25)
    result = response.json()
    print("Telegram response ok:", result.get("ok"))
    if not result.get("ok"):
        raise SystemExit(f"Telegram error: {result.get('description')}")
    return result


if __name__ == "__main__":
    for msg in chunk_messages(build_digest()):
        send_telegram_message(msg)
