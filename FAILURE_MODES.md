# 🚨 BẢNG PHÂN TÍCH FAILURE MODES — Chủ đề 9 (HR Assistant)

> **Mục đích**: Liệt kê trước tất cả các dạng lỗi mà ReAct Agent có thể gặp phải khi xử lý bài toán Sàng lọc hồ sơ & Hẹn phỏng vấn. Từ đó Role 3 viết Guardrail, Role 2 cài error handling, Role 4 lắp Safe Fallback.

---

## 📦 BỐI CẢNH 8 TOOL CỦA AGENT

| # | Tool | Mục đích | Tool ID |
|---|---|---|---|
| 1 | `list_candidates_by_job` | Lấy danh sách CV ứng tuyển 1 job | `list_candidates_by_job[job_id]` |
| 2 | `get_candidate_profile` | Lấy chi tiết 1 hồ sơ | `get_candidate_profile[candidate_id]` |
| 3 | `score_resume` | Chấm điểm CV theo JD | `score_resume[candidate_id, job_id]` |
| 4 | `match_skills` | So khớp kỹ năng | `match_skills[candidate_id, skill_list]` |
| 5 | `check_interviewer_availability` | Xem lịch trống interviewer | `check_interviewer_availability[interviewer_id, date]` |
| 6 | `schedule_interview` | Đặt lịch phỏng vấn | `schedule_interview[candidate_id, interviewer_id, slot]` |
| 7 | `send_email_invitation` | Gửi email mời PV | `send_email_invitation[candidate_id, slot]` |
| 8 | `check_duplicate_application` | Check ứng viên đã nộp chưa | `check_duplicate_application[email, job_id]` |

---

## 🚨 BẢNG 10 DẠNG LỖI + ROOT CAUSE + CÁCH XỬ LÝ

| # | Dạng lỗi (Failure Mode) | Biểu hiện thực tế | Root Cause | Cách Agent V2 xử lý |
|---|---|---|---|---|
| **F1** | **Unknown Tool** | AI gọi `rank_candidates` không có trong registry | LLM tự bịa tên tool khi không thấy | Trả về "Tool không tồn tại, các tool hợp lệ gồm: [list...]" trong Observation |
| **F2** | **Malformed Args** | `score_resume['CV001']` (thiếu job_id) | LLM quên hoặc nhầm tham số | Trả "LỖI INVALID_ARG: Thiếu tham số bắt buộc job_id", ép Agent tự sửa |
| **F3** | **Wrong Arg Type** | `schedule_interview['CV001', 'INT01', 'sáng mai']` | LLM truyền string mơ hồ thay vì ISO date | Trả "LỖI INVALID_ARG: slot phải là ISO date 'YYYY-MM-DDTHH:MM'" |
| **F4** | **Repeated Action** | Gọi `score_resume['CV001','J001']` 3 lần liên tiếp | Agent bị kẹt không biết tiến triển | Anti-loop: Sau 2 lần trùng → ép đổi tool hoặc Final Answer |
| **F5** | **Empty Result** | `list_candidates_by_job['J999']` → `[]` | Job ID không tồn tại hoặc chưa có ứng viên | Final Answer: "Chưa có ứng viên nào ứng tuyển job J999" |
| **F6** | **Permission Denied** | User không phải HR Admin cố truy cập CMND | RBAC (Role-Based Access Control) | Trả "LỖI PERMISSION: Cần quyền HR Admin" + Final Answer dừng ngay |
| **F7** | **Schedule Conflict** | `schedule_interview` lúc slot đã có người đặt | Collision trong DB | Trả "LỖI CONFLICT: Slot đã được đặt, gợi ý slot khác: [...]" |
| **F8** | **PII Leak** | Final Answer chứa "CMND: 012345678" | Tool trả về data nhạy cảm, Agent lặp lại | PII Filter trong prompt V2 + Post-process strip PII ở app.py |
| **F9** | **Hallucinated Observation** | Agent nghĩ ra "CV001 đạt 85đ" mà chưa gọi tool | LLM bỏ qua bước Action | Parser từ chối Final Answer nếu chưa có Observation thật |
| **F10** | **Max Iterations** | Agent lặp quá 5 bước mà chưa xong | Prompt không đủ rõ / Multi-step quá phức tạp | Safe Fallback message lịch sự, không crash |

---

## 🎯 4 TIÊU CHÍ AGENTIC FIT (Scoring Matrix)

| Tiêu chí | Điểm (1-5) | Lý do |
|---|:---:|---|
| 🧠 **Multi-step Reasoning** | 5/5 | Sàng lọc + match + đặt lịch + gửi mail = 4 bước phụ thuộc |
| 🛠️ **Tool Interaction** | 5/5 | Cần DB ứng viên, scheduler, mail service |
| 🔀 **Dynamic Decision** | 4/5 | Kết quả score quyết định có nên hẹn PV hay không |
| ⏳ **Long Horizon** | 4/5 | Workflow 2-5 bước, vừa phải |
| **TỔNG** | **18/20** | **RẤT NÊN DÙNG REACT AGENT** |

---

## 🛡️ GUARDRAILS ĐÃ CÀI TRONG `src/prompts.py`

```python
MAX_ITERATIONS = 5              # Phanh cứng
MAX_REPEATED_ACTIONS = 2        # Anti-loop
SCORE_THRESHOLD_QUALIFIED = 70  # Phân loại recommend/reject
SCORE_THRESHOLD_MAYBE = 50      # Vùng xám → cần Manager
PII_BLACKLIST = (
    "cmnd", "cccd", "passport",
    "số tài khoản", "mức lương cũ", "current salary"
)
```

---



> **Quy ước bàn giao**:
> - Role 2 (Tool Engineer) → Cài error handling sao cho **mọi exception đều trả về chuỗi `"LỖI <MÃ>: <message>"`** thay vì `raise`.
> - Role 4 (Integrator) → Dùng hàm `render_react_prompt(..., version="v2")` để có đầy đủ Guardrails.
> - Role 5 (Observability) → Khi thấy Observation bắt đầu bằng `"LỖI"`, ghi nhận là **1 lần trigger Guardrail**.
