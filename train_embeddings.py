import json
import os
import sys
import torch
from sentence_transformers import SentenceTransformer, util

# ป้องกันปัญหา UnicodeEncodeError บน Windows terminal
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def run_card_embedding():
    # สแกนหาไฟล์การ์ดที่คลีนแล้วทั้งหมดในรูทโฟลเดอร์
    input_files = [f for f in os.listdir(".") if f.endswith("_clean.json")]
    
    if not input_files:
        print("❌ ไม่พบไฟล์การ์ดที่คลีนแล้ว (*_clean.json) กรุณารัน data_card.py ก่อนครับ")
        return

    # เช็กอุปกรณ์ประมวลผล (AMD/CPU)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"💻 ระบบกำลังประมวลผลด้วย: {device.upper()}")
    if device == "cuda":
        print(f"🔥 การ์ดจอที่ใช้งาน: {torch.cuda.get_device_name(0)}")
    else:
        print("ℹ️ ระบบรันบน CPU (สมบูรณ์และเสถียรสำหรับข้อมูลขนาดนี้)")

    # โหลดโมเดลสำหรับทำ Embedding (โมเดลขนาดเล็กและทรงประสิทธิภาพ)
    print("🤖 กำลังโหลดโมเดลภาษา 'all-MiniLM-L6-v2'...")
    model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
    print("=" * 60)

    for input_file in sorted(input_files):
        set_name = input_file.replace("_clean.json", "")
        output_file = f"{set_name}_synergy_matrix.json"
        
        print(f"\n🚀 เริ่มประมวลผลโมเดลสำหรับชุดการ์ด: [ {set_name} ]")
        
        # โหลดข้อมูลการ์ดที่คลีนแล้ว
        with open(input_file, 'r', encoding='utf-8') as f:
            cards = json.load(f)
            
        print(f"   📖 โหลดการ์ดจำนวน {len(cards)} ใบ เข้าสู่ระบบ...")

        if len(cards) == 0:
            print("   ⚠️ ไม่พบข้อมูลการ์ดในไฟล์ ข้ามการประมวลผล...")
            print("-" * 60)
            continue

        # ดึงข้อความมาทำ Embedding
        texts = [card["text_for_ai"] for card in cards]
        card_names = [card["name"] for card in cards]

        print("   🧠 กำลังแปลงข้อความการ์ดให้เป็น Vector...")
        embeddings = model.encode(texts, convert_to_tensor=True, show_progress_bar=True)

        # สร้าง "ตาราง Synergy"
        print("   📊 กำลังคำนวณตารางความสัมพันธ์ (Synergy Matrix)...")
        cosine_scores = util.cos_sim(embeddings, embeddings)

        # แปลง Tensor กลับเป็นลิสต์ธรรมดาเพื่อเซฟเป็น JSON
        synergy_matrix = {}
        for i in range(len(cards)):
            card_a = card_names[i]
            synergy_matrix[card_a] = {}
            for j in range(len(cards)):
                card_b = card_names[j]
                synergy_matrix[card_a][card_b] = float(cosine_scores[i][j])

        # เซฟไฟล์ตารางความสัมพันธ์
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(synergy_matrix, f, ensure_ascii=False, indent=4)

        print(f"   🎉 เสร็จสิ้นการประมวลผลโมเดลชุด {set_name}!")
        print(f"   💾 บันทึกไฟล์ตารางความสัมพันธ์ไว้ที่: {os.path.abspath(output_file)}")
        
        # ตัวอย่างการแสดงผลความฉลาดของโมเดล
        test_idx = 0
        print(f"   💡 ตัวอย่างการวิเคราะห์ความสัมพันธ์ของการ์ด: '{card_names[test_idx]}'")
        scores = synergy_matrix[card_names[test_idx]]
        # ดึงความสัมพันธ์ที่มากที่สุด 3 อันดับแรก (ข้ามตัวแรกที่เป็นตัวเอง)
        top_synergies = sorted(scores.items(), key=lambda x: x[1], reverse=True)[1:4]
        for name, score in top_synergies:
            print(f"      - มีความเข้ากันได้กับ '{name}' สูงถึง: {score:.4f}")
        print("-" * 60)

if __name__ == "__main__":
    run_card_embedding()