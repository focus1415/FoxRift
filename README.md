# riftbound_aiC:\Users\focus\Desktop\riftbound_ai\README.md
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# รันโปรแกรม clean เอา null ออก+เรียงใหม่
python data_card.py
# รันโปรแกรม เช็คว่าครบมั้ย
python check_completeness.py
# รันโปรแกรม train_embeddings
python train_embeddings.py
# เช็ค กฎเด็ค
python deck_validator.py