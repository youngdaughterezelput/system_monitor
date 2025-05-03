from collections import defaultdict
import os
import psutil
from typing import Dict, List
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class DiskAnalyzer:
    def __init__(self):
        self.large_files = []
        self.dir_sizes = defaultdict(int)
        self.file_types = defaultdict(int)
        self.usage_stats = {}

    def analyze_partition(self, path: str, max_files=1000) -> Dict:
        self._reset()
        try:
            self._scan_directory(path, max_files)
            self.usage_stats = self.get_usage_analysis(path)
        except Exception as e:
            raise RuntimeError(f"Analysis failed: {str(e)}")
        
        return {
            'large_files': sorted(self.large_files, key=lambda x: x[1], reverse=True),
            'dir_sizes': sorted(self.dir_sizes.items(), key=lambda x: x[1], reverse=True),
            'file_types': sorted(self.file_types.items(), key=lambda x: x[1], reverse=True),
            'usage': self.usage_stats
        }

    def _reset(self):
        self.large_files.clear()
        self.dir_sizes.clear()
        self.file_types.clear()
        self.usage_stats = {}

    def _scan_directory(self, path: str, max_files: int):
        file_count = 0
        try:
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file_count >= max_files:
                        return
                    file_path = os.path.join(root, file)
                    self._process_file(file_path)
                    file_count += 1
        except Exception as e:
            raise RuntimeError(f"Directory scan error: {str(e)}")

    def _process_file(self, file_path: str):
        try:
            if not os.path.exists(file_path):
                return

            size = os.path.getsize(file_path)
            ext = os.path.splitext(file_path)[1].lower() or 'no_extension'
            
            self.file_types[ext] += size
            
            if size > 100 * 1024 * 1024:
                self.large_files.append((file_path, size))
            
            parent_dir = os.path.dirname(file_path)
            self.dir_sizes[parent_dir] += size

        except (PermissionError, OSError) as e:
            pass

    def get_usage_analysis(self, path: str) -> Dict:  # Добавлен параметр path
        try:
            usage = psutil.disk_usage(path)
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': usage.percent
            }
        except Exception as e:
            raise RuntimeError(f"Usage analysis failed: {str(e)}")

    def plot_analysis(self, analysis_data: Dict) -> FigureCanvas:
        fig, axes = plt.subplots(1, 3, figsize=(15, 5))
        
        # Использование диска
        labels = ['Used', 'Free']
        sizes = [analysis_data['used'], analysis_data['free']]
        axes[0].pie(sizes, labels=labels, autopct='%1.1f%%')
        axes[0].set_title('Disk Usage')

        # Топ 10 директорий
        dirs = self.dir_sizes.most_common(10) if self.dir_sizes else []
        axes[1].barh([d[0] for d in dirs], [d[1] for d in dirs])
        axes[1].set_title('Top 10 Directories')
        axes[1].tick_params(axis='x', rotation=45)

        # Типы файлов
        file_types = self.file_types.most_common(10) if self.file_types else []
        axes[2].pie([t[1] for t in file_types], 
                   labels=[t[0] for t in file_types], 
                   autopct='%1.1f%%')
        axes[2].set_title('File Types Distribution')

        plt.tight_layout()
        return FigureCanvas(fig)