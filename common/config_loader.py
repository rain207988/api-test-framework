"""配置加载器：整个框架只在这里读一次配置文件。

为什么单例 + 惰性加载：
- 50 条用例共享同一份配置对象，避免重复 IO 和"改了配置一半用例没生效"的不一致；
- 环境切换只认环境变量 MALL_TEST_ENV（CI 流水线里改环境不改代码）。
"""

import os

import yaml

# 项目根目录（common/ 的上一级），所有"相对项目根"的路径都从这里拼
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_config_instance = None


class Config:
    def __init__(self, path: str = None):
        path = path or os.path.join(PROJECT_ROOT, "config", "config.yaml")
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.env = os.environ.get("MALL_TEST_ENV") or data["default_env"]
        if self.env not in data:
            raise KeyError(f"配置文件中不存在环境 [{self.env}]，现有环境：{list(data.keys())}")
        env_conf = data[self.env]

        # base_url 支持环境变量覆盖：本地调试/CI 端口不一致时不用改文件
        self.base_url = (os.environ.get("MALL_BASE_URL") or env_conf["base_url"]).rstrip("/")
        self.timeout = env_conf.get("timeout", 10)
        self.test_key = env_conf.get("test_key", "")
        self.users = env_conf.get("users", {})

        log_conf = data.get("log", {})
        self.log_level = os.environ.get("MALL_LOG_LEVEL") or log_conf.get("level", "INFO")
        self.log_dir = os.path.join(PROJECT_ROOT, log_conf.get("dir", "reports/logs"))


def get_config() -> Config:
    """全局唯一配置入口。第一次调用读文件，之后直接返回缓存。"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
