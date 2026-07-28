"""
🧠 CẤP ĐỘ 3: REACTIVE AGENT (ReAct Agent - Thought -> Action -> Observation)
Agent biết suy luận (Thought), tự quyết định gọi Tool thực tế (Action),
rồi quan sát kết quả (Observation) để đưa ra Final Answer.

Đề tài: Trợ Lý Sàng Lọc Hồ Sơ Tuyển Dụng & Hẹn Phỏng Vấn (Chủ đề 9).
File demo minh họa Cấp 3 — tham khảo cùng `src/app.py` để thấy bản tích hợp hoàn chỉnh.
"""

import os
import sys

# Đảm bảo import được tools.py khi chạy độc lập từ src/ai_levels/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import 2 tool chính từ src/tools.py của Role 2
from tools import parse_resume, score_candidate


def reactive_agent_step(user_goal: str):
    """Demo Thought -> Action -> Observation với TC3 (C002 vs J002)."""
    print(f"🎯 Goal: {user_goal}")

    # Step 1: parse_resume -> lấy thông tin ứng viên
    print("\n🧠 [Thought 1]: Cần tra cứu hồ sơ C002 trước.")
    print("🛠️ [Action 1] : parse_resume['C002']")
    obs1 = parse_resume("C002")
    print(f"👁️ [Observation 1]: {obs1}")

    # Step 2: score_candidate -> chấm điểm
    print("\n🧠 [Thought 2]: Có rồi, giờ chấm điểm với job J002.")
    print("🛠️ [Action 2] : score_candidate['C002', 'J002']")
    obs2 = score_candidate("C002", "J002")
    print(f"👁️ [Observation 2]: {obs2}")

    # Step 3: Final Answer tổng hợp
    print("\n🧠 [Thought 3]: Đã có đủ dữ liệu, đưa ra kết luận.")
    print("🏁 [Final Answer]: Ứng viên C002 (Trần Thị B) phù hợp 100% với vị trí "
          "J002 (Backend Developer) — Recommend phỏng vấn.")


if __name__ == "__main__":
    print("=== DEMO CẤP ĐỘ 3: REACTIVE AGENT (ReAct Loop) ===")
    reactive_agent_step("Kiểm tra C002 có phù hợp với vị trí J002 không?")