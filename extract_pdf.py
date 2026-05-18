import os
import sys
import subprocess

# ปรับปรุงให้แสดงผลภาษาไทย/Unicode บน Terminal ได้ถูกต้อง
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def install_and_import(package):
    try:
        __import__(package)
        print(f"✅ {package} is already installed.")
    except ImportError:
        print(f"📦 {package} is missing. Installing in virtual environment...")
        # ค้นหา pip.exe ใน venv
        pip_path = os.path.join("venv", "Scripts", "pip.exe")
        if not os.path.exists(pip_path):
            pip_path = "pip"
        subprocess.check_call([pip_path, "install", package])
        print(f"✅ {package} installed successfully.")

if __name__ == "__main__":
    # 1. รับประกันว่ามี pypdf ติดตั้งเรียบร้อย
    install_and_import("pypdf")
    
    import pypdf
    
    pdf_path = "Riftbound Core Rules v1.2.pdf"
    output_txt = "riftbound_rules.txt"
    
    if not os.path.exists(pdf_path):
        print(f"❌ ไม่พบไฟล์ PDF: {pdf_path} ในไดเรกทอรีนี้")
        sys.exit(1)
        
    print(f"📖 กำลังเปิดและดึงข้อมูลข้อความจาก PDF: {pdf_path} ...")
    
    try:
        reader = pypdf.PdfReader(pdf_path)
        total_pages = len(reader.pages)
        print(f"📄 จำนวนหน้าทั้งหมดในไฟล์: {total_pages} หน้า")
        
        extracted_text = []
        for i in range(total_pages):
            page_text = reader.pages[i].extract_text()
            extracted_text.append(f"--- PAGE {i + 1} ---")
            extracted_text.append(page_text)
            
        full_text = "\n".join(extracted_text)
        
        # บันทึกเป็นไฟล์ข้อความ
        with open(output_txt, "w", encoding="utf-8") as f:
            f.write(full_text)
            
        print(f"💾 สกัดข้อความและบันทึกข้อกำหนดกฎระเบียบสำเร็จที่: {os.path.abspath(output_txt)}")
        
        # แสดงตัวอย่างหัวข้อบางส่วน
        print("\n🔎 ตัวอย่างข้อความบางส่วนจากหน้าระเบียบแรก ๆ:")
        print("=" * 60)
        print("\n".join(extracted_text[:10])[:800]) # แสดง 800 ตัวอักษรแรก
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการดึงข้อความ: {e}")
