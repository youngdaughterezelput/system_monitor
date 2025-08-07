import ctypes
import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QComboBox, QTextEdit, QLabel, QProgressBar, QFrame)
from PyQt5.QtCore import Qt, QProcess, QTimer
import psutil
import platform
import subprocess
import re


class DefragTab(QWidget):
    def __init__(self):
        super().__init__()
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.update_console)
        self.process.readyReadStandardError.connect(self.update_console_error)
        self.process.finished.connect(self.defrag_completed)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Disk selection
        disk_layout = QHBoxLayout()
        disk_layout.addWidget(QLabel("Выберите диск:"))

        self.disk_selector = QComboBox()
        self.update_disk_list()
        disk_layout.addWidget(self.disk_selector)

        # Analysis button
        self.analyze_btn = QPushButton("Анализировать фрагментацию")
        self.analyze_btn.clicked.connect(self.analyze_fragmentation)
        disk_layout.addWidget(self.analyze_btn)

        # Defrag button
        self.defrag_btn = QPushButton("Дефрагментировать")
        self.defrag_btn.clicked.connect(self.start_defragmentation)
        self.defrag_btn.setEnabled(False)
        disk_layout.addWidget(self.defrag_btn)

        layout.addLayout(disk_layout)

        # Visualization frame
        self.vis_frame = QFrame()
        self.vis_frame.setFrameShape(QFrame.StyledPanel)
        self.vis_frame.setMinimumHeight(150)
        vis_layout = QVBoxLayout(self.vis_frame)

        self.vis_label = QLabel("Визуализация диска")
        self.vis_label.setAlignment(Qt.AlignCenter)
        vis_layout.addWidget(self.vis_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Прогресс: %p%")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        vis_layout.addWidget(self.progress_bar)

        layout.addWidget(self.vis_frame)

        # Console output
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setPlaceholderText("Здесь будет отображаться ход выполнения операций...")
        layout.addWidget(self.console)

        # Timer for visualization update
        self.vis_timer = QTimer()
        self.vis_timer.timeout.connect(self.update_visualization)

        # Analysis data
        self.fragmentation_data = None
        self.current_disk = None
        self.total_blocks = 0
        self.processed_blocks = 0

    def update_disk_list(self):
        self.disk_selector.clear()
        for part in psutil.disk_partitions():
            if part.fstype and part.device:
                self.disk_selector.addItem(
                    f"{part.device} ({part.mountpoint})",
                    part.mountpoint
                )

    def analyze_fragmentation(self):
        self.current_disk = self.disk_selector.currentData()
        if not self.current_disk:
            self.console.append("Ошибка: диск не выбран")
            return

        self.console.append(f"Начало анализа фрагментации для диска {self.current_disk}...")

        if platform.system() == "Windows":
            self.analyze_windows()
        else:
            self.analyze_linux()

    def analyze_windows(self):
        try:
            # Проверка прав администратора
            is_debug = hasattr(sys, 'gettrace') and sys.gettrace() is not None
            skip_admin = '--no-admin' in sys.argv

            if not is_debug and not skip_admin and not self.is_admin():
                self.console.append("Ошибка: требуется запуск от имени администратора")
                return

            # Run Windows defrag analysis command
            result = subprocess.run(
                ["defrag", self.current_disk[0] + ":", "/A", "/V"],
                capture_output=True,
                text=True,
                encoding='cp866'
            )

            if result.returncode == 0:
                self.parse_windows_analysis(result.stdout)
            else:
                self.console.append(f"Ошибка анализа: {result.stderr}")

        except Exception as e:
            self.console.append(f"Ошибка выполнения анализа: {str(e)}")

    def analyze_linux(self):
        try:
            # Проверка прав root
            is_debug = hasattr(sys, 'gettrace') and sys.gettrace() is not None
            skip_admin = '--no-admin' in sys.argv

            if not is_debug and not skip_admin and os.geteuid() != 0:
                self.console.append("Ошибка: требуется запуск с правами root (sudo)")
                return

            # On Linux use filefrag
            result = subprocess.run(
                ["sudo", "filefrag", "-v", self.current_disk],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                self.parse_linux_analysis(result.stdout)
            else:
                self.console.append(f"Ошибка анализа: {result.stderr}")

        except Exception as e:
            self.console.append(f"Ошибка выполнения анализа: {str(e)}")

    def parse_windows_analysis(self, output):
        self.console.append("Результаты анализа фрагментации:")
        self.console.append(output)

        # Extract fragmentation percentage
        frag_match = re.search(r"Найдено (\d+)% фрагментации", output)
        if frag_match:
            frag_percent = int(frag_match.group(1))
            self.fragmentation_data = {"percent": frag_percent}
            self.update_visualization_state(frag_percent)
            self.defrag_btn.setEnabled(frag_percent > 0)
        else:
            self.console.append("Не удалось определить уровень фрагментации")

    def parse_linux_analysis(self, output):
        self.console.append("Результаты анализа фрагментации:")
        self.console.append(output)

        # Count fragmented files
        frag_count = output.count("found")
        total_count = output.count("extents found")

        if total_count > 0:
            frag_percent = min(100, int((frag_count / total_count) * 100))
            self.fragmentation_data = {"percent": frag_percent}
            self.update_visualization_state(frag_percent)
            self.defrag_btn.setEnabled(frag_percent > 0)
        else:
            self.console.append("Не удалось определить уровень фрагментации")

    def update_visualization_state(self, frag_percent):
        """Update visualization based on fragmentation percentage"""
        self.vis_label.setText(f"Фрагментация диска: {frag_percent}%")

        if frag_percent < 10:
            self.vis_frame.setStyleSheet("background-color: #aaffaa;")  # Green
        elif frag_percent < 30:
            self.vis_frame.setStyleSheet("background-color: #ffffaa;")  # Yellow
        else:
            self.vis_frame.setStyleSheet("background-color: #ffaaaa;")  # Red

    def start_defragmentation(self):
        if not self.current_disk:
            self.console.append("Ошибка: диск не выбран")
            return

        self.console.append(f"Начало дефрагментации диска {self.current_disk}...")
        self.defrag_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.processed_blocks = 0

        # Set initial visualization state
        self.vis_frame.setStyleSheet("background-color: #aaaaff;")  # Blue
        self.vis_label.setText("Идет дефрагментация... 0%")

        if platform.system() == "Windows":
            self.process.start("defrag", [self.current_disk[0] + ":", "/U", "/V"])
            # For Windows, use artificial progress updates
            self.vis_timer.start(500)
        else:
            # For Linux, calculate total blocks
            self.total_blocks = self.calculate_total_blocks()
            self.process.start("sudo", ["e4defrag", "-v", self.current_disk])
            # For Linux, we'll parse real progress from output
            self.vis_timer.start(100)  # Faster updates for better responsiveness

    def calculate_total_blocks(self):
        """Calculate approximate total blocks for Linux filesystems"""
        try:
            # Get disk size in 1K blocks
            result = subprocess.run(
                ["df", "-P", "--block-size=1K", self.current_disk],
                capture_output=True,
                text=True
            )
            lines = result.stdout.splitlines()
            if len(lines) > 1:
                size_kb = int(lines[1].split()[1])
                # Convert to 4K blocks (typical filesystem block size)
                return size_kb // 4
        except Exception as e:
            self.console.append(f"Ошибка расчета блоков: {str(e)}")

        return 1000  # Default value if calculation fails

    def update_console(self):
        """Handle standard output from defrag process"""
        output = self.process.readAllStandardOutput().data().decode(
            'cp866' if platform.system() == "Windows" else 'utf-8'
        )
        self.console.append(output)

        # Parse progress from output
        self.parse_defrag_progress(output)

    def update_console_error(self):
        """Handle error output from defrag process"""
        error = self.process.readAllStandardError().data().decode(
            'cp866' if platform.system() == "Windows" else 'utf-8'
        )
        self.console.append(f"Ошибка: {error}")

        # Also try to parse progress from error output
        self.parse_defrag_progress(error)

    def parse_defrag_progress(self, text):
        """Parse defragmentation progress from output text"""
        if platform.system() == "Windows":
            # Windows progress format: "Прогресс: 50%"
            progress_match = re.search(r"Прогресс:\s*(\d+)%", text)
            if progress_match:
                progress = int(progress_match.group(1))
                self.progress_bar.setValue(progress)
                self.vis_label.setText(f"Идет дефрагментация... {progress}%")
        else:
            # Linux e4defrag format: "1/100 blocks processed"
            progress_match = re.search(r"(\d+)\s*/\s*(\d+)", text)
            if progress_match:
                current = int(progress_match.group(1))
                total = int(progress_match.group(2))

                if total > 0:
                    progress = int((current / total) * 100)
                    self.progress_bar.setValue(progress)
                    self.vis_label.setText(f"Идет дефрагментация... {progress}%")

    def update_visualization(self):
        """Update visualization for Windows (artificial progress)"""
        if platform.system() != "Windows":
            return  # Linux uses real progress parsing

        # Only update if process is running
        if self.process.state() == QProcess.Running:
            current = self.progress_bar.value()
            if current < 90:
                self.progress_bar.setValue(current + 1)
                self.vis_label.setText(f"Идет дефрагментация... {current + 1}%")

    def defrag_completed(self, exit_code):
        """Handle completion of defragmentation process"""
        self.vis_timer.stop()
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setValue(100)

        if exit_code == 0:
            self.console.append("Дефрагментация успешно завершена!")
            self.vis_frame.setStyleSheet("background-color: #aaffaa;")  # Green
            self.vis_label.setText("Дефрагментация завершена")
        else:
            self.console.append(f"Дефрагментация завершена с кодом ошибки: {exit_code}")
            self.vis_frame.setStyleSheet("background-color: #ffaaaa;")  # Red
            self.vis_label.setText("Ошибка дефрагментации")

    @staticmethod
    def is_admin():
        """Check if running as admin on Windows"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False