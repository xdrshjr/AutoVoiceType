"""
自动启动管理模块
处理Windows注册表操作，实现开机自启动功能
"""
import logging
import sys
from pathlib import Path
from typing import Optional

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

logger = logging.getLogger(__name__)


class AutoStartManager:
    """自动启动管理器"""
    
    # 注册表路径
    REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
    APP_NAME = "AutoVoiceType"
    
    def __init__(self):
        """初始化自动启动管理器"""
        if not HAS_WINREG:
            logger.warning("winreg模块不可用，自动启动功能将被禁用")
        
        logger.info("自动启动管理器初始化完成")
    
    def is_enabled(self) -> bool:
        """
        检查自动启动是否已启用
        
        Returns:
            bool: 是否已启用自动启动
        """
        if not HAS_WINREG:
            logger.warning("winreg不可用，无法检查自动启动状态")
            return False
        
        try:
            # 打开注册表键
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REG_PATH,
                0,
                winreg.KEY_READ
            )
            
            # 尝试读取值
            try:
                value, _ = winreg.QueryValueEx(key, self.APP_NAME)
                winreg.CloseKey(key)
                
                # 检查值是否指向当前可执行文件
                current_exe = self._get_executable_path()
                is_enabled = (value == current_exe)
                
                logger.debug(f"自动启动状态: {'已启用' if is_enabled else '未启用'}")
                return is_enabled
            except FileNotFoundError:
                winreg.CloseKey(key)
                logger.debug("注册表中未找到自动启动项")
                return False
        except Exception as e:
            logger.error(f"检查自动启动状态失败: {e}", exc_info=True)
            return False
    
    def enable(self) -> bool:
        """
        启用自动启动
        
        Returns:
            bool: 是否成功启用
        """
        if not HAS_WINREG:
            logger.error("winreg不可用，无法启用自动启动")
            return False
        
        try:
            # 获取可执行文件路径
            exe_path = self._get_executable_path()
            
            logger.info(f"启用自动启动: {exe_path}")
            
            # 打开注册表键
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REG_PATH,
                0,
                winreg.KEY_WRITE
            )
            
            # 设置值
            winreg.SetValueEx(
                key,
                self.APP_NAME,
                0,
                winreg.REG_SZ,
                exe_path
            )
            
            winreg.CloseKey(key)
            
            logger.info("自动启动已成功启用")
            return True
        except PermissionError:
            logger.error("权限不足，无法修改注册表。请以管理员权限运行程序。")
            return False
        except Exception as e:
            logger.error(f"启用自动启动失败: {e}", exc_info=True)
            return False
    
    def disable(self) -> bool:
        """
        禁用自动启动
        
        Returns:
            bool: 是否成功禁用
        """
        if not HAS_WINREG:
            logger.error("winreg不可用，无法禁用自动启动")
            return False
        
        try:
            logger.info("禁用自动启动")
            
            # 打开注册表键
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                self.REG_PATH,
                0,
                winreg.KEY_WRITE
            )
            
            # 删除值
            try:
                winreg.DeleteValue(key, self.APP_NAME)
                logger.info("自动启动已成功禁用")
                success = True
            except FileNotFoundError:
                logger.warning("自动启动项不存在，无需删除")
                success = True
            
            winreg.CloseKey(key)
            return success
        except PermissionError:
            logger.error("权限不足，无法修改注册表。请以管理员权限运行程序。")
            return False
        except Exception as e:
            logger.error(f"禁用自动启动失败: {e}", exc_info=True)
            return False
    
    def toggle(self) -> bool:
        """
        切换自动启动状态
        
        Returns:
            bool: 切换后的状态（True=已启用，False=已禁用）
        """
        if self.is_enabled():
            self.disable()
            return False
        else:
            self.enable()
            return True
    
    def _get_executable_path(self) -> str:
        """
        获取当前可执行文件的路径
        
        Returns:
            str: 可执行文件路径
        """
        if getattr(sys, 'frozen', False):
            # 打包后的可执行文件
            exe_path = sys.executable
        else:
            # 开发环境中，使用Python解释器 + 脚本路径
            script_path = Path(__file__).parent.parent / "main.py"
            exe_path = f'"{sys.executable}" "{script_path}"'
        
        logger.debug(f"可执行文件路径: {exe_path}")
        return exe_path
    
    @staticmethod
    def is_supported() -> bool:
        """
        检查当前系统是否支持自动启动功能
        
        Returns:
            bool: 是否支持
        """
        return HAS_WINREG and sys.platform == 'win32'

