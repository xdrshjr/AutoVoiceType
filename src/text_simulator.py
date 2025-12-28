"""
文本输入模拟模块
负责将识别的文本自动输入到当前活动窗口的光标位置
实现多种输入方案以确保跨应用兼容性
"""
import logging
import time
from enum import Enum
from typing import Optional

import pyautogui
import pyperclip

try:
    import win32api
    import win32con
    import win32gui
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

logger = logging.getLogger(__name__)


class InputMethod(Enum):
    """输入方法枚举"""
    CLIPBOARD = "clipboard"  # 剪贴板方案（主方案）
    WIN32 = "win32"          # Win32 SendInput方案（备用）
    PYAUTOGUI = "pyautogui"  # pyautogui逐字输入方案（兜底）


class TextSimulator:
    """文本输入模拟器，负责将文本输入到当前活动窗口"""
    
    def __init__(self, config: Optional[dict] = None):
        """
        初始化文本输入模拟器
        
        Args:
            config: 配置字典，可包含输入方法偏好、延迟时间等
        """
        self.config = config or {}
        self._original_clipboard: Optional[str] = None
        
        # 获取配置
        self.preferred_method = self._get_preferred_method()
        self.input_delay = self.config.get('input_delay', 0.05)  # 字符间延迟（秒）
        self.paste_delay = self.config.get('paste_delay', 0.1)   # 粘贴前后延迟（秒）
        self.restore_clipboard = self.config.get('restore_clipboard', True)
        
        logger.info(
            f"文本输入模拟器初始化完成 - "
            f"首选方法: {self.preferred_method.value}, "
            f"Win32支持: {HAS_WIN32}"
        )
    
    def _get_preferred_method(self) -> InputMethod:
        """
        获取首选输入方法
        
        Returns:
            InputMethod: 首选的输入方法
        """
        method_str = self.config.get('preferred_method', 'clipboard').lower()
        
        try:
            return InputMethod(method_str)
        except ValueError:
            logger.warning(f"无效的输入方法配置: {method_str}，使用默认方法: clipboard")
            return InputMethod.CLIPBOARD
    
    def input_text(self, text: str) -> bool:
        """
        将文本输入到当前活动窗口
        使用三级降级策略确保兼容性
        
        Args:
            text: 要输入的文本
            
        Returns:
            bool: 是否成功输入
        """
        if not text:
            logger.warning("输入文本为空，跳过输入")
            return False
        
        logger.info(f"开始输入文本（长度: {len(text)}字符）")
        logger.debug(f"输入内容: {text}")
        
        # 尝试首选方法
        if self._try_input_with_method(text, self.preferred_method):
            return True
        
        # 首选方法失败，尝试降级
        logger.warning(f"首选方法 {self.preferred_method.value} 失败，尝试降级")
        
        # 尝试其他方法
        methods_to_try = [m for m in InputMethod if m != self.preferred_method]
        
        for method in methods_to_try:
            logger.info(f"尝试降级方法: {method.value}")
            if self._try_input_with_method(text, method):
                return True
        
        # 所有方法都失败
        logger.error("所有输入方法均失败")
        return False
    
    def _try_input_with_method(self, text: str, method: InputMethod) -> bool:
        """
        使用指定方法尝试输入文本
        
        Args:
            text: 要输入的文本
            method: 输入方法
            
        Returns:
            bool: 是否成功
        """
        try:
            if method == InputMethod.CLIPBOARD:
                return self._input_via_clipboard(text)
            elif method == InputMethod.WIN32:
                return self._input_via_win32(text)
            elif method == InputMethod.PYAUTOGUI:
                return self._input_via_pyautogui(text)
            else:
                logger.error(f"未知的输入方法: {method}")
                return False
        except Exception as e:
            logger.error(f"使用 {method.value} 方法输入时出错: {e}", exc_info=True)
            return False
    
    def _input_via_clipboard(self, text: str) -> bool:
        """
        通过剪贴板方案输入文本
        策略：备份剪贴板 -> 写入文本 -> 模拟Ctrl+V -> 恢复剪贴板
        
        Args:
            text: 要输入的文本
            
        Returns:
            bool: 是否成功
        """
        logger.debug("使用剪贴板方案输入文本")
        
        try:
            # 1. 备份当前剪贴板内容
            if self.restore_clipboard:
                try:
                    self._original_clipboard = pyperclip.paste()
                    logger.debug("剪贴板内容已备份")
                except Exception as e:
                    logger.warning(f"备份剪贴板失败: {e}")
                    self._original_clipboard = None
            
            # 2. 将文本写入剪贴板
            pyperclip.copy(text)
            logger.debug("文本已写入剪贴板")
            
            # 3. 短暂延迟，确保剪贴板更新完成
            time.sleep(self.paste_delay)
            
            # 4. 模拟Ctrl+V粘贴
            pyautogui.hotkey('ctrl', 'v')
            logger.debug("已执行Ctrl+V粘贴")
            
            # 5. 短暂延迟，等待粘贴完成
            time.sleep(self.paste_delay)
            
            # 6. 恢复原剪贴板内容
            if self.restore_clipboard and self._original_clipboard is not None:
                try:
                    pyperclip.copy(self._original_clipboard)
                    logger.debug("剪贴板内容已恢复")
                except Exception as e:
                    logger.warning(f"恢复剪贴板失败: {e}")
            
            logger.info("剪贴板方案输入成功")
            return True
        except Exception as e:
            logger.error(f"剪贴板方案输入失败: {e}", exc_info=True)
            
            # 尝试恢复剪贴板
            if self.restore_clipboard and self._original_clipboard is not None:
                try:
                    pyperclip.copy(self._original_clipboard)
                except:
                    pass
            
            return False
    
    def _input_via_win32(self, text: str) -> bool:
        """
        通过Win32 SendInput API输入文本
        
        Args:
            text: 要输入的文本
            
        Returns:
            bool: 是否成功
        """
        if not HAS_WIN32:
            logger.warning("Win32 API不可用，跳过此方法")
            return False
        
        logger.debug("使用Win32 SendInput方案输入文本")
        
        try:
            # 获取当前活动窗口
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                logger.error("无法获取当前活动窗口")
                return False
            
            logger.debug(f"当前活动窗口句柄: {hwnd}")
            
            # 使用pyautogui模拟键盘输入（更可靠）
            # 注意：pyautogui.write对中文支持较差，这里使用剪贴板方案
            # Win32 SendInput对中文支持需要特殊处理，实际实现较复杂
            # 因此此方法主要作为英文输入的备用方案
            
            # 检查是否包含中文
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
            
            if has_chinese:
                logger.debug("文本包含中文字符，Win32方案可能不适用")
                return False
            
            # 对于纯英文，使用pyautogui.write
            pyautogui.write(text, interval=self.input_delay)
            
            logger.info("Win32方案输入成功")
            return True
        except Exception as e:
            logger.error(f"Win32方案输入失败: {e}", exc_info=True)
            return False
    
    def _input_via_pyautogui(self, text: str) -> bool:
        """
        通过pyautogui逐字输入（兜底方案）
        注意：此方法速度较慢，但兼容性最好
        
        Args:
            text: 要输入的文本
            
        Returns:
            bool: 是否成功
        """
        logger.debug("使用pyautogui逐字输入方案")
        
        try:
            # pyautogui.write对中文支持不好，改用typewrite with interval
            # 但对于中文，仍建议使用剪贴板方案
            
            # 尝试使用pyautogui.typewrite
            # 注意：此方法对特殊字符和中文支持有限
            for char in text:
                try:
                    pyautogui.typewrite(char, interval=self.input_delay)
                except Exception as e:
                    # 如果单个字符输入失败，尝试直接按键
                    logger.debug(f"字符 '{char}' typewrite失败: {e}，尝试其他方式")
                    try:
                        pyautogui.press(char)
                    except:
                        logger.warning(f"字符 '{char}' 无法输入，跳过")
                        continue
                
                time.sleep(self.input_delay)
            
            logger.info("pyautogui逐字输入成功")
            return True
        except Exception as e:
            logger.error(f"pyautogui逐字输入失败: {e}", exc_info=True)
            return False
    
    def get_active_window_info(self) -> Optional[dict]:
        """
        获取当前活动窗口信息
        
        Returns:
            dict: 窗口信息字典，包含句柄、标题等，失败返回None
        """
        if not HAS_WIN32:
            logger.debug("Win32 API不可用，无法获取窗口信息")
            return None
        
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None
            
            window_title = win32gui.GetWindowText(hwnd)
            
            info = {
                'hwnd': hwnd,
                'title': window_title
            }
            
            logger.debug(f"活动窗口信息: {info}")
            return info
        except Exception as e:
            logger.error(f"获取活动窗口信息失败: {e}", exc_info=True)
            return None
    
    def set_input_method(self, method: InputMethod) -> None:
        """
        设置首选输入方法
        
        Args:
            method: 输入方法
        """
        self.preferred_method = method
        logger.info(f"首选输入方法已更新为: {method.value}")
    
    def test_input_methods(self) -> dict:
        """
        测试所有输入方法的可用性
        
        Returns:
            dict: 各方法的可用性测试结果
        """
        logger.info("开始测试输入方法可用性")
        
        results = {}
        test_text = "Test"
        
        for method in InputMethod:
            try:
                logger.debug(f"测试方法: {method.value}")
                
                # 特殊处理Win32方法
                if method == InputMethod.WIN32 and not HAS_WIN32:
                    results[method.value] = {
                        'available': False,
                        'reason': 'Win32 API不可用'
                    }
                    continue
                
                # 简单的可用性检查（不实际输入）
                if method == InputMethod.CLIPBOARD:
                    # 测试剪贴板读写
                    try:
                        original = pyperclip.paste()
                        pyperclip.copy(test_text)
                        pyperclip.copy(original)
                        results[method.value] = {'available': True}
                    except Exception as e:
                        results[method.value] = {
                            'available': False,
                            'reason': str(e)
                        }
                elif method == InputMethod.WIN32:
                    results[method.value] = {
                        'available': HAS_WIN32,
                        'reason': 'Win32 API可用' if HAS_WIN32 else 'Win32 API不可用'
                    }
                elif method == InputMethod.PYAUTOGUI:
                    # pyautogui通常都可用
                    results[method.value] = {'available': True}
                
                logger.debug(f"方法 {method.value} 测试结果: {results[method.value]}")
            except Exception as e:
                logger.error(f"测试方法 {method.value} 时出错: {e}")
                results[method.value] = {
                    'available': False,
                    'reason': str(e)
                }
        
        logger.info(f"输入方法测试完成: {results}")
        return results

