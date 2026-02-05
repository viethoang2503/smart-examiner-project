# FocusGuard - AI Proctoring System

Hệ thống giám sát thi cử sử dụng AI để phát hiện hành vi gian lận thời gian thực.

## Tính năng

- **Nhận diện khuôn mặt** với MediaPipe Face Mesh
- **Phát hiện hành vi**: Nhìn trái/phải, cúi đầu, nói chuyện
- **Giám sát thời gian thực** qua WebSocket
- **Dashboard web** cho giáo viên
- **Chụp ảnh vi phạm** làm bằng chứng
- **Quản lý bài thi** với mã code 6 ký tự

## Cài đặt nhanh

### Linux/macOS
```bash
chmod +x deploy.sh
./deploy.sh install
./deploy.sh server   # Chạy server
./deploy.sh client   # Chạy client (terminal khác)
```

### Windows
```cmd
deploy.bat install
deploy.bat server    :: Chạy server
deploy.bat client    :: Chạy client (terminal khác)
```

## Cấu trúc Project

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

## Tài liệu

- [Hướng dẫn Cài đặt](docs/INSTALLATION.md)
- [Hướng dẫn Giáo viên](docs/USER_MANUAL_TEACHER.md)
- [Hướng dẫn Sinh viên](docs/USER_MANUAL_STUDENT.md)

## Hiệu năng

| Metric | Giá trị |
|--------|---------|
| Latency | 37ms avg |
| FPS | 27 fps |
| Detection Rate | 100% |

## License

MIT License
