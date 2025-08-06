import ctypes
import os
import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QComboBox, QTextEdit, QLabel, QProgressBar, QFrame)
from PyQt5.QtCore import Qt, QTimer, QProcess
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
            # Проверка прав администратора (только если не в режиме отладки)
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
            # Проверка прав root (только если не в режиме отладки)
            is_debug = hasattr(sys, 'gettrace') and sys.gettrace() is not None
            skip_admin = '--no-admin' in sys.argv
            
            if not is_debug and not skip_admin and os.geteuid() != 0:
                self.console.append("Ошибка: требуется запуск с правами root (sudo)")
                return
                
            # On Linux we'll use filefrag
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
        # Parse Windows defrag analysis output
        self.console.append("Результаты анализа фрагментации:")
        self.console.append(output)
        
        # Extract fragmentation percentage
        frag_match = re.search(r"Найдено (\d+)% фрагментации", output)
        if frag_match:
            frag_percent = int(frag_match.group(1))
            self.fragmentation_data = {"percent": frag_percent}
            self.vis_label.setText(f"Фрагментация диска: {frag_percent}%")
            self.defrag_btn.setEnabled(frag_percent > 0)
            
            # Simple visualization - color based on fragmentation level
            if frag_percent < 10:
                self.vis_frame.setStyleSheet("background-color: #aaffaa;")
            elif frag_percent < 30:
                self.vis_frame.setStyleSheet("background-color: #ffffaa;")
            else:
                self.vis_frame.setStyleSheet("background-color: #ffaaaa;")
        else:
            self.console.append("Не удалось определить уровень фрагментации")
    
    def parse_linux_analysis(self, output):
        # Parse Linux filefrag output (simplified)
        self.console.append("Результаты анализа фрагментации:")
        self.console.append(output)
        
        # Count fragmented files (simplified approach)
        frag_count = output.count("found")
        total_count = output.count("extents found")
        
        if total_count > 0:
            frag_percent = min(100, int((frag_count / total_count) * 100))
            self.fragmentation_data = {"percent": frag_percent}
            self.vis_label.setText(f"Примерная фрагментация: {frag_percent}%")
            self.defrag_btn.setEnabled(frag_percent > 0)
            
            if frag_percent < 10:
                self.vis_frame.setStyleSheet("background-color: #aaffaa;")
            elif frag_percent < 30:
                self.vis_frame.setStyleSheet("background-color: #ffffaa;")
            else:
                self.vis_frame.setStyleSheet("background-color: #ffaaaa;")
        else:
            self.console.append("Не удалось определить уровень фрагментации")
    
    def start_defragmentation(self):
        if not self.current_disk:
            self.console.append("Ошибка: диск не выбран")
            return
        
        self.console.append(f"Начало дефрагментации диска {self.current_disk}...")
        self.defrag_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        
        if platform.system() == "Windows":
            self.process.start("defrag", [self.current_disk[0] + ":", "/U", "/V"])
        else:
            # On Linux we'll use e4defrag for ext4 or xfs_fsr for XFS
            self.process.start("sudo", ["e4defrag", "-v", self.current_disk])
        
        self.vis_timer.start(500)  # Update visualization every 500ms
    
    def update_console(self):
        output = self.process.readAllStandardOutput().data().decode('cp866' if platform.system() == "Windows" else 'utf-8')
        self.console.append(output)
    
    def update_console_error(self):
        error = self.process.readAllStandardError().data().decode('cp866' if platform.system() == "Windows" else 'utf-8')
        self.console.append(f"Ошибка: {error}")
    
    def defrag_completed(self, exit_code):
        self.vis_timer.stop()
        self.analyze_btn.setEnabled(True)
        
        if exit_code == 0:
            self.console.append("Дефрагментация успешно завершена!")
            self.progress_bar.setValue(100)
            self.vis_frame.setStyleSheet("background-color: #aaffaa;")
            self.vis_label.setText("Дефрагментация завершена")
        else:
            self.console.append(f"Дефрагментация завершена с кодом ошибки: {exit_code}")
            self.vis_frame.setStyleSheet("background-color: #ffaaaa;")
            self.vis_label.setText("Ошибка дефрагментации")
    
    def update_visualization(self):
        # Simulate progress update
        current = self.progress_bar.value()
        if current < 90:
            self.progress_bar.setValue(current + 5)
        
        # Simple visualization - alternating colors during defrag
        if current % 10 < 5:
            self.vis_frame.setStyleSheet("background-color: #aaaaff;")
        else:
            self.vis_frame.setStyleSheet("background-color: #aaffaa;")
        
        self.vis_label.setText(f"Идет дефрагментация... {current}%")

    @staticmethod
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False