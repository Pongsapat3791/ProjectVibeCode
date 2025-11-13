# -*- coding: utf-8 -*-
import qrcode
from PIL import Image

def crc16(data: str) -> str:
    """
    คำนวณค่า CRC16-CCITT checksum สำหรับข้อมูลที่กำหนด
    มาตรฐานนี้จำเป็นสำหรับ QR Code ของ PromptPay เพื่อตรวจสอบความถูกต้องของข้อมูล
    """
    crc = 0xFFFF
    for byte in data.encode('ascii'):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
    return "{:04X}".format(crc & 0xFFFF)

def format_promptpay_id(recipient_id: str) -> str:
    """
    จัดรูปแบบเบอร์โทรศัพท์มือถือให้อยู่ในรูปแบบ PromptPay Standard (0066...)
    """
    if len(recipient_id) == 10 and recipient_id.startswith('0'):
        # แปลงเบอร์มือถือ 0xx-xxx-xxxx เป็น 0066xxxxxxxx
        return '0066' + recipient_id[1:]
    # หากเป็นเลขบัตรประชาชนหรือ e-Wallet ID ก็ใช้ค่าเดิม
    return recipient_id

def generate_promptpay_payload(recipient_id: str, amount: float = None) -> str:
    """
    สร้าง Payload string ตามมาตรฐาน EMVCo Merchant-Presented QR Code
    ซึ่งเป็นโครงสร้างข้อมูลที่แอปธนาคารใช้ในการอ่าน QR Code
    """
    # --- ส่วนประกอบของ Payload ---
    # Tag '00': Payload Format Indicator
    payload_format = "000201"
    
    # Tag '01': Point of Initiation Method ('11' สำหรับ QR แบบ static, '12' สำหรับ dynamic)
    # เราจะใช้ '11' สำหรับ QR ที่ใช้ซ้ำได้
    point_of_initiation = "010211"

    # Tag '29': Merchant Account Information (สำหรับ PromptPay)
    # ประกอบด้วย Sub-tag
    #   - '00': AID (Application Identifier) ของ PromptPay
    #   - '01': Biller ID (เบอร์โทรศัพท์/เลขบัตรประชาชน)
    promptpay_aid = "0016A000000677010111"
    formatted_id = format_promptpay_id(recipient_id)
    biller_id_tag = "01"
    biller_id_value = f"{len(formatted_id):02d}{formatted_id}"
    merchant_account_info_value = f"{promptpay_aid}{biller_id_tag}{biller_id_value}"
    merchant_account_info = f"29{len(merchant_account_info_value):02d}{merchant_account_info_value}"

    # Tag '53': Transaction Currency (THB คือ '764')
    currency_code = "5303764"

    # Tag '54': Transaction Amount
    transaction_amount = ""
    if amount:
        amount_str = f"{amount:.2f}"
        transaction_amount = f"54{len(amount_str):02d}{amount_str}"

    # Tag '58': Country Code ('TH' สำหรับประเทศไทย)
    country_code = "5802TH"
    
    # --- รวม Payload ทั้งหมด (ยกเว้น CRC) ---
    payload_data = "".join([
        payload_format,
        point_of_initiation,
        merchant_account_info,
        currency_code,
        transaction_amount,
        country_code
    ])

    # Tag '63': CRC (Checksum)
    # ต้องคำนวณจากข้อมูลทั้งหมดก่อนหน้านี้
    crc_tag = "6304"
    crc_value = crc16(payload_data + crc_tag)
    
    # --- Payload ที่สมบูรณ์ ---
    full_payload = payload_data + crc_tag + crc_value
    
    return full_payload

def generate_qr_code(payload: str, filename: str = "promptpay-qr.png"):
    """
    สร้างไฟล์รูปภาพ QR Code จาก Payload ที่กำหนด
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(payload)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(filename)
        print(f"✅ สร้าง QR Code สำเร็จ! บันทึกเป็นไฟล์ชื่อ '{filename}'")
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการสร้าง QR Code: {e}")


# --- ส่วนของการทำงานหลัก ---
if __name__ == "__main__":
    # --- ตัวอย่างการใช้งาน ---
    # 1. ระบุเบอร์ PromptPay หรือเลขบัตรประชาชน/Tax ID
    # ใส่เบอร์โทรศัพท์ 10 หลัก หรือเลขบัตรประชาชน 13 หลัก
    my_promptpay_id = "0812345678" 
    
    # 2. ระบุจำนวนเงินที่ต้องการ (ใส่เป็นทศนิยมได้)
    # หากไม่ต้องการระบุจำนวนเงิน ให้ใส่เป็น None หรือ 0
    # ถ้าไม่ระบุ ผู้สแกนจะต้องกรอกจำนวนเงินเอง
    payment_amount = 99.50

    # 3. ตั้งชื่อไฟล์รูปภาพ QR Code ที่จะบันทึก
    output_filename = "my-payment-qr.png"

    print("กำลังสร้าง QR Code สำหรับ PromptPay...")
    print(f"   - ผู้รับ: {my_promptpay_id}")
    print(f"   - จำนวนเงิน: {payment_amount if payment_amount else 'ไม่ระบุ'}")
    
    # สร้าง Payload
    payload = generate_promptpay_payload(my_promptpay_id, payment_amount)
    
    # สร้าง QR Code จาก Payload
    generate_qr_code(payload, output_filename)

