# Entro Library Signup Enhancement

Module mở rộng chức năng đăng ký thành viên thư viện với quy trình phê duyệt.

## Tính năng

### 1. Form đăng ký mở rộng
- **Thông tin cá nhân**: Họ tên, email, điện thoại, ngày sinh, giới tính
- **Loại thành viên**: Chọn loại độc giả (sinh viên, giáo viên, v.v.)
- **Giấy tờ**: CMND/CCCD, Mã sinh viên/học sinh
- **Địa chỉ**: Địa chỉ đầy đủ
- **Ghi chú**: Thông tin bổ sung

### 2. Quy trình phê duyệt
- Yêu cầu đăng ký được lưu với trạng thái "Chờ duyệt"
- Quản lý thư viện nhận thông báo
- Xem xét và phê duyệt/từ chối
- Tự động tạo tài khoản khi phê duyệt

### 3. Quản lý yêu cầu
- Danh sách tất cả yêu cầu đăng ký
- Lọc theo trạng thái
- Chi tiết thông tin đăng ký
- Nút phê duyệt/từ chối nhanh
- Ghi chú lý do từ chối

### 4. Email thông báo
- Email thông báo khi được duyệt (kèm link đặt mật khẩu)
- Email thông báo khi bị từ chối (kèm lý do)
- Email đẹp mắt với HTML

## Cài đặt

### Yêu cầu
- `entro_library`
- `entro_library_website`
- `auth_signup`

### Các bước
1. Cài đặt module `entro_library_signup`
2. Module sẽ tự động:
   - Thêm menu "Yêu cầu đăng ký" cho Library Manager
   - Thêm link "Đăng ký" vào header website
   - Tạo email templates

## Sử dụng

### Cho người dùng

1. Truy cập `/web/library/signup`
2. Điền form đăng ký đầy đủ
3. Nhấn "Gửi đăng ký"
4. Chờ email thông báo phê duyệt
5. Click link trong email để đặt mật khẩu
6. Đăng nhập và sử dụng

### Cho quản lý thư viện

1. Vào menu **Thư Viện > Yêu cầu đăng ký**
2. Xem danh sách yêu cầu chờ duyệt
3. Mở chi tiết yêu cầu
4. Click **"Duyệt"** hoặc **"Từ chối"**
5. Nếu từ chối, nhập lý do
6. Hệ thống tự động:
   - Tạo Partner
   - Tạo User (với Portal access)
   - Gán Borrower Type
   - Gửi email thông báo
   - Gửi email đặt mật khẩu

## URL Routes

- `/web/library/signup` - Form đăng ký
- `/web/library/signup/submit` - Submit form (POST)
- `/web/library/signup/success` - Trang thành công

## Models

### library.signup.request
Lưu trữ yêu cầu đăng ký với đầy đủ thông tin.

**Fields:**
- Personal info: name, email, phone, DOB, gender
- Address: street, city, state, country, zip
- Documents: id_card_number, student_id
- Type: borrower_type_id, organization
- Status: state (pending/approved/rejected)
- Relations: partner_id, user_id

**Methods:**
- `action_approve()` - Phê duyệt và tạo tài khoản
- `action_reject()` - Từ chối yêu cầu
- `action_reset_to_pending()` - Đặt lại chờ duyệt

## Quyền truy cập

- **Library Manager**: Full access
- **Library User**: Read only
- **Public**: Create only (qua website)

## Email Templates

1. **mail_template_signup_approved**
   - Gửi khi phê duyệt
   - Thông báo tài khoản đã được kích hoạt
   - Link đăng nhập

2. **mail_template_signup_rejected**
   - Gửi khi từ chối
   - Lý do từ chối
   - Link đăng ký lại

## Tùy chỉnh

### Thêm field vào form đăng ký

Edit file `views/signup_templates.xml`:
```xml
<div class="col-md-6 mb-3">
    <label class="form-label">Field mới</label>
    <input type="text" name="new_field" class="form-control"/>
</div>
```

Thêm field vào model `library_signup_request.py`:
```python
new_field = fields.Char(string='Field mới')
```

### Thay đổi email template

Edit file `data/mail_template_data.xml`

### Thêm validation

Override method `action_approve()` hoặc thêm constraint.

## Lưu ý

- Email cần được cấu hình đúng trong Odoo
- Đảm bảo có ít nhất 1 Borrower Type
- Quản lý thư viện cần có group `entro_library.group_library_manager`
- Link "Đăng ký" sẽ xuất hiện trên header website

## Troubleshooting

### Email không được gửi
- Kiểm tra cấu hình email server
- Xem log: Settings > Technical > Email > Emails

### Không thấy menu "Yêu cầu đăng ký"
- Kiểm tra user có group Library Manager

### Form đăng ký bị lỗi
- Kiểm tra có Borrower Type nào không
- Xem browser console (F12)

## Hỗ trợ

Email: support@entro.vn
