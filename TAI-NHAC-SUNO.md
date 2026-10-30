# Bokin Suno: tải nhạc đã làm trên Suno về máy

Tool tải **các bài nhạc trong một workspace Suno** về một thư mục trên máy, dạng **WAV** (hoặc MP3). Chạy lại thì
chỉ tải các bài mới. Tool chạy trên **Windows** hoặc **Linux** (máy tính hoặc VPS).

Tool **không dùng API**. Nó mở một Chrome thật đã đăng nhập Suno rồi làm đúng các bước một người làm: mở workspace,
rồi với từng bài bấm **⋯ → Download**, trong hộp *Download 'tên bài'* chọn **WAV**, bỏ chọn MP3 (Suno chọn sẵn
MP3 và cho chọn nhiều dòng một lúc), rồi bấm **Unlock & Download** (giao diện Suno từ tháng 10/2026; cách cũ ⋯ →
Download → WAV Audio → Download File vẫn chạy).
- Hộp Download ghi số lượt tải còn lại của gói (*Downloads 59*). Khi hộp ghi **Downloads 0**, tool dừng, không bấm gì.

## Cần biết trước

- **Mỗi tài khoản Suno đăng nhập bằng tay một lần**, ngay trên máy chạy tool. Tool **không lưu mật khẩu**. Phiên
  đăng nhập nằm trong hồ sơ Chrome riêng của tài khoản (`data/profiles/<tên>`).
  - Không chép thư mục `data` sang máy khác và không gửi nó cho ai: ai có nó là vào được tài khoản Suno.
- **Lượt tải của gói Suno.** Từ 3/9/2026 Suno giới hạn số bài tải mỗi tháng theo gói (gói Pro 20 bài, Premier 60
  bài; gói cao nhất không giới hạn). Tool tải qua **đúng nút Download của Suno**, nên mỗi bài được tính như khi tải
  bằng tay:
  - Một bài tính **1 lượt**, dù tải WAV hay MP3. Tải lại bài đã tải không tính thêm.
  - Khi Suno báo hết lượt, tool **dừng lại**. Tool **không bao giờ bấm mua thêm**.
- **Điều khoản của Suno không cho phép dùng công cụ tự động** trên trang. Tool đi chậm như người (mỗi bài vài
  giây). Dù vậy, rủi ro tài khoản bị nhắc nhở hoặc khoá **vẫn có**. Nên tải vừa phải.
- **Tool đã được thử trên suno.com thật** (30/10/2026: xem danh sách và tải WAV). Suno đổi giao diện thì tool có thể
  cần sửa lại.
  - Khi gặp lỗi, tool chụp màn hình và lưu một file `.html` trong `data/logs`.
  - Gửi hai file đó cho người sửa tool. Trước khi gửi, **che tên tài khoản và email** trong ảnh.
  - Khi Suno đổi giao diện, tool báo lỗi và chụp màn hình, không làm gì sai trên tài khoản.

## Cài đặt trên Windows

1. Cài **Python 3.10 trở lên** từ <https://www.python.org/downloads/>. Khi cài, tick **Add python.exe to PATH**.
2. Tải repo này về máy (nút **Code → Download ZIP** trên GitHub), giải nén ra một thư mục, ví dụ `C:\BokinSuno`.
3. Bấm đúp **`cai-dat-windows.bat`**. Nó cài các thư viện cần thiết, cài Google Chrome nếu máy chưa có, rồi tự kiểm
   tra. Cuối cùng phải hiện `selftest OK` và `Xong`.

Bản mới của tool: tải ZIP mới, chép đè lên thư mục cũ (thư mục `data` và nhạc đã tải vẫn giữ nguyên), rồi bấm đúp
`cai-dat-windows.bat` một lần nữa.

## Cài đặt trên Linux (Ubuntu/Debian)

1. Chép repo vào máy, ví dụ bằng `git clone`.
2. Trong thư mục repo, chạy:
   ```
   bash cai-dat-linux.sh
   ```
   Nó cài Python venv, thư viện, Google Chrome và màn hình ảo (`xvfb`), rồi tự kiểm tra.
3. **Đăng nhập Suno cần màn hình thật**. Cài màn hình từ xa cho VPS một lần, rồi vào bằng **Remote Desktop** (có sẵn
   trên Windows):
   ```
   sudo apt install -y xfce4 xrdp
   echo xfce4-session > ~/.xsession
   sudo systemctl restart xrdp
   ```
   Nên dùng một tài khoản Linux thường, không dùng `root`.
   - Lệnh `login`: chạy trong Remote Desktop.
   - Các lệnh khác: chạy qua SSH cũng được. `suno.sh` tự tạo màn hình ảo cho Chrome.

## Dùng tool

Các lệnh bên dưới gõ trong cửa sổ dòng lệnh mở **trong thư mục của tool** (trong File Explorer: gõ `cmd` vào thanh địa
chỉ rồi Enter). Trên Windows, lệnh bắt đầu bằng **`suno`**. Trên Linux, dùng **`./suno.sh`** thay cho `suno`.

## Bước 1: đăng nhập Suno (mỗi tài khoản một lần)

Đặt cho tài khoản một **tên ngắn**: chữ không dấu, số, `-` hoặc `_`. Ví dụ `suno1`.

```
suno login suno1
```

Một cửa sổ Chrome mở trang suno.com:

1. Bấm **Sign In**, đăng nhập như mọi khi (Google…), làm cả bước xác minh nếu được hỏi.
2. Khi đã vào Suno (thấy ảnh đại diện của bạn), **đóng cửa sổ Chrome**.

Tool báo `Đã lưu tài khoản suno1`.

- `suno accounts`: xem các tài khoản đã đăng nhập.
- `suno check`: kiểm tra các tài khoản còn đăng nhập không. Bị đăng xuất thì chạy lại `suno login <tên>`.
- `suno remove <tên>`: xoá tài khoản khỏi máy này.

Trên Linux (VPS), lệnh `login` phải chạy trong **Remote Desktop**, xem *Cài đặt trên Linux*.

## Bước 2: lấy link của workspace

1. Mở Suno bằng Chrome thường của bạn, mở **workspace** muốn tải.
2. Bấm vào thanh địa chỉ, **Ctrl+C** để chép link. Link có dạng `https://suno.com/create?wid=...`.
3. Thử dán link đó vào một tab mới: phải mở ra **đúng workspace** với đúng các bài. Nếu không, tool cũng không thấy.

Dùng link một **playlist** hoặc link **một bài** cũng được. Link chia sẻ (`suno.com/s/...`) là link của một bài:
tool chỉ tải đúng bài đó. Bài của **người khác** (trang bài có nút Follow) tool luôn bỏ qua, không bấm tải, và ghi
`nguoi_khac` vào `danh-sach.csv`.

## Bước 3: xem trước, rồi tải

Xem workspace có những bài nào (chưa tải gì):

```
suno list suno1 "https://suno.com/create?wid=..."
```

Lần đầu, **tải thử 2 bài**:

```
suno download suno1 "https://suno.com/create?wid=..." --out "D:\Nhac\Suno" --limit 2
```

Mở thư mục `D:\Nhac\Suno`, nghe thử. Đúng rồi thì tải hết (bỏ `--limit 2`):

```
suno download suno1 "https://suno.com/create?wid=..." --out "D:\Nhac\Suno"
```

- Link luôn để trong **ngoặc kép**.
- **Nhiều workspace một lần**: ghi nhiều link liền nhau, cách nhau một dấu cách. Tool chỉ mở Chrome một lần, bài nào có
  ở hai workspace thì chỉ tải một lần:
  ```
  suno download suno1 "LINK-WORKSPACE-1" "LINK-WORKSPACE-2" --out "D:\Nhac\Suno"
  ```
- `--out`: thư mục lưu nhạc. Bỏ trống thì lưu vào thư mục `nhac-suno` cạnh tool.
- Mặc định tải **WAV**. Muốn MP3: thêm `--format mp3`.
- Tên file là tên bài: `Mưa đêm.wav`. Suno tạo bài theo cặp cùng tên, nên bài thứ hai là `Mưa đêm (2).wav`.
- Mỗi bài xong, tool báo còn bao nhiêu bài và **khoảng bao lâu nữa** thì xong. Cuối cùng nó báo tổng dung lượng đã tải.
- Bài lỗi được **thử lại ngay một lần**. Vẫn lỗi (ví dụ bài đang tạo dở trên Suno) thì tool bỏ qua, ghi lý do vào
  `danh-sach.csv`, và **lần chạy sau tự thử lại**.
- Trước khi tải, tool xem ổ đĩa còn đủ chỗ không (mỗi bài WAV khoảng 60 MB). Ổ đầy giữa chừng thì tool dừng và báo.
- Nhạc tải về dùng thẳng trong **Bokin Studio Music** (thêm cả thư mục vào danh sách nhạc).

### Stems & MIDI (tuỳ chọn)

```
suno stems suno1 "https://suno.com/song/..." --out "D:\Nhac\Suno"
suno download suno1 "https://suno.com/create?wid=..." --out "D:\Nhac\Suno" --stems
```

- `stems`: tải Stems & MIDI của các bài ở link (link một bài, workspace hoặc playlist) vào thư mục con
  **"Tên bài - stems"** (`WAV`, `MP3`, `MIDI`). `download ... --stems`: tải bài xong thì tải tiếp stems của chúng.
- Bài chưa tách stems trên Suno: tool bấm **Extract** (Auto split), **có thể tốn credit Suno**. Thêm `--no-extract`
  để bỏ qua các bài đó. Hết credit thì tool dừng, không mua thêm.
- `--files wav,mp3,midi` (mặc định cả ba), `--tempo follow|fixed` (tempo của MIDI, mặc định `follow`).
- Trong `danh-sach.csv`, stems của một bài là một dòng `dinh_dang` = `stems`. Bài đã tải stems thì không tải lại.

### File danh-sach.csv

Trong thư mục nhạc có file **`danh-sach.csv`** (mở bằng Excel): mỗi bài một dòng, gồm tên bài, tên file, trạng thái
(`xong` hoặc `loi`), lý do lỗi, link bài trên Suno và lúc tải.

- **Chạy lại cùng lệnh thì chỉ tải bài mới**, và thử lại các bài `loi`. Bài `xong` không tải lại, **kể cả khi bạn đã
  xoá file nhạc**.
- **Lần chạy sau nhanh hơn**: Suno xếp bài mới nhất lên đầu, nên tool chỉ đọc phần đầu danh sách của workspace, tới
  khi gặp 50 bài liền đã tải thì thôi. Nếu bạn chuyển bài **cũ** vào workspace (chúng nằm tít bên dưới), thêm
  `--full` để tool đọc hết danh sách.
- Muốn tải lại một bài: xoá dòng của bài đó trong `danh-sach.csv`, lưu lại dạng **CSV UTF-8**, rồi chạy lại.
- **Đóng `danh-sach.csv` trong Excel** trước khi chạy tool.
- Mỗi workspace nên tải vào một thư mục riêng cho dễ tìm. Chung một thư mục cũng không sao.

## Tự tải bài mới mỗi ngày (tuỳ chọn)

Trên Windows:

1. Tạo file `tai-nhac-suno.bat` (bằng Notepad) với nội dung như sau, sửa đường dẫn và link cho đúng:
   ```
   @echo off
   cd /d C:\BokinSuno
   call suno.bat download suno1 "https://suno.com/create?wid=..." --out "D:\Nhac\Suno"
   ```
2. Mở **Task Scheduler** → **Create Basic Task** → đặt tên → **Daily** → chọn giờ → **Start a program** → chọn file
   `tai-nhac-suno.bat` → **Finish**.
3. Lúc đến giờ, máy phải đang bật và đã đăng nhập Windows.

Trên Linux: thêm lệnh `./suno.sh download ...` vào `crontab -e` (tool tự tạo màn hình ảo cho Chrome).

## Khi có lỗi

- Mỗi lỗi có một dòng giải thích bằng tiếng Việt.
- Nhật ký đầy đủ: `data/logs/suno.log`.
- Lỗi trên trang Suno có kèm ảnh `data/logs/loi-<thời gian>-<tài khoản>.png` và file `.html` cùng tên.
- Chạy kèm `--headless` để Chrome không hiện cửa sổ. Mặc định cửa sổ có hiện để xem tool đang làm gì; đừng bấm vào
  cửa sổ đó khi tool đang chạy.

| Báo lỗi | Cách xử lý |
|---|---|
| Tài khoản Suno chưa đăng nhập hoặc đã bị đăng xuất | `suno login <tên>` |
| Chrome đang đăng nhập một tài khoản Suno khác | `suno login <tên>`, đăng nhập đúng tài khoản |
| Không phải link của Suno | Chép lại link trên thanh địa chỉ, xem *Bước 2* |
| Không thấy bài nào ở link này | Dán link vào Chrome thường xem có mở đúng workspace không |
| Suno chưa cho tải bài này | Bài chưa tạo xong hoặc lỗi trên Suno; lần chạy sau tool thử lại |
| Ổ đĩa đầy / ổ đĩa gần đầy | Xoá bớt file, hoặc chọn thư mục ở ổ khác bằng `--out` |
| Cửa sổ Chrome của tool đã bị đóng | Chạy lại lệnh: tool tải tiếp từ bài còn thiếu |
| Suno báo hết lượt tải của gói | Chờ sang tháng mới của gói (hoặc tự mua thêm lượt trên Suno), rồi chạy lại |
| 3 bài liền nhau không tải được | Có thể Suno đã đổi giao diện: gửi ảnh và file `.html` trong `data/logs` |
| Không ghi được danh-sach.csv | Đóng file đó trong Excel rồi chạy lại |
| Hồ sơ Chrome đang mở ở cửa sổ khác | Đóng cửa sổ Chrome của tool (hoặc chờ lần chạy kia xong) |

## Cho người phát triển

- Mã nguồn:
  - `suno/bokin_suno.py`: các lệnh.
  - `suno/web.py`: các bước trên suno.com. Mọi selector và chữ trên nút nằm trong `SEL`.
  - `suno/folder.py`: thư mục nhạc, tên file, `danh-sach.csv`.
- Tự kiểm tra: `python suno/bokin_suno.py selftest`.
- Thử đầu-cuối với **Suno giả lập** (`tests/fake_suno.py`) bằng Chrome thật:
  - `python tests/test_suno.py [--headless]`
  - Linux không có màn hình: `xvfb-run -a python tests/test_suno.py`
- GitHub Actions (`.github/workflows/suno.yml`) chạy cả hai bài thử trên Windows và Linux mỗi lần push.
- Suno giả lập không phải Suno thật. Khi Suno đổi giao diện, sửa `SEL` trong `web.py` theo ảnh chụp và file `.html`
  trong `data/logs`, rồi sửa Suno giả lập cho giống.
