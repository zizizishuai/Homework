import heapq
import random
import time
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QSpinBox, QRadioButton, QButtonGroup,
                             QSlider, QFrame, QMessageBox, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush


# 全局常量定义
COLOR_WALL = QColor(0, 0, 0)           # 墙壁：黑色
COLOR_PATH = QColor(255, 255, 255)     # 通路：白色
COLOR_START = QColor(0, 255, 0)        # 起点：绿色
COLOR_END = QColor(255, 0, 0)          # 终点：红色
COLOR_SEARCH = QColor(255, 255, 0)     # 算法探索节点：黄色
COLOR_FINAL = QColor(0, 0, 255)        # 最终路径：蓝色
COLOR_CANVAS_BG = QColor(224, 224, 224) # 画布背景色

CELL_SIZE = 30  # 每个迷宫单元格的像素大小
DEFAULT_ROWS = 15
DEFAULT_COLS = 15
WALL_RATE = 0.3


class Node:
    """A*算法的节点对象，存储坐标、代价、父节点"""
    def __init__(self, x, y, parent=None):
        self.x = x
        self.y = y
        self.parent = parent
        self.g = 0
        self.h = 0
        self.f = 0

    def __lt__(self, other):
        return self.f < other.f


class AStar:
    """A*寻路算法核心"""
    def __init__(self, maze, start, end, mode=4):
        self.maze = maze
        self.start = start
        self.end = end
        self.mode = mode
        self.rows = len(maze)
        self.cols = len(maze[0])
        self.open_list = []
        self.close_list = set()
        self.search_path = []

    def heuristic(self, node):
        """启发函数"""
        if self.mode == 4:
            return abs(node.x - self.end[0]) + abs(node.y - self.end[1])
        else:
            return max(abs(node.x - self.end[0]), abs(node.y - self.end[1]))

    def get_neighbors(self, node):
        """获取相邻节点"""
        neighbors = []
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if self.mode == 8:
            directions += [(-1, -1), (-1, 1), (1, -1), (1, 1)]

        for dx, dy in directions:
            x = node.x + dx
            y = node.y + dy
            if 0 <= x < self.rows and 0 <= y < self.cols and self.maze[x][y] == 0:
                neighbors.append((x, y))
        return neighbors

    def search(self):
        """执行搜索"""
        start_time = time.time()
        start_node = Node(self.start[0], self.start[1])
        end_node = Node(self.end[0], self.end[1])
        heapq.heappush(self.open_list, start_node)

        while self.open_list:
            current_node = heapq.heappop(self.open_list)
            self.close_list.add((current_node.x, current_node.y))
            self.search_path.append((current_node.x, current_node.y))

            if current_node.x == end_node.x and current_node.y == end_node.y:
                path = []
                while current_node:
                    path.append((current_node.x, current_node.y))
                    current_node = current_node.parent
                cost_time = round(time.time() - start_time, 3)
                return path[::-1], len(self.search_path), cost_time

            for x, y in self.get_neighbors(current_node):
                if (x, y) in self.close_list:
                    continue
                neighbor = Node(x, y, current_node)
                neighbor.g = current_node.g + 1
                neighbor.h = self.heuristic(neighbor)
                neighbor.f = neighbor.g + neighbor.h

                for node in self.open_list:
                    if node.x == neighbor.x and node.y == neighbor.y and node.g < neighbor.g:
                        break
                else:
                    heapq.heappush(self.open_list, neighbor)

        cost_time = round(time.time() - start_time, 3)
        return None, len(self.search_path), cost_time


class MazeGenerator:
    """迷宫生成器"""
    @staticmethod
    def create_empty(rows, cols):
        return [[0 for _ in range(cols)] for _ in range(rows)]

    @staticmethod
    def create_random(rows, cols, wall_rate=WALL_RATE):
        maze = [[0 for _ in range(cols)] for _ in range(rows)]
        for i in range(rows):
            for j in range(cols):
                if (i == 0 or i == rows - 1 or j == 0 or j == cols - 1):
                    if random.random() < wall_rate * 0.3:
                        maze[i][j] = 1
                else:
                    if random.random() < wall_rate:
                        maze[i][j] = 1
        return maze

    @staticmethod
    def create_dfs_maze(rows, cols):
        maze = [[1 for _ in range(cols)] for _ in range(rows)]
        stack = [(1, 1)]
        maze[1][1] = 0
        directions = [(-2, 0), (2, 0), (0, -2), (0, 2)]

        while stack:
            x, y = stack[-1]
            random.shuffle(directions)
            found = False
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                if 0 < nx < rows - 1 and 0 < ny < cols - 1 and maze[nx][ny] == 1:
                    maze[x + dx // 2][y + dy // 2] = 0
                    maze[nx][ny] = 0
                    stack.append((nx, ny))
                    found = True
                    break
            if not found:
                stack.pop()
        maze[0][cols // 2] = 0
        maze[rows - 1][cols // 2] = 0
        maze[rows // 2][0] = 0
        maze[rows // 2][cols - 1] = 0
        return maze


class MazeCanvas(QWidget):
    """迷宫绘制画布"""
    cell_clicked = pyqtSignal(int, int, str)  # row, col, button

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self.rows = DEFAULT_ROWS
        self.cols = DEFAULT_COLS
        self.maze = MazeGenerator.create_empty(self.rows, self.cols)
        self.start = None
        self.end = None
        self.path = []
        self.search_nodes = []
        self.drawing_wall = False

    def get_cell_size(self):
        """获取当前单元格大小（适应窗口）"""
        # 计算可用空间
        w = self.width() - 20  # 留一点边距
        h = self.height() - 20
        if w <= 0 or h <= 0:
            return CELL_SIZE
        # 计算合适的单元格大小
        cell_size = min(w // self.cols, h // self.rows)
        return max(cell_size, 10)  # 最小10像素

    def get_offset(self):
        """获取迷宫的偏移量，使迷宫居中显示"""
        cell_size = self.get_cell_size()
        total_w = cell_size * self.cols
        total_h = cell_size * self.rows
        offset_x = (self.width() - total_w) // 2
        offset_y = (self.height() - total_h) // 2
        return max(0, offset_x), max(0, offset_y)

    def set_maze(self, maze, rows, cols):
        self.maze = maze
        self.rows = rows
        self.cols = cols
        self.start = None
        self.end = None
        self.path = []
        self.search_nodes = []
        self.update()

    def clear_path(self):
        self.path = []
        self.search_nodes = []
        self.update()

    def resizeEvent(self, event):
        """窗口大小改变时重绘"""
        self.update()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cell_size = self.get_cell_size()
        offset_x, offset_y = self.get_offset()

        # 绘制背景
        painter.fillRect(self.rect(), COLOR_CANVAS_BG)

        # 绘制迷宫
        for i in range(self.rows):
            for j in range(self.cols):
                color = COLOR_WALL if self.maze[i][j] == 1 else COLOR_PATH
                self.draw_cell(painter, i, j, color, cell_size, offset_x, offset_y)

        # 绘制探索节点
        for (i, j) in self.search_nodes:
            if (i, j) != self.start and (i, j) != self.end:
                self.draw_cell(painter, i, j, COLOR_SEARCH, cell_size, offset_x, offset_y)

        # 绘制最终路径
        for (i, j) in self.path:
            if (i, j) != self.start and (i, j) != self.end:
                self.draw_cell(painter, i, j, COLOR_FINAL, cell_size, offset_x, offset_y)

        # 绘制起点和终点
        if self.start:
            self.draw_cell(painter, self.start[0], self.start[1], COLOR_START, cell_size, offset_x, offset_y)
        if self.end:
            self.draw_cell(painter, self.end[0], self.end[1], COLOR_END, cell_size, offset_x, offset_y)

        # 绘制网格线
        pen = QPen(QColor(200, 200, 200))
        pen.setWidth(1)
        painter.setPen(pen)
        for i in range(self.rows + 1):
            y = offset_y + i * cell_size
            painter.drawLine(offset_x, y, offset_x + self.cols * cell_size, y)
        for j in range(self.cols + 1):
            x = offset_x + j * cell_size
            painter.drawLine(x, offset_y, x, offset_y + self.rows * cell_size)

    def draw_cell(self, painter, row, col, color, cell_size, offset_x, offset_y):
        x = offset_x + col * cell_size
        y = offset_y + row * cell_size
        painter.fillRect(x + 1, y + 1, cell_size - 2, cell_size - 2, color)

    def get_cell_at_pos(self, x, y):
        """根据鼠标位置获取对应单元格"""
        cell_size = self.get_cell_size()
        offset_x, offset_y = self.get_offset()
        col = (x - offset_x) // cell_size
        row = (y - offset_y) // cell_size
        return row, col

    def mousePressEvent(self, event):
        row, col = self.get_cell_at_pos(event.x(), event.y())
        if 0 <= row < self.rows and 0 <= col < self.cols:
            if event.button() == Qt.LeftButton:
                if self.maze[row][col] == 1:
                    QMessageBox.warning(self, "警告", "不能将起点设置在墙壁上！")
                else:
                    self.start = (row, col)
                    self.update()
            elif event.button() == Qt.RightButton:
                if self.maze[row][col] == 1:
                    QMessageBox.warning(self, "警告", "不能将终点设置在墙壁上！")
                else:
                    self.end = (row, col)
                    self.update()
            elif event.button() == Qt.MiddleButton:
                self.drawing_wall = True
                self.toggle_wall(row, col)

    def mouseMoveEvent(self, event):
        if self.drawing_wall:
            row, col = self.get_cell_at_pos(event.x(), event.y())
            if 0 <= row < self.rows and 0 <= col < self.cols:
                self.toggle_wall(row, col)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.drawing_wall = False

    def toggle_wall(self, row, col):
        if (row, col) == self.start or (row, col) == self.end:
            return
        self.maze[row][col] = 0 if self.maze[row][col] == 1 else 1
        self.update()


class MazeSolverWidget(QWidget):
    """迷宫寻路系统主部件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = DEFAULT_ROWS
        self.cols = DEFAULT_COLS
        self.maze = MazeGenerator.create_empty(self.rows, self.cols)
        self.path = []
        self.search_nodes = []
        self.is_running = False
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animation_step)
        self.animation_index = 0
        self.search_result = None

        self.setup_ui()

    def setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)

        # 控制面板
        control_layout = QHBoxLayout()

        # 迷宫尺寸
        control_layout.addWidget(QLabel("迷宫尺寸:"))
        self.row_spin = QSpinBox()
        self.row_spin.setRange(5, 30)
        self.row_spin.setValue(DEFAULT_ROWS)
        control_layout.addWidget(self.row_spin)
        control_layout.addWidget(QLabel("×"))
        self.col_spin = QSpinBox()
        self.col_spin.setRange(5, 30)
        self.col_spin.setValue(DEFAULT_COLS)
        control_layout.addWidget(self.col_spin)

        # 功能按钮
        self.empty_btn = QPushButton("空白迷宫")
        self.empty_btn.clicked.connect(self.reset_empty_maze)
        control_layout.addWidget(self.empty_btn)

        self.random_btn = QPushButton("随机迷宫")
        self.random_btn.clicked.connect(self.reset_random_maze)
        control_layout.addWidget(self.random_btn)

        self.dfs_btn = QPushButton("DFS迷宫")
        self.dfs_btn.clicked.connect(self.reset_dfs_maze)
        control_layout.addWidget(self.dfs_btn)

        self.clear_path_btn = QPushButton("清空路径")
        self.clear_path_btn.clicked.connect(self.clear_path)
        control_layout.addWidget(self.clear_path_btn)

        self.reset_btn = QPushButton("重置迷宫")
        self.reset_btn.clicked.connect(self.reset_all)
        control_layout.addWidget(self.reset_btn)

        layout.addLayout(control_layout)

        # 第二行控制
        mode_layout = QHBoxLayout()

        mode_layout.addWidget(QLabel("寻路模式:"))
        self.mode_group = QButtonGroup()
        self.four_dir_radio = QRadioButton("四方向")
        self.four_dir_radio.setChecked(True)
        self.eight_dir_radio = QRadioButton("八方向")
        self.mode_group.addButton(self.four_dir_radio, 4)
        self.mode_group.addButton(self.eight_dir_radio, 8)
        mode_layout.addWidget(self.four_dir_radio)
        mode_layout.addWidget(self.eight_dir_radio)

        mode_layout.addWidget(QLabel("动画速度:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(10, 500)
        self.speed_slider.setValue(200)
        mode_layout.addWidget(self.speed_slider)

        self.start_btn = QPushButton("开始寻路")
        self.start_btn.clicked.connect(self.start_find_path)
        mode_layout.addWidget(self.start_btn)

        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # 信息标签
        self.info_label = QLabel("操作说明：左键设起点 | 右键设终点 | 中键拖拽画墙")
        layout.addWidget(self.info_label)

        # 迷宫画布
        self.canvas = MazeCanvas()
        layout.addWidget(self.canvas, 1)

    def reset_empty_maze(self):
        self.update_maze_size()
        self.maze = MazeGenerator.create_empty(self.rows, self.cols)
        self.canvas.set_maze(self.maze, self.rows, self.cols)
        self.info_label.setText("已创建空白迷宫")

    def reset_random_maze(self):
        self.update_maze_size()
        self.maze = MazeGenerator.create_random(self.rows, self.cols)
        self.canvas.set_maze(self.maze, self.rows, self.cols)
        self.info_label.setText("已生成随机迷宫")

    def reset_dfs_maze(self):
        self.update_maze_size()
        self.maze = MazeGenerator.create_dfs_maze(self.rows, self.cols)
        self.canvas.set_maze(self.maze, self.rows, self.cols)
        self.info_label.setText("已生成DFS单连通迷宫")

    def clear_path(self):
        self.canvas.clear_path()
        self.info_label.setText("已清空路径")

    def reset_all(self):
        self.reset_random_maze()

    def update_maze_size(self):
        self.rows = self.row_spin.value()
        self.cols = self.col_spin.value()

    def start_find_path(self):
        if self.canvas.start is None or self.canvas.end is None:
            QMessageBox.warning(self, "警告", "请先设置起点和终点！")
            return
        if self.is_running:
            return

        self.is_running = True
        self.start_btn.setEnabled(False)
        self.canvas.clear_path()

        mode = self.mode_group.checkedId()
        astar = AStar(self.maze, self.canvas.start, self.canvas.end, mode)
        self.search_result = astar.search()
        self.canvas.search_nodes = astar.search_path

        if self.search_result[0] is None:
            QMessageBox.critical(self, "错误", "无可行路径！")
            self.info_label.setText(f"无可行路径 | 探索节点：{self.search_result[1]} | 耗时：{self.search_result[2]}s")
            self.is_running = False
            self.start_btn.setEnabled(True)
            return

        self.canvas.path = []
        self.animation_index = 0
        self.canvas.update()
        self.info_label.setText(f"正在寻路... | 耗时：{self.search_result[2]}s")
        
        delay = int(500 / self.speed_slider.value() * 10)
        self.animation_timer.start(delay)

    def animation_step(self):
        if self.animation_index < len(self.canvas.search_nodes):
            self.animation_index += 1
            self.canvas.update()
        else:
            self.animation_timer.stop()
            self.canvas.path = self.search_result[0]
            self.canvas.update()
            self.info_label.setText(f"寻路完成 | 路径长度：{len(self.canvas.path)} | 探索节点：{len(self.canvas.search_nodes)}")
            self.is_running = False
            self.start_btn.setEnabled(True)
