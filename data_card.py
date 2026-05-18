import os
import json
import sys

# แก้ปัญหา UnicodeEncodeError บน Windows terminal สำหรับ emoji
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def get_card_number_key(card):
    number_str = card.get("number")
    if not number_str:
        return (1, "")
    
    # ดึงตัวเลขก่อนเครื่องหมาย / (เช่น "173/221" -> 173)
    if "/" in number_str:
        parts = number_str.split("/")
        try:
            val = int(parts[0])
            return (0, val)
        except ValueError:
            return (1, number_str)
            
    try:
        val = int(number_str)
        return (0, val)
    except ValueError:
        return (1, number_str)

def clean_and_split_cards_by_set(cards_folder_path):
    print(f"📦 กำลังกรองและแยกข้อมูลการ์ดที่ใช้เล่นจริงตามชุดจาก: {cards_folder_path}\n")
    
    if not os.path.exists(cards_folder_path):
        print("❌ ไม่พบโฟลเดอร์ กรุณาเช็กสเต็ปก่อนหน้าอีกครั้งครับ")
        return

    for filename in os.listdir(cards_folder_path):
        if filename.endswith(".json"):
            file_path = os.path.join(cards_folder_path, filename)
            set_name = filename.replace(".json", "")
            output_filename = f"{set_name}_clean.json"
            
            playable_cards = []
            ignored_products = 0
            
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    card_list = json.load(f)
                    
                    if not isinstance(card_list, list):
                        print(f"⚠️ โครงสร้างไฟล์ {filename} ไม่ใช่ List ของการ์ด ข้ามไฟล์นี้...")
                        continue
                        
                    for card_data in card_list:
                        # 🛡️ ตัวกรองทีเด็ด: ถ้าฟิลด์เหล่านี้เป็น null แปลว่าเป็นซองการ์ด/กล่องสินค้า ให้ข้ามไปเลย!
                        if card_data.get("cardType") is None and card_data.get("description") is None:
                            ignored_products += 1
                            continue
                            
                        # ดึงข้อมูลการ์ดจริง (สอดคล้องกับฟิลด์ camelCase ใน TCGplayer dataset)
                        name = card_data.get("name", "Unknown")
                        card_type = card_data.get("cardType", "Unknown")
                        domain = card_data.get("domain", "Unknown")
                        energy_cost = card_data.get("energyCost", 0)
                        description = card_data.get("description", "")
                        
                        # มัดรวมข้อความให้คลีนที่สุด ส่งต่อให้โมเดลภาษาอ่าน
                        full_context = f"Card Name: {name} | Type: {card_type} | Domain: {domain} | Energy Cost: {energy_cost} | Ability: {description}"
                        card_data["text_for_ai"] = full_context
                        
                        playable_cards.append(card_data)
                    
                    # เรียงลำดับการ์ดตาม number
                    playable_cards.sort(key=get_card_number_key)
                        
                    # บันทึกไฟล์แยกชุด
                    with open(output_filename, 'w', encoding='utf-8') as out_f:
                        json.dump(playable_cards, out_f, ensure_ascii=False, indent=4)
                        
                    print(f"📂 ชุด: [ {set_name} ]")
                    print(f"   ✅ ได้การ์ดจริงสำหรับเอาไปเล่นและจัดเด็ค: {len(playable_cards)} ใบ (เรียงลำดับเลขการ์ดเรียบร้อย)")
                    print(f"   🚫 เตะซองการ์ด/กล่องสินค้าขยะทิ้งไป: {ignored_products} ชิ้น")
                    print(f"   💾 บันทึกไฟล์คลีนไว้ที่: {os.path.abspath(output_filename)}")
                    print("-" * 50)
                    
                except Exception as e:
                    print(f"⚠️ มีข้อผิดพลาดในไฟล์ {filename}: {e}")

if __name__ == "__main__":
    cards_folder = "cards"
    clean_and_split_cards_by_set(cards_folder)