"""
🚀 CORE AGENT APP (Dành cho Role 4: Core Agent Developer / Integrator)
File chính ghép nối tất cả các thành phần: Tools (Role 2) + Prompts (Role 3)
+ Test Cases (Role 1) + Multi-Provider LLM Adapter (src/providers.py).

Mốc 2 (Baseline Chatbot & Tool Specs):
  - run_baseline_chatbot() chạy được với 5 test case từ config/test_cases.json
  - run_react_agent() hiện là STUB sẽ hoàn thiện ở Mốc 3.
"""

import json
import os
import sys
from dotenv import load_dotenv

# Đảm bảo import các module cùng thư mục src/ hoạt động mượt mà
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Import các thành phần từ file của Role 2 (Tools), Role 3 (Prompts) và Provider
from tools import AVAILABLE_TOOLS  # Role 2
from prompts import (
    CHATBOT_BASELINE_PROMPT,  # Role 3
    REACT_SYSTEM_PROMPT,      # Role 3 (dùng cho Mốc 3)
    REACT_SYSTEM_PROMPT_V2,   # Role 3 (dùng cho Mốc 3)
    MAX_ITERATIONS,           # Role 3 - Guardrail
)
from providers import get_llm_provider  # Multi-Provider Adapter

load_dotenv()


def load_test_cases():
    """Đọc bộ test cases từ config/test_cases.json của Role 1."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")

    # Fallback kiểm tra nếu file ở thư mục hiện tại
    if not os.path.exists(config_path):
        config_path = "test_cases.json"

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_baseline_chatbot(user_query: str, provider, test_meta: dict | None = None):
    """
    Dựng Chatbot gốc (Baseline) KHÔNG có công cụ - Cấp 2 LLM thuần.

    Chỉ 1 LLM call duy nhất:
        system_prompt (CHATBOT_BASELINE_PROMPT) + user_query -> final response

    KHÔNG gọi tool. KHÔNG nhúng sẵn kết quả tool vào prompt.
    Mục đích: làm đường cơ sở so sánh với ReAct Agent ở Mốc 3.
    """
    tag = f" [{test_meta['type']}]" if test_meta else ""
    print(f"\n💬 [CHATBOT BASELINE]{tag} Câu hỏi: {user_query}")

    # Gọi LLM Provider thực hiện 1 lần duy nhất
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot trả lời:\n{response}")
    return response


def run_react_agent(user_query: str, provider, test_meta: dict | None = None):
    """
    STUB cho Mốc 3: Vòng lặp ReAct Agent (Thought -> Action -> Observation)
    có Guardrails sẽ được Vibe Code hoàn thiện ở Mốc 3.

    Mốc 2 hiện chỉ in ra thông báo để xác nhận Agent chưa chạy thật.
    Khi sang Mốc 3 sẽ thay bằng:
      - while step < MAX_ITERATIONS:
          - Parse Thought/Action từ LLM output
          - Thực thi tool từ AVAILABLE_TOOLS
          - Append Observation, quay lại vòng lặp
      - Phanh MAX_ITERATIONS + Safe Fallback.
    """
    tag = f" [{test_meta['type']}]" if test_meta else ""
    print(f"\n🤖 [REACT AGENT - STUB]{tag} Câu hỏi: {user_query}")
    print(
        "⏳ ReAct Agent loop sẽ được lắp ráp ở Mốc 3.\n"
        f"   (Báo trước: phanh an toàn MAX_ITERATIONS = {MAX_ITERATIONS})"
    )
    # TODO(Mốc 3): thay stub bằng vòng lặp ReAct thật, dùng REACT_SYSTEM_PROMPT
    # hoặc REACT_SYSTEM_PROMPT_V2 + parser + executor + MAX_ITERATIONS.


def run_all_baseline_cases(provider, tests: list[dict]):
    """Chạy Chatbot Baseline trên toàn bộ 5 test case (Mốc 2 yêu cầu)."""
    print("\n" + "=" * 70)
    print("🚀 MỐC 2 - CHATBOT BASELINE (Không có tool, 1 LLM call / câu hỏi)")
    print("=" * 70)
    results = []
    for tc in tests:
        response = run_baseline_chatbot(
            tc["question"], provider,
            test_meta={"id": tc["id"], "type": tc["type"]},
        )
        results.append({
            "id": tc["id"],
            "type": tc["type"],
            "question": tc["question"],
            "response": response,
        })
    return results


if __name__ == "__main__":
    print("=" * 70)
    print("🏫 ĐẠI HỌC VINUNI - BÀI LAB 3: CHATBOT VS REACT AGENT")
    print("=" * 70)

    # Khởi tạo Multi-Provider LLM Adapter (đọc từ biến môi trường LLM_PROVIDER)
    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    print(f"🔌 LLM Provider đang hoạt động: {provider.__class__.__name__} (Model: {model_name})")

    # Load test cases của Role 1
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases từ config/test_cases.json")

    # In tóm tắt tool registry của Role 2
    print(f"🛠️  Tool registry (Role 2) đã đăng ký {len(AVAILABLE_TOOLS)} tool: "
          f"{', '.join(AVAILABLE_TOOLS.keys())}")
    print(f"🧠 Guardrail MAX_ITERATIONS = {MAX_ITERATIONS} (Role 3)")

    # ---- DEMO 1: CHẠY CHATBOT BASELINE TRÊN TOÀN BỘ 5 TEST CASE ----
    baseline_results = run_all_baseline_cases(provider, tests)

    # ---- DEMO 2: STUB REACT AGENT (chỉ chạy câu TC3 để xác nhận skeleton) ----
    print("\n" + "=" * 70)
    print("🤖 MỐC 3 PREVIEW - STUB REACT AGENT (sẽ hoàn thiện ở Mốc 3)")
    print("=" * 70)
    sample = tests[2]  # TC3 - Multi-step 2 tools
    run_react_agent(sample["question"], provider,
                    test_meta={"id": sample["id"], "type": sample["type"]})

    # ---- Kết thúc Mốc 2: nhắc Role 5 lưu trace ----
    print("\n" + "=" * 70)
    print("✅ MỐC 2 HOÀN THÀNH (phần Role 4 - Integrator)")
    print("👉 Role 5: hãy dán baseline_results vào docs/trace_eval.md để đánh giá.")
    print("👉 Cả nhóm: chuẩn bị sang MỐC 3 - ReAct Loop & Safeguards.")
    print("=" * 70)