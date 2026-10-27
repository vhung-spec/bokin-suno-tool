# Bokin Suno Tool: ghi chú cho mỗi phiên làm việc

Đọc trước: `README.md`. Hệ thống Bokin (quy tắc chung) nằm ở repo `vhung-spec/bokin-image-to-video-loop`:
`docs/tong-quan-he-thong.md`.

## Repo
- `loi-dong-am/` trang **Lời Đồng Âm**: đổi lời tiếng Anh để dán vào Suno, hai cách: viết theo âm và thêm khoảng
  trống (tách âm tiết). Chạy hoàn toàn trên trình duyệt, mở thẳng từ ổ đĩa, không máy chủ. `engine.js` (danh sách viết
  theo âm, từ đồng âm, quy tắc chính tả, tách âm tiết, chọn từ cần đổi), `hyphen-en-us.js` (bộ quy tắc tách chữ TeX,
  giữ nguyên dòng bản quyền), `index.html` (giao diện, nạp hai file trên).
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
- Tách âm tiết phải ra đúng ví dụ của chủ (bài thử *"space" splits syllables like the owner's example*): mỗi mảnh
  có nguyên âm, từ một âm tiết không tách.
- Trang luôn nhắc: chỉ dùng cho bài đã hết bản quyền (Public Domain) hoặc lời do chính chủ viết.
- Lời người dùng dán vào là không tin cậy: trang chỉ đưa vào DOM bằng `textContent`/text node, không `innerHTML`.
- Không tạo pull request nếu chủ không yêu cầu. Kiểm chứng trên Windows và Linux (CI) trước khi báo xong.

## Bokin Suno (tải nhạc, Python)
- Hướng dẫn: `TAI-NHAC-SUNO.md`. Tách ra từ `vhung-spec/bokin-upvideo-vps` (cùng cách làm với Bokin Up Video).
- `suno/` tool dòng lệnh tải các bài trong một workspace Suno về thư mục, **không dùng API**: Chrome thật
  (patchright), mỗi tài khoản Suno một hồ sơ Chrome đăng nhập tay một lần, dữ liệu ở `data/`. `bokin_suno.py` (các
  lệnh), `web.py` (các bước trên suno.com, mọi selector và chữ trên nút trong `SEL`), `folder.py` (tên file,
  `danh-sach.csv`).
- `tests/fake_suno.py` Suno giả lập, `tests/test_suno.py` bài thử đầu-cuối với Chrome thật.
- `cai-dat-windows.bat`, `cai-dat-linux.sh` cài đặt; `suno.bat`, `suno.sh` chạy lệnh; `requirements.txt`.
- `.github/workflows/suno.yml` chạy selftest và bài thử đầu-cuối trên Windows và Linux.
- Kiểm tra nhanh: `python suno/bokin_suno.py selftest`; e2e: `python tests/test_suno.py` (Linux: `xvfb-run -a`).
  Trên Linux, thư mục tạm phải có đường dẫn ngắn (Chrome không chạy với `--user-data-dir` quá dài).
- Không commit hồ sơ Chrome, cookie, mật khẩu, email thật, ID tài khoản thật, IP. Thư mục `data/` và nhạc tải về không
  bao giờ vào git. Nhắc chủ che tên tài khoản/email trong ảnh chụp màn hình.
- Chỉ tải qua nút Download của Suno (tính lượt tải như tải tay). Không lấy file bằng đường khác để né giới hạn lượt
  tải của gói, không bao giờ bấm Buy/Upgrade; hết lượt thì dừng.
- Ảnh lỗi: cửa sổ, menu và hộp thoại đang mở, nhãn các nút; không lưu cả trang (trang chứa dữ liệu tài khoản).
- Suno giả lập phải đi cùng `SEL`: sửa selector thì sửa cả Suno giả lập và bài thử.
- Chưa thử trên suno.com thật: máy chủ phiên làm việc không vào được suno.com; sửa `SEL` theo ảnh và file `.html` chủ
  gửi.
