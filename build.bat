@echo off
chcp 65001 >nul
echo ========================================
echo 拾遗 (ShiYi) - 打包脚本
echo ========================================
echo.
echo 正在打包到: G:\AI\app\eleven1.0\eleven\eleven
echo.
cd /d "%~dp0"
python scripts\build.py
echo.
pause
