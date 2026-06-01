import tkinter as tk
from tkinter import ttk, messagebox
import heapq
import random
import time

# -------------------------- 全局常量定义 --------------------------
# 界面颜色配置
COLOR_WALL = "#000000"        # 墙壁：黑色
COLOR_PATH = "#FFFFFF"        # 通路：白色
COLOR_START = "#00FF00"       # 起点：绿色
COLOR_END = "#FF0000"         # 终点：红色
COLOR_SEARCH = "#FFFF00"      # 算法探索节点：黄色
COLOR_FINAL = "#0000FF"       # 最终路径：蓝色
COLOR_CANVAS_BG = "#E0E0E0"   # 画布背景色

# 迷宫默认配置
CELL_SIZE = 30    # 每个迷宫单元格的像素大小
DEFAULT_ROWS = 15 # 默认行数
DEFAULT_COLS = 15 # 默认列数
WALL_RATE = 0.3   # 随机迷宫墙壁生成概率

# -------------------------- A*算法节点类 --------------------------
class Node:
    """A*算法的节点对象，存储坐标、代价、父节点"""
    def __init__(self, x, y, parent=None):
        self.x = x          # 行坐标
        self.y = y          # 列坐标
        self.parent = parent# 父节点（用于回溯路径）
        self.g = 0          # 从起点到当前节点的实际代价
        self.h = 0          # 启发函数代价（到终点的预估代价）
        self.f = 0          # 总代价 f = g + h

    # 重载小于号，用于优先队列排序（按f值升序）
    def __lt__(self, other):
        return self.f < other.f

# -------------------------- A*算法核心实现 --------------------------
class AStar:
    def __init__(self, maze, start, end, mode=4):
        self.maze = maze            # 迷宫矩阵（0=通路，1=墙壁）
        self.start = start          # 起点坐标 (x,y)
        self.end = end              # 终点坐标 (x,y)
        self.mode = mode            # 寻路模式：4=四方向，8=八方向
        self.rows = len(maze)
        self.cols = len(maze[0])
        self.open_list = []         # 开放列表（待探索节点，优先队列）
        self.close_list = set()     # 关闭列表（已探索节点，坐标集合）
        self.search_path = []       # 算法探索的节点序列（用于可视化）

    def heuristic(self, node):
        """启发函数：曼哈顿距离（四方向最优），支持八方向扩展"""
        if self.mode == 4:
            return abs(node.x - self.end[0]) + abs(node.y - self.end[1])
        else:
            # 切比雪夫距离（八方向最优）
            return max(abs(node.x - self.end[0]), abs(node.y - self.end[1]))

    def get_neighbors(self, node):
        """获取当前节点的相邻合法节点"""
        neighbors = []
        # 四方向：上下左右
        directions = [(-1,0), (1,0), (0,-1), (0,1)]
        # 八方向：新增对角线
        if self.mode == 8:
            directions += [(-1,-1), (-1,1), (1,-1), (1,1)]

        for dx, dy in directions:
            x = node.x + dx
            y = node.y + dy
            # 边界检查 + 墙壁检查
            if 0 <= x < self.rows and 0 <= y < self.cols and self.maze[x][y] == 0:
                neighbors.append((x, y))
        return neighbors

    def search(self):
        """A*算法主逻辑：返回最终路径、探索节点数、执行时间"""
        start_time = time.time()
        # 初始化起点
        start_node = Node(self.start[0], self.start[1])
        end_node = Node(self.end[0], self.end[1])
        heapq.heappush(self.open_list, start_node)

        while self.open_list:
            # 取出f值最小的节点
            current_node = heapq.heappop(self.open_list)
            self.close_list.add((current_node.x, current_node.y))
            self.search_path.append((current_node.x, current_node.y))

            # 找到终点，回溯路径
            if current_node.x == end_node.x and current_node.y == end_node.y:
                path = []
                while current_node:
                    path.append((current_node.x, current_node.y))
                    current_node = current_node.parent
                # 反转路径（起点→终点）
                cost_time = round(time.time() - start_time, 3)
                return path[::-1], len(self.search_path), cost_time

            # 遍历相邻节点
            for x, y in self.get_neighbors(current_node):
                if (x, y) in self.close_list:
                    continue
                neighbor = Node(x, y, current_node)
                # 计算代价
                neighbor.g = current_node.g + 1
                neighbor.h = self.heuristic(neighbor)
                neighbor.f = neighbor.g + neighbor.h

                # 检查开放列表中是否存在更优节点
                for node in self.open_list:
                    if node == neighbor and node.g < neighbor.g:
                        break
                else:
                    heapq.heappush(self.open_list, neighbor)

        # 无可行路径
        cost_time = round(time.time() - start_time, 3)
        return None, len(self.search_path), cost_time

# -------------------------- 迷宫生成器（修复版） --------------------------
class MazeGenerator:
    @staticmethod
    def create_empty(rows, cols):
        """创建空白迷宫（全通路）"""
        return [[0 for _ in range(cols)] for _ in range(rows)]

    @staticmethod
    def create_random(rows, cols, wall_rate=WALL_RATE):
        """随机生成迷宫（边缘也可生成墙壁，解决外围全通路问题）"""
        maze = [[0 for _ in range(cols)] for _ in range(rows)]
        # 边缘墙壁概率降低，避免完全封死
        for i in range(rows):
            for j in range(cols):
                if (i == 0 or i == rows-1 or j == 0 or j == cols-1):
                    if random.random() < wall_rate * 0.3:
                        maze[i][j] = 1
                else:
                    if random.random() < wall_rate:
                        maze[i][j] = 1
        return maze

    @staticmethod
    def create_dfs_maze(rows, cols):
        """使用深度优先搜索(DFS)生成单连通迷宫（有死胡同，挑战性强）"""
        # 初始化迷宫，全为墙壁（1）
        maze = [[1 for _ in range(cols)] for _ in range(rows)]
        # 从(1,1)开始生成，避开边缘
        stack = [(1, 1)]
        maze[1][1] = 0
        directions = [(-2,0), (2,0), (0,-2), (0,2)]

        while stack:
            x, y = stack[-1]
            random.shuffle(directions)
            found = False
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                if 0 < nx < rows-1 and 0 < ny < cols-1 and maze[nx][ny] == 1:
                    # 打通中间墙壁
                    maze[x + dx//2][y + dy//2] = 0
                    maze[nx][ny] = 0
                    stack.append((nx, ny))
                    found = True
                    break
            if not found:
                stack.pop()
        # 保留边缘的4个通路，避免完全封死
        maze[0][cols//2] = 0
        maze[rows-1][cols//2] = 0
        maze[rows//2][0] = 0
        maze[rows//2][cols-1] = 0
        return maze

# -------------------------- 主GUI界面（添加DFS迷宫按钮） --------------------------
class MazeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("A*算法迷宫智能寻路系统")
        self.resizable(False, False)
        self.configure(bg="#F5F5F5")

        # 迷宫核心变量
        self.rows = DEFAULT_ROWS
        self.cols = DEFAULT_COLS
        self.maze = MazeGenerator.create_empty(self.rows, self.cols)
        self.start = None   # 起点 (x,y)
        self.end = None    # 终点 (x,y)
        self.path = []     # 最终路径
        self.search_nodes = [] # 算法探索节点
        self.is_running = False # 算法运行标志

        # 初始化界面
        self.init_widgets()
        self.draw_maze()

    def init_widgets(self):
        """初始化GUI组件"""
        # 1. 控制面板框架
        control_frame = ttk.Frame(self, padding=10)
        control_frame.grid(row=0, column=0, sticky="nsew")

        # 迷宫尺寸设置
        ttk.Label(control_frame, text="迷宫尺寸：").grid(row=0, column=0, padx=5)
        self.row_entry = ttk.Entry(control_frame, width=5)
        self.row_entry.grid(row=0, column=1, padx=2)
        self.row_entry.insert(0, str(self.rows))
        ttk.Label(control_frame, text="×").grid(row=0, column=2, padx=2)
        self.col_entry = ttk.Entry(control_frame, width=5)
        self.col_entry.grid(row=0, column=3, padx=2)
        self.col_entry.insert(0, str(self.cols))

        # 功能按钮（新增DFS迷宫按钮）
        ttk.Button(control_frame, text="空白迷宫", command=self.reset_empty_maze).grid(row=0, column=4, padx=5)
        ttk.Button(control_frame, text="随机迷宫", command=self.reset_random_maze).grid(row=0, column=5, padx=5)
        ttk.Button(control_frame, text="DFS迷宫", command=self.reset_dfs_maze).grid(row=0, column=6, padx=5)
        ttk.Button(control_frame, text="清空路径", command=self.clear_path).grid(row=0, column=7, padx=5)
        ttk.Button(control_frame, text="重置迷宫", command=self.reset_all).grid(row=0, column=8, padx=5)

        # 寻路模式 + 速度调节
        ttk.Label(control_frame, text="寻路模式：").grid(row=1, column=0, padx=5, pady=10)
        self.path_mode = tk.IntVar(value=4)
        ttk.Radiobutton(control_frame, text="四方向", variable=self.path_mode, value=4).grid(row=1, column=1)
        ttk.Radiobutton(control_frame, text="八方向", variable=self.path_mode, value=8).grid(row=1, column=2)

        ttk.Label(control_frame, text="动画速度：").grid(row=1, column=3, padx=5)
        self.speed_scale = ttk.Scale(control_frame, from_=10, to=500, value=200, orient=tk.HORIZONTAL)
        self.speed_scale.grid(row=1, column=4, columnspan=2, sticky="we")

        # 开始寻路按钮
        self.start_btn = ttk.Button(control_frame, text="开始寻路", command=self.start_find_path)
        self.start_btn.grid(row=1, column=6, columnspan=3, padx=10, sticky="we")

        # 2. 信息显示栏
        info_frame = ttk.Frame(self, padding=5)
        info_frame.grid(row=1, column=0, sticky="nsew")
        self.info_label = ttk.Label(info_frame, text="操作说明：左键设起点 | 右键设终点 | 拖拽绘制/擦除墙壁")
        self.info_label.grid(row=0, column=0)

        # 3. 迷宫画布
        self.canvas = tk.Canvas(
            self,
            width=self.cols*CELL_SIZE,
            height=self.rows*CELL_SIZE,
            bg=COLOR_CANVAS_BG,
            highlightthickness=1
        )
        self.canvas.grid(row=2, column=0, padx=10, pady=10)

        # 绑定鼠标事件
        self.canvas.bind("<Button-1>", self.set_start)  # 左键：设置起点
        self.canvas.bind("<Button-3>", self.set_end)    # 右键：设置终点
        self.canvas.bind("<B1-Motion>", self.draw_wall) # 拖拽：绘制/擦除墙壁

    def draw_cell(self, x, y, color):
        """绘制单个迷宫单元格"""
        x1 = y * CELL_SIZE
        y1 = x * CELL_SIZE
        x2 = x1 + CELL_SIZE
        y2 = y1 + CELL_SIZE
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#CCCCCC")

    def draw_maze(self):
        """绘制整个迷宫"""
        self.canvas.delete("all")
        for i in range(self.rows):
            for j in range(self.cols):
                color = COLOR_WALL if self.maze[i][j] == 1 else COLOR_PATH
                self.draw_cell(i, j, color)
        # 绘制起点/终点
        if self.start:
            self.draw_cell(self.start[0], self.start[1], COLOR_START)
        if self.end:
            self.draw_cell(self.end[0], self.end[1], COLOR_END)

    def draw_animation(self, index=0):
        """动画展示算法探索过程"""
        if index >= len(self.search_nodes):
            self.draw_final_path()
            return
        x, y = self.search_nodes[index]
        if (x, y) != self.start and (x, y) != self.end:
            self.draw_cell(x, y, COLOR_SEARCH)
        # 延时递归绘制
        delay = int(500 / self.speed_scale.get() * 10)
        self.after(delay, self.draw_animation, index + 1)

    def draw_final_path(self):
        """绘制最终最短路径"""
        for x, y in self.path:
            if (x, y) != self.start and (x, y) != self.end:
                self.draw_cell(x, y, COLOR_FINAL)
        self.info_label.config(text="寻路完成 | 路径长度：{} | 探索节点：{}".format(len(self.path), len(self.search_nodes)))
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL)

    # -------------------------- 功能函数（新增DFS迷宫重置） --------------------------
    def reset_empty_maze(self):
        """重置空白迷宫"""
        self._update_maze_size()
        self.maze = MazeGenerator.create_empty(self.rows, self.cols)
        self.start = None
        self.end = None
        self.path = []
        self.draw_maze()
        self.info_label.config(text="已创建空白迷宫")

    def reset_random_maze(self):
        """重置随机迷宫（修复版，边缘可生成墙壁）"""
        self._update_maze_size()
        self.maze = MazeGenerator.create_random(self.rows, self.cols)
        self.start = None
        self.end = None
        self.path = []
        self.draw_maze()
        self.info_label.config(text="已生成修复版随机迷宫")

    def reset_dfs_maze(self):
        """重置DFS生成的迷宫"""
        self._update_maze_size()
        self.maze = MazeGenerator.create_dfs_maze(self.rows, self.cols)
        self.start = None
        self.end = None
        self.path = []
        self.draw_maze()
        self.info_label.config(text="已生成DFS单连通迷宫（含死胡同）")

    def clear_path(self):
        """清空路径，保留迷宫和起点终点"""
        self.path = []
        self.search_nodes = []
        self.draw_maze()
        self.info_label.config(text="已清空路径")

    def reset_all(self):
        """重置所有设置"""
        self.start = None
        self.end = None
        self.path = []
        self.search_nodes = []
        self.reset_random_maze()

    def set_start(self, event):
        """设置起点"""
        if self.is_running: return
        x = event.y // CELL_SIZE
        y = event.x // CELL_SIZE
        if self.maze[x][y] == 1:
            messagebox.showwarning("警告", "不能将起点设置在墙壁上！")
            return
        self.start = (x, y)
        self.draw_maze()

    def set_end(self, event):
        """设置终点"""
        if self.is_running: return
        x = event.y // CELL_SIZE
        y = event.x // CELL_SIZE
        if self.maze[x][y] == 1:
            messagebox.showwarning("警告", "不能将终点设置在墙壁上！")
            return
        self.end = (x, y)
        self.draw_maze()

    def draw_wall(self, event):
        """拖拽绘制/擦除墙壁"""
        if self.is_running: return
        x = event.y // CELL_SIZE
        y = event.x // CELL_SIZE
        if 0 <= x < self.rows and 0 <= y < self.cols:
            # 禁止覆盖起点/终点
            if (x, y) == self.start or (x, y) == self.end:
                return
            self.maze[x][y] = 0 if self.maze[x][y] == 1 else 1
            self.draw_cell(x, y, COLOR_WALL if self.maze[x][y] == 1 else COLOR_PATH)

    def start_find_path(self):
        """开始寻路"""
        # 前置检查
        if not self.start or not self.end:
            messagebox.showwarning("警告", "请先设置起点和终点！")
            return
        if self.is_running:
            return
        # 禁用按钮，防止重复操作
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.clear_path()

        # 执行A*算法
        astar = AStar(self.maze, self.start, self.end, self.path_mode.get())
        self.path, search_num, cost_time = astar.search()
        self.search_nodes = astar.search_path

        # 结果处理
        if not self.path:
            messagebox.showerror("错误", "无可行路径！")
            self.info_label.config(text="无可行路径 | 探索节点：{} | 耗时：{}s".format(search_num, cost_time))
            self.is_running = False
            self.start_btn.config(state=tk.NORMAL)
            return

        # 启动动画
        self.info_label.config(text="正在寻路... | 耗时：{}s".format(cost_time))
        self.draw_animation()

    def _update_maze_size(self):
        """更新迷宫尺寸"""
        try:
            rows = int(self.row_entry.get())
            cols = int(self.col_entry.get())
            if 5 <= rows <= 30 and 5 <= cols <= 30:
                self.rows = rows
                self.cols = cols
                self.canvas.config(width=self.cols*CELL_SIZE, height=self.rows*CELL_SIZE)
            else:
                messagebox.showwarning("警告", "尺寸必须在5~30之间！")
        except ValueError:
            messagebox.showwarning("警告", "请输入有效数字！")

# -------------------------- 程序入口 --------------------------
if __name__ == "__main__":
    app = MazeApp()
    app.mainloop()