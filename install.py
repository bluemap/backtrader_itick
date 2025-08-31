#!/usr/bin/env python3
"""
港美股量化交易通知系统 - 跨平台自动安装脚本
Author: Quantitative Trading Team
Description: 自动检测环境并安装所有必要的依赖
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path


class Colors:
    """终端颜色定义"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


class Logger:
    """日志类"""
    
    @staticmethod
    def info(msg):
        print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")
    
    @staticmethod
    def success(msg):
        print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")
    
    @staticmethod
    def warning(msg):
        print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {msg}")
    
    @staticmethod
    def error(msg):
        print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")


class Installer:
    """安装器类"""
    
    def __init__(self):
        self.logger = Logger()
        self.os_type = platform.system().lower()
        self.python_cmd = sys.executable
        self.pip_cmd = None
        self.use_mirror = False
        
    def show_welcome(self):
        """显示欢迎信息"""
        print("=" * 50)
        print("  港美股量化交易通知系统")
        print("  跨平台自动安装脚本 v1.0")
        print("=" * 50)
        print()
    
    def check_environment(self):
        """检查运行环境"""
        self.logger.info(f"检测到操作系统: {platform.system()} {platform.release()}")
        
        # 检查是否在项目根目录
        if not Path("requirements.txt").exists() or not Path("main.py").exists():
            self.logger.error("请在项目根目录下运行此脚本！")
            return False
        
        # 检查Python版本
        python_version = sys.version_info
        if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
            self.logger.error(f"Python版本过低！需要Python 3.8+，当前版本: {sys.version}")
            return False
        
        self.logger.success(f"Python版本检查通过: {sys.version.split()[0]}")
        
        # 检查pip
        try:
            import pip
            self.pip_cmd = [self.python_cmd, "-m", "pip"]
            self.logger.success("pip检查通过")
        except ImportError:
            self.logger.error("pip未安装！")
            return False
        
        return True
    
    def check_network(self):
        """检查网络连接"""
        self.logger.info("检查网络连接...")
        
        try:
            import urllib.request
            urllib.request.urlopen('https://pypi.org', timeout=5)
            self.logger.success("网络连接正常")
            self.use_mirror = False
        except:
            self.logger.warning("连接PyPI超时，将使用国内镜像")
            self.use_mirror = True
    
    def create_venv(self):
        """创建虚拟环境"""
        self.logger.info("创建Python虚拟环境...")
        
        venv_path = Path("venv")
        if venv_path.exists():
            self.logger.warning("虚拟环境已存在，跳过创建")
            return True
        
        try:
            subprocess.run([self.python_cmd, "-m", "venv", "venv"], check=True)
            self.logger.success("虚拟环境创建成功")
            
            # 更新虚拟环境中的pip命令
            if self.os_type == "windows":
                self.pip_cmd = [str(venv_path / "Scripts" / "python.exe"), "-m", "pip"]
            else:
                self.pip_cmd = [str(venv_path / "bin" / "python"), "-m", "pip"]
            
            # 升级pip
            self.logger.info("更新pip到最新版本...")
            subprocess.run(self.pip_cmd + ["install", "--upgrade", "pip"], check=True)
            
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"创建虚拟环境失败: {e}")
            return False
    
    def install_dependencies(self):
        """安装依赖包"""
        self.logger.info("开始安装Python依赖包...")
        
        # 准备pip命令
        pip_args = self.pip_cmd + ["install"]
        
        # 添加镜像源
        if self.use_mirror:
            self.logger.info("使用清华大学PyPI镜像源...")
            pip_args.extend(["-i", "https://pypi.tuna.tsinghua.edu.cn/simple/"])
        
        try:
            # 安装基础工具
            self.logger.info("安装基础工具...")
            subprocess.run(pip_args + ["--upgrade", "setuptools", "wheel"], check=True)
            
            # 安装项目依赖
            self.logger.info("安装项目依赖（这可能需要几分钟）...")
            subprocess.run(pip_args + ["-r", "requirements.txt"], check=True)
            
            self.logger.success("依赖安装完成")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"批量安装失败: {e}")
            self.logger.info("尝试单独安装失败的包...")
            return self._install_packages_individually(pip_args)
    
    def _install_packages_individually(self, pip_args):
        """单独安装每个包"""
        # 读取requirements.txt
        try:
            with open("requirements.txt", "r") as f:
                packages = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except Exception as e:
            self.logger.error(f"读取requirements.txt失败: {e}")
            return False
        
        failed_packages = []
        
        # 逐个安装
        for package in packages:
            try:
                self.logger.info(f"安装 {package}...")
                subprocess.run(pip_args + [package], check=True, capture_output=True)
                self.logger.success(f"✓ {package}")
            except subprocess.CalledProcessError:
                # 尝试备用包名
                alternate_package = self._get_alternate_package(package)
                if alternate_package:
                    try:
                        self.logger.warning(f"尝试备用包: {alternate_package}")
                        subprocess.run(pip_args + [alternate_package], check=True, capture_output=True)
                        self.logger.success(f"✓ {alternate_package} (备用)")
                        continue
                    except subprocess.CalledProcessError:
                        pass
                
                self.logger.error(f"✗ {package}")
                failed_packages.append(package)
        
        if failed_packages:
            self.logger.warning(f"以下包安装失败: {', '.join(failed_packages)}")
            self.logger.info("尝试使用不同的安装方法...")
            return self._retry_failed_packages(failed_packages, pip_args)
        
        return True
    
    def _get_alternate_package(self, package):
        """获取备用包名"""
        alternates = {
            "websocket-client": "websockets",
            "PyYAML": "ruamel.yaml",
            "pyarrow": None,  # 可选包
        }
        
        package_name = package.split(">")[0].split("=")[0].strip()
        return alternates.get(package_name)
    
    def _retry_failed_packages(self, failed_packages, base_pip_args):
        """重试安装失败的包"""
        success_count = 0
        
        for package in failed_packages:
            package_name = package.split(">")[0].split("=")[0].strip()
            
            # 尝试不同的安装策略
            strategies = [
                # 策略1: 使用--no-cache-dir
                base_pip_args + ["--no-cache-dir", package],
                # 策略2: 使用--force-reinstall
                base_pip_args + ["--force-reinstall", package],
                # 策略3: 使用--no-deps（仅安装主包）
                base_pip_args + ["--no-deps", package_name],
                # 策略4: 使用官方PyPI源
                self.pip_cmd + ["install", "-i", "https://pypi.org/simple/", package]
            ]
            
            installed = False
            for i, strategy in enumerate(strategies, 1):
                try:
                    self.logger.info(f"尝试策略{i}安装 {package_name}...")
                    subprocess.run(strategy, check=True, capture_output=True)
                    self.logger.success(f"✓ {package_name} (策略{i})")
                    success_count += 1
                    installed = True
                    break
                except subprocess.CalledProcessError:
                    continue
            
            if not installed:
                self.logger.error(f"所有策略都失败: {package_name}")
        
        return success_count > 0
    
    def verify_installation(self):
        """验证安装结果"""
        self.logger.info("验证安装结果...")
        
        # 获取Python可执行文件路径
        if Path("venv").exists():
            if self.os_type == "windows":
                python_exe = str(Path("venv") / "Scripts" / "python.exe")
            else:
                python_exe = str(Path("venv") / "bin" / "python")
        else:
            python_exe = self.python_cmd
        
        # 检查关键包
        critical_packages = {
            "pandas": "数据处理",
            "numpy": "数值计算", 
            "backtrader": "策略引擎",
            "requests": "HTTP请求", 
            "click": "命令行工具",
            "psutil": "系统监控"
        }
        
        optional_packages = {
            "websocket": "实时数据连接",
            "yaml": "配置文件解析",
            "pyarrow": "数据存储（可选）"
        }
        
        failed_critical = []
        failed_optional = []
        
        # 检查关键包
        for package, desc in critical_packages.items():
            try:
                subprocess.run([python_exe, "-c", f"import {package}"], 
                             check=True, capture_output=True)
                self.logger.success(f"✓ {package} ({desc})")
            except subprocess.CalledProcessError:
                self.logger.error(f"✗ {package} ({desc}) - 关键包")
                failed_critical.append(package)
        
        # 检查可选包
        for package, desc in optional_packages.items():
            try:
                subprocess.run([python_exe, "-c", f"import {package}"], 
                             check=True, capture_output=True)
                self.logger.success(f"✓ {package} ({desc})")
            except subprocess.CalledProcessError:
                self.logger.warning(f"✗ {package} ({desc}) - 可选包")
                failed_optional.append(package)
        
        # 结果判断
        if failed_critical:
            self.logger.error(f"关键包安装失败: {', '.join(failed_critical)}")
            return False
        elif failed_optional:
            self.logger.warning(f"可选包未安装: {', '.join(failed_optional)}")
            self.logger.info("系统可以正常运行，但部分功能可能受影响")
            self._show_manual_fix_instructions(failed_optional)
            return True
        else:
            self.logger.success("所有关键包验证通过")
            return True
    
    def _show_manual_fix_instructions(self, failed_packages):
        """显示手动修复说明"""
        print()
        self.logger.info("手动修复失败包的方法：")
        
        for package in failed_packages:
            if package == "websocket-client":
                print(f"  {package}:")
                print("    pip install websocket-client")
                print("    # 或者使用替代包: pip install websockets")
            elif package == "yaml":
                print(f"  {package} (PyYAML):")
                print("    pip install PyYAML")
                print("    # 或者使用替代包: pip install ruamel.yaml")
            elif package == "pyarrow":
                print(f"  {package} (可选):")
                print("    pip install pyarrow")
                print("    # 此包可选，不安装也可正常使用")
        
        print("\n如果上述命令仍然失败，请尝试：")
        print("  1. 更新pip: python -m pip install --upgrade pip")
        print("  2. 使用国内镜像: pip install -i https://pypi.tuna.tsinghua.edu.cn/simple/ 包名")
        print("  3. 清除pip缓存: pip cache purge")
    
    def setup_config(self):
        """设置配置文件"""
        self.logger.info("设置配置文件...")
        
        config_local = Path("config/config_local.yaml")
        config_template = Path("config/config.yaml")
        
        if not config_local.exists():
            if config_template.exists():
                shutil.copy(config_template, config_local)
                self.logger.success("创建本地配置文件: config/config_local.yaml")
            else:
                self.logger.warning("未找到配置模板文件")
        else:
            self.logger.info("本地配置文件已存在，跳过创建")
    
    def create_directories(self):
        """创建必要目录"""
        self.logger.info("创建必要目录...")
        
        directories = ["logs", "data/historical"]
        
        for directory in directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                self.logger.success(f"创建目录: {directory}")
    
    def test_system(self):
        """测试系统基本功能"""
        self.logger.info("测试系统基本功能...")
        
        # 获取Python可执行文件路径
        if Path("venv").exists():
            if self.os_type == "windows":
                python_exe = str(Path("venv") / "Scripts" / "python.exe")
            else:
                python_exe = str(Path("venv") / "bin" / "python")
        else:
            python_exe = self.python_cmd
        
        try:
            # 测试配置加载
            result = subprocess.run([
                python_exe, "-c", 
                "from src.core.config_manager import config_manager; "
                "print('配置加载测试:', '成功' if config_manager.config_data else '失败')"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self.logger.success("配置管理器测试通过")
            else:
                self.logger.warning("配置管理器测试失败，可能需要配置API Key")
        except:
            self.logger.warning("系统测试跳过（需要配置后才能正常运行）")
    
    def show_next_steps(self):
        """显示后续步骤"""
        print()
        print("=" * 50)
        self.logger.success("安装完成！")
        print("=" * 50)
        print()
        print("后续步骤：")
        print()
        print("1. 配置系统：")
        print("   编辑 config/config_local.yaml")
        print("   - 设置您的 iTick API Key")
        print("   - 配置通知方式（飞书/微信）")
        print()
        print("2. 测试配置：")
        if Path("venv").exists():
            if self.os_type == "windows":
                print("   venv\\Scripts\\python.exe cli.py config")
                print("   venv\\Scripts\\python.exe cli.py test-notifications")
            else:
                print("   venv/bin/python cli.py config")
                print("   venv/bin/python cli.py test-notifications")
        else:
            print("   python cli.py config")
            print("   python cli.py test-notifications")
        print()
        print("3. 启动系统：")
        if Path("venv").exists():
            if self.os_type == "windows":
                print("   venv\\Scripts\\python.exe main.py")
            else:
                print("   venv/bin/python main.py")
        else:
            print("   python main.py")
        print()
        if Path("venv").exists():
            print("4. 激活虚拟环境（可选）：")
            if self.os_type == "windows":
                print("   venv\\Scripts\\activate")
            else:
                print("   source venv/bin/activate")
            print()
        print("5. 查看文档：")
        print("   docs/quick_start.md - 快速入门")
        print("   docs/configuration.md - 配置指南")
        print("   docs/faq.md - 常见问题")
        print()
        self.logger.warning("重要提醒：")
        print("- 请确保设置正确的 iTick API Key")
        print("- 系统仅生成信号，不会自动下单")
        print("- 投资有风险，请谨慎决策")
        print()
    
    def run(self):
        """运行安装程序"""
        try:
            self.show_welcome()
            
            if not self.check_environment():
                return False
            
            self.check_network()
            
            if not self.create_venv():
                return False
            
            if not self.install_dependencies():
                return False
            
            if not self.verify_installation():
                return False
            
            self.setup_config()
            self.create_directories()
            self.test_system()
            self.show_next_steps()
            
            return True
        except KeyboardInterrupt:
            self.logger.warning("安装被用户中断")
            return False
        except Exception as e:
            self.logger.error(f"安装过程中发生异常: {e}")
            return False


def main():
    """主函数"""
    installer = Installer()
    success = installer.run()
    
    if not success:
        print()
        print("常见解决方法：")
        print("1. 检查网络连接")
        print("2. 更新pip: python -m pip install --upgrade pip")
        print("3. 使用国内镜像源")
        print("4. 手动安装失败的包")
        print()
        print("如需帮助，请查看 docs/faq.md 或提交 Issue")
        sys.exit(1)


if __name__ == "__main__":
    main()