import logging
import sys
import os

# 支持相对导入和直接运行
try:
    from .config import Config
except ImportError:
    from config import Config

def setup_logging():
    """配置日志系统"""
    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format=Config.LOG_FORMAT,
        handlers=[
            logging.FileHandler("news_search.log", encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()
