Earthquake Monitor & API Server 🤖🌋

ระบบติดตามรายงานแผ่นดินไหวจาก กรมอุตุนิยมวิทยา (TMD) แบบ Real-time ที่มาพร้อมกับ 2 ฟังก์ชันหลักทำงานร่วมกัน:

Discord Bot Notification: แจ้งเตือนเหตุการณ์แผ่นดินไหวเข้า Discord Server ทันที

Private FastAPI Server: ให้บริการ API ส่วนตัวสำหรับส่งต่อข้อมูลไปยัง Device อื่นๆ (เช่น Smart Home, มือถือ, เว็บไซต์ส่วนตัว)

✨ คุณสมบัติ (Features)

📡 Real-time Monitoring: ตรวจสอบข้อมูลจาก Feed ของกรมอุตุฯ ทุกๆ 60 วินาที (ตั้งค่าได้)

🧠 Smart Update:

แจ้งเตือนเมื่อมีเหตุการณ์ ใหม่

แจ้งเตือนเมื่อเหตุการณ์เดิมมีการ แก้ไขความรุนแรง (Magnitude)

📢 Advanced Discord Alerts:

แยกสีแถบสถานะตามความรุนแรง (และสีส้มสำหรับการแก้ไขข้อมูล)

รองรับการ Mention (Tag) เรียกคนเฉพาะเมื่อความรุนแรงเกินกำหนด

ส่งได้หลาย Webhook พร้อมกัน

🔐 Secured API:

มี Server สำหรับปล่อยข้อมูล JSON ให้ Device อื่น

ป้องกันการเข้าถึงด้วย API Key (Header: X-API-Key)

💾 Offline Persistence: บันทึกข้อมูลล่าสุดลงไฟล์ JSON ภายในเครื่อง ทำให้ API Server ยังตอบข้อมูลล่าสุดได้เสมอแม้เน็ตจะหลุดชั่วคราว

⚙️ การติดตั้ง (Installation)

Clone หรือดาวน์โหลดโปรเจกต์นี้

ติดตั้ง Python 3.x (หากยังไม่มี)

ติดตั้ง Dependencies โดยเปิด Terminal/Command Prompt แล้วรัน:

pip install -r requirements.txt


📝 การตั้งค่า (Configuration)

ให้สร้างไฟล์ชื่อ .env ไว้ในโฟลเดอร์เดียวกันกับโค้ด แล้วใส่ค่าตั้งค่าดังนี้:

# 1. การตั้งค่า Discord Webhook (รูปแบบ JSON List)
# ใส่ได้หลาย Webhook, role_id คือ ID ของยศที่จะให้ Tag (ถ้าไม่ใส่ให้ปล่อยว่าง "")
DISCORD_CONFIGS='[
  {
    "url": "[https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_1](https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_1)",
    "role_id": "123456789012345678"
  },
  {
    "url": "[https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_2](https://discord.com/api/webhooks/YOUR_WEBHOOK_URL_2)",
    "role_id": ""
  }
]'

# 2. การตั้งค่าบอท
MAGNITUDE_THRESHOLD=5.0   # ความแรงขั้นต่ำที่จะให้ Tag เรียกคน (Mention)
POLL_INTERVAL_SECONDS=60  # ความถี่ในการตรวจสอบข้อมูล (วินาที)

# 3. ความปลอดภัยของ API
# รหัสผ่านที่ Device อื่นต้องใช้แนบมาใน Header เพื่อขอข้อมูล
MY_API_KEY=secret_password_1234


🚀 การเริ่มระบบ (Running)

ระบบนี้ประกอบด้วย 2 ส่วนที่ทำงานแยกกัน คุณต้องเปิด Terminal 2 หน้าต่าง:

หน้าต่างที่ 1: รันตัวดึงข้อมูล (Fetch & Alert)

ทำหน้าที่ดึงข้อมูลจาก TMD, แจ้งเตือน Discord และเขียนไฟล์ข้อมูล

python app.py


หน้าต่างที่ 2: รัน API Server

ทำหน้าที่เปิดประตูให้ Device อื่นเข้ามาดึงข้อมูล

python fastapi_server.py


Server จะเริ่มทำงานที่ Port 8000

🔌 การใช้งาน API (API Usage)

Device ภายนอกสามารถดึงข้อมูลแผ่นดินไหวล่าสุดได้โดยยิง Request มาที่เครื่องที่รัน Server นี้

URL: http://<IP_ADDRESS_OF_SERVER>:8000/latest

Method: GET

Headers:

X-API-Key: (ค่าเดียวกับ MY_API_KEY ในไฟล์ .env)

ตัวอย่าง Code (Python Client)

import requests

# เปลี่ยน localhost เป็น IP ของเครื่อง Server ถ้ารันคนละเครื่อง
url = "http://localhost:8000/latest"
headers = {
    "X-API-Key": "secret_password_1234"
}

try:
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        print(f"แผ่นดินไหวล่าสุด: {data['title']}")
        print(f"ความแรง: {data['magnitude']}")
    else:
        print("เข้าถึงไม่ได้ (API Key ผิดหรือ Server มีปัญหา)")
except Exception as e:
    print(f"เชื่อมต่อไม่ได้: {e}")


❓ การแก้ปัญหาเบื้องต้น (Troubleshooting)

API ตอบกลับว่า Data file not found:

ให้รัน app.py ก่อนอย่างน้อย 1 รอบ เพื่อให้ระบบดึงข้อมูลจาก TMD มาสร้างไฟล์ forfastapi.json

หา Role ID ใน Discord ไม่เจอ:

ไปที่ User Settings > Advanced > เปิด Developer Mode

กลับไปที่ Server Settings > Roles > คลิกขวาที่ยศที่ต้องการ > Copy ID

ภาษาต่างดาวใน Console:

ตรวจสอบว่าไฟล์ .env ของคุณบันทึกเป็น encoding UTF-8