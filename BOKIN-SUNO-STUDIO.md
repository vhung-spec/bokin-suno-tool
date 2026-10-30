# Bokin Suno Studio: tải nhạc Suno, đổi lời, master trong một app

App Windows, mở trong một cửa sổ riêng, có bốn thẻ:

| Thẻ | Làm gì |
|---|---|
| **1. Tài khoản Suno** | Đăng nhập Suno một lần cho mỗi tài khoản (trong một cửa sổ Chrome), kiểm tra, xoá. |
| **2. Tải nhạc** | Dán link workspace, xem danh sách bài, tải về thư mục (WAV hoặc MP3). Bên dưới là **các bài đã tải**: nghe, xem lời, **Đổi lời**, **Master**. |
| **3. Đổi lời** | Trang **Lời Đồng Âm**: đổi lời tiếng Anh để dán vào Suno (viết theo âm, tách âm tiết). |
| **4. Master** | **Bokin Suno Master**: làm sạch và master bài hát. |

Một vòng làm việc: **tải bài về → xem lời → đổi lời → chép sang Suno**, và **master** bài đã tải.

> Đổi lời chỉ dùng cho bài **đã hết bản quyền** (Public Domain) hoặc lời do chính bạn viết. Đổi chữ để qua bộ lọc có
> thể trái điều khoản sử dụng của Suno.

## Cần biết trước

- **Cần Google Chrome** trên máy (app dùng Chrome thật để làm việc trên suno.com). Chưa có thì cài từ
  <https://www.google.com/chrome/>.
- **App không dùng API của Suno.** Nó mở Chrome đã đăng nhập Suno rồi bấm đúng các nút một người bấm:
  **⋯ → Download → WAV Audio → Download File**.
- **Lượt tải của gói Suno:** mỗi bài tính một lượt như khi tải bằng tay. Hết lượt thì app **dừng**, **không bao giờ
  bấm mua thêm** (Buy/Upgrade).
- **App không lưu mật khẩu.** Phiên đăng nhập Suno nằm trong hồ sơ Chrome riêng của từng tài khoản, trong thư mục
  `%APPDATA%\Bokin\SunoStudio\suno`. Không chép thư mục đó sang máy khác và không gửi nó cho ai.
- **Điều khoản của Suno không cho phép công cụ tự động.** App đi chậm như người, nhưng rủi ro tài khoản bị nhắc nhở
  hoặc khoá **vẫn có**. Nên tải vừa phải.
- **Phần Suno chưa được thử trên suno.com thật** (máy dùng để viết app không vào được suno.com). App đã được thử kỹ
  trên một trang Suno giả lập. Lần chạy đầu có thể cần sửa. Khi lỗi, app lưu ảnh màn hình và một file `.html` trong
  `%APPDATA%\Bokin\SunoStudio\suno\logs`: gửi hai file đó cho người sửa, **nhớ che tên tài khoản và email** trong ảnh.
  - Phần **lời bài hát** cũng vậy: app đọc lời đang hiện trên trang bài hát Suno. Nếu nút **Lời** của bài bị mờ
    dù bài có lời, hãy báo lại kèm ảnh trang bài hát đó.

## Cài đặt

1. Mở trang bản phát hành của app:
   <https://github.com/vhung-spec/bokin-suno-tool/releases/tag/studio-latest>
2. Ở mục **Assets**, tải file **BokinSunoStudio-Setup.exe**.
3. Bấm đúp file vừa tải để cài. **Không cần quyền quản trị.**
   - Nếu Windows hiện "Windows protected your PC": bấm **More info** → **Run anyway** (bộ cài chưa có chữ ký số).
4. Mở **Bokin Suno Studio** từ Desktop hoặc menu Start.

### Kích hoạt (lần đầu)

App dùng key **Bokin License**, chung với các app Bokin khác. Sản phẩm: **Bokin Suno Studio** (`suno-studio`).

1. Lần đầu mở, app hiện **Mã máy**. Bấm **Chép mã máy**.
2. Trong **Key Center**, cấp key cho mã máy đó với sản phẩm **Bokin Suno Studio**.
3. Dán key vào ô **Key** rồi bấm **Kích hoạt**.

Key của Bokin Suno Master không mở được Bokin Suno Studio (và ngược lại), trừ key gói có cả hai.

### Tự cập nhật

- App tự kiểm tra bản mới khi mở, rồi 5 phút một lần, và tự tải về ở chế độ nền.
- Có bản mới thì góc trên hiện nút **Có bản mới … · Cập nhật ngay**. Bấm vào là app tắt, cài bản mới rồi tự mở lại.
  Không bấm thì bản mới được cài khi bạn đóng app.
- Đang tải nhạc hoặc đang master thì app chờ xong mới cài.
- Bokin Suno Master (app riêng) vẫn tự cập nhật như cũ, hai app không lẫn bản của nhau.

## Bước 1: thêm tài khoản Suno (mỗi tài khoản một lần)

1. Mở thẻ **1. Tài khoản Suno**.
2. Gõ một **tên ngắn** cho tài khoản: chữ không dấu, số, `-` hoặc `_`. Ví dụ `suno1`.
3. Bấm **Đăng nhập**. Một cửa sổ Chrome mở trang suno.com:
   1. Bấm **Sign In**, đăng nhập như mọi khi (Google…), làm cả bước xác minh nếu được hỏi.
   2. Khi đã vào Suno (thấy ảnh đại diện của bạn), **đóng cửa sổ Chrome đó**.
4. App báo **Đã lưu tài khoản suno1** và tài khoản hiện trong bảng.

- **Kiểm tra đăng nhập:** xem các tài khoản còn đăng nhập không. Bị đăng xuất thì bấm **Đăng nhập lại**.
- **Xoá:** xoá tài khoản và hồ sơ Chrome của nó khỏi máy này.

## Bước 2: tải nhạc

1. Trên Chrome thường của bạn, mở **workspace** muốn tải, chép link trên thanh địa chỉ (dạng
   `https://suno.com/create?wid=...`). Link một **playlist** hoặc **một bài** cũng được.
2. Mở thẻ **2. Tải nhạc**:
   1. Chọn **Tài khoản Suno**.
   2. Dán link vào ô **Link** (nhiều workspace: mỗi link một dòng).
   3. **Thư mục lưu nhạc:** bấm **Chọn…** để chọn thư mục. Mặc định là `Nhạc\Bokin Suno Studio\Nhac Suno`.
      Mỗi workspace nên tải vào một thư mục riêng.
   4. **Định dạng:** WAV (nên dùng, để master) hoặc MP3.
3. Bấm **Xem danh sách bài** để xem workspace có những bài nào (chưa tải gì).
4. **Lần đầu, tải thử 2 bài:** ghi `2` vào ô **Tối đa**, bấm **Tải về**. Nghe thử. Đúng rồi thì xoá số trong ô
   **Tối đa** và bấm **Tải về** lần nữa để tải hết.

- Trong lúc tải, app hiện tiến độ từng bài và nhật ký. **Đừng bấm vào cửa sổ Chrome** app mở ra.
- Nút **Dừng**: app dừng sau bài đang tải. Lần sau bấm **Tải về** là tải tiếp các bài còn thiếu.
- **Chạy lại thì chỉ tải bài mới.** Bài lỗi (ví dụ bài Suno đang tạo dở) được thử lại ở lần sau.
- Ô **Đọc hết danh sách**: chỉ cần khi bạn chuyển bài **cũ** vào workspace (chúng nằm tít bên dưới danh sách).
- Trong thư mục nhạc có file **danh-sach.csv** (mở bằng Excel): mỗi bài một dòng. **Đóng file này trong Excel** trước
  khi tải.

## Bước 3: xem lời, đổi lời, chép sang Suno

Bảng **Bài đã tải trong thư mục này** (thẻ Tải nhạc) liệt kê các bài trong thư mục đang chọn:

- **Nghe:** phát bài ngay trong app.
- **Lời:** hiện lời bài hát (Suno hiện sao thì lưu vậy). Nút mờ nghĩa là bài không có lời (nhạc không lời).
  **Chép lời gốc:** chép lời vào bộ nhớ tạm.
- **Đổi lời:** mở thẻ **3. Đổi lời** với lời của bài đó. Trong đó:
  1. Chọn **Cách đổi** (Viết theo âm / Thêm khoảng trống / Cả hai) và **Mức đổi** (nên thử **Vừa** trước).
  2. Bấm vào một từ màu đỏ để chọn cách viết khác.
  3. Bấm **Chép lời**, rồi dán vào ô Lyrics ở chế độ Custom của Suno.
  4. Suno vẫn báo bản quyền: chọn **Mạnh**, đổi sang **Cả hai** hoặc bấm **Tạo bản khác**, rồi thử lại.

Cách dùng Lời Đồng Âm đầy đủ: phần **Lời Đồng Âm** trong [README.md](README.md).

## Bước 4: master

- Ở bảng bài đã tải: chọn **Kiểu master** (ví dụ **Nghe trực tuyến**, **Jazz**), rồi bấm **Master** ở bài muốn
  master. Bài được gửi sang thẻ **4. Master** và bắt đầu xử lý.
- Hoặc mở thẻ **4. Master**, kéo thả file nhạc vào, chỉnh các tuỳ chọn, bấm **Master**.
- Kết quả nằm trong `Nhạc\Bokin Suno Studio\Master`, mỗi bài một thư mục con (nút **Mở thư mục Master**).

Các kiểu master và tuỳ chỉnh: phần **Bokin Suno Master** trong [README.md](README.md).

## Khi có lỗi

| Báo lỗi | Cách xử lý |
|---|---|
| Máy này chưa có Google Chrome | Cài Chrome từ google.com/chrome, mở lại app |
| Tài khoản Suno chưa đăng nhập hoặc đã bị đăng xuất | Thẻ Tài khoản Suno → **Đăng nhập lại** |
| Chrome đang đăng nhập một tài khoản Suno khác | **Đăng nhập lại**, đăng nhập đúng tài khoản |
| Không phải link của Suno / Không thấy bài nào ở link này | Chép lại link trên thanh địa chỉ, thử mở link đó trong Chrome thường |
| Suno báo hết lượt tải của gói | Chờ sang tháng mới của gói, rồi tải lại |
| 3 bài liền nhau không tải được | Có thể Suno đã đổi giao diện: gửi ảnh và file `.html` trong `%APPDATA%\Bokin\SunoStudio\suno\logs` (che tên tài khoản) |
| Không ghi được danh-sach.csv | Đóng file đó trong Excel rồi tải lại |
| Hồ sơ Chrome đang mở ở cửa sổ khác | Đóng cửa sổ Chrome của app, chờ việc đang chạy xong |

- Nhật ký của app: `%APPDATA%\Bokin\SunoStudio\app.log`; của phần tải nhạc: `%APPDATA%\Bokin\SunoStudio\suno\logs\suno.log`.
- Gỡ app (Settings → Apps) **không xoá** nhạc đã tải, bài đã master, hay tài khoản Suno đã đăng nhập.

## Cho người phát triển

```
bokin_studio/desktop.py      cửa sổ app, một bản mỗi người dùng, --close, --selftest, "suno ..." (dòng lệnh tải nhạc)
bokin_studio/app.py          máy chủ cục bộ (127.0.0.1, mã bảo vệ mỗi lần mở) và API
bokin_studio/suno_tasks.py   chạy suno/bokin_suno.py cho từng việc, đọc tiến độ, nút Dừng
bokin_studio/library.py      bài đã tải trong một thư mục (danh-sach.csv) và lời của chúng
bokin_studio/static/         trang của app (4 thẻ); thẻ 3 và 4 là loi-dong-am/ và bokin_suno/static/ trong khung
bokin_studio/updater.py      tự cập nhật từ bản phát hành studio-latest (không phải "Latest")
bokin_studio/licensing.py    Bokin License, sản phẩm suno-studio (bit 8)
packaging/BokinSunoStudio.*  PyInstaller và Inno Setup
.github/workflows/bokin-suno-studio.yml   dựng, thử, cài thật, cập nhật thật trên Windows, rồi phát hành
```

- Chạy từ mã nguồn: `pip install -e ".[studio,dev]"`, rồi `python -m bokin_studio` (app) hoặc
  `python -m bokin_studio suno ...` (dòng lệnh tải nhạc).
- Bài thử: `python -m pytest -q` (cả bài thử đầu-cuối trong Chrome với Suno giả lập, `tests/studio/test_e2e.py`;
  Linux không có màn hình: `xvfb-run -a`; không có Google Chrome: `BOKIN_STUDIO_CHROME=<đường dẫn Chrome/Chromium>`).
- **Bản phát hành:** cùng repo với Bokin Suno Master, nhưng **không bao giờ là "Latest"** (app master tự cập nhật từ
  "Latest"). Mỗi bản: tag `studio-v<phiên bản>` tạo với `--latest=false`; bản phát hành `studio-latest` (cũng không
  phải Latest) giữ `bokin-suno-studio-latest.json` và `BokinSunoStudio-Setup.exe`. Workflow kiểm tra lại "Latest" sau
  khi phát hành.
