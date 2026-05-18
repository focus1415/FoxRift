import json
import os
import sys
import random

# แก้ปัญหา UnicodeEncodeError บน Windows terminal สำหรับ emoji
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def parse_domains(card_data):
    if not card_data:
        return set()
    domain_val = card_data.get("domain")
    if not domain_val:
        return set()
    if isinstance(domain_val, list):
        return set(domain_val)
    if isinstance(domain_val, str):
        # แยกโดยใช้ ; เช่น "Fury;Chaos" -> {"Fury", "Chaos"}
        return set(domain_val.split(";"))
    return set()

class OfficialRiftboundValidator:
    def __init__(self, master_dataset_path=None):
        self.master_cards = {}
        
        # ค้นหาไฟล์ *_clean.json ทั้งหมดเพื่อโหลดข้อมูลการ์ดรวมทุกชุดแบบอัตโนมัติ
        if not master_dataset_path or not os.path.exists(master_dataset_path):
            clean_files = [f for f in os.listdir(".") if f.endswith("_clean.json")]
            if not clean_files:
                raise FileNotFoundError("❌ ไม่พบไฟล์การ์ดที่คลีนแล้ว (*_clean.json) ในโฟลเดอร์ กรุณารัน data_card.py ก่อน")
            
            print(f"📦 ไม่พบไฟล์มาสเตอร์เดี่ยว กำลังรวมการ์ดจากชุด {len(clean_files)} ชุดอัตโนมัติ...")
            for file_name in clean_files:
                with open(file_name, 'r', encoding='utf-8') as f:
                    try:
                        cards = json.load(f)
                        for card in cards:
                            # เก็บข้อมูลการ์ดโดยใช้ชื่อการ์ดเป็นคีย์หลัก
                            self.master_cards[card["name"]] = card
                    except Exception as e:
                        print(f"⚠️ โหลดไฟล์ {file_name} ล้มเหลว: {e}")
            print(f"✅ โหลดมาสเตอร์การ์ดรวมทุกชุดสำเร็จ: ทั้งหมด {len(self.master_cards)} ใบ\n")
        else:
            with open(master_dataset_path, 'r', encoding='utf-8') as f:
                self.master_cards = {card["name"]: card for card in json.load(f)}

        # 🌟 ระบบฮีลลิ่งข้อมูลการ์ดแวเรียนต์/โปรโม (เช่น Alternate Art / Showcase) 🌟
        # ป้องกันบั๊กในดาต้าเซ็ตต้นฉบับที่เว้นฟิลด์ domain และ cardType เป็น null
        healed_count = 0
        for name, card in self.master_cards.items():
            if card.get("domain") is None or card.get("cardType") is None:
                # แปลงชื่อการ์ดแวเรียนต์เป็นชื่อการ์ดร่างหลัก เช่น "Rumble - Hotheaded (Alternate Art)" -> "Rumble - Hotheaded"
                base_name = name.split("(")[0].strip()
                base_card = self.master_cards.get(base_name)
                if base_card:
                    if card.get("domain") is None:
                        card["domain"] = base_card.get("domain")
                    if card.get("cardType") is None:
                        card["cardType"] = base_card.get("cardType")
                    
                    # อัปเดตข้อมูล text_for_ai
                    name_val = card.get("name", "Unknown")
                    card_type_val = card.get("cardType", "Unknown")
                    domain_val = card.get("domain", "Unknown")
                    energy_cost_val = card.get("energyCost", 0)
                    description_val = card.get("description", "")
                    card["text_for_ai"] = f"Card Name: {name_val} | Type: {card_type_val} | Domain: {domain_val} | Energy Cost: {energy_cost_val} | Ability: {description_val}"
                    healed_count += 1
                    
        if healed_count > 0:
            print(f"🛡️ ดึงข้อมูลตามร่างหลักเติมเต็มให้การ์ด Alternate Art/Showcase สำเร็จ: {healed_count} ใบ\n")

    def validate_complete_deck(self, legend_name, champion_name, main_deck, rune_deck, battlefields):
        """
        ตรวจกฎเหล็กตามแบบฉบับ Deckbuilding Primer ของ Riot Games
        """
        errors = []
        
        # 1. เช็กความมีอยู่จริงของ Legend หลัก
        legend = self.master_cards.get(legend_name)
        if not legend:
            return False, [f"❌ ไม่พบข้อมูล Legend: {legend_name}"]
            
        allowed_domains = parse_domains(legend) # ดึงสีที่เด็คนี้เล่นได้ เช่น {'Fury', 'Chaos'}
        legend_base = legend_name.split("-")[0].strip()
        
        # 2. เช็ก Champion Unit และความสอดคล้อง
        champ_unit = self.master_cards.get(champion_name)
        if not champ_unit:
            errors.append(f"❌ ไม่พบข้อมูล Champion Unit: {champion_name}")
        else:
            # ดึงชื่อหลักมาเปรียบเทียบ เช่น "Draven - Glorious Executioner" vs "Draven - Vanquisher"
            champ_base = champion_name.split("-")[0].strip()
            if legend_base != champ_base:
                errors.append(f"⚠️ ผิดกฎ: ตัวละครหลักของ Champion Unit ({champion_name}) ไม่ตรงกับ Legend ({legend_name})")
            
            # กฎเหล็ก: Champion Unit ต้องรวมอยู่ใน Main Deck 40 ใบด้วยอย่างน้อย 1 ใบ!
            if champion_name not in main_deck:
                errors.append(f"⚠️ ผิดกฎ: ต้องใส่การ์ด Champion Unit '{champion_name}' ไว้ใน Main Deck (40 ใบ) ด้วยอย่างน้อย 1 ใบ")
            
        # 3. เช็กจำนวน Battlefield (ต้องมี 3 ใบพอดี)
        if len(battlefields) != 3:
            errors.append(f"⚠️ ผิดกฎ: ต้องเลือก Battlefield 3 ใบพอดี (ปัจจุบันเลือกมา {len(battlefields)} ใบ)")

        # 4. เช็กกฎกติกาของ Rune Deck (ต้องมี 12 ใบพอดี และต้องตรงสี)
        if len(rune_deck) != 12:
            errors.append(f"⚠️ ผิดกฎ: Rune Deck ต้องมี 12 ใบพอดี (ปัจจุบันมี {len(rune_deck)} ใบ)")
            
        for rune_name in rune_deck:
            rune = self.master_cards.get(rune_name)
            if not rune:
                errors.append(f"❌ ไม่พบข้อมูลการ์ดรูน '{rune_name}' ในเกม")
                continue
            
            rune_domains = parse_domains(rune)
            # เช็กว่าสีของรูนทั้งหมดอยู่ในขอบเขตสีที่อนุญาตของ Legend หรือไม่
            if not rune_domains:
                errors.append(f"⚠️ ผิดกฎ: การ์ดรูน '{rune_name}' ไม่มีข้อมูล Domain ที่ถูกต้อง")
            elif not rune_domains.issubset(allowed_domains):
                errors.append(f"⚠️ ผิดกฎ: รูน '{rune_name}' มีสี {rune_domains} ที่ไม่ตรงกับ Domain ของ Legend {allowed_domains}")

        # 5. เช็กกฎกติกาของ Main Deck (ต้องมี 40 ใบพอดี, ห้ามใส่ซ้ำเกิน 3, ห้ามข้ามสี, และห้ามใส่ Champion ตัวอื่น)
        if len(main_deck) != 40:
            errors.append(f"⚠️ ผิดกฎ: Main Deck ต้องมี 40 ใบพอดี (ปัจจุบันมี {len(main_deck)} ใบ)")

        card_counts = {}
        for card_name in main_deck:
            card = self.master_cards.get(card_name)
            if not card:
                errors.append(f"❌ ไม่พบข้อมูลการ์ด '{card_name}' ในเกม")
                continue
                
            # เช็กกฎห้ามใส่ซ้ำเกิน 3 ใบ
            card_counts[card_name] = card_counts.get(card_name, 0) + 1
            if card_counts[card_name] > 3:
                errors.append(f"⚠️ ผิดกฎ: ใส่การ์ด '{card_name}' ซ้ำเกิน 3 ใบในเด็ค")
                
            # เช็กกฎ Color Identity (Multi-color ต้องตรงกับ Legend ทุกสี)
            card_domains = parse_domains(card)
            if not card_domains:
                errors.append(f"⚠️ ผิดกฎ: การ์ด '{card_name}' ไม่มีข้อมูล Domain ที่ถูกต้อง")
            elif not card_domains.issubset(allowed_domains):
                errors.append(f"⚠️ ผิดกฎ: การ์ด '{card_name}' มี Domain {card_domains} ที่ไม่สอดคล้องกับ Legend สาย {allowed_domains}")
                
            # เช็กกฎห้ามใส่ Champion Unit ของตัวละครอื่น
            c_type = card.get("cardType")
            if c_type == "Champion Unit":
                card_base = card_name.split("-")[0].strip()
                if card_base != legend_base:
                    errors.append(f"⚠️ ผิดกฎ: เด็คนี้ใช้ Legend {legend_name} จึงห้ามใส่การ์ด Champion Unit ของตัวละครอื่น ({card_name}) เข้ามาในเด็ค")

        if len(errors) == 0:
            return True, [f"🎉 เด็ค {legend_name} ถูกต้องตามกฎกติกา Official ของ Riot Games ทุกประการ! พร้อมส่งให้ AI เทรน"]
        else:
            return False, errors

    def print_deck_list(self, legend_name, champion_name, main_deck, rune_deck, battlefields):
        """
        แสดงโครงสร้างเด็คที่จัดไว้อย่างสวยงามพร้อมรวมจำนวนการ์ดที่ซ้ำกัน
        """
        print("\n📋 สรุปโครงสร้างเด็คลิสต์ (Deck List Dashboard)")
        print("=" * 60)
        
        # 👑 ข้อมูล Legend และ Champion
        legend = self.master_cards.get(legend_name)
        allowed_domains = "/".join(parse_domains(legend)) if legend else "Unknown"
        print(f"👑 LEGEND:   {legend_name} ({allowed_domains})")
        print(f"🌟 CHAMPION: {champion_name}")
        print("-" * 60)
        
        # ⚔️ รวบรวมการ์ดหลัก (Main Deck) แยกประเภทและการ์ดซ้ำ
        main_counts = {}
        for card_name in main_deck:
            main_counts[card_name] = main_counts.get(card_name, 0) + 1
            
        print(f"⚔️ MAIN DECK ({len(main_deck)}/40 ใบ):")
        # แยกหมวดหมู่ตามประเภทการ์ดเพื่อความสวยงาม
        categorized = {}
        for card_name, count in main_counts.items():
            card = self.master_cards.get(card_name)
            card_type = card.get("cardType") if card else "Other"
            if not card_type:
                card_type = "Other"
            if card_type not in categorized:
                categorized[card_type] = []
            categorized[card_type].append((card_name, count))
            
        for card_type, cards in sorted(categorized.items()):
            print(f"   🔹 [{card_type}]")
            for card_name, count in sorted(cards):
                # ตรวจดูความครบถ้วนของการ์ดแต่ละใบ
                found_status = "" if card_name in self.master_cards else " ❌ (ไม่พบในฐานข้อมูล)"
                print(f"      • {count}x {card_name}{found_status}")
        print("-" * 60)
        
        # 🌀 รวบรวมการ์ดรูน (Rune Deck)
        rune_counts = {}
        for rune_name in rune_deck:
            rune_counts[rune_name] = rune_counts.get(rune_name, 0) + 1
            
        print(f"🌀 RUNE DECK ({len(rune_deck)}/12 ใบ):")
        for rune_name, count in sorted(rune_counts.items()):
            found_status = "" if rune_name in self.master_cards else " ❌ (ไม่พบในฐานข้อมูล)"
            print(f"   • {count}x {rune_name}{found_status}")
        print("-" * 60)
        
        # 🏟️ สนามรบ (Battlefields)
        print(f"🏟️ BATTLEFIELDS ({len(battlefields)}/3 ใบ):")
        for bf in sorted(battlefields):
            print(f"   • {bf}")
        print("=" * 60 + "\n")

    def generate_random_valid_deck(self, legend_name=None):
        """
        สุ่มจัดเด็คลิสต์ที่ถูกต้องตามกฎกติกา 100% จากฐานข้อมูล
        """
        # ดึงรายชื่อ Champion Units ทั้งหมดในระบบและเก็บชื่อตัวละครต้นแบบ (base character)
        champ_chars = set()
        for card in self.master_cards.values():
            if card.get("cardType") == "Champion Unit":
                champ_base = card["name"].split("-")[0].strip()
                champ_chars.add(champ_base)

        # 1. เลือก Legend ที่เข้าคู่กับ Champion Unit ที่มีในระบบได้จริง
        legends = [
            card for card in self.master_cards.values() 
            if card.get("cardType") == "Legend" and card["name"].split("-")[0].strip() in champ_chars
        ]
        if not legends:
            return None, "❌ ไม่พบข้อมูล Legend ที่สามารถเข้าคู่กับ Champion Unit ใด ๆ ในฐานข้อมูลได้"
            
        legend = random.choice(legends) if not legend_name else self.master_cards.get(legend_name)
        if not legend:
            return None, f"❌ ไม่พบ Legend ชื่อ {legend_name}"
            
        legend_name = legend["name"]
        allowed_domains = parse_domains(legend)
        legend_char = legend_name.split("-")[0].strip()
        
        # 2. ค้นหา Champion Unit ที่ตรงกับ Legend ตัวนี้
        champions = [
            card for card in self.master_cards.values() 
            if card.get("cardType") == "Champion Unit" and card["name"].split("-")[0].strip() == legend_char
        ]
        if not champions:
            return None, f"❌ ไม่พบ Champion Unit ที่เข้ากันได้กับ Legend: {legend_name}"
            
        champion_name = random.choice(champions)["name"]
        
        # 3. ค้นหาการ์ดทั่วไป (Main Deck Cards) ที่มี Domain ตรงกับสีของ Legend
        valid_pool = []
        for card in self.master_cards.values():
            c_type = card.get("cardType")
            if c_type in ["Legend", "Rune"]:
                continue
            # ถ้าเป็น Champion Unit ของตัวละครตัวอื่น ให้ข้ามไป (ใส่ได้เฉพาะแชมเปี้ยนตัวเอกตรงกับ Legend เท่านั้น)
            if c_type == "Champion Unit" and card["name"].split("-")[0].strip() != legend_char:
                continue
                
            card_domains = parse_domains(card)
            if not card_domains: # ข้ามการ์ดที่ไม่มี Domain หรือฟิลด์ว่าง
                continue
            if card_domains.issubset(allowed_domains):
                valid_pool.append(card["name"])
                
        if len(valid_pool) < 14: # ต้องการการ์ดอย่างน้อย 14 ชนิดไม่ซ้ำ เพื่อให้จัดเด็ค 40 ใบได้โดยไม่เกินชนิดละ 3
            return None, f"❌ การ์ดในฐานข้อมูลของสาย {allowed_domains} มีน้อยเกินไปที่จะจัดเด็คได้ ({len(valid_pool)} ใบ)"
            
        # สุ่มหยิบการ์ดเข้า Main Deck 40 ใบ โดยเริ่มจากการหยิบ Champion Unit ที่เลือกไว้แล้วใส่ไปก่อน 1 ใบ!
        main_deck = [champion_name]
        card_counts = {champion_name: 1}
        
        while len(main_deck) < 40:
            candidate = random.choice(valid_pool)
            current_count = card_counts.get(candidate, 0)
            if current_count < 3:
                main_deck.append(candidate)
                card_counts[candidate] = current_count + 1
                
        # 4. ค้นหาและสุ่มรูน (Rune Deck)
        valid_runes = [
            card["name"] for card in self.master_cards.values()
            if card.get("cardType") == "Rune" and parse_domains(card).issubset(allowed_domains)
        ]
        
        if not valid_runes:
            return None, f"❌ ไม่พบการ์ด Rune ของสาย {allowed_domains} ในฐานข้อมูล"
            
        rune_deck = []
        for _ in range(12):
            rune_deck.append(random.choice(valid_runes))
            
        # 5. สนามรบ (Mock Battlefields)
        battlefields = ["Standard Arena", "Shadow Isles Border", "Noxus Warroom"]
        
        return {
            "legend_name": legend_name,
            "champion_name": champion_name,
            "main_deck": main_deck,
            "rune_deck": rune_deck,
            "battlefields": battlefields
        }, None

# 🧪 ส่วนทดลองรันตรวจกฎแบบจำลองจริง
if __name__ == "__main__":
    # ส่งค่า None หรือว่างเปล่า เพื่อสแกนหาไฟล์ *_clean.json ในรูทอัตโนมัติ
    validator = OfficialRiftboundValidator()
    
    print("=" * 60)
    print("🧪 [Test Case 1] ทดสอบเด็คที่มีการฟาวล์/ผิดกฎ (Invalid Deck)")
    print("=" * 60)
    
    # 1. เด็คผิดกฎ: ใช้ชื่อการ์ดสมมติที่ไม่มีจริงในดาต้าเบส หรือฟาวล์ซ้ำเกิน 3 ใบ
    bad_main = ["Noxian Might"] * 40  # ผิดกฎ: ใส่ซ้ำเกิน 3 ใบ และสะกดผิดไม่พบข้อมูลการ์ด
    bad_runes = ["Rune of Fury"] * 12  # สะกดผิด: ในเกมใช้ชื่อ "Fury Rune"
    bad_battlefields = ["Standard Arena", "Shadow Isles Border", "Noxus Warroom"]
    
    # แสดงพรีวิวเด็คที่มีข้อผิดพลาดก่อน
    validator.print_deck_list(
        legend_name="Draven - Glorious Executioner",
        champion_name="Draven - Vanquisher",
        main_deck=bad_main,
        rune_deck=bad_runes,
        battlefields=bad_battlefields
    )
    
    is_valid, report = validator.validate_complete_deck(
        legend_name="Draven - Glorious Executioner", 
        champion_name="Draven - Vanquisher", 
        main_deck=bad_main, 
        rune_deck=bad_runes, 
        battlefields=bad_battlefields
    )
    
    print("📢 ผลการสแกนตรวจกฎ (เด็คไม่ผ่านเกณฑ์):")
    for line in report[:15]: # แสดงผล 15 บรรทัดแรก
        print(line)
        
    print("\n" + "=" * 60)
    print("🧪 [Test Case 2] ทดสอบเด็คที่ถูกต้องตามกฎ 100% (Valid Deck - Hardcoded)")
    print("=" * 60)
    
    # 2. เด็คถูกกฎ: ใช้ชื่อการ์ดจริงจากฐานข้อมูล
    # - Legend: "Darius - Hand of Noxus" (เป็น Legend ตรงสาย)
    # - Champion: "Darius - Trifarian" (3 ใบรวมอยู่ใน Main Deck 40 ใบเรียบร้อยแล้ว)
    good_main = (
        ["Legion Rearguard"] * 3 +
        ["Cleave"] * 3 +
        ["Noxus Saboteur"] * 3 +
        ["Dangerous Duo"] * 3 +
        ["Blazing Scorcher"] * 3 +
        ["Magma Wurm"] * 3 +
        ["Noxus Hopeful"] * 3 +
        ["Pouty Poro"] * 3 +
        ["Raging Soul"] * 3 +
        ["Iron Ballista"] * 3 +
        ["Darius - Trifarian"] * 3 + # Champion Unit สอดคล้องกับ Legend และมี 3 ใบ
        ["Flame Chompers"] * 3 +
        ["Disintegrate"] * 3 +
        ["Hextech Ray"] * 1
    )
    good_runes = ["Fury Rune"] * 12
    good_battlefields = ["Standard Arena", "Shadow Isles Border", "Noxus Warroom"]
    
    # แสดงพรีวิวเด็คที่ถูกต้องอย่างสวยงาม
    validator.print_deck_list(
        legend_name="Darius - Hand of Noxus",
        champion_name="Darius - Trifarian",
        main_deck=good_main,
        rune_deck=good_runes,
        battlefields=good_battlefields
    )
    
    is_valid2, report2 = validator.validate_complete_deck(
        legend_name="Darius - Hand of Noxus", 
        champion_name="Darius - Trifarian", 
        main_deck=good_main, 
        rune_deck=good_runes, 
        battlefields=good_battlefields
    )
    
    print("📢 ผลการสแกนตรวจกฎ (เด็คผ่านเกณฑ์):")
    for line in report2:
        print(line)
    print("=" * 60)

    print("\n" + "=" * 60)
    print("🎲 [Test Case 3] สุ่มจัดเด็คตามกฎ 100% จากฐานข้อมูล (Random Valid Deck)")
    print("=" * 60)
    
    random_deck, err = validator.generate_random_valid_deck()
    if err:
        print(err)
    else:
        # แสดงพรีวิวเด็คสุ่ม
        validator.print_deck_list(
            legend_name=random_deck["legend_name"],
            champion_name=random_deck["champion_name"],
            main_deck=random_deck["main_deck"],
            rune_deck=random_deck["rune_deck"],
            battlefields=random_deck["battlefields"]
        )
        
        # รันตรวจกฎ
        is_valid3, report3 = validator.validate_complete_deck(
            legend_name=random_deck["legend_name"],
            champion_name=random_deck["champion_name"],
            main_deck=random_deck["main_deck"],
            rune_deck=random_deck["rune_deck"],
            battlefields=random_deck["battlefields"]
        )
        
        print("📢 ผลการสแกนตรวจกฎ (เด็คผ่านเกณฑ์):")
        for line in report3:
            print(line)
    print("=" * 60)