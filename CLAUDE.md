# Bokin Suno Tool: ghi chú cho mỗi phiên làm việc

Đọc trước: `README.md`. Hệ thống Bokin (quy tắc chung) nằm ở repo `vhung-spec/bokin-image-to-video-loop`:
`docs/tong-quan-he-thong.md`.

## Repo
- `loi-dong-am/` trang **Lời Đồng Âm**: viết lại lời tiếng Anh theo cách đọc để dán vào Suno. Chạy hoàn toàn trên
  trình duyệt, mở thẳng từ ổ đĩa, không máy chủ. `engine.js` (danh sách viết theo âm, từ đồng âm, quy tắc chính tả,
  chọn từ cần đổi), `index.html` (giao diện, nạp `engine.js`).
- `tests/engine.test.js` bài thử bộ đổi chữ (Node), `tests/page.test.js` bài thử trang trong Chromium (Playwright).
- `tools/build-artifact.js` gộp trang thành `dist/loi-dong-am.html` để đăng lên Claude. Bản đang đăng:
  https://claude.ai/artifact/EQoBSTcU3A4SiS4ygvMUfC (sửa trang thì build lại rồi đăng vào đúng link này).
- `.github/workflows/test.yml` chạy bài thử trên Windows và Linux.
- Nhánh chính: `main`.
- Kiểm tra nhanh: `npm test`; trang: `npm run test:page`.

## Quy tắc
- Trả lời chủ dự án bằng **tiếng Việt**, đơn giản, từng bước. Mã và chú thích trong mã bằng tiếng Anh.
- Mỗi cách viết lại phải được hát **y như từ gốc**. Thêm từ hoặc quy tắc thì chạy quy tắc trên vài nghìn từ thông dụng,
  xem kết quả, đưa từ bị đọc sai vào `NO_RULES` và vào bài thử "never offers a spelling that is sung differently".
- Trang luôn nhắc: chỉ dùng cho bài đã hết bản quyền (Public Domain) hoặc lời do chính chủ viết.
- Lời người dùng dán vào là không tin cậy: trang chỉ đưa vào DOM bằng `textContent`/text node, không `innerHTML`.
- Không tạo pull request nếu chủ không yêu cầu. Kiểm chứng trên Windows và Linux (CI) trước khi báo xong.
