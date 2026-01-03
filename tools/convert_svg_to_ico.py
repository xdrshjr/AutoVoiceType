"""
SVG 转 ICO 工具脚本
将 logo.svg 转换为 icon.ico，用于 PyInstaller 打包
"""
import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from PyQt5.QtGui import QIcon, QPixmap, QPainter
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtCore import QSize

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def svg_to_ico(svg_path: Path, ico_path: Path, sizes: list = None) -> bool:
    """
    将 SVG 文件转换为 ICO 文件
    
    Args:
        svg_path: SVG 文件路径
        ico_path: 输出的 ICO 文件路径
        sizes: ICO 文件包含的尺寸列表，默认 [16, 32, 48, 64, 128, 256]
    
    Returns:
        bool: 是否转换成功
    """
    if sizes is None:
        sizes = [16, 32, 48, 64, 128, 256]
    
    logger.info(f"开始转换 SVG 到 ICO: {svg_path} -> {ico_path}")
    
    if not svg_path.exists():
        logger.error(f"SVG 文件不存在: {svg_path}")
        return False
    
    try:
        # 创建 SVG 渲染器
        renderer = QSvgRenderer(str(svg_path))
        
        if not renderer.isValid():
            logger.error(f"SVG 文件无效: {svg_path}")
            return False
        
        # 创建 QIcon 对象
        icon = QIcon()
        
        # 为每个尺寸创建像素图并添加到图标
        for size in sizes:
            pixmap = QPixmap(size, size)
            pixmap.fill()  # 填充透明背景
            
            # 渲染 SVG 到像素图
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            renderer.render(painter)
            painter.end()
            
            # 添加到图标
            icon.addPixmap(pixmap)
            logger.debug(f"已添加 {size}x{size} 尺寸的图标")
        
        # 保存为 ICO 文件
        # 注意：QIcon 不能直接保存为 ICO，需要使用其他方法
        # 这里我们使用 QIcon 的 save 方法，但需要确保格式正确
        # 实际上，PyQt5 的 QIcon 不支持直接保存为 ICO
        # 我们需要使用 PIL/Pillow 或其他库
        
        # 临时方案：保存为 PNG，然后使用 PIL 转换为 ICO
        # 或者，直接使用最大的尺寸作为 ICO（Windows 会缩放）
        temp_png = ico_path.with_suffix('.png')
        largest_pixmap = icon.pixmap(max(sizes), max(sizes))
        if largest_pixmap.save(str(temp_png), 'PNG'):
            logger.info(f"已保存临时 PNG 文件: {temp_png}")
            
            # 尝试使用 PIL 转换为 ICO
            try:
                from PIL import Image
                img = Image.open(temp_png)
                
                # 创建包含多个尺寸的 ICO 文件
                ico_sizes = [(s, s) for s in sizes]
                img.save(str(ico_path), format='ICO', sizes=ico_sizes)
                logger.info(f"成功创建 ICO 文件: {ico_path}")
                
                # 删除临时 PNG 文件
                temp_png.unlink()
                logger.debug(f"已删除临时文件: {temp_png}")
                
                return True
            except ImportError:
                logger.warning("PIL/Pillow 未安装，无法创建 ICO 文件")
                logger.info("请安装 Pillow: pip install Pillow")
                logger.info(f"或者手动将 {temp_png} 转换为 ICO 文件")
                return False
            except Exception as e:
                logger.error(f"转换 PNG 到 ICO 时出错: {e}", exc_info=True)
                return False
        else:
            logger.error("保存 PNG 文件失败")
            return False
            
    except Exception as e:
        logger.error(f"转换 SVG 到 ICO 时出错: {e}", exc_info=True)
        return False


def main():
    """主函数"""
    # 项目根目录
    project_root = Path(__file__).parent.parent
    
    # 输入和输出路径
    svg_path = project_root / "assets" / "logo.svg"
    ico_path = project_root / "assets" / "icon.ico"
    
    logger.info("=" * 60)
    logger.info("SVG 转 ICO 工具")
    logger.info("=" * 60)
    logger.info(f"项目根目录: {project_root}")
    logger.info(f"SVG 文件: {svg_path}")
    logger.info(f"输出 ICO 文件: {ico_path}")
    logger.info("=" * 60)
    
    if not svg_path.exists():
        logger.error(f"SVG 文件不存在: {svg_path}")
        sys.exit(1)
    
    # 执行转换
    success = svg_to_ico(svg_path, ico_path)
    
    if success:
        logger.info("=" * 60)
        logger.info("转换成功！")
        logger.info(f"ICO 文件已保存到: {ico_path}")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("=" * 60)
        logger.error("转换失败！")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

