# 🚨 BẢNG PHÂN TÍCH FAILURE MODES — Chủ đề 9 (HR Assistant)

> **Mục đích**: Liệt kê trước tất cả các dạng lỗi mà ReAct Agent có thể gặp khi xử lý bài toán **Sàng lọc hồ sơ & Hẹn phỏng vấn**, dựa trên 5 tool thật + 3 ứng viên + 2 job + 2 interviewer trong `src/tools.py`. Từ đó Role 3 viết Guardrail, Role 2 cài error handling, Role 4 lắp Safe Fallback.
>
> **Cập nhật**: 2026-07-28 — Đồng bộ với bộ tool thực tế trong `src/tools.py` (Role 2).

---

## 📦 PHẠM VI TOOL & DỮ LIỆU THỰC TẾ

### 5 Tool đã khai báo trong `AVAILABLE_TOOLS`

| # | Tool | Chữ ký (signature) | Trả về khi OK | Trả về khi lỗi |
|---|---|---|---|---|
| 1 | `parse_resume` | `(candidate_id: str)` | Thông tin ứng viên | `"LỖI: Không tìm thấy hồ sơ ứng viên có mã '<id>'."` |
| 2 | `get_job_requirements` | `(job_id: str)` | Yêu cầu kỹ năng/kn của job | `"LỖI: Không tìm thấy vị trí tuyển dụng có mã '<id>'."` |
| 3 | `score_candidate` | `(candidate_id: str, job_id: str)` | Điểm % + matched skills | `"LỖI: Không tìm thấy hồ sơ ứng viên..."` / `"LỖI: Không tìm thấy vị trí..."` |
| 4 | `check_interviewer_availability` | `(interviewer_id: str)` | Danh sách slot trống | `"LỖI: Không tìm thấy người phỏng vấn..."` / `"LỖI: ...hiện không có lịch trống."` |
| 5 | `schedule_interview` | `(candidate_id, interviewer_id, slot)` | Xác nhận đặt lịch | `"LỖI: Ứng viên ... không tồn tại."` / `"LỖI: Khung giờ ... không hợp lệ hoặc đã có người đặt."` |

### Dữ liệu giả lập (FAKE DB)

```python
FAKE_CANDIDATES = {
    "C001": {"name": "Nguyễn Văn A", "skills": ["Python", "SQL", "Machine Learning"],
             "years_experience": 2, "education": "Cử nhân CNTT"},
    "C002": {"name": "Trần Thị B", "skills": ["Java", "Spring Boot"],
             "years_experience": 5, "education": "Thạc sĩ CNTT"},
    "C003": {"name": "Lê Văn C", "skills": ["Python", "Data Analysis", "SQL"],
             "years_experience": 1, "education": "Cử nhân Kinh tế"},
}

FAKE_JOBS = {
    "J001": {"title": "Data Analyst",
             "required_skills": ["Python", "SQL"], "min_experience": 1},
    "J002": {"title": "Backend Developer",
             "required_skills": ["Java", "Spring Boot"], "min_experience": 3},
}

FAKE_CALENDAR = {
    "interviewer_1": ["2026-08-01 09:00", "2026-08-01 14:00"],
    "interviewer_2": [],   # 👈 cố tình để trống → test edge case "hết lịch"
}
```

### Quy ước mã lỗi (MAPPING Chuẩn)

| Mã lỗi trong prompt | Chuỗi tool trả về | Dùng để Agent phân loại |
|---|---|---|
| `LỖI NOT_FOUND` | `LỖI: Không tìm thấy hồ sơ ứng viên...` | Đổi tool/tham số khác |
| `LỖI NOT_FOUND` | `LỖI: Không tìm thấy vị trí tuyển dụng...` | Tương tự |
| `LỖI NOT_FOUND` | `LỖI: Không tìm thấy người phỏng vấn...` | Tương tự |
| `LỖI EMPTY` | `LỖI: ...hiện không có lịch trống.` | Thử interviewer khác |
| `LỖI CONFLICT` | `LỖI: Khung giờ ... không hợp lệ hoặc đã có người đặt.` | Chọn slot khác |
| `LỖI INVALID` | `LỖI: Ứng viên ... không tồn tại.` | Kiểm tra lại ID |

> 💡 **Lưu ý cho Role 2**: Tool hiện trả `"LỖI: <message>"` (chưa có prefix mã lỗi). Cả nhóm thống nhất bổ sung prefix theo bảng trên (VD: `"LỖI NOT_FOUND: Không tìm thấy..."`) để Agent dễ parse. Role 3 đã chuẩn bị sẵn quy ước này trong prompt V2.

---

## 🚨 BẢNG 10 DẠNG LỖI + ROOT CAUSE + CÁCH XỬ LÝ

| # | Failure Mode | Ví dụ thực tế với tool hiện có | Root Cause | Cách Agent V2 xử lý |
|---|---|---|---|---|
| **F1** | **Unknown Tool** | Agent gọi `list_candidates` (không có) hoặc `send_email` (không có) | LLM tự bịa tên tool | Trả `"LỖI UNKNOWN_TOOL: Tool hợp lệ gồm [parse_resume, get_job_requirements, score_candidate, check_interviewer_availability, schedule_interview]"` |
| **F2** | **Candidate Not Found** | `parse_resume["C999"]` → `"LỖI: Không tìm thấy hồ sơ ứng viên có mã 'C999'."` | ID ứng viên sai/không tồn tại (chỉ có C001, C002, C003) | Agent V2 tự sửa: thử tool khác (VD: `get_job_requirements` để biết job ID đúng) hoặc Final Answer đề nghị user check lại |
| **F3** | **Job Not Found** | `get_job_requirements["J_NOT_EXIST"]` | Job ID sai (chỉ có J001, J002) | Tương tự F2 — Final Answer "Job J999 không tồn tại. Các job hiện có: J001 (Data Analyst), J002 (Backend Developer)" |
| **F4** | **Score With Invalid IDs** | `score_candidate["C999", "J001"]` | Candidate ID sai | Tool tự trả `"LỖI: Không tìm thấy hồ sơ ứng viên có mã 'C999'."` — Agent parse lỗi → sửa ID |
| **F5** | **Interviewer Not Found** | `check_interviewer_availability["interviewer_99"]` | Interviewer ID không tồn tại (chỉ có interviewer_1, interviewer_2) | Agent đổi sang interviewer_1; nếu user muốn cụ thể → trả "Hiện chỉ có interviewer_1 (còn lịch) và interviewer_2 (hết lịch)" |
| **F6** | **Empty Calendar (Edge Case cố ý)** | `check_interviewer_availability["interviewer_2"]` → `"LỖI: Người phỏng vấn 'interviewer_2' hiện không có lịch trống."` | `FAKE_CALENDAR["interviewer_2"] = []` — cố tình test | Agent phải **TỰ ĐỘNG** chuyển sang interviewer_1 thay vì đứng lại |
| **F7** | **Invalid Slot / Double Booking** | `schedule_interview["C001", "interviewer_1", "2026-08-01 09:00"]` (sau khi đã đặt rồi) | Slot bị xóa khỏi `FAKE_CALENDAR` sau lần đặt đầu | Tool trả `"LỖI: Khung giờ '2026-08-01 09:00' không hợp lệ hoặc đã có người đặt."` → Agent gọi lại `check_interviewer_availability` để lấy slot mới |
| **F8** | **Schedule Without Score (Logic Bug)** | Agent gọi `schedule_interview` cho C002 (Java Dev) vào job J001 (Data Analyst) mà chưa gọi `score_candidate` | Agent không tuân thủ thứ tự "sàng lọc trước, đặt lịch sau" | Prompt V2 có quy tắc: "Chỉ schedule sau khi `score_candidate` >= 70". Parser cảnh báo nếu thiếu bước |
| **F9** | **Repeated Action (Anti-Loop)** | Gọi `score_candidate["C001","J001"]` 3 lần liên tiếp | Agent kẹt không biết tiến triển | Anti-loop: Sau 2 lần trùng `(tool, args)` → ép đổi tool hoặc Final Answer dùng Observation trước đó |
| **F10** | **Max Iterations / Safe Fallback** | Workflow quá phức tạp, vượt quá 5 bước | Multi-step sàng lọc nhiều CV + nhiều job | Phanh cứng `MAX_ITERATIONS = 5` → trả Safe Fallback message lịch sự, kèm các Observation đã thu thập |
| **F11** | **Malformed Args** | `score_candidate["C001"]` (thiếu job_id) | LLM bỏ sót tham số bắt buộc | Trả `"LỖI INVALID_ARG: Thiếu tham số job_id. Cú pháp: score_candidate[candidate_id, job_id]"` |
| **F12** | **Hallucinated Observation** | Agent Final Answer "C001 đạt 85%" mà chưa gọi `score_candidate` | LLM bỏ qua bước Action | Parser từ chối Final Answer nếu Observation chưa có evidence cho tuyên bố đó |

---

