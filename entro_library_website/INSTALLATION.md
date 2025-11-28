# Hướng dẫn Cài đặt Entro Library Website

## Tổng quan

Module `entro_library_website` cung cấp giao diện website công khai và portal cho hệ thống thư viện Odoo.

## Yêu cầu

- Odoo 18.0
- Module `entro_library` đã được cài đặt
- Module `website` (core Odoo)
- Module `portal` (core Odoo)

## Các bước cài đặt

### 1. Cài đặt Module

1. Module đã có sẵn tại: `customize/EntroLibraryManagement/entro_library_website`
2. Khởi động lại Odoo server (nếu cần):
   ```bash
   ./odoo-bin -c odoo.conf
   ```
3. Vào **Apps** > Cập nhật danh sách ứng dụng
4. Tìm kiếm "Entro: Thư Viện Website"
5. Click **Install**

### 2. Cấu hình ban đầu

#### A. Xuất bản sách lên website

1. Vào menu **Thư Viện** > **Sách**
2. Mở một cuốn sách bất kỳ
3. Chuyển sang tab **Website**
4. Đánh dấu checkbox **"Xuất bản lên Website"**
5. (Tùy chọn) Điền thông tin SEO:
   - **Tiêu đề Meta**: Tiêu đề hiển thị trên Google
   - **Mô tả Meta**: Mô tả ngắn (160 ký tự)
   - **Từ khóa Meta**: Từ khóa phân cách bằng dấu phẩy
6. Lưu lại
7. Click nút **"Xuất bản Web"** ở header (hoặc "Gỡ khỏi Web" để ẩn)

#### B. Cấu hình menu website

Menu đã được tự động tạo:
- **Thư Viện** (`/thu-vien`)
  - Các Kho Tài Nguyên
  - Phiếu Mượn Của Tôi (chỉ hiển thị khi đăng nhập)
  - Giỏ Mượn Sách

Để chỉnh sửa menu:
1. Vào **Website** > **Configuration** > **Menus**
2. Tìm và chỉnh sửa các menu đã tạo

### 3. Cấu hình Portal

#### Cho phép người dùng truy cập portal

1. Vào **Settings** > **Users & Companies** > **Users**
2. Chọn user cần cấp quyền
3. Trong tab **Access Rights**, thêm group **Portal**
4. Lưu lại

User giờ có thể:
- Đăng nhập vào `/my`
- Xem phiếu mượn của mình
- Quản lý đặt trước
- Sử dụng giỏ mượn sách

### 4. Kiểm tra chức năng

#### Trang công khai (không cần đăng nhập)

1. Mở trình duyệt
2. Truy cập: `http://your-domain.com/thu-vien`
3. Kiểm tra:
   - Danh sách sách hiển thị đúng
   - Tìm kiếm hoạt động
   - Lọc theo danh mục
   - Click vào sách để xem chi tiết
   - Xem sách theo kho tài nguyên: `/thu-vien/cac-kho`

#### Portal (cần đăng nhập)

1. Đăng nhập với tài khoản portal user
2. Vào `/my/borrowings` - xem phiếu mượn
3. Vào `/my/reservations` - xem đặt trước
4. Vào `/my/borrowing-cart` - xem giỏ mượn
5. Thử thêm sách vào giỏ từ trang chi tiết sách

## Cấu trúc URL

```
# Trang công khai
/thu-vien                              → Danh sách tất cả sách
/thu-vien/trang/<page>                 → Phân trang
/thu-vien/danh-muc/<category_id>       → Lọc theo danh mục
/thu-vien/sach/<slug>-<id>             → Chi tiết sách
/thu-vien/kho-tai-nguyen/<resource_id> → Sách theo kho
/thu-vien/cac-kho                      → Danh sách các kho

# Portal (yêu cầu đăng nhập)
/my/borrowings                         → Phiếu mượn của tôi
/my/borrowing/<id>                     → Chi tiết phiếu mượn
/my/reservations                       → Đặt trước của tôi
/my/borrowing-cart                     → Giỏ mượn sách
/my/borrowing-history                  → Lịch sử và thống kê
```

## Tùy chỉnh giao diện

### Chỉnh sửa CSS

File: `static/src/scss/library_website.scss`

```scss
// Ví dụ: Đổi màu chủ đạo
.book_card {
    &:hover {
        border-color: #your-color;
    }
}
```

### Chỉnh sửa template

Các template QWeb nằm trong:
- `views/templates.xml` - Trang công khai
- `views/portal_templates.xml` - Trang portal

## Xử lý sự cố

### Lỗi: Không thấy sách trên website

**Nguyên nhân**: Sách chưa được xuất bản

**Giải pháp**:
1. Kiểm tra field `website_published = True`
2. Kiểm tra field `active = True`
3. Kiểm tra quyền truy cập (ir.rule)

### Lỗi: Không thể thêm sách vào giỏ

**Nguyên nhân**:
- Người dùng chưa đăng nhập
- Không có bản sao available
- Vi phạm giới hạn mượn

**Giải pháp**:
1. Đảm bảo user đã đăng nhập
2. Kiểm tra `book.available_quant_count > 0`
3. Kiểm tra `book.can_borrow = True`
4. Kiểm tra giới hạn của resource

### Lỗi: Access denied trên portal

**Nguyên nhân**: Thiếu record rules hoặc access rights

**Giải pháp**:
1. Kiểm tra file `security/portal_security.xml`
2. Kiểm tra file `security/ir.model.access.csv`
3. Cập nhật module để load lại security

## Bảo mật

### Record Rules đã được cấu hình

- Portal users chỉ xem được phiếu mượn của mình
- Portal users chỉ xem được đặt trước của mình
- Public users chỉ xem được sách đã published
- Portal users KHÔNG thể chỉnh sửa/xóa dữ liệu

### Best Practices

1. **Không cho phép portal user chỉnh sửa dữ liệu** qua website
2. **Luôn validate dữ liệu** trước khi thêm vào giỏ
3. **Kiểm tra giới hạn mượn** của resource
4. **Log các hành động quan trọng** (mượn, trả, hủy)

## Hỗ trợ

Nếu gặp vấn đề:
1. Kiểm tra Odoo logs: `tail -f odoo.log`
2. Kiểm tra browser console (F12)
3. Liên hệ: support@entro.vn

## Cập nhật Module

```bash
# Backup database trước
./odoo-bin -c odoo.conf -d your_db -u entro_library_website
```

## Changelog

### Version 18.0.1.0.0
- Phát hành lần đầu
- Trang danh sách và chi tiết sách
- Portal cho người mượn
- Giỏ mượn sách online
- SEO-friendly URLs tiếng Việt
