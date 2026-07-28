"""
🛠️ TOOL REGISTRY & SCHEMAS (Dành cho Role 2: Tool & Spec Engineer)
Đề tài: Sàng lọc Hồ sơ Tuyển dụng & Hẹn Phỏng vấn
"""

# ---- DATA GIẢ LẬP ----

FAKE_CANDIDATES = {
    "C001": {"name": "Nguyễn Văn A", "skills": ["Python", "SQL", "Machine Learning"], "years_experience": 2, "education": "Cử nhân CNTT"},
    "C002": {"name": "Trần Thị B", "skills": ["Java", "Spring Boot"], "years_experience": 5, "education": "Thạc sĩ CNTT"},
    "C003": {"name": "Lê Văn C", "skills": ["Python", "Data Analysis", "SQL"], "years_experience": 1, "education": "Cử nhân Kinh tế"},
}

FAKE_JOBS = {
    "J001": {"title": "Data Analyst", "required_skills": ["Python", "SQL"], "min_experience": 1},
    "J002": {"title": "Backend Developer", "required_skills": ["Java", "Spring Boot"], "min_experience": 3},
}

FAKE_CALENDAR = {
    "interviewer_1": ["2026-08-01 09:00", "2026-08-01 14:00"],
    "interviewer_2": [],  # cố tình để trống để test edge case "hết lịch"
}


def parse_resume(candidate_id: str) -> str:
    """
    Tra cứu hồ sơ ứng viên theo mã ID.

    Args:
        candidate_id (str): Mã ứng viên (Ví dụ: 'C001')

    Returns:
        str: Thông tin skills, số năm kinh nghiệm, học vấn của ứng viên
    """
    if candidate_id not in FAKE_CANDIDATES:
        return f"LỖI: Không tìm thấy hồ sơ ứng viên có mã '{candidate_id}'."
    c = FAKE_CANDIDATES[candidate_id]
    return (
        f"Ứng viên {c['name']} ({candidate_id}):\n"
        f"- Kỹ năng: {', '.join(c['skills'])}\n"
        f"- Kinh nghiệm: {c['years_experience']} năm\n"
        f"- Học vấn: {c['education']}"
    )


def get_job_requirements(job_id: str) -> str:
    """
    Tra cứu yêu cầu tuyển dụng của một vị trí công việc.

    Args:
        job_id (str): Mã vị trí (Ví dụ: 'J001')

    Returns:
        str: Yêu cầu kỹ năng và kinh nghiệm tối thiểu của vị trí
    """
    if job_id not in FAKE_JOBS:
        return f"LỖI: Không tìm thấy vị trí tuyển dụng có mã '{job_id}'."
    j = FAKE_JOBS[job_id]
    return (
        f"Vị trí {j['title']} ({job_id}):\n"
        f"- Kỹ năng yêu cầu: {', '.join(j['required_skills'])}\n"
        f"- Kinh nghiệm tối thiểu: {j['min_experience']} năm"
    )


def score_candidate(candidate_id: str, job_id: str) -> str:
    """
    Tính điểm phù hợp (%) giữa ứng viên và yêu cầu công việc, dựa trên
    mức độ trùng khớp kỹ năng và số năm kinh nghiệm.

    Args:
        candidate_id (str): Mã ứng viên (Ví dụ: 'C001')
        job_id (str): Mã vị trí (Ví dụ: 'J001')

    Returns:
        str: Điểm match phần trăm, danh sách kỹ năng trùng khớp, và
             kết luận có đủ kinh nghiệm hay không
    """
    if candidate_id not in FAKE_CANDIDATES:
        return f"LỖI: Không tìm thấy hồ sơ ứng viên có mã '{candidate_id}'."
    if job_id not in FAKE_JOBS:
        return f"LỖI: Không tìm thấy vị trí tuyển dụng có mã '{job_id}'."

    c = FAKE_CANDIDATES[candidate_id]
    j = FAKE_JOBS[job_id]
    matched = set(c["skills"]) & set(j["required_skills"])
    total = len(j["required_skills"])
    match_percent = round(len(matched) / total * 100, 1) if total else 0
    exp_ok = "Đủ" if c["years_experience"] >= j["min_experience"] else "Chưa đủ"

    return (
        f"Kết quả sàng lọc {c['name']} cho vị trí {j['title']}:\n"
        f"- Độ phù hợp kỹ năng: {match_percent}%\n"
        f"- Kỹ năng trùng khớp: {', '.join(matched) if matched else 'Không có'}\n"
        f"- Kinh nghiệm: {exp_ok} (yêu cầu {j['min_experience']} năm, ứng viên có {c['years_experience']} năm)"
    )


def check_interviewer_availability(interviewer_id: str) -> str:
    """
    Tra cứu các khung giờ trống của người phỏng vấn.

    Args:
        interviewer_id (str): Mã người phỏng vấn (Ví dụ: 'interviewer_1')

    Returns:
        str: Danh sách khung giờ trống, hoặc thông báo lỗi nếu hết lịch
    """
    if interviewer_id not in FAKE_CALENDAR:
        return f"LỖI: Không tìm thấy người phỏng vấn '{interviewer_id}'."
    slots = FAKE_CALENDAR[interviewer_id]
    if not slots:
        return f"LỖI: Người phỏng vấn '{interviewer_id}' hiện không có lịch trống."
    return f"Lịch trống của {interviewer_id}: {', '.join(slots)}"


def schedule_interview(candidate_id: str, interviewer_id: str, slot: str) -> str:
    """
    Đặt lịch phỏng vấn cho ứng viên với người phỏng vấn tại khung giờ chỉ định.
    Chỉ nên gọi tool này SAU KHI đã xác nhận điểm match đạt và slot còn trống.

    Args:
        candidate_id (str): Mã ứng viên (Ví dụ: 'C001')
        interviewer_id (str): Mã người phỏng vấn (Ví dụ: 'interviewer_1')
        slot (str): Khung giờ muốn đặt (Ví dụ: '2026-08-01 09:00')

    Returns:
        str: Xác nhận đặt lịch thành công hoặc thông báo lỗi
    """
    if candidate_id not in FAKE_CANDIDATES:
        return f"LỖI: Ứng viên '{candidate_id}' không tồn tại."
    if interviewer_id not in FAKE_CALENDAR or slot not in FAKE_CALENDAR[interviewer_id]:
        return f"LỖI: Khung giờ '{slot}' không hợp lệ hoặc đã có người đặt."

    FAKE_CALENDAR[interviewer_id].remove(slot)
    return f"Đã đặt lịch phỏng vấn thành công cho {candidate_id} với {interviewer_id} lúc {slot}."


# Danh sách các tool được đăng ký để Agent sử dụng
AVAILABLE_TOOLS = {
    "parse_resume": parse_resume,
    "get_job_requirements": get_job_requirements,
    "score_candidate": score_candidate,
    "check_interviewer_availability": check_interviewer_availability,
    "schedule_interview": schedule_interview,
}
