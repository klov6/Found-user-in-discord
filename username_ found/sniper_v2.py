import sys
import os
import json
import base64
import random
import time
import webbrowser
from datetime import datetime, timedelta

import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QCheckBox, QPushButton, QTextEdit, QFrame,
    QSlider, QMessageBox
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QTextCharFormat, QBrush, QFont, QCursor

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
CHARS = "abcdefghijklmnopqrstuvwxyz0123456789"

BLACKLIST = {
    "zzzz", "xxxx", "yyyy", "wwww", "6969", "4200", "0000",
    "1111", "2222", "proo", "gods", "ezpz", "gggg", "kkkk"
}

TOKENS_FILE = "Put ur token here (safe).txt"
PROXIES_FILE = "residential_proxies.txt"
VALID_USERNAMES_FILE = "valid_4char.txt"
LOG_FILE = "sniper.log"

MIN_DELAY = 1.0
MAX_DELAY = 2.0
EXTRA_SLEEP_AFTER_RL = 30.0

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def get_super_properties():
    build = random.randint(450000, 550000)
    props = {
        "os": "Windows",
        "browser": "Chrome",
        "device": "",
        "system_locale": "en-US",
        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "browser_version": "134.0",
        "os_version": "10",
        "referrer": "https://discord.com",
        "client_build_number": build,
        "release_channel": "stable",
        "client_event_source": None,
    }
    return base64.b64encode(json.dumps(props).encode()).decode()

SUPER_PROPERTIES_POOL = [get_super_properties() for _ in range(15)]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
]

def load_first_token():
    if not os.path.exists(TOKENS_FILE):
        return None
    with open(TOKENS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            token = line.strip()
            if token and len(token) > 30:
                return token
    return None

def load_proxies():
    if not os.path.exists(PROXIES_FILE):
        return []
    with open(PROXIES_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

temp_blacklist = set()

def generate_smart_username(target_length):
    special_chars = [".", "_", ""] 
    
    while True:
        extra_char = random.choice(special_chars)
        needed_letters = target_length - len(extra_char)
        if needed_letters < 1:
            continue
            
        letters = "".join(random.choices(CHARS, k=needed_letters))
        
        if extra_char:
            pos = random.randint(1, len(letters) - 1)
            username = letters[:pos] + extra_char + letters[pos:]
        else:
            username = letters

        if len(username) == target_length:
            if username in BLACKLIST or username in temp_blacklist:
                continue
            if username[0] in '._' or username[-1] in '._' or '..' in username or '__' in username:
                continue
            return username

# ----------------------------------------------------------------------
# Worker signals and worker thread
# ----------------------------------------------------------------------
class WorkerSignals(QObject):
    log_signal = pyqtSignal(str, str)              # message, color_name
    status_signal = pyqtSignal(int, int, float)    # checks, found, cpm
    progress_signal = pyqtSignal(bool)             # True = show progress bar, False = hide
    finished_signal = pyqtSignal()

class SniperWorker(QObject):
    def __init__(self, token, proxies, verbose, webhook_url, target_length):
        super().__init__()
        self.signals = WorkerSignals()
        self.token = token
        self.proxies = proxies
        self.verbose = verbose
        self.webhook_url = webhook_url
        self.target_length = target_length
        self._running = True

    def stop(self):
        self._running = False

    def _log(self, message, color_name="white"):
        self.signals.log_signal.emit(message, color_name)
        if self.verbose:
            try:
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
            except:
                pass

    def run(self):
        checks = 0
        found = 0
        start_time = datetime.now()
        token_cooldown_until = datetime.min
        proxy_index = 0

        self._log(f"Started with token ...{self.token[-6:]}", "yellow")

        while self._running:
            checks += 1

            if datetime.now() < token_cooldown_until:
                remaining = (token_cooldown_until - datetime.now()).total_seconds()
                self._log(f"Cooldown wait {remaining:.1f}s", "yellow")
                time.sleep(min(remaining, 2.0))
                continue

            try:
                username = generate_smart_username(self.target_length)
            except Exception as e:
                self._log(f"Error generating username: {e}", "red")
                time.sleep(1)
                continue

            self._log(f"TRY → {username}", "yellow")

            headers = {
                "Authorization": self.token,
                "User-Agent": random.choice(USER_AGENTS),
                "X-Super-Properties": random.choice(SUPER_PROPERTIES_POOL),
                "X-Discord-Locale": "en-US",
                "Accept": "*/*",
                "Content-Type": "application/json",
                "Sec-Ch-Ua": '"Google Chrome";v="134", "Chromium";v="134", "Not:A-Brand";v="24"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Origin": "https://discord.com",
                "Referer": "https://discord.com/channels/@me",
            }

            proxy = self.proxies[proxy_index % len(self.proxies)] if self.proxies else None
            proxies_dict = {"http": proxy, "https": proxy} if proxy else None

            success_request = False
            for attempt in range(3):
                if not self._running:
                    break
                try:
                    r = requests.post(
                        "https://discord.com/api/v9/users/@me/pomelo-attempt",
                        headers=headers,
                        json={"username": username},
                        proxies=proxies_dict,
                        timeout=5
                    )

                    if r.status_code == 200:
                        data = r.json()
                        if not data.get("taken", True):
                            found += 1
                            self._log(f"AVAILABLE → {username} 🔥", "green")
                            with open(VALID_USERNAMES_FILE, "a", encoding="utf-8") as f:
                                f.write(username + "\n")
                            
                            if self.webhook_url:
                                try:
                                    embed_payload = {
                                        "embeds": [
                                            {
                                                "title": "✨ Username Found",
                                                "color": 5763719,
                                                "fields": [
                                                    {
                                                        "name": " اليوزر",
                                                        "value": f"`{username}`",
                                                        "inline": True
                                                    },
                                                    {
                                                        "name": " طول اليوزر",
                                                        "value": f"`{len(username)}`",
                                                        "inline": True
                                                    },
                                                    {
                                                        "name": " الوقت ",
                                                        "value": f"`{datetime.now().strftime('%H:%M:%S')}`",
                                                        "inline": True
                                                    }
                                                ],
                                                "footer": {
                                                    "text": "Klov SNIPER • Automated Checker"
                                                }
                                            }
                                        ]
                                    }
                                    requests.post(self.webhook_url, json=embed_payload, timeout=5)
                                except Exception:
                                    pass
                            time.sleep(random.uniform(5, 10))
                        else:
                            temp_blacklist.add(username)
                    elif r.status_code == 429:
                        retry = 10.0
                        try:
                            retry = float(r.json().get("retry_after", 10.0))
                        except Exception:
                            pass
                        total_sleep = retry + EXTRA_SLEEP_AFTER_RL
                        self._log(f"429 Rate Limited → sleep {total_sleep:.1f}s", "red")
                        token_cooldown_until = datetime.now() + timedelta(seconds=total_sleep)
                    elif r.status_code in (401, 403):
                        self._log("TOKEN DEAD – Invalid/banned", "red")
                        if self.webhook_url:
                            try:
                                dead_embed = {
                                    "embeds": [
                                        {
                                            "title": "⚰️ Token Dead / Invalid",
                                            "description": f"Token ended with `...{self.token[-6:]}` has been banned or expired.",
                                            "color": 15548997,
                                            "footer": {
                                                "text": "Klov SNIPER • Alert System"
                                            }
                                        }
                                    ]
                                }
                                requests.post(self.webhook_url, json=dead_embed, timeout=5)
                            except Exception:
                                pass
                        self._running = False
                        break
                    
                    success_request = True
                    break

                except requests.exceptions.Timeout:
                    self._log(f"Timeout on attempt {attempt+1} (Proxy might be dead)", "red")
                except Exception as e:
                    self._log(f"ERR attempt {attempt+1}: {e}", "red")
                
                if attempt < 2:
                    time.sleep(1)

            if self.proxies and not success_request:
                proxy_index += 1

            elapsed = (datetime.now() - start_time).total_seconds() / 60
            cpm = round(checks / elapsed, 1) if elapsed > 0 else 0
            self.signals.status_signal.emit(checks, found, cpm)

            delay = random.uniform(MIN_DELAY, MAX_DELAY)
            time.sleep(delay)

        elapsed = (datetime.now() - start_time).total_seconds() / 60
        cpm = round(checks / elapsed, 1) if elapsed > 0 else 0
        self.signals.status_signal.emit(checks, found, cpm)
        self.signals.progress_signal.emit(False)
        self._log("Sniper stopped.", "yellow")
        self.signals.finished_signal.emit()

# ----------------------------------------------------------------------
# Main Window
# ----------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Klov Discord Username Sniper")
        self.setGeometry(100, 100, 950, 640)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0b0e14;
            }
            QWidget {
                color: #c0c6d4;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QFrame#card {
                background-color: #121824;
                border: 1px solid #1f293d;
                border-radius: 12px;
            }
            QLineEdit {
                background-color: #0d121d;
                border: 1px solid #00d2ff;
                border-radius: 8px;
                color: #ffffff;
                padding: 8px 12px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 1px solid #00f2fe;
            }
            QCheckBox {
                color: #8a99ad;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #1f293d;
                background: #0d121d;
            }
            QCheckBox::indicator:checked {
                background-color: #00d2ff;
            }
            QTextEdit {
                background-color: #090c10;
                border: 1px solid #1a2332;
                border-radius: 10px;
                color: #00f2fe;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                padding: 10px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # Header Area
        header_frame = QFrame()
        header_frame.setObjectName("card")
        header_frame.setStyleSheet("""
            QFrame#card {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #121824, stop:0.5 #1a102f, stop:1 #121824);
                border: 1px solid #2a1b4e;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 12, 15, 12)

        title_label = QLabel("Klov SNIPER")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Segoe UI", 25, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #00d2ff; letter-spacing: 2px;")
        
        subtitle_label = QLabel("discord username sniper")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        subtitle_label.setStyleSheet("color: #c0c6d4; letter-spacing: 1px;")

        links_layout = QHBoxLayout()
        links_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        owner_label = QLabel("Klov")
        owner_label.setStyleSheet("color: #ffcc00; font-weight: bold; margin-right: 15px;")
        
        yt_button = QPushButton("YouTube")
        yt_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        yt_button.setStyleSheet("background: none; border: none; color: #ff4b4b; font-weight: bold; font-size: 12px;")
        yt_button.clicked.connect(lambda: webbrowser.open("https://www.youtube.com/@Klov6")) 
        
        discord_button = QPushButton("Discord server")
        discord_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        discord_button.setStyleSheet("background: none; border: none; color: #5865F2; font-weight: bold; font-size: 12px; margin-left: 15px;")
        discord_button.clicked.connect(lambda: webbrowser.open("https://discord.gg/NnS7VTN56")) 

        links_layout.addWidget(owner_label)
        links_layout.addWidget(yt_button)
        links_layout.addWidget(discord_button)

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        header_layout.addSpacing(5)
        header_layout.addLayout(links_layout)
        main_layout.addWidget(header_frame)

        # Body Area
        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)

        # Left Panel (Stats)
        left_frame = QFrame()
        left_frame.setObjectName("card")
        left_frame.setFixedWidth(280)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(15, 15, 15, 15)

        stats_title = QLabel("📊 STATS")
        stats_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        stats_title.setStyleSheet("color: #00d2ff;")
        left_layout.addWidget(stats_title)

        self.lbl_checked = self.create_stat_card("Checked", "0", "#00d2ff")
        self.lbl_found = self.create_stat_card("Available", "0", "#00ff88")
        self.lbl_cpm = self.create_stat_card("CPM / Speed", "0.0", "#ff007f")
        self.lbl_status = self.create_stat_card("Status", "IDLE", "#8a99ad")

        left_layout.addWidget(self.lbl_checked['frame'])
        left_layout.addWidget(self.lbl_found['frame'])
        left_layout.addWidget(self.lbl_cpm['frame'])
        left_layout.addWidget(self.lbl_status['frame'])
        left_layout.addStretch()

        # Right Panel (Settings & Logs)
        right_frame = QFrame()
        right_frame.setObjectName("card")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(15, 15, 15, 15)

        # Webhook & Checkbox
        settings_box = QHBoxLayout()
        self.webhook_input = QLineEdit()
        self.webhook_input.setPlaceholderText("https://discord.com/api/webhooks/...")
        
        self.verbose_check = QCheckBox("Save File Log")
        settings_box.addWidget(QLabel("Webhook:"))
        settings_box.addWidget(self.webhook_input, 1)
        settings_box.addWidget(self.verbose_check)
        right_layout.addLayout(settings_box)

        # Username Length Slider Control
        length_layout = QHBoxLayout()
        length_label = QLabel("Username Length:")
        length_label.setStyleSheet("color: #8a99ad; font-size: 12px; font-weight: bold;")
        
        self.length_slider = QSlider(Qt.Orientation.Horizontal)
        self.length_slider.setRange(4, 10)
        self.length_slider.setValue(5)
        self.length_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #1f293d;
                height: 6px;
                background: #0d121d;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #00d2ff;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 1px solid #00d2ff;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
        """)
        
        self.length_value_label = QLabel("5")
        self.length_value_label.setStyleSheet("color: #00d2ff; font-weight: bold; font-size: 14px;")
        self.length_slider.valueChanged.connect(lambda val: self.length_value_label.setText(str(val)))
        
        length_layout.addWidget(length_label)
        length_layout.addWidget(self.length_slider, 1)
        length_layout.addWidget(self.length_value_label)
        right_layout.addLayout(length_layout)

        # Logs Area
        logs_title = QLabel("📜 LOGS")
        logs_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        logs_title.setStyleSheet("color: #8a99ad; margin-top: 5px;")
        right_layout.addWidget(logs_title)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        right_layout.addWidget(self.log_area)

        # Start / Stop Buttons
        btn_layout = QHBoxLayout()
        
        self.start_button = QPushButton("START /  بدأ")
        self.start_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.start_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00c6ff, stop:1 #0072ff);
                color: white; font-weight: bold; font-size: 13px;
                padding: 12px; border-radius: 8px; border: none;
            }
            QPushButton:hover { background: #0072ff; }
            QPushButton:disabled { background: #1a2332; color: #4a5568; }
        """)
        self.start_button.clicked.connect(self.start_sniper)

        self.stop_button = QPushButton("STOP / توقف")
        self.stop_button.setEnabled(False)
        self.stop_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.stop_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff0844, stop:1 #ffb199);
                color: white; font-weight: bold; font-size: 13px;
                padding: 12px; border-radius: 8px; border: none;
            }
            QPushButton:hover { background: #ff0844; }
            QPushButton:disabled { background: #1a2332; color: #4a5568; }
        """)
        self.stop_button.clicked.connect(self.stop_sniper)

        btn_layout.addWidget(self.start_button)
        btn_layout.addWidget(self.stop_button)
        right_layout.addLayout(btn_layout)

        body_layout.addWidget(left_frame)
        body_layout.addWidget(right_frame, 1)
        main_layout.addLayout(body_layout)

        self.worker_thread = None
        self.worker = None

    def create_stat_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #0d121d;
                border: 1px solid #1a2332;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        
        t_label = QLabel(title)
        t_label.setStyleSheet("color: #8a99ad; font-size: 10px; font-weight: bold;")
        
        v_label = QLabel(value)
        v_label.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold;")
        
        layout.addWidget(t_label)
        layout.addWidget(v_label)
        return {'frame': card, 'value': v_label}

    def append_log(self, message, color_name):
        fmt = QTextCharFormat()
        if color_name == "green":
            fmt.setForeground(QBrush(QColor("#00ff88")))
        elif color_name == "red":
            fmt.setForeground(QBrush(QColor("#ff4b4b")))
        elif color_name == "yellow":
            fmt.setForeground(QBrush(QColor("#ffcc00")))
        else:
            fmt.setForeground(QBrush(QColor("#00f2fe")))
            
        self.log_area.moveCursor(self.log_area.textCursor().MoveOperation.End)
        self.log_area.textCursor().insertText(
            f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n", fmt
        )
        self.log_area.ensureCursorVisible()

    def on_log(self, message, color):
        self.append_log(message, color)

    def on_status(self, checks, found, cpm):
        self.lbl_checked['value'].setText(str(checks))
        self.lbl_found['value'].setText(str(found))
        self.lbl_cpm['value'].setText(f"{cpm:.1f}")

    def on_worker_finished(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.lbl_status['value'].setText("IDLE")
        self.lbl_status['value'].setStyleSheet("color: #8a99ad; font-size: 16px; font-weight: bold;")
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()

    def start_sniper(self):
        token = load_first_token()
        if not token:
            QMessageBox.critical(self, "Error", f"No valid token found in '{TOKENS_FILE}'!")
            return
        proxies = load_proxies()
        verbose = self.verbose_check.isChecked()
        webhook_url = self.webhook_input.text().strip()
        target_length = self.length_slider.value()

        self.worker = SniperWorker(token, proxies, verbose, webhook_url, target_length)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)

        self.worker.signals.log_signal.connect(self.on_log)
        self.worker.signals.status_signal.connect(self.on_status)
        self.worker.signals.finished_signal.connect(self.on_worker_finished)
        self.worker.signals.finished_signal.connect(self.worker.deleteLater)
        self.worker_thread.started.connect(self.worker.run)

        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.lbl_status['value'].setText("RUNNING")
        self.lbl_status['value'].setStyleSheet("color: #00ff88; font-size: 16px; font-weight: bold;")

        self.worker_thread.start()

    def stop_sniper(self):
        if self.worker:
            self.worker.stop()
            self.stop_button.setEnabled(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
