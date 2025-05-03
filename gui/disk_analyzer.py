import os
import psutil
from collections import defaultdict
from typing import Dict, List

class DiskAnalyzer:
    def __init__(self):
        self.large_files = []
        self.dir_sizes = defaultdict(int)
        self.file_types = defaultdict(int)
        self.usage_stats = {}

    def analyze_partition(self, path: str, max_files=1000) -> Dict:
        self._reset()
        self._scan_directory(path, max_files)
        self.usage_stats = self.get_usage_analysis(path)
        return {
            'large_files': sorted(self.large_files, key=lambda x: x[1], reverse=True),
            'dir_sizes': sorted(self.dir_sizes.items(), key=lambda x: x[1], reverse=True),
            'file_types': sorted(self.file_types.items(), key=lambda x: x[1], reverse=True),
            'usage': self.usage_stats
        }

    def get_usage_analysis(self, path: str) -> Dict:
        try:
            # Проверка существования пути
            if not os.path.exists(path):
                raise FileNotFoundError(f"Path {path} does not exist")

            # Проверка прав доступа
            if not os.access(path, os.R_OK):
                raise PermissionError(f"No read access to {path}")

            usage = psutil.disk_usage(path)
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': usage.percent
            }
        except Exception as e:
            raise RuntimeError(f"Failed to analyze {path}: {str(e)}")

    def _reset(self):
        self.large_files.clear()
        self.dir_sizes.clear()
        self.file_types.clear()

    def _scan_directory(self, path: str, max_files: int):
        file_count = 0
        try:
            for root, _, files in os.walk(path):
                for file in files:
                    if file_count >= max_files:
                        return
                    file_path = os.path.join(root, file)
                    self._process_file(file_path)
                    file_count += 1
        except Exception as e:
            pass

    def _process_file(self, file_path: str):
        try:
            size = os.path.getsize(file_path)
            ext = os.path.splitext(file_path)[1].lower() or 'no_ext'
            
            self.file_types[ext] += size
            
            if size > 100 * 1024 * 1024:
                self.large_files.append((file_path, size))
            
            parent_dir = os.path.dirname(file_path)
            self.dir_sizes[parent_dir] += size
        except (PermissionError, OSError):
            pass