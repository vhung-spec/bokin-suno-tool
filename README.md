# Bokin Suno Tool

Công cụ hỗ trợ làm cover trên Suno AI.

## Lời Đồng Âm

Viết lại lời bài hát **tiếng Anh** theo cách đọc. Suno vẫn hát như cũ, nhưng chữ không còn trùng nguyên văn với
bản lời có sẵn trên mạng, nên bộ lọc lời bài hát của Suno khó nhận ra. Ví dụ:

| Lời gốc | Lời cho Suno | Mức đổi |
| --- | --- | --- |
| How precious did that grace appear | How **preshus** did that **grayce** appear | Vừa |
| Silent night, holy night | **Sylent knight**, **wholly knight** | Mạnh |

> Chỉ dùng cho bài **đã hết bản quyền** (Public Domain) hoặc lời do chính bạn viết. Đổi chữ để qua bộ lọc có thể
> trái điều khoản sử dụng của Suno. Lưu ý: lời Việt hoặc bản soạn mới của một bài cũ có thể vẫn còn bản quyền.

### Mở trang

- **Trên Claude:** https://claude.ai/artifact/EQoBSTcU3A4SiS4ygvMUfC (chỉ chủ tài khoản mở được, trừ khi được chia sẻ).
- **Trên máy:** tải repo về (nút **Code → Download ZIP**), giải nén, mở `loi-dong-am/index.html` bằng Chrome hoặc
  Edge. Không cần cài gì, không cần mạng (không có mạng thì chữ hiện bằng phông của máy).

### Cách dùng

1. Dán lời gốc vào ô **Lời gốc**. Các dòng thẻ như `[Verse]`, `[Chorus]` được giữ nguyên.
2. Chọn **Mức đổi**:
   - **Nhẹ**: còn tối đa 4 từ gốc liền nhau.
   - **Vừa** (nên dùng trước): còn tối đa 2 từ gốc liền nhau.
   - **Mạnh**: đổi mọi từ đổi được.
3. Từ màu đỏ là từ đã viết lại, từ gốc hiện nhỏ phía trên. Bấm vào một từ để chọn cách viết khác, trả về từ gốc
   hoặc tự gõ.
4. Bấm **Chép lời**, rồi dán vào ô Lyrics ở chế độ Custom của Suno.
5. Suno vẫn báo bản quyền: chọn **Mạnh** hoặc bấm **Tạo bản khác**, rồi thử lại.
6. Nghe bản Suno hát. Từ nào hát sai: bấm vào từ đó, chọn cách viết khác và đánh dấu **Ghi nhớ**. Từ đó được thêm vào
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
