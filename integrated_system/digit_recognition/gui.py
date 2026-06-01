import sys
import os

# 尝试设置 Qt 平台插件路径（Windows 上常见的 Qt 插件加载问题）
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

# 设置当前模块目录为工作目录，以便正确导入相对模块
_module_dir = os.path.dirname(os.path.abspath(__file__))
if _module_dir not in sys.path:
    sys.path.insert(0, _module_dir)

from train import Trainer
from recognizer import DigitRecognizer

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QLabel, QFileDialog, 
                            QProgressBar, QTextEdit, QMessageBox, QTabWidget,
                            QSpinBox, QDoubleSpinBox, QComboBox, QGroupBox)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

class TrainingThread(QThread):
    """训练线程，避免UI卡顿"""
    progress_update = pyqtSignal(int, int, float, float)
    training_finished = pyqtSignal(object)
    
    def __init__(self, model_type, epochs, batch_size, lr):
        super().__init__()
        self.model_type = model_type
        self.epochs = epochs
        self.batch_size = batch_size
        self.lr = lr
        
    def run(self):
        trainer = Trainer(
            model_type=self.model_type,
            epochs=self.epochs,
            batch_size=self.batch_size,
            lr=self.lr
        )
        
        def progress_callback(epoch, total_epochs, train_acc, test_acc):
            self.progress_update.emit(epoch, total_epochs, train_acc, test_acc)
            
        model = trainer.train(progress_callback)
        trainer.save_model()
        trainer.plot_training_history()
        
        self.training_finished.emit(trainer)

class MainWindow(QMainWindow):
    """主窗口类"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("手写数字识别系统")
        self.setGeometry(100, 100, 900, 700)
        
        self.recognizer = None
        self.init_ui()
        
        # 尝试加载最佳模型，如果没有则加载默认模型
        try:
            best_model_path = './models/mnist_model_best.pth'
            default_model_path = './models/mnist_model.pth'
            model_path = None

            if os.path.exists(best_model_path):
                model_path = best_model_path
            elif os.path.exists(default_model_path):
                model_path = default_model_path

            if model_path:
                self.recognizer = DigitRecognizer(model_path)
                self.model_info.setText(f"当前模型: {self.recognizer.model_type}")
                self.model_path_label.setText(f"模型文件: {model_path}")
                self.statusBar().showMessage(f"模型加载成功: {model_path}")
        except Exception as e:
            self.statusBar().showMessage(f"模型加载失败: {str(e)}")
            
    def init_ui(self):
        """初始化UI"""
        # 创建标签页
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # 识别标签页
        self.recognition_tab = QWidget()
        self.init_recognition_tab()
        self.tabs.addTab(self.recognition_tab, "数字识别")
        
        # 训练标签页
        self.training_tab = QWidget()
        self.init_training_tab()
        self.tabs.addTab(self.training_tab, "模型训练")
        
        # 状态栏
        self.statusBar().showMessage("准备就绪")
        
    def init_recognition_tab(self):
        """初始化识别标签页"""
        layout = QHBoxLayout()
        
        # 左侧控制面板
        left_panel = QVBoxLayout()
        
        # 单张识别组
        single_group = QGroupBox("单张图片识别")
        single_layout = QVBoxLayout()
        
        self.select_single_btn = QPushButton("选择图片")
        self.select_single_btn.clicked.connect(self.select_single_image)
        single_layout.addWidget(self.select_single_btn)
        
        self.single_result = QTextEdit()
        self.single_result.setReadOnly(True)
        single_layout.addWidget(self.single_result)
        
        single_group.setLayout(single_layout)
        left_panel.addWidget(single_group)
        
        # 批量识别组
        batch_group = QGroupBox("批量图片识别")
        batch_layout = QVBoxLayout()
        
        self.select_batch_btn = QPushButton("选择多张图片")
        self.select_batch_btn.clicked.connect(self.select_batch_images)
        batch_layout.addWidget(self.select_batch_btn)
        
        self.batch_result = QTextEdit()
        self.batch_result.setReadOnly(True)
        batch_layout.addWidget(self.batch_result)
        
        batch_group.setLayout(batch_layout)
        left_panel.addWidget(batch_group)
        
        # 模型加载
        model_group = QGroupBox("模型管理")
        model_layout = QVBoxLayout()
        
        self.load_model_btn = QPushButton("加载模型")
        self.load_model_btn.clicked.connect(self.load_model)
        model_layout.addWidget(self.load_model_btn)
        
        self.model_info = QLabel("当前模型: 未加载")
        model_layout.addWidget(self.model_info)
        
        self.model_path_label = QLabel("模型文件: 未加载")
        self.model_path_label.setWordWrap(True)
        model_layout.addWidget(self.model_path_label)

        left_panel.addStretch()
        layout.addLayout(left_panel, 1)
        
        # 右侧显示区域
        right_panel = QVBoxLayout()
        
        self.image_label = QLabel("图片显示区域")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(400, 400)
        self.image_label.setStyleSheet("border: 1px solid #ccc;")
        right_panel.addWidget(self.image_label)
        
        # 置信度图表
        self.figure = plt.figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.figure)
        right_panel.addWidget(self.canvas)
        
        layout.addLayout(right_panel, 2)
        
        self.recognition_tab.setLayout(layout)
        
    def init_training_tab(self):
        """初始化训练标签页"""
        layout = QVBoxLayout()
        
        # 参数设置
        params_group = QGroupBox("训练参数设置")
        params_layout = QHBoxLayout()
        
        # 模型类型
        model_layout = QVBoxLayout()
        model_layout.addWidget(QLabel("模型类型:"))
        self.model_type_combo = QComboBox()
        self.model_type_combo.addItems(["CNN", "MLP"])
        self.model_type_combo.setCurrentText("CNN")
        model_layout.addWidget(self.model_type_combo)
        params_layout.addLayout(model_layout)
        
        # Epochs
        epochs_layout = QVBoxLayout()
        epochs_layout.addWidget(QLabel("训练轮数:"))
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 50)
        self.epochs_spin.setValue(10)
        epochs_layout.addWidget(self.epochs_spin)
        params_layout.addLayout(epochs_layout)
        
        # Batch size
        batch_layout = QVBoxLayout()
        batch_layout.addWidget(QLabel("批次大小:"))
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(16, 256)
        self.batch_spin.setValue(64)
        batch_layout.addWidget(self.batch_spin)
        params_layout.addLayout(batch_layout)
        
        # 学习率
        lr_layout = QVBoxLayout()
        lr_layout.addWidget(QLabel("学习率:"))
        self.lr_spin = QDoubleSpinBox()
        self.lr_spin.setRange(0.0001, 0.1)
        self.lr_spin.setValue(0.001)
        self.lr_spin.setDecimals(4)
        lr_layout.addWidget(self.lr_spin)
        params_layout.addLayout(lr_layout)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # 训练控制
        control_layout = QHBoxLayout()
        self.start_train_btn = QPushButton("开始训练")
        self.start_train_btn.clicked.connect(self.start_training)
        control_layout.addWidget(self.start_train_btn)
        
        self.train_progress = QProgressBar()
        self.train_progress.setRange(0, 100)
        control_layout.addWidget(self.train_progress)
        
        layout.addLayout(control_layout)
        
        # 训练日志
        self.train_log = QTextEdit()
        self.train_log.setReadOnly(True)
        layout.addWidget(self.train_log)
        
        self.training_tab.setLayout(layout)
        
    def select_single_image(self):
        """选择单张图片进行识别"""
        if not self.recognizer:
            QMessageBox.warning(self, "警告", "请先加载模型!")
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if file_path:
            try:
                # 显示图片
                pixmap = QPixmap(file_path)
                scaled_pixmap = pixmap.scaled(
                    self.image_label.size(), 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
                
                # 进行识别
                result = self.recognizer.recognize_single(file_path)
                
                # 显示结果
                self.single_result.clear()
                self.single_result.append(f"识别结果: {result['digit']}")
                self.single_result.append(f"置信度: {result['confidence']:.2f}%")
                self.single_result.append(f"推理时间: {result['inference_time']:.2f} ms")
                
                # 绘制置信度图表
                self.plot_confidence(result['all_probabilities'])
                
                self.statusBar().showMessage(f"识别完成: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"识别失败: {str(e)}")
                
    def select_batch_images(self):
        """选择多张图片进行批量识别"""
        if not self.recognizer:
            QMessageBox.warning(self, "警告", "请先加载模型!")
            return
            
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择多张图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if file_paths:
            try:
                self.batch_result.clear()
                self.batch_result.append("开始批量识别...\n")
                
                results = self.recognizer.recognize_batch(file_paths)
                
                total = len(results)
                correct = 0
                
                for i, result in enumerate(results):
                    if 'error' in result:
                        self.batch_result.append(f"{i+1}. {result['filename']}: 错误 - {result['error']}")
                    else:
                        self.batch_result.append(
                            f"{i+1}. {result['filename']}: 数字={result['digit']}, "
                            f"置信度={result['confidence']:.2f}%, 时间={result['inference_time']:.2f}ms"
                        )
                        
                self.batch_result.append(f"\n批量识别完成，共处理 {total} 张图片")
                self.statusBar().showMessage(f"批量识别完成，共处理 {total} 张图片")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"批量识别失败: {str(e)}")
                
    def load_model(self):
        """加载模型"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择模型文件", "./models", "模型文件 (*.pth)"
        )
        
        if file_path:
            try:
                self.recognizer = DigitRecognizer(file_path)
                self.model_info.setText(f"当前模型: {self.recognizer.model_type}")
                self.model_path_label.setText(f"模型文件: {file_path}")
                QMessageBox.information(self, "成功", "模型加载成功!")
                self.statusBar().showMessage(f"模型加载成功: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"模型加载失败: {str(e)}")
                
    def plot_confidence(self, probabilities):
        """绘制置信度柱状图"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        digits = list(range(10))
        ax.bar(digits, probabilities, color='skyblue')
        ax.set_xlabel('数字')
        ax.set_ylabel('置信度 (%)')
        ax.set_title('各数字置信度分布')
        ax.set_xticks(digits)
        ax.set_ylim(0, 100)
        
        # 在柱子上显示数值
        for i, v in enumerate(probabilities):
            if v > 5:
                ax.text(i, v + 1, f"{v:.1f}%", ha='center', fontsize=8)
                
        self.figure.tight_layout()
        self.canvas.draw()
        
    def start_training(self):
        """开始训练模型"""
        model_type = self.model_type_combo.currentText()
        epochs = self.epochs_spin.value()
        batch_size = self.batch_spin.value()
        lr = self.lr_spin.value()
        
        # 禁用开始按钮
        self.start_train_btn.setEnabled(False)
        self.train_log.clear()
        self.train_log.append(f"开始训练 {model_type} 模型...")
        self.train_log.append(f"参数: Epochs={epochs}, Batch Size={batch_size}, Learning Rate={lr}")
        self.train_log.append("-" * 50)
        
        # 创建训练线程
        self.training_thread = TrainingThread(model_type, epochs, batch_size, lr)
        self.training_thread.progress_update.connect(self.update_training_progress)
        self.training_thread.training_finished.connect(self.training_completed)
        self.training_thread.start()
        
    def update_training_progress(self, epoch, total_epochs, train_acc, test_acc):
        """更新训练进度"""
        progress = int((epoch / total_epochs) * 100)
        self.train_progress.setValue(progress)
        
        self.train_log.append(
            f"Epoch {epoch}/{total_epochs}: 训练准确率={train_acc:.2f}%, 测试准确率={test_acc:.2f}%"
        )
        
        # 滚动到最后
        self.train_log.verticalScrollBar().setValue(
            self.train_log.verticalScrollBar().maximum()
        )
        
    def training_completed(self, trainer):
        """训练完成回调"""
        self.start_train_btn.setEnabled(True)
        self.train_progress.setValue(100)
        
        final_acc = trainer.test_accs[-1]
        self.train_log.append("-" * 50)
        self.train_log.append(f"训练完成! 最终测试准确率: {final_acc:.2f}%")
        self.train_log.append(f"模型已保存到: ./models/mnist_model.pth")
        self.train_log.append(f"最佳模型已保存到: ./models/mnist_model_best.pth")
        self.train_log.append(f"训练历史图已保存到: ./training_history.png")

        # 自动加载最佳模型
        best_model_path = './models/mnist_model_best.pth'
        default_model_path = './models/mnist_model.pth'
        load_path = best_model_path if os.path.exists(best_model_path) else default_model_path
        try:
            self.recognizer = DigitRecognizer(load_path)
            self.model_info.setText(f"当前模型: {self.recognizer.model_type}")
            self.model_path_label.setText(f"模型文件: {load_path}")
            self.statusBar().showMessage("最佳模型已自动加载")

            best_acc_text = f"最佳模型准确率: {trainer.best_test_acc:.2f}% (Epoch {trainer.best_epoch})"
            self.train_log.append(best_acc_text)
            self.train_log.append(f"当前加载的模型文件: {load_path}")
        except Exception as e:
            self.statusBar().showMessage(f"模型加载失败: {str(e)}")
            self.train_log.append(f"模型加载失败: {str(e)}")

        QMessageBox.information(
            self, "训练完成",
            f"模型训练完成!\n最终测试准确率: {final_acc:.2f}%\n已自动加载模型: {load_path}"
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
