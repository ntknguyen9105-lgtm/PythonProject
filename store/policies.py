# -*- coding: utf-8 -*-
"""
NỘI DUNG CÁC TRANG CHÍNH SÁCH – MINOO EYEWEAR

CÁCH SỬA:
- Mọi chỗ để trong dấu [ ] là thông tin cửa hàng cần điền (số ngày, phí, tài khoản...).
  Trên website, các dòng còn dấu [ ] sẽ được tô vàng để bạn dễ phát hiện.
- Tìm "[" trong file này để kiểm tra còn sót chỗ nào trước khi đưa website lên.
- Muốn thêm mục: thêm một khối {"heading": ..., "paragraphs": [...], "bullets": [...]}.
- Muốn thêm một chính sách mới: thêm một khối dict vào cuối danh sách POLICIES.
- Đây là nội dung khung tham khảo, bạn nên rà lại theo cách cửa hàng thực tế vận hành
  và theo quy định hiện hành.
"""

HOTLINE = "090 697 17 96"
EMAIL = "matkinhminoo@gmail.com"
ADDRESS = "112 Thái Thị Bôi, Đà Nẵng"

POLICIES = [

    # ------------------------------------------------------------------
    {
        "slug": "thanh-toan",
        "title": "Chính sách thanh toán",
        "summary": "Các hình thức thanh toán khi mua kính tại MINOO.",
        "sections": [
            {
                "heading": "Hình thức thanh toán",
                "paragraphs": ["MINOO hỗ trợ các hình thức thanh toán sau:"],
                "bullets": [
                    "Thanh toán trực tiếp bằng tiền mặt tại cửa hàng.",
                    "Chuyển khoản ngân hàng: [Tên ngân hàng – Số tài khoản – Chủ tài khoản].",
                    "Thanh toán khi nhận hàng (COD): [Có / Không áp dụng].",
                ],
            },
            {
                "heading": "Xác nhận thanh toán",
                "paragraphs": [
                    "Sau khi chuyển khoản, bạn vui lòng liên hệ MINOO kèm nội dung chuyển khoản để được xác nhận đơn hàng.",
                    "Đơn hàng được xử lý sau khi MINOO xác nhận đã nhận thanh toán: [Điều chỉnh theo thực tế].",
                ],
            },
            {
                "heading": "Lưu ý",
                "paragraphs": [
                    "Giá niêm yết trên website là giá đã bao gồm: [Ghi rõ có/không VAT, phí khác].",
                    "Nếu có sai lệch về giá hoặc thanh toán, MINOO sẽ liên hệ để xác nhận lại với bạn.",
                ],
            },
        ],
    },

    # ------------------------------------------------------------------
    {
        "slug": "giao-hang",
        "title": "Chính sách giao hàng",
        "summary": "Phạm vi, thời gian và phí giao hàng.",
        "sections": [
            {
                "heading": "Phạm vi giao hàng",
                "paragraphs": ["MINOO giao hàng tại: [Khu vực áp dụng, ví dụ: Đà Nẵng / toàn quốc]."],
            },
            {
                "heading": "Thời gian giao hàng",
                "bullets": [
                    "Nội thành: [Thời gian dự kiến].",
                    "Tỉnh/thành khác: [Thời gian dự kiến].",
                ],
                "paragraphs": ["Thời gian có thể thay đổi tùy tình hình vận chuyển hoặc dịp lễ, Tết."],
            },
            {
                "heading": "Phí vận chuyển",
                "paragraphs": ["[Mô tả phí giao hàng và điều kiện miễn phí (nếu có)]."],
            },
            {
                "heading": "Kiểm tra hàng khi nhận",
                "paragraphs": [
                    "Bạn nên kiểm tra sản phẩm ngay khi nhận hàng. Nếu có sai sót hoặc hư hỏng do vận chuyển, vui lòng liên hệ MINOO sớm để được hỗ trợ.",
                ],
            },
        ],
    },

    # ------------------------------------------------------------------
    {
        "slug": "doi-tra",
        "title": "Chính sách đổi trả",
        "summary": "Điều kiện và thời hạn đổi trả sản phẩm.",
        "sections": [
            {
                "heading": "Điều kiện đổi trả",
                "bullets": [
                    "Sản phẩm còn nguyên trạng, chưa qua sử dụng và còn đầy đủ phụ kiện đi kèm.",
                    "Có thông tin mua hàng (hóa đơn hoặc thông tin đơn hàng).",
                    "Thời hạn đổi trả: trong vòng [số ngày] kể từ ngày nhận hàng.",
                ],
            },
            {
                "heading": "Trường hợp không áp dụng đổi trả",
                "bullets": [
                    "Kính cắt tròng theo đơn (độ riêng của từng khách): [Ghi rõ chính sách của cửa hàng].",
                    "Sản phẩm hư hỏng do quá trình sử dụng hoặc bảo quản không đúng cách.",
                    "[Các trường hợp khác nếu có].",
                ],
            },
            {
                "heading": "Cách thực hiện",
                "paragraphs": [
                    "Bạn liên hệ MINOO qua hotline hoặc email, hoặc mang sản phẩm đến trực tiếp cửa hàng để được hỗ trợ.",
                    "Chi phí vận chuyển khi đổi trả: [Bên nào chịu phí].",
                ],
            },
        ],
    },

    # ------------------------------------------------------------------
    {
        "slug": "bao-hanh",
        "title": "Chính sách bảo hành",
        "summary": "Phạm vi, thời hạn và nơi tiếp nhận bảo hành.",
        "sections": [
            {
                "heading": "Thời hạn và phạm vi bảo hành",
                "bullets": [
                    "Thời hạn bảo hành gọng kính: [số tháng] kể từ ngày mua.",
                    "Phạm vi: [Ví dụ: lỗi kỹ thuật do nhà sản xuất, lỗi ốc vít, bản lề...].",
                ],
            },
            {
                "heading": "Trường hợp không bảo hành",
                "bullets": [
                    "Sản phẩm bị rơi vỡ, cong vênh hoặc trầy xước do tác động bên ngoài.",
                    "Sản phẩm đã bị sửa chữa ở nơi khác.",
                    "[Các trường hợp khác nếu có].",
                ],
            },
            {
                "heading": "Nơi tiếp nhận bảo hành",
                "paragraphs": [
                    "Bạn mang sản phẩm đến cửa hàng MINOO tại 112 Thái Thị Bôi, Đà Nẵng, hoặc liên hệ hotline để được hướng dẫn.",
                ],
            },
        ],
    },

    # ------------------------------------------------------------------
    {
        "slug": "bao-mat",
        "title": "Chính sách bảo mật thông tin",
        "summary": "Cách MINOO thu thập và bảo vệ thông tin của bạn.",
        "sections": [
            {
                "heading": "Thông tin MINOO thu thập",
                "paragraphs": ["Khi bạn gửi form liên hệ hoặc đặt hàng, MINOO có thể thu thập:"],
                "bullets": [
                    "Họ tên, số điện thoại, email.",
                    "Nội dung bạn gửi cho MINOO.",
                    "Thông tin đơn hàng: [Địa chỉ nhận hàng, sản phẩm đã chọn... nếu có đặt hàng online].",
                ],
            },
            {
                "heading": "Mục đích sử dụng",
                "bullets": [
                    "Liên hệ, tư vấn và hỗ trợ bạn.",
                    "Xử lý đơn hàng, giao hàng và bảo hành.",
                    "Cải thiện chất lượng phục vụ.",
                ],
            },
            {
                "heading": "Bảo mật và chia sẻ thông tin",
                "paragraphs": [
                    "MINOO cam kết không bán hoặc trao đổi thông tin cá nhân của bạn cho bên thứ ba vì mục đích thương mại.",
                    "Thông tin chỉ được chia sẻ trong phạm vi cần thiết để thực hiện dịch vụ (ví dụ đơn vị vận chuyển) hoặc khi có yêu cầu theo quy định pháp luật.",
                ],
            },
            {
                "heading": "Quyền của bạn",
                "paragraphs": [
                    "Bạn có quyền yêu cầu kiểm tra, chỉnh sửa hoặc xóa thông tin cá nhân đã cung cấp bằng cách liên hệ MINOO qua email hoặc hotline bên dưới.",
                ],
            },
        ],
    },
]