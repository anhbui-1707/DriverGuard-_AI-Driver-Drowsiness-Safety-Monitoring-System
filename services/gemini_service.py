"""Optional post-session text only. No images, names or safety decisions sent."""
import json
import os
import re
from urllib import request, error

FIELDS = ("duration", "avg_risk", "max_risk", "yawn_count", "drowsiness_count",
          "distraction_count", "emergency_count", "source", "status")


def local_report(session):
    return (f"### Tổng kết phiên #{session['id']}\n\n"
            f"Thời lượng: {session['duration']:.0f} giây. Nguồn: {session['source']}.\n\n"
            f"Risk Score trung bình {session['avg_risk']:.1f}/100, cao nhất {session['max_risk']:.1f}/100. "
            "Đây là điểm heuristic, không phải xác suất tai nạn hoặc chẩn đoán.\n\n"
            f"- Ngáp: {session['yawn_count']} lần\n- Mắt nhắm kéo dài: {session['drowsiness_count']} lần\n"
            f"- Mất tập trung: {session['distraction_count']} lần\n- Emergency Simulation: {session['emergency_count']} lần\n\n"
            "Nếu ngáp liên tục hoặc cảm thấy buồn ngủ, nên dừng ở nơi an toàn và nghỉ ngơi. "
            "Không dùng nguyên mẫu này thay thiết bị an toàn xe hoặc tư vấn y tế.\n\n"
            "_Báo cáo cục bộ theo dữ liệu thống kê; không gọi AI._")


def generate_report(session, api_key="", model="", opener=None):
    if not api_key:
        return local_report(session), "LOCAL", "Không có API key; đã tạo báo cáo cục bộ."
    model = model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    if not re.fullmatch(r"[a-zA-Z0-9._-]+", model):
        return local_report(session), "LOCAL", "Tên Gemini model không hợp lệ."
    prompt = ("Viết báo cáo ngắn bằng tiếng Việt cho dự án DriverGuard. Dữ liệu là heuristic, "
              "không được chẩn đoán y tế hoặc khẳng định hệ thống an toàn đã được chứng nhận. "
              "Emergency là mô phỏng, DEMO là dữ liệu tổng hợp. Nêu quan sát, giới hạn và lời khuyên nghỉ ngơi chung. "
              "Không bịa thông tin ngoài dữ liệu:\n" + json.dumps({key: session[key] for key in FIELDS}, ensure_ascii=False))
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": .3, "maxOutputTokens": 1600}}
    req = request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                          data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json", "x-goog-api-key": api_key}, method="POST")
    try:
        with (opener or request.urlopen)(req, timeout=15) as response:
            data = json.loads(response.read())
        candidates = data.get("candidates", [])
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        report = "\n".join(part.get("text", "") for part in parts if not part.get("thought"))
        if not report.strip():
            raise ValueError("Gemini không trả về nội dung")
        return report, "GEMINI", ""
    except (error.URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as exc:
        # Never print request/header/API key. Keep the core app working offline.
        code = getattr(exc, "code", None)
        reason = f"HTTP {code}" if code else type(exc).__name__
        return local_report(session), "LOCAL", f"Gemini không khả dụng ({reason}); đã dùng báo cáo cục bộ."
