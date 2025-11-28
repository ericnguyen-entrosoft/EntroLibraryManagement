# Installation Checklist - Entro Library Website

## ✅ Pre-Installation Check

- [ ] Odoo 18.0 is installed
- [ ] Module `entro_library` is installed and working
- [ ] Module `website` is installed (Odoo core)
- [ ] Module `portal` is installed (Odoo core)
- [ ] Database backup created

## ✅ Installation Steps

- [ ] Module files are in `customize/EntroLibraryManagement/entro_library_website/`
- [ ] Odoo can see the module in Apps list
- [ ] Install module `entro_library_website`
- [ ] No installation errors in log

## ✅ Post-Installation Verification

### A. Backend Checks

- [ ] New tab "Website" appears in library.book form
- [ ] Can toggle "Xuất bản lên Website" checkbox
- [ ] Button "Xuất bản Web" / "Gỡ khỏi Web" works
- [ ] Website URL field is auto-computed

### B. Public Website Checks (No Login)

- [ ] Access `/thu-vien` - Book listing page loads
- [ ] Search box works
- [ ] Category filter works
- [ ] Can click on a book card
- [ ] Book detail page shows full information
- [ ] Image displays correctly
- [ ] Tabs work (Tóm tắt, Chi tiết, Phương tiện)
- [ ] Related books section appears
- [ ] Access `/thu-vien/cac-kho` - Resources list shows
- [ ] Can access resource-specific page

### C. Portal Checks (Requires Portal User Login)

- [ ] Login with portal user
- [ ] Access `/my` - See "Phiếu mượn" and "Đặt trước" counters
- [ ] Access `/my/borrowings` - Borrowing list loads
- [ ] Can view borrowing detail
- [ ] Access `/my/reservations` - Reservation list loads
- [ ] Access `/my/borrowing-cart` - Cart page loads
- [ ] Can add book to cart from book detail page
- [ ] "Thêm vào giỏ mượn" button works
- [ ] Can remove book from cart
- [ ] Can checkout (confirm borrowing)

### D. Menu Checks

- [ ] Website menu "Thư Viện" appears in header
- [ ] Submenu items show correctly
- [ ] Clicking menu items navigates correctly

### E. Responsive Checks

- [ ] Open on desktop - Layout looks good
- [ ] Open on tablet - Layout adapts
- [ ] Open on mobile - Layout stacks correctly
- [ ] All buttons are clickable on mobile

### F. SEO Checks

- [ ] View page source - Meta tags present
- [ ] URLs are SEO-friendly (Vietnamese slugs)
- [ ] Images have alt tags
- [ ] Breadcrumbs are correct

## ✅ Security Checks

- [ ] Anonymous users can see published books
- [ ] Anonymous users cannot see unpublished books
- [ ] Portal users can see their own borrowings only
- [ ] Portal users cannot edit borrowings via portal
- [ ] Portal users can cancel their reservations
- [ ] Access denied errors are handled gracefully

## ✅ Data Preparation

### Publish Books to Website

For EACH book you want on website:

- [ ] Open book in backend
- [ ] Go to "Website" tab
- [ ] Check "Xuất bản lên Website"
- [ ] (Optional) Fill SEO fields
- [ ] Save
- [ ] Click "Xuất bản Web" button
- [ ] Verify book appears on `/thu-vien`

Recommended: Publish at least 10-20 books for testing

### Create Portal Test User

- [ ] Go to Settings > Users > Create
- [ ] Name: "Portal Test User"
- [ ] Email: test@example.com
- [ ] Access Rights: Add "Portal" group
- [ ] Save
- [ ] Send invite or set password
- [ ] Login and test

## ✅ Performance Checks

- [ ] Book listing page loads in < 3 seconds
- [ ] Search returns results in < 2 seconds
- [ ] Add to cart responds in < 1 second
- [ ] Images load progressively
- [ ] No JavaScript errors in console (F12)

## ✅ Error Handling Checks

- [ ] Try to access non-existent book: `/thu-vien/sach/99999999`
  - Should redirect or show 404
- [ ] Try to add unavailable book to cart
  - Should show error message
- [ ] Try to access other user's borrowing (as portal user)
  - Should be access denied
- [ ] Try to checkout with empty cart
  - Should show error

## ✅ Integration Checks

- [ ] Adding book to cart creates draft borrowing in backend
- [ ] Confirming cart changes borrowing state
- [ ] Availability counts are accurate
- [ ] Resource limits are respected
- [ ] Borrow locations display correctly

## 🐛 Common Issues & Solutions

### Issue: Books don't appear on website
**Solution**: Check `website_published = True` and `active = True`

### Issue: Can't add book to cart
**Solution**: 
- Check user is logged in
- Check `available_quant_count > 0`
- Check `can_borrow = True`
- Check resource limits

### Issue: Portal shows access denied
**Solution**: 
- Update module to reload security
- Check ir.rules are active
- Check user has Portal group

### Issue: Images don't load
**Solution**: 
- Check image fields have data
- Check web.base.url is configured
- Check file storage permissions

### Issue: Add to cart button doesn't work
**Solution**: 
- Check browser console for JS errors
- Check CSRF token is valid
- Check RPC endpoint is reachable

## 📝 Post-Go-Live Tasks

- [ ] Monitor error logs for first week
- [ ] Gather user feedback
- [ ] Check Google Search Console after 1 week
- [ ] Optimize based on usage patterns
- [ ] Document any custom changes

## ✅ Sign-Off

- [ ] All features tested and working
- [ ] Performance is acceptable
- [ ] Security verified
- [ ] Documentation reviewed
- [ ] Ready for production

**Tested by**: ________________
**Date**: ________________
**Approved by**: ________________
**Date**: ________________
