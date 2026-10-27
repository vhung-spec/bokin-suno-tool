# Bokin Suno Master: làm sạch và master nhạc tạo bằng Suno AI

Công cụ chạy trên máy bạn, mở trong trình duyệt. Bạn thả bài hát Suno vào, chọn kiểu master,
bấm **Master**, rồi nghe so sánh bản gốc với bản đã master và tải về.

Quy trình xử lý một bài:

```
Bài Suno ──► lọc ù thấp ──► khử lỗi AI ──► khớp bài mẫu / EQ ──► bass mono, độ rộng stereo
         ──► độ ấm ──► độ dày ──► nén "dính" ──► chỉnh độ to (LUFS) + limiter đỉnh thật ──► WAV / FLAC / MP3
```

| Bước | Làm gì |
|---|---|
| Lọc ù thấp | Cắt dưới 25 Hz (tiếng ù, DC), giữ nguyên hình dạng tiếng trống kick. |
| Khử lỗi AI | **Shimmer**: tiếng rè lấp lánh kiểu kim loại ở dải cao, lỗi đặc trưng của Suno. **Tiếng rít đều**: một tần số cao kêu suốt bài. **Tiếng xì nền** ("xào xào", tắt sẵn, kiểu Jazz bật 30%) và **âm "s" chói** (tắt sẵn). |
| Khớp bài mẫu | Nếu bạn đưa một bài đã phát hành làm mẫu, màu âm và độ rộng stereo của bài bạn được chỉnh dần về phía bài mẫu (kiểu Matchering). |
| EQ | Sáu nút hay dùng cho bài Suno: Bass (100 Hz), Thân âm (180 Hz), Bớt đục (300 Hz), Độ rõ (2,5 kHz), Bớt gắt (3,5 kHz), Độ sáng (10 kHz). |
| Stereo | Bass dưới 120 Hz chuyển về mono để tiếng trầm chắc, nghe ổn trên điện thoại và loa nhỏ. Có thể nới rộng hoặc thu hẹp stereo. |
| Độ ấm | Bão hoà nhẹ kiểu đèn điện tử ở dải trầm-trung (100 Hz–1,2 kHz): thêm hoạ âm cho đàn guitar, piano, contrebass, giọng. Tắt sẵn, trừ kiểu Jazz. |
| Độ dày | Nén song song: một bản nén mạnh được trộn dưới bài gốc, nên chi tiết nhỏ (tiếng chổi trống, hơi thở, đuôi vang) được nâng lên mà tiếng gảy, tiếng trống vẫn giữ lực. Tắt sẵn, trừ kiểu Jazz. |
| Nén "dính" | Nén nhẹ toàn bài cho các nhạc cụ quyện vào nhau. Trống vẫn giữ được lực vì nén phản ứng chậm. |
| Độ to + limiter | Đưa bài về độ to mục tiêu (LUFS) và giữ **đỉnh thật** (true peak, gồm cả đỉnh nằm giữa các mẫu) dưới trần, thường là -1 dBTP. |
| Xuất file | WAV 24-bit, WAV 16-bit 44,1 kHz (có dither), FLAC, hoặc MP3 320 kbps. |

Mỗi bài cho ra ba file:
- `<tên>_master.wav`: bản đã master;
- `<tên>_removed.wav`: **phần đã khử** (shimmer, tiếng rít...), để bạn nghe xem công cụ đã bỏ đi những gì;
- `<tên>_report.json`: số đo trước/sau và việc từng bước đã làm.

## Cài đặt

### Windows (qua WSL2, giống app Bokin Music)

1. Nếu máy chưa có WSL2 + Ubuntu: mở PowerShell bằng quyền Administrator, chạy `wsl --install`,
   khởi động lại máy, rồi mở **Ubuntu** để tạo tên người dùng và mật khẩu.
2. Trong cửa sổ Ubuntu, chạy:
   ```bash
   git clone -b claude/suno-ai-mastering-tool-rfg0o5 https://github.com/vhung-spec/bokin-suno-tool.git ~/bokin-suno-tool
   ~/bokin-suno-tool/scripts/install.sh
   ```
   Script cài Python, ffmpeg và thư viện, rồi tạo biểu tượng **Bokin Suno Master** trên Desktop.
3. Bấm đúp **Bokin Suno Master**. Một cửa sổ đen hiện log của app, và trình duyệt tự mở trang
   app. Đóng cửa sổ đen hoặc bấm *Tắt app* để tắt.

Công cụ chỉ cần CPU, không cần GPU. Trên máy chạy thử (một máy chủ đám mây khá chậm), một bài
3 phút mất khoảng 30 giây. Máy tính thường sẽ nhanh hơn.

### Linux hoặc macOS

```bash
git clone -b claude/suno-ai-mastering-tool-rfg0o5 https://github.com/vhung-spec/bokin-suno-tool.git ~/bokin-suno-tool
cd ~/bokin-suno-tool
python3 -m venv .venv && .venv/bin/pip install -e ".[app]"
.venv/bin/bokin-suno app --open
```

Trên Linux có thể chạy `scripts/install.sh` thay cho các lệnh trên: script tự tạo mục trong menu ứng dụng.

### Windows không dùng WSL (chưa chạy thử)

Cài [Python 3.11+](https://www.python.org/downloads/) và nhớ tick *Add python.exe to PATH*.
Tải mã nguồn về (nút **Code → Download ZIP** trên GitHub, nhánh `claude/suno-ai-mastering-tool-rfg0o5`),
giải nén, mở PowerShell trong thư mục đó rồi chạy:

```powershell
py -m venv .venv
.venv\Scripts\pip install -e ".[app]"
.venv\Scripts\bokin-suno app --open
```

## Cách dùng app

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
   | Jazz / Bossa nova | -14 LUFS | Bossa nova, jazz, jazz Giáng sinh: dày, ấm và rõ hơn (xem bên dưới). |

   Spotify, YouTube và Apple Music đều tự vặn nhỏ bài nào to hơn khoảng -14 LUFS. Master to
   hơn mức đó trên các nền tảng này không làm bài nghe to hơn, chỉ làm mất độ động.
4. **Tuỳ chỉnh** (không bắt buộc): mở mục 3 để chỉnh từng bước (xem bên dưới).
5. Bấm **Master**. Khi xong, bảng *Trước / Sau* hiện độ to, đỉnh thật và độ động. Có ba trình
   phát: bản gốc, bản đã master, phần đã khử.

Ô **So sánh cùng độ to** (bật sẵn) vặn nhỏ bản to hơn khi nghe trong app. Tai người luôn thấy
bản to hơn là "hay hơn", nên phải nghe ở cùng độ to mới biết master có thật sự tốt hơn không.

File kết quả nằm trong thư mục `outputs/` của dự án, mỗi bài một thư mục con. Trong WSL, mở
bằng Explorer tại `\\wsl$\Ubuntu\home\<tên bạn>\bokin-suno-tool\outputs` (tên `Ubuntu` có thể
khác, ví dụ `Ubuntu-22.04`), hoặc bấm *Tải về* trong app.

## Các tuỳ chỉnh

**Khử lỗi AI** (0–100%)
- **Shimmer (rè kim loại)**, mặc định 50%: tìm những điểm trên phổ ở dải cao (trên 3,5 kHz)
  vừa *ngắn* vừa *hẹp*: nổi hẳn lên so với chính tần số đó ngay trước và sau nó, và so với các
  tần số bên cạnh. Những điểm này bị kéo xuống. Tiếng trống (rộng về tần số) và nốt nhạc ngân
  dài (dài về thời gian) không bị đụng tới.
- **Tiếng rít đều**, mặc định 50%: chỉ cắt khi một tần số trên 2,5 kHz nổi lên suốt gần hết
  bài với mức ổn định. Nốt nhạc đến rồi đi nên không bị coi là tiếng rít.
- **Tiếng xì nền** (tiếng "xào xào"), mặc định tắt, kiểu Jazz bật 30%: học mức tiếng xì từ những
  đoạn yên nhất, rồi trừ đi ở dải cao. Còn nghe xào xào thì tăng lên 50–60%. Tiếng chổi trống,
  shaker cũng là tiếng "xì" nên sẽ nhỏ đi một chút.
- **Âm "s" chói**, mặc định tắt: giảm dải 5–10 kHz ở những lúc dải này vọt lên. Chỉ bật khi
  giọng hát bị chói, vì nó cũng làm hi-hat nhỏ đi.

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

## Dùng bằng dòng lệnh

```bash
.venv/bin/bokin-suno master "Bài 1.wav" "Bài 2.wav"          # preset Nghe trực tuyến, kết quả vào outputs/
.venv/bin/bokin-suno master thu_muc_bai/ --preset loud --out ket_qua/
.venv/bin/bokin-suno master bai.wav --reference bai_mau.wav --match 0.8 --match-loudness
.venv/bin/bokin-suno master bai.wav --shimmer 0.8 --deess 0.4 --mud -2 --air 1.5 --format mp3 --ceiling -1.5
.venv/bin/bokin-suno master bai.wav --keep-loudness --glue 0 --mono-bass 0   # chỉ làm sạch
.venv/bin/bokin-suno analyze bai.wav                                          # đo LUFS, đỉnh thật, LRA
.venv/bin/bokin-suno master --help                                            # mọi tuỳ chọn
```

Preset trong dòng lệnh: `streaming`, `loud`, `gentle`, `clean_only`, `jazz`.

## Kiểu Jazz / Bossa nova

Dành cho bossa nova, jazz và jazz Giáng sinh: tiếng dày, ấm và rõ hơn, mà vẫn giữ độ động của
nhạc chơi tay. So với kiểu *Nghe trực tuyến*, kiểu này:

| Bước | Jazz / Bossa nova | Vì sao |
|---|---|---|
| Thân âm 180 Hz | +2 dB | thân đàn guitar dây nylon, piano, contrebass dày hơn |
| Độ rõ 2,5 kHz | +1,5 dB | giọng, kèn, tiếng gảy đàn nổi lên |
| Độ sáng 10 kHz | +1 dB | độ thoáng của chũm chọe, chuông, tiếng chổi trống |
| Độ ấm | 35% | hoạ âm nhẹ cho dải trầm-trung |
| Độ dày | 35% | chi tiết nhỏ được nâng lên, đoạn intro nhẹ không bị chìm |
| Nén "dính" | 15% (thay vì 30%) | giữ độ động của nhạc chơi tay |
| Shimmer | 40% (thay vì 50%) | tránh làm mất tiếng chổi trống, chuông Giáng sinh |
| Tiếng xì nền | 30% (thay vì tắt) | độ dày nâng chi tiết nhỏ nên cũng nâng tiếng xì "xào xào"; khử xì bù lại |
| Bass mono dưới | 100 Hz | contrebass vẫn chắc mà không mất độ rộng của guitar |
| Limiter | nhả chậm hơn (150 ms) | tiếng contrebass không bị rè khi limiter làm việc |

Đo trên một bài bossa tạo bằng code (guitar nylon, contrebass, chổi trống, chuông; intro nhẹ 8 giây
rồi cả ban nhạc), so với kiểu *Nghe trực tuyến* ở cùng -14 LUFS:
- đoạn intro nhẹ gần đoạn đầy đủ hơn 1,3 dB (từ thấp hơn 5,4 dB còn thấp hơn 4,1 dB);
- đỉnh so với độ to (PLR) giữ nguyên khoảng 13 dB: tiếng gảy đàn không bị ép bẹt;
- dải 2–4 kHz cao hơn khoảng 1 dB, dải 120–300 Hz cao hơn khoảng 0,4 dB;
- độ động (LRA) giảm từ 5,8 xuống 4,5 LU: dày hơn nhưng vẫn còn chỗ thở.

Trên bài đó có thêm tiếng xì, ở cùng -14 LUFS: kiểu Jazz chưa khử xì làm tiếng xì ở đoạn intro to hơn
kiểu *Nghe trực tuyến* 1,3 dB; khử xì 30% đưa nó xuống thấp hơn khoảng 4–5 dB, 50% thấp hơn khoảng 5–6 dB.
Khử xì cũng làm tiếng chổi trống, shaker nhỏ đi một chút, vì chúng cũng là tiếng "xì": nếu thấy mất,
giảm *Tiếng xì nền*.

Các con số trên đo trên bài giả lập, chưa phải bài Suno thật. Hãy nghe so sánh cùng độ to. Nếu thấy
quá dày hoặc quá sáng, giảm *Độ dày*, *Độ rõ* hoặc *Độ sáng* trong mục Tuỳ chỉnh.

## Giới hạn

- Master không sửa được những gì đã hỏng sẵn trong bài: tiếng méo do clip, giọng méo, nhạc cụ
  lẫn vào nhau. App sẽ báo khi bài gốc bị clip.
- Công cụ xử lý cả bài đã mix, không tách giọng và nhạc riêng.
- Các bộ khử lỗi dựa trên quy tắc xử lý tín hiệu, không phải mô hình AI. Chúng đã được kiểm tra
  trên tín hiệu tổng hợp (bài thử tạo bằng code, có chèn shimmer, tiếng rít và tiếng xì), chưa
  được chỉnh trên nhiều bài Suno thật. Hãy tin tai mình: nghe phần đã khử, và chỉnh mức khử theo
  từng bài.

## Cách làm và nguồn tham khảo

Toàn bộ code tự viết (NumPy, SciPy, soundfile), không chép code của dự án khác. Các ý tưởng tham khảo:
- Khử shimmer bằng cách so mỗi điểm trên phổ với trung vị của các điểm lân cận theo thời gian và
  tần số: giống ý tưởng của [GS-SunoShimmerFree](https://github.com/GSGrimoire/GS-SunoShimmerFree)
  và [deshimmer](https://github.com/TheApeMachine/deshimmer).
- Khớp bài mẫu bằng EQ pha tuyến tính: giống ý tưởng của [Matchering](https://github.com/sergree/matchering).
- Đo độ to theo ITU-R BS.1770-4 / EBU R128. Bộ lọc K-weighting dùng công thức của libebur128.
  Kết quả lệch khoảng 0,03 LU so với [pyloudnorm](https://github.com/csteinmetz1/pyloudnorm),
  vì pyloudnorm dùng bộ lọc gần đúng.
- EQ theo RBJ Audio EQ Cookbook.

## Phát triển

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
| `app.py`, `static/index.html` | App web |
| `cli.py` | Dòng lệnh |
