import os
import json
import sys

# ป้องกันปัญหา UnicodeEncodeError บน Windows terminal
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def check_set_completeness(file_path):
    if not os.path.exists(file_path):
        print(f"❌ ไม่พบไฟล์: {file_path}")
        return

    print(f"🔍 กำลังตรวจสอบความครบถ้วนของข้อมูลการ์ดในไฟล์: {os.path.basename(file_path)}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        cards = json.load(f)
        
    # เก็บข้อมูลการ์ดแต่ละใบตามหมายเลข (เช่น "173/221" -> หมายเลข 173)
    present_numbers = {}
    total_expected = None
    
    for card in cards:
        number_str = card.get("number")
        if not number_str:
            continue
            
        if "/" in number_str:
            parts = number_str.split("/")
            try:
                num = int(parts[0])
                total = int(parts[1])
                if total_expected is None or total > total_expected:
                    total_expected = total
                
                if num not in present_numbers:
                    present_numbers[num] = []
                present_numbers[num].append(card)
            except ValueError:
                pass
        else:
            try:
                num = int(number_str)
                if num not in present_numbers:
                    present_numbers[num] = []
                present_numbers[num].append(card)
            except ValueError:
                pass

    if total_expected is None:
        print("⚠️ ไม่พบรูปแบบการ์ดแบบ X/Y (เช่น 173/221) ทำให้ไม่สามารถระบุจำนวนการ์ดทั้งหมดของชุดได้แบบออโต้")
        if present_numbers:
            total_expected = max(present_numbers.keys())
            print(f"ℹ️ จะใช้หมายเลขการ์ดที่สูงที่สุดที่พบคือ: {total_expected} ใบ เป็นเกณฑ์คาดหวัง")
        else:
            print("❌ ไม่พบข้อมูลหมายเลขการ์ดใด ๆ ในไฟล์นี้")
            print("=" * 60)
            return

    print(f"📊 สรุปภาพรวมชุดการ์ด:")
    print(f"   - จำนวนการ์ดทั้งหมดในไฟล์: {len(cards)} รายการ")
    print(f"   - จำนวนการ์ดที่คาดหวังในชุดสะสม: {total_expected} ใบ")
    
    # ตรวจหาการ์ดที่ขาดหายไป (Missing Numbers)
    missing_numbers = []
    for num in range(1, total_expected + 1):
        if num not in present_numbers:
            missing_numbers.append(num)
            
    # ตรวจหาการ์ดที่มีหมายเลขซ้ำ (Duplicate Numbers)
    duplicates = {}
    for num, card_list in present_numbers.items():
        if len(card_list) > 1:
            duplicates[num] = [card.get("name") for card in card_list]

    # แสดงผลการตรวจสอบ
    if not missing_numbers:
        print(f"   ✅ ยอดเยี่ยมมาก! การ์ดครบทุกหมายเลขตั้งแต่ 1 ถึง {total_expected} ไม่มีใบไหนขาดหายเลยครับ 🎉")
    else:
        print(f"   ❌ มีการ์ดขาดหายไป {len(missing_numbers)} ใบ จากทั้งหมด {total_expected} ใบ")
        print(f"   📌 หมายเลขการ์ดที่ขาดหายไป: {missing_numbers}")
        
    if duplicates:
        print(f"   ⚠️ พบหมายเลขการ์ดที่มีหลายเวอร์ชัน/ซ้ำกัน ทั้งหมด {len(duplicates)} หมายเลข:")
        for num, names in sorted(duplicates.items())[:10]: # แสดง 10 ตัวอย่างแรก
            unique_names = list(set(names))
            print(f"      - หมายเลข {num:03d}: {', '.join(unique_names)} (พบซ้ำ {len(names)} รายการ)")
        if len(duplicates) > 10:
            print(f"      - ... และมีหมายเลขซ้ำอื่น ๆ อีก {len(duplicates) - 10} หมายเลข")
    else:
        print(f"   ✅ ไม่มีหมายเลขการ์ดซ้ำกันเลย")
        
    print("=" * 60)

if __name__ == "__main__":
    # ตรวจสอบทุกไฟล์ที่ลงท้ายด้วย _clean.json ในรูทโฟลเดอร์
    files_to_check = [f for f in os.listdir(".") if f.endswith("_clean.json")]
    for file in sorted(files_to_check):
        check_set_completeness(file)
