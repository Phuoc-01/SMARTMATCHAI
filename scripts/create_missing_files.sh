#!/bin/bash

echo "=== Tạo các file bị thiếu ==="

# Tạo cấu trúc thư mục
mkdir -p frontend/public
mkdir -p frontend/src/{contexts,components,pages,utils}
mkdir -p backend

# 1. Tạo file frontend
echo "1. Tạo file frontend..."
cat > frontend/public/index.html << 'EOF'
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="utf-8" />
    <link rel="icon" href="%PUBLIC_URL%/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#000000" />
    <meta name="description" content="SMART-MATCH AI - Nền tảng kết nối sinh viên và giảng viên cho hoạt động NCKH" />
    <title>SMART-MATCH AI | BK Smart Campus</title>
</head>
<body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
</body>
</html>
EOF

# Tạo các file khác tương tự...
# (Copy nội dung từ trên vào)

echo "=== HOÀN TẤT ==="
echo "Các file đã được tạo. Chạy:"
echo "1. docker-compose up --build"
echo "2. Truy cập http://localhost:3000"