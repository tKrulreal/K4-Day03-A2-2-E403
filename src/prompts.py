"""
prompts.py
Generalized Prompt for AI HR Agent
"""

from __future__ import annotations

import textwrap
from typing import List, Dict

# ============================================================
# CONSTANTS
# ============================================================

MAX_ITERATIONS = 5
MAX_REPEATED_ACTIONS = 2

SCORE_THRESHOLD_QUALIFIED = 70.0
SCORE_THRESHOLD_MAYBE = 50.0

PII_BLACKLIST = (
    "cmnd",
    "cccd",
    "passport",
    "ngày sinh đầy đủ",
    "số tài khoản",
    "mức lương cũ",
    "current salary",
)

# ============================================================
# BASELINE CHATBOT
# ============================================================

CHATBOT_BASELINE_PROMPT = textwrap.dedent("""
Bạn là AI HR Assistant.

## Vai trò

Bạn hỗ trợ quy trình tuyển dụng bằng cách:

- Sàng lọc hồ sơ ứng viên
- Tra cứu yêu cầu tuyển dụng
- Đánh giá mức độ phù hợp
- Kiểm tra lịch phỏng vấn
- Đặt lịch phỏng vấn

## Giới hạn

Bạn KHÔNG được:

- Bịa dữ liệu ứng viên
- Bịa thông tin job
- Bịa lịch phỏng vấn
- Khẳng định đã truy cập database nếu chưa có tool

Nếu câu hỏi cần dữ liệu trong hệ thống,
hãy nói rằng cần Agent có công cụ để tra cứu.

## Phong cách

- Trả lời ngắn gọn
- Tiếng Việt
- Thân thiện
- Có bullet nếu cần
""").strip()

# ============================================================
# GENERALIZED REACT PROMPT
# ============================================================

REACT_SYSTEM_PROMPT = textwrap.dedent("""
Bạn là AI HR Agent.

Nhiệm vụ của bạn là giải quyết yêu cầu của người dùng
bằng cách suy luận và sử dụng các công cụ khi cần.

============================================================
AVAILABLE TOOLS
============================================================

{tool_descriptions}

============================================================
OUTPUT FORMAT
============================================================

Nếu cần gọi tool:

Thought: <reasoning>

Action:
<tool_name>[<json arguments>]


Nếu đã đủ thông tin:

Thought: <summary>

Final Answer:
<final response>

============================================================
GENERAL DECISION POLICY
============================================================

1.
Nếu câu hỏi chỉ cần kiến thức chung

→ trả lời trực tiếp.

Không gọi tool.

------------------------------------------------------------

2.
Nếu câu hỏi yêu cầu dữ liệu trong hệ thống

Ví dụ:

- hồ sơ ứng viên
- yêu cầu job
- điểm đánh giá
- lịch phỏng vấn

→ phải gọi tool.

------------------------------------------------------------

3.
Nếu nhiệm vụ cần nhiều bước

hãy:

- chia thành các bước nhỏ
- mỗi lần chỉ gọi một tool
- sau mỗi Observation đánh giá bước tiếp theo

Không lập kế hoạch cố định.

Hãy quyết định dựa trên:

- yêu cầu người dùng
- dữ liệu đã có
- khả năng của tool

------------------------------------------------------------

4.
Chỉ trả Final Answer khi

- đã đủ dữ liệu

hoặc

- không còn hành động hợp lệ.

============================================================
TOOL USAGE RULES
============================================================

Mỗi lần chỉ gọi MỘT tool.

Args phải là JSON hợp lệ.

Không tự tạo Observation.

Observation luôn do hệ thống cung cấp.

Không giả định kết quả của tool.

============================================================
MULTI STEP PLANNING
============================================================

Khi có nhiều bước:

Sau mỗi Observation hãy tự hỏi:

- Mình đã biết gì?
- Còn thiếu gì?
- Tool nào phù hợp nhất?

Chỉ gọi tool tiếp theo nếu thực sự cần.

============================================================
ERROR HANDLING
============================================================

Nếu Observation bắt đầu bằng

"LỖI:"

hãy:

- đọc nguyên nhân
- không giả định dữ liệu
- nếu không thể phục hồi
  → Final Answer giải thích lỗi

Nếu có nhiều cách xử lý

hãy chọn cách hợp lý nhất.

============================================================
ANTI LOOP
============================================================

Không gọi lại cùng:

(tool_name + args)

nếu Observation không thay đổi.

Nếu đã thử nhiều lần

hãy dừng.

============================================================
SAFE FALLBACK
============================================================

Nếu đạt MAX_ITERATIONS

→ dừng.

Trả lời:

- đã thu thập được gì
- còn thiếu gì
- vì sao không thể tiếp tục

Không tiếp tục gọi tool.

============================================================
PII
============================================================

Không đưa các thông tin sau vào Final Answer:

{pii_blacklist}

============================================================
FINAL ANSWER
============================================================

Final Answer cần:

- rõ ràng
- đúng dữ liệu
- không suy đoán
- trích dẫn các tool đã sử dụng

Ví dụ:

Tools used:

- parse_resume
- score_candidate
- schedule_interview

============================================================

User:

{user_query}

""").strip()
# ============================================================
# WELCOME MESSAGE
# ============================================================

WELCOME_MESSAGE = textwrap.dedent("""
👋 Xin chào!

Tôi là AI HR Agent.

Tôi có thể hỗ trợ bạn:

• Tra cứu yêu cầu tuyển dụng
• Phân tích hồ sơ ứng viên
• Đánh giá mức độ phù hợp
• Kiểm tra lịch phỏng vấn
• Đặt lịch phỏng vấn

Bạn muốn bắt đầu với tác vụ nào?
""").strip()


# ============================================================
# SAFE FALLBACK
# ============================================================

SAFE_FALLBACK_MESSAGE = textwrap.dedent("""
Xin lỗi.

Hệ thống đã đạt giới hạn xử lý sau {max_iterations} bước.

Để tránh suy đoán sai, tôi dừng tại đây.

Thông tin đã thu thập:

{collected_observations}

Bạn có thể:

- thử lại với yêu cầu cụ thể hơn
- kiểm tra dữ liệu đầu vào
- hoặc liên hệ quản trị hệ thống.
""").strip()


# ============================================================
# GENERIC FEW SHOTS
# ============================================================

FEW_SHOTS = textwrap.dedent("""

==============================
Example 1
==============================

User:
Cho tôi biết yêu cầu của vị trí Backend Developer.

Thought:
Cần tra cứu thông tin vị trí.

Action:
get_job_requirements[
    {
        "job_id":"J002"
    }
]

Observation:
<<system>>

Thought:
Đã có dữ liệu.

Final Answer:

Vị trí Backend Developer yêu cầu:

- kỹ năng ...
- kinh nghiệm ...
- ...

Tools:
get_job_requirements

==============================
Example 2
==============================

User:
Đánh giá ứng viên C001 cho vị trí J001.

Thought:

Cần tính điểm phù hợp.

Action:

score_candidate[
    {
        "candidate_id":"C001",
        "job_id":"J001"
    }
]

Observation:
<<system>>

Thought:

Đã có điểm.

Final Answer:

Ứng viên đạt ...

Tools:

score_candidate

==============================
Example 3
==============================

User:

Đặt lịch phỏng vấn cho ứng viên.

Thought:

Chưa có đủ dữ liệu.

Cần xác định:

- ứng viên
- interviewer
- khung giờ

Action:

check_interviewer_availability[
    {
        "interviewer_id":"interviewer_1"
    }
]

Observation:
<<system>>

Thought:

Đã có lịch.

Tiếp tục chọn bước tiếp theo nếu cần.

==============================
Example 4
==============================

Observation:

LỖI: Candidate not found.

Thought:

Không thể tiếp tục.

Final Answer:

Không tìm thấy ứng viên.

Vui lòng kiểm tra lại mã ứng viên.

""").strip()


# ============================================================
# TOOL DESCRIPTION FORMATTER
# ============================================================

def _format_tool_descriptions(
    tool_descriptions: list[dict]
) -> str:
    """
    Convert tool metadata thành markdown.
    """

    lines = []

    for tool in tool_descriptions:

        name = tool.get("name", "unknown_tool")

        description = tool.get(
            "description",
            "No description."
        )

        parameters = tool.get("parameters", {})

        example = tool.get(
            "example",
            f"{name}[...]"
        )

        lines.append(
            f"""
### {name}

Description:
{description}

Parameters:
{parameters}

Example:
{example}
""".strip()
        )

    return "\n\n".join(lines)


# ============================================================
# SAFE FALLBACK RENDER
# ============================================================

def render_safe_fallback(
    observations: list[str]
) -> str:

    if observations:

        observation_text = "\n".join(
            f"- {item}"
            for item in observations
        )

    else:

        observation_text = (
            "Chưa có observation."
        )

    return (
        SAFE_FALLBACK_MESSAGE
        .replace(
            "{max_iterations}",
            str(MAX_ITERATIONS)
        )
        .replace(
            "{collected_observations}",
            observation_text
        )
    )


# ============================================================
# BASELINE RENDER
# ============================================================

def render_chatbot_baseline_prompt() -> str:
    return CHATBOT_BASELINE_PROMPT

# ============================================================
# REACT PROMPT RENDER
# ============================================================

def render_react_prompt(
    user_query: str,
    tool_descriptions: list[dict],
) -> str:
    """
    Render generalized ReAct prompt.
    """

    tool_block = _format_tool_descriptions(
        tool_descriptions
    )

    pii = ", ".join(PII_BLACKLIST)

    return (
        REACT_SYSTEM_PROMPT
        .replace(
            "{tool_descriptions}",
            tool_block,
        )
        .replace(
            "{user_query}",
            user_query,
        )
        .replace(
            "{pii_blacklist}",
            pii,
        )
    )


# ============================================================
# PROMPT METADATA
# ============================================================

PROMPT_METADATA = {

    "topic":
        "AI HR Agent",

    "version":
        "generalized-v1",

    "description":
        (
            "Generalized ReAct Prompt "
            "for HR Assistant"
        ),

    "features": [

        "Reasoning",

        "Tool Selection",

        "Multi-step Planning",

        "Safe Fallback",

        "Anti Loop",

        "PII Filter",

    ],

    "guardrails": {

        "MAX_ITERATIONS":
            MAX_ITERATIONS,

        "MAX_REPEATED_ACTIONS":
            MAX_REPEATED_ACTIONS,

        "QUALIFIED_THRESHOLD":
            SCORE_THRESHOLD_QUALIFIED,

        "MAYBE_THRESHOLD":
            SCORE_THRESHOLD_MAYBE,

    },

    "expected_tools": [

        "parse_resume",

        "get_job_requirements",

        "score_candidate",

        "check_interviewer_availability",

        "schedule_interview",

    ],

}


# ============================================================
# UTILITIES
# ============================================================

def print_prompt_metadata():

    print("=" * 60)

    print("Prompt Metadata")

    print("=" * 60)

    for key, value in PROMPT_METADATA.items():

        print(f"{key}: {value}")

    print()


def validate_prompt():

    assert MAX_ITERATIONS > 0

    assert MAX_REPEATED_ACTIONS > 0

    assert SCORE_THRESHOLD_QUALIFIED >= 0

    assert SCORE_THRESHOLD_MAYBE >= 0

    assert len(PII_BLACKLIST) > 0

    return True


# ============================================================
# SMOKE TEST
# ============================================================

if __name__ == "__main__":

    sample_tools = [

        {

            "name": "parse_resume",

            "description":
                "Read candidate profile",

            "parameters": {
                "candidate_id": "string"
            },

            "example":
                'parse_resume[{"candidate_id":"C001"}]',

        },

        {

            "name":
                "get_job_requirements",

            "description":
                "Read job requirements",

            "parameters": {
                "job_id": "string"
            },

            "example":
                'get_job_requirements[{"job_id":"J001"}]',

        },

        {

            "name":
                "score_candidate",

            "description":
                "Evaluate candidate",

            "parameters": {

                "candidate_id": "string",

                "job_id": "string",

            },

            "example":
                'score_candidate[{"candidate_id":"C001","job_id":"J001"}]',

        },

        {

            "name":
                "check_interviewer_availability",

            "description":
                "Get available interview slots",

            "parameters": {

                "interviewer_id": "string"

            },

            "example":
                'check_interviewer_availability[{"interviewer_id":"interviewer_1"}]',

        },

        {

            "name":
                "schedule_interview",

            "description":
                "Book interview",

            "parameters": {

                "candidate_id": "string",

                "interviewer_id": "string",

                "slot": "string",

            },

            "example":
                'schedule_interview[{"candidate_id":"C001","interviewer_id":"interviewer_1","slot":"2026-08-01 09:00"}]',

        },

    ]

    validate_prompt()

    prompt = render_react_prompt(

        user_query=(
            "Đánh giá ứng viên C001 "
            "cho vị trí J001."
        ),

        tool_descriptions=sample_tools,

    )

    print_prompt_metadata()

    print("=" * 60)

    print("Prompt Preview")

    print("=" * 60)

    print(prompt[:3000])

    print()

    print("=" * 60)

    print("Smoke Test PASSED")

    print("=" * 60)
