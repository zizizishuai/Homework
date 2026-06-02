# 配置文件
# 姓名新闻搜索系统配置

class Config:
    # 搜索配置
    DEFAULT_SEARCH_PAGES = 5
    MAX_SEARCH_PAGES = 10
    MIN_SEARCH_PAGES = 1
    
    # 请求配置
    REQUEST_TIMEOUT = 10
    REQUEST_INTERVAL = 1  # 请求间隔（秒）
    MAX_RETRY_COUNT = 3
    
    # 历史记录配置
    MAX_HISTORY_COUNT = 50
    
    # UI配置
    DEFAULT_WINDOW_SIZE = "1200x800"
    MIN_WINDOW_SIZE = "1000x700"
    DEFAULT_ITEMS_PER_PAGE = 22
    
    # 搜索范围选项
    SEARCH_SCOPE_OPTIONS = [
        ("全部新闻", ""),
        ("新闻网站", ""),
        ("政府网站", "gov"),
        ("教育网站", "edu"),
        ("企业网站", "com"),
    ]
    
    # 排序选项
    SORT_OPTIONS = [
        "默认排序",
        "姓名出现次数降序",
        "姓名出现次数升序",
        "发布时间最新",
        "发布时间最旧",
        "来源 A-Z",
        "来源 Z-A",
    ]
    
    # 数据源配置
    BAIDU_SEARCH_URL = "https://www.baidu.com/s"
    
    # 日志配置
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
