# Entro Library Website Module

Module website công khai cho hệ thống thư viện Odoo 18.

## Tính năng

### Trang công khai
- **Danh sách sách**: Hiển thị tất cả sách đã xuất bản
- **Chi tiết sách**: Trang thông tin đầy đủ về sách
- **Lọc và tìm kiếm**: Theo danh mục, tác giả, từ khóa
- **Theo kho tài nguyên**: Xem sách theo từng thư viện/chi nhánh
- **SEO-friendly URLs**: Slug tiếng Việt cho URL

### Portal cho người dùng
- **Phiếu mượn của tôi**: Xem lịch sử và trạng thái mượn sách
- **Chi tiết phiếu mượn**: Thông tin chi tiết từng phiếu
- **Đặt trước**: Quản lý danh sách đặt trước
- **Giỏ mượn sách**: Thêm sách vào giỏ trước khi mượn
- **Thống kê cá nhân**: Lịch sử và thống kê mượn sách

## Cài đặt

1. Copy module vào thư mục addons
2. Cập nhật danh sách module trong Odoo
3. Cài đặt module `entro_library_website`

## Cấu hình

### Xuất bản sách lên website

1. Mở form sách trong backend
2. Chuyển sang tab "Website"
3. Đánh dấu "Xuất bản lên Website"
4. Điền thông tin SEO (tùy chọn)
5. Click "Xuất bản Web" trong header

### URL cấu trúc

```
/thu-vien                           → Tất cả sách
/thu-vien/sach/<slug>-<id>          → Chi tiết sách
/thu-vien/danh-muc/<id>             → Sách theo danh mục
/thu-vien/kho-tai-nguyen/<id>       → Sách theo kho
/thu-vien/cac-kho                   → Danh sách kho tài nguyên
/my/borrowings                      → Phiếu mượn của tôi
/my/reservations                    → Đặt trước của tôi
/my/borrowing-cart                  → Giỏ mượn sách
```

## Phụ thuộc

- `entro_library`: Module thư viện cơ sở
- `website`: Module website Odoo
- `portal`: Module portal Odoo

## Tác giả

Entro - https://www.entro.vn

## Giấy phép

LGPL-3
