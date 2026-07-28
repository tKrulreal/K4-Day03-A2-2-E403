"""
🤖 CẤP ĐỘ 1: RULE-BASED BOT (Chatbot dựa trên luật if/else cố định)
Khớp từ khóa (keyword matching) với câu trả lời sẵn có. Không sử dụng LLM.

Đề tài: Trợ Lý Sàng Lọc Hồ Sơ Tuyển Dụng & Hẹn Phỏng Vấn (Chủ đề 9).
File demo minh họa Cấp 1 để so sánh tiến hóa với Cấp 2/3/4 trong src/ai_levels/.
"""

def rule_based_bot(user_input: str) -> str:
    text = user_input.lower()
    if "chào" in text or "hi" in text or "hello" in text:
        return ("Xin chào! Tôi là Rule-Based Bot (Cấp độ 1). "
                "Tôi có thể giúp gì cho bạn?")
    elif "sàng lọc" in text or "đánh giá" in text or "match" in text:
        return ("Gợi ý: Hãy so sánh kỹ năng ứng viên với kỹ năng yêu cầu của vị trí, "
                "sau đó tính tỉ lệ phần trăm trùng khớp.")
    elif "lịch" in text or "phỏng vấn" in text:
        return ("Gợi ý: Kiểm tra khung giờ trống của interviewer trước, "
                "rồi chọn slot đầu tiên còn trống.")
    elif "đặt lịch" in text or "schedule" in text:
        return "Hướng dẫn: Dùng lệnh 'đặt lịch C001 với interviewer_1 lúc 09:00'."
    elif "liên hệ" in text or "hotline" in text:
        return "Hotline Phòng Nhân sự VinUni: 1900-1234, Email: hr@vinuni.edu.vn"
    else:
        return ("Xin lỗi, câu hỏi của bạn nằm ngoài tập luật (keywords) "
                "được cài đặt sẵn của Rule-Based Bot!")


if __name__ == "__main__":
    print("=== DEMO CẤP ĐỘ 1: RULE-BASED BOT ===")
    test_queries = [
        "Chào bạn",
        "Hãy sàng lọc ứng viên cho vị trí J001",
        "Kiểm tra lịch trống của interviewer_1",
    ]
    for q in test_queries:
        print(f"User: {q}")
        print(f"Bot : {rule_based_bot(q)}\n")