# -*- coding: utf-8 -*-
"""
项目统一日志模块
支持同时输出到控制台和文件，按日期分文件存储
"""

import os
import sys
import logging
from datetime import datetime
from .config import LOG_DIR


class Logger:
    """项目日志管理器"""

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, log_name: str = "taxi_analysis",
                 log_dir: str = None):
        """
        Parameters
        ----------
        log_name : str
            日志文件前缀名
        log_dir : str, optional
            日志目录，默认使用配置中的 LOG_DIR
        """
        if self._initialized:
            return

        self.log_dir = log_dir or LOG_DIR
        os.makedirs(self.log_dir, exist_ok=True)

        # 日志文件名: taxidata_20260627.log
        today = datetime.now().strftime("%Y%m%d")
        self.log_file = os.path.join(self.log_dir, f"{log_name}_{today}.log")

        # 创建 logger
        self.logger = logging.getLogger("TaxiAnalysis")
        self.logger.setLevel(logging.DEBUG)

        # 避免重复添加 handler
        if not self.logger.handlers:
            # 文件 Handler — DEBUG 级别，含时间戳
            file_handler = logging.FileHandler(self.log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(module)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

            # 控制台 Handler — INFO 级别
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                "[%(levelname)-5s] %(message)s"
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

        self._initialized = True

    # ----------------------------------------------------------
    # 便捷方法
    # ----------------------------------------------------------
    def debug(self, msg: str):
        self.logger.debug(msg)

    def info(self, msg: str):
        self.logger.info(msg)

    def warning(self, msg: str):
        self.logger.warning(msg)

    def error(self, msg: str):
        self.logger.error(msg)

    def critical(self, msg: str):
        self.logger.critical(msg)

    def section(self, title: str):
        """打印分隔标题"""
        self.info("=" * 60)
        self.info(f"  {title}")
        self.info("=" * 60)

    def get_log_file(self) -> str:
        """获取当前日志文件路径"""
        return self.log_file


# 全局单例
log = Logger()


def get_logger() -> Logger:
    """获取日志器实例"""
    return log


def setup_logger(log_name: str = "taxi_analysis") -> Logger:
    """设置并返回日志器实例"""
    global log
    log = Logger(log_name)
    return log
