# Quick Start Guide - Library Signup Enhancement

## 🚀 Installation (5 phút)

1. **Cài module**
   ```
   Apps > Update Apps List > Tìm "Entro: Library Signup Enhancement" > Install
   ```

2. **Kiểm tra**
   - Menu "Yêu cầu đăng ký" xuất hiện trong Thư Viện
   - Link "Đăng ký" xuất hiện trên website header

---

## 👤 Hướng dẫn người dùng

### Đăng ký tài khoản mới

1. Vào website thư viện
2. Click "Đăng ký" ở header
3. Điền form (các trường có dấu * là bắt buộc)
4. Click "Gửi đăng ký"
5. Chờ email thông báo

### Sau khi được duyệt

1. Check email (cả thư mục spam)
2. Mở email "Tài khoản đã được kích hoạt"
3. Click link trong email để đặt mật khẩu
4. Đăng nhập và bắt đầu mượn sách

---

## 👨‍💼 Hướng dẫn quản lý thư viện

### Duyệt yêu cầu đăng ký

1. **Xem danh sách**
   - Menu: Thư Viện > Yêu cầu đăng ký
   - Mặc định hiển thị yêu cầu "Chờ duyệt"

2. **Mở chi tiết**
   - Click vào yêu cầu cần xem xét
   - Kiểm tra thông tin đầy đủ

3. **Phê duyệt**
   - Click nút "Duyệt" ở header
   - Hệ thống tự động:
     * Tạo Partner
     * Tạo User (Portal)
     * Gửi 2 emails (thông báo + đặt mật khẩu)

4. **Từ chối (nếu cần)**
   - Click nút "Từ chối"
   - Nhập lý do từ chối
   - Confirm
   - Email từ chối được gửi tự động

### Quản lý yêu cầu

**Filters hữu ích:**
- "Chờ duyệt" - Yêu cầu mới cần xử lý
- "Đã duyệt" - Đã tạo tài khoản
- "Đã từ chối" - Bị từ chối

**Group By:**
- Trạng thái
- Loại độc giả
- Ngày tạo

---

## 🔧 Troubleshooting

### Email không được gửi

**Nguyên nhân:** Email server chưa cấu hình

**Giải pháp:**
1. Settings > General Settings
2. Cuộn xuống "Email Servers"
3. Configure email
4. Test connection

### Không thấy menu "Yêu cầu đăng ký"

**Nguyên nhân:** User không có quyền Library Manager

**Giải pháp:**
1. Settings > Users & Companies > Users
2. Chọn user
3. Tab "Access Rights"
4. Thêm group "Library / Manager"

### Form đăng ký bị lỗi 404

**Nguyên nhân:** Module chưa cài hoặc website chưa publish

**Giải pháp:**
1. Kiểm tra module đã install
2. Restart Odoo nếu cần
3. Clear browser cache

### Người dùng không nhận được email đặt mật khẩu

**Nguyên nhân:** Email trong spam hoặc email server lỗi

**Giải pháp:**
1. Hướng dẫn user check spam
2. Trong backend: Open user > Click "Send Password Reset Email"
3. Hoặc: Set password manually trong backend

---

## 📧 Email Templates

### Customization

**File:** `data/mail_template_data.xml`

**Records:**
- `mail_template_signup_approved` - Email phê duyệt
- `mail_template_signup_rejected` - Email từ chối

**Edit:** Sửa field `body_html` để thay đổi nội dung

---

## ⚙️ Configuration

### Mandatory Setup

✅ **Borrower Types** (Bắt buộc)
- Menu: Thư Viện > Configuration > Loại độc giả
- Tạo ít nhất 1 type (VD: Sinh viên, Giáo viên)

✅ **Email Server** (Bắt buộc cho email)
- Settings > General Settings > Email Servers

### Optional Setup

🔧 **Customize Form**
- File: `views/signup_templates.xml`
- Thêm/bớt fields theo nhu cầu

🔧 **Customize Approval Logic**
- File: `models/library_signup_request.py`
- Method: `action_approve()`

---

## 📞 Support

**Email:** support@entro.vn
**Documentation:** See README.md

---

## ✅ Quick Checklist

Sau khi cài đặt, check những điều sau:

Backend:
- [ ] Menu "Yêu cầu đăng ký" visible
- [ ] Có ít nhất 1 Borrower Type
- [ ] Email server configured

Website:
- [ ] Link "Đăng ký" xuất hiện ở header
- [ ] Form /web/library/signup mở được
- [ ] Form có dropdown "Loại độc giả" với dữ liệu

Test Flow:
- [ ] Đăng ký 1 tài khoản test
- [ ] Yêu cầu xuất hiện trong backend
- [ ] Duyệt yêu cầu thành công
- [ ] Partner được tạo
- [ ] User được tạo với Portal access
- [ ] Email được gửi

---

**That's it! You're ready to go! 🎉**
