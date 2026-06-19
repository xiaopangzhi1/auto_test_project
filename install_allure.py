"""
Allure 安装脚本
支持手动下载安装
"""
import os
import sys
import subprocess
import urllib.request
import zipfile


def install_allure_manual():
    """手动下载安装 allure"""
    allure_version = "2.30.0"
    download_url = f"https://github.com/allure-framework/allure2/releases/download/{allure_version}/allure-{allure_version}.zip"
    install_dir = os.path.join(os.environ.get("USERPROFILE", "."), "allure")

    print(f"正在下载 allure {allure_version}...")
    print(f"下载地址: {download_url}")

    zip_path = os.path.join(install_dir, "allure.zip")

    try:
        # 下载
        urllib.request.urlretrieve(download_url, zip_path)
        print(f"下载完成: {zip_path}")

        # 解压
        print("正在解压...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(install_dir)
        print(f"解压完成: {install_dir}")

        # 添加到 PATH
        allure_bin = os.path.join(install_dir, f"allure-{allure_version}", "bin")
        current_path = os.environ.get("PATH", "")

        if allure_bin not in current_path:
            # Windows 添加环境变量
            subprocess.run(
                f'[Environment]::SetEnvironmentVariable("PATH", [Environment]::GetEnvironmentVariable("PATH", "User") + ";{allure_bin}", "User")',
                shell=True,
                capture_output=True
            )
            os.environ["PATH"] = current_path + ";" + allure_bin
            print(f"[OK] 已添加 {allure_bin} 到 PATH")

        # 清理 zip
        os.remove(zip_path)

        # 验证
        print("\n验证安装...")
        result = subprocess.run(["allure", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Allure 安装成功: {result.stdout.strip()}")
            return True
        else:
            print("[ERROR] 验证失败，请手动添加到 PATH")
            return False

    except Exception as e:
        print(f"安装失败: {e}")
        print("\n请手动下载安装:")
        print(f"1. 下载: https://github.com/allure-framework/allure2/releases")
        print(f"2. 解压到: {install_dir}")
        print(f"3. 添加 {install_dir}\\allure-{{version}}\\bin 到 PATH")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Allure 手动安装脚本")
    print("=" * 50)

    # 检查是否已安装
    result = subprocess.run(["allure", "--version"], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"Allure 已安装: {result.stdout.strip()}")
        print("\n使用方法:")
        print("  allure generate reports/allure-results -o reports/allure-report --clean")
        print("  allure open reports/allure-report")
    else:
        print("Allure 未安装，开始下载...")
        print()
        if install_allure_manual():
            print("\n安装成功！请重新打开终端或运行:")
            print('  $env:PATH += ";C:\\\\Users\\\\你的用户名\\\\allure\\\\allure-2.30.0\\\\bin"')
        else:
            print("\n请手动下载安装")
