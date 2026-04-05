from random import choice
from bs4 import BeautifulSoup as bs
import logging
import re
import schedule
from ping3 import ping
logging.basicConfig(level=logging.INFO,format="%(asctime)s | %(name)s | %(levelname)s | %(message)s", datefmt="%m-%d %H:%M:%S")
logger = logging.getLogger("Main")
import threading
import asyncio
import time
import argparse
from datetime import datetime
import os
import json
from PlaywrightContextManager import *
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from typing import Dict, List
from demo1 import f_work
from copy import deepcopy

praser = argparse.ArgumentParser(
    description="Bilibili Ads Collector - Collects advertisements from Bilibili homepage",
    epilog="Example usage: python main.py --beacon_rate 30 --test 0")
praser.add_argument('--beacon_rate', type=int, default=40, help="Interval in minutes between each collection cycle (default: 40)")
praser.add_argument('--test', type=int, default=0, help="Run mode: 0 for continuous scheduling, 1 for single test run (default: 0)", choices=[0,1])
praser.add_argument('--file', action="store_true", help="Enable specific feature by reading configuration from JSON file in the same directory")
praser.add_argument('--type', type=str, default="chrome", help="Browser type: chrome or firefox (default: chrome)")
args = praser.parse_args()
# Logger DEF
ping_logger = logging.getLogger("PingModule")
ping_logger.setLevel(logging.INFO)

main_logger = logging.getLogger("Index_Collector")
main_logger.setLevel(logging.INFO)

Download_Logger = logging.getLogger("Download_Module")
Download_Logger.setLevel(logging.INFO)


part = r'path/to/PC_UA'
all = r"path/to/All_UA"
if args.file:
    with open("config.json", "r") as f:
        config = json.load(f)
        part :str = config["part"]
        all :str = config["all"]
chrome_flag = False
firefox_flag = False
if args.type == "chrome":
    chrome_flag = True
elif args.type == "firefox":
    firefox_flag = True

args_for_chrome = ["--headless=new", "--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox", "--disable-extensions", "--disable-plugins", "--disable-default-apps", "--window-size=1920,1080", "--disable-infobars"]
args_for_firefox={
                "permissions.default.image": 2,  # 禁用图片加载
                "media.autoplay.enabled": False,
                "useAutomationExtension": False,
                "dom.webdriver.enabled": False,
            }

def read_from(path) -> List[str]:
    try:
        with open(path, "r") as f:
            ua = f.readlines()
            return ua
    except FileNotFoundError:
        logger.error("Please edit the config.json to enter the ua file route.")
        os._exit(1)
def randua(path) -> str:
    ua_str = choice(read_from(path)).strip("\n")
    return ua_str
headers = {"Referer": r"https://www.bilibili.com/",
"Accept-Language": "zh-CN,zh;q=0.9",
"Cache-Control": "no-cache",
"Pragma": "no-cache",
"Upgrade-Insecure-Requests": "1",
"Priority": "i",
"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.26",
"Accept": "*",
"Accept-Encoding": "gzip, deflate, br, zstd"}
def ping_test(times: int) -> int | None:
    ping_results = set()
    for _ in range(times+1):
        tempval = ping("www.bilibili.com", unit="ms", ttl=64)
        if isinstance(tempval, float):
            ping_results.add(tempval)
            ping_logger.debug(f"Ping result: {tempval:.4f} ms")
    if len(ping_results) == 0:
        ping_logger.error("Ping failed, please check your network connection.")
        ping_logger.error(f"Occurred at {datetime.now():%Y-%m-%d %H:%M:%S}")
        return None
    else:
        avg_ping = sum(ping_results) / len(ping_results)
        ping_logger.info(f"Avg Ping: {avg_ping:.4f} ms")
        return 0

def index_collector():
    main_logger.info("Started. ")
    internet_con_check = ping_test(5)
    if isinstance(internet_con_check, int):
        pass
    else:
        main_logger.error("No Internet Connection. Exiting Current Wave...")
        return None
    response = playwright_dynamic_load_method(selector="div.vui_carousel__slides") #playwright式获取动态内容，可改动等待元素
    if response is None:
        return None
    matchobj = re.search(r"vui_carousel vui_carousel--bottom vui_carousel--show-arrow", response)
    if matchobj is None:
        main_logger.error("HTML changed, upgrade pattern ASAP.")
        os._exit(1)
    soup = bs(response, "lxml")
    main_logger.info(matchobj.group()+" found. ")
    container = {}
    carousel = soup.find_all("div", attrs={"class": "vui_carousel vui_carousel--bottom vui_carousel--show-arrow"})
    all_imgs = carousel[0]
    all_imgs = all_imgs.find_all("img")
    for img in all_imgs:
        title = img.attrs.get("alt")
        address = img.attrs.get("src")
        if title and address:
            container[title] = address
            main_logger.debug(f"\n标题：{title}\n链接：{address}")
    download(container)
    main_logger.warning(f"Ends At {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("-" * 120)
    cleanup_global_playwright()
def sanitize_filename(name: str):
    # 替换非法字符为下划线（跨平台兼容）
    return re.sub(r'[\\/:*?"<>|]', '_', name.strip())

# 获取日志器用于tenacity
tenacity_logger = logging.getLogger("tenacity.retry")
def playwright_dynamic_load_method(
    url: str = "https://www.bilibili.com",
    selector: str = "div.vui_carousel__slides",
    timeout_ms: int = 120000,
    max_retries: int = 10  # 这里的重试次数将完全由@retry控制
):
    @retry(
        stop=stop_after_attempt(max_retries + 1),  # 总尝试次数 = 初始1次 + 重试max_retries次
        wait=wait_exponential(multiplier=1, min=2, max=10),  # 指数退避: 2s, 4s...最大10s
        retry=retry_if_exception_type((PlaywrightTimeoutError, PlaywrightError)),
        before_sleep=before_sleep_log(tenacity_logger, logging.WARNING)  # 重试前打印日志
    )
    def _load_operation():
        """封装需要重试的核心操作"""
        # 注意：每次重试都会创建新的浏览器实例，确保环境干净
        rtval = basic_load(chrome_flag, url, selector)
        return rtval
    try:
        logger.info(f"开始加载页面，最大重试次数: {max_retries}")
        source = _load_operation()  # 这个调用会自动重试
        logger.info(f"页面加载成功。")
        cleanup_global_playwright()
        return source
    except (PlaywrightTimeoutError, PlaywrightError) as e:
        # 所有重试耗尽后仍失败，在这里记录最终错误
        logger.error(f"页面加载失败，已重试{max_retries}次。最终错误: {e}")
        return None
    except Exception as e:
        # 捕获非Playwright的其他异常，这类错误通常重试无效
        logger.error(f"发生非预期错误，未进行重试: {e}", exc_info=True)
        return None

# 程序最终退出时，确保清理全局资源
# atexit.register(cleanup_global_playwright)
def basic_load(chrome_flag: bool, url: str, selector: str):
    """
    加载页面并返回HTML源码

    :param chrome_flag: 是否使用Chrome浏览器
    :param url: 要加载的URL
    :param selector: 用于等待的元素选择器
    :return: HTML源码
    """
    if chrome_flag is True:
        firefox_prefs = None
        extra_args = args_for_chrome
        browsertype = "chromium"
        executable_path = r"E:\Chrome\chrome.exe"
    else:
        firefox_prefs = args_for_firefox
        extra_args = ["--headless"]
        browsertype = "firefox"
        executable_path = None

    with managed_playwright_browser(
        headless=True,
        user_agent=randua(part),
        channel=browsertype,
        firefox_prefs=firefox_prefs,
        executable_path=executable_path,
        extra_args=extra_args,
        reuse_playwright=False
    ) as res:
        page: Page = res["page"]
        page.set_default_timeout(120000)
        page.goto(url)
        page.wait_for_load_state("domcontentloaded")
        page.locator(selector).wait_for(state="visible", timeout=120000)
        real_ua = page.evaluate("window.navigator.userAgent")
        logger.info(f"Real UA: {real_ua}")
        return page.content()
def gen_new_headers(headers: Dict[str, str], new_headers: Dict[str, str] = dict()):
    """
    生成新的headers

    :param headers: 旧headers
    :param new_headers: 新headers
    :return new_headers: 新headers
    """
    new_headers = deepcopy(headers)
    new_headers['User-Agent'] = randua(all)
    new_headers['Priority'] = "u=5, i"
    new_headers['Sec-Fetch-Dest'] = "image"
    new_headers['Sec-Fetch-Mode'] = "no-cors"
    new_headers['Sec-Fetch-Site'] = "cross-site"
    new_headers['Accept'] = "image/*;q=0.9,*/*;q=0.6"
    new_headers['TE'] = "trailers"
    return new_headers
async def batch_download(dictobj: Dict, headers: Dict[str, str] =headers):
    tasks = [asyncio.create_task(f_work(key, value, gen_new_headers(headers))) for key, value in dictobj.items()]
    for results in asyncio.as_completed(tasks):
        try:
            result = await results
            Download_Logger.info(result)
        except Exception as e:
            Download_Logger.error(e)


def download(dictobj: Dict, headers: Dict[str, str] =headers):
    downloader_dict = {}
    cleanup_global_playwright()
    current_month = datetime.now().strftime("%Y%m")
    os.makedirs(current_month, exist_ok=True)
    for key, value in dictobj.items():
        name = sanitize_filename(key)
        filename = f"{name}.webp"
        full_path = os.path.join(current_month, filename)
        if os.path.exists(full_path):  # 检查文件是否存在
            Download_Logger.info(f"\n\nSkipped (already exists): {full_path}\n\n")
            print("-" * 120)
        else:
            downloader_dict[key] = value
    if len(downloader_dict) == 0:  # 如果字典为空，则返回
        pass
    else:
        Download_Logger.info(f"Found {len(downloader_dict)} items to download. ")
        for key, value in downloader_dict.items():
            name = sanitize_filename(key)
            filename = f"{name}.webp"
            full_path = os.path.join(current_month, filename)
            url = value
            if ("@" in url) is False:
                Download_Logger.error("URL is not valid.")
                continue
            url = re.search(r"//(.*?)@", url)
            if url and isinstance(url.group(0), str):  # 检查url.group(0)是否为字符串
                url = url.group(0).strip("@")
                url = f"https:{url}"
            else:
                Download_Logger.error("URL is not a string.")
                continue
        try:
            new_headers = gen_new_headers(headers)
            asyncio.run(batch_download(downloader_dict, new_headers))
        except Exception as e:
            Download_Logger.error(e)

        
            #img_bytes = response.content
            #original_filename_saver(key, full_path, img_bytes, url)
        
            #logger.info(f"Using User-Agent: {new_headers['User-Agent']}")
    print("-" * 120)
    cleanup_global_playwright()

def run_scheduler():
    schedule.every(args.beacon_rate).minutes.do(index_collector)
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():
    if args.test == 1:
        index_collector()
    else:
        index_collector()
        thread = threading.Thread(target=run_scheduler)
        thread.daemon = True
        thread.start()
        
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.warning("Mannual stop occurred.")
            cleanup_global_playwright()

if __name__ == "__main__":
    main()