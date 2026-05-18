import gymnasium as gym
from gymnasium import spaces
import numpy as np
import json
import os
import sys
import random

# แก้ปัญหา UnicodeEncodeError บน Windows terminal สำหรับ emoji
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

class OfficialRiftboundEnv(gym.Env):
    """Simulator รุ่นอัปเกรดตรงตามกฎระเบียบ Riftbound Core Rules v1.2 จาก PDF"""
    
    def __init__(self, master_dataset_path):
        super(OfficialRiftboundEnv, self).__init__()
        
        with open(master_dataset_path, 'r', encoding='utf-8') as f:
            self.master_cards = json.load(f)

        # Action Space: ปรับให้ครอบคลุมการกระทำจริงตามกฎ v1.2
        # [0: Pass]
        # [1-3: Play Card to Left Lane (1: Unit, 2: Gear, 3: Spell)]
        # [4-6: Play Card to Center Lane (4: Unit, 5: Gear, 6: Spell)]
        # [7-9: Play Card to Right Lane (7: Unit, 8: Gear, 9: Spell)]
        self.action_space = spaces.Discrete(10)

        # Observation Space (สถานะบอร์ด 21 มิติ ที่ส่งให้โมเดล AI มองเห็น)
        # [Might_L/C/R (เรา), Might_L/C/R (ศัตรู), Control_L/C/R, Gears_L/C/R (เรา), Gears_L/C/R (ศัตรู), Energy (เรา), Energy (ศัตรู), Score (เรา), Score (ศัตรู), Current_Phase, Turn_Count]
        self.observation_space = spaces.Box(
            low=-1.0, high=100.0, shape=(21,), dtype=np.float32
        )
        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # ตั้งค่าสถานะเริ่มต้นตามกฎจุดเริ่มต้นของเกม (Setup Phase)
        self.my_might = np.zeros(3, dtype=np.float32)      # พลัง Might 3 เลนฝั่งเรา
        self.enemy_might = np.zeros(3, dtype=np.float32)   # พลัง Might 3 เลนฝั่งศัตรู
        
        # การควบคุมสนามรบ (1: ฝั่งเราคุม, -1: ศัตรูคุม, 0: ไม่มีใครควบคุม)
        self.battlefield_control = np.zeros(3, dtype=np.float32) 
        
        self.my_gears = np.zeros(3, dtype=np.float32)      # จำนวน Gear ฝั่งเรา (เพิ่มการผลิตพลังงาน)
        self.enemy_gears = np.zeros(3, dtype=np.float32)   # จำนวน Gear ฝั่งศัตรู
        
        self.my_energy = 3.0                               # พลังงานเริ่มต้น
        self.enemy_energy = 3.0
        self.my_score = 0                                  # แต้มชัยชนะสะสม (Victory Score = 8)
        self.enemy_score = 0
        self.current_phase = 0                             # 0: Awaken/Beginning, 1: Channel/Draw, 2: Action
        self.turn_count = 1
        
        # ติดตามว่าแต่ละเลน (ซ้าย, กลาง, ขวา) ได้ถูกเก็บคะแนนไปแล้วหรือยังในเทิร์นนี้ (กฎข้อ 448.1.b)
        self.my_scored_lanes_this_turn = [False, False, False]
        self.enemy_scored_lanes_this_turn = [False, False, False]
        
        return self._get_obs(), {}


    def _get_obs(self):
        return np.concatenate([
            self.my_might, 
            self.enemy_might,
            self.battlefield_control,
            self.my_gears,
            self.enemy_gears,
            [self.my_energy, self.enemy_energy, float(self.my_score), float(self.enemy_score), float(self.current_phase), float(self.turn_count)]
        ]).astype(np.float32)

    def step(self, action):
        reward = 0.0
        terminated = False
        truncated = False
        action_phase_ended = False

        # 1. จัดการระบบเฟสและ Action (ตามกฎ Action Phase ของ v1.2)
        if action == 0:
            # เลือก Pass เพื่อจบ Action Phase ของฝั่งเรา
            action_phase_ended = True
        else:
            # ถอดรหัสตำแหน่งและประเภทการ์ดที่เล่น
            # เลน: 0 = ซ้าย, 1 = กลาง, 2 = ขวา
            lane = (action - 1) // 3
            card_type = (action - 1) % 3  # 0: Unit, 1: Gear, 2: Spell

            if card_type == 0:  # PLAY UNIT (ยูนิตบุกรบเพื่อช่วงชิงเลน)
                card_cost = 2.0
                if self.my_energy >= card_cost:
                    self.my_energy -= card_cost
                    self.my_might[lane] += 2.5
                    reward += 1.0  # รางวัลร่าย Unit สำเร็จ
                else:
                    reward -= 0.1  # พลังงานไม่พอ
                    
            elif card_type == 1:  # PLAY GEAR (เกียร์เพิ่มกำลังทรัพยากร)
                card_cost = 1.0
                if self.my_energy >= card_cost:
                    self.my_energy -= card_cost
                    # กฎติดตั้ง Gear: ต้องใส่ให้ตัวละคร        # 1.5 จำลองเทิร์นของฝั่งตรงข้าม (Enemy AI Action Phase)
        # ศัตรูจะเล่นการ์ดสกัดกั้นในเลนต่าง ๆ เมื่อเรา Pass จบเทิร์น
        if action_phase_ended:
            # เริ่มรอบเทิร์นใหม่: รีเซ็ตสถานะการทำคะแนนในแต่ละเลนสำหรับรอบนี้
            self.my_scored_lanes_this_turn = [False, False, False]
            self.enemy_scored_lanes_this_turn = [False, False, False]

            for lane in range(3):
                if self.enemy_energy >= 3.0 and random.random() < 0.4:  # ศัตรูเล่น Spell
                    self.enemy_energy -= 3.0
                    self.my_might[lane] = max(0.0, self.my_might[lane] - 4.0)
                elif self.enemy_energy >= 2.0 and random.random() < 0.5:  # ศัตรูเล่น Unit
                    self.enemy_energy -= 2.0
                    self.enemy_might[lane] += 2.5
                elif self.enemy_energy >= 1.0 and random.random() < 0.3:  # ศัตรูเล่น Gear
                    self.enemy_energy -= 1.0
                    # กฎติดตั้ง Gear ศัตรู: ต้องใส่ให้ตัวละครในเลนซ้าย/ขวา
                    # ไม่งั้นต้องปัดมาติดตั้งไว้ตรงกลาง (Base Lane 1)
                    if lane in [0, 2]:
                        if self.enemy_might[lane] > 0:
                            self.enemy_gears[lane] += 1
                        else:
                            self.enemy_gears[1] += 1
                    else:
                        self.enemy_gears[1] += 1

            # 2. คำนวณผลการต่อสู้เมื่อสิ้นสุดรอบ Action Phase (เฉพาะเลนซ้าย 0 และเลนขวา 2 เท่านั้น)
            # ตรงกลาง (Lane 1) คือ Base แยกของใครของมัน ไม่ปะทะกันและไม่มีการแย่งชิงแต้ม!
            for lane in [0, 2]:
                # 2.1 Combat Damage Step (กฎข้อ 443.1 & 444.1.a.1: หักล้าง Might พร้อมกันและฟื้นฟูยูนิตที่รอดชีวิต)
                if self.my_might[lane] > 0 and self.enemy_might[lane] > 0:
                    my_old_might = self.my_might[lane]
                    enemy_old_might = self.enemy_might[lane]

                    # คำนวณความเสียหายโดยหักล้างด้วยเกราะจากสิ่งปลูกสร้าง Gear (แต่ละ Gear ช่วยซับแรงปะทะลง 1.0 หน่วย)
                    my_damage_taken = max(0.0, enemy_old_might - 1.0 * self.my_gears[lane])
                    enemy_damage_taken = max(0.0, my_old_might - 1.0 * self.enemy_gears[lane])

                    # ตรวจสอบการรอดชีวิต: ถ้ารับความเสียหายไม่ถึงขั้นตายนับว่ารอด
                    my_survived = my_damage_taken < my_old_might
                    enemy_survived = enemy_damage_taken < enemy_old_might

                    # กฎการรักษายูนิต (Heal all Units - 444.1.a.1): ยูนิตที่รอดชีวิตจะได้รับการฟื้นฟูพลังชีวิตกลับมาเต็มร้อย!
                    my_post_might = my_old_might if my_survived else 0.0
                    enemy_post_might = enemy_old_might if enemy_survived else 0.0

                    # กฎการดึงยูนิตกลับฐาน (Attacker Recall Rule 444.1.a.2)
                    # หากต่างฝ่ายต่างรอดชีวิต (Might > 0 ทั้งคู่) ยูนิตบุกรบ (Attacker) จะต้องถูกริบกลับฐาน
                    if my_survived and enemy_survived:
                        self.my_might[lane] = 0.0  # Recall กลับฐาน!
                        self.enemy_might[lane] = enemy_post_might
                    else:
                        self.my_might[lane] = my_post_might
                        self.enemy_might[lane] = enemy_post_might

                # 2.2 Resolution Step (กฎข้อ 444.2): สถาปนาการควบคุม (Establish Control)
                # ผู้เล่นที่หลงเหลือ Unit อยู่เลนฝ่ายเดียวจะได้รับสิทธิ์ควบคุมสนามรบเลนนั้น
                old_control = self.battlefield_control[lane]

                if self.my_might[lane] > 0 and self.enemy_might[lane] == 0:
                    self.battlefield_control[lane] = 1  # เราเข้าควบคุม
                    if old_control != 1:  # กฎพิชิตเลน Conquer (446.1)
                        # กฎแต้มสุดท้าย (Final Point Restriction 448.1.b)
                        if self.my_score < 7:
                            self.my_score += 1
                            self.my_scored_lanes_this_turn[lane] = True
                            reward += 2.5  # รางวัลใหญ่จากการ Conquer ดินแดนใหม่!
                        elif self.my_score == 7:
                            # มาร์กว่าเราทำผลงานในเลนนี้แล้ว
                            self.my_scored_lanes_this_turn[lane] = True
                            # ตรวจสอบว่าในเทิร์นนี้เราเก็บคะแนนได้ครบทั้งเลนซ้ายและเลนขวาหรือไม่ (ซ้าย=0, ขวา=2)
                            if self.my_scored_lanes_this_turn[0] and self.my_scored_lanes_this_turn[2]:
                                self.my_score += 1  # ได้แต้มสุดท้าย (Final Point) ชนะทันที!
                                reward += 20.0
                            else:
                                # คะแนนยังยึดไม่ครบทั้งสองเลนในเทิร์นนี้ เปลี่ยนเป็นจั่วการ์ดแทนตามกฎ 448.1.b.2!
                                reward += 0.5  # รางวัลชดเชยสำหรับการจั่วการ์ด
                                
                elif self.enemy_might[lane] > 0 and self.my_might[lane] == 0:
                    self.battlefield_control[lane] = -1  # ศัตรูคุม
                    if old_control != -1:  # ศัตรู Conquer
                        if self.enemy_score < 7:
                            self.enemy_score += 1
                            self.enemy_scored_lanes_this_turn[lane] = True
                            reward -= 1.5  # โดนล่วงล้ำเขต
                        elif self.enemy_score == 7:
                            self.enemy_scored_lanes_this_turn[lane] = True
                            if self.enemy_scored_lanes_this_turn[0] and self.enemy_scored_lanes_this_turn[2]:
                                self.enemy_score += 1
                        
                elif self.my_might[lane] == 0 and self.enemy_might[lane] == 0:
                    # ไร้ยูนิตประจำการ เลนกลายเป็นพื้นที่รกร้างว่างเปล่า (444.2.d)
                    self.battlefield_control[lane] = 0

            # 3. เริ่มต้นเทิร์นใหม่ของรอบการเล่นถัดไป (Start of Next Turn ตามกฎ PDF 315)
            # 3.1 Beginning Phase - Scoring Step (315.2.b / 446.2): ได้รับแต้มจากการ Hold เฉพาะเลนซ้ายและขวา
            for lane in [0, 2]:
                if self.battlefield_control[lane] == 1:
                    # ตรวจสอบกฎแต้มสุดท้ายสำหรับการ Hold (ซึ่งสามารถเก็บแต้มสุดท้ายชนะได้ทันทีโดยไม่มีข้อจำกัด)
                    if self.my_score < 7:
                        self.my_score += 1
                        self.my_scored_lanes_this_turn[lane] = True
                        reward += 1.5  # รางวัลจากการป้องกันครอบครองเลนสำเร็จ (Hold)
                    elif self.my_score == 7:
                        self.my_score += 1
                        self.my_scored_lanes_this_turn[lane] = True
                        reward += 15.0  # โบนัสชนะเกมด้วย Hold
                elif self.battlefield_control[lane] == -1:
                    if self.enemy_score < 7:
                        self.enemy_score += 1
                        self.enemy_scored_lanes_this_turn[lane] = True
                        reward -= 0.8  # หักคะแนนเพราะศัตรู Hold เลนได้แต้ม
                    elif self.enemy_score == 7:
                        self.enemy_score += 1
                        self.enemy_scored_lanes_this_turn[lane] = True

            # 3.2 Channel Phase (315.3 / 417): จ่ายพลังงานขึ้นรอบใหม่ (รูนพูลเดิมจะเคลียร์ทิ้งเมื่อจบเทิร์น)
            # ผู้เล่นจะเติมพลังงานเท่ากับค่าพื้นฐาน 3.0 + โบนัสเศรษฐกิจจาก Gear ทั้งหมด (รวมที่สะสมอยู่ตรงกลางด้วย)
            self.my_energy = min(3.0 + 0.5 * np.sum(self.my_gears), 10.0)
            self.enemy_energy = min(3.0 + 0.5 * np.sum(self.enemy_gears), 10.0)

            self.turn_count += 1
#เก็บคะแนนได้ครบทั้ง 3 เลน (ผ่านการ Hold หรือ Conquer อื่นๆ) หรือไม่
            if all(self.my_scored_lanes_this_turn):
                self.my_score += 1  # ได้แต้มสุดท้าย (Final Point) ชนะทันที!
                reward += 20.0
            else:
        # คะแนนยังยึดไม่ครบทุกเลนในเทิร์นนี้ เปลี่ยนเป็นจั่วการ์ดแทนตามกฎ 448.1.b.2!
                reward += 0.5  # รางวัลชดเชยสำหรับการจั่วการ์ด
                                
                elif self.enemy_might[lane] > 0 and self.my_might[lane] == 0:
                    self.battlefield_control[lane] = -1  # ศัตรูคุม
                    if old_control != -1:  # ศัตรู Conquer
                        if self.enemy_score < 7:
                            self.enemy_score += 1
                            self.enemy_scored_lanes_this_turn[lane] = True
                            reward -= 1.5  # โดนล่วงล้ำเขต
                        elif self.enemy_score == 7:
                            self.enemy_scored_lanes_this_turn[lane] = True
                            if all(self.enemy_scored_lanes_this_turn):
                                self.enemy_score += 1
                        
                elif self.my_might[lane] == 0 and self.enemy_might[lane] == 0:
                    # ไร้ยูนิตประจำการ เลนกลายเป็นพื้นที่รกร้างว่างเปล่า (444.2.d)
                    self.battlefield_control[lane] = 0

            # 3. เริ่มต้นเทิร์นใหม่ของรอบการเล่นถัดไป (Start of Next Turn ตามกฎ PDF 315)
            # 3.1 Beginning Phase - Scoring Step (315.2.b / 446.2): ได้รับแต้มสะสมจากการ Hold เลนที่ยังครอบครองไว้
            for lane in range(3):
                if self.battlefield_control[lane] == 1:
                    # ตรวจสอบกฎแต้มสุดท้ายสำหรับการ Hold (ซึ่งสามารถเก็บแต้มสุดท้ายชนะได้ทันทีโดยไม่มีข้อจำกัด)
                    if self.my_score < 7:
                        self.my_score += 1
                        self.my_scored_lanes_this_turn[lane] = True
                        reward += 1.5  # รางวัลจากการป้องกันครอบครองเลนสำเร็จ (Hold)
                    elif self.my_score == 7:
                        self.my_score += 1
                        self.my_scored_lanes_this_turn[lane] = True
                        reward += 15.0  # โบนัสชนะเกมด้วย Hold
                elif self.battlefield_control[lane] == -1:
                    if self.enemy_score < 7:
                        self.enemy_score += 1
                        self.enemy_scored_lanes_this_turn[lane] = True
                        reward -= 0.8  # หักคะแนนเพราะศัตรู Hold เลนได้แต้ม
                    elif self.enemy_score == 7:
                        self.enemy_score += 1
                        self.enemy_scored_lanes_this_turn[lane] = True

            # 3.2 Channel Phase (315.3 / 417): จ่ายพลังงานขึ้นรอบใหม่ + โบนัสเศรษฐกิจจาก Gear การ์ด
            my_bonus = 0.5 * np.sum(self.my_gears)
            enemy_bonus = 0.5 * np.sum(self.enemy_gears)

            self.my_energy = min(self.my_energy + 3.0 + my_bonus, 10.0)
            self.enemy_energy = min(self.enemy_energy + 3.0 + enemy_bonus, 10.0)

            self.turn_count += 1

        # 4. ตรวจสอบเงื่อนไขการจบเกม (แต้มสากลสะสม 8 คะแนน)
        if self.my_score >= 8:
            reward += 20.0  # 🎉 โบนัสใหญ่คว้าชัยเกมตามกฎ
            terminated = True
        elif self.enemy_score >= 8:
            reward -= 10.0  # ❌ โดนปรับแต้มพ่ายแพ้
            terminated = True

        return self._get_obs(), reward, terminated, truncated, {}



# 🧪 ส่วนรันการฝึกฝน AI (Training Loop) และจำลองการเล่นจริง
if __name__ == "__main__":
    from stable_baselines3 import PPO
    from stable_baselines3.common.env_checker import check_env
    
    # 1. ค้นหาไฟล์ clean JSON ที่จะใช้เป็นฐานข้อมูลหลัก
    dataset_file = "origins_clean.json"
    if not os.path.exists(dataset_file):
        clean_files = [f for f in os.listdir(".") if f.endswith("_clean.json")]
        if clean_files:
            dataset_file = clean_files[0]
        else:
            dataset_file = "mock_dataset.json"
            with open(dataset_file, "w", encoding="utf-8") as f:
                json.dump([{"name": "Mock Card", "cardType": "Unit", "domain": "Fury", "energyCost": 2}], f)

    print(f"📦 กำลังเริ่มต้นระบบด้วยไฟล์ดาต้าเซ็ต: {dataset_file}")
    
    # 2. สร้าง Environment และตรวจสอบความเข้ากันได้ตามมาตรฐาน Gymnasium / Stable-Baselines3
    env = OfficialRiftboundEnv(dataset_file)
    
    print("🔍 กำลังตรวจสอบโครงสร้าง Environment...")
    check_env(env, warn=True)
    print("✅ Environment โครงสร้างถูกต้องตามมาตรฐานสากลและกฎ PDF Core Rules v1.2!")

    # 3. กำหนดค่าและสร้างโมเดล PPO (Proximal Policy Optimization) 
    # บังคับรันบน CPU เพื่อให้เสถียรบน Windows + AMD GPU แบบ 100%
    print("\n🤖 กำลังจัดเตรียมโครงข่ายประสาทเทียมโมเดล PPO...")
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=0.0003,
        n_steps=1024,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        device="cpu", 
        seed=42
    )

    # 4. ฝึกฝน AI (Training) ความเร็วสูง
    training_steps = 35000  
    print(f"🏋️‍♂️ กำลังเริ่มเทรน AI จำนวน {training_steps} steps... (รันบน CPU ความเร็วสูง)")
    model.learn(total_timesteps=training_steps)
    print("🏆 เทรน AI สำเร็จเสร็จสิ้น!")

    # 5. เซฟโมเดลเก็บไว้ใช้งานต่อ
    model_name = "riftbound_ppo_agent"
    model.save(model_name)
    print(f"💾 บันทึกโมเดล AI ไว้ที่: {model_name}.zip")

    # 6. จำลองภาพเหตุการณ์การเล่นจริง (Evaluation Rollout)
    print("\n🎮 [Evaluation] เริ่มต้นโหมดจำลองการดวลจริงของ AI (ตามกฎระเบียบ Riftbound v1.2):")
    print("=" * 70)
    
    obs, info = env.reset()
    done = False
    step_num = 1
    
    # แปลงสถานะการควบคุมบอร์ดออกมาเป็นข้อความสวยงาม
    def get_control_text(ctrl_array):
        mapping = {1.0: "⭐ คุม", -1.0: "💀 ศัตรูคุม", 0.0: "⚪ ว่าง"}
        return [mapping[c] for c in ctrl_array]
    
    while not done and step_num <= 40:
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        
        # ถอดรหัสรายละเอียดการเคลื่อนไหวของ AI
        action_desc = "Pass (สิ้นสุดเฟสส่งไม้ต่อ)"
        if action > 0:
            lane_name = ["เลนซ้าย", "เลนกลาง", "เลนขวา"][(action - 1) // 3]
            card_name = ["Unit (ทหารรบ)", "Gear (เศรษฐกิจ)", "Spell (เวททำลาย)"][(action - 1) % 3]
            action_desc = f"เล่น {card_name} ลง {lane_name}"
            
        print(f"Turn {env.turn_count} | Step {step_num}")
        print(f"🤖 Action ของ AI: {action_desc} (Action ID: {action})")
        print(f"📊 พลัง Might ของเรา:  {env.my_might} | พลัง Might ศัตรู: {env.enemy_might}")
        print(f"🛠️ สิ่งปลูกสร้าง Gear: เรา {env.my_gears} | ศัตรู {env.enemy_gears}")
        print(f"🚩 การควบคุมเลน:      {get_control_text(env.battlefield_control)}")
        print(f"⚡ พลังงานคงเหลือ:    เรา {env.my_energy:.1f} / ศัตรู {env.enemy_energy:.1f} (+0.5 ต่อ Gear)")
        print(f"🏆 แต้มชัยชนะ (Score): เรา {env.my_score} / ศัตรู {env.enemy_score} (ถึง 8 ชนะ)")
        print(f"🎁 Reward ของก้าวนี้:  {reward:+.3f}")
        print("-" * 70)
        step_num += 1

    print("🎉 สิ้นสุดการจำลองการรบตามกติกาสากล v1.2!")
    print(f"🏆 คะแนนสุดท้าย: AI ฝั่งเรา {env.my_score} คะแนน | ศัตรู {env.enemy_score} คะแนน")
    print("=" * 70)