"""Standalone entry point for PyInstaller packaging."""
import sys
import os

# 确保 src 目录在路径中
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from src.server import run_server

if __name__ == "__main__":
    run_server()
