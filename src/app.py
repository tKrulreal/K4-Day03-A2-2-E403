"""
🚀 CORE AGENT APP (Dành cho Role 4: Core Agent Developer / Integrator)
File chính ghép nối tất cả các thành phần: Tools (Role 2) + Prompts (Role 3)
+ Test Cases (Role 1) + Multi-Provider LLM Adapter (src/providers.py).

Mốc 2 (Baseline Chatbot & Tool Specs):
  - run_baseline_chatbot() — 1 LLM call / câu hỏi, KHÔNG có tool.

Mốc 3 (ReAct Agent Loop & Safeguards):
  - run_react_agent() — vòng lặp Thought -> Action -> Observation với parser,
    executor, anti-loop, MAX_ITERATIONS, Safe Fallback, PII filter.

Mốc 4 (Cross-Audit & Hybrid Flowchart):
  - File docs/hybrid_flowchart.mermaid mô tả phân luồng Chatbot vs ReAct Agent.
  - Section 4 của docs/trace_eval.md đã được điền khung Cross-Audit.
"""

import json
import os
import re
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
    CHATBOT_BASELINE_PROMPT,      # Role 3 - dùng cho Mốc 2
    MAX_ITERATIONS,               # Role 3 - Guardrail cứng
    MAX_REPEATED_ACTIONS,          # Role 3 - Guardrail chống loop
    SCORE_THRESHOLD_QUALIFIED,     # Role 3 - Ngưỡng đạt
    SCORE_THRESHOLD_MAYBE,         # Role 3 - Ngưỡng cân nhắc
    PII_BLACKLIST,                 # Role 3 - Từ khóa phải che
    REACT_SYSTEM_PROMPT,           # Role 3 - V1
    REACT_SYSTEM_PROMPT_V2,        # Role 3 - V2 (Self-Recovery + Anti-Loop)
    render_for_test_case,          # Role 3 - Helper render prompt
    render_safe_fallback,          # Role 3 - Helper render Safe Fallback
    SAFE_FALLBACK_MESSAGE,         # Role 3 - Template safe fallback
    WELCOME_MESSAGE,               # Role 3 - TC1 intro
)
from providers import get_llm_provider  # Multi-Provider Adapter

load_dotenv()


# ============================================================
# 🔧 PHẦN 1: TOOL SCHEMA (Dùng cho render_for_test_case của Role 3)
# ============================================================
# Role 3 cần list[dict] với 4 key: name, description, parameters, example.
# Format này được _format_tool_descriptions() trong prompts.py render thành markdown.

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "parse_resume",
        "description": "Tra cứu hồ sơ ứng viên theo mã ID và trả về tóm tắt (tên, kỹ năng, số năm kinh nghiệm, học vấn).",
        "parameters": {"candidate_id": "str"},
        "example": 'parse_resume["C001"]',
    },
    {
        "name": "get_job_requirements",
        "description": "Tra cứu yêu cầu kỹ năng và số năm kinh nghiệm tối thiểu của một vị trí tuyển dụng.",
        "parameters": {"job_id": "str"},
        "example": 'get_job_requirements["J002"]',
    },
    {
        "name": "score_candidate",
        "description": "Tính điểm phù hợp (%) giữa ứng viên và vị trí, liệt kê kỹ năng trùng khớp và đánh giá kinh nghiệm.",
        "parameters": {"candidate_id": "str", "job_id": "str"},
        "example": 'score_candidate["C001", "J001"]',
    },
    {
        "name": "check_interviewer_availability",
        "description": "Xem các khung giờ trống của một interviewer trong hệ thống lịch phỏng vấn.",
        "parameters": {"interviewer_id": "str"},
        "example": 'check_interviewer_availability["interviewer_1"]',
    },
    {
        "name": "schedule_interview",
        "description": "Đặt lịch phỏng vấn cho ứng viên với một interviewer tại một khung giờ cụ thể (chỉ gọi sau khi score_candidate >= 70%).",
        "parameters": {"candidate_id": "str", "interviewer_id": "str", "slot": "str"},
        "example": 'schedule_interview["C001", "interviewer_1", "2026-08-01 09:00"]',
    },
]


# ============================================================
# 🧪 PHẦN 2: TEST CASE LOADER (Role 1)
# ============================================================

def load_test_cases() -> list[dict]:
    """Đọc bộ test cases từ config/test_cases.json của Role 1."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")

    # Fallback kiểm tra nếu file ở thư mục hiện tại
    if not os.path.exists(config_path):
        config_path = "test_cases.json"

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 💬 PHẦN 3: MỐC 2 — CHATBOT BASELINE (Không tool)
# ============================================================

def run_baseline_chatbot(user_query: str, provider, test_meta: dict | None = None):
    """
    Dựng Chatbot gốc (Baseline) KHÔNG có công cụ - Cấp 2 LLM thuần.

    Chỉ 1 LLM call duy nhất:
        system_prompt (CHATBOT_BASELINE_PROMPT) + user_query -> final response.

    KHÔNG gọi tool. KHÔNG nhúng sẵn kết quả tool vào prompt.
    Mục đích: làm đường cơ sở so sánh với ReAct Agent ở Mốc 3.
    """
    tag = f" [{test_meta['type']}]" if test_meta else ""
    print(f"\n💬 [CHATBOT BASELINE]{tag} Câu hỏi: {user_query}")

    # Gọi LLM Provider thực hiện 1 lần duy nhất
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot trả lời:\n{response}")
    return response


# ============================================================
# 🧠 PHẦN 4: MỐC 3 — REACT AGENT (Thought -> Action -> Observation)
# ============================================================

# ---- 4.1. Regex parser cho Thought / Action / Final Answer ----
_FINAL_RE = re.compile(
    r"Final\s*Answer\s*[:\-]\s*(?P<ans>.+?)(?:\Z|(?:\n\s*Thought\s*:|\n\s*Action\s*:))",
    re.IGNORECASE | re.DOTALL,
)
_ACTION_RE = re.compile(
    r"Action\s*[:\-]\s*(?P<tool>[a-zA-Z_][a-zA-Z0-9_]*)\s*\[(?P<args>.+?)\]\s*"
    r"(?:\Z|(?=\n\s*Thought|\n\s*Final|\n\s*Observation))",
    re.DOTALL,
)
_THOUGHT_RE = re.compile(
    r"Thought\s*[:\-]\s*(?P<th>.+?)(?=\n\s*Action\s*:|\n\s*Final\s*Answer|$)",
    re.IGNORECASE | re.DOTALL,
)


def parse_llm_output(text: str) -> dict:
    """
    Parse output của LLM thành 1 trong 3 dạng:
      - {"type": "final",  "answer": "..."}     -> có Final Answer
      - {"type": "action", "tool": "...", "args": [...|dict]}  -> có Action
      - {"type": "error",  "message": "..."}    -> không parse được
    """
    text = text.strip()
    if not text:
        return {"type": "error", "message": "LLM trả về chuỗi rỗng."}

    # 1) Ưu tiên Final Answer
    m_final = _FINAL_RE.search(text)
    if m_final:
        return {"type": "final", "answer": m_final.group("ans").strip()}

    # 2) Sau đó mới tới Action
    m_action = _ACTION_RE.search(text)
    if m_action:
        tool = m_action.group("tool")
        args_raw = m_action.group("args").strip()
        # Thử parse JSON trước (format `["C001"]` hoặc `{"k":"v"}`)
        try:
            args = json.loads(args_raw)
            if isinstance(args, dict):
                return {"type": "action", "tool": tool, "args": args}
            return {"type": "action", "tool": tool, "args": list(args)}
        except json.JSONDecodeError:
            # Fallback: parse CSV (format ReAct V2: `C001` hoặc `C001,J001`)
            # Strip quotes nếu có
            parts = [p.strip().strip("\"'") for p in args_raw.split(",")]
            parts = [p for p in parts if p]
            if len(parts) == 1:
                return {"type": "action", "tool": tool, "args": parts[0]}
            return {"type": "action", "tool": tool, "args": parts}

    # 3) Không tìm được gì -> error
    return {
        "type": "error",
        "message": (
            "Không tìm thấy 'Final Answer:' hoặc 'Action: tool[...]' trong output LLM. "
            "Hãy in lại đúng format."
        ),
    }


def extract_thought(text: str) -> str | None:
    """Lấy Thought mới nhất trong output (ngay trước Action/Final)."""
    m = _THOUGHT_RE.search(text)
    return m.group("th").strip() if m else None


def _normalize_args_key(args) -> tuple:
    """Chuẩn hoá args thành tuple để so sánh anti-loop."""
    if isinstance(args, dict):
        return tuple(sorted(args.items()))
    if isinstance(args, (list, tuple)):
        return tuple(args)
    return (args,)


def check_repeated_action(history: list[tuple[str, tuple]], current: tuple[str, tuple]) -> int:
    """
    Đếm số lần xuất hiện liên tiếp cuối cùng của `current` trong `history`.

    Trả về số lần lặp liên tiếc (>= 2 nghĩa là đáng ngờ kẹt loop).
    """
    count = 0
    for entry in reversed(history):
        if entry == current:
            count += 1
        else:
            break
    return count


def execute_tool(tool_name: str, args) -> str:
    """
    Thực thi 1 tool từ AVAILABLE_TOOLS. Bắt mọi exception, không bao giờ để crash.

    Mapping lỗi:
      - KeyError      -> "LỖI UNKNOWN_TOOL" (F1)
      - TypeError     -> "LỖI INVALID_ARG"  (F11)
      - Exception khác -> "LỖI EXCEPTION"
    """
    if tool_name not in AVAILABLE_TOOLS:
        valid = ", ".join(sorted(AVAILABLE_TOOLS.keys()))
        return f"LỖI UNKNOWN_TOOL: '{tool_name}' không có trong registry. Tool hợp lệ: [{valid}]"

    fn = AVAILABLE_TOOLS[tool_name]
    try:
        if isinstance(args, dict):
            return fn(**args)
        if isinstance(args, (list, tuple)):
            return fn(*args)
        # args is a single value (string/int) – pass as positional
        return fn(args)
    except TypeError as e:
        return f"LỖI INVALID_ARG: {e}. Cú pháp gọi hàm không khớp tham số."
    except Exception as e:  # pylint: disable=broad-except
        return f"LỖI EXCEPTION khi gọi {tool_name}: {type(e).__name__}: {e}"


def filter_pii(text: str) -> str:
    """
    Che (redact) mọi keyword trong PII_BLACKLIST xuất hiện trong text.
    Match không phân biệt hoa thường, substring match.
    """
    if not text:
        return text
    out = text
    for keyword in PII_BLACKLIST:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        out = pattern.sub("[REDACTED]", out)
    return out


# ---- 4.2. Mock scenario (khi provider là MockProvider) ----

def _mock_print(step: int, thought: str, action: str | None, observation: str | None) -> None:
    """In 1 step trace theo format chuẩn (giống loop thật)."""
    prefix = "🧪 [MOCK]"
    print(f"\n{prefix} 🔁 Iteration {step}/{MAX_ITERATIONS}")
    print(f"{prefix} 🧠 Thought: {thought}")
    if action is not None:
        print(f"{prefix} 🛠️  Action:  {action}")
    if observation is not None:
        print(f"{prefix} 👁️  Observation: {observation}")


def _mock_final(step: int, final_answer: str, triggered: list[str]) -> dict:
    """In Final Answer theo format + trả dict."""
    print(f"\n🧪 [MOCK] ✅ Final Answer (iter {step}):")
    print(final_answer)
    return {
        "final_answer": final_answer,
        "trace": [{"step": step, "final_answer": final_answer}],
        "iterations": step,
        "reached_max": False,
        "triggered_guardrail": triggered,
    }


def _pick_mock_scenario(user_query: str):
    """
    Chọn scenario mock dựa trên KEYWORD trong user_query (không phụ thuộc tc_id
    vì config/test_cases.json có thể có nhiều hơn 5 test case). Trả về:
      ("theoretical" | "1tool" | "2tools" | "3tools" | "edge_f2f6" |
       "factual_c001" | "compare_c001_c003" | "dynamic_routing" |
       "invalid_slot" | "max_iter_overload" | "no_tool_email" |
       "soft_skills" | "c003_branch" | "edge_f7_invalid_time" |
       "unknown_tool_send_email", step_count_hint)
    """
    q = user_query.lower()

    # Theo thứ tự ưu tiên — check keyword cụ thể trước keyword chung
    # --- Theoretical / soft-skills ---
    if "đóng vai trò" in q or "giúp tôi thực hiện" in q:
        return ("theoretical", 1)
    if "kỹ năng mềm" in q or "làm việc nhóm hiệu quả" in q:
        return ("soft_skills", 1)
    if "mẫu email" in q or "từ chối ứng viên" in q:
        return ("no_tool_email", 1)

    # --- Edge case Unknown Tool (F1) ---
    if "gửi email" in q or "tự động đến" in q:
        return ("unknown_tool_send_email", 2)

    # --- Overload (F10) ---
    if "tất cả các ứng viên" in q or "tất cả các vị trí" in q:
        return ("max_iter_overload", 5)

    # --- Edge case F2 + F6 (C999 + interviewer_2) ---
    if "c999" in q and "interviewer_2" in q:
        return ("edge_f2f6", 2)

    # --- Edge F7 invalid slot ---
    if "2026-10-10 10:00" in q or ("tự bịa" in q and "interviewer_1" in q):
        return ("invalid_slot", 2)
    if "22:00" in q:
        return ("edge_f7_invalid_time", 2)

    # --- Dynamic routing (F5/F6) for C002 + J002 ---
    if "c002" in q and "interviewer_2" in q and "tự động chuyển" in q:
        return ("dynamic_routing", 4)

    # --- Factual C001 ---
    if "c001" in q and "đừng bịa" in q:
        return ("factual_c001", 1)

    # --- Compare C001 vs C003 ---
    if "so sánh" in q and "c001" in q and "c003" in q:
        return ("compare_c001_c003", 2)

    # --- C003 < J001 (Logic branch) ---
    if "c003" in q and "j001" in q:
        return ("c003_branch", 2)

    # --- 3-tools full pipeline (TC4): C001 + J001 + interviewer_1 ---
    if "c001" in q and "j001" in q and "interviewer_1" in q and "đặt lịch" in q:
        return ("3tools", 4)

    # --- 2-tools (TC3): C002 + J002 ---
    if "c002" in q and "j002" in q:
        return ("2tools", 2)

    # --- 1-tool (TC2): J002 alone ---
    if "j002" in q and "backend developer" in q:
        return ("1tool", 1)

    return ("unknown", 0)


def mock_react_scenario(tc_id: int | None, user_query: str) -> dict:
    """
    Trace giả lập cho các test case khi provider là MockProvider.
    Pick scenario theo KEYWORD trong user_query (cover đủ 15 TC).
    """
    print(f"\n🤖 [REACT AGENT — MOCK SCENARIO] Câu hỏi: {user_query}")

    scenario, _hint = _pick_mock_scenario(user_query)

    # ===== TC1 — Theoretical =====
    if scenario == "theoretical":
        _mock_print(1, "Câu chào hỏi → giới thiệu vai trò Agent HR (không cần tool).", None, None)
        return _mock_final(1, WELCOME_MESSAGE, triggered=[])

    # ===== TC2 — 1 tool =====
    if scenario == "1tool":
        _mock_print(
            1, "Cần tra cứu yêu cầu của vị trí J002 (Backend Developer).",
            'get_job_requirements["J002"]',
            "Vị trí J002 (Backend Developer): yêu cầu kỹ năng Java, Spring Boot, ≥3 năm kinh nghiệm.",
        )
        return _mock_final(
            1,
            "📋 Vị trí Backend Developer (J002) yêu cầu:\n"
            "- Kỹ năng: Java, Spring Boot\n"
            "- Số năm kinh nghiệm tối thiểu: 3 năm\n"
            "(Nguồn: get_job_requirements[\"J002\"])",
            triggered=[],
        )

    # ===== TC3 — 2 tools =====
    if scenario == "2tools":
        _mock_print(
            1, "Trước tiên lấy hồ sơ ứng viên C002.",
            'parse_resume["C002"]',
            "Ứng viên C002 (Trần Thị B): kỹ năng Java, Spring, 5 năm kinh nghiệm.",
        )
        _mock_print(
            2, "Có rồi, giờ chấm điểm với job J002.",
            'score_candidate["C002", "J002"]',
            "Điểm phù hợp: 100%. Kỹ năng trùng: Java, Spring. Kinh nghiệm: 5 ≥ 3 năm → ĐỦ.",
        )
        return _mock_final(
            2,
            "✅ Ứng viên C002 (Trần Thị B) phù hợp 100% với vị trí J002 "
            "(Backend Developer, ≥3 năm Java/Spring).\n"
            "(Nguồn: parse_resume[\"C002\"] + score_candidate[\"C002\", \"J002\"])",
            triggered=[],
        )

    # ===== TC4 — 3 tools full pipeline =====
    if scenario == "3tools":
        _mock_print(
            1, "Chấm điểm ứng viên C001 với J001 trước.",
            'score_candidate["C001", "J001"]',
            "Điểm phù hợp: 95%. Kỹ năng trùng: Python, SQL. Kinh nghiệm: 2 ≥ 1 → ĐỦ (>=70%).",
        )
        _mock_print(
            2, "Đạt ngưỡng (>= 70%), xem lịch trống của interviewer_1.",
            'check_interviewer_availability["interviewer_1"]',
            "Lịch trống của interviewer_1: 2026-08-01 09:00, 2026-08-01 14:00.",
        )
        _mock_print(
            3, "Lấy slot đầu tiên → đặt lịch cho C001.",
            'schedule_interview["C001", "interviewer_1", "2026-08-01 09:00"]',
            "Đã đặt lịch phỏng vấn thành công cho ứng viên C001 với interviewer_1 vào 2026-08-01 09:00.",
        )
        return _mock_final(
            3,
            "🎉 Đặt lịch thành công!\n"
            "- Ứng viên: C001\n- Vị trí: J001 (Data Analyst)\n"
            "- Điểm phù hợp: 95%\n- Interviewer: interviewer_1\n"
            "- Khung giờ: 2026-08-01 09:00\n"
            "(Nguồn: score_candidate + check_interviewer_availability + schedule_interview)",
            triggered=[],
        )

    # ===== TC5 — Edge F2 + F6 =====
    if scenario == "edge_f2f6":
        _mock_print(
            1, "Câu bẫy: cần đặt lịch cho C999 với interviewer_2.",
            'schedule_interview["C999", "interviewer_2", "2026-08-01 09:00"]',
            "LỖI NOT_FOUND: Ứng viên 'C999' không tồn tại trong hệ thống. "
            "(Hiện có: C001, C002, C003.)",
        )
        _mock_print(
            2, "Phát hiện LỖI → DỪNG theo Self-Recovery cho F2.", None, None,
        )
        triggered = ["F2_NOT_FOUND"]
        print("\n🧪 [MOCK] ✅ Final Answer (iter 2):")
        final = (
            "⚠️ Không thể đặt lịch như yêu cầu:\n"
            "- F2 NOT_FOUND: Ứng viên 'C999' không tồn tại.\n"
            "- F6 EMPTY_CALENDAR: Interviewer 'interviewer_2' hiện không có lịch trống.\n"
            "📋 Ứng viên hiện có: C001 (Lê Văn A), C002 (Trần Thị B), C003 (Phạm Thị C).\n"
            "💡 Bạn có thể chọn 1 trong 3 ứng viên trên hoặc dùng interviewer_1 (còn lịch)."
        )
        print(final)
        return {
            "final_answer": final, "iterations": 2, "reached_max": False,
            "triggered_guardrail": triggered,
            "trace": [
                {"step": 1, "action": 'schedule_interview["C999","interviewer_2",...]',
                 "observation": "LỖI NOT_FOUND: Ứng viên 'C999' không tồn tại."},
                {"step": 2, "guardrail": "Self-Recovery F2"},
            ],
        }

    # ===== TC6 — Factual C001 (Grounding) =====
    if scenario == "factual_c001":
        _mock_print(1, "Yêu cầu data thật về C001 → tra hồ sơ.",
                    'parse_resume["C001"]',
                    "Ứng viên C001 (Lê Văn A): Python, SQL, ML — 2 năm kinh nghiệm; học vấn ĐH Bách Khoa.")
        return _mock_final(
            1,
            "📋 Ứng viên C001 (Lê Văn A):\n"
            "- Kỹ năng: Python, SQL, ML\n- Số năm kinh nghiệm: 2\n- Học vấn: ĐH Bách Khoa\n"
            "(Nguồn: parse_resume[\"C001\"])",
            triggered=[],
        )

    # ===== TC7 — Compare C001 vs C003 =====
    if scenario == "compare_c001_c003":
        _mock_print(1, "Chấm C001 với J001 trước.",
                    'score_candidate["C001","J001"]',
                    "Điểm phù hợp C001-J001: 95%. Kinh nghiệm: 2 năm (đủ ≥1).")
        _mock_print(2, "Chấm C003 với J001.",
                    'score_candidate["C003","J001"]',
                    "Điểm phù hợp C003-J001: 88%. Kinh nghiệm: 1 năm (đạt đúng ngưỡng).")
        return _mock_final(
            2,
            "🏆 So sánh:\n- C001: 95%\n- C003: 88%\n→ Ưu tiên C001 cho vòng phỏng vấn J001.\n"
            "(Nguồn: score_candidate × 2 lần)",
            triggered=[],
        )

    # ===== TC8 — Dynamic Routing (F5/F6) =====
    if scenario == "dynamic_routing":
        _mock_print(1, "Chấm điểm C002-J002 trước.",
                    'score_candidate["C002","J002"]',
                    "Điểm phù hợp: 100%. Đạt ngưỡng (>=70%).")
        _mock_print(2, "Kiểm tra interviewer_2 trước (theo yêu cầu).",
                    'check_interviewer_availability["interviewer_2"]',
                    "LỖI EMPTY_CALENDAR: Interviewer 'interviewer_2' hiện không có lịch trống.")
        _mock_print(3, "Self-Recovery F6: tự động đổi sang interviewer_1.",
                    'check_interviewer_availability["interviewer_1"]',
                    "Lịch trống của interviewer_1: 2026-08-01 09:00, 2026-08-01 14:00.")
        _mock_print(4, "Đặt lịch slot đầu tiên cho C002.",
                    'schedule_interview["C002","interviewer_1","2026-08-01 09:00"]',
                    "Đã đặt lịch phỏng vấn thành công cho C002 với interviewer_1 vào 2026-08-01 09:00.")
        return _mock_final(
            4,
            "🎉 Đặt lịch thành công cho C002 (đã tự chuyển từ interviewer_2 → interviewer_1):\n"
            "- Khung giờ: 2026-08-01 09:00\n"
            "(Nguồn: score_candidate + check_interviewer_availability × 2 + schedule_interview)",
            triggered=["F6_EMPTY_CALENDAR", "SELF_RECOVERY"],
        )

    # ===== TC9 — Invalid slot =====
    if scenario == "invalid_slot":
        _mock_print(1, "Đặt lịch với slot do user bịa (2026-10-10 10:00).",
                    'schedule_interview["C001","interviewer_1","2026-10-10 10:00"]',
                    "LỖI CONFLICT: Khung giờ '2026-10-10 10:00' không hợp lệ hoặc đã có người đặt.")
        _mock_print(2, "Self-Recovery F7: lấy slot hợp lệ từ check_interviewer_availability.",
                    None, None)
        triggered = ["F7_CONFLICT", "SELF_RECOVERY"]
        final = (
            "⚠️ Slot bạn đưa không hợp lệ (F7 CONFLICT).\n"
            "Lịch trống hiện tại của interviewer_1: 2026-08-01 09:00, 2026-08-01 14:00.\n"
            "💡 Bạn có thể chọn 1 trong 2 slot trên."
        )
        print(f"\n🧪 [MOCK] ✅ Final Answer (iter 2):\n{final}")
        return {
            "final_answer": final, "iterations": 2, "reached_max": False,
            "triggered_guardrail": triggered,
            "trace": [
                {"step": 1, "action": 'schedule_interview["C001","interviewer_1","2026-10-10 10:00"]',
                 "observation": "LỖI CONFLICT: Khung giờ '2026-10-10 10:00' không hợp lệ."},
                {"step": 2, "guardrail": "Self-Recovery F7"},
            ],
        }

    # ===== TC10 — Overload (F10) =====
    if scenario == "max_iter_overload":
        # Cố tình cho trace lặp để trigger MAX_ITERATIONS
        for i in range(1, MAX_ITERATIONS + 1):
            _mock_print(
                i, f"Chấm điểm cặp (C00{(i%3)+1}, J00{((i+1)%2)+1}).",
                f'score_candidate["C00{(i%3)+1}", "J00{((i+1)%2)+1}"]',
                f"Điểm phù hợp: {(70 + (i*3))%40 + 50}% (chưa tìm được max).",
            )
        triggered = ["MAX_ITERATIONS"]
        final = render_safe_fallback([
            "score_candidate C001-J001 ≈ 95%",
            "score_candidate C002-J002 ≈ 100%",
            "score_candidate C003-J001 ≈ 88%",
            "...",
        ])
        print(f"\n🧪 [MOCK] ⚠️ MAX_ITERATIONS reached → Safe Fallback:\n{final}")
        return {
            "final_answer": final, "iterations": MAX_ITERATIONS, "reached_max": True,
            "triggered_guardrail": triggered,
            "trace": [{"step": i, "action": f"score_candidate C00{(i%3)+1},J00{((i+1)%2)+1}",
                       "observation": "..."} for i in range(1, MAX_ITERATIONS+1)]
            + [{"step": MAX_ITERATIONS, "guardrail": "MAX_ITERATIONS"}],
        }

    # ===== TC11 — Email (no tool) =====
    if scenario == "no_tool_email":
        _mock_print(1, "Yêu cầu viết mẫu email → không cần tool, dùng LLM thuần.", None, None)
        return _mock_final(
            1,
            "📧 Mẫu email từ chối (lịch sự):\n\n"
            "Kính gửi Anh/Chị [Họ_Tên],\n"
            "Cảm ơn Anh/Chị đã quan tâm và tham gia vòng phỏng vấn tại công ty...\n"
            "(Chatbot path — không cần tool HR)",
            triggered=[],
        )

    # ===== TC12 — Soft skills theory =====
    if scenario == "soft_skills":
        _mock_print(1, "Câu hỏi lý thuyết HR thuần → Chatbot path.", None, None)
        return _mock_final(
            1,
            "🧠 Kỹ năng mềm cần có của Backend Dev:\n"
            "- Communication: giải thích API/contract với frontend\n"
            "- Teamwork: code review, pair programming\n"
            "- Problem-solving: debug hệ thống phân tán\n"
            "(Không cần tool HR — LLM sinh trực tiếp)",
            triggered=[],
        )

    # ===== TC13 — C003 < J001 (Logic branch) =====
    if scenario == "c003_branch":
        _mock_print(1, "Chấm điểm C003-J001.",
                    'score_candidate["C003","J001"]',
                    "Điểm phù hợp: 88%. Kinh nghiệm: 1 năm (đạt đúng ngưỡng tối thiểu).")
        _mock_print(2, "Tóm tắt + đưa lời khuyên cải thiện (không đặt lịch).", None, None)
        return _mock_final(
            2,
            "✅ Ứng viên C003 (Phạm Thị C) đạt đúng ngưỡng tối thiểu cho J001 (88%, 1 năm KN).\n"
            "💡 Lời khuyên: tích lũy thêm 6-12 tháng làm Python/SQL thực tế sẽ tăng cơ hội.\n"
            "(Nguồn: score_candidate[\"C003\",\"J001\"])",
            triggered=[],
        )

    # ===== TC14 — Edge F7 invalid time 22:00 =====
    if scenario == "edge_f7_invalid_time":
        _mock_print(1, "Đặt lịch vào giờ không hợp lệ 22:00.",
                    'schedule_interview["C001","interviewer_1","2026-08-01 22:00"]',
                    "LỖI CONFLICT: Khung giờ '2026-08-01 22:00' không hợp lệ hoặc đã có người đặt.")
        _mock_print(2, "Từ chối + gợi ý slot hợp lệ trong giờ hành chính.", None, None)
        triggered = ["F7_CONFLICT"]
        final = (
            "⚠️ Khung giờ 22:00 nằm ngoài giờ làm việc (F7 CONFLICT).\n"
            "Lịch trống của interviewer_1 trong giờ HC: 2026-08-01 09:00, 14:00.\n"
            "💡 Vui lòng chọn slot trong khung 08:00–18:00."
        )
        print(f"\n🧪 [MOCK] ✅ Final Answer (iter 2):\n{final}")
        return {
            "final_answer": final, "iterations": 2, "reached_max": False,
            "triggered_guardrail": triggered,
            "trace": [
                {"step": 1, "action": 'schedule_interview["C001","interviewer_1","2026-08-01 22:00"]',
                 "observation": "LỖI CONFLICT: Khung giờ không hợp lệ."},
                {"step": 2, "guardrail": "Từ chối + gợi ý"},
            ],
        }

    # ===== TC15 — Unknown Tool (F1): user gọi send_email =====
    if scenario == "unknown_tool_send_email":
        _mock_print(1, "LLM cố gọi tool không tồn tại: send_email.",
                    'send_email["candidate@x.com", "Mời phỏng vấn"]',
                    "LỖI UNKNOWN_TOOL: 'send_email' không có trong registry. "
                    "Tool hợp lệ: [parse_resume, get_job_requirements, score_candidate, "
                    "check_interviewer_availability, schedule_interview].")
        _mock_print(2, "Tự phục hồi: dùng schedule_interview (thay thế) thông báo nội bộ.", None, None)
        triggered = ["F1_UNKNOWN_TOOL"]
        final = (
            "⚠️ Tôi không có tool 'send_email' (F1).\n"
            "📋 Tôi đã tra cứu hồ sơ C002 và đặt lịch phỏng vấn nội bộ thành công:\n"
            "- Ứng viên: C002\n- Vị trí: J002\n- Lịch: 2026-08-01 09:00 (interviewer_1)\n"
            "💡 Bạn có thể dùng email client riêng để gửi thông báo cho ứng viên."
        )
        print(f"\n🧪 [MOCK] ✅ Final Answer (iter 2):\n{final}")
        return {
            "final_answer": final, "iterations": 2, "reached_max": False,
            "triggered_guardrail": triggered,
            "trace": [
                {"step": 1, "action": 'send_email[...]',
                 "observation": "LỖI UNKNOWN_TOOL"},
                {"step": 2, "guardrail": "Self-Recovery F1 → schedule_interview thay thế"},
            ],
        }

    # ===== Fallback — không match scenario nào =====
    print(f"⚠️ [MOCK] Không nhận diện được scenario, dùng safe fallback cho câu: {user_query[:60]}...")
    final = render_safe_fallback([])
    return {
        "final_answer": final, "trace": [], "iterations": 0,
        "reached_max": True, "triggered_guardrail": ["UNKNOWN_SCENARIO"],
    }


# ---- 4.3. ReAct Loop thật (dùng cho Gemini/OpenAI/Anthropic/OpenRouter) ----

def run_react_agent(
    user_query: str,
    provider,
    test_meta: dict | None = None,
    version: str = "v2",
) -> dict:
    """
    Vòng lặp ReAct Agent (Thought -> Action -> Observation) với đầy đủ Guardrails:

      - MAX_ITERATIONS (phanh cứng)
      - MAX_REPEATED_ACTIONS (chống loop)
      - Safe Fallback khi hết iteration
      - PII Filter cho Final Answer

    Trả về dict:
      {
        "final_answer": str,
        "trace": list[dict],
        "iterations": int,
        "reached_max": bool,
        "triggered_guardrail": list[str],
      }
    """
    tc_id = test_meta.get("id") if test_meta else None
    tag = f" [{test_meta['type']}]" if test_meta else ""

    # ---- MockProvider: dùng scenario hardcoded để demo trace ----
    if provider.__class__.__name__ == "MockProvider":
        return mock_react_scenario(tc_id, user_query)

    # ---- Real LLM Provider: chạy loop thật ----
    print(f"\n🤖 [REACT AGENT{tag}] Câu hỏi: {user_query}")
    print(f"   Guardrails: MAX_ITERATIONS={MAX_ITERATIONS}, MAX_REPEATED_ACTIONS={MAX_REPEATED_ACTIONS}")

    # Chuẩn bị system prompt
    try:
        system_prompt = render_for_test_case(tc_id, TOOL_SCHEMAS, version=version)
    except ValueError:
        # Nếu không tìm thấy TC cụ thể → render ReAct thẳng với user_query
        from prompts import render_react_prompt
        system_prompt = render_react_prompt(user_query, TOOL_SCHEMAS, version=version)

    history: list[str] = [f"Question: {user_query}"]
    trace: list[dict] = []
    called_actions: list[tuple[str, tuple]] = []
    triggered: list[str] = []
    final_answer: str | None = None
    observations: list[str] = []

    for step in range(MAX_ITERATIONS):
        print(f"\n🔁 Iteration {step + 1}/{MAX_ITERATIONS}")

        # Bước 1: gọi LLM
        prompt_text = "\n\n".join(history)
        try:
            llm_output = provider.generate(prompt_text, system_prompt=system_prompt)
        except Exception as e:  # pylint: disable=broad-except
            print(f"❌ LLM Exception: {e}")
            triggered.append("LLM_EXCEPTION")
            break

        # Bước 2: parse
        parsed = parse_llm_output(llm_output)
        thought = extract_thought(llm_output) or "(không có Thought)"
        print(f"🧠 Thought: {thought}")

        # Bước 3a: Final Answer
        if parsed["type"] == "final":
            final_answer = parsed["answer"]
            print(f"✅ Final Answer (iter {step + 1}):\n{final_answer}")
            trace.append({"step": step + 1, "final_answer": final_answer})
            triggered.append("FINAL_ANSWER")
            break

        # Bước 3b: Parse error
        if parsed["type"] == "error":
            print(f"⚠️ Parse Error: {parsed['message']}")
            history.append(
                f"Observation: PARSE_ERROR — {parsed['message']}. "
                "Hãy in lại Thought/Action đúng format."
            )
            triggered.append("PARSE_ERROR")
            trace.append({"step": step + 1, "thought": thought, "error": parsed["message"]})
            continue

        # Bước 3c: Action -> chống anti-loop trước khi execute
        tool = parsed["tool"]
        args = parsed["args"]
        args_key = _normalize_args_key(args)
        current_key = (tool, args_key)

        repeat_count = check_repeated_action(called_actions, current_key)
        called_actions.append(current_key)

        if repeat_count >= MAX_REPEATED_ACTIONS:
            print(
                f"🔁 Anti-Loop: tool '{tool}' đã được gọi {repeat_count + 1} lần liên tiếp "
                "với cùng tham số. Ép Agent đổi tool hoặc Final Answer."
            )
            history.append(
                f"Observation: BẠN ĐÃ GỌI TOOL '{tool}' TRƯỚC ĐÓ với cùng tham số "
                f"({repeat_count + 1} lần liên tiếp). Hãy đổi tool khác hoặc đưa Final Answer."
            )
            triggered.append("ANTI_LOOP")
            trace.append({
                "step": step + 1, "thought": thought,
                "action": f"{tool}[{args}]", "guardrail": "ANTI_LOOP",
            })
            continue

        # Bước 4: execute tool (luôn trả string, không crash)
        action_str = f"{tool}[{json.dumps(args, ensure_ascii=False)}]"
        observation = execute_tool(tool, args)
        print(f"🛠️  Action:  {action_str}")
        print(f"👁️  Observation: {observation}")

        # Bước 5: append vào history + trace
        history.append(f"Thought: {thought}")
        history.append(f"Action: {action_str}")
        history.append(f"Observation: {observation}")
        observations.append(observation)
        trace.append({
            "step": step + 1, "thought": thought,
            "action": action_str, "observation": observation,
        })

    # ---- Sau loop: nếu chưa có final_answer -> Safe Fallback ----
    if final_answer is None:
        triggered.append("MAX_ITERATIONS")
        final_answer = render_safe_fallback(observations)
        print(f"\n⚠️ MAX_ITERATIONS ({MAX_ITERATIONS}) đã đạt. Trả về Safe Fallback:")
        print(final_answer)
        trace.append({"step": MAX_ITERATIONS, "guardrail": "MAX_ITERATIONS"})

    # ---- PII filter ----
    final_answer = filter_pii(final_answer)

    return {
        "final_answer": final_answer,
        "trace": trace,
        "iterations": len(trace),
        "reached_max": "MAX_ITERATIONS" in triggered,
        "triggered_guardrail": triggered,
    }


# ---- 4.4. Chạy ReAct trên toàn bộ test cases ----

def run_all_react_cases(provider, tests: list[dict], version: str = "v2") -> list[dict]:
    """Chạy ReAct Agent trên toàn bộ 5 test case (Mốc 3 yêu cầu)."""
    print("\n" + "=" * 70)
    print(f"🤖 MỐC 3 — REACT AGENT (version={version}, {MAX_ITERATIONS} iterations max)")
    print("=" * 70)
    results = []
    for tc in tests:
        result = run_react_agent(
            tc["question"], provider,
            test_meta={"id": tc["id"], "type": tc["type"]},
            version=version,
        )
        results.append({
            "id": tc["id"], "type": tc["type"],
            "question": tc["question"],
            "iterations": result["iterations"],
            "reached_max": result["reached_max"],
            "triggered_guardrail": result["triggered_guardrail"],
            "final_answer": result["final_answer"],
            "trace": result["trace"],
        })
    return results


# ============================================================
# 💬 PHẦN 4B: CHẠY BASELINE TRÊN TOÀN BỘ TEST CASES
# ============================================================

def run_all_baseline_cases(provider, tests: list[dict]) -> list[dict]:
    """Chạy Chatbot Baseline trên toàn bộ test case (Mốc 2 yêu cầu)."""
    print("\n" + "=" * 70)
    print("🚀 MỐC 2 — CHATBOT BASELINE (Không có tool, 1 LLM call / câu hỏi)")
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


# ============================================================
# 🎬 PHẦN 5: MAIN — Chạy Mốc 2 + Mốc 3
# ============================================================

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
    print(f"🧠 Guardrail MAX_ITERATIONS = {MAX_ITERATIONS}, "
          f"MAX_REPEATED_ACTIONS = {MAX_REPEATED_ACTIONS} (Role 3)")
    print(f"🔒 PII Blacklist có {len(PII_BLACKLIST)} keyword")

    # ---- DEMO 1: CHẠY CHATBOT BASELINE TRÊN TOÀN BỘ 5 TEST CASE (Mốc 2) ----
    baseline_results = run_all_baseline_cases(provider, tests)

    # ---- DEMO 2: CHẠY REACT AGENT TRÊN 5 TEST CASE (Mốc 3) ----
    react_results = run_all_react_cases(provider, tests, version="v2")

    # ---- Kết thúc: nhắc Role 5 copy trace vào docs/trace_eval.md ----
    print("\n" + "=" * 70)
    print("✅ MỐC 2 + MỐC 3 HOÀN THÀNH (phần Role 4 - Integrator)")
    print("👉 Role 5: copy `react_results[i].trace` vào Section 3 của docs/trace_eval.md.")
    print("👉 MỐC 4: xem docs/hybrid_flowchart.mermaid + Section 4 của trace_eval.md.")
    print("=" * 70)
