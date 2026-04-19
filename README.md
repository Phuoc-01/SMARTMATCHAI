# SMARTMATCHAI / WEBMATCH

Nền tảng ghép cặp **Sinh viên ↔ Đề tài nghiên cứu** bằng AI (Sentence Transformers) và tìm kiếm vector với **pgvector**.

## Tech stack

- Backend: Flask + SQLAlchemy
- Database: PostgreSQL + pgvector
- AI: sentence-transformers (PyTorch)
- Frontend: HTML tĩnh (phục vụ bằng `python -m http.server`)

## Ports (mặc định)

- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- PostgreSQL: localhost:5432
- Adminer (tuỳ chọn): http://localhost:8080

## Chạy nhanh bằng Docker (khuyến nghị)

### 1) Yêu cầu

- Docker Desktop (Windows/macOS) hoặc Docker Engine (Linux)

### 2) (Tuỳ chọn) Tạo file cấu hình môi trường

Repo có file `.env.example`. Bạn có thể copy thành `.env` để tuỳ biến:

```powershell
Copy-Item .env.example .env
```

Các biến hay dùng (nếu không set sẽ dùng giá trị mặc định trong `docker-compose.yml`):

- `DB_PASSWORD`
- `SECRET_KEY`
- `BOOTSTRAP_ADMIN_KEY`

### 3) Start services

```powershell
# Docker Compose v2
docker compose up --build

# (Nếu máy bạn dùng docker-compose)
# docker-compose up --build
```

Mở:

- Frontend: http://localhost:3000
- Adminer (tuỳ chọn): http://localhost:8080

Ghi chú: container Postgres sẽ chạy init script tại `database/init.sql` **chỉ khi volume DB còn trống**.

## Chạy local (không Docker)

### 1) Yêu cầu

- Python 3.10+ (khuyến nghị 3.10 để khớp Dockerfile backend)
- PostgreSQL có cài extension `pgvector`

### 2) Tạo DB + extensions

Bạn cần tạo database `smartmatch` và bật extensions `pgcrypto` + `vector`.
Script mẫu có sẵn trong `database/init.sql`.

Cách nhanh (tuỳ môi trường Postgres của bạn):

```sql
CREATE DATABASE smartmatch;
\c smartmatch
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3) Cài backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

### 4) Set biến môi trường bắt buộc

Backend **bắt buộc** có `DATABASE_URL` (nếu thiếu sẽ báo lỗi ngay khi khởi động).

PowerShell:

```powershell
$env:DATABASE_URL = "postgresql://postgres:<PASSWORD>@localhost:5432/smartmatch"
```

### 5) Chạy backend

```powershell
cd backend
python app.py
```

### 6) Chạy frontend (HTML tĩnh)

Mở terminal khác:

```powershell
cd frontend\public
python -m http.server 3000
```

Sau đó mở http://localhost:3000

## Tạo admin (Bootstrap) (tuỳ chọn)

Backend có endpoint bootstrap:

- `POST http://localhost:5000/api/admin/bootstrap`
- Header: `X-Bootstrap-Key: <BOOTSTRAP_ADMIN_KEY>`

Trong Docker, `BOOTSTRAP_ADMIN_KEY` có thể set qua `.env` hoặc dùng mặc định trong `docker-compose.yml`.

## Seed dữ liệu demo (tuỳ chọn)

Seed sẽ import `backend/app.py`, vì vậy bạn vẫn cần `DATABASE_URL` trỏ tới Postgres.

```powershell
# đang ở thư mục repo
$env:DATABASE_URL = "postgresql://postgres:<PASSWORD>@localhost:5432/smartmatch"
python backend\seed.py

python backend\verify_seed_counts.py
```

## Database notes

- `database/init.sql`: dùng để khởi tạo DB mới (Docker mount file này khi tạo container Postgres lần đầu).
- `database/migrations/`: các file SQL idempotent để cập nhật schema cho DB **đã tồn tại** (không tự chạy, dùng khi bạn muốn nâng cấp schema mà không xoá volume).

## Troubleshooting

- **Lỗi `DATABASE_URL environment variable is required`**: bạn chưa set `DATABASE_URL` khi chạy local.
- **Model tải lâu / nặng**: lần chạy đầu cần tải model sentence-transformers (mạng chậm sẽ lâu).
- **Port bị chiếm**: đổi port trong `docker-compose.yml` hoặc dừng tiến trình đang dùng port 3000/5000/5432.

---
