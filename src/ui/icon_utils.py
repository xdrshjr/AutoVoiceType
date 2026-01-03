"""
图标工具模块
提供统一的图标加载功能，支持开发环境和打包环境
"""
import logging
import sys
from pathlib import Path
from typing import Optional

from PyQt5.QtGui import QIcon

logger = logging.getLogger(__name__)


def get_icon_path() -> Optional[Path]:
    """
    获取图标文件路径
    优先查找 logo.ico（Windows任务栏需要ICO格式），如果找不到则查找 logo.svg
    
    Returns:
        Optional[Path]: 图标文件路径，如果不存在则返回 None
    """
    # 优先使用ICO格式（Windows任务栏需要）
    icon_filenames = ["logo.ico", "logo.svg"]
    
    # 检测运行环境
    if getattr(sys, 'frozen', False):
        # 打包环境：尝试多个可能的路径
        base_paths = [
            Path(sys.executable).parent,  # exe 所在目录
            Path(sys.executable).parent / "_internal",  # _internal 目录
        ]
        
        # 如果存在 _MEIPASS（PyInstaller 临时目录）
        if hasattr(sys, '_MEIPASS'):
            base_paths.insert(0, Path(sys._MEIPASS))
        
        logger.debug(f"检测到打包环境，尝试路径: {[str(p) for p in base_paths]}")
    else:
        # 开发环境：使用项目根目录
        base_paths = [
            Path(__file__).parent.parent.parent,  # 从 src/ui/icon_utils.py 向上到项目根目录
        ]
        logger.debug(f"检测到开发环境，尝试路径: {[str(p) for p in base_paths]}")
    
    # 按优先级尝试查找图标文件（先ICO，后SVG）
    for icon_filename in icon_filenames:
        logger.debug(f"尝试查找图标文件: {icon_filename}")
        
        for base_path in base_paths:
            icon_path = base_path / "assets" / icon_filename
            logger.debug(f"尝试图标路径: {icon_path}")
            
            if icon_path.exists():
                logger.info(f"找到图标文件: {icon_path} (格式: {icon_filename.split('.')[-1].upper()})")
                logger.debug(f"图标文件大小: {icon_path.stat().st_size} 字节")
                return icon_path
    
    # 如果所有路径和格式都找不到，记录警告
    all_attempted_paths = []
    for base_path in base_paths:
        for icon_filename in icon_filenames:
            all_attempted_paths.append(str(base_path / "assets" / icon_filename))
    
    logger.warning(f"未找到图标文件，尝试的所有路径: {all_attempted_paths}")
    return None


def get_app_icon() -> QIcon:
    """
    获取应用图标
    
    Returns:
        QIcon: 应用图标对象，如果加载失败则返回空图标
    """
    logger.info("=" * 50)
    logger.info("开始加载应用图标")
    
    icon_path = get_icon_path()
    
    if icon_path is None:
        logger.error("无法找到图标文件，返回空图标")
        logger.error("这将导致Windows任务栏显示默认图标（如Python/Anaconda图标）")
        return QIcon()  # 返回空图标
    
    try:
        icon_format = icon_path.suffix.upper().lstrip('.')
        logger.info(f"尝试加载图标文件")
        logger.info(f"  路径: {icon_path}")
        logger.info(f"  格式: {icon_format}")
        logger.debug(f"  绝对路径: {icon_path.resolve()}")
        logger.debug(f"  文件是否存在: {icon_path.exists()}")
        logger.debug(f"  文件大小: {icon_path.stat().st_size} 字节")
        
        # 使用绝对路径加载图标，确保路径正确
        icon_absolute_path = str(icon_path.resolve())
        logger.debug(f"使用绝对路径加载: {icon_absolute_path}")
        
        icon = QIcon(icon_absolute_path)
        
        # 验证图标是否有效
        if icon.isNull():
            logger.error("=" * 50)
            logger.error(f"图标文件加载失败: {icon_path}")
            logger.error(f"格式: {icon_format}")
            logger.error("图标对象为空，可能原因：")
            logger.error("  1. 文件格式不支持（PyQt5可能不支持某些ICO格式）")
            logger.error("  2. 文件损坏")
            logger.error("  3. 文件路径不正确")
            logger.error("这将导致Windows任务栏显示默认图标（如Python/Anaconda图标）")
            logger.error("=" * 50)
            return QIcon()
        
        # 验证图标是否包含有效的尺寸
        available_sizes = icon.availableSizes()
        if available_sizes:
            size_list = [f'{s.width()}x{s.height()}' for s in available_sizes]
            logger.info(f"成功加载应用图标")
            logger.info(f"  路径: {icon_path}")
            logger.info(f"  格式: {icon_format}")
            logger.info(f"  可用尺寸: {', '.join(size_list)}")
            logger.debug(f"图标文件大小: {icon_path.stat().st_size} 字节")
            logger.info("=" * 50)
        else:
            logger.warning("=" * 50)
            logger.warning(f"图标已加载但无可用尺寸: {icon_path} (格式: {icon_format})")
            logger.warning("这可能导致图标在某些情况下无法正常显示")
            logger.warning("=" * 50)
        
        return icon
    except Exception as e:
        logger.error("=" * 50)
        logger.error(f"加载图标时发生异常: {e}", exc_info=True)
        logger.error("这将导致Windows任务栏显示默认图标（如Python/Anaconda图标）")
        logger.error("=" * 50)
        return QIcon()  # 返回空图标

