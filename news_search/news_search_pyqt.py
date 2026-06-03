import sys
import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib
matplotlib.use('Qt5Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from fake_useragent import UserAgent
import re
import json
import time
from datetime import datetime, timedelta
import webbrowser

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QSpinBox, QComboBox, QTabWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
                             QTextEdit, QMessageBox, QFileDialog, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

# 导入本地模块（支持相对导入和直接运行）
try:
    from .config import Config
    from .logger import logger
except ImportError:
    from config import Config
    from logger import logger


class NewsCrawler:
    """百度新闻爬虫类"""

    def __init__(self):
        self.ua = UserAgent()
        self.base_url = Config.BAIDU_SEARCH_URL
        self.session = requests.Session()

    def search_news(self, name, page=1, site_filter="", timeout=Config.REQUEST_TIMEOUT):
        """搜索指定姓名的新闻"""
        query = f"{name} 新闻".strip()

        headers = {
            "User-Agent": self.ua.random,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://www.baidu.com/",
        }

        params = {
            "wd": query,
            "tn": "news",
            "pn": (page - 1) * 10,
            "rn": 10,
            "ie": "utf-8",
            "cl": 2
        }
        if site_filter:
            params["site"] = site_filter

        try:
            response = self.session.get(self.base_url, headers=headers, params=params, timeout=timeout)
            response.raise_for_status()
            response.encoding = "utf-8"
            if self.is_security_page(response.text):
                logger.warning("触发百度安全验证，尝试重新请求")
                self.session.cookies.clear()
                response = self.session.get(self.base_url, headers=headers, params=params, timeout=timeout)
                response.raise_for_status()
                response.encoding = "utf-8"
            return self.parse_news(response.text, name)
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求失败: {str(e)}")
            raise Exception(f"网络请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"搜索异常: {str(e)}")
            raise Exception(f"搜索异常: {str(e)}")

    def is_security_page(self, html):
        """检查是否被百度安全验证拦截"""
        return "百度安全验证" in html or "安全验证" in html or "请输入验证码" in html

    def parse_news(self, html, name):
        """解析新闻页面"""
        soup = BeautifulSoup(html, "html.parser")
        news_list = []

        news_items = soup.select("div.result-op.c-container.xpath-log.new-pmd, div.result-op.c-container.xpath-log, div.result, div.c-container, div.result-op")
        if not news_items:
            news_items = soup.find_all("div", class_="result")

        for item in news_items:
            try:
                title_elem = item.find("h3")
                if not title_elem:
                    title_elem = item.find("a")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link_elem = title_elem.find("a") if title_elem.name != "a" else title_elem
                link = link_elem["href"] if link_elem and link_elem.has_attr("href") else ""

                source, time_str, summary = self.extract_news_meta(item)

                name_count = title.count(name) + summary.count(name)

                if name_count > 0:
                    news_list.append({
                        "title": title,
                        "source": source,
                        "time": time_str,
                        "summary": summary,
                        "link": link,
                        "name_count": name_count,
                    })
            except Exception as e:
                logger.debug(f"解析新闻条目失败: {str(e)}")
                continue

        logger.info(f"解析到 {len(news_list)} 条新闻（已过滤不相关结果）")
        return news_list

    def extract_news_meta(self, item):
        """提取新闻来源、时间和摘要"""
        source = ""
        time_str = ""
        summary = ""

        source_elem = item.find("div", class_="news-source_2g3K-")
        if source_elem:
            source_text = source_elem.get_text(strip=True)
            parts = re.split(r"\s+", source_text)
            if len(parts) >= 2:
                source = parts[0]
                time_str = " ".join(parts[1:])
            elif len(parts) == 1:
                source = parts[0]

        if not source or not time_str or not summary:
            candidates = [tag.get_text(strip=True) for tag in item.find_all(["span", "p"]) if tag.get_text(strip=True)]
            for text in candidates:
                if not time_str and re.search(r"\d{4}年|\d{1,2}月|\d{1,2}日|小时前|分钟前|秒前|天前|小时|分钟", text):
                    time_str = text
                    continue
                if not summary and len(text) > 20 and "http" not in text:
                    summary = text
                    continue

            if not source:
                for text in reversed(candidates):
                    if text != time_str and text != summary:
                        source = text
                        break

        return source, time_str, summary


class HistoryManager:
    """历史记录管理器"""

    def __init__(self, filename="search_history.json"):
        self.filename = os.path.join(os.path.dirname(__file__), filename)
        self.history = self.load_history()

    def load_history(self):
        """加载历史记录"""
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.info("历史记录文件不存在或格式错误，创建新记录")
            return []

    def save_history(self):
        """保存历史记录"""
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def add_record(self, name, result_count):
        """添加搜索记录"""
        record = {
            "name": name,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "result_count": result_count,
        }
        self.history.insert(0, record)
        if len(self.history) > Config.MAX_HISTORY_COUNT:
            self.history = self.history[:Config.MAX_HISTORY_COUNT]
        self.save_history()
        logger.info(f"添加搜索记录: {name} - {result_count} 条结果")

    def clear_history(self):
        """清空历史记录"""
        self.history = []
        self.save_history()
        logger.info("清空搜索历史")


class SearchThread(QThread):
    """搜索线程"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(list, str)
    error = pyqtSignal(str)

    def __init__(self, name, page_count, site_filter):
        super().__init__()
        self.name = name
        self.page_count = page_count
        self.site_filter = site_filter
        self.crawler = NewsCrawler()
        self._is_running = True

    def run(self):
        try:
            all_news = []
            for page in range(1, self.page_count + 1):
                if not self._is_running:
                    break
                self.progress.emit(f"正在搜索第 {page}/{self.page_count} 页...")
                news = self.crawler.search_news(self.name, page, self.site_filter)
                all_news.extend(news)
                if page < self.page_count:
                    time.sleep(Config.REQUEST_INTERVAL)
            self.finished.emit(all_news, self.name)
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._is_running = False


class NewsSearchWidget(QWidget):
    """姓名新闻搜索系统主部件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.crawler = NewsCrawler()
        self.history_manager = HistoryManager()
        self.current_news = []
        self.filtered_news = []
        self.current_page = 0
        self.items_per_page = Config.DEFAULT_ITEMS_PER_PAGE
        self.search_thread = None

        self.setup_ui()

    def setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)

        # 搜索栏
        search_layout = QHBoxLayout()
        
        search_layout.addWidget(QLabel("输入姓名:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("请输入要搜索的姓名")
        self.name_edit.returnPressed.connect(self.start_search)
        search_layout.addWidget(self.name_edit)

        search_layout.addWidget(QLabel("搜索页数:"))
        self.page_spin = QSpinBox()
        self.page_spin.setRange(Config.MIN_SEARCH_PAGES, Config.MAX_SEARCH_PAGES)
        self.page_spin.setValue(Config.DEFAULT_SEARCH_PAGES)
        search_layout.addWidget(self.page_spin)

        search_layout.addWidget(QLabel("搜索范围:"))
        self.scope_combo = QComboBox()
        self.scope_combo.addItem("全部新闻", "")
        for name, value in Config.SEARCH_SCOPE_OPTIONS:
            self.scope_combo.addItem(name, value)
        search_layout.addWidget(self.scope_combo)

        self.search_btn = QPushButton("搜索")
        self.search_btn.clicked.connect(self.start_search)
        search_layout.addWidget(self.search_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_search)
        self.stop_btn.setEnabled(False)
        search_layout.addWidget(self.stop_btn)

        search_layout.addStretch()
        layout.addLayout(search_layout)

        # 状态标签
        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)

        # 标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget, 1)

        # 搜索结果页
        self.results_tab = QWidget()
        self.setup_results_tab()
        self.tab_widget.addTab(self.results_tab, "搜索结果")

        # 统计分析页
        self.stats_tab = QWidget()
        self.setup_stats_tab()
        self.tab_widget.addTab(self.stats_tab, "统计分析")

        # 历史记录页
        self.history_tab = QWidget()
        self.setup_history_tab()
        self.tab_widget.addTab(self.history_tab, "搜索历史")

    def setup_results_tab(self):
        """设置搜索结果标签页"""
        layout = QVBoxLayout(self.results_tab)

        # 筛选栏
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("来源筛选:"))
        self.source_combo = QComboBox()
        self.source_combo.addItem("全部来源")
        self.source_combo.currentTextChanged.connect(self.on_filter_sort_changed)
        filter_layout.addWidget(self.source_combo)

        filter_layout.addWidget(QLabel("排序:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(Config.SORT_OPTIONS)
        self.sort_combo.currentTextChanged.connect(self.on_filter_sort_changed)
        filter_layout.addWidget(self.sort_combo)

        self.export_btn = QPushButton("导出CSV")
        self.export_btn.clicked.connect(self.export_csv)
        filter_layout.addWidget(self.export_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # 分页控制
        page_layout = QHBoxLayout()
        self.prev_btn = QPushButton("上一页")
        self.prev_btn.clicked.connect(self.goto_prev_page)
        self.prev_btn.setEnabled(False)
        page_layout.addWidget(self.prev_btn)

        self.page_info_label = QLabel("当前页 0 / 0")
        page_layout.addWidget(self.page_info_label)

        self.next_btn = QPushButton("下一页")
        self.next_btn.clicked.connect(self.goto_next_page)
        self.next_btn.setEnabled(False)
        page_layout.addWidget(self.next_btn)

        self.open_link_btn = QPushButton("打开原文")
        self.open_link_btn.clicked.connect(self.open_selected_link)
        page_layout.addWidget(self.open_link_btn)

        # 详情面板切换按钮
        self.toggle_detail_btn = QPushButton("隐藏详情")
        self.toggle_detail_btn.clicked.connect(self.toggle_detail_panel)
        page_layout.addWidget(self.toggle_detail_btn)

        page_layout.addStretch()
        layout.addLayout(page_layout)

        # 结果表格和详情
        splitter = QSplitter(Qt.Horizontal)
        self.splitter = splitter

        self.news_table = QTableWidget()
        self.news_table.setColumnCount(4)
        self.news_table.setHorizontalHeaderLabels(["标题", "来源", "发布时间", "姓名出现次数"])
        self.news_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.news_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.news_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.news_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.news_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.news_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.news_table.cellDoubleClicked.connect(self.open_news_link)
        self.news_table.itemSelectionChanged.connect(self.show_news_detail)
        splitter.addWidget(self.news_table)

        self.detail_text = QTextEdit()
        self.detail_text.setReadOnly(True)
        self.detail_text.setPlaceholderText("选择新闻查看详情")
        splitter.addWidget(self.detail_text)
        self.detail_text_visible = True

        splitter.setSizes([2, 1])
        layout.addWidget(splitter, 1)

    def setup_stats_tab(self):
        """设置统计分析标签页"""
        layout = QVBoxLayout(self.stats_tab)
        
        self.stats_info_label = QLabel("暂无统计数据")
        layout.addWidget(self.stats_info_label)

        # 图表容器
        self.figure = plt.figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, 1)

    def setup_history_tab(self):
        """设置历史记录标签页"""
        layout = QVBoxLayout(self.history_tab)

        btn_layout = QHBoxLayout()
        self.refresh_history_btn = QPushButton("刷新历史")
        self.refresh_history_btn.clicked.connect(self.refresh_history)
        btn_layout.addWidget(self.refresh_history_btn)

        self.clear_history_btn = QPushButton("清空历史")
        self.clear_history_btn.clicked.connect(self.clear_history)
        btn_layout.addWidget(self.clear_history_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(3)
        self.history_table.setHorizontalHeaderLabels(["搜索姓名", "搜索时间", "结果数量"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.cellDoubleClicked.connect(self.research_from_history)
        layout.addWidget(self.history_table, 1)

        self.refresh_history()

    def start_search(self):
        """开始搜索"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "警告", "请输入要搜索的姓名")
            return

        if self.search_thread and self.search_thread.isRunning():
            QMessageBox.information(self, "提示", "正在搜索中，请稍候...")
            return

        page_count = self.page_spin.value()
        site_filter = self.scope_combo.currentData()

        self.search_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.current_news = []

        self.search_thread = SearchThread(name, page_count, site_filter)
        self.search_thread.progress.connect(self.on_search_progress)
        self.search_thread.finished.connect(self.on_search_finished)
        self.search_thread.error.connect(self.on_search_error)
        self.search_thread.start()

    def stop_search(self):
        """停止搜索"""
        if self.search_thread:
            self.search_thread.stop()
            self.status_label.setText("搜索已停止")
            logger.info("搜索已停止")

    def on_search_progress(self, message):
        """搜索进度更新"""
        self.status_label.setText(message)

    def on_search_finished(self, news_list, name):
        """搜索完成"""
        self.current_news = news_list
        self.search_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText(f"搜索完成，共找到 {len(news_list)} 条新闻")
        
        if len(news_list) > 0:
            self.history_manager.add_record(name, len(news_list))
            self.refresh_history()
        
        self.update_source_filter_options()
        self.current_page = 0
        self.display_current_page(name)
        self.update_statistics(name)

    def on_search_error(self, error_msg):
        """搜索错误"""
        self.search_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.critical(self, "错误", f"搜索失败: {error_msg}")
        self.status_label.setText("搜索失败")

    def update_source_filter_options(self):
        """更新来源筛选选项"""
        sources = set()
        for news in self.current_news:
            if news.get("source"):
                sources.add(news["source"])
        
        self.source_combo.blockSignals(True)
        current_text = self.source_combo.currentText()
        self.source_combo.clear()
        self.source_combo.addItem("全部来源")
        for source in sorted(sources):
            self.source_combo.addItem(source)
        index = self.source_combo.findText(current_text)
        if index >= 0:
            self.source_combo.setCurrentIndex(index)
        self.source_combo.blockSignals(False)

    def on_filter_sort_changed(self):
        """筛选或排序改变"""
        self.current_page = 0
        self.display_current_page(self.name_edit.text().strip())

    def apply_filter_sort(self):
        """应用筛选和排序"""
        filtered = list(self.current_news)
        
        source = self.source_combo.currentText()
        if source and source != "全部来源":
            filtered = [n for n in filtered if n.get("source") == source]
        
        sort_option = self.sort_combo.currentText()
        if sort_option == "姓名出现次数降序":
            filtered.sort(key=lambda x: x.get("name_count", 0), reverse=True)
        elif sort_option == "姓名出现次数升序":
            filtered.sort(key=lambda x: x.get("name_count", 0))
        elif sort_option == "发布时间最新":
            filtered.sort(key=lambda x: self.parse_time_sort_value(x.get("time", "")), reverse=True)
        elif sort_option == "发布时间最旧":
            filtered.sort(key=lambda x: self.parse_time_sort_value(x.get("time", "")))
        elif sort_option == "来源 A-Z":
            filtered.sort(key=lambda x: x.get("source", ""))
        elif sort_option == "来源 Z-A":
            filtered.sort(key=lambda x: x.get("source", ""), reverse=True)
        
        self.filtered_news = filtered

    def parse_time_sort_value(self, time_str):
        """解析时间用于排序"""
        if not time_str:
            return datetime.min
        time_str = time_str.strip()
        now = datetime.now()
        relative_match = re.search(r"(\d+)(分钟|小时|天)前", time_str)
        if relative_match:
            value = int(relative_match.group(1))
            unit = relative_match.group(2)
            if unit == "分钟":
                return now - timedelta(minutes=value)
            if unit == "小时":
                return now - timedelta(hours=value)
            if unit == "天":
                return now - timedelta(days=value)
        match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", time_str)
        if match:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        match = re.search(r"(\d{1,2})月(\d{1,2})日", time_str)
        if match:
            year = now.year
            return datetime(year, int(match.group(1)), int(match.group(2)))
        return datetime.min

    def display_current_page(self, name):
        """显示当前页"""
        self.apply_filter_sort()
        total_count = len(self.filtered_news)
        total_pages = max(1, (total_count + self.items_per_page - 1) // self.items_per_page)

        if self.current_page >= total_pages:
            self.current_page = max(0, total_pages - 1)

        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_news = self.filtered_news[start:end]

        self.news_table.setRowCount(len(page_news))
        for row, news in enumerate(page_news):
            self.news_table.setItem(row, 0, QTableWidgetItem(news.get("title", "")))
            self.news_table.setItem(row, 1, QTableWidgetItem(news.get("source", "")))
            self.news_table.setItem(row, 2, QTableWidgetItem(news.get("time", "")))
            self.news_table.setItem(row, 3, QTableWidgetItem(str(news.get("name_count", 0))))

        self.page_info_label.setText(f"当前页 {self.current_page + 1} / {total_pages}")
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page < total_pages - 1)

    def goto_prev_page(self):
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            self.display_current_page(self.name_edit.text().strip())

    def goto_next_page(self):
        """下一页"""
        total_count = len(self.filtered_news)
        total_pages = max(1, (total_count + self.items_per_page - 1) // self.items_per_page)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.display_current_page(self.name_edit.text().strip())

    def show_news_detail(self):
        """显示新闻详情"""
        selected_rows = self.news_table.selectionModel().selectedRows()
        if not selected_rows:
            self.detail_text.clear()
            return

        row = selected_rows[0].row()
        start = self.current_page * self.items_per_page
        if start + row < len(self.filtered_news):
            news = self.filtered_news[start + row]
            detail = f"标题: {news.get('title', '')}\n\n"
            detail += f"来源: {news.get('source', '')}\n"
            detail += f"发布时间: {news.get('time', '')}\n"
            detail += f"姓名出现次数: {news.get('name_count', 0)}\n\n"
            detail += f"摘要:\n{news.get('summary', '')}\n\n"
            detail += f"链接: {news.get('link', '')}\n\n"
            detail += "提示：双击表格行可在浏览器中打开新闻链接"
            self.detail_text.setText(detail)

    def open_news_link(self, row, column):
        """打开新闻链接"""
        start = self.current_page * self.items_per_page
        if start + row < len(self.filtered_news):
            news = self.filtered_news[start + row]
            link = news.get("link", "")
            if link:
                try:
                    webbrowser.open(link)
                    logger.info(f"打开链接: {link}")
                except Exception as e:
                    logger.error(f"打开链接失败: {str(e)}")
                    QMessageBox.critical(self, "错误", f"无法打开链接: {str(e)}")

    def open_selected_link(self):
        """打开选中的链接"""
        selected_rows = self.news_table.selectionModel().selectedRows()
        if selected_rows:
            self.open_news_link(selected_rows[0].row(), 0)
        else:
            QMessageBox.information(self, "提示", "请先选择一条新闻")

    def toggle_detail_panel(self):
        """切换详情面板显示"""
        if self.detail_text_visible:
            self.detail_text.hide()
            self.detail_text_visible = False
            self.toggle_detail_btn.setText("显示详情")
        else:
            self.detail_text.show()
            self.detail_text_visible = True
            self.toggle_detail_btn.setText("隐藏详情")

    def export_csv(self):
        """导出CSV"""
        if not self.filtered_news:
            QMessageBox.warning(self, "提示", "当前没有可导出的新闻结果")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "保存CSV", f"新闻搜索结果_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 
            "CSV文件 (*.csv);;所有文件 (*.*)"
        )
        if filename:
            try:
                df = pd.DataFrame(self.filtered_news)
                df.to_csv(filename, index=False, encoding="utf-8-sig")
                QMessageBox.information(self, "成功", f"已导出 {len(self.filtered_news)} 条新闻到\n{filename}")
                logger.info(f"导出CSV成功: {filename}, {len(self.filtered_news)} 条")
            except Exception as e:
                logger.error(f"导出CSV失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"导出CSV失败: {str(e)}")

    def update_statistics(self, name):
        """更新统计图表"""
        if not self.current_news:
            self.stats_info_label.setText("暂无统计数据 - 请先进行搜索")
            self.figure.clear()
            self.canvas.draw()
            return

        self.figure.clear()

        df = pd.DataFrame(self.current_news)
        df["source"] = df["source"].fillna("未知")
        df["name_count"] = df["name_count"].fillna(0).astype(int)
        df["summary"] = df["summary"].fillna("")
        df["time"] = df["time"].fillna("")

        gs = self.figure.add_gridspec(2, 2)

        ax1 = self.figure.add_subplot(gs[0, 0])
        source_counts = df["source"].value_counts().head(10)
        ax1.bar(source_counts.index, source_counts.values, color="skyblue")
        ax1.set_title("新闻来源分布(Top10)", fontsize=12)
        ax1.set_xlabel("来源")
        ax1.set_ylabel("新闻数量")
        ax1.tick_params(axis="x", rotation=45)

        ax2 = self.figure.add_subplot(gs[0, 1])
        name_count_max = max(1, int(df["name_count"].max()))
        ax2.hist(df["name_count"], bins=range(0, name_count_max + 2, 1), color="lightgreen", edgecolor="black")
        ax2.set_title("姓名出现次数分布", fontsize=12)
        ax2.set_xlabel("出现次数")
        ax2.set_ylabel("新闻数量")

        ax3 = self.figure.add_subplot(gs[1, 0])

        def extract_year_month(time_str):
            match = re.search(r"(\d{4})年(\d{1,2})月", time_str)
            if match:
                return f"{match.group(1)}-{match.group(2).zfill(2)}"
            match = re.search(r"(\d{1,2})月(\d{1,2})日", time_str)
            if match:
                return f"{datetime.now().year}-{match.group(1).zfill(2)}"
            if "前" in time_str or "小时" in time_str or "分钟" in time_str or "天" in time_str:
                return "近期"
            return "未知"

        df["year_month"] = df["time"].apply(extract_year_month)
        time_counts = df["year_month"].value_counts().sort_index()
        if not time_counts.empty:
            ax3.plot(time_counts.index, time_counts.values, marker="o", color="orange")
            ax3.set_title("新闻发布时间分布", fontsize=12)
            ax3.set_xlabel("时间")
            ax3.set_ylabel("新闻数量")
            ax3.tick_params(axis="x", rotation=45)
        else:
            ax3.text(0.5, 0.5, "无可用发布时间数据", ha="center", va="center", fontsize=12)
            ax3.set_axis_off()

        ax4 = self.figure.add_subplot(gs[1, 1])
        df["summary_length"] = df["summary"].str.len()
        if df["summary_length"].sum() > 0:
            ax4.scatter(df["summary_length"], df["name_count"], alpha=0.6, color="purple")
            ax4.set_title("摘要长度与姓名出现次数关系", fontsize=12)
            ax4.set_xlabel("摘要长度(字符)")
            ax4.set_ylabel("姓名出现次数")
        else:
            ax4.text(0.5, 0.5, "无摘要长度数据", ha="center", va="center", fontsize=12)
            ax4.set_axis_off()

        self.figure.suptitle(f"'{name}' 新闻统计分析", fontsize=16)
        self.figure.tight_layout()
        self.canvas.draw()

        self.stats_info_label.setText(f"统计数据基于 {len(df)} 条新闻生成")

    def refresh_history(self):
        """刷新历史记录"""
        history = self.history_manager.history
        self.history_table.setRowCount(len(history))
        for row, record in enumerate(history):
            self.history_table.setItem(row, 0, QTableWidgetItem(record.get("name", "")))
            self.history_table.setItem(row, 1, QTableWidgetItem(record.get("time", "")))
            self.history_table.setItem(row, 2, QTableWidgetItem(str(record.get("result_count", 0))))

    def clear_history(self):
        """清空历史记录"""
        if QMessageBox.question(self, "确认", "确定要清空所有搜索历史吗？",
                               QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.history_manager.clear_history()
            self.refresh_history()

    def research_from_history(self, row, column):
        """从历史记录重新搜索"""
        history = self.history_manager.history
        if row < len(history):
            self.name_edit.setText(history[row].get("name", ""))
            self.start_search()

    def toggle_detail_panel(self):
        """切换详情面板显示"""
        if self.detail_text_visible:
            self.detail_text.hide()
            self.detail_text_visible = False
            self.toggle_detail_btn.setText("显示详情")
        else:
            self.detail_text.show()
            self.detail_text_visible = True
            self.toggle_detail_btn.setText("隐藏详情")
