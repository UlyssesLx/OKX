@echo off
echo ========================================
echo 加密货币自动交易系统 - 启动脚本
echo ========================================
echo.

echo [1/2] 启动后端服务...
cd backend
start cmd /k "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
cd ..

timeout /t 3 /nobreak > nul

echo [2/2] 启动前端服务...
cd frontend
start cmd /k "npm run dev"
cd ..

echo.
echo ========================================
echo 服务已启动！
echo 后端地址: http://localhost:8000
echo 前端地址: http://localhost:3000
echo API文档: http://localhost:8000/docs
echo ========================================
pause
