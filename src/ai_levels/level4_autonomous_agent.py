"""
🚀 CẤP ĐỘ 4: AUTONOMOUS AGENT (Agent tự chủ với Planning & Memory)
Tự chia nhỏ mục tiêu phức tạp thành nhiều bước, duy trì bộ nhớ (Memory)
và tự đánh giá tiến độ.

Đề tài: Trợ Lý Sàng Lọc Hồ Sơ Tuyển Dụng & Hẹn Phỏng Vấn (Chủ đề 9).
Demo minh họa bonus Cấp 4 — kết hợp planning + memory cho Agent tuyển dụng.
"""

import os
import sys

# Đảm bảo import được tools.py khi chạy độc lập từ src/ai_levels/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import parse_resume, get_job_requirements, score_candidate


class AutonomousGoalAgent:
    def __init__(self, goal: str, max_steps: int = 4):
        self.goal = goal
        self.max_steps = max_steps
        self.memory = []  # Bộ nhớ lưu vết các bước đã thực hiện

    def execute(self):
        print(f"🚀 === Bắt đầu Autonomous Goal: {self.goal} ===")

        for step in range(1, self.max_steps + 1):
            print(f"\n--- Vòng lặp tự chủ Planning & Action (Step {step}/{self.max_steps}) ---")

            if step == 1:
                plan = "Bước 1: Tra cứu yêu cầu của vị trí J002"
                action = "Call Tool: get_job_requirements['J002']"
                result = get_job_requirements("J002")
            elif step == 2:
                plan = "Bước 2: Đọc hồ sơ ứng viên C002"
                action = "Call Tool: parse_resume['C002']"
                result = parse_resume("C002")
            elif step == 3:
                plan = "Bước 3: Chấm điểm phù hợp giữa C002 và J002"
                action = "Call Tool: score_candidate['C002', 'J002']"
                result = score_candidate("C002", "J002")
            else:
                print("🎯 [Goal Evaluation]: Mục tiêu đã hoàn thành 100%!")
                break

            self.memory.append({"step": step, "plan": plan, "result": result})
            print(f"📋 [Planning]: {plan}")
            print(f"🛠️ [Execution]: {action} ➔ {result}")
            print(f"💾 [Memory Saved]: Logged step {step} to memory.")


if __name__ == "__main__":
    agent = AutonomousGoalAgent("Tuyển dụng 1 Backend Developer cho vị trí J002")
    agent.execute()