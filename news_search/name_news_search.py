import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, font as tkfont
import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from fake_useragent import UserAgent
import re
import json
import time
from datetime import datetime, timedelta
import threading
import webbrowser
from config import Config
from logger import logger

plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
plt.rcParams["axes.unicode_minus"] = False


class NewsCrawler:
    """百度新闻爬虫类"""

    def __init__(self):
        self.ua = UserAgent()
        self.base_url = Config.BAIDU_SEARCH_URL
        self.session = requests.Session()

    def search_news(self, name, page=1, site_filter="", timeout=Config.REQUEST_TIMEOUT):
        """搜索指定姓名的新闻"""
        query = f"{name} 新闻".strip()
        search_type = "news"

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
            "ie": "utf-8"
        }
        if search_type == "news":
            params["cl"] = 2
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

                # 只保留姓名出现次数大于0的新闻
                if name_count > 0:
                    news_list.append(
                        {
                            "title": title,
                            "source": source,
                            "time": time_str,
                            "summary": summary,
                            "link": link,
                            "name_count": name_count,
                        }
                    )
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
        self.filename = filename
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

    def get_recent_names(self, limit=10):
        """获取最近搜索的姓名（去重）"""
        names = []
        seen = set()
        for record in self.history:
            name = record["name"]
            if name not in seen:
                names.append(name)
                seen.add(name)
            if len(names) >= limit:
                break
        return names


class NameNewsSearchApp:
    """主应用类"""

    def __init__(self, root):
        self.root = root
        self.root.title("姓名新闻搜索系统")
        self.root.geometry(Config.DEFAULT_WINDOW_SIZE)
        self.root.minsize(*map(int, Config.MIN_WINDOW_SIZE.split("x")))

        self.crawler = NewsCrawler()
        self.history_manager = HistoryManager()
        self.current_news = []
        self.filtered_news = []
        self.displayed_news = []
        self.current_page = 0
        self.items_per_page = Config.DEFAULT_ITEMS_PER_PAGE
        self.is_searching = False
        self.search_page_count = Config.DEFAULT_SEARCH_PAGES
        self.page_display_var = tk.StringVar(value="每页 0 / 共 0 页")
        self.detail_visible = True
        self.detail_frame = None
        self.history_recorded = False
        self.all_news_pages = []
        
        self.search_scope_options = Config.SEARCH_SCOPE_OPTIONS
        self.sort_options = Config.SORT_OPTIONS
        self.search_scope_var = tk.StringVar(value=self.search_scope_options[0][0])

        self.setup_ui()

    def setup_ui(self):
        """设置用户界面"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        search_frame = ttk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="输入姓名:", font=("微软雅黑", 12)).pack(side=tk.LEFT, padx=(0, 5))

        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(search_frame, textvariable=self.name_var, font=("微软雅黑", 12), width=30)
        self.name_entry.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        self.name_entry.bind("<Return>", lambda e: self.start_search())

        ttk.Label(search_frame, text="搜索页数:", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(10, 5))
        self.page_count_var = tk.StringVar(value=str(self.search_page_count))
        self.page_count_spinbox = ttk.Spinbox(
            search_frame, 
            from_=Config.MIN_SEARCH_PAGES, 
            to=Config.MAX_SEARCH_PAGES, 
            textvariable=self.page_count_var,
            width=5,
            font=("微软雅黑", 10)
        )
        self.page_count_spinbox.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Label(search_frame, text="搜索范围:", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(10, 5))
        self.search_scope_combo = ttk.Combobox(
            search_frame, 
            textvariable=self.search_scope_var, 
            values=[name for name, _ in self.search_scope_options],
            state="readonly",
            width=12
        )
        self.search_scope_combo.pack(side=tk.LEFT, padx=(0, 5))

        self.search_btn = ttk.Button(search_frame, text="搜索", command=self.start_search, width=10)
        self.search_btn.pack(side=tk.LEFT, padx=(10, 5))

        self.page_count_label = ttk.Label(search_frame, textvariable=self.page_display_var, font=("微软雅黑", 10))
        self.page_count_label.pack(side=tk.LEFT, padx=(10, 10))

        self.stop_btn = ttk.Button(search_frame, text="停止", command=self.stop_search, width=10, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        self.results_frame = ttk.Frame(notebook)
        notebook.add(self.results_frame, text="搜索结果")
        self.setup_results_tab()

        self.stats_frame = ttk.Frame(notebook)
        notebook.add(self.stats_frame, text="统计分析")
        self.setup_stats_tab()

        self.history_frame = ttk.Frame(notebook)
        notebook.add(self.history_frame, text="搜索历史")
        self.setup_history_tab()

        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(5, 2))
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.root.bind("<Configure>", lambda e: self.on_root_resize())
        self.root.after(200, self.update_items_per_page)

    def setup_results_tab(self):
        """设置搜索结果标签页"""
        info_frame = ttk.Frame(self.results_frame)
        info_frame.pack(fill=tk.X, pady=(0, 5))

        self.result_count_var = tk.StringVar()
        self.result_count_var.set("共找到 0 条新闻")
        ttk.Label(info_frame, textvariable=self.result_count_var, font=("微软雅黑", 10)).pack(side=tk.LEFT)

        self.page_info_var = tk.StringVar()
        self.page_info_var.set("当前页 0 / 0")
        ttk.Label(info_frame, textvariable=self.page_info_var, font=("微软雅黑", 10)).pack(side=tk.RIGHT)

        filter_frame = ttk.Frame(self.results_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(filter_frame, text="来源筛选:", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.source_filter_var = tk.StringVar(value="全部来源")
        self.source_filter_combo = ttk.Combobox(filter_frame, textvariable=self.source_filter_var, values=["全部来源"], state="readonly", width=18)
        self.source_filter_combo.pack(side=tk.LEFT)
        self.source_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.on_filter_or_sort_changed())

        ttk.Label(filter_frame, text="排序:", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=(20, 5))
        self.sort_option_var = tk.StringVar(value=self.sort_options[0])
        self.sort_option_combo = ttk.Combobox(filter_frame, textvariable=self.sort_option_var, values=self.sort_options, state="readonly", width=18)
        self.sort_option_combo.pack(side=tk.LEFT)
        self.sort_option_combo.bind("<<ComboboxSelected>>", lambda e: self.on_filter_or_sort_changed())

        ttk.Button(filter_frame, text="导出CSV", command=self.export_csv, width=10).pack(side=tk.RIGHT)

        nav_frame = ttk.Frame(self.results_frame)
        nav_frame.pack(fill=tk.X, pady=(0, 5))
        self.prev_page_btn = ttk.Button(nav_frame, text="上一页", command=self.goto_prev_page, width=10, state=tk.DISABLED)
        self.prev_page_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.next_page_btn = ttk.Button(nav_frame, text="下一页", command=self.goto_next_page, width=10, state=tk.DISABLED)
        self.next_page_btn.pack(side=tk.LEFT)
        ttk.Button(nav_frame, text="打开原文", command=self.open_selected_link, width=10).pack(side=tk.LEFT, padx=(10, 0))
        self.toggle_detail_btn = ttk.Button(nav_frame, text="隐藏详情", command=self.toggle_detail_panel, width=10)
        self.toggle_detail_btn.pack(side=tk.LEFT, padx=(10, 0))

        content_frame = ttk.Frame(self.results_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.columnconfigure(0, weight=3)
        content_frame.columnconfigure(1, weight=2)
        content_frame.rowconfigure(0, weight=1)

        columns = ("标题", "来源", "发布时间", "姓名出现次数")

        self.tree_frame = ttk.Frame(content_frame)
        self.tree_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 5))
        self.tree_frame.columnconfigure(0, weight=1)
        self.tree_frame.rowconfigure(0, weight=1)

        self.news_tree = ttk.Treeview(self.tree_frame, columns=columns, show="headings")
        self.news_tree.column("标题", width=500, anchor=tk.W)
        self.news_tree.column("来源", width=150, anchor=tk.CENTER)
        self.news_tree.column("发布时间", width=150, anchor=tk.CENTER)
        self.news_tree.column("姓名出现次数", width=100, anchor=tk.CENTER)

        for col in columns:
            self.news_tree.heading(col, text=col)

        tree_scroll = ttk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.news_tree.yview)
        self.news_tree.configure(yscrollcommand=tree_scroll.set)

        self.news_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.news_tree.bind("<Double-1>", self.open_news_link)

        detail_frame = ttk.LabelFrame(content_frame, text="新闻详情", padding="10")
        detail_frame.grid(row=0, column=1, sticky="nsew", pady=(0, 5))

        self.detail_text = scrolledtext.ScrolledText(detail_frame, wrap=tk.WORD, font=("微软雅黑", 10), borderwidth=0)
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        self.detail_text.config(state=tk.DISABLED)
        self.detail_frame = detail_frame

        self.news_tree.bind("<<TreeviewSelect>>", self.show_news_detail)

    def setup_stats_tab(self):
        """设置统计分析标签页"""
        stats_info_frame = ttk.Frame(self.stats_frame)
        stats_info_frame.pack(fill=tk.X, pady=(0, 10))

        self.stats_info_var = tk.StringVar()
        self.stats_info_var.set("暂无统计数据")
        ttk.Label(stats_info_frame, textvariable=self.stats_info_var, font=("微软雅黑", 10)).pack(side=tk.LEFT)

        self.chart_frame = ttk.Frame(self.stats_frame)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)

    def setup_history_tab(self):
        """设置历史记录标签页"""
        btn_frame = ttk.Frame(self.history_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(btn_frame, text="刷新历史", command=self.refresh_history).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="清空历史", command=self.clear_history).pack(side=tk.LEFT)

        columns = ("搜索姓名", "搜索时间", "结果数量")
        self.history_tree = ttk.Treeview(self.history_frame, columns=columns, show="headings", height=20)

        self.history_tree.column("搜索姓名", width=200, anchor=tk.CENTER)
        self.history_tree.column("搜索时间", width=250, anchor=tk.CENTER)
        self.history_tree.column("结果数量", width=100, anchor=tk.CENTER)

        for col in columns:
            self.history_tree.heading(col, text=col)

        history_scroll = ttk.Scrollbar(self.history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=history_scroll.set)

        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        history_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.history_tree.bind("<Double-1>", self.research_from_history)

        self.refresh_history()

    def start_search(self):
        """开始搜索"""
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("警告", "请输入要搜索的姓名")
            return

        if self.is_searching:
            messagebox.showinfo("提示", "正在搜索中，请稍候...")
            return

        try:
            self.search_page_count = int(self.page_count_var.get())
        except ValueError:
            self.search_page_count = Config.DEFAULT_SEARCH_PAGES
            self.page_count_var.set(str(self.search_page_count))

        self.is_searching = True
        self.search_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set(f"正在搜索 '{name}' 的新闻...")

        self.clear_results()
        self.history_recorded = False

        search_thread = threading.Thread(target=self.perform_search, args=(name,))
        search_thread.daemon = True
        search_thread.start()

    def perform_search(self, name):
        """执行搜索"""
        try:
            self.all_news_pages = []
            page_count = max(Config.MIN_SEARCH_PAGES, min(self.search_page_count, Config.MAX_SEARCH_PAGES))
            site_filter = self.get_site_filter()
            
            logger.info(f"开始搜索: {name}, 页数: {page_count}, 站点筛选: {site_filter}")
            
            for page in range(1, page_count + 1):
                if not self.is_searching:
                    break

                self.root.after(0, lambda p=page: self.status_var.set(f"正在搜索第 {p}/{page_count} 页..."))
                news = self.crawler.search_news(name, page, site_filter)
                self.all_news_pages.append(news)
                
                if page < page_count:
                    time.sleep(Config.REQUEST_INTERVAL)

            self.current_news = [item for page in self.all_news_pages for item in page]
            self.current_page = 0
            self.root.after(0, lambda: self.display_current_page(name))
            
            logger.info(f"搜索完成: {name}, 共找到 {len(self.current_news)} 条新闻")
        except Exception as e:
            logger.error(f"搜索失败: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("错误", f"搜索失败: {str(e)}"))
        finally:
            self.is_searching = False
            self.root.after(0, lambda: self.search_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.status_var.set("搜索完成"))

    def get_site_filter(self):
        """根据搜索范围选择器返回 site: 过滤值"""
        selected = self.search_scope_var.get()
        for name, filter_value in self.search_scope_options:
            if name == selected:
                return filter_value
        return ""

    def goto_prev_page(self):
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            self.display_current_page(self.name_var.get().strip())

    def goto_next_page(self):
        """下一页"""
        total_count = len(self.filtered_news)
        total_pages = max(1, (total_count + self.items_per_page - 1) // self.items_per_page)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.display_current_page(self.name_var.get().strip())

    def display_current_page(self, name):
        """显示当前页结果"""
        for item in self.news_tree.get_children():
            self.news_tree.delete(item)

        if not self.all_news_pages:
            self.page_info_var.set("当前页 0 / 0")
            self.result_count_var.set(f"共找到 0 条关于 '{name}' 的新闻")
            self.displayed_news = []
            self.update_statistics(name)
            return

        self.apply_filter_sort()
        total_count = len(self.filtered_news)
        total_pages = max(1, (total_count + self.items_per_page - 1) // self.items_per_page)
        if self.current_page >= total_pages:
            self.current_page = max(0, total_pages - 1)

        start = self.current_page * self.items_per_page
        end = start + self.items_per_page
        page_news = self.filtered_news[start:end]
        self.displayed_news = page_news

        for i, news in enumerate(page_news):
            values = (news["title"], news["source"], news["time"], news["name_count"])
            self.news_tree.insert("", tk.END, iid=str(i), values=values)

        self.update_source_filter_options()
        self.source_filter_combo.set(self.source_filter_var.get())

        self.result_count_var.set(f"共找到 {total_count} 条关于 '{name}' 的新闻")
        self.page_info_var.set(f"当前页 {self.current_page + 1} / {total_pages}")
        self.page_display_var.set(f"每页 {self.items_per_page} / 共 {total_pages} 页")

        self.prev_page_btn.config(state=tk.NORMAL if self.current_page > 0 else tk.DISABLED)
        self.next_page_btn.config(state=tk.NORMAL if self.current_page < total_pages - 1 else tk.DISABLED)

        if total_count > 0 and not self.history_recorded:
            self.history_manager.add_record(name, total_count)
            self.history_recorded = True
            self.refresh_history()

        self.update_statistics(name)

    def on_filter_or_sort_changed(self):
        """响应来源筛选或排序选项变化"""
        self.current_page = 0
        self.display_current_page(self.name_var.get().strip())

    def apply_filter_sort(self):
        """对当前新闻列表应用来源筛选与排序"""
        filtered = list(self.current_news)
        selected_source = self.source_filter_var.get()
        if selected_source and selected_source != "全部来源":
            filtered = [item for item in filtered if item.get("source") == selected_source]

        filtered = self.sort_results(filtered)
        self.filtered_news = filtered

    def sort_results(self, news_list):
        option = self.sort_option_var.get()
        if option == "姓名出现次数降序":
            return sorted(news_list, key=lambda item: item.get("name_count", 0), reverse=True)
        if option == "姓名出现次数升序":
            return sorted(news_list, key=lambda item: item.get("name_count", 0))
        if option == "发布时间最新":
            return sorted(news_list, key=lambda item: self.parse_time_sort_value(item.get("time", "")), reverse=True)
        if option == "发布时间最旧":
            return sorted(news_list, key=lambda item: self.parse_time_sort_value(item.get("time", "")) or datetime.min)
        if option == "来源 A-Z":
            return sorted(news_list, key=lambda item: item.get("source", ""))
        if option == "来源 Z-A":
            return sorted(news_list, key=lambda item: item.get("source", ""), reverse=True)
        return news_list

    def parse_time_sort_value(self, time_str):
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

    def update_source_filter_options(self):
        sources = {item.get("source", "未知") for item in self.current_news if item.get("source")}
        options = ["全部来源"] + sorted(sources)
        self.source_filter_combo.config(values=options)
        if self.source_filter_var.get() not in options:
            self.source_filter_var.set("全部来源")

    def export_csv(self):
        """导出当前结果为 CSV"""
        if not self.filtered_news:
            messagebox.showwarning("提示", "当前没有可导出的新闻结果")
            return

        path = filedialog.asksaveasfilename(
            title="保存 CSV",
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*")],
        )
        if not path:
            return

        try:
            df = pd.DataFrame(self.filtered_news)
            df.to_csv(path, index=False, encoding="utf-8-sig")
            messagebox.showinfo("成功", f"已导出 {len(self.filtered_news)} 条新闻到 {path}")
            logger.info(f"导出CSV成功: {path}, {len(self.filtered_news)} 条")
        except Exception as e:
            logger.error(f"导出CSV失败: {str(e)}")
            messagebox.showerror("错误", f"导出 CSV 失败: {str(e)}")

    def stop_search(self):
        """停止搜索"""
        self.is_searching = False
        self.status_var.set("搜索已停止")
        logger.info("搜索已停止")

    def clear_results(self):
        """清空搜索结果"""
        for item in self.news_tree.get_children():
            self.news_tree.delete(item)

        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)
        self.detail_text.config(state=tk.DISABLED)

        self.current_news = []
        self.filtered_news = []
        self.all_news_pages = []
        self.displayed_news = []
        self.current_page = 0
        self.page_info_var.set("当前页 0 / 0")

    def show_news_detail(self, event):
        """显示新闻详情"""
        selected_items = self.news_tree.selection()
        if not selected_items:
            return

        index = int(selected_items[0])
        if index < 0 or index >= len(self.displayed_news):
            return
        news = self.displayed_news[index]

        self.detail_text.config(state=tk.NORMAL)
        self.detail_text.delete(1.0, tk.END)

        detail_text = f"标题: {news['title']}\n\n"
        detail_text += f"来源: {news['source']}\n"
        detail_text += f"发布时间: {news['time']}\n"
        detail_text += f"姓名出现次数: {news['name_count']}\n\n"
        detail_text += f"摘要:\n{news['summary']}\n\n"
        detail_text += f"链接: {news['link']}\n\n"
        detail_text += "提示: 双击表格行可在浏览器中打开新闻链接"

        self.detail_text.insert(tk.END, detail_text)
        self.detail_text.config(state=tk.DISABLED)

    def open_news_link(self, event=None):
        """在浏览器中打开新闻链接"""
        selected_items = self.news_tree.selection()
        if not selected_items:
            return

        index = int(selected_items[0])
        if index < 0 or index >= len(self.displayed_news):
            return
        news = self.displayed_news[index]

        if news["link"]:
            try:
                webbrowser.open(news["link"])
                logger.info(f"打开链接: {news['link']}")
            except Exception as e:
                logger.error(f"打开链接失败: {str(e)}")
                messagebox.showerror("错误", f"无法打开链接: {str(e)}")

    def open_selected_link(self):
        """按钮触发打开选中链接"""
        self.open_news_link()

    def update_statistics(self, name):
        """更新统计分析图表"""
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        if not self.current_news:
            self.stats_info_var.set("暂无统计数据")
            return

        df = pd.DataFrame(self.current_news)
        df["source"] = df["source"].fillna("未知")
        df["name_count"] = df["name_count"].fillna(0).astype(int)
        df["summary"] = df["summary"].fillna("")
        df["time"] = df["time"].fillna("")

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle(f"'{name}' 新闻统计分析", fontsize=16)

        source_counts = df["source"].value_counts().head(10)
        ax1.bar(source_counts.index, source_counts.values, color="skyblue")
        ax1.set_title("新闻来源分布(Top10)")
        ax1.set_xlabel("来源")
        ax1.set_ylabel("新闻数量")
        ax1.tick_params(axis="x", rotation=45)

        name_count_max = max(1, int(df["name_count"].max()))
        ax2.hist(df["name_count"], bins=range(0, name_count_max + 2, 1), color="lightgreen", edgecolor="black")
        ax2.set_title("姓名出现次数分布")
        ax2.set_xlabel("出现次数")
        ax2.set_ylabel("新闻数量")

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
            ax3.set_title("新闻发布时间分布")
            ax3.set_xlabel("时间")
            ax3.set_ylabel("新闻数量")
            ax3.tick_params(axis="x", rotation=45)
        else:
            ax3.text(0.5, 0.5, "无可用发布时间数据", ha="center", va="center", fontsize=12)
            ax3.set_axis_off()

        df["summary_length"] = df["summary"].str.len()
        if df["summary_length"].sum() > 0:
            ax4.scatter(df["summary_length"], df["name_count"], alpha=0.6, color="purple")
            ax4.set_title("摘要长度与姓名出现次数关系")
            ax4.set_xlabel("摘要长度(字符)")
            ax4.set_ylabel("姓名出现次数")
        else:
            ax4.text(0.5, 0.5, "无摘要长度数据", ha="center", va="center", fontsize=12)
            ax4.set_axis_off()

        plt.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.stats_info_var.set(f"统计数据基于 {len(df)} 条新闻生成")

    def update_items_per_page(self, force_refresh=False):
        """根据树状视图高度动态计算每页显示的项目数并刷新显示"""
        try:
            style = ttk.Style()
            row_height = style.lookup("Treeview", "rowheight")
            if not row_height:
                try:
                    tree_font_name = self.news_tree.cget("font")
                    tree_font = tkfont.nametofont(tree_font_name) if tree_font_name else tkfont.nametofont("TkDefaultFont")
                except Exception:
                    tree_font = tkfont.nametofont("TkDefaultFont")
                row_height = tree_font.metrics("linespace") + 6

            if not row_height or int(row_height) <= 0:
                row_height = 24

            tree_h = self.tree_frame.winfo_height()
            if tree_h <= 0:
                self.root.after(150, lambda: self.update_items_per_page(force_refresh))
                return

            header_height = 22
            scrollbar_width = 18
            visible_height = max(0, tree_h - header_height - scrollbar_width - 8)
            row_height_int = int(row_height)
            
            if row_height_int <= 0:
                row_height_int = 24

            base_count = visible_height // row_height_int
            extra_count = 1 if (visible_height % row_height_int) > row_height_int // 2 else 0
            new_count = max(5, base_count + extra_count)

            if new_count != self.items_per_page or force_refresh:
                self.items_per_page = new_count
                self.news_tree.configure(height=new_count)
                self.current_page = 0
                self.display_current_page(self.name_var.get().strip())
            self.update_tree_column_widths()
        except Exception as e:
            logger.error(f"update_items_per_page error: {str(e)}")

    def on_root_resize(self, event=None):
        self.root.after(150, lambda: self.update_items_per_page())

    def toggle_detail_panel(self):
        """切换新闻详情面板显示"""
        if self.detail_visible:
            self.detail_frame.grid_remove()
            self.detail_visible = False
            self.toggle_detail_btn.config(text="显示详情")
        else:
            self.detail_frame.grid()
            self.detail_visible = True
            self.toggle_detail_btn.config(text="隐藏详情")
        self.update_items_per_page()

    def update_tree_column_widths(self):
        """让标题列随窗口宽度自适应"""
        tree_w = self.tree_frame.winfo_width()
        if tree_w <= 0:
            return

        other_columns_width = 150 + 150 + 100 + 24
        title_width = max(150, tree_w - other_columns_width)
        self.news_tree.column("标题", width=title_width)
        self.news_tree.column("来源", width=150, minwidth=100, stretch=False)
        self.news_tree.column("发布时间", width=150, minwidth=100, stretch=False)
        self.news_tree.column("姓名出现次数", width=100, minwidth=80, stretch=False)

    def refresh_history(self):
        """刷新历史记录"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        for i, record in enumerate(self.history_manager.history):
            values = (record["name"], record["time"], record["result_count"])
            self.history_tree.insert("", tk.END, iid=str(i), values=values)

    def clear_history(self):
        """清空历史记录"""
        if messagebox.askyesno("确认", "确定要清空所有搜索历史吗？"):
            self.history_manager.clear_history()
            self.refresh_history()

    def research_from_history(self, event):
        """从历史记录重新搜索"""
        selected_items = self.history_tree.selection()
        if not selected_items:
            return

        index = int(selected_items[0])
        record = self.history_manager.history[index]

        self.name_var.set(record["name"])
        self.start_search()


def main():
    logger.info("启动姓名新闻搜索系统")
    root = tk.Tk()
    app = NameNewsSearchApp(root)
    root.mainloop()
    logger.info("姓名新闻搜索系统已关闭")


if __name__ == "__main__":
    main()
