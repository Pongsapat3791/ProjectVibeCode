import requests
import xml.etree.ElementTree as ET
import sys
import os
import json
import time
from dotenv import load_dotenv

load_dotenv()

# --- Configs ---
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
FASTAPI_DATA_PATH = "forfastapi.json"

def load_latest_seen_data(filepath):
    """
    โหลดข้อมูลล่าสุดที่เคยบันทึกไว้ (Link และ Magnitude)
    """
    if not os.path.exists(filepath):
        print(f"ไม่พบไฟล์ {filepath} (ถือเป็นการรันครั้งแรก)")
        return {"latest_link": None, "magnitude": 0.0}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # รองรับความเข้ากันได้กับไฟล์เวอร์ชันเก่าที่มีแค่ latest_link
            return {
                "latest_link": data.get("latest_link"),
                "magnitude": data.get("magnitude", 0.0)
            }
    except (json.JSONDecodeError, IOError, TypeError) as e:
        print(f"เกิดข้อผิดพลาดในการอ่าน {filepath}: {e} - เริ่มต้นใหม่")
        return {"latest_link": None, "magnitude": 0.0}

def save_latest_seen_data(filepath, link, magnitude):
    """
    บันทึกสถานะล่าสุด (Link และ Magnitude) เพื่อใช้เปรียบเทียบครั้งต่อไป
    """
    try:
        data_to_save = {"latest_link": link, "magnitude": magnitude}
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)
        print(f"บันทึกสถานะล่าสุดลง {filepath} สำเร็จ (Link: {link}, Mag: {magnitude})")
    except IOError as e:
        print(f"เกิดข้อผิดพลาดในการบันทึก {filepath}: {e}")

def save_data_for_fastapi(data):
    """บันทึกข้อมูลสำหรับ FastAPI"""
    try:
        with open(FASTAPI_DATA_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 [API] อัปเดตข้อมูลใน {FASTAPI_DATA_PATH} เรียบร้อยแล้ว")
    except IOError as e:
        print(f"❌ ไม่สามารถบันทึกข้อมูลสำหรับ API ได้: {e}")

def get_safe_text(element, default="N/A"):
    if element is None:
        return default
    text = (element.text or "").strip()
    return text if text else default

def check_latest_earthquake(force_send=False):
    # โหลดค่าเก่ามาเปรียบเทียบ (Link และ Magnitude)
    last_data = load_latest_seen_data(JSON_FILE_PATH)
    last_seen_link = last_data.get("latest_link")
    last_seen_mag = last_data.get("magnitude", 0.0)
    
    try:
        # print(f"กำลังตรวจสอบข้อมูลแผ่นดินไหวล่าสุดจาก TMD...")
        response = requests.get(DATA_URL, timeout=10)
        response.raise_for_status() 

        root = ET.fromstring(response.content)
        items_from_feed = root.findall('.//item')
        
        if not items_from_feed:
            print("ไม่พบข้อมูลแผ่นดินไหวในฟีด")
            return

        latest_item = items_from_feed[0] 
        current_link = (latest_item.find('link').text or "#").strip()
        
        if current_link == "#":
            return

        # --- ดึงข้อมูลรายละเอียด ---
        title = get_safe_text(latest_item.find('title'))
        comments = get_safe_text(latest_item.find('comments'))
        pubDate = get_safe_text(latest_item.find('pubDate'))
        lat = get_safe_text(latest_item.find('{*}lat'))
        long = get_safe_text(latest_item.find('{*}long'))
        depth = get_safe_text(latest_item.find('{*}depth'))
        event_time = get_safe_text(latest_item.find('{*}time'))
        magnitude_str = get_safe_text(latest_item.find('{*}magnitude'), default="0.0") 
        if not magnitude_str: magnitude_str = "0.0"
        current_magnitude = float(magnitude_str)

        image_url = None
        if "earthquake=" in current_link:
            try:
                eq_id = current_link.split("earthquake=")[-1].split("&")[0]
                if eq_id.isdigit():
                    image_url = f"https://earthquake.tmd.go.th/images/png/{eq_id}.png"
            except Exception:
                pass

        # เตรียมข้อมูล Object สำหรับ FastAPI และ Discord
        earthquake_data = {
            "title": title,
            "link": current_link,
            "description": comments,
            "magnitude": current_magnitude,
            "depth": depth,
            "lat": lat,
            "long": long,
            "time_utc": event_time,
            "pub_date": pubDate,
            "image_url": image_url,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # --- Logic ตรวจสอบการเปลี่ยนแปลง (Link หรือ Magnitude) ---
        is_new_link = (current_link != last_seen_link)
        is_mag_changed = (abs(current_magnitude - last_seen_mag) > 0.01) # เปรียบเทียบ Float

        if not is_new_link and not is_mag_changed and not force_send:
            # ถ้า Link เดิม และ Magnitude เท่าเดิม -> ไม่ทำอะไร
            return

        # ถ้ามีการเปลี่ยนแปลง หรือ บังคับส่ง
        update_reason = ""
        if force_send:
            update_reason = "[FORCE START]"
        elif is_new_link:
            update_reason = "พบรายการใหม่ (New Link)"
        elif is_mag_changed:
            update_reason = f"ข้อมูลมีการอัปเดต (Magnitude เปลี่ยนจาก {last_seen_mag} -> {current_magnitude})"

        print(f"🔔 {update_reason} - กำลังประมวลผล...")

        # 1. อัปเดตไฟล์สำหรับ FastAPI (สำคัญ: ทำทันทีที่มีการเปลี่ยนแปลง)
        save_data_for_fastapi(earthquake_data)

        # 2. ส่งแจ้งเตือน Discord
        try:
            should_mention = (current_magnitude >= MAGNITUDE_THRESHOLD)
            # ส่ง flag is_update ไปด้วยเพื่อให้รู้ว่าเป็นการแก้ไขข้อมูล
            send_discord_alert_multiple(earthquake_data, should_mention, is_update=(not is_new_link and is_mag_changed))
            
            # 3. บันทึกสถานะล่าสุดลงไฟล์ (Link และ Magnitude)
            save_latest_seen_data(JSON_FILE_PATH, current_link, current_magnitude)
        
        except Exception as e:
            print(f"เกิดข้อผิดพลาดระหว่างประมวลผล item ล่าสุด: {e}")

    except Exception as e:
        print(f"เกิดข้อผิดพลาดทั่วไป: {e}")

def send_discord_alert_multiple(data, should_mention: bool, is_update: bool = False):
    if not WEBHOOK_CONFIGS:
        return

    # ถ้าเป็นการอัปเดตข้อมูล (Link เดิมแต่แก้ Magnitude) ให้ใช้สีส้ม
    if is_update:
        embed_color = 16753920 # สีส้ม (Orange)
        embed_title_prefix = "⚠️ อัปเดตข้อมูล:"
    else:
        embed_color = 16711680 if should_mention else 3447003 # แดง หรือ ฟ้า
        embed_title_prefix = "🚨" if should_mention else "ℹ️"
    
    embed = {
        "title": f"{embed_title_prefix} {data['title']}",
        "url": data['link'],
        "description": f"**{data['description']}**",
        "color": embed_color,
        "fields": [
            { "name": "ขนาด (Magnitude)", "value": f"**{data['magnitude']}**", "inline": True },
            { "name": "ความลึก (Depth)", "value": f"{data['depth']} กม.", "inline": True },
            { "name": "พิกัด (Lat, Long)", "value": f"`{data['lat']}, {data['long']}`", "inline": True },
            { "name": "เวลาเกิดเหตุ (UTC)", "value": data['time_utc'], "inline": False },
        ],
        "footer": { "text": f"Source: TMD | เผยแพร่: {data['pub_date']}" }
    }
    if data['image_url']:
        embed["image"] = { "url": data['image_url'] }

    for i, config in enumerate(WEBHOOK_CONFIGS):
        webhook_url = config.get("url")
        role_id = config.get("role_id")

        if not webhook_url:
            continue

        message_content = ""
        # ถ้าเป็นการ Update อาจจะไม่ต้อง Tag Everyone ซ้ำก็ได้ หรือจะ Tag ก็ได้ตามต้องการ
        # ในที่นี้ตั้งให้ Tag เหมือนเดิมถ้าขนาดเกินเกณฑ์
        if should_mention and role_id:
            message_content = f"‼️ **แจ้งเตือนแผ่นดินไหวรุนแรง** <@&{role_id}>"
        elif should_mention:
            message_content = f"‼️ **แจ้งเตือนแผ่นดินไหวรุนแรง**"
        
        if is_update:
            message_content += " (มีการปรับปรุงข้อมูล)"

        payload = { "content": message_content, "embeds": [embed] }

        try:
            requests.post(webhook_url, json=payload, timeout=10)
            print(f"✅ ส่ง Discord สำเร็จ [{i+1}]")
        except requests.RequestException as e:
            print(f"❌ ส่ง Discord ล้มเหลว [{i+1}]: {e}")

if __name__ == "__main__":
    print(f"--- 🤖 บอทแจ้งเตือนแผ่นดินไหว (Smart Update) ---")
    
    print(f"--- 1. Startup Check ---")
    check_latest_earthquake(force_send=True)

    print(f"--- 2. Loop Start ({POLL_INTERVAL_SECONDS}s) ---")
    try:
        while True:
            check_latest_earthquake(force_send=False)
            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nStop.")