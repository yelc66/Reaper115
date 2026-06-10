
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


def _prefer_flaresolverr():
    """是否优先用 Flaresolverr 直取 HTML（绕过 chrome 容器回灌 cookie）。

    config.yaml: flaresolverr_fetch (默认 true，只要配置了 flaresolverr_url 就启用)。
    设为 false 可强制回到旧的 chrome + cookie 回灌方案。
    """
    val = init.bot_config.get("flaresolverr_fetch")
    if val is None:
        val = os.getenv("FLARESOLVERR_FETCH")
    if val is None:
        return True
    return str(val).strip().lower() not in ("0", "false", "no", "off", "")


def fetch_html_via_flaresolverr(url, cookies=None, timeout_ms=120000):
    """直接用 Flaresolverr 抓取 url 的最终 HTML。

    Flaresolverr 在它自己的浏览器会话里解 Cloudflare、加载页面并返回渲染后的
    HTML —— IP / UA / 指纹 / cookie 全部自洽，无需回灌到独立的 chrome 容器。

    Returns: (html, solution_cookies) 或 (None, None)。
    """
    flareSolverr = _flaresolverr_url()
    payload = {"cmd": "request.get", "url": url, "maxTimeout": timeout_ms}
    if cookies:
        fs_cookies = []
        for c in cookies:
            name = c.get("name")
            value = c.get("value")
            if not name or value is None:
                continue
            fs_cookies.append({"name": name, "value": str(value)})
        if fs_cookies:
            payload["cookies"] = fs_cookies
    try:
        resp = requests.post(
            flareSolverr,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=(timeout_ms / 1000) + 10,
        )
        data = resp.json()
    except Exception as e:
        init.logger.warn(f"Flaresolverr 直取请求失败: {e}")
        return None, None

    if data.get("status") != "ok":
        init.logger.warn(f"Flaresolverr 直取返回非 ok: {data.get('message') or data.get('status')}")
        return None, None

    solution = data.get("solution") or {}
    html = solution.get("response")
    if not html:
        init.logger.warn("Flaresolverr 直取成功但 response 为空")
        return None, None
    return html, solution.get("cookies") or []


class _FlaresolverrSession:
    """Flaresolverr 直取模式下的轻量 driver 占位。

    只实现爬虫真正会调用的 driver 接口（cookie 管理 / refresh / page_source 等），
    把它们变成存内存的无害操作，避免改动调用方。真正的取页在 SeleniumBrowser.goto 里
    通过 fetch_html_via_flaresolverr 完成。
    """

    def __init__(self, base_url=None):
        self.base_url = base_url
        self.current_url = base_url or ""
        self.page_source = ""
        self.title = ""
        self._cookies = {}

    def add_cookie(self, cookie):
        name = cookie.get("name")
        if name:
            self._cookies[name] = cookie

    def delete_all_cookies(self):
        self._cookies.clear()

    def get_cookies(self):
        return list(self._cookies.values())

    def refresh(self):
        pass

    def get(self, url):
        self.current_url = url

    def quit(self):
        pass

    def execute_script(self, *args, **kwargs):
        return None


class SeleniumBrowser:
    def __init__(self, base_url=None):
        self.base_url = base_url
        self.driver = None
        self.last_error = None
        self.executor = ThreadPoolExecutor(max_workers=1)
        # Flaresolverr 直取模式下，goto() 抓到的 HTML 暂存于此，供 get_page_source() 返回
        self._fs_html = None
        self._fs_cookies = []
        self.use_flaresolverr_fetch = _prefer_flaresolverr()

    async def init_browser(self):
        await asyncio.get_running_loop().run_in_executor(self.executor, self._init_driver)

    def _init_driver(self):
        # 规范化 base_url，无论走哪种取页方式都需要
        if self.base_url and not self.base_url.startswith('http'):
            self.base_url = f"https://{self.base_url}"

        if self.use_flaresolverr_fetch:
            # Flaresolverr 直取模式：不依赖 chrome 容器，标记一个轻量"会话"占位，
            # 让上层 `if not browser.driver` 的存活检查通过。
            self.last_error = None
            self.driver = _FlaresolverrSession(self.base_url)
            init.logger.info(f"使用 Flaresolverr 直取模式取页，目标站点: {self.base_url}")
            return

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
        if self.use_flaresolverr_fetch:
            # 合并配置 cookie + 上一次 Flaresolverr 解出的 cookie 一起带上
            extra_cookies = list(self._fs_cookies or [])
            if isinstance(self.driver, _FlaresolverrSession):
                extra_cookies = list(self.driver.get_cookies()) + extra_cookies
            html, cookies = fetch_html_via_flaresolverr(url, cookies=extra_cookies)
            self._fs_html = html or ""
            init.logger.debug(f"Flaresolverr 直取 {url} -> {len(self._fs_html)} 字节")
            if cookies:
                self._fs_cookies = cookies
            if isinstance(self.driver, _FlaresolverrSession):
                self.driver.current_url = url
                self.driver.page_source = self._fs_html
            return

        if self.driver:
            try:
                self.driver.get(url)
                time.sleep(2)
            except Exception as e:
                init.logger.warn(f"Selenium导航失败: {e}")

    async def get_page_source(self):
        if self.use_flaresolverr_fetch:
            return self._fs_html or ""
        return await asyncio.get_running_loop().run_in_executor(self.executor, lambda: self.driver.page_source if self.driver else "")

    async def get_cookies(self):
        if self.use_flaresolverr_fetch:
            return list(self._fs_cookies or [])
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
        if self.use_flaresolverr_fetch:
            return  # Flaresolverr 返回的已是渲染完成的 HTML，无需等待元素
        if not self.driver: return
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((by, selector)))
        except: pass

    async def pass_cloudflare_check(self):
        await asyncio.get_running_loop().run_in_executor(self.executor, self._pass_cloudflare_check_sync)

    def _pass_cloudflare_check_sync(self):
        if self.use_flaresolverr_fetch:
            return  # Flaresolverr 取页时已在其内部浏览器中处理了 Cloudflare
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
