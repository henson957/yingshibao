import sys
import os
import threading
import time
import socket
import subprocess
import webview

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import app, get_local_ip


class Api:
    def play_alert(self, room_name):
        """Play system sound and show native OS notification."""
        import platform
        system = platform.system()

        if system == 'Darwin':
            # macOS
            try:
                subprocess.run(['afplay', '/System/Library/Sounds/Ping.aiff'],
                             capture_output=True, timeout=2)
            except Exception:
                pass
            try:
                subprocess.run(['osascript', '-e',
                    f'display notification "{room_name}，时间到了！" with title "盈时宝" sound name "default"'],
                    capture_output=True, timeout=5)
            except Exception:
                pass

        elif system == 'Windows':
            # Windows
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass
            try:
                # Windows 10+ toast notification via PowerShell
                ps_script = f'''
                [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
                $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
                $textNodes = $template.GetElementsByTagName("text")
                $textNodes.Item(0).AppendChild($template.CreateTextNode("盈时宝")) > $null
                $textNodes.Item(1).AppendChild($template.CreateTextNode("{room_name}，时间到了！")) > $null
                $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
                [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("盈时宝").Show($toast)
                '''
                subprocess.run(['powershell', '-Command', ps_script],
                             capture_output=True, timeout=5)
            except Exception:
                pass

        return True


def start_server():
    app.run(host='0.0.0.0', port=5050, debug=False, use_reloader=False)


def wait_for_server():
    for i in range(30):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', 5050))
            s.close()
            return True
        except:
            time.sleep(1)
    return False


if __name__ == '__main__':
    threading.Thread(target=start_server, daemon=True).start()
    ip = get_local_ip()
    wait_for_server()

    api = Api()
    window = webview.create_window(
        '盈时宝',
        'http://localhost:5050',
        width=1100, height=780,
        resizable=True,
        text_select=True,
        js_api=api,
    )

    webview.start(private_mode=False)
