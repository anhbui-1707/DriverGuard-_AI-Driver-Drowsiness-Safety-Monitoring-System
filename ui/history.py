import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from ui.styles import heading, cards, timeline


def session_label(row):
    try:
        when = datetime.fromisoformat(row["start_time"]).astimezone().strftime("%d/%m/%Y · %H:%M")
    except (ValueError, TypeError):
        when = row["start_time"] or "—"
    return f"#{row['id']} · {when} · {row['source']} · {row['status']}"


def select_session(repository, key):
    sessions = repository.sessions()
    if not sessions:
        st.info("Chưa có phiên. Bắt đầu Webcam hoặc Demo rồi dừng để xem lịch sử.")
        return None
    sid = st.selectbox("Chọn phiên", [row["id"] for row in sessions], format_func=lambda sid: session_label(next(row for row in sessions if row["id"] == sid)), key=key)
    return next(row for row in sessions if row["id"] == sid)


def snapshot_path(path, root):
    if not path:
        return None
    value = Path(path)
    candidate = value if value.is_absolute() else root/value
    # Only show images stored inside this project's snapshot folder.
    if candidate.resolve().is_relative_to((root/"assets/screenshots").resolve()) and candidate.is_file():
        return candidate
    return None


def render_snapshots(events, root):
    for event in events:
        if event["event_type"] != "EMERGENCY":
            continue
        st.markdown(f"**Emergency Simulation · {event['timestamp']} · {event['risk_score']:.0f}/100**")
        image = snapshot_path(event["snapshot_path"], root)
        if image:
            st.image(str(image), width=480)
        else:
            st.caption("Không có snapshot: phiên mô phỏng, camera mất hình hoặc ảnh không còn trên máy.")


def render(repository, root):
    heading("Lịch sử phiên", "Thống kê, Risk Score và sự kiện được lưu trên máy của bạn.")
    session = select_session(repository, "history_session")
    if session is None:
        return
    cards([( "Thời lượng", f"{session['duration']:.0f}s", session["status"]),
           ("Risk trung bình", f"{session['avg_risk']:.1f}", "Heuristic / 100"),
           ("Risk cao nhất", f"{session['max_risk']:.1f}", "Heuristic / 100"),
           ("Emergency", session["emergency_count"], "Chỉ mô phỏng")])
    st.caption(f"Ngáp: {session['yawn_count']} · Buồn ngủ: {session['drowsiness_count']} · Mất tập trung: {session['distraction_count']} · Nguồn: {session['source']}")
    if session["status"] == "RUNNING":
        st.info("Phiên đang chạy; thống kê được checkpoint mỗi vài giây. Dừng phiên để lấy số liệu cuối.")
    tabs = st.tabs(["Risk timeline", "Sự kiện", "Snapshots", "Báo cáo đã lưu"])
    with tabs[0], st.container(border=True):
        samples = repository.samples(session["id"])
        if samples:
            data = pd.DataFrame(samples).rename(columns={"elapsed": "Giây", "risk_score": "Risk Score"}).set_index("Giây")
            st.line_chart(data, color="#186b59", height=260)
        else:
            st.caption("Phiên quá ngắn hoặc phiên cũ chưa lưu risk samples.")
    events = repository.events(session["id"])
    with tabs[1], st.container(border=True):
        timeline(events)
    with tabs[2]:
        render_snapshots(events, root)
    with tabs[3]:
        if session["report"]:
            st.markdown(session["report"])
        else:
            st.caption("Mở trang Báo cáo phiên để tạo báo cáo.")


def render_emergencies(repository, root):
    heading("Sự kiện an toàn", "Các lần buồn ngủ, xác nhận tỉnh táo và Emergency Simulation.", "SIMULATION ONLY")
    session = select_session(repository, "emergency_session")
    if session:
        events = [row for row in repository.events(session["id"]) if row["event_type"] in ("DROWSINESS", "DRIVER_CONFIRMED_AWAKE", "CRITICAL", "EMERGENCY", "EMERGENCY_RESET")]
        with st.container(border=True):
            timeline(events)
        render_snapshots(events, root)
