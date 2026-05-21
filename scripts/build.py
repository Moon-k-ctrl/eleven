#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
打包脚本 - 将项目打包到指定路径
G:\AI\app\eleven1.0\eleven\eleven
"""
import os
import sys
import shutil
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = Path("G:/AI/app/eleven1.0/eleven/eleven")

def clean_build():
    """清理旧的构建文件"""
    print("清理旧的构建文件...")
    build_dir = BASE_DIR / "build"
    dist_dir = BASE_DIR / "dist"
    
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    print("✅ 清理完成")

def build_exe():
    """使用PyInstaller打包"""
    print("\n开始打包...")
    
    # 检查spec文件是否存在
    spec_file = BASE_DIR / "eleven.spec"
    if not spec_file.exists():
        print(f"❌ 错误: {spec_file} 不存在")
        return False
    
    # 确保输出目录存在
    OUTPUT_DIR.parent.mkdir(parents=True, exist_ok=True)
    
    # 构建命令
    cmd = f'pyinstaller --clean --noconfirm --distpath "{OUTPUT_DIR.parent}" "{spec_file}"'
    print(f"执行命令: {cmd}")
    print()
    
    # 执行构建
    result = os.system(cmd)
    
    if result == 0:
        print("\n✅ 打包成功!")
        
        # 检查输出
        built_exe = OUTPUT_DIR / "eleven.exe"
        if built_exe.exists():
            print(f"✅ 生成的exe文件: {built_exe}")
        elif (OUTPUT_DIR.parent / "eleven" / "eleven.exe").exists():
            print(f"✅ 生成的exe文件: {OUTPUT_DIR.parent / 'eleven' / 'eleven.exe'}")
            
        return True
    else:
        print("\n❌ 打包失败!")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("拾遗 (ShiYi) - 打包脚本")
    print("=" * 60)
    print(f"输出目录: {OUTPUT_DIR}")
    print()
    
    # 清理旧构建
    clean_build()
    
    # 构建
    success = build_exe()
    
    if success:
        print("\n" + "=" * 60)
        print("打包完成!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("打包失败!")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
