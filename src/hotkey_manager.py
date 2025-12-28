"""
全局快捷键管理模块
负责监听全局键盘事件，检测右Ctrl键的按下和释放
"""
import logging
import threading
from typing import Callable, Optional

from pynput import keyboard

logger = logging.getLogger(__name__)


class HotkeyManager:
    """全局快捷键管理器，监听右Ctrl键的按下和释放事件"""
    
    def __init__(self):
        """初始化快捷键管理器"""
        self.listener: Optional[keyboard.Listener] = None
        self.is_listening = False
        self._press_callback: Optional[Callable] = None
        self._release_callback: Optional[Callable] = None
        self._is_key_pressed = False  # 标记键是否正在按下（防止重复触发）
        
        logger.info("快捷键管理器初始化完成")
    
    def set_callbacks(
        self, 
        on_press: Optional[Callable] = None, 
        on_release: Optional[Callable] = None
    ) -> None:
        """
        设置按键回调函数
        
        Args:
            on_press: 按键按下时的回调函数
            on_release: 按键释放时的回调函数
        """
        self._press_callback = on_press
        self._release_callback = on_release
        logger.debug("回调函数已设置")
    
    def is_right_ctrl(self, key) -> bool:
        """
        判断按键是否为右Ctrl键
        
        Args:
            key: pynput键对象
            
        Returns:
            bool: 是否为右Ctrl键
        """
        # 方法1：通过key.vk虚拟键码判断（更准确）
        # VK_RCONTROL = 0xA3 (163)
        if hasattr(key, 'vk') and key.vk == 0xA3:
            return True
        
        # 方法2：通过键名判断（备用方案）
        try:
            if key == keyboard.Key.ctrl_r:
                return True
        except AttributeError:
            pass
        
        return False
    
    def _on_press(self, key) -> None:
        """
        按键按下事件处理
        
        Args:
            key: 按下的键
        """
        try:
            # 只处理右Ctrl键
            if self.is_right_ctrl(key):
                # 防止重复触发（按住时会持续触发按下事件）
                if not self._is_key_pressed:
                    self._is_key_pressed = True
                    logger.debug("右Ctrl键按下")
                    
                    # 调用用户定义的回调函数
                    if self._press_callback:
                        try:
                            self._press_callback()
                        except Exception as e:
                            logger.error(f"执行按键按下回调函数时出错: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"处理按键按下事件时出错: {e}", exc_info=True)
    
    def _on_release(self, key) -> None:
        """
        按键释放事件处理
        
        Args:
            key: 释放的键
        """
        try:
            # 只处理右Ctrl键
            if self.is_right_ctrl(key):
                if self._is_key_pressed:
                    self._is_key_pressed = False
                    logger.debug("右Ctrl键释放")
                    
                    # 调用用户定义的回调函数
                    if self._release_callback:
                        try:
                            self._release_callback()
                        except Exception as e:
                            logger.error(f"执行按键释放回调函数时出错: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"处理按键释放事件时出错: {e}", exc_info=True)
    
    def start_listening(self) -> bool:
        """
        启动全局键盘监听
        
        Returns:
            bool: 是否成功启动
        """
        if self.is_listening:
            logger.warning("监听器已经在运行中")
            return False
        
        try:
            # 创建键盘监听器
            self.listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            
            # 启动监听器（在独立线程中运行）
            self.listener.start()
            self.is_listening = True
            
            logger.info("全局键盘监听已启动")
            return True
        except Exception as e:
            logger.error(f"启动键盘监听失败: {e}", exc_info=True)
            return False
    
    def stop_listening(self) -> bool:
        """
        停止全局键盘监听
        
        Returns:
            bool: 是否成功停止
        """
        if not self.is_listening:
            logger.warning("监听器未在运行")
            return False
        
        try:
            if self.listener:
                self.listener.stop()
                self.listener = None
            
            self.is_listening = False
            self._is_key_pressed = False
            
            logger.info("全局键盘监听已停止")
            return True
        except Exception as e:
            logger.error(f"停止键盘监听失败: {e}", exc_info=True)
            return False
    
    def is_key_currently_pressed(self) -> bool:
        """
        检查右Ctrl键当前是否处于按下状态
        
        Returns:
            bool: 是否按下
        """
        return self._is_key_pressed
    
    def __del__(self):
        """析构函数，确保资源释放"""
        if self.is_listening:
            self.stop_listening()

