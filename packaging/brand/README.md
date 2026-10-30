# Biểu tượng Bokin Suno Master

Bản chép `make_icons.py` và `glyphs.json` từ thư mục `brand/` của kho `vhung-spec/bokin-video-fx` (nơi giữ bộ logo
chung của các app Bokin), thêm một dòng cho Bokin Suno Master: ô xanh lá `#6FD98A`, chữ "Su" màu `#0A3218`.

Chữ là Be Vietnam Pro ExtraBold (Lâm Bảo, Tony Le, ViệtAnh Nguyễn; Google Fonts), giấy phép SIL Open Font License
1.1; `glyphs.json` chỉ giữ đường viền các chữ, không phải file font.

Thêm cả một dòng cho **Bokin Suno Studio**: ô đỏ `#F25A5A`, chữ "Ss" màu `#3A0709` (đỏ nằm giữa hồng của Studio
Music và cam của Loop, không lẫn với app nào). `bokin_studio/static/logo.svg` là logo đó cho trang của app
(`make_icons.svg("suno-studio")`); `packaging/make_studio_icon.py` làm file `.ico` cho bộ cài.

Nên thêm dòng `suno-master` và dòng `suno-studio` vào `APPS` của bản gốc bên kho đó nữa, để bộ logo chung có đủ app.
