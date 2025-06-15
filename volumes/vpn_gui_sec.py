from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel,
    QPushButton, QLineEdit, QMessageBox, QHBoxLayout, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QFont, QCursor, QColor, QRegion
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
import sys
import subprocess

class VPNOutputReader(QThread):
    auth_result = pyqtSignal(bool)
    assigned_ip = pyqtSignal(str)

    def __init__(self, process):
        super().__init__()
        self.process = process
        self.running = True

    def run(self):
        while self.running and self.process and self.process.stdout:
            line = self.process.stdout.readline()
            if not line:
                break
            if "AUTH_RESULT:True" in line:
                self.auth_result.emit(True)
            elif "AUTH_RESULT:False" in line:
                self.auth_result.emit(False)
            elif line.startswith("ASSIGN_IP:"):
                ip = line.strip().split(":")[1]
                self.assigned_ip.emit(ip)

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

class VPNApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vortex")
        self.setFixedSize(400, 700)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.connected = False
        self.drag_position = None
        self.vpn_process = None
        self.output_thread = None

        self.round_corners()
        self.init_ui()

    def round_corners(self):
        radius = 20
        mask = QRegion(0, 0, 0, 0)
        for x in range(0, 400):
            for y in range(0, 700):
                if (x < radius and y < radius and (x - radius) ** 2 + (y - radius) ** 2 > radius ** 2) or \
                   (x >= 400 - radius and y < radius and (x - (400 - radius)) ** 2 + (y - radius) ** 2 > radius ** 2) or \
                   (x < radius and y >= 700 - radius and (x - radius) ** 2 + (y - (700 - radius)) ** 2 > radius ** 2) or \
                   (x >= 400 - radius and y >= 700 - radius and (x - (400 - radius)) ** 2 + (y - (700 - radius)) ** 2 > radius ** 2):
                    continue
                mask = mask.united(QRegion(x, y, 1, 1))
        self.setMask(mask)

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        container = QWidget()
        container.setStyleSheet("background-color: #1e1e2f; border-radius: 20px;")

        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignTop)

        title_bar = QHBoxLayout()
        title_bar.setContentsMargins(25, 15, 20, 0)

        title_label = QLabel("Vortex")
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setStyleSheet("color: #bfaaff;")
        title_bar.addWidget(title_label)
        title_bar.addStretch()

        btn_min = QPushButton("-")
        btn_min.setFixedSize(40, 28)
        btn_min.setStyleSheet("QPushButton { color: white; border-radius: 14px; font-size: 18px; } QPushButton:hover { background: #666; }")
        btn_min.clicked.connect(self.showMinimized)

        btn_close = QPushButton("\u00d7")
        btn_close.setFixedSize(28, 28)
        btn_close.setStyleSheet("QPushButton { background: #aa4444; color: white; border-radius: 14px; font-size: 18px; } QPushButton:hover { background: #ff5555; }")
        btn_close.clicked.connect(self.close)

        title_bar.addWidget(btn_min)
        title_bar.addWidget(btn_close)
        layout.addLayout(title_bar)

        layout.addSpacing(120)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("VPN Password")
        self.password_input.setAlignment(Qt.AlignCenter)
        self.password_input.setFixedSize(260, 40)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 2px solid #444;
                border-radius: 10px;
                font-size: 14px;
                background-color: #2b2b3d;
                color: #ffffff;
            }
        """)
        layout.addWidget(self.password_input, alignment=Qt.AlignCenter)
        layout.addSpacing(65)

        self.connect_button = QPushButton("\u23fb")
        self.connect_button.setFont(QFont("Arial", 36))
        self.connect_button.setFixedSize(140, 140)
        layout.addWidget(self.connect_button, alignment=Qt.AlignHCenter)
        self.connect_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.connect_button.setStyleSheet("""
            QPushButton {
                border-radius: 70px;
                background-color: #3a3a50;
                color: #bfaaff;
            }
            QPushButton:hover {
                background-color: #4a4a65;
            }
        """)
        layout.addWidget(self.connect_button, alignment=Qt.AlignCenter)
        layout.addSpacing(30)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(191, 170, 255, 80))
        self.connect_button.setGraphicsEffect(shadow)

        self.connect_button.clicked.connect(self.toggle_vpn)

        self.status_label = QLabel("Not Connected")
        self.status_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.status_label.setStyleSheet("color: #ff6666;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.explain_label = QLabel("Your internet is not private.")
        self.explain_label.setFont(QFont("Arial", 10))
        self.explain_label.setStyleSheet("color: #bbbbbb;")
        self.explain_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.explain_label)

        layout.addStretch()

        self.ip_label = QLabel()
        self.ip_label.setFont(QFont("Arial", 11))
        self.ip_label.setStyleSheet("color: #bfaaff; margin-bottom: 20px;")
        self.ip_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.ip_label)

        main_layout.addWidget(container)
        self.setLayout(main_layout)

        QTimer.singleShot(500, self.update_ip)

    def update_ip(self, ip=None):
        if ip:
            self.ip_label.setText(f"IP: {ip}")
        else:
            self.default_ip = "10.9.0.5"
            self.ip_label.setText(f"IP: {self.default_ip}")

    def toggle_vpn(self):
        password = self.password_input.text().strip()
        if not password or len(password) < 4:
            msg = QMessageBox(self)
            msg.setIcon(QMessageBox.Warning)
            msg.setWindowTitle("Invalid Password")
            msg.setText("Enter a password with at least 4 characters.")
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #2b2b3d;
                    color: #bfaaff;
                    border: 2px solid #444;
                    font-family: Arial;
                    font-size: 13px;
                }
                QLabel {
                    color: #bfaaff; 
                }
                QPushButton {
                    background-color: #bfaaff;
                    color: #1e1e2f;
                    border-radius: 6px;
                    padding: 6px 12px;
                    min-width: 60px;
                }
                QPushButton:hover {
                    background-color: #d2bfff;
                }
            """)
            msg.exec_()
            return

        if not self.connected:
            try:
                self.vpn_process = subprocess.Popen(
                    ["sudo", "python3", "tun_client_sec.py"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                self.vpn_process.stdin.write(password + "\n")
                self.vpn_process.stdin.flush()

                self.output_thread = VPNOutputReader(self.vpn_process)
                self.output_thread.auth_result.connect(self.handle_auth_result)
                self.output_thread.assigned_ip.connect(self.update_ip)
                self.output_thread.start()

            except Exception as e:
                QMessageBox.critical(self, "Connection Error", f"Failed to start VPN client.\n\n{str(e)}")
        else:
            if self.output_thread:
                self.output_thread.stop()
                self.output_thread = None

            if self.vpn_process:
                try:
                    self.vpn_process.terminate()
                    try:
                        self.vpn_process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        self.vpn_process.kill()
                        self.vpn_process.wait()
                except Exception as e:
                    print("Error terminating VPN process:", e)
                self.vpn_process = None

            self.status_label.setText("Not Connected")
            self.status_label.setStyleSheet("color: #ff6666;")
            self.explain_label.setText("Your internet is not private.")
            self.connect_button.setStyleSheet("""
                QPushButton {
                    border-radius: 70px;
                    background-color: #3a3a50;
                    color: #bfaaff;
                }
                QPushButton:hover {
                    background-color: #4a4a65;
                }
            """)
            self.connected = False
            self.update_ip()

    def handle_auth_result(self, success):
        if success:
            self.status_label.setText("Connected")
            self.status_label.setStyleSheet("color: #66ff99;")
            self.explain_label.setText("Your internet is private.")
            self.connect_button.setStyleSheet("""
                QPushButton {
                    border-radius: 70px;
                    background-color: #bfaaff;
                    color: #1e1e2f;
                }
                QPushButton:hover {
                    background-color: #d2bfff;
                }
            """)
            self.connected = True
        else:
            self.status_label.setText("\u274c Not Connected")
            self.status_label.setStyleSheet("color: #ff6666;")
            self.explain_label.setText("Could not verify VPN connection.")
            self.connected = False
            if self.vpn_process:
                self.vpn_process.terminate()
                self.vpn_process = None

    def handle_assigned_ip(self, ip):
        self.update_ip(ip)

    def closeEvent(self, event):
        if self.output_thread:
            self.output_thread.stop()
            self.output_thread = None
        if self.vpn_process:
            self.vpn_process.terminate()
            self.vpn_process.wait()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    vpn_ui = VPNApp()
    vpn_ui.show()
    sys.exit(app.exec_())
