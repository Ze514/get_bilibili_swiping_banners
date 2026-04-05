from contextlib import contextmanager
from typing import Optional, Dict, Generator, Any
import logging
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright

logger = logging.getLogger(__name__)

# 模块级全局变量
_global_playwright: Optional[Playwright] = None
_global_browser: Optional[Browser] = None

@contextmanager
def managed_playwright_browser(
    headless: bool = True,
    user_agent: Optional[str] = None,
    viewport: Optional[Dict] = None,
    browser_type: str = "chromium",  # 可选: chromium, firefox, webkit
    channel: Optional[str] = None,  # Firefox 不支持 channel
    executable_path: Optional[str] = None,
    extra_args: Optional[list] = None,
    firefox_prefs: Optional[Dict] = None,  # 🔥 新增：Firefox 首选项
    reuse_playwright: bool = False
) -> Generator[Dict[str, Any], None, None]:
    """
    增强版Playwright浏览器上下文管理器（支持多浏览器）
    
    Args:
        browser_type: 浏览器类型，支持 "chromium", "firefox", "webkit"
        firefox_prefs: Firefox 特有的首选项配置
        ... 其他参数保持不变 ...
    """
    global _global_playwright, _global_browser
    
    playwright_instance: Optional[Playwright] = None
    browser: Optional[Browser] = None
    context: Optional[BrowserContext] = None
    page: Optional[Page] = None
    
    try:
        # 1. 创建或复用Playwright实例
        if reuse_playwright and _global_playwright:
            playwright_instance = _global_playwright
            logger.debug("复用全局Playwright实例")
        else:
            playwright_instance = sync_playwright().start()
            logger.info("创建新的Playwright实例")
            if reuse_playwright:
                _global_playwright = playwright_instance
        
        # 2. 浏览器启动参数配置 - 根据不同浏览器类型调整
        launch_options = {
            "headless": headless,
            "args": []
        }
        if user_agent:
            logger.info(f"设置自定义UA: {user_agent}")
        
        # 添加默认参数（根据浏览器类型）
        if browser_type == "chromium" or browser_type == "chrome":
            launch_options["args"].extend([
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ])
            if extra_args:
                launch_options["args"].extend(extra_args)
            
            if executable_path:
                launch_options["executable_path"] = executable_path
            elif channel:
                launch_options["channel"] = channel
                
        elif browser_type == "firefox":
            # Firefox 特定的启动配置
            launch_options["args"].extend([
                "--no-sandbox",  # Linux 环境可能需要
            ])
            if extra_args:
                launch_options["args"].extend(extra_args)
            
            # Firefox 不支持 executable_path 和 channel
            if executable_path:
                logger.warning("Firefox 不支持 executable_path 参数，将忽略")
            
            # 添加 Firefox 首选项
            if firefox_prefs:
                launch_options["firefox_user_prefs"] = firefox_prefs
                
        elif browser_type == "webkit":
            # WebKit 特定配置
            if extra_args:
                launch_options["args"].extend(extra_args)
        
        # 3. 创建或复用浏览器实例
        if reuse_playwright and _global_browser and _global_browser.is_connected():
            browser = _global_browser
            logger.debug("复用全局浏览器实例")
        else:
            # 根据浏览器类型选择启动方法
            browser_launcher = getattr(playwright_instance, browser_type)
            browser = browser_launcher.launch(**launch_options)
            logger.info(f"启动 {browser_type} 浏览器")
            
            if reuse_playwright:
                _global_browser = browser
        
        # 4. 创建浏览器上下文
        context_options = {}
        if user_agent:
            pass
        if viewport:
            context_options["viewport"] = viewport
        
        # Firefox 特定的上下文选项
        if browser_type == "firefox" and firefox_prefs:
            # 部分首选项也可以在上下文级别设置
            pass
        
        context = browser.new_context(**context_options, 
        user_agent=user_agent, 
        locale="zh-CN", 
        geolocation={"latitude": 34.50, "longitude": 121.43, "accuracy": 100}, 
        timezone_id="Asia/Shanghai", 
        viewport={"width": 1920, "height": 1080})
        logger.debug("创建浏览器上下文")
        
        # 5. 创建页面
        page = context.new_page()
        page.set_default_timeout(30000)
        logger.debug("创建新页面")
        
        # 6. 返回资源字典
        yield {
            "playwright": playwright_instance,
            "browser": browser,
            "context": context,
            "page": page,
            "browser_type": browser_type
        }
        
    except Exception as launch_error:
        logger.error(f"启动 {browser_type} 浏览器失败: {launch_error}")
        error_msg = f"""
        启动配置详情:
        - browser_type: {browser_type}
        - headless: {headless}
        - extra_args: {extra_args}
        错误: {str(launch_error)}
        """
        logger.error(error_msg)
        raise RuntimeError(f"无法启动浏览器: {launch_error}") from launch_error
        
    finally:
        # 7. 资源清理（与之前相同，但已修正 is_closed 问题）
        cleanup_success = True
        
        # 清理页面
        if page and not page.is_closed():
            try:
                page.close()
                logger.debug("页面已关闭")
            except Exception as page_error:
                logger.warning(f"关闭页面时出错: {page_error}")
                cleanup_success = False
        
        # 清理上下文 - 修正：移除 is_closed() 检查
        if context:
            try:
                context.close()
                logger.debug("上下文已关闭")
            except Exception as context_error:
                logger.debug(f"关闭上下文时遇到预期内异常: {context_error}")
        
        # 清理浏览器实例（如果不复用）
        if not reuse_playwright:
            if browser and browser.is_connected():
                try:
                    browser.close()
                    logger.info(f"{browser_type} 浏览器实例已关闭")
                except Exception as browser_error:
                    logger.warning(f"关闭浏览器时出错: {browser_error}")
                    cleanup_success = False
        
        # 清理Playwright实例（如果不复用）
        if not reuse_playwright and playwright_instance:
            try:
                playwright_instance.stop()
                logger.info("Playwright实例已停止")
            except Exception as playwright_error:
                logger.warning(f"停止Playwright时出错: {playwright_error}")
                cleanup_success = False
        
        if not cleanup_success:
            logger.error("资源清理过程中出现错误，可能存在资源泄漏风险")


def cleanup_global_playwright():
    """清理全局复用的Playwright和浏览器实例"""
    global _global_browser, _global_playwright
    
    if _global_browser and _global_browser.is_connected():
        try:
            _global_browser.close()
            logger.info("全局浏览器实例已关闭")
        except Exception as e:
            logger.error(f"关闭全局浏览器失败: {e}")
        finally:
            _global_browser = None
    
    if _global_playwright:
        try:
            _global_playwright.stop()
            logger.info("全局Playwright实例已停止")
        except Exception as e:
            logger.error(f"停止全局Playwright失败: {e}")
        finally:
            _global_playwright = None