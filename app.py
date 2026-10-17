"""Launch the single local monitoring screen directly in the browser."""
import logging
import time
import webbrowser
from config import SETTINGS
from core.runtime import MonitorRuntime
from ui.live_bridge import LiveBridge


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    runtime = MonitorRuntime(SETTINGS)
    bridge = LiveBridge(runtime)
    url = bridge.url()
    print(f'DriverGuard đang chạy tại: {url}', flush=True)
    print('Giữ cửa sổ Terminal này mở. Nhấn Ctrl+C để thoát.', flush=True)
    webbrowser.open(url)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        runtime.stop()
        bridge.close()


if __name__ == '__main__':
    main()
