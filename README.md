# Bokin Suno Tool

Công cụ hỗ trợ làm cover trên Suno AI.

## Bokin Suno Studio: một app cho cả ba việc

**Bokin Suno Studio** là app Windows gộp ba công cụ dưới đây vào một cửa sổ:

1. **Tải nhạc** từ một workspace Suno về máy, kèm **lời bài hát** (file `.txt` cạnh file nhạc).
2. **Đổi lời** tiếng Anh để dán vào Suno (Lời Đồng Âm): bấm **Đổi lời** ở một bài vừa tải là lời đó được đưa sang.
3. **Master** bài hát (Bokin Suno Master): bấm **Master** ở một bài vừa tải.

Cài đặt và cách dùng: [BOKIN-SUNO-STUDIO.md](BOKIN-SUNO-STUDIO.md).

Ba công cụ vẫn dùng riêng được như trước: Lời Đồng Âm (trang web), Bokin Suno (dòng lệnh), Bokin Suno Master (app).

## Lời Đồng Âm

Đổi lời bài hát **tiếng Anh** để Suno vẫn hát như cũ, nhưng chữ không còn trùng nguyên văn với bản lời có sẵn trên
mạng, nên bộ lọc lời bài hát của Suno khó nhận ra. Có hai cách, dùng riêng hoặc cùng lúc:

- **Viết theo âm:** đổi chính tả mà giữ cách đọc.
- **Thêm khoảng trống:** tách các từ nhiều âm tiết bằng khoảng trống, dấu gạch nối giữa hai từ cũng thành khoảng
  trống (one-horse → one horse).

| Lời gốc | Lời cho Suno | Cách đổi, mức đổi |
| --- | --- | --- |
| How precious did that grace appear | How **preshus** did that **grayce** appear | Viết theo âm, Vừa |
| Silent night, holy night | **Sylent knight**, **wholly knight** | Viết theo âm, Mạnh |
| In a one-horse open sleigh | In a one horse **o pen** sleigh | Thêm khoảng trống, Mạnh |
| A sleighing song tonight! | A **sleigh ing** song **to night**! | Thêm khoảng trống, Mạnh |

> Chỉ dùng cho bài **đã hết bản quyền** (Public Domain) hoặc lời do chính bạn viết. Đổi chữ để qua bộ lọc có thể
> trái điều khoản sử dụng của Suno. Lưu ý: lời Việt hoặc bản soạn mới của một bài cũ có thể vẫn còn bản quyền.

### Mở trang

- **Trên Claude:** https://claude.ai/artifact/EQoBSTcU3A4SiS4ygvMUfC (chỉ chủ tài khoản mở được, trừ khi được chia sẻ).
- **Trên máy:** tải repo về (nút **Code → Download ZIP**), giải nén, mở `loi-dong-am/index.html` bằng Chrome hoặc
  Edge. Không cần cài gì, không cần mạng (không có mạng thì chữ hiện bằng phông của máy).

### Cách dùng

1. Dán lời gốc vào ô **Lời gốc**. Các dòng thẻ như `[Verse]`, `[Chorus]` được giữ nguyên.
2. Chọn **Cách đổi**: **Viết theo âm**, **Thêm khoảng trống** hoặc **Cả hai** (mỗi từ dùng cách nào có được).
   Thêm khoảng trống chỉ tách được từ có hai âm tiết trở lên; bài nhiều từ một âm tiết thì chọn **Cả hai**.
3. Chọn **Mức đổi**:
   - **Nhẹ**: còn tối đa 4 từ gốc liền nhau.
   - **Vừa** (nên dùng trước): còn tối đa 2 từ gốc liền nhau.
   - **Mạnh**: đổi mọi từ đổi được.
4. Từ màu đỏ là từ đã đổi, từ gốc hiện nhỏ phía trên. Bấm vào một từ để chọn cách viết khác, trả về từ gốc
   hoặc tự gõ.
5. Bấm **Chép lời**, rồi dán vào ô Lyrics ở chế độ Custom của Suno.
6. Suno vẫn báo bản quyền: chọn **Mạnh**, đổi sang **Cả hai** hoặc bấm **Tạo bản khác**, rồi thử lại.
7. Nghe bản Suno hát. Từ nào hát sai: bấm vào từ đó, chọn cách viết khác và đánh dấu **Ghi nhớ**. Từ đó được thêm vào
   **Từ điển riêng** (lưu trên trình duyệt) và lần sau tự dùng.

Ô **Đoạn trùng dài nhất** cho biết số từ gốc liền nhau còn giữ nguyên: càng ngắn càng khó bị nhận ra. Nút
**Đọc thử** dùng giọng máy của trình duyệt, chỉ để tham khảo, Suno có thể đọc khác.

### Từ điển riêng

Mỗi dòng một từ, dạng `word = cách viết`, ví dụ `lord = lawrd`. Từ có trong danh sách luôn được đổi theo cách bạn
ghi. Ghi `word = word` (giống hệt từ gốc) để không bao giờ đổi từ đó.

### Cách hoạt động

Mỗi từ được xét theo thứ tự:

1. **Từ điển riêng** của bạn.
2. **Từ đồng âm** (từ thật, đọc y hệt): night → knight, peace → piece, I → Eye. Suno hát từ thật chuẩn nhất, nhưng
   nghĩa thay đổi. Tắt bằng ô *Dùng từ đồng âm*.
3. **Danh sách viết theo âm** hơn 300 từ hay gặp trong lời hát: love → luv, heart → hart, enough → enuff.
4. **Quy tắc chính tả** giữ nguyên âm đọc: `ph` → `f`, `-ight` → `-ite`, `-tion` → `-shun`, `c` → `k`,
   `-y` → `-ee`… Các quy tắc đã được thử trên 4.000 từ tiếng Anh thông dụng nhất; từ nào bị đọc sai được loại ra.

Cách **Thêm khoảng trống** tách âm tiết bằng bộ quy tắc tách chữ tiếng Anh của TeX (hyph-en-us, giữ nguyên bản
quyền trong `loi-dong-am/hyphen-en-us.js`), rồi tách thêm các âm tiết mở mà bộ quy tắc để dính (o pen, to night).
Từ một âm tiết (night, grace) không tách.

Sau đó trang chọn những từ cần đổi sao cho số từ gốc liền nhau không vượt quá mức đã chọn. Mỗi lần bấm
**Tạo bản khác**, trang chọn lại các từ và cách viết khác.

Không đổi được: các từ rất ngắn như *the, and, a, my, now*. Muốn đổi thì thêm vào Từ điển riêng.

## Tải nhạc từ Suno (Bokin Suno)

Tải các bài trong một workspace Suno về máy, dạng **WAV** (hoặc MP3); chạy lại thì chỉ tải bài mới. Tool mở một
Chrome thật đã đăng nhập Suno và tải qua đúng nút **Download** của Suno. Chạy trên **Windows** hoặc **Linux**.

Cài đặt và cách dùng: [TAI-NHAC-SUNO.md](TAI-NHAC-SUNO.md).

## Cho người phát triển

```
loi-dong-am/engine.js       bộ đổi chữ (chạy trên trình duyệt và Node)
loi-dong-am/hyphen-en-us.js bộ quy tắc tách âm tiết tiếng Anh (TeX hyph-en-us)
loi-dong-am/index.html      giao diện
tests/engine.test.js        bài thử bộ đổi chữ
tests/page.test.js          bài thử trang trong Chromium (Playwright)
tools/build-artifact.js     gộp trang thành một file để đăng lên Claude: dist/loi-dong-am.html
```

```
npm ci
npx playwright install chromium
npm test                 # bộ đổi chữ
npm run test:page        # trang
npm run build:artifact   # dist/loi-dong-am.html
```

GitHub Actions (`.github/workflows/test.yml`) chạy cả ba bước trên Windows và Linux mỗi lần push.

## Bokin Suno Master: làm sạch và master nhạc tạo bằng Suno AI

Công cụ chạy trên máy bạn, mở trong trình duyệt. Bạn thả bài hát Suno vào, chọn kiểu master,
bấm **Master**, rồi nghe so sánh bản gốc với bản đã master và tải về.

Quy trình xử lý một bài:

```
Bài Suno ──► lọc ù thấp ──► khử lỗi AI ──► khớp bài mẫu / EQ ──► bass mono, độ rộng stereo
         ──► độ ấm ──► độ dày ──► nén "dính" ──► chỉnh độ to (LUFS) + limiter đỉnh thật ──► WAV / FLAC / MP3
```

| Bước | Làm gì |
|---|---|
| Lọc ù thấp | Cắt dưới 25 Hz (kiểu Dark piano và Giáng sinh cổ điển: 20 Hz) (tiếng ù, DC), giữ nguyên hình dạng tiếng trống kick. |
| Khử lỗi AI | **Shimmer**: tiếng rè lấp lánh kiểu kim loại ở dải cao, lỗi đặc trưng của Suno. **Tiếng rít đều**: một tần số cao kêu suốt bài. **Tiếng xì nền** ("xào xào", tắt sẵn, trừ kiểu Bossa nova, Jazz, Dark piano và Giáng sinh cổ điển) và **âm "s" chói** (tắt sẵn, trừ kiểu Giáng sinh cổ điển). |
| Khớp bài mẫu | Nếu bạn đưa một bài đã phát hành làm mẫu, màu âm và độ rộng stereo của bài bạn được chỉnh dần về phía bài mẫu (kiểu Matchering). |
| EQ | Sáu nút hay dùng cho bài Suno: Bass (100 Hz), Thân âm (180 Hz), Bớt đục (300 Hz), Độ rõ (2,5 kHz), Bớt gắt (3,5 kHz), Độ sáng (10 kHz). |
| Stereo | Bass dưới 120 Hz chuyển về mono để tiếng trầm chắc, nghe ổn trên điện thoại và loa nhỏ. Có thể nới rộng hoặc thu hẹp stereo. |
| Độ ấm | Bão hoà nhẹ kiểu đèn điện tử ở dải trầm-trung (100 Hz–1,2 kHz): thêm hoạ âm cho đàn guitar, piano, contrebass, giọng. Tắt sẵn, trừ kiểu Bossa nova, Jazz, Dark piano và Giáng sinh cổ điển. |
| Độ dày | Nén song song: một bản nén mạnh được trộn dưới bài gốc, nên chi tiết nhỏ (tiếng chổi trống, hơi thở, đuôi vang) được nâng lên mà tiếng gảy, tiếng trống vẫn giữ lực. Tắt sẵn, trừ kiểu Bossa nova, Jazz và Dark piano. |
| Nén "dính" | Nén nhẹ toàn bài cho các nhạc cụ quyện vào nhau. Trống vẫn giữ được lực vì nén phản ứng chậm. |
| Độ to + limiter | Đưa bài về độ to mục tiêu (LUFS) và giữ **đỉnh thật** (true peak, gồm cả đỉnh nằm giữa các mẫu) dưới trần, thường là -1 dBTP. |
| Xuất file | WAV 24-bit, WAV 16-bit 44,1 kHz (có dither), FLAC, hoặc MP3 320 kbps. |

Mỗi bài cho ra ba file:
- `<tên>_master.wav`: bản đã master;
- `<tên>_removed.wav`: **phần đã khử** (shimmer, tiếng rít...), để bạn nghe xem công cụ đã bỏ đi những gì;
- `<tên>_report.json`: số đo trước/sau và việc từng bước đã làm.

### Cài đặt (Windows)

1. Mở trang **[Bản phát hành mới nhất](https://github.com/vhung-spec/bokin-suno-tool/releases/latest)**, tải file
   **BokinSunoMaster-Setup-….exe** ở mục *Assets*.
2. Bấm đúp file vừa tải để cài. Không cần quyền quản trị. Nếu Windows hiện "Windows protected your PC", bấm
   **More info** → **Run anyway** (bộ cài chưa có chữ ký số).
3. Mở **Bokin Suno Master** từ Desktop hoặc menu Start. App mở trong một cửa sổ riêng.

#### Kích hoạt (lần đầu)

App dùng key **Bokin License**, chung với các app Bokin khác:

1. Lần đầu mở, app hiện **Mã máy** (dạng `ABCD-EFGH-IJKL-MNOP`). Bấm **Chép mã máy**.
2. Trong **Key Center**, cấp key cho mã máy đó với sản phẩm **Bokin Suno Master** (`suno-master`). Key gói (nhiều
   app) cũng được: kích hoạt ở một app là các app khác trong gói trên máy đó cùng mở.
3. Dán key vào ô **Key** rồi bấm **Kích hoạt**.

#### Tự cập nhật

- App tự kiểm tra bản mới khi mở, rồi 5 phút một lần, và tự tải về ở chế độ nền.
- Có bản mới thì góc trên hiện nút **Có bản mới … · Cập nhật ngay**. Bấm vào là app tắt, cài bản mới, rồi tự mở lại
  (khoảng nửa phút). Không bấm thì bản mới được cài khi bạn đóng app.
- Bài đang master dở thì app chờ xong mới cài.
- Bản mới do GitHub tự build, chạy thử (cài thật, cài đè, tự cập nhật) rồi mới phát hành, mỗi lần có thay đổi.

Bài đã master nằm trong thư mục **Nhạc\Bokin Suno Master** (`Music\Bokin Suno Master`), mỗi bài một thư mục con. Nút
**Thư mục kết quả** và **Mở thư mục** trong app mở thẳng thư mục đó. Gỡ app hay cập nhật không xoá các bài này.

Công cụ chỉ cần CPU, không cần GPU. Trên máy chạy thử (một máy chủ đám mây khá chậm), một bài
3 phút mất khoảng 30 giây. Máy tính thường sẽ nhanh hơn.

### Chạy từ mã nguồn (WSL2, Linux, macOS)

Bản chạy từ mã nguồn cũng cần key (Mã máy của Linux/WSL khác Mã máy của Windows trên cùng máy), và không tự cập
nhật: lấy bản mới bằng `git pull`.

```bash
git clone -b claude/suno-ai-mastering-tool-rfg0o5 https://github.com/vhung-spec/bokin-suno-tool.git ~/bokin-suno-tool
~/bokin-suno-tool/scripts/install.sh      # WSL2/Ubuntu: tạo biểu tượng trên Desktop của Windows
~/bokin-suno-tool/.venv/bin/bokin-suno app
```

Trên macOS, thay dòng `install.sh` bằng `python3 -m venv .venv && .venv/bin/pip install -e ".[app]"` trong thư mục
`~/bokin-suno-tool`.

### Cách dùng app

1. **Chọn bài hát**: kéo thả một hoặc nhiều bài. Nên tải bản **WAV** từ Suno: bản MP3 đã mất
   một phần chất lượng.
2. **Bài mẫu** (không bắt buộc): một bài đã phát hành, cùng thể loại, có tiếng bạn thích.
3. **Kiểu master**:

   | Kiểu | Độ to | Dùng cho |
   |---|---|---|
   | Nghe trực tuyến | -14 LUFS | Spotify, YouTube, TikTok, Apple Music. **Nên dùng.** |
   | To | -10 LUFS | EDM, nhạc club: to hơn nhưng bớt độ động. |
   | Nhẹ nhàng | -16 LUFS | Piano, acoustic, ballad. |
   | Chỉ làm sạch | giữ nguyên | Chỉ khử lỗi AI, không đổi độ to. |
   | Bossa nova | -14 LUFS | Ấm, gần, mượt: guitar nylon, giọng hát nhẹ (xem bên dưới). |
   | Jazz | -14 LUFS | Swing, piano trio, big band, jazz Giáng sinh: rõ, có lực, giữ độ động (xem bên dưới). |
   | Dark piano | -16 LUFS | Piano buồn, u tối, cinematic: trầm sâu, mềm, giữ độ động, đoạn lặng sạch xì (xem bên dưới). |
   | Giáng sinh cổ điển | -16 LUFS | Dàn nhạc, hợp xướng, chuông (Silent Night, O Holy Night, Kẹp hạt dẻ): rộng, trong, giữ độ động lớn (xem bên dưới). |

   Spotify, YouTube và Apple Music đều tự vặn nhỏ bài nào to hơn khoảng -14 LUFS. Master to
   hơn mức đó trên các nền tảng này không làm bài nghe to hơn, chỉ làm mất độ động.
4. **Tuỳ chỉnh** (không bắt buộc): mở mục 3 để chỉnh từng bước (xem bên dưới).
5. Bấm **Master**. Khi xong, bảng *Trước / Sau* hiện độ to, đỉnh thật và độ động. Có ba trình
   phát: bản gốc, bản đã master, phần đã khử.

Ô **So sánh cùng độ to** (bật sẵn) vặn nhỏ bản to hơn khi nghe trong app. Tai người luôn thấy
bản to hơn là "hay hơn", nên phải nghe ở cùng độ to mới biết master có thật sự tốt hơn không.

File kết quả nằm trong thư mục **Music\Bokin Suno Master**, mỗi bài một thư mục con (bấm *Thư mục kết quả*, hoặc
*Tải về* ở từng bài).

### Các tuỳ chỉnh

**Khử lỗi AI** (0–100%)
- **Shimmer (rè kim loại)**, mặc định 50%: tìm những điểm trên phổ ở dải cao (trên 3,5 kHz)
  vừa *ngắn* vừa *hẹp*: nổi hẳn lên so với chính tần số đó ngay trước và sau nó, và so với các
  tần số bên cạnh. Những điểm này bị kéo xuống. Tiếng trống (rộng về tần số) và nốt nhạc ngân
  dài (dài về thời gian) không bị đụng tới.
- **Tiếng rít đều**, mặc định 50%: chỉ cắt khi một tần số trên 2,5 kHz nổi lên suốt gần hết
  bài với mức ổn định. Nốt nhạc đến rồi đi nên không bị coi là tiếng rít. Một nốt được gõ lặp lại
  suốt bài (ostinato piano, nốt pedal) cũng không: bồi âm của nó luôn có nốt gốc nằm ở tần số
  1/2, 1/3... bên dưới, còn tiếng rít thì đứng một mình.
- **Tiếng xì nền** (tiếng "xào xào"), mặc định tắt, kiểu Bossa nova và Dark piano bật 35%, Giáng sinh cổ điển 30%, Jazz 20%: học mức tiếng xì từ những
  đoạn yên nhất, rồi trừ đi ở dải cao. Còn nghe xào xào thì tăng lên 50–60%. Tiếng chổi trống,
  shaker cũng là tiếng "xì" nên sẽ nhỏ đi một chút.
- **Âm "s" chói**, mặc định tắt, kiểu Giáng sinh cổ điển bật 30% (hợp xướng): giảm dải 5–10 kHz ở những
  lúc dải này vọt lên. Chỉ bật khi giọng hát bị chói, vì nó cũng làm hi-hat nhỏ đi.

Sau khi master, nghe file **phần đã khử**: nó chỉ nên chứa tiếng rè, rít, xì. Nếu nghe rõ nhạc
trong đó, hãy giảm mức khử xuống.

**Màu âm** (dB): Bass (100 Hz), Thân âm (180 Hz, tăng cho dày), Bớt đục (300 Hz, giảm khi bài
nghe "bí", "đục"), Độ rõ (2,5 kHz, tăng cho giọng và nhạc cụ nổi lên), Bớt gắt (3,5 kHz, giảm khi
giọng hoặc synth nghe gắt), Độ sáng (10 kHz).

**Độ dày và độ ấm** (0–100%): *Độ ấm* thêm hoạ âm nhẹ cho dải trầm-trung. Mức thêm tự theo độ to
của chính bài, nên bài nhỏ hay to đều được "màu" như nhau. Ở 35%, hoạ âm bậc 2 thấp hơn âm gốc
khoảng 34 dB ở những đoạn to: nghe ấm hơn chứ không méo. *Độ dày* là mức trộn bản nén song song.

**Bài mẫu**: *Mức khớp* (mặc định 70%) cho biết chỉnh màu âm bao xa về phía bài mẫu. Mỗi dải
tần được tăng tối đa +6 dB và giảm tối đa -9 dB. Từ 12 kHz trở lên, mức tăng tối đa giảm dần
(còn +1 dB ở 18 kHz). Dải nào bài Suno gần như trống thì không tăng, vì tăng chỗ trống chỉ làm
to tiếng xì. Ô *Độ to theo bài mẫu* dùng độ to của bài mẫu làm mục tiêu.

**Stereo và độ động**: Bass mono dưới (mặc định 120 Hz), Độ rộng stereo, Nén "dính" (mặc định 30%),
Độ to mục tiêu, Trần đỉnh thật. Nếu xuất MP3, đặt trần đỉnh khoảng -1,5 dBTP: bộ mã hoá MP3 có
thể đẩy đỉnh lên một chút.

### Dùng bằng dòng lệnh

```bash
.venv/bin/bokin-suno master "Bài 1.wav" "Bài 2.wav"          # preset Nghe trực tuyến, kết quả vào outputs/
.venv/bin/bokin-suno master thu_muc_bai/ --preset loud --out ket_qua/
.venv/bin/bokin-suno master bai.wav --reference bai_mau.wav --match 0.8 --match-loudness
.venv/bin/bokin-suno master bai.wav --shimmer 0.8 --deess 0.4 --mud -2 --air 1.5 --format mp3 --ceiling -1.5
.venv/bin/bokin-suno master bai.wav --keep-loudness --glue 0 --mono-bass 0   # chỉ làm sạch
.venv/bin/bokin-suno analyze bai.wav                                          # đo LUFS, đỉnh thật, LRA
.venv/bin/bokin-suno master --help                                            # mọi tuỳ chọn
```

Preset trong dòng lệnh: `streaming`, `loud`, `gentle`, `clean_only`, `bossa`, `jazz`, `dark_piano`,
`classical_christmas`.

### Kiểu Bossa nova và kiểu Jazz

Cả hai làm bài dày, ấm và rõ hơn mà vẫn giữ chất nhạc chơi tay, nhưng theo hai hướng khác nhau:
- **Bossa nova**: ấm, gần, mượt. Guitar nylon và giọng hát nhẹ được làm dày, hơi thở và tiếng chổi
  trống được kéo lại gần, cạnh gắt của tiếng gảy được làm dịu.
- **Jazz** (swing, piano trio, big band, jazz Giáng sinh): rõ, thoáng, có lực. Giữ nhiều độ động hơn,
  contrebass đi bè có trọng lượng, kèn và piano nổi lên, chũm chọe ride sáng.

| Bước | Bossa nova | Jazz | Nghe trực tuyến |
|---|---|---|---|
| Bass 100 Hz | 0 | +1 dB (contrebass đi bè) | 0 |
| Thân âm 180 Hz | +2,5 dB | +1,5 dB | 0 |
| Độ rõ 2,5 kHz | +1 dB | +1,5 dB (kèn, piano) | 0 |
| Bớt gắt 3,5 kHz | −1,5 dB (tiếng gảy, giọng Suno) | 0 | 0 |
| Độ sáng 10 kHz | +1 dB | +2 dB (chũm chọe ride) | 0 |
| Độ ấm | 50% | 25% | tắt |
| Độ dày | 45% | 20% (giữ độ động) | tắt |
| Nén "dính" | 15% | 25% (cho cả ban nhạc quyện) | 30% |
| Shimmer | 40% | 35% (giữ chũm chọe) | 50% |
| Tiếng xì nền | 35% | 20% (giữ chũm chọe, chổi trống) | tắt |
| Bass mono dưới | 100 Hz | 100 Hz | 120 Hz |
| Limiter nhả | 150 ms | 150 ms (contrebass không bị rè) | 80 ms |

Độ dày nâng chi tiết nhỏ nên cũng nâng tiếng xì "xào xào". Vì vậy cả hai kiểu đều bật khử xì: ở đoạn
nhẹ, tiếng xì còn thấp hơn kiểu *Nghe trực tuyến* khoảng 2,5 dB. Khử xì cũng làm tiếng chổi trống,
shaker, chũm chọe nhỏ đi một chút, vì chúng cũng là âm thanh dạng "xì". Nếu thấy mất, hãy giảm
*Tiếng xì nền*; nếu vẫn còn xào xào, tăng lên 50–60%.

Đo trên hai bài tạo bằng code, ở cùng -14 LUFS:

| | Nghe trực tuyến | Bossa nova | Jazz |
|---|---|---|---|
| Bài jazz swing: độ động (LRA) | 11,1 LU | 9,4 LU | 10,4 LU |
| Bài jazz swing: đoạn intro nhẹ thấp hơn đoạn đầy đủ | 10,2 dB | 8,3 dB | 9,4 dB |
| Bài bossa: dải 120–300 Hz | 0 | +0,7 dB | +0,2 dB |
| Bài bossa: dải 2–4 kHz | 0 | −0,9 dB | −0,1 dB |
| Đỉnh so với độ to (PLR), cả hai bài | ~13 dB | ~13 dB | ~13 dB |

PLR không đổi nghĩa là tiếng gảy đàn và tiếng trống không bị ép bẹt. Bài bossa có guitar nylon,
contrebass, chổi trống, chuông Giáng sinh. Bài jazz có contrebass đi bè, chũm chọe ride, piano đệm,
một câu saxophone. Cả hai đều có chút rè và xì kiểu Suno, và có thể nghe trong bản trình duyệt.

Các con số trên đo trên bài giả lập, chưa phải bài Suno thật. Hãy nghe so sánh cùng độ to. Nếu thấy
quá dày hoặc quá sáng, giảm *Độ dày*, *Độ rõ* hoặc *Độ sáng* trong mục Tuỳ chỉnh.

### Kiểu Dark piano

Cho nhạc piano buồn, u tối, cinematic (piano solo, hoặc piano với pad, dây, vang dài): **trầm sâu,
mềm, giữ độ động**.
- **-16 LUFS** thay vì -14: đỉnh tiếng búa đàn piano cao hơn độ to khoảng 17 dB. Ép lên -14 LUFS thì
  limiter phải nén mạnh, tiếng gõ phím bị bẹt. Ở -16 LUFS, limiter chỉ chạm nhẹ, nhả chậm (300 ms) nên
  hợp âm ngân dài không bị "phập phồng".
- Quãng tám trầm có trọng lượng (+1,5 dB ở 100 Hz). Tiếng hộp, đục ở 300 Hz và tiếng búa leng keng
  của piano Suno được dịu xuống. Dải cao tối hơn một chút.
- Đoạn lặng và đuôi vang là chỗ tiếng xì của Suno lộ rõ nhất, nên kiểu này bật khử xì 35%.
- Lọc ù thấp ở 20 Hz (không phải 25 Hz) để giữ nốt La thấp nhất của piano (27,5 Hz). Bass mono dưới
  80 Hz, để tiếng piano trầm vẫn còn độ rộng.

| Bước | Dark piano | Nghe trực tuyến |
|---|---|---|
| Độ to | -16 LUFS | -14 LUFS |
| Bass 100 Hz | +1,5 dB (quãng tám trầm) | 0 |
| Bớt đục 300 Hz | −1,5 dB | 0 |
| Bớt gắt 3,5 kHz | −2 dB (tiếng búa leng keng) | 0 |
| Độ sáng 10 kHz | −1 dB (tối, mềm) | 0 |
| Độ ấm | 30% | tắt |
| Độ dày | 20% (đuôi vang, nốt nhẹ) | tắt |
| Nén "dính" | 10% | 30% |
| Shimmer | 45% | 50% |
| Tiếng xì nền | 35% | tắt |
| Bass mono dưới | 80 Hz | 120 Hz |
| Limiter nhả | 300 ms | 80 ms |

Đo trên một bài dark piano tạo bằng code dài 40 giây, cung Rê thứ: quãng tám trầm, giai điệu thưa,
một nốt La cao gõ lặp lại suốt bài, dây nền ở đoạn giữa, vang 2,8 giây. Bài có đoạn mở đầu nhẹ, đoạn
giữa mạnh, một đoạn lặng, và có tiếng xì, rè, tiếng hộp, tiếng gắt kiểu Suno:

| | Nghe trực tuyến | Nhẹ nhàng | Dark piano |
|---|---|---|---|
| Độ to | -14 LUFS | -16 LUFS | -16 LUFS |
| Limiter nén tối đa | 2,9 dB | 0,7 dB | 1,2 dB |
| Độ động (LRA) | 10,5 LU | 11,3 LU | 10,1 LU |
| Đoạn mạnh to hơn đoạn nhẹ | 7,8 dB | 8,4 dB | 7,4 dB |
| Tiếng xì ở đoạn lặng (so với độ to bài) | −33 dB | −34 dB | −37 dB |
| Dải 40–120 Hz | 0 | −0,2 dB | +1,5 dB |
| Dải 250–350 Hz | 0 | −0,1 dB | −1,2 dB |
| Dải 2,5–5 kHz | 0 | −0,2 dB | −1,5 dB |
| Dải trên 10 kHz | 0 | −0,3 dB | −2,1 dB |

Phần bị khử ở đoạn mạnh thấp hơn tiếng đàn 43 dB, tức tiếng piano gần như không bị đụng tới. Nốt La
lặp lại không bị coi là tiếng rít. Nếu muốn sáng hơn, tăng *Độ sáng* về 0. Nếu muốn to hơn cho
YouTube, đặt độ to -14 LUFS trong mục Tuỳ chỉnh: đổi lại, tiếng gõ phím sẽ bị nén nhiều hơn.

### Kiểu Giáng sinh cổ điển

Cho nhạc Giáng sinh giao hưởng và hợp xướng (Silent Night, O Holy Night, Kẹp hạt dẻ...): **rộng, trong,
giữ độ động lớn**.
- **Giữ độ động**: không nén song song, nén "dính" rất nhẹ (10%), -16 LUFS và limiter nhả chậm (400 ms).
  Đoạn pianissimo vẫn nhẹ, đoạn cả dàn nhạc vẫn hoành tráng.
- Contrebass và timpani có trọng lượng (+1 dB ở 100 Hz). Tiếng đục ở 300 Hz do vang nhà thờ dồn lại được
  bớt đi. Lời hợp xướng rõ hơn (+1 dB ở 2,5 kHz). Tiếng vĩ cầm rít kiểu Suno được dịu xuống (−2 dB ở
  3,5 kHz). Dải cao sáng hơn (+1,5 dB ở 10 kHz) cho chuông và hợp xướng.
- Khử "s" nhẹ (30%), vì hợp xướng của Suno hay "xì" ở âm "s". Bộ khử chỉ ra tay khi dải 5–10 kHz vọt lên
  đột ngột so với phần còn lại của bài, nên tiếng chuông không bị đụng tới.
- Khử xì 30% cho các đoạn lặng. Lọc ù ở 20 Hz để giữ pedal organ và timpani. Bass mono dưới 60 Hz, để dàn
  dây trầm vẫn có độ rộng.

| Bước | Giáng sinh cổ điển | Nghe trực tuyến |
|---|---|---|
| Độ to | -16 LUFS | -14 LUFS |
| Bass 100 Hz | +1 dB (contrebass, timpani) | 0 |
| Bớt đục 300 Hz | −1,5 dB (vang nhà thờ) | 0 |
| Độ rõ 2,5 kHz | +1 dB (lời hợp xướng) | 0 |
| Bớt gắt 3,5 kHz | −2 dB (vĩ cầm rít) | 0 |
| Độ sáng 10 kHz | +1,5 dB (chuông) | 0 |
| Độ ấm | 20% | tắt |
| Độ dày | tắt (giữ độ động) | tắt |
| Nén "dính" | 10% | 30% |
| Shimmer | 50% | 50% |
| Tiếng xì nền | 30% | tắt |
| Âm "s" chói | 30% (hợp xướng) | tắt |
| Bass mono dưới | 60 Hz | 120 Hz |
| Limiter nhả | 400 ms | 80 ms |

Đo trên một bài Giáng sinh giao hưởng tạo bằng code, dài 48 giây, giọng Đô trưởng: dàn dây (vĩ cầm, viola,
cello, contrebass), hợp xướng hát "aah" có âm "s" ở đầu từ, chuông glockenspiel và chuông ống, timpani, vang
nhà thờ 3,5 giây. Bài mở đầu pp, rồi hợp xướng vào, rồi cả dàn nhạc ff, rồi nhỏ dần, cuối cùng là một đoạn
lặng. Bài có tiếng vĩ cầm rít, tiếng đục, tiếng xì, tiếng rè kiểu Suno. Bài được đo hai lần: bản gốc với độ
động lớn như một bản thu giao hưởng, và bản đã bị nén to lên -11 LUFS như Suno thường làm:

| | Nghe trực tuyến | Giáng sinh cổ điển |
|---|---|---|
| Bản gốc (LRA 20,9 LU): độ động sau master | 17,0 LU | 19,9 LU |
| Bản gốc: đoạn ff to hơn đoạn pp (lúc đầu 16,4 dB) | 14,6 dB | 15,8 dB |
| Bản kiểu Suno (LRA 13,8 LU): độ động sau master | 12,3 LU | 13,9 LU |
| Bản kiểu Suno: đoạn ff to hơn đoạn pp (lúc đầu 13,2 dB) | 12,2 dB | 12,9 dB |
| Tiếng xì ở đoạn lặng (so với độ to bài) | −34 dB | −39 dB |
| Tiếng chuông nổi lên khỏi nền nhạc | 2,9 dB | 3,3 dB |
| Âm "s" của hợp xướng nổi lên khỏi nền nhạc | 3,8 dB | 3,7 dB |
| Dải 40–120 Hz (so với dải 500–1000 Hz) | 0 | +1,8 dB |
| Dải 250–350 Hz | 0 | −1,0 dB |
| Dải 1,5–2,5 kHz | 0 | +0,6 dB |
| Dải 3–5 kHz | 0 | −0,9 dB |

Tăng sáng thường làm âm "s" gắt thêm: kiểu Jazz đưa nó lên 4,3 dB. Ở kiểu này, bộ khử "s" giữ âm "s" như
cũ trong khi chuông sáng hơn. Ở một bài thử có âm "s" mạnh hơn, âm "s" nhỏ đi 3,8 dB mà chuông không đổi.
Phần bị khử ở đoạn cả dàn nhạc thấp hơn nhạc khoảng 43 dB, và không nốt nào bị coi nhầm là tiếng rít.

Nếu hợp xướng vẫn còn xì ở âm "s", tăng *Âm "s" chói* lên 50%. Nếu muốn to hơn cho YouTube, đặt độ to
-14 LUFS: bài to hơn 2 dB, đổi lại các cú timpani và đoạn cả dàn nhạc bị nén nhiều hơn.

### Giới hạn

- Master không sửa được những gì đã hỏng sẵn trong bài: tiếng méo do clip, giọng méo, nhạc cụ
  lẫn vào nhau. App sẽ báo khi bài gốc bị clip.
- Công cụ xử lý cả bài đã mix, không tách giọng và nhạc riêng.
- Các bộ khử lỗi dựa trên quy tắc xử lý tín hiệu, không phải mô hình AI. Chúng đã được kiểm tra
  trên tín hiệu tổng hợp (bài thử tạo bằng code, có chèn shimmer, tiếng rít và tiếng xì), chưa
  được chỉnh trên nhiều bài Suno thật. Hãy tin tai mình: nghe phần đã khử, và chỉnh mức khử theo
  từng bài.

### Cách làm và nguồn tham khảo

Toàn bộ code tự viết (NumPy, SciPy, soundfile), không chép code của dự án khác. Các ý tưởng tham khảo:
- Khử shimmer bằng cách so mỗi điểm trên phổ với trung vị của các điểm lân cận theo thời gian và
  tần số: giống ý tưởng của [GS-SunoShimmerFree](https://github.com/GSGrimoire/GS-SunoShimmerFree)
  và [deshimmer](https://github.com/TheApeMachine/deshimmer).
- Khớp bài mẫu bằng EQ pha tuyến tính: giống ý tưởng của [Matchering](https://github.com/sergree/matchering).
- Đo độ to theo ITU-R BS.1770-4 / EBU R128. Bộ lọc K-weighting dùng công thức của libebur128.
  Kết quả lệch khoảng 0,03 LU so với [pyloudnorm](https://github.com/csteinmetz1/pyloudnorm),
  vì pyloudnorm dùng bộ lọc gần đúng.
- EQ theo RBJ Audio EQ Cookbook.

### Phát triển

```bash
.venv/bin/pip install -e ".[app,dev]"
.venv/bin/python -m pytest
```

Mã nguồn nằm trong `bokin_suno/`:

| File | Nội dung |
|---|---|
| `master.py` | Chuỗi xử lý, cài đặt, preset |
| `clean.py` | Khử lỗi AI (STFT) |
| `tone.py` | Lọc ù, EQ, khớp bài mẫu, stereo |
| `dynamics.py` | Nén và limiter đỉnh thật |
| `analysis.py` | Đo độ to, đỉnh thật, phổ |
| `audio_io.py` | Đọc/ghi file |
| `app.py`, `static/index.html` | Máy chủ cục bộ và trang của app (màn hình kích hoạt, nút cập nhật) |
| `desktop.py` | App trên máy: cửa sổ riêng, một bản chạy, tự tắt, cài bản mới khi tắt, `--close` cho bộ cài |
| `licensing.py` | Kiểm tra key Bokin License (sản phẩm `suno-master`) |
| `updater.py` | Tự cập nhật từ Releases của kho này |
| `selftest.py` | `BokinSunoMaster.exe --selftest`: kiểm tra bản build từ đầu đến cuối |
| `cli.py` | Dòng lệnh |

`bokin_license/` là thư viện bản quyền chung của các app Bokin, chép nguyên từ kho Bokin License (`VENDORED.txt`).
Không sửa bản chép ở đây: sửa ở kho đó rồi chép lại.

Đóng gói Windows nằm trong `packaging/` (PyInstaller, Inno Setup, biểu tượng "Su" của bộ logo Bokin). Mỗi lần đẩy
lên nhánh `claude/suno-ai-mastering-tool-rfg0o5`, workflow `.github/workflows/bokin-suno-master.yml` chạy trên
Windows của GitHub:

1. Kiểm thử, build app bằng PyInstaller, chạy `--selftest` trên bản đã build, rồi build bộ cài Inno Setup.
2. Cài thật, cài đè lúc app đang chạy, rồi thử tự cập nhật lên bản `N.1` với một GitHub giả.
3. Phát hành Release `app-v1.0.<số lần chạy>` ngay trong kho này (kèm `bokin-suno-master-latest.json` mà app đọc).
