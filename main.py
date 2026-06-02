import sys
import os

# 先尝试导入torch！！！这很重要！
DIGIT_RECOGNITION_AVAILABLE = False
DigitRecognitionWindow = None

try:
    import torch
    print("OK: PyTorch imported successfully! Version:", torch.__version__)
except Exception as e:
    print("Warning: PyTorch import failed:", str(e))

# 设置Qt平台插件路径
try:
    import PyQt5
    _base = os.path.dirname(PyQt5.__file__)
    _candidates = [
        os.path.join(_base, 'Qt5', 'plugins', 'platforms'),
        os.path.join(_base, 'Qt', 'plugins', 'platforms'),
        os.path.join(_base, 'Qt5', 'plugins'),
        os.path.join(_base, 'Qt', 'plugins'),
    ]
    for _qt_plugins in _candidates:
        if os.path.isdir(_qt_plugins):
            os.environ.setdefault('QT_QPA_PLATFORM_PLUGIN_PATH', _qt_plugins)
            break
except Exception:
    pass

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QLabel, QStyleFactory,
                             QMessageBox)
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor
from PyQt5.QtCore import Qt

# 导入三个系统的模块
from maze_solver.maze_pyqt import MazeSolverWidget
from news_search.news_search_pyqt import NewsSearchWidget

# 尝试导入gui（注意torch已经在前面导入过了！）
try:
    from digit_recognition.gui import MainWindow as DigitRecognitionWindow
    DIGIT_RECOGNITION_AVAILABLE = True
except Exception as e:
    print("Warning: 手写数字识别系统加载失败:", str(e))


class IntegratedSystem(QMainWindow):
    """整合三个系统的主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能工具整合系统")
        self.setGeometry(100, 50, 1200, 800)
        self.setMinimumSize(800, 600)
        
        self.setup_ui()
        self.apply_style()
        
    def setup_ui(self):
        """设置用户界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题栏
        title_label = QLabel("智能工具整合系统")
        title_label.setFont(QFont("微软雅黑", 20, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # 创建标签页控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("微软雅黑", 11))
        main_layout.addWidget(self.tab_widget, 1)
        
        # 添加三个系统的标签页
        self.add_maze_solver_tab()
        self.add_digit_recognition_tab()
        self.add_news_search_tab()
        
        # 状态栏
        self.statusBar().showMessage("欢迎使用智能工具整合系统")
        
    def add_maze_solver_tab(self):
        """添加迷宫寻路系统标签页"""
        try:
            maze_widget = MazeSolverWidget()
            self.tab_widget.addTab(maze_widget, "迷宫寻路系统")
        except Exception as e:
            error_label = QLabel(f"迷宫寻路系统加载失败：{str(e)}")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: red; font-size: 14px;")
            self.tab_widget.addTab(error_label, "迷宫寻路系统")
            
    def add_digit_recognition_tab(self):
        """添加手写数字识别系统标签页"""
        if not DIGIT_RECOGNITION_AVAILABLE:
            # 手写数字识别系统不可用
            unavailable_label = QLabel("手写数字识别系统\n\n该系统需要 PyTorch 支持。\n请安装 PyTorch 后重试。\n\n提示: pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu")
            unavailable_label.setAlignment(Qt.AlignCenter)
            unavailable_label.setStyleSheet("color: #666; font-size: 14px; padding: 50px;")
            self.tab_widget.addTab(unavailable_label, "手写数字识别")
            return
            
        try:
            # 更改工作目录到digit_recognition
            original_dir = os.getcwd()
            digit_dir = os.path.join(os.path.dirname(__file__), 'digit_recognition')
            if os.path.exists(digit_dir):
                os.chdir(digit_dir)
                
            digit_window = DigitRecognitionWindow()
            
            # 创建一个QWidget来包含DigitRecognitionWindow的内容
            digit_widget = QWidget()
            digit_layout = QVBoxLayout(digit_widget)
            digit_layout.setContentsMargins(0, 0, 0, 0)
            
            # 将digit_window的central widget取出并重新parent
            central = digit_window.takeCentralWidget()
            if central:
                digit_layout.addWidget(central)
                
            self.tab_widget.addTab(digit_widget, "手写数字识别")
            
            # 保存一些引用以便后续使用
            self.digit_window = digit_window
            
            # 恢复原工作目录
            os.chdir(original_dir)
            
        except Exception as e:
            error_label = QLabel(f"手写数字识别系统加载失败：{str(e)}\n\n其他两个系统仍可正常使用。")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: red; font-size: 14px; padding: 50px;")
            self.tab_widget.addTab(error_label, "手写数字识别")
            
    def add_news_search_tab(self):
        """添加姓名新闻搜索系统标签页"""
        try:
            news_widget = NewsSearchWidget()
            self.tab_widget.addTab(news_widget, "姓名新闻搜索")
        except Exception as e:
            error_label = QLabel(f"姓名新闻搜索系统加载失败：{str(e)}")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: red; font-size: 14px;")
            self.tab_widget.addTab(error_label, "姓名新闻搜索")
            
    def apply_style(self):
        """应用样式"""
        # 设置应用样式
        QApplication.setStyle(QStyleFactory.create('Fusion'))
        
        # 设置调色板
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.WindowText, Qt.black)
        palette.setColor(QPalette.Base, Qt.white)
        palette.setColor(QPalette.AlternateBase, QColor(233, 233, 233))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.black)
        palette.setColor(QPalette.Text, Qt.black)
        palette.setColor(QPalette.Button, QColor(240, 240, 240))
        palette.setColor(QPalette.ButtonText, Qt.black)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.white)
        
        QApplication.setPalette(palette)


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("智能工具整合系统")
    
    # 设置字体
    font = QFont("微软雅黑", 10)
    app.setFont(font)
    
    window = IntegratedSystem()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
