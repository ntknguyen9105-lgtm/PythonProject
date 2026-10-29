from django.db import models
import uuid
from django.conf import settings

# =========================================================
# DANH MỤC SẢN PHẨM
# =========================================================

class Category(models.Model):

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Tên danh mục"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ngày tạo"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Danh mục"
        verbose_name_plural = "Danh mục"
        ordering = ["name"]


# =========================================================
# SẢN PHẨM
# =========================================================

class Product(models.Model):

    # -----------------------------
    # THÔNG TIN CƠ BẢN
    # -----------------------------

    sku = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Mã sản phẩm"
    )

    name = models.CharField(
        max_length=200,
        verbose_name="Tên sản phẩm"
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="Danh mục"
    )
    # -----------------------------
    # SẢN PHẨM ĐỀ XUẤT
    # -----------------------------

    upsell_products = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        related_name="upsell_for_products",
        verbose_name="Sản phẩm Upsell",
        help_text="Các sản phẩm cao cấp hơn được đề xuất thay thế."
    )

    cross_sell_products = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        related_name="cross_sell_for_products",
        verbose_name="Sản phẩm Cross-sell",
        help_text="Các sản phẩm liên quan hoặc nên mua cùng."
    )
    # -----------------------------
    # THUỘC TÍNH GỌNG KÍNH
    # -----------------------------

    frame_shape = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Kiểu dáng"
    )

    material = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Chất liệu"
    )

    color = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Màu sắc"
    )

    size = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Kích thước"
    )
    # =========================================================
    # THÔNG TIN DÀNH RIÊNG CHO TRÒNG KÍNH
    # =========================================================

    lens_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Loại tròng"
    )

    lens_index = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Chiết suất"
    )

    lens_feature = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Tính năng tròng"
    )

    lens_diameter = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Đường kính"
    )
    # -----------------------------
    # ĐỐI TƯỢNG SỬ DỤNG
    # -----------------------------

    GENDER_CHOICES = [
        ("male", "Nam"),
        ("female", "Nữ"),
        ("unisex", "Unisex"),
    ]

    gender = models.CharField(
        max_length=20,
        choices=GENDER_CHOICES,
        default="unisex",
        verbose_name="Đối tượng"
    )

    # -----------------------------
    # GIÁ
    # -----------------------------

    original_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name="Giá gốc"
    )

    sale_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name="Giá bán"
    )

    # -----------------------------
    # TỒN KHO
    # -----------------------------

    stock = models.PositiveIntegerField(
        default=0,
        verbose_name="Số lượng tồn kho"
    )

    # -----------------------------
    # MÔ TẢ
    # -----------------------------

    description = models.TextField(
        blank=True,
        verbose_name="Mô tả sản phẩm"
    )

    # -----------------------------
    # ẢNH ĐẠI DIỆN
    # -----------------------------

    image = models.ImageField(
        upload_to="products/main/",
        blank=True,
        null=True,
        verbose_name="Ảnh đại diện"
    )

    # -----------------------------
    # HIỂN THỊ
    # -----------------------------

    is_active = models.BooleanField(
        default=True,
        verbose_name="Hiển thị trên website"
    )

    is_featured = models.BooleanField(
        default=False,
        verbose_name="Sản phẩm nổi bật"
    )

    # -----------------------------
    # THỜI GIAN
    # -----------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ngày tạo"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Ngày cập nhật"
    )

    # -----------------------------
    # HIỂN THỊ TÊN
    # -----------------------------

    def __str__(self):
        return f"{self.sku} - {self.name}"

    # -----------------------------
    # KIỂM TRA CÒN HÀNG
    # -----------------------------

    # -----------------------------
    # KIỂM TRA CÓ BIẾN THỂ
    # -----------------------------



    # -----------------------------
    # KIỂM TRA CÒN HÀNG
    # -----------------------------

    @property
    def active_variants(self):
        return self.variants.filter(is_active=True)

    @property
    def has_variants(self):
        return self.active_variants.exists()

    @property
    def total_variant_stock(self):
        return sum(
            variant.stock
            for variant in self.active_variants
        )

    @property
    def in_stock(self):
        if self.has_variants:
            return self.total_variant_stock > 0

        return self.stock > 0

    # -----------------------------
    # TÍNH % GIẢM GIÁ
    # -----------------------------

    @property
    def discount_percent(self):

        if (
            self.original_price
            and self.sale_price
            and self.original_price > self.sale_price
        ):

            discount = (
                (
                    self.original_price
                    - self.sale_price
                )
                / self.original_price
            ) * 100

            return round(discount)

        return 0

    class Meta:
        verbose_name = "Sản phẩm"
        verbose_name_plural = "Sản phẩm"
        ordering = ["-created_at"]


# =========================================================
# ẢNH CHI TIẾT SẢN PHẨM
# =========================================================

class ProductImage(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Sản phẩm"
    )

    image = models.ImageField(
        upload_to="products/gallery/",
        verbose_name="Ảnh chi tiết"
    )

    alt_text = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Mô tả ảnh"
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Thứ tự ảnh"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ngày thêm"
    )

    def __str__(self):
        return f"Ảnh - {self.product.name}"

    class Meta:
        verbose_name = "Ảnh sản phẩm"
        verbose_name_plural = "Ảnh sản phẩm"
        ordering = ["order", "id"]


# =========================================================
# BIẾN THỂ SẢN PHẨM
# =========================================================

# =========================================================
# BIẾN THỂ SẢN PHẨM
# =========================================================

class ProductVariant(models.Model):

    VARIANT_TYPE_CHOICES = [
        ("color", "Màu sắc"),
        ("degree", "Độ cận"),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants",
        verbose_name="Sản phẩm"
    )

    sku = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        verbose_name="Mã biến thể"
    )

    # -----------------------------
    # LOẠI BIẾN THỂ
    # -----------------------------

    variant_type = models.CharField(
        max_length=20,
        choices=VARIANT_TYPE_CHOICES,
        default="color",
        verbose_name="Loại biến thể"
    )

    value = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Giá trị biến thể"
    )
    color = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Màu sắc cũ"
    )

    degree = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Độ cận cũ"
    )

    # -----------------------------
    # THÔNG TIN BỔ SUNG
    # -----------------------------

    size = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Kích thước"
    )

    material = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Chất liệu"
    )

    # -----------------------------
    # GIÁ
    # -----------------------------

    price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        null=True,
        blank=True,
        verbose_name="Giá bán"
    )

    # -----------------------------
    # TỒN KHO
    # -----------------------------

    stock = models.PositiveIntegerField(
        default=0,
        verbose_name="Số lượng tồn kho"
    )

    # -----------------------------
    # ẢNH BIẾN THỂ
    # -----------------------------

    image = models.ImageField(
        upload_to="products/variants/",
        blank=True,
        null=True,
        verbose_name="Ảnh biến thể"
    )

    # -----------------------------
    # TRẠNG THÁI
    # -----------------------------

    is_active = models.BooleanField(
        default=True,
        verbose_name="Đang bán"
    )

    # -----------------------------
    # THỜI GIAN
    # -----------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ngày tạo"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Ngày cập nhật"
    )

    # -----------------------------
    # KIỂM TRA CÒN HÀNG
    # -----------------------------

    @property
    def in_stock(self):
        return self.stock > 0

    # -----------------------------
    # TỰ ĐỘNG TẠO SKU
    # -----------------------------

    def save(self, *args, **kwargs):

        if not self.sku or not self.sku.strip():

            product_sku = (
                self.product.sku
                if self.product and self.product.sku
                else "MINOO"
            )

            existing_count = (
                ProductVariant.objects
                .filter(product=self.product)
                .exclude(pk=self.pk)
                .count()
                + 1
            )

            base_sku = (
                f"{product_sku}-VAR-{existing_count:03d}"
            )

            sku = base_sku
            counter = 1

            while (
                ProductVariant.objects
                .filter(sku=sku)
                .exclude(pk=self.pk)
                .exists()
            ):

                counter += 1

                sku = (
                    f"{product_sku}-VAR-"
                    f"{existing_count:03d}-{counter}"
                )

            self.sku = sku

        super().save(*args, **kwargs)

    # -----------------------------
    # HIỂN THỊ TÊN
    # -----------------------------

    def __str__(self):

        if self.variant_type == "color":
            label = "Màu"

        elif self.variant_type == "degree":
            label = "Độ cận"

        else:
            label = "Biến thể"

        return (
            f"{self.product.name} - "
            f"{label}: {self.value}"
        )

    class Meta:
        verbose_name = "Biến thể sản phẩm"
        verbose_name_plural = "Biến thể sản phẩm"
        ordering = ["product", "id"]


# =========================================================
# TIN NHẮN LIÊN HỆ
# =========================================================

class ContactMessage(models.Model):

    name = models.CharField(
        "Họ và tên",
        max_length=100
    )

    phone = models.CharField(
        "Số điện thoại",
        max_length=20
    )

    email = models.EmailField(
        "Email",
        blank=True
    )

    message = models.TextField(
        "Nội dung"
    )

    is_read = models.BooleanField(
        "Đã xem",
        default=False
    )

    created_at = models.DateTimeField(
        "Gửi lúc",
        auto_now_add=True
    )

    SOURCE_CHOICES = [
        ("form", "Form liên hệ"),
        ("chat", "Chatbot"),
    ]

    source = models.CharField(
        "Nguồn",
        max_length=10,
        choices=SOURCE_CHOICES,
        default="form"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Tin nhắn liên hệ"
        verbose_name_plural = "Tin nhắn liên hệ"

    def __str__(self):
        return f"{self.name} - {self.phone}"


# =========================================================
# ĐÁNH GIÁ SẢN PHẨM
# =========================================================

class ProductReview(models.Model):

    RATING_CHOICES = [
        (1, "1 sao"),
        (2, "2 sao"),
        (3, "3 sao"),
        (4, "4 sao"),
        (5, "5 sao"),
    ]

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Sản phẩm"
    )

    order = models.ForeignKey(
        "Order",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="product_reviews",
        verbose_name="Đơn hàng"
    )

    order_item = models.ForeignKey(
        "OrderItem",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="product_reviews",
        verbose_name="Sản phẩm trong đơn hàng"
    )

    reviewer_name = models.CharField(
        "Tên người đánh giá",
        max_length=100
    )

    rating = models.PositiveSmallIntegerField(
        "Số sao",
        choices=RATING_CHOICES
    )

    comment = models.TextField(
        "Nội dung đánh giá"
    )

    created_at = models.DateTimeField(
        "Ngày đánh giá",
        auto_now_add=True
    )

    is_approved = models.BooleanField(
        "Đã duyệt",
        default=False
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Đánh giá sản phẩm"
        verbose_name_plural = "Đánh giá sản phẩm"

    def __str__(self):
        return (
            f"{self.reviewer_name} - "
            f"{self.product.name}"
        )


# =========================================================
# ĐƠN HÀNG
# =========================================================

class Order(models.Model):

    # -----------------------------
    # PHƯƠNG THỨC THANH TOÁN
    # -----------------------------

    PAYMENT_METHOD_CHOICES = [
        (
            "cod",
            "Thanh toán khi nhận hàng"
        ),
        (
            "bank",
            "Chuyển khoản ngân hàng"
        ),
    ]

    # -----------------------------
    # TRẠNG THÁI ĐƠN HÀNG
    # -----------------------------

    STATUS_CHOICES = [
        (
            "pending",
            "Chờ xác nhận"
        ),
        (
            "confirmed",
            "Đã xác nhận"
        ),
        (
            "shipping",
            "Đang giao hàng"
        ),
        (
            "completed",
            "Đã hoàn thành"
        ),
        (
            "cancelled",
            "Đã hủy"
        ),
    ]

    # -----------------------------
    # TRẠNG THÁI THANH TOÁN
    # -----------------------------

    PAYMENT_STATUS_CHOICES = [
        (
            "unpaid",
            "Chưa thanh toán"
        ),
        (
            "pending",
            "Chờ xác nhận"
        ),
        (
            "paid",
            "Đã thanh toán"
        ),
    ]

    # -----------------------------
    # MÃ ĐƠN HÀNG
    # -----------------------------

    order_code = models.CharField(
        "Mã đơn hàng",
        max_length=30,
        unique=True,
        editable=False
    )

    # -----------------------------
    # THÔNG TIN KHÁCH HÀNG
    # -----------------------------

    full_name = models.CharField(
        "Họ và tên",
        max_length=100
    )

    phone = models.CharField(
        "Số điện thoại",
        max_length=20
    )

    email = models.EmailField(
        "Email",
        blank=True
    )

    address = models.TextField(
        "Địa chỉ nhận hàng"
    )

    note = models.TextField(
        "Ghi chú",
        blank=True
    )

    # -----------------------------
    # THANH TOÁN
    # -----------------------------

    payment_method = models.CharField(
        "Phương thức thanh toán",
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        default="cod"
    )

    payment_status = models.CharField(
        "Trạng thái thanh toán",
        max_length=10,
        choices=PAYMENT_STATUS_CHOICES,
        default="unpaid"
    )

    # -----------------------------
    # TRẠNG THÁI ĐƠN
    # -----------------------------

    status = models.CharField(
        "Trạng thái đơn hàng",
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    # -----------------------------
    # GIÁ TRỊ ĐƠN HÀNG
    # -----------------------------

    subtotal = models.DecimalField(
        "Tạm tính",
        max_digits=12,
        decimal_places=0,
        default=0
    )

    shipping_fee = models.DecimalField(
        "Phí vận chuyển",
        max_digits=12,
        decimal_places=0,
        default=0
    )

    total = models.DecimalField(
        "Tổng thanh toán",
        max_digits=12,
        decimal_places=0,
        default=0
    )

    # -----------------------------
    # THỜI GIAN
    # -----------------------------

    created_at = models.DateTimeField(
        "Ngày đặt hàng",
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        "Cập nhật lần cuối",
        auto_now=True
    )

    # -----------------------------
    # TỰ ĐỘNG TẠO MÃ ĐƠN HÀNG
    # -----------------------------

    def save(self, *args, **kwargs):

        if not self.order_code:

            import uuid

            self.order_code = (
                f"MN{uuid.uuid4().hex[:10].upper()}"
            )

        super().save(*args, **kwargs)

    # -----------------------------
    # HIỂN THỊ
    # -----------------------------

    def __str__(self):
        return (
            f"{self.order_code} - "
            f"{self.full_name}"
        )

    class Meta:
        verbose_name = "Đơn hàng"
        verbose_name_plural = "Đơn hàng"
        ordering = ["-created_at"]


# =========================================================
# SẢN PHẨM TRONG ĐƠN HÀNG
# =========================================================

class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Đơn hàng"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Sản phẩm"
    )

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Biến thể"
    )

    # Lưu tên sản phẩm tại thời điểm đặt hàng
    # để sau này sản phẩm bị đổi tên/xóa
    # thì đơn hàng vẫn hiển thị đúng thông tin cũ.
    product_name = models.CharField(
        "Tên sản phẩm",
        max_length=255
    )

    variant_name = models.CharField(
        "Thông tin biến thể",
        max_length=255,
        blank=True
    )

    price = models.DecimalField(
        "Đơn giá",
        max_digits=12,
        decimal_places=0
    )

    quantity = models.PositiveIntegerField(
        "Số lượng",
        default=1
    )

    line_total = models.DecimalField(
        "Thành tiền",
        max_digits=12,
        decimal_places=0
    )

    def __str__(self):
        return (
            f"{self.product_name} "
            f"x {self.quantity}"
        )

    class Meta:
        verbose_name = "Sản phẩm trong đơn"
        verbose_name_plural = "Sản phẩm trong đơn"


class PromotionCustomer(models.Model):
        AGE_CHOICES = [
            ('under_18', 'Dưới 18 tuổi'),
            ('18_22', '18 - 22 tuổi'),
            ('23_30', '23 - 30 tuổi'),
            ('31_40', '31 - 40 tuổi'),
            ('over_40', 'Trên 40 tuổi'),
        ]

        GENDER_CHOICES = [
            ('male', 'Nam'),
            ('female', 'Nữ'),
            ('other', 'Khác'),
        ]

        PRICE_CHOICES = [
            ('under_300', 'Dưới 300.000đ'),
            ('300_500', '300.000đ - 500.000đ'),
            ('500_800', '500.000đ - 800.000đ'),
            ('over_800', 'Trên 800.000đ'),
        ]

        user = models.OneToOneField(
            settings.AUTH_USER_MODEL,
            on_delete=models.SET_NULL,
            null=True,
            blank=True,
            related_name='promotion_profile',
            verbose_name='Tài khoản'
        )

        name = models.CharField(
            max_length=150,
            verbose_name='Họ và tên'
        )

        phone = models.CharField(
            max_length=20,
            unique=True,
            verbose_name='Số điện thoại'
        )

        email = models.EmailField(
            blank=True,
            verbose_name='Email'
        )

        age_group = models.CharField(
            max_length=20,
            choices=AGE_CHOICES,
            verbose_name='Độ tuổi'
        )

        gender = models.CharField(
            max_length=10,
            choices=GENDER_CHOICES,
            verbose_name='Giới tính'
        )

        price_range = models.CharField(
            max_length=20,
            choices=PRICE_CHOICES,
            verbose_name='Mức giá quan tâm'
        )

        first_order_completed = models.BooleanField(
            default=False,
            verbose_name='Đã mua đơn đầu'
        )

        second_order_completed = models.BooleanField(
            default=False,
            verbose_name='Đã mua đơn thứ hai'
        )

        created_at = models.DateTimeField(
            auto_now_add=True,
            verbose_name='Ngày tạo'
        )

        updated_at = models.DateTimeField(
            auto_now=True,
            verbose_name='Cập nhật'
        )

        def __str__(self):
            return f'{self.name} - {self.phone}'

        class Meta:
            verbose_name = 'Khách hàng ưu đãi'
            verbose_name_plural = 'Khách hàng ưu đãi'

class DiscountCoupon(models.Model):
        TYPE_CHOICES = [
            ('FIRST', 'Đơn đầu tiên - 20%'),
            ('SECOND', 'Đơn tiếp theo - 25%'),
        ]

        customer = models.ForeignKey(
            PromotionCustomer,
            on_delete=models.CASCADE,
            related_name='coupons',
            verbose_name='Khách hàng'
        )

        code = models.CharField(
            max_length=50,
            unique=True,
            verbose_name='Mã giảm giá'
        )

        coupon_type = models.CharField(
            max_length=10,
            choices=TYPE_CHOICES,
            verbose_name='Loại mã'
        )

        discount_percent = models.PositiveIntegerField(
            verbose_name='Phần trăm giảm'
        )

        is_used = models.BooleanField(
            default=False,
            verbose_name='Đã sử dụng'
        )

        is_active = models.BooleanField(
            default=True,
            verbose_name='Đang hoạt động'
        )

        created_at = models.DateTimeField(
            auto_now_add=True,
            verbose_name='Ngày tạo'
        )

        used_at = models.DateTimeField(
            null=True,
            blank=True,
            verbose_name='Ngày sử dụng'
        )

        def __str__(self):
            return f'{self.code} - {self.discount_percent}%'

        class Meta:
            verbose_name = 'Mã giảm giá'
            verbose_name_plural = 'Mã giảm giá'





class SePayTransaction(models.Model):
    sepay_transaction_id = models.CharField(
        max_length=100,
        unique=True,
    )

    order = models.ForeignKey(
        "Order",
        on_delete=models.PROTECT,
        related_name="sepay_transactions",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    transfer_content = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return (
            f"SePay {self.sepay_transaction_id} "
            f"- {self.order.order_code}"
        )