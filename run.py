"""
测试运行入口
支持配置文件控制运行方式

用法:
    python run.py                    # 按配置文件运行
    python run.py --all              # 运行全部用例
    python run.py --module login     # 运行登录模块
    python run.py --tag critical     # 运行 critical 标签用例
    python run.py --case test_login_success   # 运行指定用例
    python run.py --list             # 列出所有可用用例
"""

import sys
import os
import subprocess
import argparse
import time
import json
import shutil

# 确保项目根目录在路径中
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# 自动检测正确的 Python 解释器
def get_python_executable():
    """获取正确的 Python 解释器路径"""
    # 优先使用虚拟环境
    venv_python = os.path.join(PROJECT_ROOT, ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python
    
    # 检查常见虚拟环境路径
    common_venv = "D:\\测试资料\\project\\test\\Scripts\\python.exe"
    if os.path.exists(common_venv):
        return common_venv
    
    # 使用当前 Python
    return sys.executable

PYTHON_EXE = get_python_executable()

# 尝试导入 yaml 用于配置文件
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("[WARN]  PyYAML 未安装，将使用 Python 配置文件")
    print("   安装: pip install PyYAML")

def load_config():
    """加载配置文件，优先使用 YAML，失败时使用 Python 配置"""
    config_path = os.path.join(PROJECT_ROOT, "config", "config.yaml")
    
    # 如果 YAML 可用且配置文件存在，则加载 YAML
    if YAML_AVAILABLE and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f)
            
            if not yaml_config:
                print("[WARN]  YAML 配置文件为空，使用默认配置")
                raise ValueError("Empty YAML config")
            
            # 从 YAML 配置中提取 run 和 device 部分
            run_config = yaml_config.get('run', {})
            device_config = yaml_config.get('device', {})
            
            try:
                print(f"[OK] 已加载 YAML 配置文件: {config_path}")
            except UnicodeEncodeError:
                sys.stdout.buffer.write(f"[OK] 已加载 YAML 配置文件: ".encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(str(config_path).encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(b'\n')
            return run_config, device_config
            
        except Exception as e:
            try:
                print(f"[WARN]  加载 YAML 配置失败: {e}")
            except UnicodeEncodeError:
                sys.stdout.buffer.write(f"[WARN]  加载 YAML 配置失败: ".encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(str(e).encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(b'\n')
            print("   将使用 Python 配置文件")
    
    # 回退到 Python 配置
    from config.run_config import RUN_CONFIG as run_config
    from config.device_config import DEVICE_CONFIG as device_config
    
    print("[NOTE] 使用 Python 配置文件")
    return run_config, device_config

# 加载配置
RUN_CONFIG, DEVICE_CONFIG = load_config()


def build_pytest_args(config=None):
    """根据配置构建 pytest 参数"""
    if config is None:
        config = RUN_CONFIG

    args = ["-v", "--tb=short"]

    # 重试配置（需要安装 pytest-rerunfailures）
    reruns = config.get("reruns", 0)
    if reruns > 0:
        # 直接添加参数，pytest 会自动检测插件是否可用
        args.append(f"--reruns={reruns}")
        args.append(f"--reruns-delay={config.get('reruns_delay', 3)}")

    # 并发配置
    workers = config.get("workers", 0)
    if workers > 0:
        args.extend(["-n", str(workers)])

    # Allure 报告
    os.makedirs("reports/allure-results", exist_ok=True)
    mode = config.get("mode", "all")

    if mode == "all":
        # 运行全部
        args.append("testcases/")

    elif mode == "module":
        # 按模块运行（目录结构：testcases/test{module}/）
        modules = config.get("modules", [])
        if not modules:
            print("错误: mode=module 但 modules 列表为空")
            sys.exit(1)
        for module in modules:
            # 模块名 settings -> 目录 testcases/testsettings/
            args.append(f"testcases/test{module}/")

    elif mode == "case":
        # 按用例运行
        cases = config.get("cases", [])
        if not cases:
            print("错误: mode=case 但 cases 列表为空")
            sys.exit(1)
        # 使用 -k 参数匹配用例名
        case_filter = " or ".join(cases)
        args.extend(["-k", case_filter])
        args.append("testcases/")

    elif mode == "tag":
        # 按标签运行（通过 marker）
        tags = config.get("tags", [])
        if not tags:
            print("错误: mode=tag 但 tags 列表为空")
            sys.exit(1)
        # 使用 -m 参数匹配 marker
        tag_filter = " or ".join(tags)
        args.extend(["-m", tag_filter])
        args.append("testcases/")

    else:
        print(f"错误: 未知的运行模式: {mode}")
        sys.exit(1)

    # 排除用例
    excludes = config.get("exclude", [])
    if excludes:
        exclude_filter = " and not (" + " or ".join(excludes) + ")"
        # 如果已经有 -k，需要合并
        if "-k" in args:
            idx = args.index("-k")
            existing = args[idx + 1]
            args[idx + 1] = f"({existing}){exclude_filter}"
        else:
            args.extend(["-k", exclude_filter[5:]])  # 去掉 " and "

    return args


def check_allure_installed():
    """检查 Allure 是否已安装，返回可执行文件路径，否则返回 None"""
    def get_best_allure_path(path):
        """返回最佳的 Allure 可执行文件路径，优先使用 .bat 文件"""
        if path is None:
            return None
        # 如果路径已经是 "allure" 字符串（表示在 PATH 中），直接返回
        if path == "allure":
            return path
        # 检查路径是否存在
        if not os.path.exists(path):
            return None
        # 如果路径以 .bat 结尾，直接返回
        if path.lower().endswith('.bat'):
            return path
        # 尝试添加 .bat 扩展名
        bat_path = path + '.bat'
        if os.path.exists(bat_path):
            return bat_path
        # 尝试添加 .exe 扩展名
        exe_path = path + '.exe'
        if os.path.exists(exe_path):
            return exe_path
        # 原始路径存在但无扩展名，可能是一个脚本文件（如 Unix shell 脚本）
        # 在 Windows 上，我们仍然尝试执行它，但可能失败
        return path
    
    try:
        # 方法1: 直接运行 allure --version
        result = subprocess.run(["allure", "--version"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            # 尝试获取完整路径
            full_path = shutil.which("allure")
            if full_path:
                best_path = get_best_allure_path(full_path)
                if best_path:
                    return best_path
            # 回退到 "allure"
            return "allure"
    except FileNotFoundError:
        pass
    
    # 方法2: Windows 上使用 where 命令
    try:
        result = subprocess.run(["where", "allure"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.returncode == 0 and "allure" in result.stdout.lower():
            # 返回第一个找到的路径
            lines = result.stdout.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line:
                    best_path = get_best_allure_path(line)
                    if best_path:
                        return best_path
    except FileNotFoundError:
        pass
    
    # 方法3: 检查常见安装路径
    common_paths = [
        os.path.join(os.environ.get("USERPROFILE", ""), "allure", "bin", "allure.bat"),
        os.path.join(os.environ.get("USERPROFILE", ""), "allure", "bin", "allure"),
        "C:\\allure\\bin\\allure.bat",
        "C:\\Program Files\\allure\\bin\\allure.bat",
        "C:\\Program Files (x86)\\allure\\bin\\allure.bat",
        # 用户特定路径
        "C:\\Users\\86185\\allure-2.43.0\\bin\\allure.bat",
        "C:\\Users\\86185\\allure-2.43.0\\bin\\allure",
    ]
    
    # 检查 ALLURE_HOME 环境变量
    allure_home = os.environ.get("ALLURE_HOME")
    if allure_home:
        common_paths.insert(0, os.path.join(allure_home, "bin", "allure.bat"))
        common_paths.insert(1, os.path.join(allure_home, "bin", "allure"))
    
    for path in common_paths:
        best_path = get_best_allure_path(path)
        if best_path:
            return best_path
    
    return None


def generate_allure_report():
    """生成 Allure HTML 报告"""
    print("\n" + "=" * 50)
    print("生成 Allure 报告...")

    # 写入环境信息
    env_dir = "reports/allure-results"
    os.makedirs(env_dir, exist_ok=True)

    env_content = ""
    for key, value in RUN_CONFIG.get("environment", {}).items():
        env_content += f"{key}={value}\n"

    # 添加设备信息
    env_content += f"设备序列号={DEVICE_CONFIG.get('serial', '未配置')}\n"
    env_content += f"连接方式={'USB' if DEVICE_CONFIG.get('serial') else 'WiFi'}\n"

    with open(os.path.join(env_dir, "environment.properties"), "w", encoding="utf-8") as f:
        f.write(env_content)

    # 检查 allure 命令是否存在
    allure_path = check_allure_installed()
    if allure_path is None:
        print("[ERROR] Allure 未安装，无法生成 HTML 报告")
        print("\n[PACKAGE] 安装 Allure 方法（任选一种）：")
        print("1. 自动安装（推荐小白）：")
        print("   运行: python install_allure.py")
        print("2. 手动安装：")
        print("   a. 下载: https://github.com/allure-framework/allure2/releases")
        print("   b. 解压到任意目录，如: C:\\allure")
        print("   c. 添加 bin 目录到系统 PATH 环境变量")
        print("3. 使用包管理器：")
        print("   Windows: scoop install allure")
        print("   Mac: brew install allure")
        print("\n[REPORT] 当前已保存原始数据到: reports/allure-results/")
        print("   安装后运行: allure generate reports/allure-results -o reports/allure-report --clean")
        print("   或在线查看: allure serve reports/allure-results")
        return False
    else:
        try:
            print(f"[DEBUG] 检测到 Allure 路径: {allure_path}")
        except UnicodeEncodeError:
            sys.stdout.buffer.write(f"[DEBUG] 检测到 Allure 路径: ".encode('utf-8', errors='ignore'))
            sys.stdout.buffer.write(str(allure_path).encode('utf-8', errors='ignore'))
            sys.stdout.buffer.write(b'\n')

    # 生成报告
    try:
        # 验证 Allure 可执行文件
        if allure_path == "allure":
            # 尝试获取完整路径
            full_path = shutil.which("allure")
            if full_path:
                try:
                    print(f"[DEBUG] 通过 shutil.which 找到 Allure: {full_path}")
                except UnicodeEncodeError:
                    sys.stdout.buffer.write(f"[DEBUG] 通过 shutil.which 找到 Allure: ".encode('utf-8', errors='ignore'))
                    sys.stdout.buffer.write(str(full_path).encode('utf-8', errors='ignore'))
                    sys.stdout.buffer.write(b'\n')
                # 使用完整路径
                cmd = [full_path, "generate", "reports/allure-results", "-o", "reports/allure-report", "--clean"]
            else:
                # 回退到 "allure"
                cmd = ["allure", "generate", "reports/allure-results", "-o", "reports/allure-report", "--clean"]
        else:
            cmd = [allure_path, "generate", "reports/allure-results", "-o", "reports/allure-report", "--clean"]
        
        # 调试信息
        try:
            print(f"[DEBUG] 执行命令: {' '.join(cmd)}")
            print(f"[DEBUG] 工作目录: {os.getcwd()}")
            # 检查命令是否存在
            if cmd[0] == "allure":
                which_path = shutil.which("allure")
                print(f"[DEBUG] shutil.which('allure'): {which_path}")
            else:
                print(f"[DEBUG] 检查 Allure 可执行文件是否存在: {os.path.exists(cmd[0])}")
        except UnicodeEncodeError:
            sys.stdout.buffer.write(f"[DEBUG] 执行命令: ".encode('utf-8', errors='ignore'))
            sys.stdout.buffer.write(' '.join(cmd).encode('utf-8', errors='ignore'))
            sys.stdout.buffer.write(b'\n')
            sys.stdout.buffer.write(f"[DEBUG] 工作目录: ".encode('utf-8', errors='ignore'))
            sys.stdout.buffer.write(str(os.getcwd()).encode('utf-8', errors='ignore'))
            sys.stdout.buffer.write(b'\n')
            if cmd[0] == "allure":
                which_path = shutil.which("allure")
                sys.stdout.buffer.write(f"[DEBUG] shutil.which('allure'): ".encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(str(which_path).encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(b'\n')
            else:
                sys.stdout.buffer.write(f"[DEBUG] 检查 Allure 可执行文件是否存在: ".encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(str(os.path.exists(cmd[0])).encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(b'\n')
        
        # 验证命令是否可执行（可选）
        try:
            if cmd[0] == "allure":
                test_result = subprocess.run(["allure", "--version"], capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=5)
            else:
                test_result = subprocess.run([cmd[0], "--version"], capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=5)
            try:
                print(f"[DEBUG] Allure 版本检查成功: {test_result.stdout.strip()}")
            except UnicodeEncodeError:
                sys.stdout.buffer.write(f"[DEBUG] Allure 版本检查成功: ".encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(test_result.stdout.strip().encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(b'\n')
        except Exception as e:
            try:
                print(f"[DEBUG] Allure 版本检查失败: {e}")
            except UnicodeEncodeError:
                sys.stdout.buffer.write(f"[DEBUG] Allure 版本检查失败: ".encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(str(e).encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(b'\n')
            # 继续执行，可能仍然可以生成报告
        
        result = subprocess.run(
            ' '.join(cmd),
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )

        if result.returncode == 0:
            print(f"[OK] 报告已生成: reports/allure-report/index.html")
            print("   可用浏览器打开查看")
            print("   或运行: allure open reports/allure-report")
            return True
        else:
            print(f"[ERROR] 生成报告失败: {result.stderr}")
            print("[TIP] 提示: 尝试手动运行:")
            print("   allure generate reports/allure-results -o reports/allure-report --clean")
            return False
    except Exception as e:
        print(f"[ERROR] 生成报告时出错: {e}")
        return False


def list_test_cases():
    """列出所有可用用例"""
    print("=" * 50)
    print("可用测试用例列表")
    print(f"Python: {PYTHON_EXE}")
    print("=" * 50)

    result = subprocess.run(
        [PYTHON_EXE, "-m", "pytest", "testcases/", "--collect-only", "-q"],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='ignore'
    )

    if result.returncode == 0:
        lines = result.stdout.strip().split("\n")
        for line in lines:
            if line.strip() and not line.startswith("no tests"):
                print(f"  {line}")
    else:
        print(f"获取用例列表失败: {result.stderr}")


def run_tests(args_list=None):
    """运行测试"""
    try:
        print("=" * 50)
        print("Android UI 自动化测试")
        print(f"Python: {PYTHON_EXE}")
        print("=" * 50)
        print(f"运行模式: {RUN_CONFIG.get('mode', 'all')}")
        
        # 检查设备配置
        device_display = DEVICE_CONFIG.get('serial') or DEVICE_CONFIG.get('host', '未配置')
        print(f"设备: {device_display}")
        
        # 检查测试目录是否存在
        test_dir = "testcases"
        if not os.path.exists(test_dir):
            print(f"[ERROR] 测试目录不存在: {test_dir}")
            print("[TIP] 请确保 testcases/ 目录存在并包含测试用例")
            return 1
            
        print("=" * 50)
        
        # 提前检查 Allure 安装（如果配置了生成报告）
        if RUN_CONFIG.get("allure_report", True):
            allure_path = check_allure_installed()
            if allure_path is None:
                print("[WARN]  注意: Allure 未安装，将无法生成 HTML 报告")
                print("   运行测试前可先安装: python install_allure.py")
                print("   或使用 --no-report 跳过报告生成")
                print("-" * 50)
            else:
                try:
                    print(f"[DEBUG] 检测到 Allure 路径: {allure_path}")
                except UnicodeEncodeError:
                    sys.stdout.buffer.write(f"[DEBUG] 检测到 Allure 路径: ".encode('utf-8', errors='ignore'))
                    sys.stdout.buffer.write(str(allure_path).encode('utf-8', errors='ignore'))
                    sys.stdout.buffer.write(b'\n')

        pytest_args = build_pytest_args()
        cmd = [PYTHON_EXE, "-m", "pytest"] + pytest_args

        try:
            print(f"\n执行命令: {' '.join(cmd)}")
        except UnicodeEncodeError:
            sys.stdout.buffer.write("\n执行命令: ".encode('utf-8'))
            sys.stdout.buffer.write(' '.join(cmd).encode('utf-8', errors='ignore'))
            sys.stdout.buffer.write(b'\n')
        print("-" * 50)

        start_time = time.time()
        
        # 运行测试 - 重定向输出到文件以确保捕获
        output_file = "pytest_output.txt"
        try:
            print(f"[DEBUG] 开始执行测试命令，超时: 300秒")
        except UnicodeEncodeError:
            sys.stdout.buffer.write("[DEBUG] 开始执行测试命令，超时: 300秒\n".encode('utf-8'))
        try:
            cmd_str = ' '.join(cmd)
            try:
                print(f"[DEBUG] 命令字符串: {cmd_str}")
            except UnicodeEncodeError:
                sys.stdout.buffer.write("[DEBUG] 命令字符串: ".encode('utf-8'))
                sys.stdout.buffer.write(cmd_str.encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(b'\n')
            result = subprocess.run(cmd_str, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=300, shell=True)
            try:
                print(f"[DEBUG] Subprocess return code: {result.returncode}")
            except UnicodeEncodeError:
                sys.stdout.buffer.write("[DEBUG] Subprocess return code: ".encode('utf-8'))
                sys.stdout.buffer.write(str(result.returncode).encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(b'\n')
            try:
                print(f"[DEBUG] 命令执行完成，返回码: {result.returncode}")
            except UnicodeEncodeError:
                sys.stdout.buffer.write("[DEBUG] 命令执行完成，返回码: ".encode('utf-8'))
                sys.stdout.buffer.write(str(result.returncode).encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(b'\n')
            # 将输出写入文件
            with open(output_file, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(result.stdout)
                if result.stderr:
                    f.write("\n=== STDERR ===\n")
                    f.write(result.stderr)
        except subprocess.TimeoutExpired as e:
            try:
                print(f"[DEBUG] 命令超时: {e}")
            except UnicodeEncodeError:
                sys.stdout.buffer.write("[DEBUG] 命令超时: ".encode('utf-8'))
                sys.stdout.buffer.write(str(e).encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(b'\n')
            raise
        except Exception as e:
            try:
                print(f"[DEBUG] 命令执行异常: {e}")
            except UnicodeEncodeError:
                sys.stdout.buffer.write("[DEBUG] 命令执行异常: ".encode('utf-8'))
                sys.stdout.buffer.write(str(e).encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(b'\n')
            raise
        elapsed = time.time() - start_time
        
        # 读取并打印输出
        try:
            print(f"[DEBUG] Output file path: {os.path.abspath(output_file)}")
        except UnicodeEncodeError:
            sys.stdout.buffer.write("[DEBUG] Output file path: ".encode('utf-8', errors='ignore'))
            sys.stdout.buffer.write(str(os.path.abspath(output_file)).encode('utf-8', errors='ignore'))
            sys.stdout.buffer.write(b'\n')
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
                output_content = f.read()
                try:
                    print("[DEBUG] Read output content")
                except UnicodeEncodeError:
                    sys.stdout.buffer.write("[DEBUG] Read output content\n".encode('utf-8', errors='ignore'))
                try:
                    print(f"输出文件大小: {len(output_content)} 字节")
                except UnicodeEncodeError:
                    sys.stdout.buffer.write("输出文件大小: ".encode('utf-8'))
                    sys.stdout.buffer.write(str(len(output_content)).encode('utf-8', errors='ignore'))
                    sys.stdout.buffer.write(" 字节\n".encode('utf-8'))
                if output_content:
                    # 直接使用 buffer.write 避免编码问题
                    sys.stdout.buffer.write(output_content.encode('utf-8', errors='ignore'))
                    sys.stdout.buffer.write(b'\n')
                print("-" * 50)
        else:
            print(f"[WARN]  输出文件不存在: {output_file}")

        print("-" * 50)
        
        # 输出测试结果摘要
        if result.returncode == 0:
            print(f"[OK] 测试通过，耗时: {elapsed:.1f}秒")
            
        elif result.returncode == 1:
            print(f"[WARN]  测试失败，耗时: {elapsed:.1f}秒")
            # 输出错误摘要
            if result.stderr:
                error_lines = result.stderr.strip().split('\n')
                for line in error_lines[-5:]:  # 显示最后5行错误
                    if line.strip():
                        print(f"  错误: {line}")
        else:
            print(f"[ERROR] 测试异常退出 (代码: {result.returncode})，耗时: {elapsed:.1f}秒")
            if result.stderr:
                print(f"  错误输出: {result.stderr[:200]}...")

        # 生成报告
        if RUN_CONFIG.get("allure_report", True) and result.returncode in (0, 1):
            print("\n" + "=" * 50)
            print("生成测试报告...")
            report_generated = generate_allure_report()
            if not report_generated:
                print("\n[TIP] 提示: 原始测试数据已保存到 reports/allure-results/")
                print("   安装 Allure 后可以生成 HTML 报告")
            print("=" * 50)

        return result.returncode
        
    except KeyboardInterrupt:
        print("\n\n[STOP]  测试被用户中断")
        return 130
    except subprocess.TimeoutExpired:
        print("\n[TIMEOUT]  测试执行超时 (300秒)")
        print("[TIP] 可能原因: 设备连接失败、测试用例卡住、网络问题")
        print("   建议检查:")
        print("   1. 设备是否正确连接 (adb devices)")
        print("   2. 设备序列号配置是否正确")
        print("   3. 尝试使用离线模式: 设置 OFFLINE_MODE=true 环境变量")
        return 124
    except FileNotFoundError as e:
        try:
            print(f"\n[ERROR] 文件未找到: {e}")
        except UnicodeEncodeError:
            sys.stdout.buffer.write(f"\n[ERROR] 文件未找到: ".encode('utf-8', errors='ignore'))
            sys.stdout.buffer.write(str(e).encode('utf-8', errors='ignore'))
            sys.stdout.buffer.write(b'\n')
        print("[TIP] 请检查 Python 解释器路径或 pytest 是否安装")
        return 1
    except Exception as e:
        try:
            print(f"\n[ERROR] 运行测试时出错: {e}")
        except UnicodeEncodeError:
            sys.stdout.buffer.write(f"\n[ERROR] 运行测试时出错: ".encode('utf-8', errors='ignore'))
            sys.stdout.buffer.write(str(e).encode('utf-8', errors='ignore'))
            sys.stdout.buffer.write(b'\n')
        print("[TIP] 请检查日志文件获取详细信息")
        return 1


def main():
    """主函数，处理命令行参数并运行测试"""
    try:
        parser = argparse.ArgumentParser(
            description="Android UI 自动化测试运行工具",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
使用示例:
  python run.py                    # 按配置文件运行
  python run.py --all              # 运行全部用例
  python run.py --module settings  # 运行settings模块
  python run.py --tag critical     # 运行critical标签用例
  python run.py --case test_wifi_switch   # 运行指定用例
  python run.py --list             # 列出所有可用用例
  python run.py --reruns 3         # 失败重试3次
  python run.py --workers 2        # 2进程并行运行
  python run.py --no-report        # 不生成Allure报告

配置文件:
  config/config.yaml (YAML格式，优先使用)
  config/run_config.py (Python格式，备用)
  config/device_config.py (Python格式，备用)
            """
        )
        parser.add_argument("--all", action="store_true", help="运行全部用例")
        parser.add_argument("--module", nargs="+", help="按模块运行，如: settings login")
        parser.add_argument("--case", nargs="+", help="按用例名运行，如: test_wifi_switch")
        parser.add_argument("--tag", nargs="+", help="按标签运行，如: critical smoke")
        parser.add_argument("--list", action="store_true", help="列出所有可用用例")
        parser.add_argument("--reruns", type=int, help="重试次数 (默认: 2)")
        parser.add_argument("--workers", type=int, help="并发数 (默认: 0，串行)")
        parser.add_argument("--no-report", action="store_true", help="不生成 Allure 报告")
        parser.add_argument("--config", help="指定配置文件路径")

        args = parser.parse_args()

        # 如果有指定配置文件，重新加载配置
        if args.config:
            global RUN_CONFIG, DEVICE_CONFIG
            config_path = os.path.abspath(args.config)
            if not os.path.exists(config_path):
                try:
                    print(f"[ERROR] 配置文件不存在: {config_path}")
                except UnicodeEncodeError:
                    sys.stdout.buffer.write(f"[ERROR] 配置文件不存在: ".encode('utf-8', errors='ignore'))
                    sys.stdout.buffer.write(str(config_path).encode('utf-8', errors='ignore'))
                    sys.stdout.buffer.write(b'\n')
                return 1
            try:
                print(f"[FILE] 使用指定配置文件: {config_path}")
            except UnicodeEncodeError:
                sys.stdout.buffer.write(f"[FILE] 使用指定配置文件: ".encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(str(config_path).encode('utf-8', errors='ignore'))
                sys.stdout.buffer.write(b'\n')
            # 这里可以扩展为加载指定配置文件

        # 覆盖配置
        if args.all:
            RUN_CONFIG["mode"] = "all"
            print("[MODE] 运行模式: 全部用例")
        elif args.module:
            RUN_CONFIG["mode"] = "module"
            RUN_CONFIG["modules"] = args.module
            print(f"[MODE] 运行模式: 模块 - {', '.join(args.module)}")
        elif args.case:
            RUN_CONFIG["mode"] = "case"
            RUN_CONFIG["cases"] = args.case
            print(f"[MODE] 运行模式: 用例 - {', '.join(args.case)}")
        elif args.tag:
            RUN_CONFIG["mode"] = "tag"
            RUN_CONFIG["tags"] = args.tag
            print(f"[MODE] 运行模式: 标签 - {', '.join(args.tag)}")
        elif args.list:
            list_test_cases()
            return 0

        if args.reruns is not None:
            RUN_CONFIG["reruns"] = args.reruns
            print(f"[RETRY] 重试次数: {args.reruns}")
        if args.workers is not None:
            RUN_CONFIG["workers"] = args.workers
            print(f"[WORKER] 并发数: {args.workers}")
        if args.no_report:
            RUN_CONFIG["allure_report"] = False
            print("[REPORT] 报告生成: 禁用")

        return run_tests()
        
    except KeyboardInterrupt:
        print("\n\n[STOP]  用户中断，停止测试")
        return 130
    except Exception as e:
        try:
            print(f"\n[ERROR] 运行出错: {e}")
        except UnicodeEncodeError:
            sys.stdout.buffer.write(f"\n[ERROR] 运行出错: ".encode('utf-8', errors='ignore'))
            sys.stdout.buffer.write(str(e).encode('utf-8', errors='ignore'))
            sys.stdout.buffer.write(b'\n')
        print("\n[TIP] 常见问题排查:")
        print("  1. 检查设备是否连接: adb devices")
        print("  2. 检查Python依赖: pip install -r requirements.txt")
        print("  3. 检查配置文件: config/config.yaml")
        print("  4. 查看详细日志: logs/ 目录")
        return 1


if __name__ == "__main__":
    sys.exit(main())
