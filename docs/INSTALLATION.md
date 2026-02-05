# FocusGuard - Hướng dẫn Cài đặt

## Yêu cầu Hệ thống

### Phần cứng
- CPU: Intel Core i3 trở lên
- RAM: 4GB tối thiểu (khuyến nghị 8GB)
- Webcam: USB hoặc tích hợp
- Kết nối mạng: LAN hoặc WiFi

### Phần mềm
- Hệ điều hành: Windows 10+, Ubuntu 20.04+, macOS 10.15+
- Python: 3.10 - 3.12

---

## Cài đặt Server

### 1. Clone repository
```bash
git clone https://github.com/your-repo/focusguard.git
cd focusguard
```

### 2. Tạo virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 3. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 4. Khởi tạo database
```bash
python init_database.py
```

### 5. Chạy server
```bash
python run_server.py
```

Server sẽ chạy tại `http://localhost:8000`

---

## Cài đặt Client

### 1. Cài đặt dependencies (cùng project)
```bash
pip install -r requirements.txt
```

### 2. Chạy client
```bash
python run_client.py
```

---

## Cấu hình

### Server (shared/constants.py)
```python
SERVER_HOST = "0.0.0.0"  # Bind address
SERVER_PORT = 8000       # Port
```

### Tài khoản mặc định
| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | Admin |

---

## Xử lý lỗi thường gặp

### 1. Webcam không hoạt động
```bash
# Kiểm tra camera
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```
- Đảm bảo không có ứng dụng khác đang sử dụng camera
- Thử đổi CAMERA_INDEX trong config

### 2. Không kết nối được server
- Kiểm tra firewall
- Đảm bảo server đang chạy
- Kiểm tra đúng IP/Port

### 3. Module không tìm thấy
```bash
pip install -r requirements.txt --force-reinstall
```

---

## Liên hệ hỗ trợ
- Email: support@focusguard.edu.vn
- Hotline: 1900-xxxx
