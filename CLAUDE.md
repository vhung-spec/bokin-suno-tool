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
- Máy chủ phiên làm việc trên cloud không vào được suno.com. Thử trên suno.com thật phải chạy trên máy Windows của chủ
  (hồ sơ Chrome đã đăng nhập của app: `--data "%APPDATA%\Bokin\SunoStudio\suno"`, app phải tắt). Đã thử như vậy
  ngày 30/10/2026: `list`, `download` WAV chạy đúng.
- suno.com thật (30/10/2026): menu ⋯ (nút `More options`, `role=menu`, các `div role=menuitem`): Remix, Edit,
  Publish, Share, Download, Manage, Add to Queue, Add to Playlist, Song Radio, Report, Move to Trash. Download mở hộp
  `role=dialog` "Download 'tên bài'": các dòng M4A, MP3, WAV, MP4 video asset là `<button>` **không có aria-***;
  dòng đang chọn chỉ có dấu ✓ (một `svg`). **Chọn được nhiều dòng một lúc** (MP3 chọn sẵn; bấm một dòng là chọn/bỏ
  chọn), dòng Stems & MIDI có nút Manage. Nút "Unlock & Download" ("Plan Premier · Downloads 59 · Refreshes
  11/28/26"), hoặc "Download" và "You've unlocked this song..." với bài đã tải. Tool chọn WAV, bỏ chọn mọi dòng
  khác, rồi bấm nút đó; "Downloads 0" thì dừng, không bấm. Trên ảnh bìa có nút "Download cover image": không bấm.
- Trang Create (`suno.com/create`, có thể có `?wid=`): danh sách bài là khung cuộn (`clip-browser-list-scroller`)
  chia trang bằng nút Previous page / Next page; **Next page vẫn bật ở trang cuối** và bấm không đổi gì: tool dừng
  khi bấm Next page mà danh sách không đổi (sau `NEXT_PAGE_QUIET` giây trang không tải gì, tối đa `NEXT_PAGE_WAIT`).
- Đọc danh sách (`web.list_songs`, rà soát 01/11/2026; trang playlist thật **chưa thử**): khung danh sách chọn lại mỗi
  lượt (khung nhiều link hơn thì thay, bỏ bài đọc từ khung cũ); hết danh sách khi ở cuối mà `LIST_END_QUIET` giây
  không có gì mới và trang không chờ gì (`_Net`), tối đa `LIST_END_MAX`; dòng trong tầm nhìn chưa có link thì đứng chờ
  (`HOLD_SECONDS`); đọc lại từ đầu tới khi không thêm bài (`SWEEPS`). Dừng sớm khi gặp 50 bài liền đã tải chỉ cho
  workspace (`web.newest_first`) và khi lần trước tải hết (`chua-xong.json` trong `data/`). Bài lỗi lần trước thử
  sau cùng và không tính vào `STUCK_IN_A_ROW`.
- Mọi lần đọc phần tử / bấm trong lúc tải một bài có hạn ngắn (`READ_MS`, `_press`), không đợi 30 giây mặc định của
  Playwright: lỗi `TimeoutError: Timeout 30000ms` của chủ (01/11/2026) là hộp Download mở chậm hơn 5 giây rồi bị
  bấm ⋯ đè lên; nay chờ hộp `BOX_WAIT_MS` và dùng hộp đã mở; ⋯ bấm lại tới `MENU_TRIES` lần (trang bài chậm). Tab mở file .wav của bài trước không bao giờ bị lấy cho
  bài sau (`Catcher.reset`). Nút Download của hộp bấm một lần cho mỗi bài, kể cả khi nó đổi tên thành "Download" (lại sau 60 giây không có file). Hộp khác (không phải hộp Download)
  đòi mua chỉ dừng lượt tải khi còn đó sau `OTHER_BOX_SECONDS`.
- Bài của tài khoản khác: bỏ qua (`not_mine`, ghi `nguoi_khac`, lần chạy sau xem lại), trừ khi `--others` (ô tick
  "Tải cả bài của tài khoản khác" trong Studio, chủ chọn 01/11/2026). Nhận ra theo menu ⋯ đang mở: có Publish / Move
  to Trash (`text_owner_item`) là bài của mình; chỉ khi không có mà cạnh tên bài có nút Follow mới là bài người khác
  (playlist của chủ 01/11/2026: bài của chính chủ cũng có nút Follow cạnh tên, Suno giả lập `follow_on_own`). Link
  chia sẻ `suno.com/s/...` dẫn tới một bài; trang bài có cột Similar (bài người khác): không bao giờ đọc làm danh
  sách. Suno giả lập có cả hai giao diện (`download_ui` "box"/"menu"), hộp chọn nhiều dòng như thật, và
  `paging` "pages" như trang Create.
- Stems & MIDI (`web.download_stems`, lệnh `stems`, `download --stems`; theo 3 ảnh chủ gửi 30/10/2026, **chưa thử trên
  suno.com thật**): hộp Download → Stems & MIDI · Manage → hộp "Extract Stems and MIDI" (Auto split / Split from mix /
  Advanced split, nút Extract, các stem đã tách mỗi cái có biểu tượng Download riêng: không bấm, nút "Download ▾" cuối
  hộp) → hộp "Download · Auto split · 6 stems" (ô MP3, WAV, MIDI; Tempo behavior Fixed / Follow tempo changes; Cancel /
  Download) → một file zip, giải nén an toàn (`folder.unpack`) vào "Tên bài - stems". Chủ chọn (30/10/2026): bài chưa
  tách thì bấm Extract (có thể tốn credit), tải WAV + MP3 + MIDI, Follow tempo changes; hết credit / Upgrade thì dừng.
  Extract chỉ bấm khi hộp đã hiện xong (ít nhất `SETTLE_SECONDS`, rồi tới khi trang hết chờ trả lời `NET_QUIET`, tính từ
  lúc bấm Manage; quá `SETTLE_MAX` mà trang vẫn tải thì không bấm) mà không có stems nào (đã tách, đang tách, nút
  Download), và
  **mỗi bài một lần** (`data/stems-extract.json`, lớp `Extracted`); hộp xác nhận chỉ bấm một lần, nhận ra theo dấu
  `data-bokin-box`/`data-bokin-seen` chứ không theo chữ. Downloads 0 thì dừng trước Manage. Giải nén vào thư mục ẩn, đủ
  WAV/MP3/MIDI đã chọn mới đổi tên thành thư mục stems. Ô tick MP3/WAV/MIDI: theo aria nếu có, không thì bấm thử và
  xem dấu ✓ (svg) thêm hay bớt (`JS_MARKS`). Dừng (`BOKIN_SUNO_STOP`) có hiệu lực cả khi đang chờ Suno tách. Suno giả
  lập có đủ các hộp này (`stems`, `credits`, `credits_ui`, `extract_confirm`, `stems_aria`, `stems_load_ms`,
  `extract_silent`, `confirm_close_ms`, `stems_drop`, `files_start`, `files_square`; hộp Download biến mất khỏi DOM
  sau Manage).
- Lời bài hát: tải xong một bài, tool lưu lời đang hiện trên trang bài hát vào `Tên bài.txt` cạnh file nhạc
  (`web.JS_LYRICS`, `SEL["lyrics"]`; chưa thử trên suno.com thật). Một tên file (bỏ đuôi) thuộc về một bài.
- Máy chủ phiên làm việc chỉ có Chromium của Playwright, không có Google Chrome: ở đó `tests/test_suno.py` hỏng từ
  lần tải thứ hai (Chromium đóng trang khi mở lại hồ sơ đã tải file), cả trên `main`. CI dùng Chrome thật.

## Bokin Suno Studio (app Windows gộp ba công cụ)
- Hướng dẫn: `BOKIN-SUNO-STUDIO.md`. Nhánh `claude/bokin-suno-studio` (đã gộp nhánh của Bokin Suno Master
  `claude/suno-ai-mastering-tool-rfg0o5`; gói `bokin_suno/` dùng chung, chỉ sửa ở đây những gì ghi dưới "Thẻ Master").
- Gói `bokin_studio/` (tên khác `bokin_suno` của app master): làm theo mẫu app master (FastAPI 127.0.0.1, mã bảo vệ
  mỗi lần mở, cửa sổ Edge/Chrome dạng app, một bản mỗi người dùng). Bốn thẻ: Tài khoản Suno, Tải nhạc (chạy
  `suno/bokin_suno.py` thành chương trình riêng: `BokinSunoStudio.exe suno ...`), Đổi lời (`loi-dong-am/` trong
  khung, không sửa), Master (trang của app master trong khung, cùng API `/api/jobs`...).
- Thẻ Master (31/10/2026, chủ yêu cầu): mỗi kết quả ghi **Kiểu master** (`master.style_of`, lưu trong `settings.json`
  của bài, "(đã chỉnh)" khi thanh trượt lệch kiểu đã chọn), tên file `Tên bài_master_<kiểu>.wav`, và trình nghe so
  sánh như trang Bokin Suno Master trên claude.ai (artifact Sj29KnjpWFXuMTdhC4qfHR): một nút phát, Gốc / Đã master /
  Phần đã khử chuyển tại chỗ (các file phát cùng lúc, bản không nghe bị tắt tiếng), dạng sóng `/api/peaks/...`, nghe
  cùng độ to. Phần này sửa trong `bokin_suno/` (trang, `app.py`, `master.py`) trên nhánh Studio: app Bokin Suno Master
  (nhánh của nó) chưa có, chủ muốn thì chép commit đó sang.
- Bokin License: sản phẩm `suno-studio`, bit 8 (đã thêm vào `vhung-spec/Bokin-License`, `bokin_license/` chép lại).
- **Không làm hỏng tự cập nhật của app master:** app master đọc bản phát hành "Latest" của repo này. Bản phát hành
  của Studio luôn `--latest=false`: tag `studio-v<phiên bản>`, và bản `studio-latest` giữ
  `bokin-suno-studio-latest.json` (Studio đọc ở đó) cùng `BokinSunoStudio-Setup.exe`. Workflow
  `.github/workflows/bokin-suno-studio.yml` kiểm tra lại "Latest" sau khi phát hành.
- Kiểm tra: `python -m pytest -q` (cả `tests/studio/test_e2e.py`: trang thật trong Chrome với Suno giả lập; không có
  Chrome thì đặt `BOKIN_STUDIO_CHROME`); `python -m bokin_studio --selftest`.
