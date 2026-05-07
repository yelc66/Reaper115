
import asyncio
import re
import time
import os
import requests
import json
from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.common.by import By
from selenium import webdriver
import init
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def _remote_selenium_url():
    """优先 config.yaml remote_selenium_url（仅填 host），再读环境变量。"""
    val = init.bot_config.get("remote_selenium_url") or ""
    host = (val or os.getenv("REMOTE_SELENIUM_URL") or "").rstrip("/")
    if not host:
        return None
    return host if host.endswith("/wd/hub") else f"{host}/wd/hub"

def _flaresolverr_url():
    """优先 config.yaml flaresolverr_url（仅填 host），再读环境变量。"""
    val = init.bot_config.get("flaresolverr_url") or ""
    host = (val or os.getenv("FLARESOLVERR_URL") or "").rstrip("/")
    if not host:
        host = "http://flaresolverr:8191"
    return host if host.endswith("/v1") else f"{host}/v1"


def _build_chrome_options():
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument(f'user-agent={init.USER_AGENT}')
    return options


def check_browser_health(timeout=15):
    """启动时检查远程 Selenium 浏览器是否能创建并执行一个基础会话。"""
    remote_url = _remote_selenium_url()
    if not remote_url:
        return False, "未配置 REMOTE_SELENIUM_URL，无法连接远程 Selenium 浏览器"

    driver = None
    try:
        init.logger.info(f"正在检查远程 Selenium 浏览器: {remote_url} ...")
        driver = webdriver.Remote(
            command_executor=remote_url,
            options=_build_chrome_options()
        )
        driver.set_page_load_timeout(timeout)
        driver.get("about:blank")
        ready_state = driver.execute_script("return document.readyState")
        user_agent = driver.execute_script("return navigator.userAgent")

        if ready_state not in ("interactive", "complete"):
            return False, f"浏览器会话异常，页面状态: {ready_state}"

        caps = driver.capabilities or {}
        browser_name = caps.get("browserName", "Chrome")
        browser_version = caps.get("browserVersion") or caps.get("version") or "unknown"
        return True, f"浏览器健康检查通过: {browser_name} {browser_version}, User-Agent: {user_agent}"
    except Exception as e:
        return False, f"浏览器健康检查失败: {e}"
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                init.logger.warn(f"浏览器健康检查清理失败: {e}")


class SeleniumBrowser:
    def __init__(self, base_url=None):
        self.base_url = base_url
        self.driver = None
        self.last_error = None
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def init_browser(self):
        await asyncio.get_running_loop().run_in_executor(self.executor, self._init_driver)

    def _init_driver(self):
        remote_url = _remote_selenium_url()
        if not remote_url:
            self.last_error = "未配置 REMOTE_SELENIUM_URL，无法连接远程 Selenium 浏览器"
            init.logger.error(self.last_error)
            return

        try:
            self.last_error = None
            init.logger.info(f"正在连接远程 Selenium: {remote_url} ...")

            self.driver = webdriver.Remote(
                command_executor=remote_url,
                options=_build_chrome_options()
            )
            user_agent = self.driver.execute_script("return navigator.userAgent")
            init.logger.info(f"远程 Selenium 会话已创建，浏览器 User-Agent: {user_agent}")

            if self.base_url:
                if not self.base_url.startswith('http'):
                    self.base_url = f"https://{self.base_url}"
                self.driver.set_page_load_timeout(init.bot_config.get("selenium_timeout", 60))
                self.driver.get(self.base_url)

            init.logger.info("远程 Selenium 连接成功")
        except Exception as e:
            self.last_error = f"远程 Selenium 连接失败: {e}"
            init.logger.error(self.last_error)

    async def close(self):
        try:
            init.logger.info("正在关闭浏览器并清理环境...")

            def _close_sync():
                if self.driver:
                    try:
                        self.driver.quit()
                    except Exception as e:
                        if "invalid session id" not in str(e).lower():
                            init.logger.warn(f"Driver quit 异常: {e}")

                if hasattr(os, 'waitpid'):
                    try:
                        while True:
                            pid, status = os.waitpid(-1, os.WNOHANG)
                            if pid == 0:
                                break
                    except OSError:
                        pass
                    except Exception:
                        pass

            await asyncio.get_running_loop().run_in_executor(self.executor, _close_sync)
            self.executor.shutdown(wait=True)
            init.logger.info("浏览器清理完成")
        except Exception as e:
            init.logger.error(f"关闭浏览器时发生错误: {e}")
        finally:
            self.driver = None

    async def goto(self, url):
        await asyncio.get_running_loop().run_in_executor(self.executor, self._goto_sync, url)

    def _goto_sync(self, url):
        if self.driver:
            try:
                self.driver.get(url)
                time.sleep(2)
            except Exception as e:
                init.logger.warn(f"Selenium导航失败: {e}")

    async def get_page_source(self):
        return await asyncio.get_running_loop().run_in_executor(self.executor, lambda: self.driver.page_source if self.driver else "")

    async def get_cookies(self):
        return await asyncio.get_running_loop().run_in_executor(self.executor, lambda: self.driver.get_cookies() if self.driver else [])

    async def get_current_url(self):
        return await asyncio.get_running_loop().run_in_executor(self.executor, lambda: self.driver.current_url if self.driver else "")

    async def execute_script(self, script, *args):
        return await asyncio.get_running_loop().run_in_executor(self.executor, lambda: self.driver.execute_script(script, *args) if self.driver else None)

    async def execute_async_script(self, script, *args):
        return await asyncio.get_running_loop().run_in_executor(self.executor, lambda: self.driver.execute_async_script(script, *args) if self.driver else None)

    async def click_text(self, text):
        await asyncio.get_running_loop().run_in_executor(self.executor, self._click_text_sync, text)

    def _click_text_sync(self, text):
        if not self.driver: return
        try:
            elem = self.driver.find_element(By.XPATH, f"//*[contains(text(), '{text}')]")
            elem.click()
            time.sleep(2)
        except Exception as e:
            init.logger.debug(f"点击文本 '{text}' 失败: {e}")

    async def wait_for_element(self, selector, by=By.CSS_SELECTOR, timeout=30):
        await asyncio.get_running_loop().run_in_executor(self.executor, self._wait_for_element_sync, selector, by, timeout)

    def _wait_for_element_sync(self, selector, by, timeout):
        if not self.driver: return
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((by, selector)))
        except: pass

    async def pass_cloudflare_check(self):
        await asyncio.get_running_loop().run_in_executor(self.executor, self._pass_cloudflare_check_sync)

    def _pass_cloudflare_check_sync(self):
        if not self.driver:
            return

        try:
            title = self.driver.title
            if not title or not any(x in title for x in ["Just a moment", "Cloudflare", "请稍候", "安全检查"]):
                return

            init.logger.info(f"检测到 Cloudflare 验证 ({title})，尝试使用 Flaresolverr 处理...")
            current_url = self.driver.current_url
            if not current_url:
                return

            payload = {
                "cmd": "request.get",
                "url": current_url,
                "maxTimeout": 120000
            }
            headers = {"Content-Type": "application/json"}

            flareSolverr = _flaresolverr_url()
            init.logger.info(f"请求 Flaresolverr: {flareSolverr}")
            response = requests.post(flareSolverr, json=payload, headers=headers, timeout=125)
            resp_data = response.json()

            if resp_data.get("status") == "ok":
                init.logger.info("Flaresolverr 验证成功，正在同步 Cookies...")
                solution = resp_data.get("solution", {})
                cookies = solution.get("cookies", [])
                user_agent = solution.get("userAgent")

                if user_agent:
                    init.logger.info(f"同步 Flaresolverr User-Agent: {user_agent[:50]}...")
                    try:
                        self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": user_agent})
                    except Exception as e:
                        init.logger.warn(f"设置 User-Agent 失败: {e}")

                if cookies:
                    self.driver.delete_all_cookies()
                    for cookie in cookies:
                        cookie_dict = {
                            'name': cookie['name'],
                            'value': cookie['value'],
                            'domain': cookie['domain'],
                            'path': cookie['path']
                        }
                        if 'expiry' in cookie: cookie_dict['expiry'] = int(cookie['expiry'])
                        if 'secure' in cookie: cookie_dict['secure'] = cookie['secure']
                        if 'httpOnly' in cookie: cookie_dict['httpOnly'] = cookie['httpOnly']
                        if 'sameSite' in cookie: cookie_dict['sameSite'] = cookie['sameSite']

                        try:
                            self.driver.add_cookie(cookie_dict)
                        except Exception:
                            pass

                    init.logger.info(f"成功同步 {len(cookies)} 个 Cookies，刷新页面...")
                    self.driver.refresh()
                    time.sleep(5)

                    title = self.driver.title
                    if any(x in title for x in ["Just a moment", "Cloudflare", "请稍候", "安全检查"]):
                        init.logger.warn("同步 Cookie 后依然显示 Cloudflare 验证页")
                    else:
                        init.logger.info("Cloudflare 验证已通过")
            else:
                init.logger.error(f"Flaresolverr 返回错误: {resp_data}")

        except Exception as e:
            init.logger.warn(f"Cloudflare 验证处理出错: {e}")

    async def run_with_driver(self, func, *args):
        return await asyncio.get_running_loop().run_in_executor(self.executor, func, self.driver, *args)
