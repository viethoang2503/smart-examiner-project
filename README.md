# SMART EXAMINER - AI Proctoring System

**English** | [Tiếng Việt](#tiếng-việt)

---

## English

### Overview
Smart Examiner is an AI-powered exam proctoring system that detects cheating behaviors in real-time using computer vision and machine learning.

### Features
- **Face Detection** - MediaPipe Face Mesh with 468 landmarks
- **Behavior Detection** - Looking left/right, head down, talking
- **Real-time Monitoring** - WebSocket-based live updates
- **Web Dashboard** - Teacher monitoring interface
- **Violation Evidence** - Screenshot capture on detection
- **Exam Management** - 6-character exam codes

### Quick Start

```bash
# Clone repository
git clone https://github.com/viethoang2503/smart-examiner-project.git
cd smart-examiner-project

# Setup (Linux/macOS)
chmod +x deploy.sh
./deploy.sh install
./deploy.sh server   # Run server
./deploy.sh client   # Run client (new terminal)

# Setup (Windows)
deploy.bat install
deploy.bat server
deploy.bat client
```

### Project Structure

```
focusguard/
├── client/           # Client application
│   ├── ai_engine/    # Face detection, geometry, classifier
│   ├── gui/          # PyQt6 dialogs
│   └── network/      # WebSocket client
├── server/           # FastAPI server
├── shared/           # Shared constants
├── ml/               # ML model training
├── tests/            # Test suites
└── docs/             # Documentation
```

### Performance

| Metric | Value |
|--------|-------|
| Latency | 37ms avg |
| FPS | 27 fps |
| Detection Rate | 100% |

### Documentation
- [Installation Guide](docs/INSTALLATION.md)
- [Teacher Manual](docs/USER_MANUAL_TEACHER.md)
- [Student Manual](docs/USER_MANUAL_STUDENT.md)

---

## Tiếng Việt

### Giới thiệu
Smart Examiner là hệ thống giám sát thi cử sử dụng AI để phát hiện hành vi gian lận theo thời gian thực bằng thị giác máy tính và học máy.

### Tính năng
- **Nhận diện khuôn mặt** - MediaPipe Face Mesh với 468 điểm landmark
- **Phát hiện hành vi** - Nhìn trái/phải, cúi đầu, nói chuyện
- **Giám sát thời gian thực** - Cập nhật trực tiếp qua WebSocket
- **Dashboard web** - Giao diện giám sát cho giáo viên
- **Bằng chứng vi phạm** - Chụp ảnh khi phát hiện vi phạm
- **Quản lý bài thi** - Mã bài thi 6 ký tự

### Cài đặt nhanh

```bash
# Clone repository
git clone https://github.com/viethoang2503/smart-examiner-project.git
cd smart-examiner-project

# Cài đặt (Linux/macOS)
chmod +x deploy.sh
./deploy.sh install
./deploy.sh server   # Chạy server
./deploy.sh client   # Chạy client (terminal mới)

# Cài đặt (Windows)
deploy.bat install
deploy.bat server
deploy.bat client
```

### Hiệu năng

| Chỉ số | Giá trị |
|--------|---------|
| Độ trễ | 37ms trung bình |
| FPS | 27 khung/giây |
| Tỷ lệ phát hiện | 100% |

### Tài liệu
- [Hướng dẫn Cài đặt](docs/INSTALLATION.md)
- [Hướng dẫn Giáo viên](docs/USER_MANUAL_TEACHER.md)
- [Hướng dẫn Sinh viên](docs/USER_MANUAL_STUDENT.md)

---

## License

MIT License

## Author

Viet Hoang - USTH 2026
