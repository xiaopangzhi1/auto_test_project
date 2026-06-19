# Android UI 自动化测试框架

一个基于 `uiautomator2` + `pytest` 的 Android UI 自动化测试框架，专为小白用户设计，提供精美的测试报告和友好的使用体验。

## ✨ 特性

- **小白友好**：一键安装，清晰的使用说明
- **精美报告**：交互式 Allure 报告 + 美化 HTML 报告
- **配置灵活**：支持 YAML 和 Python 两种配置方式
- **多设备支持**：USB/WiFi 连接，单设备/多设备并行
- **错误友好**：详细的错误提示和问题排查指南
- **PyCharm 集成**：提供现成的运行配置

## 📋 快速开始

### 1. 环境准备

```bash
# 1. 安装 Python 3.8+ (推荐 3.10+)
# 2. 安装 ADB 并添加到 PATH
# 3. 连接 Android 设备 (USB调试模式开启)

# 检查设备连接
adb devices
```

### 2. 安装依赖

```bash
# 进入项目目录
cd android_auto_test

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Allure (可选，用于生成精美报告)
python install_allure.py
```

### 3. 配置设备

编辑 `config/config.yaml` 文件：

```yaml
device:
  serial: "你的设备序列号"  # 通过 adb devices 获取
  # 或使用 WiFi 连接
  # host: "192.168.1.100:5555"
```

### 4. 运行测试

```bash
# 基本运行 (按配置文件)
python run.py

# 运行全部用例
python run.py --all

# 按模块运行
python run.py --module settings

# 按标签运行
python run.py --tag critical

# 列出所有用例
python run.py --list

# 失败重试3次
python run.py --reruns 3

# 2进程并行运行
python run.py --workers 2

# 不生成报告
python run.py --no-report
```

## 🎨 测试报告

### Allure 报告 (推荐)
- **位置**: `reports/allure-report/index.html`
- **特性**: 交互式时间线、步骤详情、截图附件、环境信息
- **查看**: 浏览器打开或运行 `allure open reports/allure-report`

### HTML 报告
- **位置**: `reports/report.html`
- **特性**: 美化样式、筛选功能、进度条、暗色模式
- **查看**: 直接浏览器打开

## ⚙️ 配置文件

### YAML 配置 (推荐)
```yaml
# config/config.yaml
run:
  mode: "module"          # all | module | case | tag
  modules: ["settings"]   # 模块列表
  reruns: 2              # 重试次数
  workers: 0             # 并发数 (0=串行)

device:
  serial: "0123456789ABCDEF"  # 设备序列号
  # host: "192.168.1.100:5555" # WiFi连接
```

### Python 配置 (备用)
- `config/run_config.py` - 运行配置
- `config/device_config.py` - 设备配置

## 🚀 PyCharm 集成

### 方法1: 使用启动脚本
1. 在 PyCharm 中打开项目
2. 右键点击 `run_tests.bat` (Windows) 或 `run_tests.sh` (Mac/Linux)
3. 选择 "Run 'run_tests.bat'"

### 方法2: 创建运行配置
1. **Run** → **Edit Configurations**
2. 点击 **+** → **Python**
3. 配置:
   - **Script path**: `run.py`
   - **Parameters**: `--module settings` (可选)
   - **Working directory**: 项目根目录
4. 点击 **OK** 保存

### 方法3: 使用内置终端
1. 打开 PyCharm 终端
2. 运行: `python run.py --module settings`

## 📁 项目结构

```
android_auto_test/
├── config/                    # 配置文件
│   ├── config.yaml           # YAML 配置文件 (推荐)
│   ├── config.yaml.example   # 配置示例
│   ├── run_config.py         # Python 运行配置
│   └── device_config.py      # Python 设备配置
├── pages/                    # 页面对象模型
│   ├── base_page.py          # 基础页面类
│   └── settings_page/        # 设置页面
│       └── wifi_switch_page.py
├── testcases/               # 测试用例
│   ├── conftest.py          # pytest 夹具
│   └── testsettings/        # 设置模块测试
│       └── test_wifi_switch.py
├── utils/                   # 工具模块
│   ├── logger.py            # 日志配置
│   └── report_style.py      # 报告样式
├── reports/                 # 测试报告
│   ├── allure-results/      # Allure 原始数据
│   ├── allure-report/       # Allure HTML 报告
│   └── report.html          # HTML 报告
├── logs/                    # 日志文件
├── screenshots/             # 失败截图
├── run.py                   # 主运行脚本
├── run_tests.bat            # Windows 启动脚本
├── run_tests.sh             # Linux/Mac 启动脚本
├── install_allure.py        # Allure 安装脚本
├── pytest.ini              # pytest 配置
└── requirements.txt         # Python 依赖
```

## 🐛 常见问题

### Q1: 设备连接失败
```
❌ 运行出错: 设备连接失败
```
**解决方案**:
1. 检查 USB 调试是否开启: `adb devices`
2. 检查设备序列号: 修改 `config/config.yaml` 中的 `serial`
3. 尝试 WiFi 连接: 使用 `host` 配置

### Q2: Allure 未安装
```
⚠️ Allure 未安装，将无法生成 HTML 报告
```
**解决方案**:
1. 自动安装: `python install_allure.py`
2. 手动安装: 下载并添加 Allure 到 PATH
3. 跳过报告: `python run.py --no-report`

### Q3: 依赖安装失败
```
ModuleNotFoundError: No module named 'uiautomator2'
```
**解决方案**:
```bash
pip install -r requirements.txt
```

### Q4: 测试用例找不到
```
❌ 测试目录不存在: testcases
```
**解决方案**:
确保 `testcases/` 目录存在并包含测试文件

## 🔧 高级功能

### 多设备并行测试
```yaml
# config/config.yaml
device:
  devices:
    - serial: "设备1序列号"
      name: "设备1"
    - serial: "设备2序列号" 
      name: "设备2"
  parallel: true
  workers: 2
```

### 自定义报告样式
编辑 `utils/report_style.py` 自定义:
- CSS 样式
- JavaScript 交互
- 环境信息显示

### 扩展页面对象
1. 在 `pages/` 下创建新目录，如 `pages/login_page/`
2. 继承 `BasePage` 类
3. 在 `testcases/` 下创建对应测试

## 📞 支持

### 查看日志
- 控制台日志: 实时彩色输出
- 文件日志: `logs/` 目录
- 错误日志: `logs/error_*.log`

### 获取帮助
```bash
# 查看使用说明
python run.py -h

# 查看可用用例
python run.py --list
```

## 📄 许可证

本项目仅供学习交流使用

---

**💡 提示**: 首次使用建议运行 `python run.py --list` 查看可用用例，然后运行 `python run.py --module settings` 体验完整流程。