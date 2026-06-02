# 智能工具整合系统

将三个独立的Python工具整合到一个统一的PyQt5图形界面中。

---

## ⚠️ 重要说明

**关键问题：PyTorch 与 PyQt5 导入顺序**
在 Windows 系统下，必须**先导入 torch，再导入 PyQt5**，否则会导致：
```
OSError: [WinError 1114] 动态链接库(DLL)初始化例程失败
```

本项目已经在 [`main.py`](file:///d:/github/integrated_system/main.py#L4-L12) 中正确配置了导入顺序！

---

## 包含的子系统

1. **迷宫寻路系统** - 基于A*算法的智能迷宫寻路工具
2. **手写数字识别系统** - 基于PyTorch的MNIST手写数字识别
3. **姓名新闻搜索系统** - 基于百度新闻的姓名相关新闻搜索与分析

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

## 项目结构

```
integrated_system/
├── main.py                    # 主入口文件
├── requirements.txt           # 依赖列表
├── README.md                  # 项目说明
├── maze_solver/              # 迷宫寻路子系统
│   ├── __init__.py
│   ├── maze_pyqt.py
│   └── 迷宫.py               # 原版Tkinter版本（保留）
├── digit_recognition/        # 手写数字识别子系统
│   ├── __init__.py
│   ├── gui.py
│   ├── model.py
│   ├── train.py
│   ├── recognizer.py
│   ├── evaluate.py
│   ├── data/                  # MNIST数据集
│   └── models/                # 训练好的模型
└── news_search/              # 姓名新闻搜索子系统
    ├── __init__.py
    ├── news_search_pyqt.py    # PyQt5版本
    ├── name_news_search.py    # 原版Tkinter版本（保留）
    ├── config.py
    └── logger.py
```

## 使用说明

启动程序后，通过顶部的主标签页切换不同的子系统。每个子系统保持其原有功能不变。

### 🚀 快速开始

1. **安装依赖**
   ```bash
   cd d:\github\integrated_system
   pip install -r requirements.txt
   ```

2. **运行程序**
   ```bash
   python main.py
   ```

3. **切换系统**
   - 迷宫寻路系统
   - 手写数字识别
   - 姓名新闻搜索

---

## 📍 迷宫寻路系统

### 功能特点

- **A*智能寻路**：使用启发式搜索算法，找到最短路径
- **多种迷宫生成**：空白迷宫、随机迷宫、DFS经典迷宫
- **双模式支持**：四方向（上下左右）和八方向（含对角线）
- **实时可视化**：动画展示算法探索过程和最终路径

### 操作指南

1. **生成迷宫**
   - 点击"空白迷宫"：创建空的网格
   - 点击"随机迷宫"：生成随机墙壁
   - 点击"DFS迷宫"：生成经典迷宫（包含死胡同）

2. **设置起点和终点**
   - **左键点击**：设置起点（绿色方块）
   - **右键点击**：设置终点（红色方块）

3. **编辑墙壁**
   - **中键拖拽**：绘制或擦除墙壁
   - 注意：不能将起点/终点设置在墙壁上

4. **寻路设置**
   - 选择寻路模式：四方向 或 八方向
   - 调整动画速度滑块
   - 点击"开始寻路"开始演示

5. **功能按钮**
   - "清空路径"：清除当前路径但保留迷宫
   - "重置迷宫"：重新生成随机迷宫

### 颜色标识

| 颜色 | 含义 |
|------|------|
| 黑色 | 墙壁 |
| 白色 | 通路 |
| 绿色 | 起点 |
| 红色 | 终点 |
| 黄色 | 算法探索节点 |
| 蓝色 | 最终最短路径 |

---

## 🔢 手写数字识别系统

### 功能特点

- **双模型支持**：CNN（卷积神经网络）和MLP（多层感知机）
- **图形界面**：直观的图片选择和结果展示
- **批量识别**：支持一次识别多张图片
- **模型训练**：支持自定义参数训练新模型
- **统计分析**：显示识别置信度分布图

### 操作指南

#### 数字识别

1. **加载模型**
   - 程序启动时自动加载最佳模型
   - 可点击"加载模型"手动选择 `.pth` 文件

2. **单张识别**
   - 点击"选择图片"按钮
   - 选择要识别的图片（支持PNG、JPG、BMP格式）
   - 查看识别结果、置信度和推理时间

3. **批量识别**
   - 点击"选择多张图片"按钮
   - 选择多张图片文件
   - 查看批量识别结果清单

#### 模型训练

1. **参数设置**
   - 模型类型：CNN 或 MLP
   - 训练轮数：1-50
   - 批次大小：16-256
   - 学习率：0.0001-0.1

2. **开始训练**
   - 点击"开始训练"
   - 查看训练进度和准确率
   - 训练完成后自动保存模型

3. **输出文件**
   - 模型文件：`./models/mnist_model.pth`
   - 最佳模型：`./models/mnist_model_best.pth`
   - 训练曲线：`./training_history.png`

### 注意事项

- 图片会自动转换为28×28灰度图
- 首次使用会自动下载MNIST数据集
- 训练需要一定时间，GPU可加速训练

### 模型与数据集

> **注意**：由于模型文件较大，本仓库不包含预训练模型和数据集文件。

**首次使用数字识别功能，需要：**

1. **下载 MNIST 数据集**（自动）
   - 首次运行训练或识别时会自动下载
   - 数据将保存在 `digit_recognition/data/MNIST/` 目录

2. **训练模型**
   - 运行程序后，在"手写数字识别"标签页点击"开始训练"
   - 或使用命令行：
     ```bash
     cd digit_recognition
     python train.py
     ```
   - 训练完成后模型将保存在 `digit_recognition/models/` 目录

---

## 📰 姓名新闻搜索系统

### 功能特点

- **百度新闻搜索**：搜索指定姓名的相关新闻
- **多页翻页**：支持搜索多页结果（1-10页）
- **分页展示**：每页显示22条新闻
- **统计分析**：可视化展示来源分布、时间趋势等
- **筛选排序**：按来源筛选，多种排序方式
- **历史记录**：保存和回顾历史搜索
- **导出功能**：支持导出CSV文件

### 操作指南

#### 基本搜索

1. 输入要搜索的姓名
2. 调整搜索页数（默认5页）
3. 选择搜索范围（全部新闻/政府网站/教育网站等）
4. 点击"搜索"或按回车键

#### 搜索结果

1. **查看详情**
   - 点击新闻条目，右侧显示完整信息

2. **打开原文**
   - 双击表格行在浏览器中打开链接
   - 或选中后点击"打开原文"按钮

3. **分页浏览**
   - 使用"上一页"/"下一页"按钮翻页

4. **筛选和排序**
   - 来源筛选：下拉选择特定新闻来源
   - 排序方式：按姓名出现次数、时间、来源等排序

5. **导出数据**
   - 点击"导出CSV"保存搜索结果

#### 统计分析

- 查看新闻来源分布柱状图
- 查看姓名出现次数分布
- 查看新闻发布时间趋势
- 查看摘要长度与姓名出现次数关系

#### 搜索历史

- 自动记录每次搜索
- 双击历史记录快速重新搜索
- 点击"清空历史"清除所有记录

### 注意事项

- 搜索间隔1秒，防止请求过于频繁
- 需要稳定的网络连接
- 百度安全验证可能导致搜索失败
- 请遵守百度服务条款，合理使用

---

## ⚠️ 常见问题及解决方法

### Q1: 启动时提示缺少模块？

**错误信息：**
```
ModuleNotFoundError: No module named 'xxx'
```

**解决方法：**
```bash
pip install --break-system-packages -r requirements.txt
```

> 注意：由于 Python 环境管理限制，需要添加 `--break-system-packages` 参数。

---

### Q2: PyQt5 未安装？

**错误信息：**
```
ModuleNotFoundError: No module named 'PyQt5'
```

**解决方法：**
```bash
pip install --break-system-packages PyQt5 matplotlib numpy Pillow
```

---

### Q3: PyTorch DLL 加载失败？

**错误信息：**
```
OSError: [WinError 1114] 动态链接库(DLL)初始化例程失败
Error loading "torch\lib\c10.dll"
```

**关键原因：** **导入顺序错误！！！**
在代码中如果先导入 PyQt5，再导入 torch，就会导致这个错误！

**解决方法：**

#### 方法1：确保正确的导入顺序（已在 main.py 中修复）
在 [`main.py`](file:///d:/github/integrated_system/main.py#L4-L12) 中，**必须先导入 torch，再导入 PyQt5**：
```python
# 先尝试导入torch！！！这很重要！
try:
    import torch
    print("OK: PyTorch imported successfully! Version:", torch.__version__)
except Exception as e:
    print("Warning: PyTorch import failed:", str(e))

# 然后再导入PyQt5
```

#### 方法2：安装 CPU 版本的 PyTorch
```bash
pip install --break-system-packages torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

#### 方法3：安装 Visual C++ Redistributable
- 下载地址：https://aka.ms/vs/17/release/vc_redist.x64.exe
- 安装后重启电脑

---

### Q4: 模块导入路径错误？

**错误信息：**
```
ModuleNotFoundError: No module named 'train'
```

**原因：** 模块导入路径配置问题

**解决方法：**
项目已自动修复此问题，确保使用正确的相对导入路径。

---

### Q5: 新闻搜索失败？

**可能原因：**
- 网络连接不稳定
- 百度安全验证拦截
- 请求过于频繁

**解决方法：**
- 检查网络连接
- 等待几秒后重试
- 减少搜索页数
- 遵守百度服务条款，合理使用

---

### Q6: 程序无响应？

**原因：** 新闻搜索和模型训练在后台线程进行

**解决方法：**
- 请耐心等待，不要强制关闭
- 观察状态栏提示信息

---

### Q7: uv 环境限制？

**错误信息：**
```
error: externally-managed-environment
```

**原因：** Python 环境由 uv 管理，不允许直接修改

**解决方法：**
所有 pip install 命令都需要添加 `--break-system-packages` 参数：
```bash
pip install --break-system-packages <package>
```

---

## 🛠️ 完整安装步骤

如果遇到多个问题，按以下顺序操作：

1. **安装基础依赖**
   ```bash
   pip install --break-system-packages PyQt5 matplotlib numpy Pillow requests beautifulsoup4 pandas fake-useragent lxml
   ```

2. **安装 PyTorch（可选，用于手写数字识别）**
   ```bash
   pip install --break-system-packages torch torchvision --index-url https://download.pytorch.org/whl/cpu
   ```

3. **运行程序**
   ```bash
   python main.py
   ```

4. **如果 PyTorch 仍有问题**
   - 安装 Visual C++ Redistributable
   - 或忽略手写数字识别功能，使用其他两个系统

---

## 📄 许可证

本项目采用MIT许可证。

## 📅 更新日志

### v1.1.0 (2026-06-01)
- **关键修复**：解决 PyTorch 与 PyQt5 导入顺序问题
  - 必须先导入 torch，再导入 PyQt5，避免 DLL 初始化失败
- 优化姓名新闻搜索默认配置
  - 默认搜索页数：5页
  - 每页显示数量：22条

### v1.0.0 (2026-06-01)
- 初始版本
- 整合迷宫寻路系统
- 整合手写数字识别系统
- 整合姓名新闻搜索系统
- 修复窗口自适应问题
- 修复模块导入路径问题
