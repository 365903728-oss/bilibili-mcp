@echo off
REM ========================================
REM Bilibili MCP 发布脚本
REM ========================================

echo.
echo ========================================
echo   正在推送到 GitHub...
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 推送代码到 master 分支...
git push origin master
if %errorlevel% neq 0 (
    echo   X 推送 master 失败！
    pause
    exit /b 1
)

echo.
echo [2/3] 推送 tag v1.1.0...
git push origin v1.1.0
if %errorlevel% neq 0 (
    echo   X 推送 tag 失败！
    pause
    exit /b 1
)

echo.
echo [3/3] 推送成功！
echo.
echo ========================================
echo   GitHub Actions 将自动构建并发布到 npm
echo   发布地址: https://www.npmjs.com/package/@xzxzzx/bilibili-mcp
echo ========================================
echo.

pause
