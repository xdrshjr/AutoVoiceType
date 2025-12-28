"""
快速测试脚本 - 验证配置和环境
用于在运行主程序前检查环境是否正确配置
"""
import sys
from pathlib import Path


def check_python_version():
    """检查Python版本"""
    print("=" * 60)
    print("检查Python版本...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"❌ Python版本过低: {version.major}.{version.minor}.{version.micro}")
        print("   需要 Python 3.8 或更高版本")
        return False


def check_dependencies():
    """检查依赖包是否已安装"""
    print("\n" + "=" * 60)
    print("检查依赖包...")
    
    required_packages = [
        ("PyQt5", "PyQt5"),
        ("pynput", "pynput"),
        ("pyaudio", "pyaudio"),
        ("websocket", "websocket-client"),
        ("dashscope", "dashscope"),
        ("pyperclip", "pyperclip"),
        ("pyautogui", "pyautogui"),
    ]
    
    all_installed = True
    
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name} - 未安装")
            all_installed = False
    
    if not all_installed:
        print("\n请运行以下命令安装缺失的依赖:")
        print("pip install -r requirements.txt")
    
    return all_installed


def check_config():
    """检查配置文件"""
    print("\n" + "=" * 60)
    print("检查配置文件...")
    
    config_dir = Path.home() / ".autovoicetype"
    config_file = config_dir / "config.json"
    
    if not config_file.exists():
        print("⚠️  配置文件不存在（首次运行将自动创建）")
        print(f"   配置文件位置: {config_file}")
        return True
    
    print(f"✅ 配置文件存在: {config_file}")
    
    # 检查API密钥
    import json
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        api_key = config.get('api', {}).get('dashscope_api_key', '')
        if api_key and api_key.strip():
            print(f"✅ API密钥已配置: {api_key[:10]}...")
            return True
        else:
            print("❌ API密钥未配置")
            print(f"   请编辑配置文件: {config_file}")
            print("   设置 api.dashscope_api_key 字段")
            return False
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return False


def check_audio_device():
    """检查音频设备"""
    print("\n" + "=" * 60)
    print("检查音频设备...")
    
    try:
        import pyaudio
        audio = pyaudio.PyAudio()
        
        # 获取默认输入设备
        default_input = audio.get_default_input_device_info()
        print(f"✅ 默认麦克风: {default_input['name']}")
        
        # 列出所有输入设备
        input_devices = []
        for i in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                input_devices.append(info['name'])
        
        print(f"✅ 可用麦克风数量: {len(input_devices)}")
        
        audio.terminate()
        return True
    except Exception as e:
        print(f"❌ 音频设备检查失败: {e}")
        return False


def main():
    """主函数"""
    print("\n🚀 AutoVoiceType 环境检查工具")
    print("=" * 60)
    
    results = []
    
    # 检查Python版本
    results.append(("Python版本", check_python_version()))
    
    # 检查依赖包
    results.append(("依赖包", check_dependencies()))
    
    # 检查配置文件
    results.append(("配置文件", check_config()))
    
    # 检查音频设备
    results.append(("音频设备", check_audio_device()))
    
    # 总结
    print("\n" + "=" * 60)
    print("检查结果汇总:")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有检查通过！可以运行主程序：")
        print("\n   cd src")
        print("   python main.py")
    else:
        print("❌ 存在问题，请按照上面的提示解决后再运行主程序")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n检查已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 检查过程出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

