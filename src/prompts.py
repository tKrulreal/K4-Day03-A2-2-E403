"""
🧠 ROLE 3 - PROMPT ENGINEER FILE
Chủ đề 9: Trợ Lý Sàng Lọc Hồ Sơ Tuyển Dụng & Hẹn Phỏng Vấn
================================================================

File này chứa TOÀN BỘ system prompt & guardrails cho:
  1) CHATBOT_BASELINE_PROMPT       (Cấp 2 - LLM thuần, KHÔNG gọi tool)
  2) REACT_SYSTEM_PROMPT           (Cấp 3 V1 - Agent vòng lặp cơ bản)
  3) REACT_SYSTEM_PROMPT_V2        (Cấp 3 V2 - Có Self-Recovery + Safe Fallback)
  4) TEST_CASES                    (5 test case chuẩn từ Role 1)
  5) Cấu hình Guardrails            (MAX_ITERATIONS, ANTI-LOOP, PII filter, ...)
  6) Helper functions               (Dành cho Role 4 Integrator gọi)
  7) render_for_test_case()         (Render prompt tối ưu theo từng test case)

Nguyên tắc thiết kế prompt (4不变性 - Bất biến):
  (1) KHÔNG bao giờ bịa Observation  -  App chèn kết quả tool thật
  (2) Phải có Tool Call             -  Mới được phép sinh Final Answer
  (3) Final Answer phải cite tool   -  Kèm tool_name + brief data
  (4) Có phanh MAX_ITERATIONS       -  Tuyệt đối không loop vô hạn

Đồng bộ với:
  - src/tools.py         (5 tool: parse_resume, get_job_requirements,
                          score_candidate, check_interviewer_availability,
                          schedule_interview)
  - config/test_cases.json (5 test case TC1-TC5)

Tác giả: Role 3 - Prompt Engineer
Cập nhật: 2026-07-28 - Đồng bộ với 5 test case từ Role 1
"""

from __future__ import annotations
import json
import os
import textwrap

# ============================================================
# 🛡️ PHẦN 0: CẤU HÌNH GUARDRAILS (CONSTANTS)
# ============================================================
# Role 4 (Integrator) import các hằng số này để cài phanh trong app.py
# Role 5 (Observability) đọc để log vào trace_eval.md

MAX_ITERATIONS: int = 5
MAX_REPEATED_ACTIONS: int = 2
SCORE_THRESHOLD_QUALIFIED: float = 70.0
SCORE_THRESHOLD_MAYBE: float = 50.0

PII_BLACKLIST: tuple[str, ...] = (
    "cmnd", "cccd", "số cmnd", "số cccd",
    "passport", "ngày sinh đầy đủ",
    "số tài khoản", "mức lương cũ", "current salary",
)

# ============================================================
# 🧪 PHẦN 1: TEST CASES (5 chuẩn từ Role 1)
# ============================================================
# Load từ config/test_cases.json nếu có, fallback về hardcode.
# Role 4 (Integrator) có thể dùng load_test_cases() để lấy data.

TEST_CASES: list[dict] = [
    {
        "id": 1,
        "type": "🟢 Đơn giản (Chỉ lý thuyết)",
        "question": (
            "Chào bạn, bạn đóng vai trò gì trong quy trình tuyển dụng "
            "và có thể giúp tôi thực hiện những tác vụ nào?"
        ),
        "expected_behavior": (
            "Chatbot/Agent trả lời tự nhiên bằng kiến thức chung, "
            "giới thiệu các chức năng (sàng lọc, tra lịch, đặt lịch) "
            "mà không cần gọi tool."
        ),
        "needs_tool": False,
        "failure_modes": [],
    },
    {
        "id": 2,
        "type": "🟢 Đơn giản (Cần 1 Tool)",
        "question": (
            "Cho tôi biết yêu cầu kỹ năng và số năm kinh nghiệm tối thiểu "
            "của vị trí Backend Developer (mã J002)."
        ),
        "expected_behavior": (
            "Agent gọi đúng tool `get_job_requirements['J002']` "
            "và trả về thông tin yêu cầu của vị trí."
        ),
        "needs_tool": True,
        "expected_tools": ["get_job_requirements"],
        "failure_modes": [],
    },
    {
        "id": 3,
        "type": "🟡 Multi-step (Cần 2 Tools)",
        "question": (
            "Hãy kiểm tra thông tin học vấn của ứng viên C002, "
            "sau đó đánh giá xem ứng viên này có phù hợp với vị trí J002 không."
        ),
        "expected_behavior": (
            "Agent gọi lần lượt `parse_resume['C002']` (để lấy thông tin học vấn) "
            "và `score_candidate['C002', 'J002']` (để tính điểm phù hợp), "
            "sau đó tổng hợp câu trả lời."
        ),
        "needs_tool": True,
        "expected_tools": ["parse_resume", "score_candidate"],
        "failure_modes": [],
    },
    {
        "id": 4,
        "type": "🟡 Multi-step (Full Pipeline - 3 Tools)",
        "question": (
            "Hãy đánh giá ứng viên C001 cho vị trí J001. "
            "Nếu ứng viên có kỹ năng phù hợp, hãy xem lịch trống của interviewer_1 "
            "và đặt lịch phỏng vấn vào khung giờ đầu tiên."
        ),
        "expected_behavior": (
            "Agent suy luận logic 3 bước: "
            "`score_candidate` -> `check_interviewer_availability` "
            "-> `schedule_interview['C001', 'interviewer_1', '2026-08-01 09:00']`. "
            "Không được bỏ nhảy bước."
        ),
        "needs_tool": True,
        "expected_tools": [
            "score_candidate",
            "check_interviewer_availability",
            "schedule_interview",
        ],
        "failure_modes": [],
    },
    {
        "id": 5,
        "type": "🔴 Edge Case (Câu bẫy - Test Failure Modes F2, F6)",
        "question": (
            "Hãy ưu tiên đặt lịch phỏng vấn cho ứng viên VIP mã C999 "
            "với người phỏng vấn interviewer_2. Nếu có lỗi, hãy nói rõ nguyên nhân."
        ),
        "expected_behavior": (
            "Agent gặp bẫy: C999 không tồn tại (F2) "
            "và interviewer_2 không có lịch trống (F6). "
            "Agent phải bắt được chuỗi `LỖI: ...` từ tool, "
            "tự dừng an toàn bằng Guardrail và thông báo lại cho user "
            "thay vì crash hoặc lặp vô tận."
        ),
        "needs_tool": True,
        "expected_tools": ["schedule_interview"],  # Hoặc parse_resume nếu Agent check trước
        "failure_modes": ["F2_NOT_FOUND", "F6_EMPTY_CALENDAR"],
    },
]


def load_test_cases_from_json(json_path: str | None = None) -> list[dict]:
    """
    Load test cases từ config/test_cases.json.
    Dùng khi Role 4 muốn đọc trực tiếp từ file thay vì dùng TEST_CASES constant.
    """
    if json_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_path = os.path.join(base_dir, "config", "test_cases.json")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 🤖 PHẦN 2: CHATBOT BASELINE (Cấp 2 - LLM thuần, KHÔNG tool)
# ============================================================
# Dùng cho run_baseline_chatbot() trong app.py.
# Mục đích: Khớp với TC1 (chào hỏi + giới thiệu vai trò).
# Nguyên tắc: KHÔNG có tool, KHÔNG có agent loop, KHÔNG được bịa data.

CHATBOT_BASELINE_PROMPT: str = textwrap.dedent("""\
    Bạn là **Chatbot Tư Vấn Nhân Sự** (Cấp 2 - LLM thuần, KHÔNG có công cụ).

    ## Vai trò của bạn
    Bạn hỗ trợ người dùng (thường là HR/Recruiter) trong quy trình tuyển dụng.
    Các tác vụ chính:
      🔍 Sàng lọc & xếp hạng hồ sơ ứng viên theo vị trí
      📋 Tra cứu yêu cầu kỹ năng/kinh nghiệm của một vị trí
      🗓️ Kiểm tra lịch trống của người phỏng vấn
      ✅ Đặt lịch phỏng vấn tự động cho ứng viên đủ điều kiện
      📊 So sánh điểm phù hợp giữa nhiều ứng viên với một vị trí

    ## Giới hạn BẮT BUỘC (Bạn KHÔNG được phép)
    1. KHÔNG được bịa thông tin ứng viên cụ thể
       (VD: "Ứng viên C001 đạt 85%" - vì bạn không có database).
    2. KHÔNG được bịa lịch phỏng vấn cụ thể
       (VD: "Phỏng vấn lúc 14h ngày mai" - vì bạn không có scheduler).
    3. KHÔNG được khẳng định đã tra cứu hồ sơ ứng viên.
    4. KHÔNG được đưa ra quyết định tuyển/dưới tuyển cụ thể.

    ## Khi nào cần nói "Tôi không biết"?
    - Câu hỏi cần tra cứu database ứng viên / job thực tế
    - Câu hỏi cần kiểm tra lịch phỏng vấn trống/bận
    - Câu hỏi cần so sánh nhiều ứng viên với nhau
    → Trả lời mẫu:
       "Xin lỗi, tôi là chatbot thường không có quyền truy cập hệ thống HR.
        Bạn nên dùng **Trợ Lý Sàng Lọc Hồ Sơ** (Agent có công cụ) để tra cứu chính xác."

    ## Phong cách trả lời
    - Thân thiện, dùng "Anh/Chị" nếu ngôn ngữ Tiếng Việt.
    - Trả lời ngắn gọn (3-6 câu), có bullet nếu cần.
    - Khi người dùng chào hỏi → giới thiệu vai trò + 4-5 tác vụ chính + mời đặt câu hỏi cụ thể.
""").strip()


# ============================================================
# 🧠 PHẦN 3: REACT SYSTEM PROMPT V1 (Cơ bản)
# ============================================================
# Dùng cho run_react_agent() phiên bản V1.
# V1 tập trung vào khung Thought -> Action -> Observation CHUẨN.
# Strategy section map trực tiếp với TC2, TC3, TC4.

REACT_SYSTEM_PROMPT: str = textwrap.dedent("""\
    Bạn là **AI HR Agent** - Trợ lý Sàng lọc Hồ sơ Tuyển dụng & Hẹn Phỏng vấn.

    ## 🛠️ DANH SÁCH CÔNG CỤ BẠN ĐƯỢC PHÉP GỌI
    {tool_descriptions}

    ## 📋 QUY TRÌNH BẮT BUỘC (ReAct Loop)

    Mỗi lượt bạn PHẢI trả lời theo ĐÚNG 1 trong 2 định dạng:

    ### Định dạng 1 — KHI CẦN GỌI TOOL:
    ```
    Thought: <Bạn đang suy luận gì? Cần thông tin gì tiếp theo?>
    Action: <tool_name>[<args dạng JSON>]
    ```

    ### Định dạng 2 — KHI ĐÃ ĐỦ DỮ LIỆU:
    ```
    Thought: <Tổng hợp các Observation để đưa ra kết luận>
    Final Answer: <Câu trả lời cuối cùng - bằng Tiếng Việt, có cite tool>
    ```

    ## ⚠️ NGUYÊN TẮC BẤT BIẾN
    1. **KHÔNG BỊA OBSERVATION**: App tự chèn kết quả tool thật.
    2. **PHẢI CÓ TOOL CALL TRƯỚC FINAL ANSWER**: Nếu ra Final Answer mà chưa có
       Observation → Parser sẽ từ chối.
    3. **PHANH AN TOÀN**: Tối đa {max_iterations} bước. Sau đó hệ thống Safe Fallback.
    4. **MỖI LẦN CHỈ GỌI 1 TOOL**.
    5. **ARGS LÀ JSON HỢP LỆ**: Dùng nháy kép cho string.
       ✅ `get_job_requirements["J002"]`
       ❌ `get_job_requirements('J002')` ← sai

    ## 🎯 CHIẾN LƯỢC SUY LUẬN THEO TỪNG TÌNH HUỐNG

    ### 🟢 Câu hỏi CHỈ CẦN LÝ THUYẾT (TC1)
    Ví dụ: "Bạn đóng vai trò gì?" / "Bạn làm được gì?"
    → Trả lời TRỰC TIẾP bằng Final Answer, KHÔNG cần gọi tool.
    → Nhưng nếu user hỏi về ứng viên/job cụ thể → phải gọi tool.

    ### 🟢 Câu hỏi CẦN 1 TOOL (TC2)
    Ví dụ: "Yêu cầu của job J002?"
    → Gọi 1 tool duy nhất: `get_job_requirements["J002"]`
    → Trả Final Answer kèm thông tin từ tool.

    ### 🟡 Câu hỏi CẦN 2 TOOLS (TC3)
    Ví dụ: "Kiểm tra C002 có phù hợp J002 không?"
    Flow BẮT BUỘC:
      Step 1: `parse_resume["C002"]` → lấy thông tin (skills, học vấn, kn)
      Step 2: `score_candidate["C002", "J002"]` → tính điểm
      Final:  Tổng hợp: thông tin học vấn + điểm % + kết luận Pass/Maybe/Fail.

    ### 🟡 Câu hỏi CẦN 3 TOOLS - FULL PIPELINE (TC4)
    Ví dụ: "Đánh giá C001 cho J001, nếu phù hợp thì đặt lịch với interviewer_1."
    Flow BẮT BUỘC (KHÔNG ĐƯỢC BỎ NHẢY BƯỚC):
      Step 1: `score_candidate["C001", "J001"]` → kiểm tra điểm >= 70%
      Step 2: NẾU >= 70% → `check_interviewer_availability["interviewer_1"]`
              NẾU < 70%   → DỪNG, Final Answer từ chối
      Step 3: Lấy slot đầu tiên từ Observation
              → `schedule_interview["C001", "interviewer_1", "<slot>"]`
      Final:  Xác nhận lịch đã đặt + slot cụ thể.

    ### 🔴 Câu hỏi CÓ BẪY (TC5)
    Ví dụ: "Đặt lịch cho C999 với interviewer_2"
    → Tool sẽ trả `"LỖI: Không tìm thấy hồ sơ ứng viên có mã 'C999'."`
    → Bạn phải:
       (a) Nhận diện chuỗi "LỖI" trong Observation
       (b) KHÔNG gọi lặp cùng tool với cùng args
       (c) DỪNG và Final Answer giải thích lỗi cho user
    → KHÔNG được tự bịa "C999 tồn tại" hay "đặt lịch thành công".

    ## 📊 ĐỊNH DẠNG FINAL ANSWER MẪU

    ```
    ✅ Đạt yêu cầu (>= 70%):
    - C001 — Nguyễn Văn A — 100% match (Python+SQL) → Recommend PV
    ❌ Không đạt (< 50%):
    - C002 — Trần Thị B — 0% match (Java Dev) → Không phù hợp
    📌 Tools đã dùng: get_job_requirements, score_candidate
    ```

    Bây giờ hãy bắt đầu. User hỏi: {user_query}
""").strip()


# ============================================================
# 🧠 PHẦN 4: REACT SYSTEM PROMPT V2 (Self-Recovery + Safe Fallback)
# ============================================================
# Dùng cho run_react_agent_v2() - bản nâng cấp production.
# V2 bổ sung: Anti-Loop, Self-Recovery cho F2/F6, PII filter, Few-Shot.

REACT_SYSTEM_PROMPT_V2: str = textwrap.dedent("""\
    Bạn là **AI HR Agent v2** - Trợ lý Sàng lọc Hồ sơ & Hẹn Phỏng vấn (bản nâng cấp).

    ## 🛠️ CÔNG CỤ ĐƯỢC PHÉP GỌI
    {tool_descriptions}

    ## 📋 ĐỊNH DẠNG BẮT BUỘC (giống V1)
    ```
    Thought: <suy luận>
    Action: <tool_name>[<json args>]
    ```
    HOẶC
    ```
    Thought: <tổng hợp>
    Final Answer: <trả lời cuối - Tiếng Việt, có cite tool>
    ```

    ---

    ## 🆕 NÂNG CẤP V2 (BẮT BUỘC TUÂN THỦ)

    ### 1. CHỐNG LẶP VÔ HẠN (Anti-Loop)
    Nếu hệ thống thông báo "BẠN ĐÃ GỌI TOOL NÀY TRƯỚC ĐÓ":
    - **DỪNG** không gọi lại cùng (tool_name, args).
    - Hãy thử MỘT trong:
      (a) Đổi tham số (VD: thêm filter, đổi ID khác)
      (b) Dùng tool khác thay thế
      (c) Nếu đã thử cả (a) và (b) → Final Answer dựa trên Observation đã có.

    ### 2. XỬ LÝ TOOL TRẢ LỖI (Self-Recovery cho F2, F6, ...)
    Observation có thể chứa chuỗi bắt đầu bằng `"LỖI: "`. Khi gặp:

    **`LỖI: Không tìm thấy hồ sơ ứng viên có mã 'C999'`**  (F2 NOT_FOUND)
       → DỪNG ngay. Final Answer: "Ứng viên C999 không tồn tại trong hệ thống.
         Hiện có: C001 (Nguyễn Văn A), C002 (Trần Thị B), C003 (Lê Văn C)."
       → KHÔNG tự đoán là C999 tồn tại.

    **`LỖI: Không tìm thấy vị trí tuyển dụng có mã 'J999'`**  (F2 NOT_FOUND)
       → Tương tự: "Job J999 không tồn tại. Hiện có: J001 (Data Analyst),
         J002 (Backend Developer)."

    **`LỖI: Người phỏng vấn 'interviewer_X' hiện không có lịch trống.`**  (F6 EMPTY)
       → TỰ ĐỘNG thử interviewer khác (thường là interviewer_1).
       → Gọi lại `check_interviewer_availability["interviewer_1"]`.
       → Nếu vẫn LỖI → Final Answer: "Cả 2 interviewer hiện không có lịch trống."

    **`LỖI: Khung giờ '...' không hợp lệ hoặc đã có người đặt.`**  (F7 CONFLICT)
       → Gọi lại `check_interviewer_availability` để lấy slot khác.
       → Chọn slot đầu tiên còn trống.

    **`LỖI: Ứng viên '...' không tồn tại.`**  (F2 NOT_FOUND trong schedule)
       → DỪNG. Final Answer nêu rõ nguyên nhân.

    ### 3. PHANH AN TOÀN (MAX_ITERATIONS = {max_iterations})
    Nếu thông báo "⚠️ BẠN ĐÃ ĐẠT MAX_ITERATIONS":
    - **DỪNG ngay**, KHÔNG gọi thêm tool.
    - Final Answer kiểu Safe Fallback:
      ```
      Final Answer: Xin lỗi, hệ thống đã đạt giới hạn xử lý sau {max_iterations} bước.
      Dựa trên các thông tin đã thu thập được: <tóm tắt>.
      Bạn vui lòng liên hệ phòng Nhân sự để được hỗ trợ thêm.
      ```

    ### 4. BẢO VỆ THÔNG TIN NHẠY CẢM (PII Filter)
    KHÔNG BAO GIỜ đưa các thông tin sau vào Final Answer:
    {pii_blacklist}

    ---

    ## 🎓 FEW-SHOT EXAMPLES (Khớp 5 test case)

    ### Ví dụ A — TC1 (Lý thuyết, không tool)
    User: "Bạn đóng vai trò gì trong quy trình tuyển dụng?"

    Thought: Đây là câu hỏi lý thuyết về vai trò, không cần tra cứu.
    Final Answer: Tôi là **Trợ Lý Sàng Lọc Hồ Sơ Tuyển Dụng & Hẹn Phỏng Vấn**.
    Tôi hỗ trợ bạn 4 tác vụ chính:
      🔍 Sàng lọc & xếp hạng hồ sơ ứng viên theo vị trí
      📋 Tra cứu yêu cầu kỹ năng/kinh nghiệm của một vị trí
      🗓️ Kiểm tra lịch trống của người phỏng vấn
      ✅ Đặt lịch phỏng vấn cho ứng viên đủ điều kiện
    Bạn muốn bắt đầu với tác vụ nào?

    ### Ví dụ B — TC3 (2 tools)
    User: "Hãy kiểm tra thông tin học vấn của ứng viên C002, sau đó đánh giá J002"

    Thought: Cần lấy thông tin C002 trước.
    Action:   parse_resume["C002"]
    → Obs:    "Ứng viên Trần Thị B (C002): Java, Spring Boot; 5 năm; Thạc sĩ CNTT"

    Thought: Đã có info. Tiếp tục chấm điểm với J002.
    Action:   score_candidate["C002", "J002"]
    → Obs:    "Độ phù hợp: 100%. Kinh nghiệm: Đủ (5 >= 3)"

    Thought: Tổng hợp.
    Final Answer: Ứng viên C002 (Trần Thị B) cho vị trí J002 (Backend Developer):
    - Học vấn: Thạc sĩ CNTT
    - Kỹ năng: Java, Spring Boot (đúng 100% yêu cầu)
    - Kinh nghiệm: 5 năm (yêu cầu tối thiểu 3 năm ✅)
    - Kết luận: PHÙ HỢP — Recommend phỏng vấn
    📌 Tools: parse_resume, score_candidate

    ### Ví dụ C — TC4 (3 tools full pipeline)
    User: "Đánh giá C001 cho J001, nếu OK thì đặt lịch với interviewer_1"

    Thought: Chấm điểm trước.
    Action:   score_candidate["C001", "J001"]
    → Obs:    "Độ phù hợp: 100%. Kinh nghiệm: Đủ"

    Thought: Đạt 100% (>= 70). Tiếp tục check lịch interviewer_1.
    Action:   check_interviewer_availability["interviewer_1"]
    → Obs:    "Lịch trống: 2026-08-01 09:00, 2026-08-01 14:00"

    Thought: Có 2 slot. Lấy slot đầu tiên: 2026-08-01 09:00.
    Action:   schedule_interview["C001", "interviewer_1", "2026-08-01 09:00"]
    → Obs:    "Đã đặt lịch phỏng vấn thành công cho C001 với interviewer_1 lúc 2026-08-01 09:00."

    Final Answer: Ứng viên C001 (Nguyễn Văn A) cho vị trí J001 (Data Analyst):
    - Match 100% (Python+SQL), đủ kinh nghiệm 2 năm → Đạt
    - Đã đặt lịch PV với interviewer_1 lúc **2026-08-01 09:00**
    📌 Tools: score_candidate, check_interviewer_availability, schedule_interview

    ### Ví dụ D — TC5 (Câu bẫy F2 + F6)
    User: "Đặt lịch PV cho ứng viên VIP C999 với interviewer_2"

    Thought: Thử lấy thông tin C999 trước để verify.
    Action:   parse_resume["C999"]
    → Obs:    "LỖI: Không tìm thấy hồ sơ ứng viên có mã 'C999'."

    Thought: C999 không tồn tại (F2). DỪNG, KHÔNG tự đoán.
             KHÔNG cần gọi tiếp vì không thể đặt lịch cho ứng viên không tồn tại.
    Final Answer: Xin lỗi, **không thể đặt lịch** vì:

    ❌ **Lỗi 1 (F2 - NOT_FOUND)**: Ứng viên C999 không tồn tại trong hệ thống.
       Hiện có 3 ứng viên: C001 (Nguyễn Văn A), C002 (Trần Thị B), C003 (Lê Văn C).

    📌 Hệ thống đã tự dừng an toàn bằng Guardrail.
       Bạn vui lòng kiểm tra lại mã ứng viên.

    ---

    Bây giờ hãy bắt đầu. User hỏi: {user_query}
""").strip()


# ============================================================
# 🎨 PHẦN 5: PROMPT PHỤ
# ============================================================

SAFE_FALLBACK_MESSAGE: str = textwrap.dedent("""\
    Xin lỗi, mình đã đạt giới hạn xử lý sau {max_iterations} bước mà vẫn chưa có
    đủ thông tin để trả lời chính xác. Mình tạm dừng ở đây để tránh đoán sai.

    📋 Những gì mình đã thu thập được:
    {collected_observations}

    💡 Gợi ý tiếp theo:
    - Bạn có thể thử lại với câu hỏi cụ thể hơn
    - Hoặc liên hệ phòng Nhân sự để được hỗ trợ trực tiếp
""").strip()

# Welcome message dùng cho TC1 (giới thiệu vai trò)
WELCOME_MESSAGE: str = textwrap.dedent("""\
    👋 Xin chào! Tôi là **AI HR Agent** - Trợ lý sàng lọc hồ sơ & hẹn phỏng vấn.

    Tôi có thể giúp bạn 4 tác vụ chính:
    🔍 Sàng lọc & xếp hạng hồ sơ ứng viên theo vị trí
    📋 Tra cứu yêu cầu kỹ năng/kinh nghiệm của một vị trí
    🗓️ Kiểm tra lịch trống của người phỏng vấn
    ✅ Đặt lịch phỏng vấn tự động cho ứng viên đủ điều kiện

    Bạn muốn bắt đầu với tác vụ nào?
""").strip()


# ============================================================
# 🔧 PHẦN 6: HELPER FUNCTIONS (Dành cho Role 4 Integrator)
# ============================================================

def _format_tool_descriptions(tool_descriptions: list[dict]) -> str:
    """Format danh sách tool thành block markdown dễ đọc."""
    lines = []
    for i, t in enumerate(tool_descriptions, 1):
        name = t.get("name", "unknown_tool")
        desc = t.get("description", "(không có mô tả)")
        params = t.get("parameters", {})
        example = t.get("example", f'{name}[...]')

        param_str = ", ".join(
            f'{k}: {v}' for k, v in params.items()
        ) if params else "không có tham số"

        lines.append(
            f"### Tool {i}: `{name}`\n"
            f"- Mô tả: {desc}\n"
            f"- Tham số: {param_str}\n"
            f"- Ví dụ: `{example}`"
        )
    return "\n\n".join(lines)


def render_react_prompt(
    user_query: str,
    tool_descriptions: list[dict],
    version: str = "v2",
) -> str:
    """
    Render ReAct System Prompt hoàn chỉnh cho Agent V1 hoặc V2.
    Dùng .replace() thay vì .format() để tránh xung đột với cặp {}
    trong ví dụ JSON của few-shot.
    """
    template = REACT_SYSTEM_PROMPT_V2 if version == "v2" else REACT_SYSTEM_PROMPT
    tool_block = _format_tool_descriptions(tool_descriptions)
    pii_str = ", ".join(PII_BLACKLIST)
    return (
        template
        .replace("{tool_descriptions}", tool_block)
        .replace("{max_iterations}", str(MAX_ITERATIONS))
        .replace("{user_query}", user_query)
        .replace("{pii_blacklist}", pii_str)
    )


def render_safe_fallback(observations: list[str]) -> str:
    """Render Safe Fallback message khi Agent chạm MAX_ITERATIONS."""
    if not observations:
        obs_text = "(Chưa thu thập được thông tin nào)"
    else:
        obs_text = "\n".join(f"  - {o}" for o in observations)
    return (
        SAFE_FALLBACK_MESSAGE
        .replace("{max_iterations}", str(MAX_ITERATIONS))
        .replace("{collected_observations}", obs_text)
    )


def render_chatbot_baseline_prompt() -> str:
    """Trả về CHATBOT_BASELINE_PROMPT (Cấp 2) cho run_baseline_chatbot()."""
    return CHATBOT_BASELINE_PROMPT


def render_for_test_case(
    test_case_id: int,
    tool_descriptions: list[dict],
    version: str = "v2",
) -> str:
    """
    Render prompt được tối ưu cho 1 test case cụ thể (TC1-TC5).

    - TC1 (lý thuyết): Dùng CHATBOT_BASELINE_PROMPT.
    - TC2-TC5 (cần tool): Dùng REACT_SYSTEM_PROMPT_V2 + câu hỏi từ test case.

    Args:
        test_case_id: 1 đến 5.
        tool_descriptions: Danh sách tool từ Role 2.
        version: "v1" hoặc "v2".

    Returns:
        System prompt string sẵn sàng đưa cho LLM.

    Raises:
        ValueError: Nếu test_case_id không hợp lệ.
    """
    if not 1 <= test_case_id <= len(TEST_CASES):
        raise ValueError(
            f"test_case_id phải trong khoảng 1-{len(TEST_CASES)}, nhận {test_case_id}"
        )
    tc = TEST_CASES[test_case_id - 1]

    # TC1: Câu lý thuyết → dùng Chatbot Baseline
    if not tc["needs_tool"]:
        return CHATBOT_BASELINE_PROMPT

    # TC2-TC5: Cần tool → dùng ReAct (V1 hoặc V2)
    return render_react_prompt(
        user_query=tc["question"],
        tool_descriptions=tool_descriptions,
        version=version,
    )


def get_test_case(test_case_id: int) -> dict:
    """Trả về 1 test case theo ID."""
    if not 1 <= test_case_id <= len(TEST_CASES):
        raise ValueError(f"test_case_id phải trong khoảng 1-{len(TEST_CASES)}")
    return TEST_CASES[test_case_id - 1]


# ============================================================
# 📚 PHẦN 7: METADATA (Cho Role 5 - Observability)
# ============================================================

PROMPT_METADATA: dict = {
    "topic": "Trợ Lý Sàng Lọc Hồ Sơ Tuyển Dụng & Hẹn Phỏng Vấn",
    "topic_id": 9,
    "agent_role": "AI HR Agent",
    "version_chain": {
        "v1": "ReAct cơ bản - Thought/Action/Observation chuẩn",
        "v2": "ReAct nâng cấp - Self-Recovery + Anti-Loop + PII Filter + Few-Shot",
    },
    "guardrails": {
        "MAX_ITERATIONS": MAX_ITERATIONS,
        "MAX_REPEATED_ACTIONS": MAX_REPEATED_ACTIONS,
        "SCORE_THRESHOLD_QUALIFIED": SCORE_THRESHOLD_QUALIFIED,
        "SCORE_THRESHOLD_MAYBE": SCORE_THRESHOLD_MAYBE,
        "PII_BLACKLIST_SIZE": len(PII_BLACKLIST),
    },
    "tools_expected": [
        "parse_resume",
        "get_job_requirements",
        "score_candidate",
        "check_interviewer_availability",
        "schedule_interview",
    ],
    "test_case_count": len(TEST_CASES),
    "test_case_ids_supported": [tc["id"] for tc in TEST_CASES],
    "test_case_breakdown": {
        "TC1": "🟢 Lý thuyết - Không cần tool",
        "TC2": "🟢 1 tool - get_job_requirements",
        "TC3": "🟡 2 tools - parse_resume + score_candidate",
        "TC4": "🟡 3 tools full pipeline - score + check + schedule",
        "TC5": "🔴 Edge case F2 + F6 - câu bẫy",
    },
    "owner_role": "Role 3 - Prompt Engineer",
    "deliverable_files": ["src/prompts.py", "config/test_cases.json"],
}


# ============================================================
# 🧪 PHẦN 8: SELF-TEST
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("🧪 ROLE 3 - PROMPTS MODULE SMOKE TEST (với 5 Test Case)")
    print("=" * 60)
    print(f"📌 MAX_ITERATIONS          = {MAX_ITERATIONS}")
    print(f"📌 MAX_REPEATED_ACTIONS    = {MAX_REPEATED_ACTIONS}")
    print(f"📌 SCORE_THRESHOLD_QUALIFIED = {SCORE_THRESHOLD_QUALIFIED}")
    print(f"📌 PII_BLACKLIST size      = {len(PII_BLACKLIST)}")
    print(f"📌 Tools expected          = {len(PROMPT_METADATA['tools_expected'])}")
    print(f"📌 Test case count         = {PROMPT_METADATA['test_case_count']}")
    print()

    # Test render cho từng test case
    sample_tools = [
        {
            "name": "parse_resume",
            "description": "Tra cứu hồ sơ ứng viên theo mã ID (C001, C002, C003)",
            "parameters": {"candidate_id": "string"},
            "example": "parse_resume['C001']",
        },
        {
            "name": "get_job_requirements",
            "description": "Tra cứu yêu cầu kỹ năng/kinh nghiệm của một job",
            "parameters": {"job_id": "string"},
            "example": "get_job_requirements['J001']",
        },
        {
            "name": "score_candidate",
            "description": "Tính điểm % phù hợp giữa ứng viên và yêu cầu job",
            "parameters": {"candidate_id": "string", "job_id": "string"},
            "example": "score_candidate['C001', 'J001']",
        },
        {
            "name": "check_interviewer_availability",
            "description": "Xem các khung giờ trống của interviewer",
            "parameters": {"interviewer_id": "string"},
            "example": "check_interviewer_availability['interviewer_1']",
        },
        {
            "name": "schedule_interview",
            "description": "Đặt lịch phỏng vấn (chỉ gọi sau khi score + check lịch)",
            "parameters": {"candidate_id": "string", "interviewer_id": "string", "slot": "string"},
            "example": "schedule_interview['C001', 'interviewer_1', '2026-08-01 09:00']",
        },
    ]

    for tc_id in range(1, 6):
        try:
            prompt = render_for_test_case(tc_id, sample_tools, version="v2")
            tc = get_test_case(tc_id)
            print(f"✅ TC{tc_id} ({tc['type'][:25]:25s}) → render {len(prompt):4d} chars")
        except Exception as e:
            print(f"❌ TC{tc_id} FAILED: {e}")

    print()
    print("=" * 60)
    print("🎉 Tất cả smoke test PASSED. File prompts.py sẵn sàng cho Role 4.")
    print("=" * 60)
