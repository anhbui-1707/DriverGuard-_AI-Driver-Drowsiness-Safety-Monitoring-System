import streamlit as st
import pandas as pd
from ui.styles import heading, cards
from ui.history import session_label


def render(repository):
    heading("Tổng quan", "Một góc nhìn rõ ràng về các phiên giám sát và tín hiệu an toàn.")
    rows = repository.sessions()
    finished = [row for row in rows if row["status"] != "RUNNING"]
    cards([( "Phiên đã lưu", len(finished), "Webcam & Demo"),
           ("Thời gian giám sát", f"{sum(row['duration'] for row in finished)/60:.1f} phút", "Tổng các phiên đã dừng"),
           ("Mắt nhắm kéo dài", sum(row["drowsiness_count"] for row in finished), "Số lần bắt đầu xác nhận"),
           ("Emergency Simulation", sum(row["emergency_count"] for row in finished), "Không gọi cứu hộ thật")])
    left, right = st.columns([2, 1], gap="large")
    with left, st.container(border=True):
        st.markdown("### Risk Score theo phiên")
        if finished:
            data = pd.DataFrame(list(reversed(finished[:20]))).rename(columns={"id": "Phiên", "avg_risk": "Trung bình", "max_risk": "Cao nhất"}).set_index("Phiên")
            st.bar_chart(data[["Trung bình", "Cao nhất"]], color=["#186b59", "#b6cbc4"], height=280)
        else:
            st.info("Dữ liệu thật sẽ xuất hiện sau phiên đầu tiên. Bạn có thể dùng Demo để thử.")
    with right, st.container(border=True):
        st.markdown("### Trước khi bắt đầu")
        st.markdown("1. Đặt webcam ngang tầm mắt, có đủ ánh sáng.\n2. Nhìn thẳng khi khởi tạo phiên.\n3. Chỉnh EAR/MAR nếu việc nhận diện chưa phù hợp.\n4. Dùng Demo để luyện luồng xác nhận trước buổi trình bày.")
        st.caption("Đóng ứng dụng khác đang dùng webcam. Không dùng để giám sát khi lái xe thật.")
    with st.container(border=True):
        st.markdown("### Phiên gần đây")
        if rows:
            display = [{"Phiên": session_label(row), "Thời lượng (s)": row["duration"], "Risk TB": row["avg_risk"], "Risk max": row["max_risk"], "Ngáp": row["yawn_count"], "Buồn ngủ": row["drowsiness_count"], "Emergency": row["emergency_count"]} for row in rows[:12]]
            st.dataframe(display, hide_index=True, use_container_width=True)
        else:
            st.caption("Chưa có phiên nào được lưu.")
