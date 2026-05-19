import json
import os
import pandas as pd

def convert_json_to_excel():
    # 1. ระบุชื่อไฟล์ Output และทำการค้นหาไฟล์ข้อมูล Input อัตโนมัติ
    output_file = "riftbound_cards_notebooklm.xlsx"
    
    # ค้นหาไฟล์ *_clean.json ทั้งหมดเพื่อโหลดข้อมูลการ์ดรวมทุกชุดแบบอัตโนมัติ
    clean_files = [f for f in os.listdir(".") if f.endswith("_clean.json")]
    
    cards_data = []
    
    if clean_files:
        print(f"🔍 พบไฟล์การ์ดที่คลีนแล้วจำนวน {len(clean_files)} ไฟล์ ในโฟลเดอร์ปัจจุบัน:")
        for clean_file in sorted(clean_files):
            print(f"📖 กำลังอ่านข้อมูลจากไฟล์ {clean_file}...")
            with open(clean_file, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    if isinstance(data, list):
                        cards_data.extend(data)
                    else:
                        print(f"⚠️ รูปแบบข้อมูลใน {clean_file} ไม่ถูกต้อง ข้าม...")
                except Exception as e:
                    print(f"⚠️ เกิดข้อผิดพลาดในการโหลดไฟล์ {clean_file}: {e}")
    else:
        # Fallback: ตรวจสอบไฟล์เดี่ยว riftbound_clean_dataset.json เผื่อผู้ใช้มีอยู่แล้ว
        fallback_file = "riftbound_clean_dataset.json"
        if os.path.exists(fallback_file):
            print(f"📖 กำลังอ่านข้อมูลจากไฟล์ {fallback_file}...")
            with open(fallback_file, 'r', encoding='utf-8') as f:
                cards_data = json.load(f)
        else:
            print("❌ ไม่พบไฟล์การ์ดที่คลีนแล้ว (*_clean.json) หรือไฟล์รวม (riftbound_clean_dataset.json) ในโฟลเดอร์ปัจจุบัน")
            print("💡 กรุณารันคำสั่ง `python data_card.py` เพื่อแปลงและจัดเตรียมข้อมูลการ์ดก่อนครับ")
            return

    # 2. แตกข้อมูลและจัดระเบียบฟิลด์ให้เป็นตารางที่สะอาดสำหรับ NotebookLM
    rows = []
    for card in cards_data:
        # ดึงข้อมูลโดยใส่ค่า Default ไว้เผื่อบางฟิลด์เป็น null หรือไม่มีค่า
        card_id = card.get("id", "N/A")
        name = card.get("name", "Unknown")
        card_type = card.get("cardType", "Unknown")
        
        # จัดการเรื่อง Domain (ถ้ามาเป็น List ให้ยุบรวมเป็นข้อความคั่นด้วยจุลภาค)
        domain = card.get("domain", "Unknown")
        if isinstance(domain, list):
            domain = ", ".join(domain)
            
        energy_cost = card.get("energyCost", 0)
        power_cost = card.get("powerCost", 0)
        might = card.get("might", 0)
        description = card.get("description", "")
        flavor_text = card.get("flavorText", "")
        rarity = card.get("rarity", "Standard")

        # มัดรวมก้อนแถวข้อมูล
        row = {
            "Card ID": card_id,
            "Card Name": name,
            "Type": card_type,
            "Domain (Faction/Color)": domain,
            "Energy Cost": energy_cost,
            "Power Cost": power_cost,
            "Might (Power)": might,
            "Rarity": rarity,
            "Card Ability (Description)": description,
            "Flavor Text": flavor_text
        }
        rows.append(row)

    # 3. แปลงเป็น DataFrame ของ Pandas
    df = pd.DataFrame(rows)

    # 4. ส่งออกไฟล์เป็น Excel
    print(f"📊 กำลังแปลงข้อมูลจำนวน {len(df)} แถว ลงสู่ไฟล์ Excel...")
    df.to_excel(output_file, index=False, sheet_name="Riftbound Cards")
    
    print("============================================================")
    print(f"🎉 สำเร็จแล้ว! ดำเนินการสร้างไฟล์ Excel เรียบร้อย")
    print(f"📁 พิกัดไฟล์: {os.path.abspath(output_file)}")
    print("💡 เทคนิค: คุณสามารถลากไฟล์ .xlsx นี้ไปอัปโหลดเข้าคลัง Source ของ NotebookLM")
    print("   แล้วพิมพ์ถามกติกาหรือให้มันสรุป Combo การ์ดเสมือนมีโปรเพลเยอร์ส่วนตัวได้เลยครับ!")
    print("============================================================")

if __name__ == "__main__":
    convert_json_to_excel()