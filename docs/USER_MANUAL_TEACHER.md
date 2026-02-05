# FocusGuard - Hướng dẫn Sử dụng cho Giáo viên

## 1. Đăng nhập Hệ thống

1. Mở trình duyệt, truy cập: `http://localhost:8000`
2. Nhập **Username** và **Password**
3. Nhấn **Login**

---

## 2. Quản lý Bài thi

### 2.1 Tạo Bài thi mới

1. Vào menu **Exams** (hoặc truy cập `/exams`)
2. Nhấn **Create New Exam**
3. Điền thông tin:
   - **Exam Name**: Tên bài thi (VD: "Kiểm tra giữa kỳ Toán")
   - **Exam Date**: Ngày thi
   - **Duration**: Thời gian thi (phút)
   - **Max Violations**: Số vi phạm tối đa (mặc định: 5)
4. Nhấn **Create Exam**
5. Hệ thống tạo **Exam Code** (6 ký tự) - Chia sẻ mã này cho sinh viên

### 2.2 Bắt đầu Bài thi

1. Chọn bài thi từ danh sách
2. Nhấn **Start Exam**
3. Đồng hồ đếm ngược bắt đầu
4. Sinh viên có thể tham gia qua mã code

### 2.3 Kết thúc Bài thi

1. Nhấn **End Exam** hoặc đợi hết giờ
2. Hệ thống lưu tất cả dữ liệu

---

## 3. Giám sát Thời gian thực

### 3.1 Dashboard Giám sát

- **Xanh lá**: Sinh viên bình thường
- **Đỏ**: Đang có hành vi vi phạm
- **Xám**: Offline/Mất kết nối

### 3.2 Các loại Vi phạm

| Hành vi | Mô tả |
|---------|-------|
| Looking Left | Nhìn sang trái |
| Looking Right | Nhìn sang phải |
| Head Down | Cúi đầu |
| Talking | Nói chuyện |
| No Face | Không phát hiện khuôn mặt |

### 3.3 Cờ cảnh báo

- Sinh viên vượt quá **Max Violations** sẽ bị **đánh dấu cờ đỏ**
- Bạn có thể xem chi tiết vi phạm kèm **ảnh chụp màn hình**

---

## 4. Xem Báo cáo

### 4.1 Báo cáo Vi phạm

1. Chọn bài thi đã kết thúc
2. Nhấn **View Report** bên cạnh tên sinh viên
3. Xem danh sách vi phạm với:
   - Thời gian
   - Loại hành vi
   - Độ tin cậy
   - Ảnh chụp

### 4.2 Thống kê

- Tổng số vi phạm
- Số sinh viên bị cờ
- Tỷ lệ vi phạm theo loại

---

## 5. Quản lý Người dùng (Admin)

### 5.1 Tạo Tài khoản

1. Vào **Admin > Users**
2. Nhấn **Create User**
3. Điền: Username, Password, Full Name, Role
4. Nhấn **Create**

### 5.2 Vai trò

| Role | Quyền hạn |
|------|-----------|
| Admin | Toàn quyền |
| Teacher | Tạo/quản lý bài thi |
| Student | Tham gia thi |

---

## 6. Hỗ trợ

- **F5**: Làm mới trang
- **Ctrl+Shift+R**: Xóa cache và làm mới
- Nếu gặp lỗi, liên hệ bộ phận IT
