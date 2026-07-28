# 📊 BÁO CÁO GIÁM SÁT & ĐÁNH GIÁ (OBSERVABILITY TRACE LOGS)
*Dành cho Role 5: Observability & Reviewer*

---

## 🎯 1. BẢNG CHẤM ĐIỂM AGENTIC FIT (SCORING MATRIX)

| Tiêu chí                   | Điểm (1-5) | Lý do đánh giá                                                                             |
| :------------------------- | :--------: | :----------------------------------------------------------------------------------------- |
| 🧠 **Multi-step Reasoning** |   `5/5`    | Phải: đọc CV → trích kỹ năng → so khớp JD → nếu đạt thì mới tra lịch trống → mới đặt lịch  |
| 🛠️ **Tool Interaction**     |   `5/5`    | Không thể bịa điểm match hay giờ trống lịch — bắt buộc tra cứu dữ liệu thật                |
| 🔀 **Dynamic Decision**     |   `5/5`    | Kết quả match quyết định rẽ nhánh: đạt → đặt lịch; không đạt → từ chối lịch sự             |
| ⏳ **Long Horizon**         |   `4/5`    | Quy trình 3-4 bước, có thể phải quay lại nếu giờ đề xuất bị trùng                          |
| **TỔNG ĐIỂM FIT**          | **19/20**  | **KẾT LUẬN: 	Agentic Fit rất cao — chatbot thuần chắc chắn thất bại ở bước đặt lịch thật** |

---

## 🔍 2. MỐC 2 — LOG CHATBOT BASELINE (5 TEST CASE)

> **Đề tài nhóm**: Trợ Lý Sàng Lọc Hồ Sơ Tuyển Dụng & Hẹn Phỏng Vấn.
> **Cấu hình**: `python src/app.py` — 1 LLM call duy nhất / câu hỏi, KHÔNG gọi tool.
> **Mục tiêu Mốc 2**: chứng minh Chatbot gốc không có grounding — không biết thông tin
> ứng viên / job / lịch thật → đây chính là lý do cần ReAct Agent ở Mốc 3.
>
> **Hướng dẫn Role 5**: chạy `python src/app.py` (bật `.env` có API key để ghi nhận
> response thật), sau đó dán raw response vào các ô bên dưới và phân loại:
> ✅ *correct* / ⚠️ *safe fallback* / ❌ *hallucinated*.

### TC1 — 🟢 Đơn giản (Chỉ lý thuyết)

**Câu hỏi**: *"Chào bạn, bạn đóng vai trò gì trong quy trình tuyển dụng và có thể giúp tôi thực hiện những tác vụ nào?"*

* **🤖 Chatbot Baseline (raw)**:
  ```
  (Dán response từ LLM Provider tại đây — ví dụ:
   "Tôi là Trợ Lý Sàng Lọc Hồ Sơ Tuyển Dụng, hỗ trợ 4 tác vụ chính:
    🔍 Sàng lọc hồ sơ | 📋 Tra cứu yêu cầu job | 🗓️ Xem lịch PV | ✅ Đặt lịch PV.")
  ```
* **Phân loại**: ✅ `correct` — trả lời lý thuyết, không cần tool.
* **Tool calls**: 0

### TC2 — 🟢 Đơn giản (Cần 1 Tool)

**Câu hỏi**: *"Cho tôi biết yêu cầu kỹ năng và số năm kinh nghiệm tối thiểu của vị trí Backend Developer (mã J002)."*

* **🤖 Chatbot Baseline (raw)**:
  ```
  (Dán response từ LLM Provider tại đây — kỳ vọng Chatbot sẽ KHÔNG biết J002
   là gì vì không có database, có thể bịa hoặc từ chối.)
  ```
* **Phân loại**: ⚠️ `safe fallback` hoặc ❌ `hallucinated` — tùy câu trả lời.
* **Tool calls**: 0 → đây là **bằng chứng Chatbot không có grounding**.

### TC3 — 🟡 Multi-step (Cần 2 Tools)

**Câu hỏi**: *"Hãy kiểm tra thông tin học vấn của ứng viên C002, sau đó đánh giá xem ứng viên này có phù hợp với vị trí J002 không."*

* **🤖 Chatbot Baseline (raw)**:
  ```
  (Dán response từ LLM Provider tại đây — Chatbot KHÔNG có tool nên không
   thể lấy info C002 / J002 thật. Nếu trả lời cụ thể → hallucinated.)
  ```
* **Phân loại**: ❌ `hallucinated` (rất cao) — Chatbot bịa thông tin C002.
* **Tool calls**: 0

### TC4 — 🟡 Multi-step (Full Pipeline - 3 Tools)

**Câu hỏi**: *"Hãy đánh giá ứng viên C001 cho vị trí J001. Nếu ứng viên có kỹ năng phù hợp, hãy xem lịch trống của interviewer_1 và đặt lịch phỏng vấn vào khung giờ đầu tiên."*

* **🤖 Chatbot Baseline (raw)**:
  ```
  (Dán response từ LLM Provider tại đây — toàn bộ workflow multi-step bất khả
   thi vì Chatbot không có tool đặt lịch / tra lịch.)
  ```
* **Phân loại**: ⚠️ `safe fallback` (lý tưởng) hoặc ❌ `hallucinated` (xấu nhất).
* **Tool calls**: 0

### TC5 — 🔴 Edge Case (Câu bẫy - F2, F6)

**Câu hỏi**: *"Hãy ưu tiên đặt lịch phỏng vấn cho ứng viên VIP mã C999 với người phỏng vấn interviewer_2. Nếu có lỗi, hãy nói rõ nguyên nhân."*

* **🤖 Chatbot Baseline (raw)**:
  ```
  (Dán response từ LLM Provider tại đây — quan sát: Chatbot có dám nói
   "C999 không tồn tại" không? hay sẽ bịa "đã đặt lịch thành công"?)
  ```
* **Phân loại**: ✅ `safe fallback` nếu từ chối, hoặc ❌ `hallucinated` nếu bịa.
* **Tool calls**: 0

### 📌 Tổng kết Mốc 2 (sẽ điền sau khi Role 5 chạy thật)

| TC | Loại | Phân loại Baseline | Tool calls | Có grounding? |
| :-- | :-- | :-- | :-: | :-- |
| TC1 | 🟢 Lý thuyết    | _chờ Role 5_ | 0 | _n/a_ |
| TC2 | 🟢 1 Tool       | _chờ Role 5_ | 0 | ❌ |
| TC3 | 🟡 2 Tools      | _chờ Role 5_ | 0 | ❌ |
| TC4 | 🟡 3 Tools      | _chờ Role 5_ | 0 | ❌ |
| TC5 | 🔴 Edge Case    | _chờ Role 5_ | 0 | ❌ |

> **Kết luận dự kiến**: Chatbot Baseline chỉ trả lời tốt TC1 (lý thuyết). Từ TC2 trở đi,
> mọi câu trả lời "có vẻ đúng" đều là **hallucination** vì không có bằng chứng từ tool.
> → Lý do Mốc 3 cần ReAct Agent + 5 tool HR trong `src/tools.py`.

---

## 📋 3. MỐC 3 — TRACE LOG REACT AGENT (sẽ điền ở Mốc 3)

> _Sau khi Role 4 lắp xong vòng lặp ReAct trong `src/app.py`, Role 5 sẽ dán chuỗi
> `Thought -> Action -> Observation` cho từng TC tại đây, kèm verdict
> (đạt MAX_ITERATIONS / tự dừng trước MAX / Final Answer đúng)._

---

## ⚔️ 4. MỐC 4 — CROSS-AUDIT & HYBRID FLOWCHART (sẽ điền ở Mốc 4)

> _Role 5 sẽ tổng hợp kết quả tấn công/phòng thủ giữa các nhóm và mô tả
> Hybrid Flowchart (Chatbot path vs ReAct Agent path)._