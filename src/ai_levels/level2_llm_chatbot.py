"""
🤖 CẤP ĐỘ 2: LLM CHATBOT (Baseline Chatbot không có Tool)
Dùng LLM sinh câu trả lời tự nhiên mượt mà, nhưng không thể truy cập
database HR thật (FAKE_CANDIDATES, FAKE_JOBS, FAKE_CALENDAR).

Đề tài: Trợ Lý Sàng Lọc Hồ Sơ Tuyển Dụng & Hẹn Phỏng Vấn (Chủ đề 9).
"""

CHATBOT_BASELINE_PROMPT = """Bạn là một Chatbot tư vấn HR thông thường.
Hãy trả lời câu hỏi của người dùng một cách thân thiện dựa trên kiến thức có sẵn.
Nếu không biết thông tin ứng viên / vị trí / lịch phỏng vấn cụ thể,
hãy thông báo lịch sự cho người dùng rằng cần Agent có công cụ để tra cứu.
"""


def llm_chatbot(user_input: str) -> str:
    """Demo offline không gọi LLM thật — dùng if/else giả lập."""
    text = user_input.lower()
    if "c001" in text or "c002" in text or "c003" in text or "ứng viên" in text:
        return ("🤖 [LLM Chatbot]: Tôi là AI hội thoại nhưng không được cấp "
                "công cụ tra cứu database HR, nên tôi không biết chính xác "
                "thông tin ứng viên bạn hỏi!")
    elif "j001" in text or "j002" in text or "vị trí" in text or "job" in text:
        return ("🤖 [LLM Chatbot]: Tôi không có quyền truy cập hệ thống tuyển dụng, "
                "nên tôi không thể tra cứu yêu cầu kỹ năng của vị trí cụ thể!")
    elif "lịch" in text or "phỏng vấn" in text or "interviewer" in text:
        return ("🤖 [LLM Chatbot]: Tôi không thể xem lịch trống của interviewer "
                "vì không có scheduler tool. Bạn cần Agent có công cụ để làm việc này!")
    else:
        return f"🤖 [LLM Chatbot]: Rất vui được hỗ trợ bạn về câu hỏi '{user_input}'!"


if __name__ == "__main__":
    print("=== DEMO CẤP ĐỘ 2: LLM CHATBOT BASELINE ===")
    q = "Ứng viên C002 có phù hợp với vị trí J002 không?"
    print(f"User: {q}")
    print(f"Bot : {llm_chatbot(q)}")