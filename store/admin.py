from datetime import timedelta
from decimal import Decimal

from django.contrib import admin, messages
from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncMonth
from django.urls import path, reverse
from django.template.response import TemplateResponse
from django.utils import timezone
import uuid
from . import views
from .models import (
    Category,
    Product,
    ProductImage,
    ProductVariant,
    ContactMessage,
    ProductReview,
    Order,
    OrderItem,
    PromotionCustomer,
    DiscountCoupon,
)



# =========================================================
# COUPON 25% HELPERS
# =========================================================

# =========================================================
# COUPON 25% HELPERS
# =========================================================

def _normalize_phone(phone):
    """
    Chuẩn hóa số điện thoại Việt Nam để:
    0365756900
    +84365756900
    84365756900
    được hiểu là cùng một số.
    """

    phone = str(phone or "").strip()

    # Chỉ giữ số
    digits = "".join(
        char
        for char in phone
        if char.isdigit()
    )

    if not digits:
        return ""

    # +84xxxxxxxxx / 84xxxxxxxxx
    # -> 0xxxxxxxxx
    if digits.startswith("84"):

        digits = (
            "0"
            + digits[2:]
        )

    return digits


def _generate_second_coupon_code():

    while True:

        code = (
            f"MINOO25-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        if not DiscountCoupon.objects.filter(
            code=code
        ).exists():

            return code


def _get_promotion_customer_for_order(order):
    """
    Tìm PromotionCustomer của đơn hàng.
    So sánh số điện thoại sau khi chuẩn hóa.
    Nếu không tìm được thì thử email.
    """

    order_phone = _normalize_phone(
        getattr(
            order,
            "phone",
            ""
        )
    )

    # ==========================================
    # TÌM THEO PHONE ĐÃ CHUẨN HÓA
    # ==========================================

    if order_phone:

        for customer in (
            PromotionCustomer.objects.all()
        ):

            customer_phone = (
                _normalize_phone(
                    customer.phone
                )
            )

            if customer_phone == order_phone:

                return customer

    # ==========================================
    # FALLBACK EMAIL
    # ==========================================

    order_email = (
        getattr(
            order,
            "email",
            ""
        )
        or ""
    ).strip()

    if order_email:

        return (
            PromotionCustomer.objects
            .filter(
                email__iexact=order_email
            )
            .first()
        )

    return None


def _count_completed_orders_for_customer(
    customer
):
    """
    Đếm các đơn completed của cùng khách,
    kể cả khi phone lưu dạng 036... hoặc +8436...
    """

    customer_phone = _normalize_phone(
        customer.phone
    )

    if not customer_phone:
        return 0

    completed_count = 0

    completed_orders = (
        Order.objects
        .filter(
            status="completed"
        )
        .only(
            "phone"
        )
    )

    for order in completed_orders:

        if (
            _normalize_phone(
                order.phone
            )
            == customer_phone
        ):

            completed_count += 1

    return completed_count


def _sync_customer_reward_after_completed_order(
    order
):

    result = {
        "customer": None,
        "created_second_coupon": None,
        "completed_order_count": 0,
    }

    if order.status != "completed":

        return result

    customer = (
        _get_promotion_customer_for_order(
            order
        )
    )

    if customer is None:

        return result

    result["customer"] = customer

    completed_order_count = (
        _count_completed_orders_for_customer(
            customer
        )
    )

    result[
        "completed_order_count"
    ] = completed_order_count

    fields_to_update = []

    # ==========================================
    # ĐÃ CÓ ÍT NHẤT 1 ĐƠN HOÀN THÀNH
    # ==========================================

    if (
        completed_order_count >= 1
        and not customer.first_order_completed
    ):

        customer.first_order_completed = True

        fields_to_update.append(
            "first_order_completed"
        )

    # ==========================================
    # ĐÃ CÓ ÍT NHẤT 2 ĐƠN HOÀN THÀNH
    # ==========================================

    if (
        completed_order_count >= 2
        and not customer.second_order_completed
    ):

        customer.second_order_completed = True

        fields_to_update.append(
            "second_order_completed"
        )

    if fields_to_update:

        fields_to_update.append(
            "updated_at"
        )

        customer.save(
            update_fields=fields_to_update
        )

    # ==========================================
    # KHÓA MÃ FIRST 20%
    # ==========================================

    if completed_order_count >= 1:

        first_coupon = (
            DiscountCoupon.objects
            .filter(
                customer=customer,
                coupon_type="FIRST",
            )
            .order_by(
                "-created_at"
            )
            .first()
        )

        if first_coupon:

            first_updates = []

            if not first_coupon.is_used:

                first_coupon.is_used = True

                first_updates.append(
                    "is_used"
                )

            if first_coupon.is_active:

                first_coupon.is_active = False

                first_updates.append(
                    "is_active"
                )

            if first_coupon.used_at is None:

                first_coupon.used_at = (
                    timezone.now()
                )

                first_updates.append(
                    "used_at"
                )

            if first_updates:

                first_coupon.save(
                    update_fields=first_updates
                )

    # ==========================================
    # TẠO MÃ 25%
    # ==========================================
    #
    # Chỉ tạo sau đơn đầu và trước khi hoàn thành
    # đơn thứ hai.
    # ==========================================

    if (
        completed_order_count >= 1
        and completed_order_count < 2
    ):

        second_coupon = (
            DiscountCoupon.objects
            .filter(
                customer=customer,
                coupon_type="SECOND",
            )
            .order_by(
                "-created_at"
            )
            .first()
        )

        if second_coupon is None:

            second_coupon = (
                DiscountCoupon.objects.create(
                    customer=customer,
                    code=(
                        _generate_second_coupon_code()
                    ),
                    coupon_type="SECOND",
                    discount_percent=25,
                    is_used=False,
                    is_active=True,
                )
            )

            result[
                "created_second_coupon"
            ] = second_coupon

    return result

# =========================================================
# CATEGORY
# =========================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
    )

    search_fields = (
        "name",
    )


# =========================================================
# PRODUCT IMAGE INLINE
# =========================================================

class ProductImageInline(admin.TabularInline):

    model = ProductImage
    extra = 3


# =========================================================
# PRODUCT VARIANT INLINE
# =========================================================

class ProductVariantInline(admin.TabularInline):

    model = ProductVariant
    extra = 1

    fields = (
        "sku",
        "variant_type",
        "value",
        "price",
        "stock",
        "image",
        "is_active",
    )

    readonly_fields = (
        "sku",
    )


# =========================================================
# PRODUCT
# =========================================================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        "sku",
        "name",
        "category",
        "sale_price",
        "stock",
        "is_active",
    )

    search_fields = (
        "sku",
        "name",
    )
    filter_horizontal = (
        "upsell_products",
        "cross_sell_products",
    )
    list_filter = (
        "category",
        "is_active",
    )
    fields = (
        # =========================
        # THÔNG TIN CHUNG
        # =========================
        "sku",
        "name",
        "category",
        "gender",
        "original_price",
        "sale_price",
        "stock",
        "description",
        "image",
        "is_active",
        "is_featured",

        # =========================
        # THÔNG TIN GỌNG KÍNH
        # =========================
        "frame_shape",
        "material",
        "color",
        "size",

        # =========================
        # THÔNG TIN TRÒNG KÍNH
        # =========================
        "lens_type",
        "lens_index",
        "lens_feature",
        "lens_diameter",

        # =========================
        # SẢN PHẨM ĐỀ XUẤT
        # =========================
        "upsell_products",
        "cross_sell_products",
    )

    inlines = [
        ProductImageInline,
        ProductVariantInline,
    ]

    class Media:
        js = (
            "js/product_category_fields.js",
        )

    def changelist_view(
        self,
        request,
        extra_context=None
    ):

        extra_context = extra_context or {}

        extra_context[
            "recognition_url"
        ] = reverse(
            "admin:product_image_recognition"
        )

        return super().changelist_view(
            request,
            extra_context=extra_context,
        )

    # =====================================================
    # CUSTOM URL CHO TÌM KÍNH BẰNG HÌNH ẢNH
    # =====================================================

    def get_urls(self):

        urls = super().get_urls()

        custom_urls = [

            path(
                "tim-kinh/",
                self.admin_site.admin_view(
                    views.admin_product_recognition
                ),
                name="product_image_recognition",
            ),

            path(
                "tim-kinh/cap-nhat/",
                self.admin_site.admin_view(
                    views.admin_product_recognition_update
                ),
                name="product_image_recognition_update",
            ),

            path(
                "tim-kinh/them-moi/",
                self.admin_site.admin_view(
                    views.admin_product_recognition_create
                ),
                name="product_image_recognition_create",
            ),

        ]

        return custom_urls + urls


# =========================================================
# PRODUCT VARIANT
# =========================================================

@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):

    list_display = (
        "product",
        "sku",
        "variant_type",
        "value",
        "price",
        "stock",
        "is_active",
    )

    search_fields = (
        "product__name",
        "sku",
        "value",
    )

    list_filter = (
        "variant_type",
        "is_active",
    )

# =========================================================
# CONTACT MESSAGE
# =========================================================

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "phone",
        "email",
        "source",
        "message",
        "created_at",
        "is_read",
    )

    list_filter = (
        "source",
        "is_read",
        "created_at",
    )

    search_fields = (
        "name",
        "phone",
        "email",
        "message",
    )

    list_editable = (
        "is_read",
    )


# =========================================================
# PRODUCT REVIEW
# =========================================================

@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):

    list_display = (
        "reviewer_name",
        "product",
        "rating",
        "created_at",
        "is_approved",
    )

    list_filter = (
        "rating",
        "is_approved",
        "created_at",
    )

    search_fields = (
        "reviewer_name",
        "product__name",
        "comment",
    )

    list_editable = (
        "is_approved",
    )

    readonly_fields = (
        "created_at",
    )


# =========================================================
# ORDER ITEM INLINE
# =========================================================

class OrderItemInline(admin.TabularInline):

    model = OrderItem
    extra = 0

    fields = (
        "product",
        "variant",
        "product_name",
        "variant_name",
        "price",
        "quantity",
        "line_total",
    )

    readonly_fields = (
        "product_name",
        "variant_name",
        "price",
        "quantity",
        "line_total",
    )


# =========================================================
# ORDER
# =========================================================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        "order_code",
        "full_name",
        "phone",
        "payment_method",
        "payment_status",
        "status",
        "total",
        "created_at",
    )

    list_filter = (
        "payment_method",
        "payment_status",
        "status",
        "created_at",
    )

    search_fields = (
        "order_code",
        "full_name",
        "phone",
        "email",
        "address",
    )

    readonly_fields = (
        "order_code",
        "created_at",
        "updated_at",
        "subtotal",
        "shipping_fee",
        "total",
    )

    list_editable = (
        "payment_status",
        "status",
    )

    inlines = [
        OrderItemInline,
    ]

    fieldsets = (

        (
            "Thông tin đơn hàng",
            {
                "fields": (
                    "order_code",
                    "created_at",
                    "updated_at",
                    "status",
                )
            },
        ),

        (
            "Thông tin khách hàng",
            {
                "fields": (
                    "full_name",
                    "phone",
                    "email",
                    "address",
                    "note",
                )
            },
        ),

        (
            "Thanh toán",
            {
                "fields": (
                    "payment_method",
                    "payment_status",
                )
            },
        ),

        (
            "Giá trị đơn hàng",
            {
                "fields": (
                    "subtotal",
                    "shipping_fee",
                    "total",
                )
            },
        ),

    )


    # =====================================================
    # TỰ ĐỘNG PHÁT HÀNH MÃ 25% SAU KHI HOÀN THÀNH ĐƠN
    # =====================================================

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.status != "completed":
            return

        reward_result = _sync_customer_reward_after_completed_order(
            obj
        )

        customer = reward_result.get("customer")

        if customer is None:
            self.message_user(
                request,
                (
                    "Đơn đã được lưu ở trạng thái Đã hoàn thành, "
                    "nhưng chưa tìm thấy Khách hàng ưu đãi có "
                    "số điện thoại/email tương ứng."
                ),
                level=messages.WARNING,
            )
            return

        created_coupon = reward_result.get(
            "created_second_coupon"
        )

        if created_coupon:
            self.message_user(
                request,
                (
                    f"Đơn đầu của {customer.name} đã hoàn thành. "
                    f"Đã tạo mã {created_coupon.code} giảm 25% "
                    "cho lần mua tiếp theo."
                ),
                level=messages.SUCCESS,
            )
        elif customer.second_order_completed:
            self.message_user(
                request,
                (
                    f"{customer.name} đã có từ 2 đơn hoàn thành. "
                    "Đã cập nhật trạng thái khách quay lại."
                ),
                level=messages.SUCCESS,
            )



# =========================================================
# PROMOTION CUSTOMER
# =========================================================

@admin.register(PromotionCustomer)
class PromotionCustomerAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "phone",
        "age_group",
        "gender",
        "price_range",
        "first_order_completed",
        "second_order_completed",
        "second_coupon_status",
        "created_at",
    )

    search_fields = (
        "name",
        "phone",
        "email",
    )

    list_filter = (
        "age_group",
        "gender",
        "price_range",
        "first_order_completed",
        "second_order_completed",
        "created_at",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


    @admin.display(description="Ưu đãi 25%")
    def second_coupon_status(self, obj):
        coupon = (
            obj.coupons
            .filter(
                coupon_type="SECOND"
            )
            .order_by("-created_at")
            .first()
        )

        if coupon is None:
            return "Chưa có"

        if coupon.is_used:
            return f"{coupon.code} - Đã dùng"

        if not coupon.is_active:
            return f"{coupon.code} - Đã khóa"

        return f"{coupon.code} - Sẵn sàng"



# =========================================================
# DISCOUNT COUPON
# =========================================================

@admin.register(DiscountCoupon)
class DiscountCouponAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "customer",
        "coupon_type",
        "discount_percent",
        "is_used",
        "is_active",
        "created_at",
    )

    search_fields = (
        "code",
        "customer__name",
        "customer__phone",
    )

    list_filter = (
        "coupon_type",
        "discount_percent",
        "is_used",
        "is_active",
        "created_at",
    )

    readonly_fields = (
        "created_at",
        "used_at",
    )


# =========================================================
# MINOO ADMIN CONFIG
# =========================================================

admin.site.site_header = "MINOO ADMIN"
admin.site.site_title = "MINOO ADMIN"
admin.site.index_title = (
    "Hệ thống quản trị Minoo Eyewear"
)


# =========================================================
# DASHBOARD HELPERS
# =========================================================

def _format_vnd(value):

    value = value or Decimal("0")

    try:
        number = int(value)
    except (
        TypeError,
        ValueError,
    ):
        number = 0

    return (
        f"{number:,}"
        .replace(",", ".")
        + "đ"
    )


def _choice_count_data(
    queryset,
    field_name,
    choices,
):

    counts = {
        row[field_name]: row["total"]
        for row in (
            queryset
            .values(field_name)
            .annotate(
                total=Count("id")
            )
        )
    }

    return {
        "labels": [
            label
            for value, label in choices
        ],
        "values": [
            counts.get(
                value,
                0
            )
            for value, label in choices
        ],
    }


def _build_dashboard_data():

    customers = (
        PromotionCustomer.objects
        .all()
    )

    valid_orders = (
        Order.objects
        .exclude(
            status="cancelled"
        )
    )

    completed_orders = (
        valid_orders
        .filter(
            status="completed"
        )
    )

    coupons = (
        DiscountCoupon.objects
        .all()
    )


    # =====================================================
    # KPI
    # =====================================================

    total_customers = (
        customers.count()
    )

    total_orders = (
        valid_orders.count()
    )

    order_value = (
        valid_orders
        .aggregate(
            value=Sum("total")
        )["value"]
        or Decimal("0")
    )

    completed_revenue = (
        completed_orders
        .aggregate(
            value=Sum("total")
        )["value"]
        or Decimal("0")
    )

    average_order_value = (
        valid_orders
        .aggregate(
            value=Avg("total")
        )["value"]
        or Decimal("0")
    )


    # =====================================================
    # KHÁCH HÀNG
    # =====================================================

    gender_data = (
        _choice_count_data(
            customers,
            "gender",
            PromotionCustomer.GENDER_CHOICES,
        )
    )

    age_data = (
        _choice_count_data(
            customers,
            "age_group",
            PromotionCustomer.AGE_CHOICES,
        )
    )

    price_data = (
        _choice_count_data(
            customers,
            "price_range",
            PromotionCustomer.PRICE_CHOICES,
        )
    )


    # =====================================================
    # KHÁCH HÀNG MỚI THEO THÁNG
    # =====================================================

    today = (
        timezone.localdate()
    )

    start_date = (
        today.replace(
            day=1
        )
        - timedelta(
            days=155
        )
    )

    monthly_rows = list(
        customers
        .filter(
            created_at__date__gte=start_date
        )
        .annotate(
            month=TruncMonth(
                "created_at"
            )
        )
        .values(
            "month"
        )
        .annotate(
            total=Count(
                "id"
            )
        )
        .order_by(
            "month"
        )
    )

    customer_month_labels = [
        row["month"].strftime(
            "%m/%Y"
        )
        for row in monthly_rows
        if row["month"]
    ]

    customer_month_values = [
        row["total"]
        for row in monthly_rows
        if row["month"]
    ]


    # =====================================================
    # COUPON 20%
    # =====================================================

    first_coupons = (
        coupons.filter(
            coupon_type="FIRST"
        )
    )

    coupon_20_total = (
        first_coupons.count()
    )

    coupon_20_used = (
        first_coupons
        .filter(
            is_used=True
        )
        .count()
    )

    if coupon_20_total:

        coupon_20_rate = round(
            (
                coupon_20_used
                / coupon_20_total
            )
            * 100,
            1
        )

    else:

        coupon_20_rate = 0


    # =====================================================
    # COUPON 25%
    # =====================================================

    second_coupons = (
        coupons.filter(
            coupon_type="SECOND"
        )
    )

    coupon_25_total = (
        second_coupons.count()
    )

    coupon_25_used = (
        second_coupons
        .filter(
            is_used=True
        )
        .count()
    )

    coupon_25_active = (
        second_coupons
        .filter(
            is_used=False,
            is_active=True,
        )
        .count()
    )

    if coupon_25_total:

        coupon_25_rate = round(
            (
                coupon_25_used
                / coupon_25_total
            )
            * 100,
            1
        )

    else:

        coupon_25_rate = 0


    # =====================================================
    # KHÁCH QUAY LẠI
    # =====================================================

    first_order_customers = (
        customers
        .filter(
            first_order_completed=True
        )
        .count()
    )

    returning_customers = (
        customers
        .filter(
            second_order_completed=True
        )
        .count()
    )

    if first_order_customers:

        returning_customer_rate = round(
            (
                returning_customers
                / first_order_customers
            )
            * 100,
            1
        )

    else:

        returning_customer_rate = 0


    # =====================================================
    # TOP SẢN PHẨM
    # =====================================================

    top_products = list(
        OrderItem.objects
        .exclude(
            order__status="cancelled"
        )
        .values(
            "product_name"
        )
        .annotate(
            quantity=Sum(
                "quantity"
            ),
            sales=Sum(
                "line_total"
            ),
        )
        .order_by(
            "-quantity"
        )[:5]
    )

    for row in top_products:

        row[
            "sales_display"
        ] = _format_vnd(
            row.get(
                "sales"
            )
        )


    # =====================================================
    # ĐƠN HÀNG GẦN ĐÂY
    # =====================================================

    recent_orders = list(
        valid_orders
        .order_by(
            "-created_at"
        )[:8]
    )

    for order in recent_orders:

        order.total_display = (
            _format_vnd(
                order.total
            )
        )


    return {

        "total_customers":
            total_customers,

        "total_orders":
            total_orders,

        "order_value":
            _format_vnd(
                order_value
            ),

        "completed_revenue":
            _format_vnd(
                completed_revenue
            ),

        "average_order_value":
            _format_vnd(
                average_order_value
            ),

        "gender_labels":
            gender_data[
                "labels"
            ],

        "gender_values":
            gender_data[
                "values"
            ],

        "age_labels":
            age_data[
                "labels"
            ],

        "age_values":
            age_data[
                "values"
            ],

        "price_labels":
            price_data[
                "labels"
            ],

        "price_values":
            price_data[
                "values"
            ],

        "customer_month_labels":
            customer_month_labels,

        "customer_month_values":
            customer_month_values,

        "coupon_20_total":
            coupon_20_total,

        "coupon_20_used":
            coupon_20_used,

        "coupon_20_rate":
            coupon_20_rate,

        "coupon_25_total":
            coupon_25_total,

        "coupon_25_used":
            coupon_25_used,

        "coupon_25_active":
            coupon_25_active,

        "coupon_25_rate":
            coupon_25_rate,

        "first_order_customers":
            first_order_customers,

        "returning_customers":
            returning_customers,

        "returning_customer_rate":
            returning_customer_rate,

        "top_products":
            top_products,

        "recent_orders":
            recent_orders,
    }


# =========================================================
# DASHBOARD VIEW RIÊNG
# =========================================================

def minoo_dashboard_view(request):

    context = {
        **admin.site.each_context(
            request
        ),

        "title":
            "Dashboard MINOO",

        "minoo_dashboard":
            _build_dashboard_data(),
    }

    return TemplateResponse(
        request,
        "admin/dashboard.html",
        context,
    )


# =========================================================
# THÊM URL /admin/dashboard/
# =========================================================

_original_admin_get_urls = (
    admin.site.get_urls
)


def minoo_admin_get_urls():

    custom_urls = [

        path(
            "dashboard/",
            admin.site.admin_view(
                minoo_dashboard_view
            ),
            name="minoo_dashboard",
        ),

    ]

    return (
        custom_urls
        + _original_admin_get_urls()
    )


admin.site.get_urls = (
    minoo_admin_get_urls
)


# =========================================================
# THÊM "DASHBOARD" VÀO NHÓM STORE Ở MENU BÊN TRÁI
# =========================================================

_original_admin_get_app_list = (
    admin.site.get_app_list
)


def minoo_admin_get_app_list(
    request,
    app_label=None
):

    app_list = (
        _original_admin_get_app_list(
            request,
            app_label
        )
    )

    dashboard_url = reverse(
        "admin:minoo_dashboard"
    )

    for app in app_list:

        if app.get(
            "app_label"
        ) == "store":

            # Tránh thêm trùng nếu Django gọi nhiều lần.
            already_exists = any(
                model.get(
                    "object_name"
                ) == "MinooDashboard"
                for model in app.get(
                    "models",
                    []
                )
            )

            if not already_exists:

                app[
                    "models"
                ].append(
                    {
                        "name":
                            "Dashboard",

                        "object_name":
                            "MinooDashboard",

                        "perms": {
                            "add": False,
                            "change": False,
                            "delete": False,
                            "view": True,
                        },

                        "admin_url":
                            dashboard_url,

                        "add_url":
                            None,

                        "view_only":
                            True,
                    }
                )

            break

    return app_list


admin.site.get_app_list = (
    minoo_admin_get_app_list
)
