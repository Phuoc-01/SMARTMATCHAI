@echo off
echo === Tạo các file bị thiếu cho SMART-MATCH AI ===
echo.

:: Tạo cấu trúc thư mục
mkdir frontend\public 2>nul
mkdir frontend\src\contexts 2>nul
mkdir frontend\src\components 2>nul
mkdir frontend\src\pages 2>nul
mkdir frontend\src\utils 2>nul
mkdir backend 2>nul

echo 1. Tạo frontend/public/index.html...
(
echo ^<!DOCTYPE html^>
echo ^<html lang="vi"^>
echo ^<head^>
echo     ^<meta charset="utf-8" /^>
echo     ^<link rel="icon" href="%%PUBLIC_URL%%/favicon.ico" /^>
echo     ^<meta name="viewport" content="width=device-width, initial-scale=1" /^>
echo     ^<meta name="theme-color" content="#000000" /^>
echo     ^<meta name="description" content="SMART-MATCH AI - Nền tảng kết nối sinh viên và giảng viên cho hoạt động NCKH" /^>
echo     ^<title^>SMART-MATCH AI ^| BK Smart Campus^</title^>
echo ^</head^>
echo ^<body^>
echo     ^<noscript^>You need to enable JavaScript to run this app.^</noscript^>
echo     ^<div id="root"^>^</div^>
echo ^</body^>
echo ^</html^>
) > frontend\public\index.html

echo 2. Tạo frontend/src/index.js...
(
echo import React from 'react';^
echo import ReactDOM from 'react-dom/client';^
echo import './index.css';^
echo import App from './App';^
echo.^
echo const root = ReactDOM.createRoot(document.getElementById('root'));^
echo root.render(^
echo   ^<React.StrictMode^>^
echo     ^<App /^>^
echo   ^</React.StrictMode^>^
echo );^
) > frontend\src\index.js

echo 3. Tạo frontend/src/index.css...
(
echo @tailwind base;^
echo @tailwind components;^
echo @tailwind utilities;^
echo.^
echo body {^
echo   margin: 0;^
echo   font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',^
echo     'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',^
echo     sans-serif;^
echo   -webkit-font-smoothing: antialiased;^
echo   -moz-osx-font-smoothing: grayscale;^
echo }^
echo.^
echo code {^
echo   font-family: source-code-pro, Menlo, Monaco, Consolas, 'Courier New',^
echo     monospace;^
echo }^
) > frontend\src\index.css

echo 4. Tạo các file .env...
(
echo SECRET_KEY=smart-match-ai-secret-key-2025^
echo DATABASE_URL=postgresql://postgres:password@localhost:5432/smartmatch^
echo MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2^
echo FLASK_ENV=development^
) > backend\.env

(
echo REACT_APP_API_URL=http://localhost:5000^
) > frontend\.env

echo 5. Tạo tailwind.config.js...
(
echo module.exports = {^
echo   content: [^
echo     "./src/**/*.{js,jsx,ts,tsx}",^
echo   ],^
echo   theme: {^
echo     extend: {},^
echo   },^
echo   plugins: [],^
echo }^
) > frontend\tailwind.config.js

echo 6. Tạo Dockerfiles...
:: Backend Dockerfile
(
echo FROM python:3.9-slim^
echo.^
echo WORKDIR /app^
echo.^
echo COPY requirements.txt .^
echo RUN pip install --no-cache-dir -r requirements.txt^
echo.^
echo COPY . .^
echo.^
echo EXPOSE 5000^
echo.^
echo CMD ["python", "app.py"]^
) > backend\Dockerfile

:: Frontend Dockerfile
(
echo FROM node:18-alpine^
echo.^
echo WORKDIR /app^
echo.^
echo COPY package*.json ./^
echo RUN npm install^
echo.^
echo COPY . .^
echo.^
echo EXPOSE 3000^
echo.^
echo CMD ["npm", "start"]^
) > frontend\Dockerfile

echo.^
echo === HOÀN TẤT ===^
echo.^
echo CÁC BƯỚC TIẾP THEO:^
echo 1. Cài đặt Docker Desktop từ: https://www.docker.com/products/docker-desktop/^
echo 2. Mở Docker Desktop và đợi nó chạy^
echo 3. Mở PowerShell hoặc Command Prompt với quyền Administrator^
echo 4. Chạy lệnh: docker-compose up --build^
echo 5. Truy cập: http://localhost:3000^
echo.^
pause
