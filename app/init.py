# -*- coding: utf-8 -*-

import os
import yaml
import sys
import shutil
import subprocess
from typing import Optional
from app.core.open_115 import OpenAPI_115


# 模块路径现在通过 Dockerfile 中的 PYTHONPATH 环境变量设置
# 为了兼容本地开发，添加后备路径设置
def _ensure_module_paths():
    """
    确保模块路径可用，主要用于本地开发环境
    在 Docker 环境中，PYTHONPATH 已通过环境变量设置
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    required_paths = [current_dir, os.path.dirname(current_dir)]

    for path in required_paths:
        if path not in sys.path:
            sys.path.insert(0, path)

# 执行路径检查
_ensure_module_paths()

from app.utils.logger import Logger
from app.utils.sqlitelib import *


def _load_dotenv():
    """本地开发时从项目根目录的 .env 加载环境变量，不覆盖已有值。Docker 环境中文件不存在则静默跳过。"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(root, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val

_load_dotenv()

# 调试模式。本地开发用 TG115_DEBUG=1 时读取项目内 config/tmp/app 路径。
debug_mode = os.getenv("TG115_DEBUG", "").lower() in ("1", "true", "yes", "on")

# 全局日志
logger:Optional[Logger] = None

# 全局配置
bot_config = dict()

# 115开放API对象
openapi_115 = None

# TG用户客户端（占位，video_handler 需要此引用做 None 判断）
tg_user_client = None

# 爬取状态
CRAWL_SEHUA_STATUS = 0  # 涩花爬取状态


# yaml配置文件
CONFIG_FILE = "/config/config.yaml"
# yaml配置文件示例
CONFIG_FILE_EXAMPLE = "/config/config.yaml.example"
# SessionFile
TG_SESSION_FILE = "/config/user_session.session"
# DB File
DB_FILE = "/config/db.db"
# APP path
APP = "/app"
# Config path
CONFIG = "/config"
# Temp path
TEMP = "/tmp"
IMAGE_PATH = "/app/images"

def _get_system_chrome_version():
    """获取系统安装的 Chrome/Chromium 版本"""
    try:
        # 1. 尝试获取 google-chrome-stable 版本
        res = subprocess.run(['google-chrome-stable', '--version'], capture_output=True, text=True, check=False)
        if res.returncode == 0:
             # Output: "Google Chrome 121.0.6167.85"
            return res.stdout.strip().split()[-1]

        # 2. 尝试获取 chromium 版本
        res = subprocess.run(['chromium', '--version'], capture_output=True, text=True, check=False)
        if res.returncode == 0:
            # Output: "Chromium 121.0.6167.85 ..."
            return res.stdout.strip().split()[-1]
    except Exception:
        pass
    return "143.0.0.0"  # Fallback version

# 动态获取当前环境 Chrome 版本生成 User-Agent
_chrome_ver = _get_system_chrome_version()
USER_AGENT = f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_chrome_ver} Safari/537.36"

# 调试用
if debug_mode:
    CONFIG_FILE = "config/config.yaml"
    CONFIG_FILE_EXAMPLE = "config/config.yaml.example"
    TG_SESSION_FILE = "config/user_session.session"
    DB_FILE = "config/db.db"
    APP = "app"
    CONFIG = "config"
    TEMP = "tmp"
    IMAGE_PATH = "app/images"


def create_logger():
    """
    创建全局日志对象
    :return:
    """
    global logger
    import logging
    from typing import Dict
    # 日志级别映射字典
    LOG_LEVEL_MAP: Dict[str, int] = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    log_level = bot_config.get('log_level', 'info').lower()
    log_level = LOG_LEVEL_MAP.get(log_level, logging.INFO)
    logger = Logger(level=log_level, debug_model=debug_mode)
    logger.info("Logger init success!")


def load_yaml_config():
    """
    读取配置文件
    :return:
    """
    global bot_config, CONFIG_FILE, CONFIG_FILE_EXAMPLE, APP
    yaml_path = CONFIG_FILE

    example_config_path = f"{APP}/config.yaml.example"
    # 尝试更新示例配置文件
    try:
        shutil.copy2(example_config_path, CONFIG_FILE_EXAMPLE)
    except Exception as e:
        print(f"Update config example file failed: {e}")

    # 获取yaml文件名称
    try:
        # 获取yaml文件路径
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r', encoding='utf-8') as f:
                cfg = f.read()
                f.close()
            bot_config = yaml.load(cfg, Loader=yaml.FullLoader)
        else:
            if os.path.exists(example_config_path):
                # 确保目标目录存在
                os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
                # 复制示例配置文件
                shutil.copy2(example_config_path, yaml_path)
                print(f"已复制示例配置文件到 {yaml_path}")
                # 重新读取配置文件
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    cfg = f.read()
                    f.close()
                bot_config = yaml.load(cfg, Loader=yaml.FullLoader)
            else:
                print("Config example file not found!")
    except Exception as e:
        print(f"配置文件[{yaml_path}]格式有误，请检查!")


def get_bot_token():
    global CONFIG_FILE, bot_config
    bot_token = ""
    if 'bot_token' in bot_config.keys():
        bot_token = bot_config['bot_token']
    else:
        yaml_path = CONFIG_FILE
        if os.path.exists(yaml_path):
            with open(yaml_path, 'r', encoding='utf-8') as f:
                cfg = f.read()
                f.close()
            bot_config = yaml.load(cfg, Loader=yaml.FullLoader)
            bot_token = bot_config['bot_token']
        return bot_token

def save_tokens_to_config(access_token: str, refresh_token: str):
    """将 access_token / refresh_token 写入 bot_config 并持久化到 config.yaml。
    用逐行替换而非整体 dump，保持文件其余内容和格式不变。"""
    import re
    global bot_config
    bot_config['access_token'] = access_token
    bot_config['refresh_token'] = refresh_token
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        for key, val in (('access_token', access_token), ('refresh_token', refresh_token)):
            # 匹配 "key: 任意值（到行尾）"，替换为带引号的新值
            content = re.sub(
                rf'^{key}:.*$',
                f'{key}: "{val}"',
                content,
                flags=re.MULTILINE,
            )
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        if logger:
            logger.info("Tokens saved to config.yaml")
    except Exception as e:
        if logger:
            logger.error(f"保存token到config.yaml失败: {e}")


def create_tmp():
    if not os.path.exists(TEMP):
        os.mkdir(TEMP, mode=0o777)
        os.chmod(TEMP, 0o777)

def initialize_115open():
    """
    初始化115开放API客户端
    :return: bool - 初始化是否成功
    """
    global openapi_115, logger
    try:
        openapi_115 = OpenAPI_115()
        # 检查是否成功获取到token
        if openapi_115.access_token and openapi_115.refresh_token:
            user_info = openapi_115.get_user_info()
            if not user_info:
                logger.error("115 OpenAPI客户端初始化失败: OpenAPI测试失败！")
                openapi_115 = None
                return False
            logger.info("115 OpenAPI客户端初始化成功")
            return True
        else:
            logger.error("115 OpenAPI客户端初始化失败: 无法获取有效的token")
            openapi_115 = None
            return False
    except Exception as e:
        logger.error(f"115 OpenAPI客户端初始化失败: {e}")
        openapi_115 = None
        return False


def check_user(user_id):
    global bot_config
    if isinstance(bot_config.get('allowed_user'), int):
        if user_id == bot_config['allowed_user']:
            return True
    if isinstance(bot_config.get('allowed_user'), str):
        if str(user_id) == bot_config['allowed_user']:
            return True
    return False

def init_db():
    with SqlLiteLib() as sqlite:
        # 创建表（如果不存在）
        # create_table_query = '''
        # CREATE TABLE IF NOT EXISTS subscribe (
        #     id INTEGER PRIMARY KEY AUTOINCREMENT,
        #     actor_name TEXT, -- 演员名称
        #     actor_id TEXT, -- 演员ID
        #     number TEXT, -- 相关编号
        #     pub_date DATETIME, -- 发布时间
        #     title TEXT, -- 标题
        #     post_url TEXT, -- 封面URL
        #     is_download TINYINT DEFAULT 0, -- 是否下载, 0或1, 默认0
        #     score REAL,
        #     magnet TEXT,
        #     sub_user INTEGER,
        #     pub_url TEXT,
        #     created_at DATETIME DEFAULT CURRENT_TIMESTAMP -- 创建时间，默认当前时间
        # );
        # '''
        # sqlite.execute_sql(create_table_query)
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS offline_task (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, -- 任务标题
            save_path TEXT, -- 保存路径
            magnet TEXT, -- 磁力链接
            is_download TINYINT DEFAULT 0, -- 是否下载, 0或1, 默认0
            retry_count INTEGER DEFAULT 1, -- 重试次数
            completed_at DATETIME, -- 完成时间
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP -- 创建时间，默认当前时间
        );
        '''
        sqlite.execute_sql(create_table_query)

        create_table_query = """
        CREATE TABLE IF NOT EXISTS av_daily_update (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            av_number TEXT, -- 番号
            publish_date DATETIME, -- 发布时间
            title TEXT, -- 标题
            post_url TEXT, -- 封面URL
            pub_url TEXT, -- 发布链接
            magnet TEXT, -- 磁力链接
            is_download TINYINT DEFAULT 0, -- 是否下载, 0或1, 默认0
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP -- 创建时间，默认当前时间
        );
        """
        sqlite.execute_sql(create_table_query)

        create_table_query = '''
        CREATE TABLE IF NOT EXISTS sub_movie (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_name TEXT, -- 电影名称
            tmdb_id INTEGER, -- TMDB ID
            size TEXT, -- 文件大小
            category_folder TEXT, -- 分类文件夹
            is_download TINYINT DEFAULT 0, -- 是否下载, 0或1, 默认0
            download_url TEXT,  -- 下载链接, magnet, ed2k, 115share
            sub_user INTEGER,
            post_url TEXT, -- 封面URL
            is_delete TINYINT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP -- 创建时间，默认当前时间
        );
        '''
        sqlite.execute_sql(create_table_query)

        create_table_query = '''
        CREATE TABLE IF NOT EXISTS sehua_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_name TEXT, -- 版块名称
            av_number TEXT, -- 番号
            title TEXT, -- 标题
            movie_type TEXT, -- 有码|无码
            size TEXT, -- 文件大小
            magnet TEXT, -- 磁力链接
            post_url TEXT, -- 封面url
            publish_date DATETIME, -- 发布时间
            pub_url TEXT, -- 资源链接
            image_path TEXT, -- 图片本地路径
            save_path TEXT, -- 保存路径
            is_download TINYINT DEFAULT 0, -- 0=未提交 1=已提交离线 2=115下载完成+后处理完成
            submitted_at DATETIME, -- 提交离线时间
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP -- 创建时间，默认当前时间
        );
        '''
        sqlite.execute_sql(create_table_query)

        create_table_query = '''
        CREATE TABLE IF NOT EXISTS t66y (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_name TEXT, -- 版块名称
            movie_info TEXT, -- 影片信息
            title TEXT, -- 标题
            magnet TEXT, -- 磁力链接
            poster_url TEXT, -- 封面url
            publish_date DATE, -- 发布日期
            pub_url TEXT, -- 资源链接
            save_path TEXT, -- 保存路径
            is_download TINYINT DEFAULT 0, -- 是否下载, 0或1, 默认0
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP -- 创建时间，默认当前时间
        );
        '''
        sqlite.execute_sql(create_table_query)

        create_table_query = '''
        CREATE TABLE IF NOT EXISTS javbus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            av_number TEXT, -- 番号
            actress TEXT, -- 演员，多个演员逗号分隔
            sub_category TEXT, -- 订阅类别
            movie_info TEXT, -- 影片信息
            title TEXT, -- 标题
            magnet TEXT, -- 磁力链接
            poster_url TEXT, -- 封面url
            publish_date DATE, -- 发布日期
            pub_url TEXT, -- 资源链接
            save_path TEXT, -- 保存路径
            is_download TINYINT DEFAULT 0, -- 是否下载, 0或1, 默认0
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP -- 创建时间，默认当前时间
        );
        '''
        sqlite.execute_sql(create_table_query)
        logger.info("init DataBase success.")


def init_log():
    create_logger()


def init():
    global bot_config, logger
    load_yaml_config()
    create_logger()
    create_tmp()
    init_db()

if __name__ == "__main__":
    load_yaml_config()
