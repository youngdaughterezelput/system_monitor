import sys
import os
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow
import matplotlib
matplotlib.use('Qt5Agg')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    
    app = QApplication(sys.argv)
    
    # Set application style (optional)
    app.setStyle('Fusion')
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start application event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()