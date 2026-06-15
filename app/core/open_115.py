import requests
import os
import base64
import hashlib
import re
import sys
import threading
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
sys.path.append(current_dir)
import init
import qrcode
import json
import time
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
from functools import wraps
from app.utils.message_queue import add_task_to_queue
from app.utils.alioss import upload_file_to_oss
from telegram.helpers import escape_markdown

RISK_THRESHOLD = 0.95

def handle_token_expiry(func):
    """装饰器：统一处理API调用中的token过期情况"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        max_retries = 2  # 最大重试次数
        for attempt in range(max_retries):
            try:
                # 调用原始函数，获取HTTP响应
                response = func(self, *args, **kwargs)
                
                # 检查响应是否是字典且包含错误码
                if isinstance(response, dict) and 'code' in response:
                    if response['code'] == 40140125:
                        # token需要刷新
                        if attempt < max_retries - 1:  # 还有重试机会
                            init.logger.info("Token需要刷新，正在重试...")
                            try:
                                self.refresh_access_token()
                            except Exception as refresh_err:
                                init.logger.warn(f"Token刷新失败，放弃重试: {refresh_err}")
                                return response
                            continue
                        else:
                            init.logger.warn("Token刷新后仍然失败")
                            return response
                    elif response['code'] in [40140116, 40140119]:
                        # token已过期，需要重新授权
                        init.logger.warn("Access token 已过期，请重新授权！")
                        return response
                    elif response['code'] == 40140118:
                        init.logger.warn("开发者认证已过期，请到115开放平台重新授权！")
                        return response
                    elif response['code'] == 40140110:
                        init.logger.warn("应用已过期，请到115开放平台重新授权！")
                        return response
                    elif response['code'] == 40140109:
                        init.logger.warn("应用被停用，请到115开放平台查询详细信息！")
                        return response
                    elif response['code'] == 40140108:
                        init.logger.warn("应用审核未通过，请稍后再试！")
                        return response
                
                # 成功或其他情况，直接返回
                return response
                
            except Exception as e:
                init.logger.warn(f"API调用最终失败: {e}")
                raise
        
        return response
    return wrapper


class OpenAPI_115:
    def __init__(self):
        self.access_token = ""
        self.refresh_token = ""
        self.base_url = "https://proapi.115.com"
        self.lifetime_vip = False
        self.request_count = 0
        self.lock = threading.Lock()
        self.refresh_lock = threading.Lock()
        self.last_req_time = 0
        self.file_info_cache = {}
        self.cache_hit = 0
        self.get_token()  # 初始化时获取token
        
    def get_token(self):
        if not self.refresh_token or not self.access_token:
            app_id = init.bot_config.get('115_app_id')
            _access_token = init.bot_config.get('access_token', '')
            _refresh_token = init.bot_config.get('refresh_token', '')
            if _access_token and _refresh_token and \
               _access_token.lower() not in ('', 'your_access_token') and \
               _refresh_token.lower() not in ('', 'your_refresh_token'):
                self.access_token = _access_token
                self.refresh_token = _refresh_token
                init.logger.info("使用配置文件中的access_token和refresh_token")
            elif app_id and str(app_id).lower() not in ('', 'your_115_app_id'):
                init.logger.info("正在进入PKCE授权流程，获取refresh_token...")
                self.auth_pkce(init.get_allowed_user(), app_id)
        
        
    def auth_pkce(self, sub_user, app_id):
        header = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": init.USER_AGENT
        }
        verifier, challenge = self.get_challenge()
        data = {
            "client_id": app_id,
            "code_challenge": challenge,
            "code_challenge_method": "sha256"
        }
        response = requests.post(f"https://passportapi.115.com/open/authDeviceCode", headers=header, data=data)
        res = response.json()
        if response.status_code == 200:
            uid = res['data']['uid']
            check_time = res['data']['time']
            qr_data = res['data']['qrcode']
            sign = res['data']['sign']
        else:
            init.logger.warn(f"获取二维码失败: {response.status_code} - {response.text}")
            raise Exception(f"Error: {response.status_code} - {response.text}")
        
        # 2. 创建QRCode对象并生成图片
        qr = qrcode.QRCode(
            version=1,               # 控制大小（1~40，默认为自动）
            error_correction=qrcode.constants.ERROR_CORRECT_L,  # 容错率（L/M/Q/H）
            box_size=10,             # 每个模块的像素大小
            border=4,                # 边框宽度（模块数）
        )
        qr.add_data(qr_data)        # 添加文本数据
        qr.make(fit=True)           # 自动调整版本

        # 3. 生成图片并保存为文件
        img = qr.make_image(fill_color="black", back_color="white")
        save_path= f"{init.IMAGE_PATH}/qrcode.png"
        if os.path.exists(save_path):
            os.remove(save_path)
        img.save(save_path)      # 保存为PNG
        
        add_task_to_queue(sub_user, save_path, "请用115APP扫码授权！")
        
        time.sleep(5)
        params = {
            "uid": uid,
            "time": check_time,
            "sign": sign
        }
        while True:
            response = requests.get(f"https://qrcodeapi.115.com/get/status/", params=params)
            if response.status_code == 200:
                res = response.json()
                if res['state'] == 0:
                    init.logger.info("二维码已失效...")
                    break
                else:
                    if res['data'].get('status', None) is None:
                        init.logger.info("等待扫码...")
                        time.sleep(2)
                        continue
                    # 1.扫码成功，等待确认
                    if res['data']['status'] == 1:
                        time.sleep(1)
                        continue
                    elif res['data']['status'] == 2:
                        # 2.扫码成功，获取access_token
                        init.logger.info("二维码扫码成功，正在获取access_token...")
                        time.sleep(1)
                        response = requests.post("https://passportapi.115.com/open/deviceCodeToToken", headers=header, data={
                            "uid": uid,
                            "code_verifier": verifier
                        })
                        res = response.json()
                        if response.status_code == 200 and 'data' in res:
                            self.access_token = res['data']['access_token']
                            self.refresh_token = res['data']['refresh_token']
                            self.expires_in = res['data']['expires_in']
                            init.logger.info("access_token获取成功！")
                            init.save_tokens_to_config(self.access_token, self.refresh_token)
                            break
              
                        
    def auth_pkce_get_qr(self, app_id: str) -> dict:
        """发起PKCE授权，返回二维码base64图片及轮询所需参数，供Web UI调用"""
        import io
        header = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": init.USER_AGENT,
        }
        verifier, challenge = self.get_challenge()
        data = {
            "client_id": app_id,
            "code_challenge": challenge,
            "code_challenge_method": "sha256",
        }
        response = requests.post("https://passportapi.115.com/open/authDeviceCode", headers=header, data=data)
        res = response.json()
        if response.status_code != 200:
            raise Exception(f"获取二维码失败: {response.status_code} - {response.text}")

        uid = res["data"]["uid"]
        check_time = res["data"]["time"]
        qr_data = res["data"]["qrcode"]
        sign = res["data"]["sign"]

        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()

        return {
            "qr_b64": qr_b64,
            "uid": uid,
            "time": check_time,
            "sign": sign,
            "verifier": verifier,
            "app_id": app_id,
        }

    def auth_pkce_poll(self, uid: str, check_time: int, sign: str, verifier: str, app_id: str) -> dict:
        """轮询一次二维码扫码状态，返回 {status, done, message}，供Web UI SSE逐步调用"""
        params = {"uid": uid, "time": check_time, "sign": sign}
        response = requests.get("https://qrcodeapi.115.com/get/status/", params=params, timeout=10)
        if response.status_code != 200:
            return {"status": "error", "done": True, "message": f"轮询失败: {response.status_code}"}

        res = response.json()
        if res["state"] == 0:
            return {"status": "expired", "done": True, "message": "二维码已失效"}

        scan_status = res["data"].get("status") if res.get("data") else None
        if scan_status is None:
            return {"status": "waiting", "done": False, "message": "等待扫码..."}
        if scan_status == 1:
            return {"status": "scanned", "done": False, "message": "已扫码，等待确认..."}
        if scan_status == 2:
            header = {"Content-Type": "application/x-www-form-urlencoded", "User-Agent": init.USER_AGENT}
            r = requests.post(
                "https://passportapi.115.com/open/deviceCodeToToken",
                headers=header,
                data={"uid": uid, "code_verifier": verifier},
                timeout=10,
            )
            r_data = r.json()
            if r.status_code == 200 and "data" in r_data:
                access_token = r_data["data"]["access_token"]
                refresh_token = r_data["data"]["refresh_token"]
                self.access_token = access_token
                self.refresh_token = refresh_token
                init.save_tokens_to_config(access_token, refresh_token)
                return {"status": "success", "done": True, "message": "授权成功！"}
            return {"status": "error", "done": True, "message": "获取token失败"}

        return {"status": "waiting", "done": False, "message": "等待扫码..."}

    def _load_token_from_file(self):
        return (
            init.bot_config.get('access_token', ''),
            init.bot_config.get('refresh_token', ''),
        )

    def refresh_access_token(self):
        with self.refresh_lock:
            # 进锁后先检查文件：若其他线程已刷新完毕，直接用新 token，不重复请求
            file_access_token, file_refresh_token = self._load_token_from_file()
            if file_refresh_token and file_refresh_token != self.refresh_token:
                init.logger.info("发现本地Token文件已更新，加载新Token...")
                self.access_token = file_access_token
                self.refresh_token = file_refresh_token
                return

            if not self.refresh_token:
                if not file_refresh_token:
                    init.logger.warn("请先进行授权，获取refresh_token！")
                    add_task_to_queue(init.get_allowed_user(), "/app/images/male023.png", "请先进行授权，获取refresh_token！")
                    return
                self.access_token = file_access_token
                self.refresh_token = file_refresh_token

            header = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": init.USER_AGENT
            }
            url = "https://passportapi.115.com/open/refreshToken"
            data = {"refresh_token": self.refresh_token}

            try:
                response = requests.post(url, headers=header, data=data)
                res = response.json()
            except Exception as e:
                init.logger.warn(f"刷新Token请求异常: {e}")
                raise

            if response.status_code == 200 and isinstance(res, dict) and res.get('state'):
                token_data = res.get('data')
                if isinstance(token_data, dict) and token_data.get('access_token'):
                    self.access_token = token_data['access_token']
                    self.refresh_token = token_data['refresh_token']
                    init.save_tokens_to_config(self.access_token, self.refresh_token)
                    init.logger.info("Access token 更新成功.")
                else:
                    init.logger.warn(f"Access token 更新失败: 响应数据异常 - {res}")
                    raise Exception(f"Failed to refresh access token: invalid data format")
            else:
                init.logger.warn(f"Access token 更新失败: {res}")
                raise Exception(f"Failed to refresh access token: {res.get('message', 'unknown error')}")
        

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": init.USER_AGENT
        }

    def _make_api_request(self, method: str, url: str, params=None, data=None, headers=None):
        """统一的API请求方法"""
        with self.lock:
            # 1. 检查风控计数
            if self.check_risk():
                return {"code": -1, "message": "今日请求即将到达上限！请明日再试！"}
            
            # 2. 智能流控：确保请求间隔至少 0.5s (即最大 2 QPS)
            min_interval = 0.5
            current_time = time.time()
            elapsed = current_time - self.last_req_time
            
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            
            self.last_req_time = time.time()
            
            if headers is None:
                headers = self._get_headers()
        
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, data=data)
        else:
            raise ValueError(f"不支持的HTTP方法: {method}")
        if response.status_code == 200:
            return response.json()
        else:
            init.logger.warn(f"API请求失败: {response.status_code} - {response.text}")
            return {"code": response.status_code, "message": response.text}
    
    @handle_token_expiry
    def get_file_info(self, path: str):
        # 优先从缓存获取
        if path in self.file_info_cache:
            data = self.file_info_cache[path]
            # 直接从缓存中获取
            init.logger.debug(f"Cache hit for {path}")
            self.cache_hit += 1
            return data


        url = f"{self.base_url}/open/folder/get_info"
        params = {"path": path}
        response = self._make_api_request('GET', url, params=params)
        
        # 如果成功获取文件信息，记录日志
        if isinstance(response, dict) and response.get('code') == 0:
            init.logger.debug(f"获取文件信息成功: {response}")
            # 更新缓存
            self.file_info_cache[path] = (response['data'])
            return response['data']
        else:
            init.logger.warn(f"获取文件信息失败: {response}")
            if response['code'] == 40140125:
                return response
            return None
        
    @handle_token_expiry
    def get_file_info_by_id(self, file_id: str):
        url = f"{self.base_url}/open/folder/get_info"
        params = {"file_id": file_id}
        response = self._make_api_request('GET', url, params=params)
        
        # 如果成功获取文件信息，记录日志
        if isinstance(response, dict) and response.get('code') == 0:
            init.logger.debug(f"获取文件信息成功: {response}")
            return response['data']
        else:
            init.logger.warn(f"获取文件信息失败: {response}")
            if response['code'] == 40140125:
                return response
            return None
    
    @handle_token_expiry
    def offline_download(self, download_url):
        url = f"{self.base_url}/open/offline/add_task_urls"
        file_info = self.get_file_info(init.bot_config['offline_path'])
        if not file_info:
            init.logger.warn(f"获取离线下载目录信息失败: {file_info}")
            return False
        
        data = {
            "urls": download_url,
            "wp_path_id": file_info['file_id']
        }
        response = self._make_api_request('POST', url, data=data, headers=self._get_headers())
        if response['state'] == True:
            init.logger.info(f"离线下载任务添加成功: {response['message']}")
            return True
        else:
            init.logger.warn(f"离线下载任务添加失败: {response['message']}")
            if response['code'] == 40140125:
                return response
            return None
    
    @handle_token_expiry
    def offline_download_specify_path(self, download_url, save_path):
        save_path = os.path.normpath(save_path)
        url = f"{self.base_url}/open/offline/add_task_urls"
        file_info = self.get_file_info(save_path)
        
        if not file_info:
            created_info = self.create_dir_recursive(save_path)
            if created_info:
                file_info = created_info
            
            # Create directory might have lag, retry getting info
            if not file_info:
                for _ in range(3):
                    file_info = self.get_file_info(save_path)
                    if file_info:
                        break
                    time.sleep(2)
        
        data = {
            "urls": download_url,
            "wp_path_id": file_info['file_id']
        }
        response = self._make_api_request('POST', url, data=data, headers=self._get_headers())
        if response['state'] == True:
            init.logger.info(f"离线下载任务添加成功: {response}")
            return True
        else:
            if response['code'] == 40140125:
                return response
            init.logger.warn(f"离线下载任务添加失败: {response['message']}")
            raise Exception(response['message'])

    # @handle_token_expiry
    def get_offline_tasks_by_page(self, page=1):
        url = f"{self.base_url}/open/offline/get_task_list"
        params = {"page": page}
        response = self._make_api_request('GET', url, params=params)
        if isinstance(response, dict) and response.get('code') == 0 and 'data' in response:
            return response['data'] 
        else:
            init.logger.warn(f"获取离线下载任务列表失败: {response}")
            if isinstance(response, dict) and response.get('code') == 40140125:
                if response['code'] == 40140125:
                    return response
            return None
    
    @handle_token_expiry
    def get_offline_tasks(self):
        url = f"{self.base_url}/open/offline/get_task_list"
        response = self._make_api_request('GET', url)
        task_list = []
        if isinstance(response, dict) and response.get('code') == 0 and 'data' in response:
            page_count = response['data'].get('page_count', 1)
            for i in range(1, page_count + 1):
                tasks = self.get_offline_tasks_by_page(i)
                if tasks and 'tasks' in tasks:
                    for task in tasks['tasks']:
                        task_list.append({
                            'name': task['name'],
                            'url': task['url'],
                            'status': task['status'],
                            'percentDone': task['percentDone'],
                            'info_hash': task['info_hash'],
                            'file_id': task['file_id'],               # 最终目录id
                            'wp_path_id': task['wp_path_id'],         # 下载目录id
                            'delete_file_id': task['delete_file_id']  # 同file_id
                        })
                time.sleep(2)  # 避免请求过快
            return task_list  
        else:
            init.logger.warn(f"获取离线下载任务列表失败: {response}")
            if isinstance(response, dict) and response.get('code') == 40140125:
                if response['code'] == 40140125:
                    return response
            return None
    
    
    @handle_token_expiry
    def del_offline_task(self, info_hash, del_source_file=1):
        url = f"{self.base_url}/open/offline/del_task"
        data = {
            "info_hash": info_hash,
            "del_source_file": del_source_file
        }
        response = self._make_api_request('POST', url, data=data, headers=self._get_headers())
        if response['state'] == True:
            if del_source_file == 1:
                init.logger.info(f"清理失败的离线下载任务成功!")
            else:
                init.logger.info(f"清理已完成的云端任务成功!")
            return True
        else:
            init.logger.warn(f"清理离线下载任务失败: {response['message']}")
            if response['code'] == 40140125:
                return response
            return None
        
    @handle_token_expiry
    def copy_file(self, source_path, target_path, nodupli=1):
        """复制文件或目录"""
        src_file_info = self.get_file_info(source_path)
        if not src_file_info:
            init.logger.warn(f"获取源文件信息失败: {src_file_info}")
            return False

        dst_file_info = self.get_file_info(target_path)
        if not dst_file_info:
            init.logger.warn(f"获取目标文件信息失败: {dst_file_info}")
            return False

        file_id = src_file_info['file_id']
        to_cid = dst_file_info['file_id']
        url = f"{self.base_url}/open/ufile/copy"
        data = {
            "pid": to_cid,
            "file_id": file_id,
            "nodupli": nodupli
        }
        response = self._make_api_request('POST', url, data=data, headers=self._get_headers())
        if response['state'] == True:
            init.logger.info(f"文件复制成功: [{source_path}] -> [{target_path}]")
            return True
        else:
            init.logger.warn(f"文件复制失败: {response['message']}")
            if response['code'] == 40140125:
                return response
        return None
    
    @handle_token_expiry      
    def rename(self, old_name, new_name):
        """重命名文件或目录"""
        file_info = self.get_file_info(old_name)
        if not file_info:
            init.logger.warn(f"获取文件信息失败: {file_info}")
            return False
        
        file_id = file_info['file_id']
        url = f"{self.base_url}/open/ufile/update"
        data = {
            "file_id": file_id,
            "file_name": new_name
        }
        response = self._make_api_request('POST', url, data=data, headers=self._get_headers())
        if response['state'] == True:
            init.logger.info(f"文件重命名成功: [{old_name}] -> [{new_name}]")
            
            # 1. 清除旧名称缓存
            if old_name in self.file_info_cache:
                del self.file_info_cache[old_name]
            
            # 2. 关键修复：清除新名称可能存在的全部缓存
            # 避免因缓存了旧同名目录的ID，导致get_files_from_dir获取到错误的文件列表
            try:
                # 获取父目录
                parent_dir = str(Path(old_name).parent)
                full_new_path = f"{parent_dir}/{new_name}"
                
                # 如果新路径在缓存中（可能是旧的ID），必须清除
                if full_new_path in self.file_info_cache:
                    init.logger.info(f"发现新名称[{full_new_path}]的脏缓存，正在清除...")
                    del self.file_info_cache[full_new_path]
            except Exception as e:
                init.logger.warn(f"清除新名称缓存异常: {e}")
                
            return True
        else:
            init.logger.warn(f"文件重命名失败: {response['message']}")
            if response['code'] == 40140125:
                return response
            return None
        
    @handle_token_expiry
    def rename_by_id(self, file_id, old_name, new_name):
        """重命名文件或目录"""
        url = f"{self.base_url}/open/ufile/update"
        data = {
            "file_id": file_id,
            "file_name": new_name
        }
        response = self._make_api_request('POST', url, data=data, headers=self._get_headers())
        if response['state'] == True:
            init.logger.info(f"文件重命名成功: [{old_name}] -> [{new_name}]")
            
            # 1. 清除旧名称缓存
            if old_name in self.file_info_cache:
                del self.file_info_cache[old_name]
            
            # 2. 清除新名称缓存（防止脏数据）
            try:
                # 尝试推断父目录（虽然rename_by_id不一定能准确拿到父path，但如果有old_name是全路径则可以）
                if "/" in old_name:
                    parent_dir = str(Path(old_name).parent)
                    full_new_path = f"{parent_dir}/{new_name}"
                    if full_new_path in self.file_info_cache:
                        init.logger.info(f"同时清除新名称[{full_new_path}]的缓存")
                        del self.file_info_cache[full_new_path]
            except Exception as e:
                init.logger.warn(f"清除新名称缓存异常: {e}")
                
            return True
        else:
            init.logger.warn(f"文件重命名失败: {response['message']}")
            if response['code'] == 40140125:
                return response
            return None
            
    @handle_token_expiry
    def get_file_list(self, params):
        """获取指定目录下的所有文件"""
        url = f"{self.base_url}/open/ufile/files"
        response = self._make_api_request('GET', url, params=params, headers=self._get_headers())
        
        if isinstance(response, dict) and response.get('code') == 0:
            init.logger.debug(f"获取文件列表成功: {response}")
            return response['data']
        else:
            init.logger.warn(f"获取文件列表失败: {response}")
            if response['code'] == 40140125:
                return response
            return None
        
    @handle_token_expiry
    def create_directory(self, pid, file_name):
        """创建目录"""
        url = f"{self.base_url}/open/folder/add"
        # 恢复使用 file_name，因为之前是工作的
        data = {
            "pid": pid,
            "file_name": file_name,
        }
        response = self._make_api_request('POST', url, data=data, headers=self._get_headers())
        
        # 兼容两种判断方式
        if isinstance(response, dict) and (response.get('state') == True or response.get('code') == 0):
            init.logger.info(f"目录创建成功: {file_name}")
            
            # 刷新可能存在的缓存：
            # 1. 如果我们能根据 pid 反推父目录路径，应该清理父目录路径下 file_name 的缓存
            #    但这里只有 pid，很难反推路径。只能假设调用方会重新获取。
            # 2. 如果之前尝试访问过该目录但失败（虽然我们目前没缓存失败结果），
            #    或者该目录曾存在->删除->重建，那么缓存中的旧 ID 必须清除。
            #    由于无法根据 pid 轻易拼出完整路径，这里无法像 rename 那样精确清除。
            #    建议调用 create_directory 的地方，如果涉及到完整路径的缓存，手动清除。
            
            return response.get('data') or True
        elif response.get('code') == 20004:
            init.logger.info(f"目录已存在: {file_name}")
            return True
        else:
            init.logger.warn(f"目录创建失败: {response}")
            if response['code'] == 40140125:
                return response
            return None
        
    @handle_token_expiry
    def delet_file(self, file_ids):
        """删除文件或目录"""
        url = f"{self.base_url}/open/ufile/delete"
        data = {
            "file_ids": file_ids
        }
        response = self._make_api_request('POST', url, data=data, headers=self._get_headers())
        if response['state'] == True:
            init.logger.info(f"文件或目录删除成功: {file_ids}")
            return True
        else:
            init.logger.warn(f"文件或目录删除失败: {response}")
            if response['code'] == 40140125:
                return response
            return None
    
    def _batch_delete_files(self, fid_list, batch_size=100):
        """分批删除文件，避免单次请求过长
        
        Args:
            fid_list: 文件ID列表
            batch_size: 每批删除的文件数量，默认100
        """
        if not fid_list:
            return
            
        total_files = len(fid_list)
        init.logger.info(f"准备分批删除 {total_files} 个文件，每批 {batch_size} 个")
        
        # 分批处理
        for i in range(0, total_files, batch_size):
            batch = fid_list[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_files + batch_size - 1) // batch_size
            
            init.logger.info(f"正在执行第 {batch_num}/{total_batches} 批删除操作，共 {len(batch)} 个文件")
            
            file_ids = ",".join(batch)
            result = self.delet_file(file_ids)
            
            if result is True:
                init.logger.info(f"第 {batch_num} 批删除成功")
            else:
                init.logger.warn(f"第 {batch_num} 批删除失败: {result}")
            
            # 批次间添加短暂延迟，避免请求过快
            if i + batch_size < total_files:
                time.sleep(1)
        # 等待服务器处理删除请求
        time.sleep(10)
        
    @handle_token_expiry
    def delete_single_file(self, path):
        """删除单个文件"""
        file_info = self.get_file_info(path)
        if not file_info:
            return None
        file_id = file_info['file_id']
        url = f"{self.base_url}/open/ufile/delete"
        data = {
            "file_ids": file_id
        }
        response = self._make_api_request('POST', url, data=data, headers=self._get_headers())
        if response['state'] == True:
            init.logger.info(f"文件(夹)删除成功: {path}")
            if path in self.file_info_cache:
                del self.file_info_cache[path]
            return True
        else:
            init.logger.warn(f"文件(夹)删除失败: {response['message']}")
            if response['code'] == 40140125:
                return response
            return None

    @handle_token_expiry
    def upload_file(self, **kwargs):
        """上传文件"""
        target = kwargs.get('target') 
        file_info = self.get_file_info(target)
        if not file_info:
            init.logger.warn(f"获取目标目录信息失败: {file_info}")
            return False, False
        target = f"U_1_{file_info['file_id']}"
        url = f"{self.base_url}/open/upload/init"
        if not kwargs.get('sign_key') and not kwargs.get('sign_val'):
            # 如果没有提供sign_key和sign_val，则直接使用文件名和大小
            data = {
                "file_name": kwargs.get('file_name', ''),
                "file_size": kwargs.get('file_size', 0),    
                "target": target,  # 0: 根目录, 1: 指定目录
                "fileid": kwargs.get('fileid', '')
            }
        else:
            # 如果提供了sign_key和sign_val，则使用它们进行二次认证
            data = {
                "file_name": kwargs.get('file_name', ''),
                "file_size": kwargs.get('file_size', 0),    
                "target": target,  # 0: 根目录, 1: 指定目录
                "fileid": kwargs.get('fileid', ''),
                "sign_key": kwargs.get('sign_key'),
                "sign_val": kwargs.get('sign_val')
            }
        response = self._make_api_request('POST', url, data=data, headers=self._get_headers())
        if isinstance(response, dict) and response.get('code') == 0:
            init.logger.info(response['data'])
            # 需要二次认证
            if response['data']['sign_key'] and response['data']['sign_check'] and kwargs.get('request_times') == 1:
                sign_check = response['data']['sign_check'].split('-')
                sign_val = file_sha1_by_range(kwargs.get('file_path', ''), int(sign_check[0]), int(sign_check[1])).upper()
                return self.upload_file(
                    file_name=kwargs.get('file_name', ''),
                    file_size=kwargs.get('file_size', 0),    
                    target=kwargs.get('target'),
                    fileid=kwargs.get('fileid', ''),
                    file_path=kwargs.get('file_path', ''),  # 添加这个参数
                    sign_key=response['data']['sign_key'],
                    sign_val=sign_val,
                    request_times=2)
            if response['data']['status'] != 2:
                # 秒传失败，需要上传到阿里服务器时
                callback_params = response['data'].get('callback', {})
                if callback_params:
                    # 获取上传token
                    token_info = self.get_upload_token()
                    if not token_info:
                        init.logger.warn("获取上传token失败")
                        return False, False
                    # 准备上传参数
                    access_key_id = token_info['AccessKeyId']
                    access_key_secret = token_info['AccessKeySecret']
                    security_token = token_info['SecurityToken']
                    endpoint = token_info['endpoint']
                    bucket = response['data']['bucket']
                    object_key = response['data']['object']
                    pick_code = response['data']['pick_code']
                    region = 'cn-shenzhen'
                    callback_body_str = callback_params.get('callback', '{}')
                    callback_vars_str = callback_params.get('callback_var', '{}')

                    # 构造回调参数（callback）：指定回调地址和回调请求体，使用 Base64 编码
                    callback=base64.b64encode(callback_body_str.encode()).decode()
                    # 构造自定义变量（callback-var），使用 Base64 编码
                    callback_var=base64.b64encode(callback_vars_str.encode()).decode()
                    
                    # 上传文件到阿里云OSS
                    try:
                        init.logger.info(f"开始上传文件: {kwargs.get('file_name', '')}")
                        upload_result = upload_file_to_oss(
                            access_key_id=access_key_id,
                            access_key_secret=access_key_secret,
                            security_token=security_token,
                            endpoint=endpoint,
                            bucket=bucket,
                            file_path=kwargs.get('file_path', ''),
                            key=object_key,
                            region=region,
                            callback=callback,
                            callback_var=callback_var
                        )
                        
                        if upload_result:
                            init.logger.info(f"[{kwargs.get('file_name', '')}]上传成功！")
                            return True, False
                        else:
                            init.logger.warn(f"[{kwargs.get('file_name', '')}]上传失败!")
                            return False, False
                    except Exception as e:
                        init.logger.warn(f"上传文件到OSS时出错: {e}")
                        return False, False
            else:
                init.logger.info(f"[{kwargs.get('file_name', '')}]秒传成功！")
                return True, True
        else:
            init.logger.warn(f"文件上传初始化失败: {response['message']}")
            return False, False
    
    
    @handle_token_expiry
    def get_upload_token(self):
        """获取上传文件的token"""
        url = f"{self.base_url}/open/upload/get_token"
        response = self._make_api_request('GET', url)
        
        if isinstance(response, dict) and response.get('code') == 0:
            init.logger.info(f"获取上传token成功: {response}")
            return response['data']
        else:
            init.logger.warn(f"获取上传token失败: {response}")
            if response['code'] == 40140125:
                    return response
        return None
    
        
    @handle_token_expiry
    @handle_token_expiry
    def get_user_info(self):
        """获取用户信息"""
        url = f"{self.base_url}/open/user/info"
        response = self._make_api_request('GET', url)
        
        if isinstance(response, dict) and response.get('code') == 0:
            init.logger.info(f"获取用户信息成功: {response}")
            return response['data']
        else:
            init.logger.warn(f"获取用户信息失败: {response}")
            if response['code'] == 40140125:
                return response
            return None
        
    @handle_token_expiry
    def get_quota_info(self):
        """获取配额信息"""
        url = f"{self.base_url}/open/offline/get_quota_info"
        response = self._make_api_request('GET', url)
        
        if isinstance(response, dict) and response.get('code') == 0:
            init.logger.info(f"获取配额信息成功: {response}")
            return response['data']
        else:
            init.logger.warn(f"获取配额信息失败: {response}")
            if response['code'] == 40140125:
                return response
            return None
        
    @handle_token_expiry
    def get_file_play_url(self, file_path):
        file_info = self.get_file_info(file_path)
        if not file_info:
            return None
        params = {
            "cid": file_info['file_id'],
            "type": 4,
            "limit": 1000
        }
        file_list = self.get_file_list(params)
        if not file_list:
            return None
        video_name = file_list[0]['fn']
        video_info = self.get_file_info(f"{file_path}/{video_name}")
        pick_code = video_info.get('pick_code', '')
        url = f"{self.base_url}/open/video/play"
        params = {
            "pick_code": pick_code
        }
        response = self._make_api_request('GET', url, params=params)
        if isinstance(response, dict) and response.get('code') == 0:
            init.logger.info(f"获取视频播放链接成功: {response}")
            return response['data']['video_url'][0]['url']
        else:
            init.logger.warn(f"获取视频播放链接失败: {response}")
            if response['code'] == 40140125:
                return response
        return None
    
    @handle_token_expiry
    def get_file_download_url(self, file_path):
        """获取文件下载链接"""
        file_info = self.get_file_info(file_path)
        file_id = file_info['file_id']
        videos = self.get_file_list({
            "cid": file_id,
            "type": 4,
            "limit": 1,
            "asc": 0,
            "o": "file_size",
            "custom_order": 1
        })
        url = f"{self.base_url}/open/ufile/downurl"
        download_urls = []
        for i in range(len(videos)):
            data = {  
                "pick_code": videos[0]['pc']
            }
            response = self._make_api_request('POST', url, data=data, headers=self._get_headers())
            if response['state'] == True:
                init.logger.info(f"获取文件下载链接成功: {response}")
                download_urls.append(response['data'][videos[i]['fid']]['url']['url'])
                time.sleep(3)  # 避免请求过快
            else:
                init.logger.warn(f"获取文件下载链接失败: {response}")
                if response['code'] == 40140125:
                    return response
        return download_urls
    
    
    @handle_token_expiry
    def clear_cloud_task(self, flag=0):
        url = f"{self.base_url}/open/offline/clear_task"
        # 清除任务类型：0清空已完成、1清空全部、2清空失败、3清空进行中、4清空已完成任务并清空对应源文件、5清空全部任务并清空对应源文件
        data = {
            "flag": flag 
        }
        response = self._make_api_request('POST', url, data=data)
        if response['state'] == True:
            init.logger.info(f"清理云端任务成功！")
            return True
        else:
            init.logger.warn(f"清理云端任务失败: {response['message']}")
            if response['code'] == 40140125:
                return response
            return None
        
    def move_file(self, source_path, target_path):
        """移动文件或目录"""
        # copy_file 实际上是把文件复制到 target_path 目录下
        # 所以新文件的全路径是 target_path/basename(source_path)
        
        # 1. 执行复制
        copy_result = self.copy_file(source_path, target_path)
        if copy_result == True:
            # 2. 清除目标位置可能存在的旧缓存（因为现在有了新文件）
            try:
                # 获取源文件/目录名称
                msg_filename = os.path.basename(source_path.rstrip('/'))
                
                # 构造目标完整路径
                target_path_clean = target_path.rstrip('/')
                full_new_path = f"{target_path_clean}/{msg_filename}"
                
                if full_new_path in self.file_info_cache:
                    init.logger.info(f"清除移动目标位置[{full_new_path}]的缓存")
                    del self.file_info_cache[full_new_path]
            except Exception as e:
                init.logger.warn(f"清除移动目标缓存异常: {e}")

            # 3. 执行删除源文件
            # delete_single_file 内部已经处理了 source_path 的缓存清除
            delete_result = self.delete_single_file(source_path)
            
            if delete_result == True:
                return True
            else:
                init.logger.warn(f"移动文件失败: 删除源文件失败")
                return False
        else:
            init.logger.warn(f"移动文件失败: 复制文件失败")
            return False
    
    def clear_request_count(self):
        """清除请求计数"""
        self.request_count = 0
        self.cache_hit = 0
        
    def welcome_message(self):
        """欢迎消息"""
        user_info = self.get_user_info()
        quota_info = self.get_quota_info()
        space_info = user_info.get('rt_space_info') if isinstance(user_info, dict) else None
        if space_info:
            user_name = user_info.get('user_name', '')
            total_space = space_info['all_total']['size_format']
            used_space = space_info['all_use']['size_format']
            remaining_space = space_info['all_remain']['size_format']
            vip_info = user_info.get('vip_info', {})
            # 判断永V
            if "长期" in vip_info.get('level_name', ''):
                self.lifetime_vip = True
            expire_date = datetime.fromtimestamp(vip_info.get('expire', 0), tz=timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
            line1 = escape_markdown(f"👋 [{user_name}]您好， 欢迎使用Telegram-115Bot！", version=2)
            line2 = escape_markdown(f"会员等级：{vip_info.get('level_name', '')} \n到期时间：{expire_date}", version=2)
            line3 = escape_markdown(f"总空间：{total_space} \n已用：{used_space} \n剩余：{remaining_space}", version=2)
            quota_used = quota_info.get('used', '?') if isinstance(quota_info, dict) else '?'
            quota_count = quota_info.get('count', '?') if isinstance(quota_info, dict) else '?'
            line4 = escape_markdown(f"离线配额：{quota_used}/{quota_count}", version=2)
            return line1, line2, line3, line4
        else:
            line1 = escape_markdown("👋 欢迎使用Telegram-115Bot！（Token 已过期，请重新授权）", version=2)
            return line1, "", "", ""


    def check_offline_download_success(self, url, offline_timeout=300):
        time_out = 0
        task_name = ""
        info_hash = ""
        while time_out < offline_timeout:
            tasks = self.get_offline_tasks()
            if not tasks:
                return False, "", ""
            for task in tasks:
                # 判断任务的URL是否匹配
                if task.get('url') == url:
                    task_name = task.get('name', '')
                    info_hash = task.get('info_hash', '')
                    # 检查任务状态
                    if task.get('status') == 2 or task.get('percentDone') == 100:
                        return True, task_name, info_hash
                    else:
                        time.sleep(10)
                        time_out += 10
                    break
        init.logger.warn(f"[{task_name}]离线下载超时!")
        return False, task_name, info_hash
    
    # def check_offline_download_success(self, url, offline_timeout=180):
    #     time.sleep(offline_timeout)  # 等待下载完成
    #     task_name = ""
    #     info_hash = ""
    #     tasks = self.get_offline_tasks()
    #     if not tasks:
    #         return False, "", ""
    #     for task in tasks:
    #         # 判断任务的URL是否匹配
    #         if task.get('url') == url:
    #             task_name = task.get('name', '')
    #             info_hash = task.get('info_hash', '')
    #             # 检查任务状态
    #             if task.get('status') == 2 or task.get('percentDone') == 100:
    #                 return True, task_name, info_hash
    #             else:
    #                 break

    #     init.logger.warn(f"[{task_name}]离线下载超时!")
    #     return False, task_name, info_hash

        
    def get_files_from_dir(self, path, file_type=4):
        """获取指定目录下的所有文件"""
        video_list = []
        file_info = self.get_file_info(path)
        if not file_info:
            init.logger.warn(f"获取目录信息失败: {file_info}")
            return video_list
        
        # 文件类型；1.文档；2.图片；3.音乐；4.视频；5.压缩；6.应用；7.书籍
        params = {
            "cid": file_info['file_id'],
            "type": 4,
            "limit": 1000
        }
        file_list = self.get_file_list(params)
        for file in file_list:
            video_list.append(file['fn'])
        return video_list
    
    def get_sync_dir(self, path, file_type=4, offset=0, limit=1150):
        """获取指定目录下的所有文件"""
        video_list = []
        file_info = self.get_file_info(path)
        if not file_info:
            init.logger.warn(f"获取目录信息失败: {file_info}")
            return video_list
        
        # 文件类型；1.文档；2.图片；3.音乐；4.视频；5.压缩；6.应用；7.书籍
        params = {
            "cid": file_info['file_id'],
            "type": file_type,
            "limit": limit,
            "offset": offset
        }
        file_list = self.get_file_list(params)
        if not file_list:
            init.logger.warn(f"目录 {path} 中没有找到视频文件")
            return video_list
        
        if len(file_list) >= limit:
            offset += limit
            self.get_sync_dir(path, file_type, offset, limit)
        else:
            for file in file_list:
                file_info = self.get_file_info_by_id(file['pid'])
                folder_name = file_info['file_name']
                video_list.append(f"{folder_name}/{file['fn']}")

        return video_list
    
    def is_directory(self, path):
        """检查路径是否为目录"""
        file_info = self.get_file_info(path)
        if not file_info:
            init.logger.warn(f"获取文件信息失败: {file_info}")
            return False
        
        if file_info['file_category'] == '0':
            return True
        return False
    
    def create_dir_for_file(self, path, floder_name):
        file_info = self.get_file_info(path)
        if not file_info:
            init.logger.warn(f"获取目录信息失败: {path}")
            return False
        
        # 创建文件夹
        return self.create_directory(file_info['file_id'], floder_name)
        
    
    def auto_clean(self, path):
        # 开关关闭直接返回
        if str(init.bot_config['clean_policy']['switch']).lower() == "off":
            return
        
        file_info = self.get_file_info(path)
        if not file_info:
            init.logger.warn(f"获取目录信息失败: {file_info}")
            return
        params = {
            "cid": file_info['file_id'],
            "limit": 1000,
            "show_dir": 1
        }
        file_list = self.get_file_list(params)
        
        # 换算字节大小
        byte_size = 0
        less_than = init.bot_config['clean_policy']['less_than']
        if less_than is not None:
            if str(less_than).upper().endswith("M"):
                byte_size = int(less_than[:-1]) * 1024 * 1024
            elif str(less_than).upper().endswith("K"):
                byte_size = int(less_than[:-1]) * 1024
            elif str(less_than).upper().endswith("G"):
                byte_size = int(less_than[:-1]) * 1024 * 1024 * 1024
                
        fid_list = []
        for file in file_list:
            # 删除小于指定大小的文件
            if file['fc'] == '1':
                if file['fs'] < byte_size:
                    fid_list.append(file['fid'])
                    init.logger.info(f"[{file['fn']}]已添加到清理列表")
            # 目录直接删除
            else:
                fid_list.append(file['fid'])
                init.logger.info(f"[{file['fn']}]已添加到清理列表")
        
        if fid_list:
            self._batch_delete_files(fid_list)
            
            
    def auto_clean_by_id(self, file_id):
        # 开关关闭直接返回
        if str(init.bot_config['clean_policy']['switch']).lower() == "off":
            return
        params = {
            "cid": file_id,
            "limit": 1000,
            "show_dir": 1
        }
        file_list = self.get_file_list(params)
        
        # 换算字节大小
        byte_size = 0
        less_than = init.bot_config['clean_policy']['less_than']
        if less_than is not None:
            if str(less_than).upper().endswith("M"):
                byte_size = int(less_than[:-1]) * 1024 * 1024
            elif str(less_than).upper().endswith("K"):
                byte_size = int(less_than[:-1]) * 1024
            elif str(less_than).upper().endswith("G"):
                byte_size = int(less_than[:-1]) * 1024 * 1024 * 1024
                
        fid_list = []
        for file in file_list:
            # 删除小于指定大小的文件
            if file['fc'] == '1':
                if file['fs'] < byte_size:
                    fid_list.append(file['fid'])
                    init.logger.info(f"[{file['fn']}]已添加到清理列表")
            # 目录直接删除
            else:
                fid_list.append(file['fid'])
                init.logger.info(f"[{file['fn']}]已添加到清理列表")
        
        if fid_list:
            self._batch_delete_files(fid_list)
            
    
    def auto_clean_all(self, path, clean_empty_dir=False, protect_sibling_of_largest=False):
         # 开关关闭直接返回
        if str(init.bot_config['clean_policy']['switch']).lower() == "off":
            return
        
        file_info = self.get_file_info(path)
        if not file_info:
            init.logger.warn(f"获取目录信息失败: {file_info}")
            return

        # 先剥掉正片文件名里被植入的广告前缀（六位数字.com@）。
        # 放在垃圾文件判断之前，因为带前缀的往往是受保护的正片，目录里未必有其它垃圾文件。
        self.strip_ad_prefix_in_dir(path)

        # 换算字节大小
        byte_size = 0
        less_than = init.bot_config['clean_policy']['less_than']
        if less_than is not None:
            if str(less_than).upper().endswith("M"):
                byte_size = int(less_than[:-1]) * 1024 * 1024
            elif str(less_than).upper().endswith("K"):
                byte_size = int(less_than[:-1]) * 1024
            elif str(less_than).upper().endswith("G"):
                byte_size = int(less_than[:-1]) * 1024 * 1024 * 1024
        
        # 找到所有垃圾文件
        junk_file_list = self.find_all_junk_files(
            file_info['file_id'], 0, byte_size,
            protect_sibling_of_largest=protect_sibling_of_largest)
        if not junk_file_list:
            init.logger.info(f"[{path}]下没有找到需要清理的垃圾文件！")
            return
                
        fid_list = []
        pid_list = []
        for file in junk_file_list:
            fid_list.append(file['fid'])
            init.logger.info(f"[{file['fn']}]已添加到清理列表")
            if file['pid'] not in pid_list:
                pid_list.append(file['pid'])
        
        if fid_list:
            self._batch_delete_files(fid_list)
        
        # 清理空目录
        if clean_empty_dir:
            empty_dir_list = self.find_all_empty_dirs(pid_list)
            if not empty_dir_list:
                init.logger.info(f"[{path}]下没有找到需要清理的空目录！")
                return
            fid_list = []
            for dir_id in empty_dir_list:
                fid_list.append(dir_id)
                init.logger.info(f"[{dir_id}]已添加到清理列表")
            if fid_list:
                self._batch_delete_files(fid_list)

    # 植入正片文件名的广告前缀，形如 489155.com@DLDSS-496-C.mp4
    # 规则：恰六位数字 + ".com@"，位于文件名开头（大小写不敏感）
    _AD_PREFIX_RE = re.compile(r'^\d{6}\.com@', re.IGNORECASE)

    def strip_ad_prefix_in_dir(self, path: str):
        """剥掉目录内文件名开头被植入的广告前缀（六位数字.com@）并重命名。

        与删除整文件的广告清理不同：这里保留文件本体，只把正片文件名里的
        广告前缀去掉。受 clean_policy.strip_ad_prefix 开关控制（默认开）。
        """
        clean_cfg = init.bot_config.get('clean_policy', {}) or {}
        if str(clean_cfg.get('strip_ad_prefix', 'true')).lower() == 'false':
            return

        file_info = self.get_file_info(path)
        if not file_info or 'file_id' not in file_info:
            return

        params = {
            "cid": file_info['file_id'],
            "limit": 1150,
            "show_dir": 0,
            "offset": 0,
        }
        files = self.get_file_list(params) or []

        renamed = 0
        for f in files:
            fn = f.get('fn', '')
            fid = f.get('fid')
            if not fn or not fid:
                continue
            new_fn = self._AD_PREFIX_RE.sub('', fn, count=1)
            if new_fn and new_fn != fn:
                init.logger.info(f"[去广告前缀] {fn} -> {new_fn}")
                result = self.rename_by_id(fid, fn, new_fn)
                if result is True:
                    renamed += 1
                time.sleep(0.2)  # 避免请求过快

        if renamed:
            init.logger.info(f"[{path}] 共去除 {renamed} 个文件的广告前缀")

    def _is_ad_filename(self, filename: str, ad_patterns: list) -> bool:
        """文件名是否命中广告关键词（大小写不敏感）。"""
        fn_lower = filename.lower()
        return any(p.lower() in fn_lower for p in ad_patterns if p)

    def find_all_junk_files(self, cid, offset, byte_size, file_list=None, limit=1150,
                            protect_sibling_of_largest=False):
        """
        递归查找垃圾文件。判定规则（同时支持）：
          1. 文件名命中 clean_policy.ad_name_patterns 中的广告关键词
          2. 文件大小 < byte_size（仅当 byte_size > 0 时生效）

        clean_policy.protect_largest=true（默认）时，目录内体积最大的文件永远受保护，
        即使文件名命中广告模式也不会被删除，防止误删主视频。

        protect_sibling_of_largest（missav 专用）透传给 _filter_junk，额外保护与正片同名的字幕等。
        """
        if file_list is None:
            file_list = []

        params = {
            "cid": cid,
            "limit": limit,
            "show_dir": 0,
            "custom_order": 1,
            "asc": 1,
            "o": "file_size",
            "offset": offset
        }

        current_files = self.get_file_list(params)

        if not current_files:
            return self._filter_junk(file_list, byte_size, protect_sibling_of_largest)

        file_list.extend(current_files)

        if len(current_files) < limit:
            return self._filter_junk(file_list, byte_size, protect_sibling_of_largest)

        try:
            last_file_size = int(current_files[-1].get('fs', 0))
        except (ValueError, TypeError, IndexError):
            last_file_size = 0

        if last_file_size < byte_size:
            offset += limit
            time.sleep(1)
            return self.find_all_junk_files(cid, offset, byte_size, file_list,
                                            protect_sibling_of_largest=protect_sibling_of_largest)
        else:
            return self._filter_junk(file_list, byte_size, protect_sibling_of_largest)

    @staticmethod
    def _filename_stem(filename: str) -> str:
        """取文件名主干（去最后一个扩展名），小写。如 START-583.srt -> start-583"""
        if '.' in filename:
            return filename.rsplit('.', 1)[0].strip().lower()
        return filename.strip().lower()

    def _filter_junk(self, file_list: list, byte_size: int,
                     protect_sibling_of_largest: bool = False) -> list:
        """
        从 file_list 中筛选出垃圾文件：
          - 文件扩展名命中 ad_extensions → 删（不受 protect_largest 保护）
          - 文件名命中广告模式 → 删
          - 文件大小 < byte_size（且 byte_size > 0）→ 删
        但目录中体积最大的文件受 protect_largest 保护，永不删（扩展名命中除外）。

        protect_sibling_of_largest=True（missav 专用）时，额外保护「与最大文件主文件名
        相同」的文件（如正片 START-583.mp4 旁的字幕 START-583.srt），避免字幕被当小文件误删。
        但若该同名文件扩展名命中 ad_extensions 仍会删。
        """
        if not file_list:
            return []

        clean_cfg = init.bot_config.get('clean_policy', {})
        ad_patterns = clean_cfg.get('ad_name_patterns') or []
        ad_extensions = [e.lower() for e in (clean_cfg.get('ad_extensions') or [])]
        protect_largest = str(clean_cfg.get('protect_largest', 'true')).lower() != 'false'

        # 找出体积最大的文件 fid（受保护）+ 其主文件名（用于保护同名字幕）
        protected_fid = None
        largest_stem = None
        if file_list and (protect_largest or protect_sibling_of_largest):
            largest = max(file_list, key=lambda f: int(f.get('fs', 0)))
            if protect_largest:
                protected_fid = largest.get('fid')
            if protect_sibling_of_largest:
                largest_stem = self._filename_stem(largest.get('fn', ''))

        junk = []
        for f in file_list:
            fid = f.get('fid')
            fn = f.get('fn', '')
            fs = int(f.get('fs', 0))
            ext = '.' + fn.rsplit('.', 1)[-1].lower() if '.' in fn else ''

            # 扩展名命中：无条件删，不受任何保护
            if ad_extensions and ext in ad_extensions:
                init.logger.debug(f"[广告清理] 命中(广告扩展名): {fn}")
                junk.append(f)
                continue

            if fid == protected_fid:
                init.logger.debug(f"[广告清理] 保护最大文件，跳过: {fn} ({fs} bytes)")
                continue

            # 保护与正片同名的文件（如字幕），仅 missav 启用
            if largest_stem and fid != protected_fid and self._filename_stem(fn) == largest_stem:
                init.logger.info(f"[广告清理] 保护与正片同名文件（字幕等），跳过: {fn}")
                continue

            is_ad_name = bool(ad_patterns) and self._is_ad_filename(fn, ad_patterns)
            is_small = byte_size > 0 and fs < byte_size

            if is_ad_name or is_small:
                reason = []
                if is_ad_name:
                    reason.append("广告文件名")
                if is_small:
                    reason.append(f"小于 {byte_size} bytes")
                init.logger.debug(f"[广告清理] 命中({'/'.join(reason)}): {fn}")
                junk.append(f)

        return junk
        
    def find_all_empty_dirs(self, pid_list):
        """
        pid_list: 目录ID列表
            
        Returns:
            list: 所有空目录列表，包含目录的fid、fn等信息
        """
        empty_dir_list = []
        for pid in pid_list:
            file_info = self.get_file_info_by_id(pid)
            if file_info and (file_info['size_byte'] == 0 or file_info['count'] == 0):
                empty_dir_list.append(pid)
            time.sleep(0.1)  # 避免请求过快
        return empty_dir_list
    
    
    def find_all_voideos(self, path, success_task, time_stamp, offset=0, video_list=None, limit=1150):
        file_info = self.get_file_info(path)
        if not file_info:
            init.logger.warn(f"获取目录信息失败: {path}")
            return []
            
        cid = file_info['file_id']
        if video_list is None:
            video_list = []
            
        params = {
            "cid": cid,
            "type": 4,
            "limit": limit,
            "show_dir": 0,
            "custom_order": 1,
            "asc": 0,
            "o": "user_utime",
            "offset": offset
        }
        current_files = self.get_file_list(params)
        
        stop_searching = False
        
        if current_files:
            for item in current_files:
                diff = time_stamp - item['upt']
                # 寻找 time_stamp 前 600 秒内上传的文件（包含最新的）
                if diff > 600:
                    # 文件太旧，且后续更旧，停止
                    stop_searching = True
                    break
                else:
                    video_list.append({"pid": item['pid'], 'name': item['fn']})
            
            # 如果没有遇到太旧的文件，且当前页是满的，继续翻页
            if not stop_searching and len(current_files) == limit:
                offset += limit
                return self.find_all_voideos(path, success_task, time_stamp, offset, video_list, limit)
        
        result = []
        for video in video_list:
            for item in success_task:
                # 兼容 offline_task_retry.py 传入的包装结构 {"task": task, "save_path": ...}
                task = item['task'] if isinstance(item, dict) and 'task' in item else item
                if video['pid'] == task.get('file_id'):
                    # 优先从item中获取image_path，如果没有则尝试从task中获取
                    image_path = item.get('image_path') if isinstance(item, dict) else None
                    if not image_path:
                        image_path = task.get('image_path', '')

                    result.append({
                        "save_path": path,
                        "folder_name": task.get('name'),
                        "file_name": video['name'],
                        "image_path": image_path
                    })
                    break
        return result
                


    def create_dir_recursive(self, path):
        """递归创建目录"""
        # 清除目标路径缓存，确保状态最新
        if path in self.file_info_cache:
            del self.file_info_cache[path]

        res = self.get_file_info(path)
        if res:
            init.logger.info(f"[{path}]目录已存在！")
            return res
        
        path_list = get_parent_paths(path) 
        # get_parent_paths 返回如 ['/AV', '/AV/涩花', '/AV/涩花/亚洲无码原创', ...]
        
        last_path = ""
        final_info = None
        
        for index, item in enumerate(path_list):
            # 同样清除沿途路径缓存
            if item in self.file_info_cache:
                del self.file_info_cache[item]

            res = self.get_file_info(item)  # 确保目录存在
            if res:
                last_path = item
                final_info = res
            else:
                # 需要创建
                parent_id = 0
                if index > 0:
                    # 需要父目录ID
                    if not final_info:
                         # 尝试重新获取 last_path 信息
                         final_info = self.get_file_info(last_path)
                    
                    if final_info:
                        parent_id = final_info.get('file_id') or final_info.get('cid')
                    else:
                        init.logger.error(f"无法获取父目录信息: {last_path}")
                        return None
                
                # 解析目录名
                name = os.path.basename(item)
                if index == 0 and item.startswith("/") and not name: 
                    # item 可能就是 "/" 或者 "/foo"
                    # 这里假设 path_list 里的 item 都是完整路径
                    pass
                if not name and index == 0: # 处理特殊情况
                     name = item.strip("/")
                
                created_res = self.create_directory(parent_id, name)
                
                current_info = None
                
                if isinstance(created_res, dict):
                    current_info = created_res
                    if 'file_id' not in current_info and 'cid' in current_info:
                        current_info['file_id'] = current_info['cid']
                elif created_res is True:
                    # 目录已存在 (code 20004)，但 get_file_info 没查到
                    init.logger.info(f"目录已存在但未获取到信息，尝试从父目录列表查找: {item}")
                    try:
                        file_list_data = self.get_file_list({'cid': parent_id, 'limit': 1000})
                        file_list = []
                        if isinstance(file_list_data, list):
                            file_list = file_list_data
                        elif isinstance(file_list_data, dict):
                            file_list = file_list_data.get('list', []) or file_list_data.get('data', [])
                        
                        for f in file_list:
                            fname = f.get('n') or f.get('file_name') or f.get('name')
                            if fname == name:
                                current_info = f
                                if 'file_id' not in current_info:
                                    current_info['file_id'] = current_info.get('cid') or current_info.get('fid')
                                break
                    except Exception as e:
                        init.logger.warn(f"从父目录查找失败: {e}")
                
                if current_info:
                    final_info = current_info
                    # 关键：更新缓存！
                    self.file_info_cache[item] = final_info
                    last_path = item
                    init.logger.info(f"目录[{item}]检查/创建/获取成功, ID: {final_info.get('file_id')}")
                else:
                    init.logger.error(f"创建目录后无法获取其信息: {item}")
                    return None
                    
                time.sleep(1)
                    
        init.logger.info(f"目录[{path}]处理完成！")
        return final_info
        
    
    def check_risk(self):
        self.request_count += 1
        if self.lifetime_vip:
            request_risk_value = 15000 * RISK_THRESHOLD
        else:
            request_risk_value = 10000 * RISK_THRESHOLD
        if self.request_count >= request_risk_value:
            init.logger.warn("今日请求次数即将达到风险阈值，自动停止所有115请求，以免被风控...")
            return True
        return False

        
            
    @staticmethod
    def save_token_to_file(access_token: str, refresh_token: str, file_path: str):
        """已废弃，保留仅防外部调用报错"""
        init.save_tokens_to_config(access_token, refresh_token)
        
    @staticmethod
    def get_challenge() -> str:
        # 生成随机字节（避免直接使用 ASCII 字符以确保安全随机性）
        random_bytes = os.urandom(64)
        # 转换为 URL-safe Base64，并移除填充字符（=）
        verifier = base64.urlsafe_b64encode(random_bytes).rstrip(b'=').decode('utf-8')
        # 确保符合规范（虽然 urlsafe_b64encode 已满足要求，此处做二次验证）
        verifier = re.sub(r'[^A-Za-z0-9\-._~]', '', verifier)[:64]  # 限制长度为64字符
        sha256_hash = hashlib.sha256(verifier.encode('utf-8')).digest()
        # Base64 URL 安全编码并移除填充字符
        challenge = base64.urlsafe_b64encode(sha256_hash).rstrip(b'=').decode('utf-8')
        return verifier, challenge
    
def file_sha1(file_path):
    with open(file_path, 'rb') as f:
        return hashlib.sha1(f.read()).hexdigest()
    
def sha1_digest(file_path):
    h = hashlib.sha1()
    with Path(file_path).open('rb') as f:
        for chunk in iter(lambda: f.read(128), b''):
            h.update(chunk)
            break
    return h.hexdigest()


def calculate_sha1(file_path):
    """计算文件的SHA1哈希值"""
    sha1 = hashlib.sha1()
    try:
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sha1.update(chunk)
        return sha1.hexdigest()
    except FileNotFoundError:
        init.logger.error(f"错误：文件未找到 -> {file_path}")
        return None
    
def file_sha1_by_range(file_path, start, end):
    """计算文件从start到end（含end）的SHA1"""
    size = end - start + 1
    sha1 = hashlib.sha1()
    with open(file_path, "rb") as f:
        f.seek(start)
        data = f.read(size)
        sha1.update(data)
    return sha1.hexdigest()


def get_parent_paths(path):
    """
    获取路径的所有父级路径列表
    :param path: 输入路径，如 "/AV/rigeng/111/222"
    :return: 父级路径列表，如 ["/AV", "/AV/rigeng", "/AV/rigeng/111"]
    """
    # 规范化路径（处理多余的斜杠等问题）
    normalized_path = os.path.normpath(path)
    
    # 分割路径
    parts = normalized_path.split(os.sep)
    
    # 处理Unix系统的根目录情况
    if parts[0] == '':
        parts[0] = os.sep
    
    # 逐步构建路径
    result = []
    current_path = parts[0] if parts[0] == os.sep else ""
    
    for part in parts[1:]:
        current_path = os.path.join(current_path, part)
        result.append(current_path)
    
    return result

if __name__ == "__main__":
    init.init_log()
    init.load_yaml_config()
    app = OpenAPI_115()
    # empty_dir_list = app.auto_clean_all("/AV/1024/亚洲无码原创", clean_empty_dir=True)
    # if not empty_dir_list:
    #     init.logger.info("没有找到空目录")
    # else:
    #     for dir in empty_dir_list:
    #         init.logger.info(f"找到空目录: {dir['fn']}")
    vedio_list = app.get_sync_dir("/影视/电影/老电影")
    # app.offline_download_specify_path("magnet:?xt=urn:btih:2A93EFB4E2E8ED96B52207D9C5AA4FF2F7E8D9DF", "/test")
    # time.sleep(10)
    # dl_flg, resource_name = app.check_offline_download_success_no_waite("magnet:?xt=urn:btih:2A93EFB4E2E8ED96B52207D9C5AA4FF2F7E8D9DF")
    # print(dl_flg, resource_name)
    # quota_info = app.get_quota_info()
    # print(f"离线下载配额: {quota_info['used']}/{quota_info['count']}")

    # app.auto_clean(f"{init.bot_config['offline_path']}/nyoshin-n1996")
    # app.clear_failed_task("magnet:?xt=urn:btih:C506443C77A1F7EC3D18718F0DAC6AAA2BCE1FB6&dn=nyoshin-n1996")  # 示例URL
    # if app.is_directory(f"{init.bot_config['offline_path']}"):
    #     init.logger.info("这是一个目录")
    # else:
    #     init.logger.info("这不是一个目录")
    # app.create_dir_for_video_file(f"{init.bot_config['offline_path']}/gc2048.com-agnes-sss.mp4")
    # file_list = app.get_files_from_dir(f"{init.bot_config['offline_path']}/极品眼镜妹~【agnes-sss】清纯外表~长腿黑丝~白领装~全裸跳蛋")
    # for file in file_list:
    #     init.logger.info(f"找到视频文件: {file}")
    # app.rename(f"{init.bot_config['offline_path']}/temp", "1111")
    # if app.offline_download("magnet:?xt=urn:btih:C506443C77A1F7EC3D18718F0DAC6AAA2BCE1FB6&dn=nyoshin-n1996"):
    #     init.logger.info("离线下载任务添加成功")
    #     if app.check_offline_download_success("magnet:?xt=urn:btih:C506443C77A1F7EC3D18718F0DAC6AAA2BCE1FB6&dn=nyoshin-n1996"):
    #         init.logger.info("离线下载任务成功")
    #     else:
    #         init.logger.error("离线下载任务失败或超时")
    #         app.clear_failed_task("magnet:?xt=urn:btih:C506443C77A1F7EC3D18718F0DAC6AAA2BCE1FB6&dn=nyoshin-n1996")
    # file_path = f"{init.TEMP}/20250713174710.mp4"
    # file_size = os.path.getsize(file_path)
    # file_name = os.path.basename(file_path)
    # sha1_value = file_sha1(file_path)
    # up_flg, bingo = app.upload_file(
    #     target="/AV/国产直播精选",
    #     file_name=file_name,
    #     file_size=file_size,
    #     fileid=sha1_value,
    #     file_path=file_path,
    #     request_times=1  # 第一次请求
    # )
    # if up_flg and bingo:
    #     init.logger.info(f"秒传成功")
    # elif up_flg and not bingo:
    #     init.logger.error("文件上传成功")
    # elif not up_flg and not bingo:
    #     init.logger.error("文件上传失败")
    # welcome_text = app.welcome_message()
    # init.logger.info(welcome_text)
    # app.clear_cloud_task()  # 清理云端任务

