import os
import streamlit as st
from services.gemini_service import generate_report
from ui.history import select_session
from ui.styles import heading


def render(repository, runtime):
    heading("Báo cáo phiên", "Tóm tắt các tín hiệu quan sát được, không đưa ra chẩn đoán.")
    session = select_session(repository, "report_session")
    if session is None:
        return
    with st.container(border=True):
        mode = st.radio("Loại báo cáo", ["Cục bộ / không gửi dữ liệu", "Gemini / tùy chọn"], horizontal=True)
        key = ""
        if mode.startswith("Gemini"):
            st.caption("Chỉ gửi thống kê: thời lượng, điểm nguy cơ, số sự kiện và nhãn Webcam/Demo. Không gửi ảnh, tên hay video.")
            key = os.getenv("GEMINI_API_KEY", "")
            if not key:
                key = st.text_input("Gemini API key", type="password", help="Hoặc cấu hình GEMINI_API_KEY trong .env. Không lưu key vào SQLite.")
            model = st.text_input("Gemini model", value=os.getenv("GEMINI_MODEL", "gemini-3.5-flash"))
        else:
            model = ""
        disabled = runtime.is_active() or session["status"] == "RUNNING"
        if disabled:
            st.info("Dừng phiên giám sát trước khi tạo báo cáo để số liệu được chốt.")
        if st.button("Tạo báo cáo", type="primary", disabled=disabled):
            with st.spinner("Đang tổng hợp báo cáo..."):
                report, source, message = generate_report(session, key, model)
                repository.save_report(session["id"], report, source)
                session["report"] = report
                session["report_source"] = source
            if message:
                st.warning(message)
        if session["report"]:
            st.caption(f"Nguồn: {session['report_source']}")
            st.markdown(session["report"])
            st.download_button("Tải báo cáo Markdown", session["report"], file_name=f"driverguard_session_{session['id']}.md", mime="text/markdown")
