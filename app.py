"""Local entry point: UI routing only; safety runs in core/runtime.py."""
import logging
import sqlite3
import streamlit as st
from core.runtime import MonitorRuntime
from database.database import Repository
from ui import dashboard, live_monitor, history, report, settings
from ui.styles import apply_styles
from utils.environment import load_local_env

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
st.set_page_config(page_title="DriverGuard · Safety workspace", page_icon="DG", layout="wide")
apply_styles()
try:
    load_local_env()
except OSError as exc:
    st.warning(f"Không đọc được .env: {exc}. Giám sát vẫn có thể hoạt động.")
if "runtime" not in st.session_state:
    st.session_state.runtime = MonitorRuntime()
runtime = st.session_state.runtime

with st.sidebar:
    st.markdown('<div class="brand"><div class="brandmark">D</div><div><div class="brandname">DriverGuard</div><div class="brandnote">SAFETY WORKSPACE</div></div></div><div class="eyebrow">WORKSPACE</div>', unsafe_allow_html=True)
    page = st.radio("Điều hướng", ["Giám sát trực tiếp", "Tổng quan", "Lịch sử phiên", "Sự kiện an toàn", "Báo cáo phiên", "Cấu hình"], label_visibility="collapsed", key="navigation")
    st.divider()
    st.caption("LOCAL FIRST\n\nVideo xử lý trên máy. Chỉ gửi thống kê tới Gemini khi bạn chủ động tạo báo cáo.")
    st.markdown('<div class="safety-note">University prototype<br>Không dùng khi lái xe thật.<br>Emergency chỉ là mô phỏng.</div>', unsafe_allow_html=True)

    @st.fragment(run_every=1)
    def connection():
        runtime.heartbeat()
        result = runtime.latest()
        active = runtime.is_active()
        if active:
            st.caption(f"Phiên #{result.session_id or '…'} · {result.source} · {result.system_state}")
            if page != "Giám sát trực tiếp" and result.system_state in ("CONFIRMATION", "EMERGENCY"):
                st.error(f"{result.system_state} · {result.confirmation_remaining:.1f}s")
                if st.button("I'M AWAKE", key="sidebar_confirm", disabled=result.system_state != "CONFIRMATION"):
                    runtime.command("CONFIRM")
                st.caption("Quay lại Giám sát trực tiếp để xem chi tiết.")
            if page != "Giám sát trực tiếp" and st.button("Dừng & lưu phiên", key="sidebar_stop", use_container_width=True):
                runtime.stop()
                st.rerun()
        else:
            st.caption("Không có phiên đang chạy")
        old = st.session_state.get("was_active", active)
        st.session_state.was_active = active
        if old != active:
            st.rerun()
    connection()

try:
    with Repository(runtime.settings.database_path) as repository:
        if page == "Giám sát trực tiếp":
            live_monitor.render(runtime)
        elif page == "Tổng quan":
            dashboard.render(repository)
        elif page == "Lịch sử phiên":
            history.render(repository, runtime.settings.snapshot_root)
        elif page == "Sự kiện an toàn":
            history.render_emergencies(repository, runtime.settings.snapshot_root)
        elif page == "Báo cáo phiên":
            report.render(repository, runtime)
        else:
            settings.render(runtime)
except (sqlite3.Error, OSError) as exc:
    st.error(f"Không truy cập được dữ liệu: {exc}. Kiểm tra quyền ghi thư mục data và dung lượng ổ đĩa.")
    if runtime.is_active() and st.button("Dừng phiên an toàn"):
        runtime.stop()
        st.rerun()
st.markdown('<div class="safety-note">DriverGuard · AI Driver Drowsiness & Safety Monitoring System · Educational prototype, not a certified safety system.</div>', unsafe_allow_html=True)
