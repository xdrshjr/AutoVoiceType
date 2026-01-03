"""
Windows特定的图标工具模块
使用Windows API来设置任务栏图标
"""
import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 尝试导入Windows API
try:
    import win32gui
    import win32con
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logger.warning("win32api不可用，Windows特定图标功能将不可用")


def set_window_icon_win32(hwnd: int, icon_path: str) -> bool:
    """
    使用Windows API设置窗口图标
    
    Args:
        hwnd: 窗口句柄
        icon_path: 图标文件路径
        
    Returns:
        bool: 是否设置成功
    """
    if not HAS_WIN32:
        logger.debug("Win32 API不可用，跳过Windows API图标设置")
        return False
    
    try:
        # 加载图标
        icon_handle = win32gui.LoadImage(
            0,  # hInst: 0表示从文件加载
            icon_path,
            win32con.IMAGE_ICON,  # 类型：图标
            0,  # 宽度：0表示使用默认大小
            0,  # 高度：0表示使用默认大小
            win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE  # 从文件加载，使用默认大小
        )
        
        if icon_handle == 0:
            error_code = win32api.GetLastError()
            logger.error(f"加载图标失败: {icon_path}, 错误代码: {error_code}")
            return False
        
        # 设置窗口图标（小图标和大图标）
        # WM_SETICON消息用于设置窗口图标
        # ICON_SMALL = 0, ICON_BIG = 1
        
        # 设置小图标（16x16，用于任务栏）
        win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, icon_handle)
        
        # 设置大图标（32x32，用于Alt+Tab等）
        win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, icon_handle)
        
        logger.info(f"使用Windows API成功设置窗口图标: {icon_path}")
        logger.debug(f"窗口句柄: {hwnd}")
        
        return True
    except Exception as e:
        logger.error(f"使用Windows API设置图标时发生异常: {e}", exc_info=True)
        return False


def set_qt_window_icon_win32(window, icon_path: str) -> bool:
    """
    为PyQt5窗口设置Windows任务栏图标
    
    Args:
        window: PyQt5窗口对象（QMainWindow, QDialog等）
        icon_path: 图标文件路径
        
    Returns:
        bool: 是否设置成功
    """
    if not HAS_WIN32:
        logger.debug("Win32 API不可用，跳过Windows API图标设置")
        return False
    
    try:
        # 确保窗口已经创建（显示后才能获取有效的句柄）
        if not window.isVisible():
            logger.debug("窗口未显示，无法获取窗口句柄")
            return False
        
        # 获取窗口的Win32句柄
        # PyQt5的winId()返回一个整数句柄
        hwnd = window.winId()
        
        if hwnd is None:
            logger.warning("窗口句柄为None，跳过Windows API图标设置")
            return False
        
        # 转换为整数（PyQt5可能返回不同的类型）
        try:
            hwnd_int = int(hwnd)
        except (ValueError, TypeError):
            logger.warning(f"无法将窗口句柄转换为整数: {hwnd}, 类型: {type(hwnd)}")
            return False
        
        if hwnd_int == 0:
            logger.warning("窗口句柄为0，跳过Windows API图标设置")
            return False
        
        logger.debug(f"获取到窗口句柄: {hwnd_int} (原始值: {hwnd})")
        
        # 使用Windows API设置图标
        return set_window_icon_win32(hwnd_int, icon_path)
    except Exception as e:
        logger.error(f"为PyQt5窗口设置Windows图标时发生异常: {e}", exc_info=True)
        return False

