# -*- coding: utf-8 -*-

from pathlib import Path
import requests
import init


def create_strm_file(new_name, file_list):
    strm_mode = init.bot_config.get('strm_mode', 'disable')
    if strm_mode == "disable":
        return
    try:
        cd2_mount_root = Path(init.bot_config.get('mount_root', '/CloudNAS/115'))
        strm_root = Path(init.bot_config.get('strm_root', '/media/115'))

        relative_path = Path(new_name).relative_to(Path(new_name).anchor)
        cd2_mount_path = cd2_mount_root.joinpath(relative_path)
        strm_path = strm_root.joinpath(relative_path)

        if not strm_path.exists():
            strm_path.mkdir(parents=True, exist_ok=True)

        for file in file_list:
            target_file = strm_path / (Path(file).stem + ".strm")
            if strm_mode == "strm_local":
                mkv_file = cd2_mount_path / file
            else:
                mkv_file = Path(init.bot_config.get('openlist_root', '/115')) / relative_path / (Path(file))
            with target_file.open('w', encoding='utf-8') as f:
                f.write(str(mkv_file))
                init.logger.info(f"strm文件创建成功，{target_file} -> {mkv_file}")
    except Exception as e:
        init.logger.info(f"Error creating .strm files: {e}")


def notice_emby_scan_library(path):
    strm_root = Path(init.bot_config.get("strm_root", ""))
    if not strm_root:
        init.logger.warn("未设置strm_root，无法扫库！")
        return False
    relative_path = Path(path).relative_to(Path(path).anchor)
    movie_path_in_emby = strm_root / relative_path
    emby_server = init.bot_config['emby_server']
    api_key = init.bot_config['api_key']
    if api_key is None or api_key.strip() == "" or api_key.strip().lower() == "your_api_key":
        init.logger.warn("Emby API Key 未配置，跳过通知Emby扫库")
        return False
    if str(emby_server).endswith("/"):
        emby_server = emby_server[:-1]
    url = f"{emby_server}/Library/Media/Updated"
    headers = {
        "accept": "*/*",
        "X-Emby-Token": api_key,
        "Content-Type": "application/json"
    }
    data = {
        "Updates": [
            {
                "Path": str(movie_path_in_emby),
                "UpdateType": "Created"
            }
        ]
    }
    emby_response = requests.post(url, headers=headers, json=data)
    if emby_response.text == "":
        init.logger.info("通知Emby扫库成功！")
        return True
    else:
        init.logger.error(f"通知Emby扫库失败：{emby_response}")
        return False
