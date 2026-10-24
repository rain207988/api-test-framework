"""统一日志：控制台看进度，文件留证据（失败排查的第一现场）。

设计要点：
- 同名 logger 全局复用（handlers 只挂一次，防止重复打印两遍）；
- 文件按天滚动：今天跑了多少轮都在一个文件里，方便"昨晚 Jenkins 回归"式回看；
- 级别从配置读取：默认 INFO 只记动作，改 DEBUG 可看完整请求/响应报文。
"""

import logging
import os
from datetime import datetime

from common.config_loader import get_config

FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"


def get_logger(name: str = "api-test") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:                      # 已初始化过，直接复用
        return logger

    cfg = get_config()
    os.makedirs(cfg.log_dir, exist_ok=True)
    log_file = os.path.join(cfg.log_dir, f"run_{datetime.now():%Y%m%d}.log")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(FORMAT))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(FORMAT))

    logger.setLevel(cfg.log_level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.propagate = False                 # 防止向 pytest 的 root logger 冒泡重复输出
    return logger
