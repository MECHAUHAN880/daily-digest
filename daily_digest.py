import os
import requests
from datetime import datetime

# Configuration
TELEGRAM_BOT_TOKEN = "8805233054:AAHhDleg5SjHIismgXbsW-fCYN9791w1E2Y"
TELEGRAM_CHAT_ID = "6494109304"

def fetch_events():
    """
    Fetch events across multiple tiers.
    Can be expanded with Unstop scrapers, Devpost RSS, or Google Custom Search APIs.
    """
    today_str = datetime.now().strftime("%d %b %Y")
    
    # Structure categorized by geographic / organizational tier
    digest = f"📢 *Daily Competition & Event Digest — {today_str}*\n\n"
    
    # 1. International
    digest += "🌐 *International (Hackathons & Global MUNs)*\n"
    digest += "• *MIT Climate Hackathon* | Online | Deadline: Oct 15\n"
    digest += "• *Global Debate Open 2026* | Online / Discord | Registration Open\n\n"
    
    # 2. National (India)
    digest += "🇮🇳 *National Level (Debate, Quiz & Ideathons)*\n"
    digest += "• *Tata Crucible Campus Quiz* | Hybrid | National finals in Nov\n"
    digest += "• *National Youth Parliament Festival* | Ministry of Youth Affairs\n\n"
    
    # 3. State Level (Delhi, Haryana, UP)
    digest += "🏛️ *State Level (Delhi NCR / Haryana / UP)*\n"
    digest += "• *Delhi University Parliamentary Debate (DU PD)* | North Campus, Delhi\n"
    digest += "• *Haryana State Level Science Quiz & Debate* | MDU Rohtak / Kurukshetra\n"
    digest += "• *UP Tech Fest Hackathon & GD Round* | AKTU Lucknow\n\n"
    
    # 4. Block / District Level
    digest += "📍 *Block / District Level*\n"
    digest += "• *Gurugram Youth Forum Panel Discussion* | Civil Lines, Gurugram\n"
    digest += "• *District Inter-College Youth Festival* | Check local DIC / Nehru Yuva Kendra (NYKS)\n\n"
    
    digest += "🔗 *Curated Platforms to explore daily:* Unstop, Devpost, Devfolio, NYKS India."
    return digest

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    result = response.json()
    print("Telegram response:", result)
    if not result.get("ok"):
        raise SystemExit(f"Telegram error: {result.get('description')}")
    return result

if __name__ == "__main__":
    content = fetch_events()
    send_telegram_message(content)
