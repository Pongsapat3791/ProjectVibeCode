import requests
import xml.etree.ElementTree as ET
import sys
import os
import json
import time
from dotenv import load_dotenv

load_dotenv()

try:
    config_str = os.getenv("DISCORD_CONFIGS", "[]")
    WEBHOOK_CONFIGS = json.loads(config_str)
except json.JSONDecodeError as e:
    print(f"❌ Error parsing DISCORD_CONFIGS in .env: {e}")
    WEBHOOK_CONFIGS = []

MAGNITUDE_THRESHOLD = float(os.getenv("MAGNITUDE_THRESHOLD", 5.0))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", 60))

DATA_URL = "https://earthquake.tmd.go.th/feed/rss_tmd.xml"
JSON_FILE_PATH = "latest_earthquake_link.json"

def load_latest_seen_link(filepath):
    if not os.path.exists(filepath):
        print(f"ไม่พบไฟล์ {filepath} (ถือเป็นการรันครั้งแรก)")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("latest_link") 
    except (json.JSONDecodeError, IOError, TypeError) as e:
        print(f"เกิดข้อผิดพลาดในการอ่าน {filepath}: {e} - เริ่มต้นใหม่")
        return None

def save_latest_seen_link(filepath, link):
    try:
        data_to_save = {"latest_link": link}
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        print(f"บันทึก Link ล่าสุด ({link}) ลง {filepath} สำเร็จ")
    except IOError as e:
        print(f"เกิดข้อผิดพลาดในการบันทึก {filepath}: {e}")

def get_safe_text(element, default="N/A"):
    if element is None:
        return default
    text = (element.text or "").strip()
    return text if text else default

def check_latest_earthquake(force_send=False):
    last_seen_link = load_latest_seen_link(JSON_FILE_PATH)
    print(f"Link ล่าสุดที่เคยเห็น (จาก JSON): {last_seen_link or 'ยังไม่มี'}")
    
    try:
        print(f"กำลังตรวจสอบข้อมูลแผ่นดินไหวล่าสุดจาก TMD...")
        response = requests.get(DATA_URL, timeout=10)
        response.raise_for_status() 

        root = ET.fromstring(response.content)
        items_from_feed = root.findall('.//item')
        
        if not items_from_feed:
            print("ไม่พบข้อมูลแผ่นดินไหวในฟีด")
            return

        latest_item = items_from_feed[0] 
        current_latest_link = (latest_item.find('link').text or "#").strip()
        
        if current_latest_link == "#":
            print("ไม่พบ Link ในรายการล่าสุด, ข้ามการตรวจสอบ")
            return

        print(f"Link ล่าสุดที่พบใน Feed: {current_latest_link}")

        if current_latest_link == last_seen_link and not force_send:
            print("เป็นรายการเดียวกับที่เคยเห็นล่าสุด ไม่ต้องทำอะไร")
            return

        if force_send:
            print(f"[FORCE SEND] บังคับส่งข้อมูลล่าสุด...")
        else:
            print(f"พบรายการใหม่! กำลังประมวลผล...")
        
        try:
            title = get_safe_text(latest_item.find('title'))
            comments = get_safe_text(latest_item.find('comments'))
            pubDate = get_safe_text(latest_item.find('pubDate'))

            lat = get_safe_text(latest_item.find('{*}lat'))
            long = get_safe_text(latest_item.find('{*}long'))
            depth = get_safe_text(latest_item.find('{*}depth'))
            event_time = get_safe_text(latest_item.find('{*}time'))
            magnitude_str = get_safe_text(latest_item.find('{*}magnitude'), default="0.0") 

            if not magnitude_str: magnitude_str = "0.0"
            magnitude = float(magnitude_str)

            image_url = None
            if "earthquake=" in current_latest_link:
                try:
                    eq_id = current_latest_link.split("earthquake=")[-1].split("&")[0]
                    if eq_id.isdigit():
                        image_url = f"https://earthquake.tmd.go.th/images/png/{eq_id}.png"
                except Exception:
                    pass

            print(f"รายการใหม่: {title} (Magnitude: {magnitude})")

            should_mention = (magnitude >= MAGNITUDE_THRESHOLD)
            
            send_discord_alert_multiple(title, current_latest_link, lat, long, depth, magnitude_str, event_time, comments, pubDate, should_mention, image_url)
            
            save_latest_seen_link(JSON_FILE_PATH, current_latest_link)
        
        except Exception as e:
            print(f"เกิดข้อผิดพลาดระหว่างประมวลผล item ล่าสุด: {e}")

    except Exception as e:
        print(f"เกิดข้อผิดพลาดทั่วไป: {e}")

def send_discord_alert_multiple(title, link, lat, long, depth, magnitude, event_time, comments, pubDate, should_mention: bool, image_url=None):
    """
    ส่ง Embed ไปยัง 'ทุก Webhook' ที่ตั้งค่าไว้ใน WEBHOOK_CONFIGS
    """
    if not WEBHOOK_CONFIGS:
        print("⚠️ ไม่มี Webhook Config ที่ถูกต้องให้ส่ง")
        return

    embed_color = 16711680 if should_mention else 3447003 # แดง หรือ ฟ้า
    embed_title_prefix = "🚨" if should_mention else "ℹ️"
    
    embed = {
        "title": f"{embed_title_prefix} {title}",
        "url": link,
        "description": f"**{comments}**",
        "color": embed_color,
        "fields": [
            { "name": "ขนาด (Magnitude)", "value": f"**{magnitude}**", "inline": True },
            { "name": "ความลึก (Depth)", "value": f"{depth} กม.", "inline": True },
            { "name": "พิกัด (Lat, Long)", "value": f"`{lat}, {long}`", "inline": True },
            { "name": "เวลาเกิดเหตุ (UTC)", "value": event_time, "inline": False },
        ],
        "footer": { "text": f"Source: TMD | เผยแพร่: {pubDate}" }
    }
    if image_url:
        embed["image"] = { "url": image_url }

    for i, config in enumerate(WEBHOOK_CONFIGS):
        webhook_url = config.get("url")
        role_id = config.get("role_id")

        if not webhook_url:
            continue

        message_content = ""
        if should_mention and role_id:
            message_content = f"‼️ **แจ้งเตือนแผ่นดินไหวรุนแรง** <@&{role_id}>"
        elif should_mention:
            message_content = f"‼️ **แจ้งเตือนแผ่นดินไหวรุนแรง** (No Role ID)"
        
        payload = { "content": message_content, "embeds": [embed] }

        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            print(f"✅ ส่งสำเร็จ [{i+1}]: Webhook ปลายทาง (Role: {role_id or 'None'})")
        except requests.RequestException as e:
            print(f"❌ ส่งล้มเหลว [{i+1}]: {e}")


if __name__ == "__main__":
    print(f"--- 🤖 บอทแจ้งเตือนแผ่นดินไหว (Multi-Webhook) ---")
    
    if not WEBHOOK_CONFIGS:
        print("="*50)
        print("‼️ **ข้อผิดพลาด:** ไม่พบการตั้งค่า DISCORD_CONFIGS ใน .env หรือรูปแบบ JSON ผิด")
        print("ตัวอย่างใน .env: DISCORD_CONFIGS='[{\"url\":\"...\",\"role_id\":\"...\"}]'")
        print("="*50)
        sys.exit(1)
    else:
        print(f"โหลด Webhook ได้จำนวน: {len(WEBHOOK_CONFIGS)} รายการ")

    print(f"--- 1. Startup Send Check ---")
    check_latest_earthquake(force_send=True)

    print(f"--- 2. Loop Start ({POLL_INTERVAL_SECONDS}s) ---")
    try:
        while True:
            check_latest_earthquake(force_send=False)
            print(f"--- รอ {POLL_INTERVAL_SECONDS} วินาที ---")
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nStop.")