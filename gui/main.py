import sys
import ctypes
import platform
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow
import matplotlib
matplotlib.use('Qt5Agg')

def is_admin():
    """Проверка прав администратора"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# main.py
if __name__ == "__main__":
    # Проверяем, запущен ли в режиме отладки
    is_debug = hasattr(sys, 'gettrace') and sys.gettrace() is not None
    
    # Для Windows проверяем права администратора только если не в режиме отладки
    if platform.system() == "Windows" and not is_debug:
        if not is_admin():
            # Перезапускаем с правами администратора
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, " ".join(sys.argv), None, 1
            )
            sys.exit()
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())