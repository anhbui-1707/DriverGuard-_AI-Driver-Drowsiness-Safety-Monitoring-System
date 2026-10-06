"""The cockpit renders once. Browser updates video and JSON independently."""
import streamlit as st
import streamlit.components.v1 as components
from ui.live_bridge import LiveBridge


def render(runtime):
    bridge = st.session_state.get("live_bridge")
    if bridge is None or bridge.runtime is not runtime:
        if bridge is not None:
            bridge.close()
        try:
            bridge = LiveBridge(runtime)
        except OSError as exc:
            st.error(f"Không mở được màn hình giám sát local: {exc}. Kiểm tra Terminal và chạy lại app.")
            return
        st.session_state.live_bridge = bridge
    # Fixed viewport with scrolling works on both laptop and narrow screens.
    # Link provides a direct view if an extension/browser blocks embedded frames.
    components.iframe(bridge.url(), height=1130, scrolling=True)
    st.link_button("Mở màn hình giám sát riêng", bridge.url())
    st.caption("Nếu vùng giám sát không hiện, dùng nút mở riêng phía trên. Các trang lịch sử/cấu hình vẫn ở menu bên trái.")
