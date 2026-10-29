# =========================================================
# MINOO EYEWEAR
# STORE VIEWS
# =========================================================

from decimal import Decimal, InvalidOperation
from urllib.parse import quote
from pathlib import Path
import uuid

from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET


import imagehash

from PIL import Image, UnidentifiedImageError

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.files import File
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Avg, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone

from .forms import (
    ContactForm,
    AdminProductRecognitionCreateForm,
)

from .models import (
    Category,
    ContactMessage,
    Product,
    ProductImage,
    ProductReview,
    ProductVariant,
    Order,
    OrderItem,
    PromotionCustomer,
    DiscountCoupon,
)
from django.contrib.auth import (
    authenticate,
    login,
    logout,
)
from django.contrib.auth.models import User

from django.contrib.auth.decorators import (
    login_required,
)

from django.contrib import messages

from django.shortcuts import (
    render,
    redirect,
)

from django.utils.http import (
    url_has_allowed_host_and_scheme,
)

from .forms import RegisterForm

from .image_similarity import find_similar_products

import hashlib
import hmac
import json
import time
from django.conf import settings
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import SePayTransaction
# =========================================================
# CẤU HÌNH
# =========================================================

FREE_SHIPPING_THRESHOLD = Decimal("500000")
STANDARD_SHIPPING_FEE = Decimal("30000")

RECOGNITION_UPLOAD_DIR = "admin_recognition"
CUSTOMER_VISUAL_SEARCH_UPLOAD_DIR = "customer_visual_search"
MAX_VISUAL_SEARCH_UPLOAD_SIZE = 8 * 1024 * 1024  # 8 MB

MATCH_DISTANCE_THRESHOLD = 12


# =========================================================
# TÍNH PHÍ VẬN CHUYỂN
# =========================================================

def calculate_shipping_fee(subtotal):
    """
    Tính phí vận chuyển:

    - Đơn từ 500.000đ trở lên: miễn phí
    - Đơn dưới 500.000đ: 30.000đ
    - Không có sản phẩm: 0đ
    """

    subtotal = Decimal(
        str(subtotal or 0)
    )

    if subtotal <= 0:
        return Decimal("0")

    if subtotal >= FREE_SHIPPING_THRESHOLD:
        return Decimal("0")

    return STANDARD_SHIPPING_FEE



# =========================================================
# KHÔI PHỤC / ĐỒNG BỘ MÃ GIẢM GIÁ CỦA KHÁCH
# =========================================================

def get_customer_available_coupon(request):
    """
    Đồng bộ coupon theo đúng vòng đời khách hàng:

    - Chưa hoàn thành đơn đầu:
        ưu tiên coupon FIRST 20%.
    - Đã hoàn thành đơn đầu nhưng chưa hoàn thành đơn thứ hai:
        ưu tiên coupon SECOND 25%.
    - Đã hoàn thành đơn thứ hai:
        không còn coupon cho chương trình này.

    Khách chỉ cần điền form ưu đãi một lần. Hệ thống cố gắng
    nhận diện lại khách bằng:
        1) tài khoản đang đăng nhập;
        2) promotion_customer_id trong session;
        3) coupon hiện có trong session;
        4) email của tài khoản nếu hồ sơ chưa liên kết user.

    Nếu coupon thay đổi từ 20% sang 25%, trạng thái
    applied_coupon_code cũ sẽ được gỡ để khách chủ động áp dụng
    mã mới ở checkout.
    """

    customer = None

    # =====================================================
    # 1. ƯU TIÊN HỒ SƠ ĐÃ LIÊN KẾT VỚI TÀI KHOẢN
    # =====================================================

    if request.user.is_authenticated:

        customer = (
            PromotionCustomer.objects
            .filter(
                user=request.user
            )
            .first()
        )

    # =====================================================
    # 2. TÌM HỒ SƠ TỪ SESSION
    # =====================================================

    if customer is None:

        promotion_customer_id = (
            request.session.get(
                "promotion_customer_id"
            )
        )

        if promotion_customer_id:

            session_customer = (
                PromotionCustomer.objects
                .filter(
                    id=promotion_customer_id
                )
                .first()
            )

            if session_customer:

                # Nếu profile đã thuộc tài khoản khác thì bỏ qua.
                if (
                    request.user.is_authenticated
                    and session_customer.user_id
                    and session_customer.user_id
                    != request.user.id
                ):

                    session_customer = None

                if session_customer:

                    customer = session_customer

    # =====================================================
    # 3. TÌM HỒ SƠ TỪ COUPON ĐANG LƯU TRONG SESSION
    # =====================================================

    if customer is None:

        coupon_code = request.session.get(
            "discount_coupon_code"
        )

        if coupon_code:

            session_coupon = (
                DiscountCoupon.objects
                .filter(
                    code=coupon_code
                )
                .select_related(
                    "customer"
                )
                .first()
            )

            if session_coupon:

                session_customer = (
                    session_coupon.customer
                )

                if (
                    request.user.is_authenticated
                    and session_customer.user_id
                    and session_customer.user_id
                    != request.user.id
                ):

                    session_customer = None

                if session_customer:

                    customer = session_customer

    # =====================================================
    # 4. TÌM THEO EMAIL ĐĂNG NHẬP NẾU PROFILE CHƯA GẮN USER
    # =====================================================

    if (
        customer is None
        and request.user.is_authenticated
        and request.user.email
    ):

        email_customer = (
            PromotionCustomer.objects
            .filter(
                email__iexact=(
                    request.user.email.strip()
                ),
                user__isnull=True,
            )
            .first()
        )

        if email_customer:

            user_has_profile = (
                PromotionCustomer.objects
                .filter(
                    user=request.user
                )
                .exists()
            )

            if not user_has_profile:

                email_customer.user = (
                    request.user
                )

                email_customer.save(
                    update_fields=[
                        "user"
                    ]
                )

                customer = email_customer

    # =====================================================
    # CHƯA CÓ HỒ SƠ ƯU ĐÃI
    # =====================================================

    if customer is None:

        request.session.pop(
            "discount_coupon_code",
            None
        )

        request.session.pop(
            "applied_coupon_code",
            None
        )

        request.session.modified = True

        return None

    # Giữ lại hồ sơ khách trong session.
    request.session[
        "promotion_customer_id"
    ] = customer.id

    # =====================================================
    # XÁC ĐỊNH COUPON ĐÚNG THEO GIAI ĐOẠN
    # =====================================================

    desired_coupon_type = None

    if customer.second_order_completed:

        desired_coupon_type = None

    elif customer.first_order_completed:

        desired_coupon_type = "SECOND"

    else:

        desired_coupon_type = "FIRST"

    coupon = None

    if desired_coupon_type:

        coupon = (
            DiscountCoupon.objects
            .filter(
                customer=customer,
                coupon_type=desired_coupon_type,
                is_active=True,
                is_used=False,
            )
            .order_by(
                "-created_at"
            )
            .first()
        )

    old_coupon_code = request.session.get(
        "discount_coupon_code"
    )

    # =====================================================
    # KHÔNG CÒN COUPON HỢP LỆ
    # =====================================================

    if coupon is None:

        request.session.pop(
            "discount_coupon_code",
            None
        )

        request.session.pop(
            "applied_coupon_code",
            None
        )

        # CỐ Ý KHÔNG XÓA promotion_customer_id.
        # Nhờ vậy khách không phải nhập lại form ưu đãi.
        request.session.modified = True

        return None

    # =====================================================
    # CÓ COUPON HỢP LỆ
    # =====================================================

    request.session[
        "discount_coupon_code"
    ] = coupon.code

    # Nếu hệ thống vừa chuyển từ mã 20% sang mã 25%,
    # gỡ trạng thái áp dụng của mã cũ.
    if (
        old_coupon_code
        and old_coupon_code != coupon.code
    ):

        request.session.pop(
            "applied_coupon_code",
            None
        )

    request.session.modified = True

    return coupon



# =========================================================
# TRANG CHỦ
# =========================================================

def home(request):
    products = (
        Product.objects
        .filter(
            is_active=True,
            is_featured=True,
            category__name__iexact="Gọng kính",
        )
        .filter(
            Q(stock__gt=0)
            |
            Q(
                variants__is_active=True,
                variants__stock__gt=0
            )
        )
        .select_related("category")
        .prefetch_related(
            "images",
            "variants",
        )
        .distinct()[:8]
    )

    categories = Category.objects.all()

    return render(
        request,
        "home.html",
        {
            "products": products,
            "categories": categories,
        }
    )


# =========================================================
# DANH SÁCH SẢN PHẨM
# =========================================================


# =========================================================
# DANH SÁCH SẢN PHẨM
# =========================================================

def products(request):
    min_price_raw = request.GET.get("min_price", "").strip()
    max_price_raw = request.GET.get("max_price", "").strip()
    product_list = (
        Product.objects
        .filter(is_active=True)
        .filter(
            category__name__icontains="gọng"
        )
        .select_related("category")
        .prefetch_related("images", "variants")
    )

    categories = Category.objects.all()

    # Giới hạn giá tối đa của toàn bộ danh sách gọng kính,
    # không phụ thuộc vào kết quả lọc hiện tại.
    price_max_limit = (
        Product.objects
        .filter(
            is_active=True,
            category__name__icontains="gọng",
        )
        .order_by("-sale_price")
        .values_list("sale_price", flat=True)
        .first()
        or 1000000
    )

    # =====================================================
    # TÌM KIẾM SẢN PHẨM
    # =====================================================

    q = request.GET.get("q", "").strip()

    if q:
        product_list = (
            product_list
            .filter(
                Q(name__icontains=q)
                | Q(sku__icontains=q)
                | Q(category__name__icontains=q)
                | Q(frame_shape__icontains=q)
                | Q(material__icontains=q)
                | Q(color__icontains=q)
                | Q(size__icontains=q)
                | Q(lens_type__icontains=q)
                | Q(lens_index__icontains=q)
                | Q(lens_feature__icontains=q)
                | Q(lens_diameter__icontains=q)
                | Q(description__icontains=q)
            )
            .distinct()
        )

    # =====================================================
    # LỌC THEO GIỚI TÍNH - NEW
    # =====================================================

    selected_gender = request.GET.get(
        "gender", ""
    ).strip().lower()

    if selected_gender not in ["male", "female", "unisex"]:
        selected_gender = ""

    if selected_gender:
        product_list = product_list.filter(
            gender=selected_gender
        )

    # =====================================================
    # DANH MỤC
    # =====================================================

    category = request.GET.get("category", "").strip()

    if category:
        product_list = product_list.filter(
            category_id=category
        )

    # =====================================================
    # KIỂU GỌNG
    # =====================================================

    shape = request.GET.get("shape", "").strip()

    if shape:
        product_list = product_list.filter(
            frame_shape__icontains=shape
        )


    # =====================================================
    # LỌC THEO KHOẢNG GIÁ
    # =====================================================

    from decimal import Decimal, InvalidOperation

    min_price_raw = request.GET.get("min_price", "").strip()
    max_price_raw = request.GET.get("max_price", "").strip()

    min_price = None
    max_price = None

    try:
        if min_price_raw:
            min_price = Decimal(min_price_raw)
            if not min_price.is_finite() or min_price < 0:
                min_price = None
    except (InvalidOperation, ValueError):
        min_price = None

    try:
        if max_price_raw:
            max_price = Decimal(max_price_raw)
            if not max_price.is_finite() or max_price < 0:
                max_price = None
    except (InvalidOperation, ValueError):
        max_price = None

    # Đổi vị trí nếu giá tối thiểu lớn hơn giá tối đa
    if (
        min_price is not None
        and max_price is not None
        and min_price > max_price
    ):
        min_price, max_price = max_price, min_price

    # Áp dụng lọc vào QuerySet hiện tại
    if min_price is not None:
        product_list = product_list.filter(
            sale_price__gte=min_price
        )

    if max_price is not None:
        product_list = product_list.filter(
            sale_price__lte=max_price
        )


    # =====================================================
    # SẮP XẾP
    # =====================================================

    sort = request.GET.get("sort", "").strip()

    if sort == "price_asc":
        product_list = product_list.order_by("sale_price")

    elif sort == "price_desc":
        product_list = product_list.order_by("-sale_price")

    elif sort == "newest":
        product_list = product_list.order_by("-created_at")

    else:
        product_list = product_list.order_by("-created_at")

    # =====================================================
    # RENDER
    # =====================================================

    return render(
        request,
        "products.html",
        {
            "products": product_list,
            "categories": categories,
            "price_max_limit": price_max_limit,
            "q": q,
            "selected_gender": selected_gender,
            "selected_category": category,
            "selected_shape": shape,
            "selected_sort": sort,
            "result_count": product_list.count(),
            "min_price": (
                str(min_price) if min_price is not None else ""
            ),
            "max_price": (
                str(max_price) if max_price is not None else ""
            ),
        }
    )



# =========================================================
# CHI TIẾT SẢN PHẨM
# =========================================================


def product_detail(
    request,
    product_id
):

    product = get_object_or_404(
        Product.objects
        .select_related("category")
        .prefetch_related(
            "images",
            "variants",
        ),
        id=product_id,
        is_active=True,
    )
    upsell_products = (
        product.upsell_products
        .filter(is_active=True)
        .exclude(id=product.id)
        .order_by("-created_at")[:4]
    )

    cross_sell_products = (
        product.cross_sell_products
        .filter(is_active=True)
        .exclude(id=product.id)
        .order_by("-created_at")[:4]
    )
    # =====================================================
    # ẢNH CHI TIẾT SẢN PHẨM
    # =====================================================

    related_images = (
        product.images
        .all()
        .order_by("order")
    )

    # =====================================================
    # BIẾN THỂ SẢN PHẨM
    # =====================================================

    variants = (
        ProductVariant.objects
        .filter(
            product=product,
            is_active=True,
        )
        .order_by(
            "color",
        )
    )

    # =====================================================
    # REVIEW
    # =====================================================

    reviews = (
        ProductReview.objects
        .filter(
            product=product,
            is_approved=True,
        )
        .order_by(
            "-created_at"
        )
    )

    total_reviews = reviews.count()

    review_average = (
        reviews.aggregate(
            average=Avg("rating")
        )["average"]
        or 0
    )

    # =====================================================
    # RENDER
    # =====================================================

    return render(
        request,
        "product_detail.html",
        {
            "product": product,

            # Ảnh chi tiết
            "related_images": related_images,

            # Biến thể
            "variants": variants,

            # Đánh giá
            "reviews": reviews,
            "average_rating": review_average,
            "total_reviews": total_reviews,
            "upsell_products": upsell_products,
            "cross_sell_products": cross_sell_products,
        }
    )


# =========================================================
# THÊM VÀO GIỎ HÀNG
# =========================================================

def add_to_cart(
    request,
    product_id
):

    if request.method != "POST":

        return redirect(
            "product_detail",
            product_id=product_id
        )

    # =====================================================
    # XÁC ĐỊNH TRANG CẦN QUAY LẠI
    # =====================================================

    next_url = request.POST.get(
        "next",
        ""
    ).strip()

    referer_url = request.META.get(
        "HTTP_REFERER",
        ""
    ).strip()

    # Ưu tiên next nếu là URL nội bộ hợp lệ
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):

        return_url = next_url

    # Nếu không có next thì dùng trang trước đó
    elif referer_url and url_has_allowed_host_and_scheme(
        referer_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):

        return_url = referer_url

    # Không xác định được thì quay về chi tiết sản phẩm
    else:

        return_url = None

    # =====================================================
    # LẤY SẢN PHẨM
    # =====================================================

    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True,
    )

    variant_id = request.POST.get(
        "variant_id"
    )

    quantity_raw = request.POST.get(
        "quantity",
        "1"
    )

    # =====================================================
    # SỐ LƯỢNG
    # =====================================================

    try:

        quantity = int(
            quantity_raw
        )

    except (
        ValueError,
        TypeError,
    ):

        quantity = 1

    if quantity < 1:

        quantity = 1

    # =====================================================
    # GIỎ HÀNG
    # =====================================================

    cart = request.session.get(
        "cart",
        {}
    )

    # =====================================================
    # SẢN PHẨM CÓ BIẾN THỂ
    # =====================================================

    if product.has_variants:

        # -------------------------------------------------
        # CHƯA CHỌN BIẾN THỂ
        # -------------------------------------------------

        if not variant_id:

            messages.warning(
                request,
                "Vui lòng chọn biến thể sản phẩm trước khi thêm vào giỏ."
            )

            if return_url:

                return redirect(
                    return_url
                )

            return redirect(
                "product_detail",
                product_id=product.id
            )

        # -------------------------------------------------
        # LẤY BIẾN THỂ
        # -------------------------------------------------

        variant = get_object_or_404(
            ProductVariant,
            id=variant_id,
            product=product,
            is_active=True,
        )

        # -------------------------------------------------
        # KIỂM TRA TỒN KHO
        # -------------------------------------------------

        if variant.stock <= 0:

            messages.error(
                request,
                "Biến thể bạn chọn hiện đã hết hàng."
            )

            if return_url:

                return redirect(
                    return_url
                )

            return redirect(
                "product_detail",
                product_id=product.id
            )

        if quantity > variant.stock:

            messages.warning(
                request,
                f"Biến thể chỉ còn {variant.stock} sản phẩm."
            )

            if return_url:

                return redirect(
                    return_url
                )

            return redirect(
                "product_detail",
                product_id=product.id
            )

        # -------------------------------------------------
        # KEY GIỎ HÀNG
        # -------------------------------------------------

        cart_key = (
            f"{product.id}_{variant.id}"
        )

        # -------------------------------------------------
        # ĐÃ CÓ TRONG GIỎ
        # -------------------------------------------------

        if cart_key in cart:

            current_quantity = int(
                cart[cart_key].get(
                    "quantity",
                    0
                )
            )

            new_quantity = (
                current_quantity
                + quantity
            )

            if new_quantity > variant.stock:

                messages.warning(
                    request,
                    f"Chỉ còn {variant.stock} sản phẩm trong kho."
                )

                if return_url:

                    return redirect(
                        return_url
                    )

                return redirect(
                    "product_detail",
                    product_id=product.id
                )

            cart[cart_key][
                "quantity"
            ] = new_quantity

        # -------------------------------------------------
        # CHƯA CÓ TRONG GIỎ
        # -------------------------------------------------

        else:

            cart[cart_key] = {
                "product_id": product.id,
                "variant_id": variant.id,
                "quantity": quantity,
            }

    # =====================================================
    # SẢN PHẨM KHÔNG CÓ BIẾN THỂ
    # =====================================================

    else:

        # -------------------------------------------------
        # KIỂM TRA TỒN KHO
        # -------------------------------------------------

        if product.stock <= 0:

            messages.error(
                request,
                "Sản phẩm hiện đã hết hàng."
            )

            if return_url:

                return redirect(
                    return_url
                )

            return redirect(
                "product_detail",
                product_id=product.id
            )

        if quantity > product.stock:

            messages.warning(
                request,
                f"Sản phẩm chỉ còn {product.stock} sản phẩm."
            )

            if return_url:

                return redirect(
                    return_url
                )

            return redirect(
                "product_detail",
                product_id=product.id
            )

        # -------------------------------------------------
        # KEY GIỎ HÀNG
        # -------------------------------------------------

        cart_key = str(
            product.id
        )

        # -------------------------------------------------
        # ĐÃ CÓ TRONG GIỎ
        # -------------------------------------------------

        if cart_key in cart:

            current_quantity = int(
                cart[cart_key].get(
                    "quantity",
                    0
                )
            )

            new_quantity = (
                current_quantity
                + quantity
            )

            if new_quantity > product.stock:

                messages.warning(
                    request,
                    f"Chỉ còn {product.stock} sản phẩm trong kho."
                )

                if return_url:

                    return redirect(
                        return_url
                    )

                return redirect(
                    "product_detail",
                    product_id=product.id
                )

            cart[cart_key][
                "quantity"
            ] = new_quantity

        # -------------------------------------------------
        # CHƯA CÓ TRONG GIỎ
        # -------------------------------------------------

        else:

            cart[cart_key] = {
                "product_id": product.id,
                "variant_id": None,
                "quantity": quantity,
            }

    # =====================================================
    # LƯU GIỎ HÀNG
    # =====================================================

    request.session["cart"] = cart

    # Sản phẩm được thêm vào giỏ → checkout theo giỏ hàng
    request.session["checkout_mode"] = "cart"

    # Xóa dữ liệu Mua ngay cũ
    request.session.pop(
        "buy_now_item",
        None
    )

    request.session.modified = True

    # =====================================================
    # THÔNG BÁO
    # =====================================================

    messages.success(
        request,
        f"Đã thêm '{product.name}' vào giỏ hàng."
    )

    # =====================================================
    # QUAY LẠI TRANG TRƯỚC ĐÓ
    # =====================================================

    if return_url:

        return redirect(
            return_url
        )

    return redirect(
        "product_detail",
        product_id=product.id
    )


# =========================================================
# MUA NGAY
# =========================================================

def buy_now(
    request,
    product_id
):

    if request.method != "POST":

        return redirect(
            "product_detail",
            product_id=product_id
        )

    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True,
    )

    variant_id = request.POST.get(
        "variant_id"
    )

    quantity_raw = request.POST.get(
        "quantity",
        "1"
    )

    try:

        quantity = int(
            quantity_raw
        )

    except (
        ValueError,
        TypeError,
    ):

        quantity = 1

    if quantity < 1:
        quantity = 1

    variants = ProductVariant.objects.filter(
        product=product,
        is_active=True,
    )

    # =====================================================
    # CÓ BIẾN THỂ
    # =====================================================

    if variants.exists():

        if not variant_id:

            messages.warning(
                request,
                "Vui lòng chọn biến thể sản phẩm trước khi mua."
            )

            return redirect(
                "product_detail",
                product_id=product_id
            )

        variant = get_object_or_404(
            ProductVariant,
            id=variant_id,
            product=product,
            is_active=True,
        )

        if variant.stock <= 0:

            messages.error(
                request,
                "Biến thể bạn chọn hiện đã hết hàng."
            )

            return redirect(
                "product_detail",
                product_id=product_id
            )

        if quantity > variant.stock:

            messages.warning(
                request,
                f"Biến thể chỉ còn {variant.stock} sản phẩm."
            )

            return redirect(
                "product_detail",
                product_id=product_id
            )

    # =====================================================
    # KHÔNG CÓ BIẾN THỂ
    # =====================================================

    else:

        variant_id = None

        if product.stock <= 0:

            messages.error(
                request,
                "Sản phẩm hiện đã hết hàng."
            )

            return redirect(
                "product_detail",
                product_id=product_id
            )

        if quantity > product.stock:

            messages.warning(
                request,
                f"Sản phẩm chỉ còn {product.stock} sản phẩm."
            )

            return redirect(
                "product_detail",
                product_id=product_id
            )

    # =====================================================
    # LƯU SẢN PHẨM MUA NGAY
    # =====================================================

    request.session["buy_now_item"] = {
        "product_id": product.id,
        "variant_id": (
            int(variant_id)
            if variant_id
            else None
        ),
        "quantity": quantity,
    }

    # Chuyển sang chế độ Mua ngay
    request.session["checkout_mode"] = "buy_now"

    # Xóa lựa chọn cũ từ giỏ hàng
    request.session.pop(
        "selected_cart_keys",
        None
    )

    # Xóa mã thanh toán cũ
    request.session.pop(
        "checkout_payment_ref",
        None
    )

    request.session.modified = True

    return redirect(
        "checkout"
    )


# =========================================================
# GIỎ HÀNG
# =========================================================

def cart(request):
    # ==========================================
    # ĐỒNG BỘ COUPON 20% / 25%
    # ==========================================

    available_coupon = (
        get_customer_available_coupon(
            request
        )
    )

    # ==========================================
    # GIỎ HÀNG
    # ==========================================

    cart_data = request.session.get(
        "cart",
        {}
    )

    # Nếu chưa từng có trạng thái chọn sản phẩm
    # thì mặc định chọn toàn bộ sản phẩm trong giỏ.
    selected_keys = request.session.get(
        "selected_cart_keys"
    )

    if selected_keys is None:

        selected_keys = list(
            cart_data.keys()
        )

        request.session[
            "selected_cart_keys"
        ] = selected_keys

        # Người dùng đang thanh toán từ GIỎ HÀNG
        request.session["checkout_mode"] = "cart"

        # Xóa sản phẩm "Mua ngay" cũ
        request.session.pop(
            "buy_now_item",
            None
        )

        request.session.modified = True

    else:

        # Loại bỏ key cũ không còn trong giỏ.
        selected_keys = [
            key
            for key in selected_keys
            if key in cart_data
        ]

        request.session[
            "selected_cart_keys"
        ] = selected_keys


    selected_key_set = set(
        selected_keys
    )

    cart_items = []

    subtotal = Decimal("0")

    cart_count = 0

    selected_count = 0


    for key, item in cart_data.items():

        product_id = item.get(
            "product_id"
        )

        variant_id = item.get(
            "variant_id"
        )


        try:

            quantity = int(
                item.get(
                    "quantity",
                    1
                )
            )

        except (
            ValueError,
            TypeError,
        ):

            quantity = 1


        if quantity < 1:
            quantity = 1


        product = (
            Product.objects
            .filter(
                id=product_id,
                is_active=True,
            )
            .first()
        )


        if not product:
            continue


        variant = None


        if variant_id:

            variant = (
                ProductVariant.objects
                .filter(
                    id=variant_id,
                    product=product,
                    is_active=True,
                )
                .first()
            )


        if (
            variant
            and variant.price is not None
        ):

            price = variant.price

        else:

            price = product.sale_price


        price = Decimal(
            str(price)
        )


        if (
            variant
            and variant.image
        ):

            image = variant.image

        else:

            image = product.image


        line_total = (
            price
            * quantity
        )


        is_selected = (
            key in selected_key_set
        )


        cart_count += quantity


        if is_selected:

            subtotal += line_total

            selected_count += quantity


        cart_items.append(
            {
                "key": key,
                "product": product,
                "variant": variant,
                "quantity": quantity,
                "price": price,
                "line_total": line_total,
                "image": image,
                "is_selected": is_selected,
            }
        )


    shipping_fee = calculate_shipping_fee(
        subtotal
    )


    total = (
        subtotal
        + shipping_fee
    )


    return render(
        request,
        "cart.html",
        {
            "cart_items": cart_items,
            "cart_count": cart_count,
            "selected_count": selected_count,
            "subtotal": subtotal,
            "shipping_fee": shipping_fee,
            "total": total,
            "available_coupon": available_coupon,
        }
    )



# =========================================================
# CẬP NHẬT SẢN PHẨM ĐƯỢC CHỌN TRONG GIỎ
# =========================================================

@require_POST
def update_cart_selection(request):

    cart_data = request.session.get(
        "cart",
        {}
    )


    # cart.html hiện tại gửi field "selected_keys".
    # Giữ fallback "selected_items" để tương thích code cũ.
    selected_keys = request.POST.getlist(
        "selected_keys"
    )

    if not selected_keys:

        selected_keys = request.POST.getlist(
            "selected_items"
        )


    # Chỉ giữ những key thực sự còn tồn tại trong giỏ.
    selected_keys = [
        key
        for key in selected_keys
        if key in cart_data
    ]

    request.session[
        "selected_cart_keys"
    ] = selected_keys

    # Người dùng đang thanh toán từ GIỎ HÀNG
    request.session[
        "checkout_mode"
    ] = "cart"

    # Xóa sản phẩm Mua ngay cũ
    request.session.pop(
        "buy_now_item",
        None
    )

    # Xóa mã thanh toán cũ
    request.session.pop(
        "checkout_payment_ref",
        None
    )

    request.session.modified = True


    # ==========================================
    # TÍNH LẠI TÓM TẮT GIỎ HÀNG
    # ==========================================

    subtotal = Decimal("0")

    selected_count = 0


    for key in selected_keys:

        item = cart_data.get(
            key
        )

        if not item:
            continue


        product = (
            Product.objects
            .filter(
                id=item.get(
                    "product_id"
                ),
                is_active=True,
            )
            .first()
        )


        if not product:
            continue


        variant = None

        variant_id = item.get(
            "variant_id"
        )


        if variant_id:

            variant = (
                ProductVariant.objects
                .filter(
                    id=variant_id,
                    product=product,
                    is_active=True,
                )
                .first()
            )


        try:

            quantity = int(
                item.get(
                    "quantity",
                    1
                )
            )

        except (
            ValueError,
            TypeError,
        ):

            quantity = 1


        if quantity < 1:
            quantity = 1


        if (
            variant
            and variant.price is not None
        ):

            price = variant.price

        else:

            price = product.sale_price


        price = Decimal(
            str(price)
        )


        subtotal += (
            price
            * quantity
        )

        selected_count += quantity


    shipping_fee = calculate_shipping_fee(
        subtotal
    )


    total = (
        subtotal
        + shipping_fee
    )


    # cart.html gọi bằng fetch/AJAX và cần JSON.
    if (
        request.headers.get(
            "X-Requested-With"
        )
        == "XMLHttpRequest"
    ):

        return JsonResponse(
            {
                "success": True,
                "selected_count": selected_count,
                "subtotal": float(
                    subtotal
                ),
                "shipping_fee": float(
                    shipping_fee
                ),
                "total": float(
                    total
                ),
            }
        )


    # Fallback cho form POST thông thường.
    return redirect(
        "checkout"
    )



# =========================================================
# CẬP NHẬT SỐ LƯỢNG GIỎ HÀNG
# =========================================================

def update_cart(
    request,
    cart_key
):

    if request.method != "POST":

        return redirect(
            "cart"
        )

    cart = request.session.get(
        "cart",
        {}
    )

    if cart_key not in cart:

        messages.error(
            request,
            "Sản phẩm không tồn tại trong giỏ hàng."
        )

        return redirect(
            "cart"
        )

    quantity_raw = request.POST.get(
        "quantity",
        "1"
    )

    try:

        quantity = int(
            quantity_raw
        )

    except (
        ValueError,
        TypeError,
    ):

        quantity = 1

    if quantity < 1:

        cart.pop(
            cart_key,
            None
        )

    else:

        item = cart[cart_key]

        product = Product.objects.filter(
            id=item.get("product_id"),
            is_active=True,
        ).first()

        if not product:

            cart.pop(
                cart_key,
                None
            )

        else:

            variant = None

            if item.get("variant_id"):

                variant = (
                    ProductVariant.objects
                    .filter(
                        id=item.get("variant_id"),
                        product=product,
                        is_active=True,
                    )
                    .first()
                )

            stock = (
                variant.stock
                if variant
                else product.stock
            )

            if quantity > stock:

                messages.warning(
                    request,
                    f"Chỉ còn {stock} sản phẩm trong kho."
                )

                quantity = stock

            if quantity <= 0:

                cart.pop(
                    cart_key,
                    None
                )

            else:

                cart[cart_key][
                    "quantity"
                ] = quantity

    request.session["cart"] = cart
    request.session.modified = True

    return redirect(
        "cart"
    )


# =========================================================
# XÓA SẢN PHẨM KHỎI GIỎ
# =========================================================

def remove_from_cart(
    request,
    cart_key
):

    if request.method != "POST":

        return redirect(
            "cart"
        )

    cart = request.session.get(
        "cart",
        {}
    )

    cart.pop(
        cart_key,
        None
    )

    request.session["cart"] = cart

    selected_keys = request.session.get(
        "selected_cart_keys",
        []
    )

    selected_keys = [
        key
        for key in selected_keys
        if key != cart_key
    ]

    request.session[
        "selected_cart_keys"
    ] = selected_keys

    request.session.modified = True

    messages.success(
        request,
        "Đã xóa sản phẩm khỏi giỏ hàng."
    )

    return redirect(
        "cart"
    )



# =========================================================
# CHÍNH SÁCH MINOO EYEWEAR
# =========================================================

HOTLINE = "090 697 17 96"
EMAIL = "matkinhminoo@gmail.com"
ADDRESS = "112 Thái Thị Bôi, Đà Nẵng"


POLICIES = [
    # =====================================================
    # 1. CHÍNH SÁCH THANH TOÁN
    # =====================================================
    {
        "slug": "thanh-toan",
        "title": "Chính sách thanh toán",
        "summary": "Các phương thức thanh toán được MINOO hỗ trợ khi khách hàng mua sắm tại cửa hàng và đặt hàng trực tuyến.",
        "sections": [
            {
                "heading": "1. Hình thức thanh toán",
                "paragraphs": [
                    "MINOO hỗ trợ các hình thức thanh toán sau để khách hàng thuận tiện lựa chọn khi mua sắm:",
                ],
                "bullets": [
                    "Thanh toán trực tiếp bằng tiền mặt tại cửa hàng MINOO.",
                    "Thanh toán chuyển khoản ngân hàng theo thông tin tài khoản do MINOO cung cấp tại bước đặt hàng hoặc xác nhận đơn hàng.",
                    "Thanh toán khi nhận hàng (COD) đối với các đơn hàng đáp ứng điều kiện áp dụng của cửa hàng.",
                ],
            },
            {
                "heading": "2. Thanh toán chuyển khoản",
                "paragraphs": [
                    "Khi lựa chọn chuyển khoản, khách hàng vui lòng kiểm tra chính xác thông tin tài khoản và số tiền cần thanh toán trước khi thực hiện giao dịch.",
                    "Khách hàng nên ghi mã đơn hàng hoặc nội dung chuyển khoản theo hướng dẫn của MINOO để cửa hàng thuận tiện đối chiếu giao dịch.",
                    "Thông tin tài khoản ngân hàng được cung cấp tại bước thanh toán hoặc trong thông báo xác nhận đơn hàng của MINOO.",
                ],
            },
            {
                "heading": "3. Xác nhận thanh toán",
                "paragraphs": [
                    "Đối với đơn hàng chuyển khoản, MINOO kiểm tra giao dịch và xác nhận thanh toán trước khi xử lý đơn hàng theo quy trình của cửa hàng.",
                    "Việc khách hàng gửi ảnh chụp màn hình giao dịch không thay thế cho việc xác minh khoản tiền thực tế đã được ghi nhận.",
                    "Nếu giao dịch chưa được xác nhận hoặc có sai lệch về số tiền, nội dung chuyển khoản, MINOO sẽ liên hệ khách hàng để kiểm tra và hướng dẫn xử lý.",
                    "Đối với đơn hàng COD, khách hàng thanh toán theo số tiền được xác nhận khi nhận hàng.",
                ],
            },
            {
                "heading": "4. Giá bán và số tiền thanh toán",
                "paragraphs": [
                    "Giá sản phẩm được hiển thị trên website là căn cứ để khách hàng tham khảo và đặt hàng. Tổng số tiền thanh toán của đơn hàng được xác định theo thông tin đơn hàng đã xác nhận, bao gồm các khoản phí áp dụng nếu có.",
                    "Nếu phát sinh sai lệch về giá, phí vận chuyển hoặc thông tin thanh toán, MINOO sẽ liên hệ khách hàng để kiểm tra và thống nhất phương án xử lý trước khi tiếp tục thực hiện đơn hàng.",
                ],
            },
            {
                "heading": "5. Hỗ trợ thanh toán",
                "paragraphs": [
                    "Nếu gặp khó khăn trong quá trình thanh toán hoặc cần kiểm tra trạng thái giao dịch, khách hàng vui lòng liên hệ MINOO qua hotline hoặc email được cung cấp ở cuối trang chính sách.",
                ],
            },
        ],
    },

    # =====================================================
    # 2. CHÍNH SÁCH GIAO HÀNG
    # =====================================================
    {
        "slug": "giao-hang",
        "title": "Chính sách giao hàng",
        "summary": "Thông tin về phạm vi giao hàng, thời gian vận chuyển, phí giao hàng và cách kiểm tra sản phẩm khi nhận.",
        "sections": [
            {
                "heading": "1. Phạm vi giao hàng",
                "paragraphs": [
                    "MINOO hỗ trợ giao hàng trên toàn quốc thông qua hình thức vận chuyển phù hợp với đơn hàng.",
                    "Sau khi đơn hàng được xác nhận, cửa hàng tiến hành chuẩn bị sản phẩm và bàn giao cho đơn vị vận chuyển theo quy trình xử lý đơn hàng.",
                    "Đối với một số khu vực đặc biệt hoặc địa chỉ giao hàng khó tiếp cận, thời gian và khả năng giao hàng có thể thay đổi tùy điều kiện vận chuyển thực tế.",
                ],
            },
            {
                "heading": "2. Thời gian giao hàng",
                "paragraphs": [
                    "Thời gian giao hàng được tính sau khi đơn hàng được xác nhận và sẵn sàng bàn giao cho đơn vị vận chuyển.",
                    "Thời gian thực tế có thể thay đổi tùy địa chỉ nhận hàng, tình trạng vận chuyển, thời tiết hoặc các dịp lễ, Tết.",
                ],
                "bullets": [
                    "Khu vực nội thành: 1-2 ngày.",
                    "Các tỉnh/thành phố khác: 3-4 ngày.",
                ],
            },
            {
                "heading": "3. Phí vận chuyển",
                "paragraphs": [
                    "MINOO áp dụng chính sách phí vận chuyển theo giá trị đơn hàng như sau:",
                ],
                "bullets": [
                    "Đơn hàng từ 500.000₫ trở lên: miễn phí vận chuyển.",
                    "Đơn hàng dưới 500.000₫: phí vận chuyển tiêu chuẩn 30.000₫.",
                ],
                "paragraphs_extra": [
                    "Nếu có chương trình ưu đãi hoặc điều kiện vận chuyển đặc biệt, phí giao hàng sẽ được thông báo theo thông tin áp dụng cho đơn hàng tại thời điểm đặt hàng.",
                ],
            },
            {
                "heading": "4. Kiểm tra hàng khi nhận",
                "paragraphs": [
                    "Khi nhận hàng, khách hàng nên kiểm tra tình trạng bên ngoài của kiện hàng và đối chiếu sản phẩm với thông tin đơn hàng.",
                    "Nếu phát hiện sản phẩm giao sai, thiếu phụ kiện hoặc có dấu hiệu hư hỏng do vận chuyển, khách hàng vui lòng ghi nhận tình trạng thực tế và liên hệ MINOO sớm để được hỗ trợ.",
                    "Việc tiếp nhận và xử lý yêu cầu sẽ căn cứ vào tình trạng sản phẩm, thông tin đơn hàng và kết quả kiểm tra của cửa hàng.",
                ],
            },
            {
                "heading": "5. Trường hợp giao hàng chưa thành công",
                "paragraphs": [
                    "Nếu đơn vị vận chuyển không thể giao hàng do khách hàng cung cấp sai thông tin, không thể liên hệ người nhận hoặc các nguyên nhân khách quan khác, thời gian giao hàng có thể kéo dài.",
                    "MINOO có thể liên hệ khách hàng để xác nhận lại thông tin nhận hàng và hướng dẫn phương án xử lý phù hợp.",
                ],
            },
            {
                "heading": "6. Hỗ trợ giao hàng",
                "paragraphs": [
                    "Nếu cần kiểm tra tình trạng đơn hàng hoặc cập nhật thông tin nhận hàng, khách hàng vui lòng liên hệ MINOO qua hotline hoặc email ở cuối trang.",
                ],
            },
        ],
    },

    # =====================================================
    # 3. CHÍNH SÁCH ĐỔI TRẢ
    # =====================================================
    {
        "slug": "doi-tra",
        "title": "Chính sách đổi trả",
        "summary": "Quy định về điều kiện, trường hợp và quy trình tiếp nhận yêu cầu đổi trả sản phẩm tại MINOO.",
        "sections": [
            {
                "heading": "1. Trường hợp được xem xét đổi trả",
                "paragraphs": [
                    "MINOO tiếp nhận và xem xét yêu cầu đổi trả trong các trường hợp như sản phẩm có lỗi do nhà sản xuất hoặc sản phẩm được giao không đúng với đơn hàng đã xác nhận.",
                    "Mỗi yêu cầu sẽ được kiểm tra dựa trên tình trạng sản phẩm, thông tin đơn hàng và nguyên nhân phát sinh để xác định phương án xử lý phù hợp.",
                ],
            },
            {
                "heading": "2. Điều kiện đổi trả",
                "paragraphs": [
                    "Để được xem xét đổi trả, khách hàng cần đáp ứng các điều kiện sau:",
                ],
                "bullets": [
                    "Sản phẩm còn nguyên trạng, chưa qua sử dụng và còn đầy đủ phụ kiện đi kèm.",
                    "Khách hàng cung cấp được hóa đơn hoặc thông tin đơn hàng để MINOO kiểm tra.",
                    "Yêu cầu được gửi trong thời hạn đổi trả áp dụng của cửa hàng: 07 kể từ ngày nhận hàng.",
                    "Sản phẩm được kiểm tra để xác định tình trạng và nguyên nhân cần đổi trả.",
                ],
            },
            {
                "heading": "3. Trường hợp không áp dụng đổi trả",
                "paragraphs": [
                    "MINOO có thể từ chối yêu cầu đổi trả nếu sản phẩm không đáp ứng điều kiện áp dụng hoặc thuộc các trường hợp dưới đây:",
                ],
                "bullets": [
                    "Sản phẩm bị hư hỏng, biến dạng, trầy xước do va đập, sử dụng hoặc bảo quản không đúng cách.",
                    "Sản phẩm đã bị tự ý sửa chữa hoặc can thiệp làm thay đổi tình trạng ban đầu.",
                ],
            },
            {
                "heading": "4. Quy trình đổi trả",
                "paragraphs": [
                    "Khách hàng vui lòng liên hệ MINOO qua hotline, email hoặc trực tiếp tại cửa hàng để trình bày tình trạng sản phẩm và cung cấp thông tin đơn hàng.",
                    "Sau khi tiếp nhận yêu cầu, MINOO kiểm tra thông tin và hướng dẫn khách hàng cách gửi sản phẩm hoặc mang sản phẩm đến cửa hàng để kiểm tra.",
                    "Khi có kết quả kiểm tra, MINOO sẽ thông báo phương án xử lý phù hợp, chẳng hạn như đổi sản phẩm hoặc hỗ trợ theo chính sách áp dụng.",
                ],
            },
            {
                "heading": "5. Chi phí vận chuyển khi đổi trả",
                "paragraphs": [
                    "Chi phí vận chuyển phát sinh trong quá trình đổi trả được áp dụng theo từng trường hợp và chính sách thực tế của cửa hàng.",

                ],
            },
            {
                "heading": "6. Liên hệ hỗ trợ",
                "paragraphs": [
                    "Để được hướng dẫn về điều kiện đổi trả hoặc kiểm tra tình trạng yêu cầu, khách hàng vui lòng liên hệ MINOO qua thông tin ở cuối trang.",
                ],
            },
        ],
    },

    # =====================================================
    # 4. CHÍNH SÁCH BẢO HÀNH
    # =====================================================
    {
        "slug": "bao-hanh",
        "title": "Chính sách bảo hành",
        "summary": "Thông tin về thời hạn, điều kiện, phạm vi và quy trình tiếp nhận bảo hành sản phẩm tại MINOO.",
        "sections": [
            {
                "heading": "1. Thời hạn và phạm vi bảo hành",
                "paragraphs": [
                    "MINOO hỗ trợ tiếp nhận và xem xét bảo hành đối với các sản phẩm phát sinh lỗi kỹ thuật thuộc phạm vi bảo hành được áp dụng tại cửa hàng.",
                    "Thời hạn và phạm vi bảo hành cụ thể được xác định theo chính sách của sản phẩm và thông tin mua hàng.",
                ],
                "bullets": [
                    "Thời hạn bảo hành gọng kính: 01 kể từ ngày mua.",
                    "Phạm vi bảo hành: Lỗi kỹ thuật do nhà sản xuất, lỗi ốc vít, bản lề...",
                ],
            },
            {
                "heading": "2. Điều kiện tiếp nhận bảo hành",
                "paragraphs": [
                    "Khách hàng vui lòng cung cấp thông tin mua hàng để MINOO kiểm tra sản phẩm và xác nhận điều kiện bảo hành.",
                    "Sản phẩm sẽ được kiểm tra tình trạng thực tế trước khi xác định nguyên nhân lỗi và phương án hỗ trợ phù hợp.",
                ],
                "bullets": [
                    "Có thông tin mua hàng hoặc hóa đơn để đối chiếu.",
                    "Sản phẩm còn trong thời hạn bảo hành áp dụng.",
                    "Lỗi phát sinh thuộc phạm vi bảo hành được công bố cho sản phẩm.",
                ],
            },
            {
                "heading": "3. Trường hợp không thuộc phạm vi bảo hành",
                "paragraphs": [
                    "Các trường hợp dưới đây có thể không thuộc phạm vi bảo hành của cửa hàng:",
                ],
                "bullets": [
                    "Sản phẩm bị rơi vỡ, cong vênh hoặc trầy xước do tác động bên ngoài.",
                    "Sản phẩm hư hỏng do sử dụng hoặc bảo quản không đúng cách.",
                    "Sản phẩm đã bị tự ý sửa chữa hoặc can thiệp tại nơi khác.",

                ],
            },
            {
                "heading": "4. Quy trình tiếp nhận bảo hành",
                "paragraphs": [
                    "Khách hàng liên hệ MINOO qua hotline, email hoặc mang sản phẩm đến cửa hàng để yêu cầu kiểm tra bảo hành.",
                    "MINOO tiếp nhận thông tin, kiểm tra tình trạng sản phẩm và đối chiếu điều kiện bảo hành.",
                    "Sau khi kiểm tra, cửa hàng thông báo kết quả và hướng dẫn phương án xử lý phù hợp với tình trạng thực tế.",
                ],
            },
            {
                "heading": "5. Địa điểm tiếp nhận bảo hành",
                "paragraphs": [
                    "Khách hàng có thể mang sản phẩm đến cửa hàng MINOO tại 112 Thái Thị Bôi, Đà Nẵng để được hướng dẫn kiểm tra và tiếp nhận yêu cầu bảo hành.",
                    "Khách hàng nên liên hệ trước qua hotline để được hướng dẫn về thông tin cần cung cấp và quy trình tiếp nhận.",
                ],
            },
        ],
    },

    # =====================================================
    # 5. CHÍNH SÁCH BẢO MẬT THÔNG TIN
    # =====================================================
    {
        "slug": "bao-mat",
        "title": "Chính sách bảo mật thông tin",
        "summary": "Cam kết của MINOO trong việc thu thập, sử dụng, bảo vệ và xử lý thông tin cá nhân của khách hàng.",
        "sections": [
            {
                "heading": "1. Thông tin MINOO thu thập",
                "paragraphs": [
                    "Khi khách hàng sử dụng website, gửi biểu mẫu liên hệ hoặc đặt hàng, MINOO có thể tiếp nhận những thông tin cần thiết để hỗ trợ và xử lý yêu cầu.",
                ],
                "bullets": [
                    "Thông tin liên hệ: họ tên, số điện thoại và địa chỉ email.",
                    "Nội dung trao đổi mà khách hàng gửi cho MINOO qua biểu mẫu liên hệ hoặc các kênh hỗ trợ.",
                    "Thông tin đơn hàng: sản phẩm đã chọn, số lượng, địa chỉ nhận hàng và thông tin cần thiết để xử lý đơn hàng.",
                    "Thông tin khác do khách hàng tự nguyện cung cấp trong quá trình sử dụng dịch vụ.",
                ],
            },
            {
                "heading": "2. Mục đích sử dụng thông tin",
                "paragraphs": [
                    "MINOO sử dụng thông tin khách hàng trong phạm vi cần thiết để phục vụ hoạt động bán hàng và nâng cao chất lượng dịch vụ.",
                ],
                "bullets": [
                    "Liên hệ, tư vấn và phản hồi các yêu cầu của khách hàng.",
                    "Tiếp nhận, xác nhận và xử lý đơn hàng.",
                    "Hỗ trợ giao hàng, thanh toán, đổi trả và bảo hành sản phẩm.",
                    "Giải quyết các vấn đề phát sinh liên quan đến đơn hàng và dịch vụ.",
                    "Cải thiện chất lượng website và trải nghiệm mua sắm.",
                    "Thực hiện các nghĩa vụ theo quy định pháp luật khi có yêu cầu hợp lệ.",
                ],
            },
            {
                "heading": "3. Bảo mật và chia sẻ thông tin",
                "paragraphs": [
                    "MINOO cam kết không bán hoặc trao đổi thông tin cá nhân của khách hàng cho bên thứ ba vì mục đích thương mại trái với chính sách này.",
                    "Thông tin có thể được chia sẻ trong phạm vi cần thiết với đơn vị vận chuyển hoặc bên cung cấp dịch vụ liên quan để thực hiện đơn hàng và hỗ trợ khách hàng.",
                    "Thông tin cũng có thể được cung cấp khi có yêu cầu hợp lệ từ cơ quan có thẩm quyền theo quy định pháp luật.",
                    "MINOO thực hiện các biện pháp phù hợp để hạn chế việc truy cập, sử dụng hoặc tiết lộ thông tin không được phép trong phạm vi hệ thống và hoạt động quản lý của cửa hàng.",
                ],
            },
            {
                "heading": "4. Thời gian lưu trữ thông tin",
                "paragraphs": [
                    "Thông tin khách hàng được lưu trữ trong khoảng thời gian cần thiết để thực hiện mục đích thu thập, hỗ trợ đơn hàng, giải quyết yêu cầu liên quan hoặc đáp ứng nghĩa vụ lưu trữ theo quy định pháp luật.",
                    "Thời gian lưu trữ cụ thể phụ thuộc vào loại thông tin và mục đích sử dụng tương ứng.",
                ],
            },
            {
                "heading": "5. Quyền của khách hàng",
                "paragraphs": [
                    "Khách hàng có thể liên hệ MINOO để yêu cầu kiểm tra, cập nhật hoặc chỉnh sửa thông tin cá nhân đã cung cấp.",
                    "Khách hàng cũng có thể gửi yêu cầu liên quan đến việc xóa hoặc hạn chế sử dụng thông tin theo phạm vi được phép và các quy định pháp luật áp dụng.",
                    "MINOO sẽ tiếp nhận, kiểm tra và phản hồi yêu cầu theo điều kiện thực tế và quy định liên quan.",
                ],
            },
            {
                "heading": "6. Bảo vệ thông tin cá nhân",
                "paragraphs": [
                    "Khách hàng nên cung cấp thông tin chính xác và chỉ gửi các thông tin cần thiết cho mục đích liên hệ hoặc đặt hàng.",
                    "Nếu phát hiện vấn đề liên quan đến thông tin cá nhân đã cung cấp, khách hàng vui lòng liên hệ MINOO để được tiếp nhận và hỗ trợ xử lý.",
                ],
            },
            {
                "heading": "7. Thay đổi chính sách bảo mật",
                "paragraphs": [
                    "MINOO có thể cập nhật nội dung chính sách bảo mật khi cần thiết để phù hợp với hoạt động thực tế hoặc các quy định liên quan.",
                    "Nội dung cập nhật sẽ được đăng tải trên website để khách hàng tham khảo trước khi tiếp tục sử dụng dịch vụ.",
                ],
            },
            {
                "heading": "8. Liên hệ về thông tin cá nhân",
                "paragraphs": [
                    "Nếu có câu hỏi hoặc yêu cầu liên quan đến việc thu thập, sử dụng và bảo vệ thông tin cá nhân, khách hàng vui lòng liên hệ MINOO qua hotline hoặc email ở cuối trang.",
                ],
            },
        ],
    },
]


# =========================================================
# DANH SÁCH CHÍNH SÁCH
# =========================================================

def policy_index(request):
    return render(
        request,
        "policy_index.html",
        {
            "policies": POLICIES,
        },
    )


# =========================================================
# CHI TIẾT CHÍNH SÁCH
# =========================================================

def policy_detail(request, policy_slug):
    policy = next(
        (
            item
            for item in POLICIES
            if item["slug"] == policy_slug
        ),
        None,
    )

    if policy is None:
        return redirect("policies")

    return render(
        request,
        "policy_detail.html",
        {
            "policy": policy,
            "policies": POLICIES,
            "HOTLINE": HOTLINE,
            "EMAIL": EMAIL,
            "ADDRESS": ADDRESS,
        },
    )


# =========================================================
# GIỚI THIỆU
# =========================================================

def about(request):

    return render(
        request,
        "about.html"
    )


# =========================================================
# LIÊN HỆ
# =========================================================

def contact(request):

    if request.method == "POST":

        form = ContactForm(
            request.POST
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Cảm ơn bạn đã liên hệ với Minoo."
            )

            return redirect(
                "contact"
            )

    else:

        form = ContactForm()

    return render(
        request,
        "contact.html",
        {
            "form": form,
        }
    )


# =========================================================
# TẠO URL VIETQR
# =========================================================

def build_vietqr_url(
    amount,
    transfer_content
):

    amount = int(
        Decimal(
            str(amount)
        )
    )

    encoded_content = quote(
        str(transfer_content)
    )

    return (
        "https://img.vietqr.io/image/"
        "MB-5228082005-compact2.png"
        f"?amount={amount}"
        f"&addInfo={encoded_content}"
        "&accountName=TRAN%20NGOC%20YEN%20NHI"
    )


# =========================================================
# CHECKOUT
# =========================================================
@login_required(
    login_url='login'
)

def checkout(request):

    cart = request.session.get(
        "cart",
        {}
    )

    selected_keys = request.session.get(
        "selected_cart_keys",
        []
    )

    checkout_mode = request.session.get(
        "checkout_mode",
        "cart"
    )

    selected_items = []

    # =====================================================
    # MUA NGAY
    # =====================================================

    if checkout_mode == "buy_now":

        buy_now_item = request.session.get(
            "buy_now_item"
        )

        if not buy_now_item:

            messages.warning(
                request,
                "Không tìm thấy sản phẩm cần thanh toán."
            )

            return redirect(
                "products"
            )

        product_id = buy_now_item.get(
            "product_id"
        )

        variant_id = buy_now_item.get(
            "variant_id"
        )

        try:

            quantity = int(
                buy_now_item.get(
                    "quantity",
                    1
                )
            )

        except (
            ValueError,
            TypeError,
        ):

            quantity = 1

        if quantity < 1:
            quantity = 1

        product = (
            Product.objects
            .filter(
                id=product_id,
                is_active=True,
            )
            .first()
        )

        if not product:

            messages.error(
                request,
                "Sản phẩm không còn tồn tại."
            )

            return redirect(
                "products"
            )

        variant = None

        if variant_id:

            variant = (
                ProductVariant.objects
                .filter(
                    id=variant_id,
                    product=product,
                    is_active=True,
                )
                .first()
            )

            if not variant:

                messages.error(
                    request,
                    f"Biến thể của sản phẩm '{product.name}' không còn tồn tại."
                )

                return redirect(
                    "product_detail",
                    product_id=product.id
                )

        if variant:

            if variant.stock < quantity:

                messages.error(
                    request,
                    f"Biến thể của sản phẩm '{product.name}' không đủ số lượng trong kho."
                )

                return redirect(
                    "product_detail",
                    product_id=product.id
                )

        else:

            if product.stock < quantity:

                messages.error(
                    request,
                    f"Sản phẩm '{product.name}' không đủ số lượng trong kho."
                )

                return redirect(
                    "product_detail",
                    product_id=product.id
                )

        if (
            variant
            and variant.price is not None
        ):

            price = variant.price

        else:

            price = product.sale_price

        price = Decimal(
            str(price)
        )

        variant_name = ""

        if variant:

            variant_details = []

            # Gọng kính: value = màu sắc
            # Tròng kính: value = độ cận
            if variant.value:
                variant_details.append(
                    str(variant.value)
                )

            if variant.size:
                variant_details.append(
                    str(variant.size)
                )

            if variant.material:
                variant_details.append(
                    str(variant.material)
                )

            if variant_details:

                variant_name = ", ".join(
                    variant_details
                )

            else:

                variant_name = (
                    str(variant.sku)
                    if variant.sku
                    else ""
                )
        if (
            variant
            and variant.image
        ):

            image = variant.image

        else:

            image = product.image

        line_total = (
            price
            * quantity
        )

        selected_items.append(
            {
                "key": None,
                "cart_key": None,
                "product": product,
                "variant": variant,
                "product_id": product.id,
                "variant_id": (
                    variant.id
                    if variant
                    else None
                ),
                "name": product.name,
                "variant_name": variant_name,
                "price": price,
                "quantity": quantity,
                "image": image,
                "line_total": line_total,
            }
        )

    # =====================================================
    # THANH TOÁN TỪ GIỎ HÀNG
    # =====================================================

    else:

        if not selected_keys:

            messages.warning(
                request,
                "Vui lòng chọn sản phẩm cần thanh toán."
            )

            return redirect(
                "cart"
            )

        for key in selected_keys:

            item = cart.get(
                key
            )

            if not item:
                continue

            product_id = item.get(
                "product_id"
            )

            variant_id = item.get(
                "variant_id"
            )

            try:

                quantity = int(
                    item.get(
                        "quantity",
                        1
                    )
                )

            except (
                ValueError,
                TypeError,
            ):

                quantity = 1

            if quantity < 1:
                quantity = 1

            product = (
                Product.objects
                .filter(
                    id=product_id,
                    is_active=True,
                )
                .first()
            )

            if not product:
                continue

            variant = None

            if variant_id:

                variant = (
                    ProductVariant.objects
                    .filter(
                        id=variant_id,
                        product=product,
                        is_active=True,
                    )
                    .first()
                )

                if not variant:

                    messages.error(
                        request,
                        f"Biến thể của sản phẩm '{product.name}' không còn tồn tại."
                    )

                    return redirect(
                        "cart"
                    )

            if (
                variant
                and variant.price is not None
            ):

                price = variant.price

            else:

                price = product.sale_price

            price = Decimal(
                str(price)
            )

            variant_name = ""

            if variant:

                variant_details = []

                # Gọng kính: value = màu sắc
                # Tròng kính: value = độ cận
                if variant.value:
                    variant_details.append(
                        str(variant.value)
                    )

                if variant.size:
                    variant_details.append(
                        str(variant.size)
                    )

                if variant.material:
                    variant_details.append(
                        str(variant.material)
                    )

                if variant_details:

                    variant_name = ", ".join(
                        variant_details
                    )

                else:

                    variant_name = (
                        str(variant.sku)
                        if variant.sku
                        else ""
                    )
            if (
                variant
                and variant.image
            ):

                image = variant.image

            else:

                image = product.image

            line_total = (
                price
                * quantity
            )

            selected_items.append(
                {
                    "key": key,
                    "cart_key": key,
                    "product": product,
                    "variant": variant,
                    "product_id": product.id,
                    "variant_id": (
                        variant.id
                        if variant
                        else None
                    ),
                    "name": product.name,
                    "variant_name": variant_name,
                    "price": price,
                    "quantity": quantity,
                    "image": image,
                    "line_total": line_total,
                }
            )

    # =====================================================
    # KIỂM TRA SẢN PHẨM
    # =====================================================

    if not selected_items:

        messages.warning(
            request,
            "Không tìm thấy sản phẩm cần thanh toán."
        )

        if checkout_mode == "buy_now":

            return redirect(
                "products"
            )

        return redirect(
            "cart"
        )

    # =====================================================
    # TẠM TÍNH
    # =====================================================

    subtotal = sum(
        (
            item["price"]
            * item["quantity"]
            for item in selected_items
        ),
        Decimal("0")
    )

    # =====================================================
    # PHÍ VẬN CHUYỂN
    # =====================================================

    shipping_fee = calculate_shipping_fee(
        subtotal
    )

    # =====================================================
    # MÃ GIẢM GIÁ
    # =====================================================

    available_coupon = get_customer_available_coupon(
        request
    )

    discount_amount = Decimal("0")

    applied_coupon_code = request.session.get(
        "applied_coupon_code"
    )

    if (
        available_coupon
        and applied_coupon_code
        == available_coupon.code
    ):

        discount_amount = (
            subtotal
            * Decimal(
                str(
                    available_coupon.discount_percent
                )
            )
            / Decimal("100")
        ).quantize(
            Decimal("1")
        )

    # =====================================================
    # TỔNG THANH TOÁN SAU GIẢM
    # =====================================================

    total = (
        subtotal
        - discount_amount
        + shipping_fee
    )

    if total < 0:
        total = Decimal("0")

    # =====================================================
    # MÃ THANH TOÁN
    # =====================================================

    payment_ref = request.session.get(
        "checkout_payment_ref"
    )

    if not payment_ref:

        payment_ref = (
            "MINOO"
            + uuid.uuid4().hex[:8].upper()
        )

        request.session[
            "checkout_payment_ref"
        ] = payment_ref

        request.session.modified = True

    # =====================================================
    # VIETQR
    # =====================================================

    qr_url = build_vietqr_url(
        total,
        payment_ref
    )

    # =====================================================
    # POST - ĐẶT HÀNG
    # =====================================================

    if request.method == "POST":

        full_name = request.POST.get(
            "full_name",
            ""
        ).strip()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        address = request.POST.get(
            "address",
            ""
        ).strip()

        note = request.POST.get(
            "note",
            ""
        ).strip()

        payment_method = request.POST.get(
            "payment_method",
            "cod"
        )

        checkout_context = {
            "selected_items": selected_items,
            "items": selected_items,
            "subtotal": subtotal,
            "available_coupon": available_coupon,
            "discount_amount": discount_amount,
            "shipping_fee": shipping_fee,
            "total": total,
            "qr_url": qr_url,
            "payment_ref": payment_ref,
        }

        if not full_name:

            messages.error(
                request,
                "Vui lòng nhập họ và tên."
            )

            return render(
                request,
                "checkout.html",
                checkout_context
            )

        if not phone:

            messages.error(
                request,
                "Vui lòng nhập số điện thoại."
            )

            return render(
                request,
                "checkout.html",
                checkout_context
            )

        if not address:

            messages.error(
                request,
                "Vui lòng nhập địa chỉ nhận hàng."
            )

            return render(
                request,
                "checkout.html",
                checkout_context
            )

        if payment_method not in [
            "cod",
            "bank",
        ]:

            payment_method = "cod"

        # =================================================
        # KIỂM TRA TỒN KHO LẦN CUỐI
        # =================================================

        for item in selected_items:

            product = (
                Product.objects
                .filter(
                    id=item["product_id"],
                    is_active=True,
                )
                .first()
            )

            if not product:

                messages.error(
                    request,
                    "Một sản phẩm không còn tồn tại."
                )

                if checkout_mode == "buy_now":

                    return redirect(
                        "products"
                    )

                return redirect(
                    "cart"
                )

            if item.get("variant_id"):

                variant = (
                    ProductVariant.objects
                    .filter(
                        id=item["variant_id"],
                        product=product,
                        is_active=True,
                    )
                    .first()
                )

                if not variant:

                    messages.error(
                        request,
                        f"Biến thể của sản phẩm '{product.name}' không còn tồn tại."
                    )

                    if checkout_mode == "buy_now":

                        return redirect(
                            "product_detail",
                            product_id=product.id
                        )

                    return redirect(
                        "cart"
                    )

                if variant.stock < item["quantity"]:

                    messages.error(
                        request,
                        f"Biến thể của sản phẩm '{product.name}' không đủ số lượng trong kho."
                    )

                    if checkout_mode == "buy_now":

                        return redirect(
                            "product_detail",
                            product_id=product.id
                        )

                    return redirect(
                        "cart"
                    )

            else:

                if product.stock < item["quantity"]:

                    messages.error(
                        request,
                        f"Sản phẩm '{product.name}' không đủ số lượng trong kho."
                    )

                    if checkout_mode == "buy_now":

                        return redirect(
                            "product_detail",
                            product_id=product.id
                        )

                    return redirect(
                        "cart"
                    )

        # =================================================
        # TẠO ĐƠN HÀNG
        # =================================================

        with transaction.atomic():

            order = Order.objects.create(

                order_code=payment_ref,

                full_name=full_name,

                phone=phone,

                email=email,

                address=address,

                note=note,

                payment_method=payment_method,

                payment_status=(
                    "unpaid"
                    if payment_method == "cod"
                    else "pending"
                ),

                status="pending",

                subtotal=subtotal,

                shipping_fee=shipping_fee,

                total=total,
            )

            # =================================================
            # TẠO ORDER ITEM
            # =================================================

            for item in selected_items:

                product = Product.objects.get(
                    id=item["product_id"]
                )

                variant = None

                if item.get("variant_id"):

                    variant = (
                        ProductVariant.objects
                        .filter(
                            id=item["variant_id"],
                            product=product,
                            is_active=True,
                        )
                        .first()
                    )

                line_total = (
                    item["price"]
                    * item["quantity"]
                )

                OrderItem.objects.create(

                    order=order,

                    product=product,

                    variant=variant,

                    product_name=product.name,

                    variant_name=item.get(
                        "variant_name",
                        ""
                    ),

                    price=item["price"],

                    quantity=item["quantity"],

                    line_total=line_total,
                )

                # =================================================
                # TRỪ TỒN KHO
                # =================================================

                if variant:

                    variant.stock -= (
                        item["quantity"]
                    )

                    variant.save(
                        update_fields=[
                            "stock"
                        ]
                    )

                else:

                    product.stock -= (
                        item["quantity"]
                    )

                    product.save(
                        update_fields=[
                            "stock"
                        ]
                    )

        # =====================================================
        # LƯU ĐƠN HÀNG VÀO SESSION
        # =====================================================

        order_ids = request.session.get(
            "order_ids",
            []
        )

        order_ids = [
            str(item)
            for item in order_ids
        ]

        current_order_id = str(
            order.id
        )

        if current_order_id not in order_ids:

            order_ids.append(
                current_order_id
            )

        request.session[
            "order_ids"
        ] = order_ids

        request.session[
            "last_order_id"
        ] = current_order_id

        request.session[
            "order_id"
        ] = current_order_id

        request.session[
            "last_order_code"
        ] = order.order_code

        # =====================================================
        # XỬ LÝ SAU KHI ĐẶT HÀNG
        # =====================================================

        if checkout_mode == "buy_now":

            request.session.pop(
                "buy_now_item",
                None
            )

            request.session.pop(
                "checkout_mode",
                None
            )

        else:

            for key in selected_keys:

                cart.pop(
                    key,
                    None
                )

            request.session[
                "cart"
            ] = cart

            request.session.pop(
                "selected_cart_keys",
                None
            )

            request.session.pop(
                "checkout_mode",
                None
            )

        # =====================================================
        # XÓA MÃ THANH TOÁN
        # =====================================================

        request.session.pop(
            "checkout_payment_ref",
            None
        )

        request.session.modified = True

        # =====================================================
        # CHUYỂN TRANG
        # =====================================================

        if payment_method == "bank":

            return redirect(
                "bank_payment",
                order_id=order.id
            )

        return redirect(
            "order_success"
        )

    # =====================================================
    # HIỂN THỊ CHECKOUT
    # =====================================================

    return render(
        request,
        "checkout.html",
        {
            "selected_items": selected_items,
            "items": selected_items,
            "subtotal": subtotal,
            "available_coupon": available_coupon,
            "discount_amount": discount_amount,
            "shipping_fee": shipping_fee,
            "total": total,
            "qr_url": qr_url,
            "payment_ref": payment_ref,
        }
    )


# =========================================================
# ĐẶT HÀNG THÀNH CÔNG
# =========================================================

def order_success(request):

    order_id = (
        request.session.get(
            "last_order_id"
        )
        or request.session.get(
            "order_id"
        )
    )

    if not order_id:

        return redirect(
            "home"
        )

    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items"
        ),
        id=order_id
    )

    return render(
        request,
        "order_success.html",
        {
            "order": order
        }
    )


# =========================================================
# THEO DÕI ĐƠN HÀNG - DANH SÁCH
# =========================================================

def order_tracking(request):

    order_ids = request.session.get(
        "order_ids",
        []
    )

    order_ids = [
        str(item)
        for item in order_ids
    ]

    last_order_id = request.session.get(
        "last_order_id"
    )

    if last_order_id:

        last_order_id = str(
            last_order_id
        )

        if last_order_id not in order_ids:

            order_ids.append(
                last_order_id
            )

    if order_ids:

        request.session[
            "order_ids"
        ] = order_ids

        request.session.modified = True

    if not order_ids:

        return render(
            request,
            "order_tracking.html",
            {
                "orders": []
            }
        )

    orders = (
        Order.objects
        .filter(
            id__in=order_ids
        )
        .prefetch_related(
            "items"
        )
        .order_by(
            "-created_at"
        )
    )

    return render(
        request,
        "order_tracking.html",
        {
            "orders": orders
        }
    )


# =========================================================
# THANH TOÁN CHUYỂN KHOẢN
# =========================================================


def bank_payment(
    request,
    order_id
):

    order = get_object_or_404(
        Order,
        id=order_id
    )

    # ==========================================
    # KIỂM TRA QUYỀN TRUY CẬP ĐƠN HÀNG
    # ==========================================

    allowed_order_ids = {
        str(item)
        for item in request.session.get("order_ids", [])
    }

    last_order_id = request.session.get("last_order_id")

    if last_order_id:
        allowed_order_ids.add(str(last_order_id))

    if str(order.id) not in allowed_order_ids:
        return JsonResponse(
            {"error": "Không có quyền truy cập đơn hàng"},
            status=403,
        )

    # ==========================================
    # KIỂM TRA PHƯƠNG THỨC THANH TOÁN
    # ==========================================

    if order.payment_method != "bank":
        return redirect("order_success")

    if order.payment_status == "paid":
        return redirect("order_success")

    bank_code = "MBBank"

    account_number = "5228082005"

    account_name = "TRAN NGOC YEN NHI"

    transfer_content = order.order_code

    qr_url = build_vietqr_url(
        order.total,
        transfer_content
    )

    return render(
        request,
        "bank_payment.html",
        {
            "order": order,
            "qr_url": qr_url,
            "bank_code": bank_code,
            "account_number": account_number,
            "account_name": account_name,
            "transfer_content": transfer_content,
        }
    )



# =========================================================
# XÁC NHẬN ĐÃ CHUYỂN KHOẢN
# =========================================================

@require_POST
def confirm_bank_payment(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        payment_method="bank",
    )

    allowed_order_ids = {
        str(item)
        for item in request.session.get("order_ids", [])
    }

    last_order_id = request.session.get("last_order_id")

    if last_order_id:
        allowed_order_ids.add(str(last_order_id))

    if str(order.id) not in allowed_order_ids:
        return JsonResponse(
            {"error": "Không có quyền truy cập đơn hàng"},
            status=403,
        )

    if order.payment_status == "paid":
        return redirect("order_success")

    messages.info(
        request,
        "Hệ thống đang chờ ngân hàng xác nhận thanh toán."
    )

    return redirect(
        "bank_payment",
        order_id=order.id,
    )


# =========================================================
# CHI TIẾT / THEO DÕI ĐƠN HÀNG
# =========================================================

def order_tracking_detail(
    request,
    order_id
):

    order_ids = {
        str(item)
        for item in request.session.get(
            "order_ids",
            []
        )
    }

    last_order_id = request.session.get(
        "last_order_id"
    )

    if last_order_id:

        order_ids.add(
            str(last_order_id)
        )

    if str(order_id) not in order_ids:

        messages.error(
            request,
            "Bạn không có quyền xem đơn hàng này."
        )

        return redirect(
            "order_tracking"
        )

    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items"
        ),
        id=order_id
    )
    reviewed_item_ids = set(
        ProductReview.objects.filter(
            order=order,
            order_item__isnull=False
        ).values_list("order_item_id", flat=True)
    )

    return render(
        request,
        "order_tracking_detail.html",
        {
            "order": order,
            "reviewed_item_ids": reviewed_item_ids,
        }
    )

# =====================================================
# KHÁCH HÀNG ĐÁNH GIÁ SẢN PHẨM SAU KHI NHẬN HÀNG
# =====================================================

@require_POST
def submit_product_review(request, order_id, item_id):

    # 1. Kiểm tra đơn hàng có thuộc session của khách không
    order_ids = {
        str(item)
        for item in request.session.get("order_ids", [])
    }

    last_order_id = request.session.get("last_order_id")

    if last_order_id:
        order_ids.add(str(last_order_id))

    if str(order_id) not in order_ids:
        messages.error(
            request,
            "Bạn không có quyền đánh giá đơn hàng này."
        )
        return redirect("order_tracking")

    # 2. Lấy đơn hàng
    order = get_object_or_404(
        Order,
        id=order_id
    )

    # 3. Chỉ cho đánh giá khi đơn hàng hoàn thành
    if order.status != "completed":
        messages.warning(
            request,
            "Bạn chỉ có thể đánh giá sau khi đơn hàng hoàn thành."
        )
        return redirect(
            "order_tracking_detail",
            order_id=order.id
        )

    # 4. Xác minh sản phẩm thuộc đúng đơn hàng
    item = get_object_or_404(
        OrderItem.objects.select_related("product"),
        id=item_id,
        order=order,
        product__isnull=False
    )

    # 5. Không cho đánh giá trùng mặt hàng trong đơn
    if ProductReview.objects.filter(
        order_item=item
    ).exists():
        messages.warning(
            request,
            "Bạn đã đánh giá sản phẩm này trong đơn hàng."
        )
        return redirect(
            "order_tracking_detail",
            order_id=order.id
        )

    # 6. Kiểm tra số sao
    try:
        rating = int(request.POST.get("rating", "0"))
    except (TypeError, ValueError):
        rating = 0

    if rating not in range(1, 6):
        messages.error(
            request,
            "Vui lòng chọn số sao từ 1 đến 5."
        )
        return redirect(
            "order_tracking_detail",
            order_id=order.id
        )

    # 7. Kiểm tra nội dung
    comment = request.POST.get("comment", "").strip()

    if not comment:
        messages.error(
            request,
            "Vui lòng nhập nội dung đánh giá."
        )
        return redirect(
            "order_tracking_detail",
            order_id=order.id
        )

    # 8. Lưu đánh giá
    ProductReview.objects.create(
        product=item.product,
        order=order,
        order_item=item,
        reviewer_name=order.full_name,
        rating=rating,
        comment=comment,
        is_approved=True,
    )

    messages.success(
        request,
        "Cảm ơn bạn đã đánh giá sản phẩm tại MINOO!"
    )

    return redirect(
        "order_tracking_detail",
        order_id=order.id
    )
# =========================================================
# HỦY ĐƠN HÀNG
# =========================================================

def cancel_order(
    request,
    order_id
):

    if request.method != "POST":

        return redirect(
            "order_tracking_detail",
            order_id=order_id
        )

    order_ids = {
        str(item)
        for item in request.session.get(
            "order_ids",
            []
        )
    }

    last_order_id = request.session.get(
        "last_order_id"
    )

    if last_order_id:

        order_ids.add(
            str(last_order_id)
        )

    if str(order_id) not in order_ids:

        messages.error(
            request,
            "Bạn không có quyền hủy đơn hàng này."
        )

        return redirect(
            "order_tracking"
        )

    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items"
        ),
        id=order_id
    )

    if order.status != "pending":

        messages.warning(
            request,
            "Đơn hàng này không thể hủy ở trạng thái hiện tại."
        )

        return redirect(
            "order_tracking_detail",
            order_id=order.id
        )

    if order.payment_status == "paid":

        messages.warning(
            request,
            "Đơn hàng đã thanh toán không thể tự hủy."
        )

        return redirect(
            "order_tracking_detail",
            order_id=order.id
        )

    with transaction.atomic():

        order = (
            Order.objects
            .select_for_update()
            .prefetch_related(
                "items"
            )
            .get(
                pk=order.id
            )
        )

        if order.status != "pending":

            messages.warning(
                request,
                "Đơn hàng đã được xử lý và không thể hủy."
            )

            return redirect(
                "order_tracking_detail",
                order_id=order.id
            )

        for item in order.items.all():

            if item.variant_id:

                variant = (
                    ProductVariant.objects
                    .select_for_update()
                    .filter(
                        id=item.variant_id
                    )
                    .first()
                )

                if variant:

                    variant.stock += (
                        item.quantity
                    )

                    variant.save(
                        update_fields=[
                            "stock"
                        ]
                    )

            elif item.product_id:

                product = (
                    Product.objects
                    .select_for_update()
                    .filter(
                        id=item.product_id
                    )
                    .first()
                )

                if product:

                    product.stock += (
                        item.quantity
                    )

                    product.save(
                        update_fields=[
                            "stock"
                        ]
                    )

        order.status = "cancelled"

        order.save(
            update_fields=[
                "status",
                "updated_at",
            ]
        )

    messages.success(
        request,
        f"Đơn hàng {order.order_code} đã được hủy thành công."
    )

    return redirect(
        "order_tracking_detail",
        order_id=order.id
    )


# =========================================================
# ADMIN - XÓA ẢNH NHẬN DIỆN
# =========================================================

def _delete_recognition_image(path):

    if not path:
        return

    try:

        if default_storage.exists(path):

            default_storage.delete(
                path
            )

    except Exception:

        pass


# =========================================================
# ADMIN - LƯU ẢNH NHẬN DIỆN
# =========================================================

def _save_recognition_upload(
    uploaded_file
):

    original_name = Path(
        uploaded_file.name
    )

    extension = (
        original_name
        .suffix
        .lower()
    )

    allowed_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    ]

    if extension not in allowed_extensions:

        extension = ".jpg"

    filename = (
        f"{RECOGNITION_UPLOAD_DIR}/"
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    return default_storage.save(
        filename,
        uploaded_file
    )


# =========================================================
# ADMIN - HASH ẢNH TỪ IMAGE FIELD
# =========================================================

def _get_image_hash_from_field(
    image_field
):

    if not image_field:
        return None

    if not image_field.name:
        return None

    try:

        with image_field.storage.open(
            image_field.name,
            "rb"
        ) as image_file:

            with Image.open(
                image_file
            ) as image:

                image = image.convert(
                    "RGB"
                )

                return imagehash.phash(
                    image
                )

    except (
        FileNotFoundError,
        UnidentifiedImageError,
        OSError,
    ):

        return None


# =========================================================
# ADMIN - HASH ẢNH TỪ PATH
# =========================================================

def _get_image_hash_from_path(
    path
):

    try:

        with default_storage.open(
            path,
            "rb"
        ) as image_file:

            with Image.open(
                image_file
            ) as image:

                image = image.convert(
                    "RGB"
                )

                return imagehash.phash(
                    image
                )

    except (
        FileNotFoundError,
        UnidentifiedImageError,
        OSError,
    ):

        return None


# =========================================================
# ADMIN - LẤY URL ẢNH
# =========================================================

def _get_image_url(
    image_field
):

    if not image_field:
        return ""

    if not image_field.name:
        return ""

    try:

        return image_field.url

    except Exception:

        return ""


# =========================================================
# ADMIN - TÌM SẢN PHẨM TƯƠNG TỰ
# =========================================================

def _find_similar_products(
    image_path
):

    uploaded_hash = (
        _get_image_hash_from_path(
            image_path
        )
    )

    if uploaded_hash is None:

        return []

    products = (
        Product.objects
        .select_related(
            "category"
        )
        .prefetch_related(
            "images",
            "variants",
        )
        .filter(
            is_active=True
        )
    )

    results = []

    for product in products:

        product_best_distance = None

        product_best_url = ""

        product_best_source = ""

        # =================================================
        # 1. ẢNH CHÍNH
        # =================================================

        if product.image:

            product_hash = (
                _get_image_hash_from_field(
                    product.image
                )
            )

            if product_hash is not None:

                distance = (
                    uploaded_hash
                    - product_hash
                )

                if (
                    product_best_distance
                    is None
                    or distance
                    < product_best_distance
                ):

                    product_best_distance = (
                        distance
                    )

                    product_best_url = (
                        _get_image_url(
                            product.image
                        )
                    )

                    product_best_source = (
                        "Ảnh chính"
                    )

        # =================================================
        # 2. GALLERY
        # =================================================

        for product_image in (
            product.images.all()
        ):

            image_hash = (
                _get_image_hash_from_field(
                    product_image.image
                )
            )

            if image_hash is None:
                continue

            distance = (
                uploaded_hash
                - image_hash
            )

            if (
                product_best_distance
                is None
                or distance
                < product_best_distance
            ):

                product_best_distance = (
                    distance
                )

                product_best_url = (
                    _get_image_url(
                        product_image.image
                    )
                )

                product_best_source = (
                    "Ảnh sản phẩm"
                )

        # =================================================
        # 3. ẢNH BIẾN THỂ
        # =================================================

        for variant in (
            product.variants.all()
        ):

            if not variant.image:
                continue

            image_hash = (
                _get_image_hash_from_field(
                    variant.image
                )
            )

            if image_hash is None:
                continue

            distance = (
                uploaded_hash
                - image_hash
            )

            if (
                product_best_distance
                is None
                or distance
                < product_best_distance
            ):

                product_best_distance = (
                    distance
                )

                product_best_url = (
                    _get_image_url(
                        variant.image
                    )
                )

                product_best_source = (
                    "Ảnh biến thể"
                )

        # =================================================
        # CÓ ẢNH HỢP LỆ
        # =================================================

        if product_best_distance is None:
            continue

        similarity = max(
            0,
            100
            - (
                product_best_distance
                / 64
                * 100
            )
        )

        active_variants = [
            variant
            for variant
            in product.variants.all()
            if variant.is_active
        ]

        results.append(
            {
                "product": product,

                "distance": (
                    product_best_distance
                ),

                "similarity": round(
                    similarity,
                    1
                ),

                "image_url": (
                    product_best_url
                ),

                "source": (
                    product_best_source
                ),

                "variants": (
                    active_variants
                ),
            }
        )

    # =====================================================
    # SẮP XẾP
    # =====================================================

    results.sort(
        key=lambda item: item[
            "distance"
        ]
    )

    return results[:5]


# =========================================================
# CUSTOMER - LƯU ẢNH TÌM KIẾM
# =========================================================

def _save_customer_visual_search_upload(
    uploaded_file
):

    original_name = Path(
        uploaded_file.name
    )

    extension = (
        original_name
        .suffix
        .lower()
    )

    allowed_extensions = [
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    ]

    if extension not in allowed_extensions:
        extension = ".jpg"

    filename = (
        f"{CUSTOMER_VISUAL_SEARCH_UPLOAD_DIR}/"
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    return default_storage.save(
        filename,
        uploaded_file
    )


# =========================================================
# CUSTOMER - TÌM KÍNH BẰNG HÌNH ẢNH
# =========================================================

def customer_visual_search(request):
    """
    Cho khách hàng:
    - chụp ảnh từ điện thoại hoặc tải ảnh từ thiết bị;
    - kiểm tra ảnh hợp lệ;
    - dùng engine similarity hiện có của MINOO;
    - trả về tối đa 5 sản phẩm giống / tương tự nhất.

    Không yêu cầu đăng nhập và không thay đổi dữ liệu sản phẩm.
    """

    results = []
    preview_url = None
    searched = False
    error_message = ""

    # Nếu session còn ảnh tìm kiếm trước đó thì dùng để preview.
    saved_image_path = request.session.get(
        "customer_visual_search_path"
    )

    if saved_image_path:

        if default_storage.exists(
            saved_image_path
        ):

            preview_url = default_storage.url(
                saved_image_path
            )

        else:

            request.session.pop(
                "customer_visual_search_path",
                None
            )

            request.session.modified = True

    if request.method == "POST":

        searched = True

        uploaded_file = request.FILES.get(
            "image"
        )

        # =================================================
        # CHƯA CHỌN ẢNH
        # =================================================

        if not uploaded_file:

            error_message = (
                "Vui lòng chụp ảnh hoặc chọn ảnh kính "
                "trước khi tìm kiếm."
            )

            return render(
                request,
                "visual_search.html",
                {
                    "results": results,
                    "preview_url": preview_url,
                    "searched": searched,
                    "error_message": error_message,
                    "result_count": 0,
                }
            )

        # =================================================
        # GIỚI HẠN DUNG LƯỢNG ẢNH
        # =================================================

        if uploaded_file.size > MAX_VISUAL_SEARCH_UPLOAD_SIZE:

            error_message = (
                "Ảnh quá lớn. Vui lòng chọn ảnh có dung lượng "
                "không quá 8 MB."
            )

            return render(
                request,
                "visual_search.html",
                {
                    "results": results,
                    "preview_url": preview_url,
                    "searched": searched,
                    "error_message": error_message,
                    "result_count": 0,
                }
            )

        # =================================================
        # KIỂM TRA ẢNH HỢP LỆ
        # =================================================

        try:

            with Image.open(
                uploaded_file
            ) as image:

                image.verify()

            uploaded_file.seek(0)

        except (
            UnidentifiedImageError,
            OSError,
        ):

            error_message = (
                "File bạn chọn không phải hình ảnh hợp lệ. "
                "Vui lòng sử dụng JPG, JPEG, PNG hoặc WEBP."
            )

            return render(
                request,
                "visual_search.html",
                {
                    "results": results,
                    "preview_url": preview_url,
                    "searched": searched,
                    "error_message": error_message,
                    "result_count": 0,
                }
            )

        # =================================================
        # XÓA ẢNH TÌM KIẾM CŨ CỦA KHÁCH
        # =================================================

        old_path = request.session.get(
            "customer_visual_search_path"
        )

        if old_path:

            _delete_recognition_image(
                old_path
            )

        # =================================================
        # LƯU ẢNH MỚI
        # =================================================

        uploaded_file.seek(0)

        image_path = (
            _save_customer_visual_search_upload(
                uploaded_file
            )
        )

        request.session[
            "customer_visual_search_path"
        ] = image_path

        request.session.modified = True

        preview_url = default_storage.url(
            image_path
        )

        # =================================================
        # TÌM TOP 5 SẢN PHẨM TƯƠNG TỰ
        # =================================================

        results = (
            _find_similar_products(
                image_path
            )
        )

        # =================================================
        # GẮN NHÃN DỄ HIỂU CHO KHÁCH
        # =================================================

        for index, item in enumerate(
            results,
            start=1
        ):

            similarity = item.get(
                "similarity",
                0
            )

            item["rank"] = index

            if similarity >= 90:

                item["match_label"] = (
                    "Khả năng cao có mẫu tương ứng"
                )

            elif similarity >= 75:

                item["match_label"] = (
                    "Có mẫu tương tự"
                )

            elif similarity >= 55:

                item["match_label"] = (
                    "Mẫu gần giống"
                )

            else:

                item["match_label"] = (
                    "Độ tương đồng thấp"
                )

            item["in_stock"] = (
                item["product"].in_stock
            )

    return render(
        request,
        "visual_search.html",
        {
            "results": results,
            "preview_url": preview_url,
            "searched": searched,
            "error_message": error_message,
            "result_count": len(results),
        }
    )


# =========================================================
# ADMIN - TÌM KÍNH BẰNG HÌNH ẢNH
# =========================================================

@staff_member_required
def admin_product_recognition(
    request
):

    results = []

    matched = None

    scan_image_url = None

    if request.method == "POST":

        uploaded_file = (
            request.FILES.get(
                "image"
            )
        )

        if not uploaded_file:

            messages.error(
                request,
                "Vui lòng chọn hoặc chụp một hình ảnh."
            )

            return redirect(
                "admin:product_image_recognition"
            )

        # =================================================
        # KIỂM TRA ẢNH
        # =================================================

        try:

            with Image.open(
                uploaded_file
            ) as image:

                image.verify()

            uploaded_file.seek(0)

        except (
            UnidentifiedImageError,
            OSError,
        ):

            messages.error(
                request,
                "File bạn chọn không phải hình ảnh hợp lệ."
            )

            return redirect(
                "admin:product_image_recognition"
            )

        # =================================================
        # XÓA ẢNH CŨ
        # =================================================

        old_path = request.session.get(
            "recognition_image_path"
        )

        if old_path:

            _delete_recognition_image(
                old_path
            )

        # =================================================
        # LƯU ẢNH MỚI
        # =================================================

        uploaded_file.seek(0)

        image_path = (
            _save_recognition_upload(
                uploaded_file
            )
        )

        request.session[
            "recognition_image_path"
        ] = image_path

        request.session.modified = True

        # =================================================
        # TÌM SẢN PHẨM
        # =================================================

        results = (
            _find_similar_products(
                image_path
            )
        )

        scan_image_url = (
            default_storage.url(
                image_path
            )
        )

        # =================================================
        # SẢN PHẨM PHÙ HỢP NHẤT
        # =================================================

        if results:

            best_result = results[0]

            if (
                best_result["distance"]
                <= MATCH_DISTANCE_THRESHOLD
            ):

                matched = best_result

    else:

        image_path = request.session.get(
            "recognition_image_path"
        )

        if (
            image_path
            and default_storage.exists(
                image_path
            )
        ):

            scan_image_url = (
                default_storage.url(
                    image_path
                )
            )

    return render(
        request,
        "admin/product_recognition.html",
        {
            "title": "Tìm kính bằng hình ảnh",

            "results": results,

            "matched": matched,

            "scan_image_url": scan_image_url,

            "match_threshold": (
                MATCH_DISTANCE_THRESHOLD
            ),
        }
    )


# =========================================================
# ADMIN - CẬP NHẬT TỒN KHO
# =========================================================

@staff_member_required
def admin_product_recognition_update(
    request
):

    if request.method != "POST":

        return redirect(
            "admin:product_image_recognition"
        )

    product_id = request.POST.get(
        "product_id"
    )

    variant_id = request.POST.get(
        "variant_id"
    )

    quantity_raw = request.POST.get(
        "quantity"
    )

    # =====================================================
    # KIỂM TRA SỐ LƯỢNG
    # =====================================================

    try:

        quantity = int(
            quantity_raw
        )

        if quantity <= 0:

            raise ValueError

    except (
        TypeError,
        ValueError,
    ):

        messages.error(
            request,
            "Số lượng nhập thêm phải lớn hơn 0."
        )

        return redirect(
            "admin:product_image_recognition"
        )

    # =====================================================
    # CẬP NHẬT KHO
    # =====================================================

    try:

        with transaction.atomic():

            product = (
                Product.objects
                .select_for_update()
                .get(
                    pk=product_id
                )
            )

            # =================================================
            # CÓ VARIANT
            # =================================================

            if variant_id:

                variant = (
                    ProductVariant.objects
                    .select_for_update()
                    .get(
                        pk=variant_id,
                        product=product,
                    )
                )

                variant.stock += quantity

                variant.save(
                    update_fields=[
                        "stock"
                    ]
                )

                messages.success(
                    request,
                    (
                        f"Đã nhập thêm {quantity} sản phẩm "
                        f"cho biến thể "
                        f"'{variant.color or variant.sku}'. "
                        f"Tồn kho hiện tại: {variant.stock}."
                    )
                )

            # =================================================
            # KHÔNG CÓ VARIANT
            # =================================================

            else:

                product.stock += quantity

                product.save(
                    update_fields=[
                        "stock"
                    ]
                )

                messages.success(
                    request,
                    (
                        f"Đã nhập thêm {quantity} sản phẩm "
                        f"'{product.name}'. "
                        f"Tồn kho hiện tại: {product.stock}."
                    )
                )

    except Product.DoesNotExist:

        messages.error(
            request,
            "Không tìm thấy sản phẩm."
        )

    except ProductVariant.DoesNotExist:

        messages.error(
            request,
            "Không tìm thấy biến thể sản phẩm."
        )

    return redirect(
        "admin:product_image_recognition"
    )


# =========================================================
# ADMIN - THÊM SẢN PHẨM MỚI TỪ ẢNH
# =========================================================

@staff_member_required
def admin_product_recognition_create(
    request
):

    image_path = request.session.get(
        "recognition_image_path"
    )

    # =====================================================
    # KHÔNG CÓ ẢNH
    # =====================================================

    if (
        not image_path
        or not default_storage.exists(
            image_path
        )
    ):

        messages.warning(
            request,
            (
                "Ảnh nhận diện không còn tồn tại. "
                "Vui lòng chụp/tải ảnh lại."
            )
        )

        return redirect(
            "admin:product_image_recognition"
        )

    scan_image_url = (
        default_storage.url(
            image_path
        )
    )

    # =====================================================
    # POST - TẠO SẢN PHẨM
    # =====================================================

    if request.method == "POST":

        form = (
            AdminProductRecognitionCreateForm(
                request.POST
            )
        )

        if form.is_valid():

            product = form.save(
                commit=False
            )

            try:

                with default_storage.open(
                    image_path,
                    "rb"
                ) as image_file:

                    filename = Path(
                        image_path
                    ).name

                    product.image.save(
                        filename,
                        File(image_file),
                        save=False,
                    )

                    product.save()

                # ---------------------------------------------
                # XÓA ẢNH TẠM
                # ---------------------------------------------

                _delete_recognition_image(
                    image_path
                )

                request.session.pop(
                    "recognition_image_path",
                    None
                )

                request.session.modified = True

                messages.success(
                    request,
                    (
                        f"Đã thêm sản phẩm "
                        f"'{product.name}' thành công."
                    )
                )

                return redirect(
                    "admin:product_image_recognition"
                )

            except Exception as exc:

                messages.error(
                    request,
                    (
                        "Không thể lưu sản phẩm. "
                        f"Chi tiết: {exc}"
                    )
                )

    else:

        form = (
            AdminProductRecognitionCreateForm()
        )

    return render(
        request,
        "admin/product_recognition_create.html",
        {
            "title": "Thêm sản phẩm mới",

            "form": form,

            "scan_image_url": scan_image_url,
        }
    )
# =========================================================
# TRANG TRÒNG KÍNH
# =========================================================

def lenses(request):

    lens_products = (
        Product.objects
        .filter(
            is_active=True,
            category__name__icontains="tròng",
        )
        .select_related(
            "category"
        )
        .prefetch_related(
            "images",
            "variants",
        )
        .distinct()
        .order_by(
            "-created_at"
        )
    )

    return render(
        request,
        "lenses.html",
        {
            "products": lens_products,
        }
    )

#MÃ GIẢM GIÁ
def generate_coupon_code(prefix):
    while True:
        random_code = uuid.uuid4().hex[:6].upper()
        code = f'{prefix}-{random_code}'

        if not DiscountCoupon.objects.filter(code=code).exists():
            return code
@require_POST
def claim_discount(request):

    name = request.POST.get('name', '').strip()
    phone = request.POST.get('phone', '').strip()
    email = request.POST.get('email', '').strip()
    age_group = request.POST.get('age_group', '').strip()
    gender = request.POST.get('gender', '').strip()
    price_range = request.POST.get('price_range', '').strip()

    # Kiểm tra dữ liệu
    if not name:
        return JsonResponse({
            'success': False,
            'message': 'Vui lòng nhập họ tên.'
        })

    if not phone:
        return JsonResponse({
            'success': False,
            'message': 'Vui lòng nhập số điện thoại.'
        })

    if not age_group:
        return JsonResponse({
            'success': False,
            'message': 'Vui lòng chọn độ tuổi.'
        })

    if not gender:
        return JsonResponse({
            'success': False,
            'message': 'Vui lòng chọn giới tính.'
        })

    if not price_range:
        return JsonResponse({
            'success': False,
            'message': 'Vui lòng chọn mức giá quan tâm.'
        })

    # Tìm khách theo số điện thoại
    customer, created = PromotionCustomer.objects.get_or_create(
        phone=phone,
        defaults={
            'name': name,
            'email': email,
            'age_group': age_group,
            'gender': gender,
            'price_range': price_range,
        }
    )

    # Nếu khách đã tồn tại thì cập nhật
    if not created:

        customer.name = name

        if email:
            customer.email = email

        customer.age_group = age_group
        customer.gender = gender
        customer.price_range = price_range

        customer.save()

    # =====================================
    # ĐÃ HOÀN THÀNH CẢ 2 ĐƠN ƯU ĐÃI
    # → KHÔNG PHÁT THÊM MÃ MỚI
    # =====================================

    if customer.second_order_completed:

        request.session[
            'promotion_customer_id'
        ] = customer.id

        request.session.pop(
            'discount_coupon_code',
            None
        )

        request.session.pop(
            'applied_coupon_code',
            None
        )

        request.session.modified = True

        return JsonResponse({
            'success': False,
            'message': (
                'Bạn đã hoàn thành chương trình ưu đãi '
                '20% và 25% của MINOO.'
            )
        })

    # =====================================
    # KHÁCH CHƯA MUA ĐƠN ĐẦU
    # → NHẬN 20%
    # =====================================

    if not customer.first_order_completed:

        coupon = DiscountCoupon.objects.filter(
            customer=customer,
            coupon_type='FIRST',
            is_used=False,
            is_active=True,
        ).first()

        # Chưa có mã thì mới tạo
        if coupon is None:

            coupon = DiscountCoupon.objects.create(
                customer=customer,
                code=generate_coupon_code('MINOO20'),
                coupon_type='FIRST',
                discount_percent=20,
            )

    # =====================================
    # ĐÃ MUA ĐƠN ĐẦU
    # → NHẬN 25%
    # =====================================

    else:

        coupon = DiscountCoupon.objects.filter(
            customer=customer,
            coupon_type='SECOND',
            is_used=False,
            is_active=True,
        ).first()

        if coupon is None:

            coupon = DiscountCoupon.objects.create(
                customer=customer,
                code=generate_coupon_code('MINOO25'),
                coupon_type='SECOND',
                discount_percent=25,
            )

    # Lưu khách + coupon vào session
    request.session['promotion_customer_id'] = customer.id

    request.session['discount_coupon_code'] = coupon.code

    return JsonResponse({
        'success': True,
        'code': coupon.code,
        'discount_percent': coupon.discount_percent,
        'customer_name': customer.name,
    })


# =========================================================
# ÁP DỤNG / BỎ MÃ GIẢM GIÁ Ở CHECKOUT
# =========================================================

@require_POST
@login_required(login_url="login")
def apply_discount_coupon(request):

    coupon = get_customer_available_coupon(
        request
    )

    if coupon is None:

        return JsonResponse({
            "success": False,
            "message": (
                "Không tìm thấy mã giảm giá còn hiệu lực "
                "của tài khoản này."
            )
        })


    if (
        coupon.customer.user_id
        and coupon.customer.user_id
        != request.user.id
    ):

        return JsonResponse({
            "success": False,
            "message": (
                "Mã giảm giá không thuộc tài khoản này."
            )
        })


    action = request.POST.get(
        "action",
        "apply"
    ).strip()


    if action == "remove":

        request.session.pop(
            "applied_coupon_code",
            None
        )

        request.session.modified = True

        return JsonResponse({
            "success": True,
            "applied": False,
        })


    request.session[
        "applied_coupon_code"
    ] = coupon.code

    request.session[
        "discount_coupon_code"
    ] = coupon.code

    request.session[
        "promotion_customer_id"
    ] = coupon.customer_id

    request.session.modified = True


    return JsonResponse({
        "success": True,
        "applied": True,
        "code": coupon.code,
        "discount_percent":
            coupon.discount_percent,
    })


def register_view(request):

    next_url = (
        request.GET.get(
            "next"
        )
        or request.POST.get(
            "next"
        )
        or ""
    )


    # Nếu đã đăng nhập thì quay lại trang next hợp lệ.
    if request.user.is_authenticated:

        if (
            next_url
            and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={
                    request.get_host()
                },
                require_https=request.is_secure(),
            )
        ):

            return redirect(
                next_url
            )

        return redirect(
            "checkout"
        )


    # ==========================================
    # LẤY KHÁCH ƯU ĐÃI ĐÃ NHẬP TRƯỚC ĐÓ
    # ==========================================

    promotion_customer = None

    promotion_customer_id = (
        request.session.get(
            "promotion_customer_id"
        )
    )


    if promotion_customer_id:

        promotion_customer = (
            PromotionCustomer.objects.filter(
                id=promotion_customer_id
            ).first()
        )


    # ==========================================
    # SUBMIT FORM
    # ==========================================

    if request.method == "POST":

        form = RegisterForm(
            request.POST
        )


        if form.is_valid():

            name = (
                form.cleaned_data[
                    "name"
                ].strip()
            )

            email = (
                form.cleaned_data[
                    "email"
                ].strip().lower()
            )

            phone = (
                form.cleaned_data[
                    "phone"
                ].strip()
            )

            password = (
                form.cleaned_data[
                    "password1"
                ]
            )


            # ==================================
            # TẠO USER
            # username = email
            # ==================================

            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
            )

            user.first_name = name

            user.save()


            # ==================================
            # LIÊN KẾT VỚI KHÁCH ĐÃ NHẬN MÃ
            # ==================================

            customer = (
                PromotionCustomer.objects.filter(
                    phone=phone
                ).first()
            )


            if customer is None:

                customer = promotion_customer


            if customer:

                # Tránh gán đè profile đang thuộc tài khoản khác.
                if (
                    customer.user_id
                    and customer.user_id
                    != user.id
                ):

                    messages.warning(
                        request,
                        (
                            "Thông tin ưu đãi này đã được liên kết "
                            "với một tài khoản khác."
                        )
                    )

                else:

                    customer.user = user
                    customer.name = name
                    customer.email = email
                    customer.phone = phone

                    customer.save()


                    request.session[
                        "promotion_customer_id"
                    ] = customer.id


                    # Đồng bộ đúng coupon FIRST/SECOND
                    # theo trạng thái mua hàng của khách.
                    get_customer_available_coupon(
                        request
                    )


            # ==================================
            # ĐĂNG NHẬP LUÔN
            # ==================================

            login(
                request,
                user
            )


            messages.success(
                request,
                "Đăng ký tài khoản thành công."
            )


            if (
                next_url
                and url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={
                        request.get_host()
                    },
                    require_https=request.is_secure(),
                )
            ):

                return redirect(
                    next_url
                )


            return redirect(
                "checkout"
            )


    # ==========================================
    # LẦN ĐẦU MỞ FORM
    # ==========================================

    else:

        initial_data = {}


        if promotion_customer:

            initial_data = {
                "name":
                    promotion_customer.name,

                "email":
                    promotion_customer.email,

                "phone":
                    promotion_customer.phone,
            }


        form = RegisterForm(
            initial=initial_data
        )


    return render(
        request,
        "register.html",
        {
            "form": form,
            "next": next_url,
        }
    )



# =========================================================
# ĐĂNG NHẬP
# =========================================================

def login_view(request):

    next_url = (
        request.GET.get(
            "next"
        )
        or request.POST.get(
            "next"
        )
        or ""
    )


    # Nếu đã đăng nhập.
    if request.user.is_authenticated:

        if (
            next_url
            and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={
                    request.get_host()
                },
                require_https=request.is_secure(),
            )
        ):

            return redirect(
                next_url
            )

        return redirect(
            "home"
        )


    if request.method == "POST":

        email = request.POST.get(
            "email",
            ""
        ).strip().lower()

        password = request.POST.get(
            "password",
            ""
        )


        if not email:

            messages.error(
                request,
                "Vui lòng nhập email."
            )

        elif not password:

            messages.error(
                request,
                "Vui lòng nhập mật khẩu."
            )

        else:

            user = authenticate(
                request,
                username=email,
                password=password,
            )


            if user is not None:

                login(
                    request,
                    user
                )


                # ==================================
                # LIÊN KẾT PROFILE ƯU ĐÃI NẾU CÓ
                # ==================================

                promotion_customer_id = (
                    request.session.get(
                        "promotion_customer_id"
                    )
                )


                if promotion_customer_id:

                    customer = (
                        PromotionCustomer.objects.filter(
                            id=promotion_customer_id
                        ).first()
                    )


                    if customer:

                        # Chỉ tự liên kết khi profile chưa thuộc
                        # tài khoản khác và User này chưa có
                        # PromotionCustomer khác.
                        user_has_other_profile = (
                            PromotionCustomer.objects
                            .filter(
                                user=user
                            )
                            .exclude(
                                id=customer.id
                            )
                            .exists()
                        )


                        if (
                            not user_has_other_profile
                            and (
                                customer.user_id is None
                                or customer.user_id
                                == user.id
                            )
                        ):

                            customer.user = user

                            if (
                                not customer.email
                                and user.email
                            ):

                                customer.email = (
                                    user.email
                                )

                            customer.save()


                # Sau khi liên kết profile, đồng bộ lại
                # coupon 20% / 25% đúng với tài khoản.
                get_customer_available_coupon(
                    request
                )


                messages.success(
                    request,
                    "Đăng nhập thành công."
                )


                if (
                    next_url
                    and url_has_allowed_host_and_scheme(
                        url=next_url,
                        allowed_hosts={
                            request.get_host()
                        },
                        require_https=request.is_secure(),
                    )
                ):

                    return redirect(
                        next_url
                    )


                return redirect(
                    "home"
                )


            messages.error(
                request,
                "Email hoặc mật khẩu không đúng."
            )


    return render(
        request,
        "login.html",
        {
            "next": next_url,
        }
    )



def logout_view(request):

    logout(
        request
    )

    messages.success(
        request,
        'Bạn đã đăng xuất.'
    )

    return redirect(
        'home'
    )




@csrf_exempt
@require_POST
def sepay_webhook(request):
    """
    Nhận giao dịch từ SePay.
    Chỉ đánh dấu thanh toán sau khi xác minh chữ ký,
    mã đơn hàng, số tiền và mã giao dịch.
    """

    secret = getattr(
        settings,
        "SEPAY_WEBHOOK_SECRET",
        "",
    )

    if not secret:
        return JsonResponse(
            {
                "success": False,
                "message": "Webhook secret chưa được cấu hình",
            },
            status=503,
        )

    # 1. Đọc nguyên body để kiểm tra chữ ký HMAC.
    raw_body = request.body

    signature = request.headers.get(
        "X-SePay-Signature",
        "",
    )

    timestamp = request.headers.get(
        "X-SePay-Timestamp",
        "",
    )

    try:
        timestamp_int = int(timestamp)
    except (TypeError, ValueError):
        return JsonResponse(
            {"success": False, "message": "Timestamp không hợp lệ"},
            status=401,
        )

    # Chống request cũ bị gửi lại.
    if abs(int(time.time()) - timestamp_int) > 300:
        return JsonResponse(
            {"success": False, "message": "Webhook đã hết hạn"},
            status=401,
        )

    signed_data = timestamp.encode("utf-8") + b"." + raw_body

    expected_signature = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        signed_data,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(
        expected_signature,
        signature,
    ):
        return JsonResponse(
            {"success": False, "message": "Chữ ký không hợp lệ"},
            status=401,
        )

    # 2. Đọc payload JSON.
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse(
            {"success": False, "message": "JSON không hợp lệ"},
            status=400,
        )

    if not isinstance(payload, dict):
        return JsonResponse(
            {"success": False, "message": "Payload không hợp lệ"},
            status=400,
        )

    transaction_id = str(payload.get("id", "")).strip()
    transfer_type = str(
        payload.get("transferType", "")
    ).strip().lower()

    transfer_content = str(
        payload.get("content") or ""
    ).strip()

    # 3. Chỉ chấp nhận giao dịch tiền vào có ID hợp lệ.
    # ID 0 thường là payload gửi thử, không phải giao dịch thật
    # hoặc giao dịch mô phỏng đã được ghi nhận.
    if (
        not transaction_id.isdigit()
        or int(transaction_id) <= 0
        or transfer_type != "in"
        or not transfer_content
    ):
        return JsonResponse(
            {"success": False, "message": "Giao dịch không hợp lệ"},
            status=400,
        )

    try:
        transfer_amount = Decimal(
            str(payload.get("transferAmount"))
        )
    except (InvalidOperation, TypeError, ValueError):
        return JsonResponse(
            {"success": False, "message": "Số tiền không hợp lệ"},
            status=400,
        )

    if not transfer_amount.is_finite() or transfer_amount <= 0:
        return JsonResponse(
            {"success": False, "message": "Số tiền không hợp lệ"},
            status=400,
        )

    # 4. Nếu cấu hình tài khoản nhận, phải khớp số tài khoản.
    expected_account = getattr(
        settings,
        "SEPAY_EXPECTED_ACCOUNT_NUMBER",
        "",
    ).strip()

    received_account = str(
        payload.get("accountNumber") or ""
    ).strip()

    if (
            not expected_account
            or received_account != expected_account
    ):
        return JsonResponse(
            {"success": False, "message": "Sai tài khoản nhận"},
            status=400,
        )

    # 5. Nội dung chuyển khoản phải khớp chính xác mã đơn hàng.
    # QR MINOO hiện dùng order.order_code làm nội dung chuyển khoản.

    import re

    payment_code = str(payload.get("code") or "").strip().upper()

    # Mã thanh toán phải đúng cấu trúc MINOO + 8 ký tự HEX.
    if not re.fullmatch(r"MINOO[0-9A-F]{8}", payment_code):
        return JsonResponse(
            {"success": False, "message": "Mã thanh toán không hợp lệ"},
            status=400,
        )

    # Mã phải thực sự xuất hiện trong nội dung chuyển khoản.
    content_upper = transfer_content.upper()
    pattern = rf"(?<![A-Z0-9]){re.escape(payment_code)}(?![A-Z0-9])"

    if not re.search(pattern, content_upper):
        return JsonResponse(
            {"success": False, "message": "Mã đơn không khớp nội dung chuyển khoản"},
            status=400,
        )

    order = Order.objects.filter(
        order_code__iexact=payment_code,
        payment_method="bank",
    ).first()


    if order is None:
        return JsonResponse(
            {"success": False, "message": "Không tìm thấy đơn hàng"},
            status=404,
        )

    # Không cho thanh toán thiếu hoặc thừa số tiền đơn hàng.
    if transfer_amount != Decimal(str(order.total)):
        return JsonResponse(
            {"success": False, "message": "Số tiền không khớp"},
            status=400,
        )

    # 6. Chống xử lý lại cùng một giao dịch.
    if SePayTransaction.objects.filter(
        sepay_transaction_id=transaction_id
    ).exists():
        return JsonResponse({"success": True})

    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(
                pk=order.pk
            )

            # Không xác nhận thanh toán cho đơn đã hủy
            if order.status == "cancelled":
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Đơn hàng đã bị hủy",
                    },
                    status=409,
                )

            # Nếu đơn đã thanh toán, không ghi nhận lần nữa
            if order.payment_status == "paid":
                return JsonResponse({"success": True})
            SePayTransaction.objects.create(
                sepay_transaction_id=transaction_id,
                order=order,
                amount=transfer_amount,
                transfer_content=transfer_content,
            )

            order.payment_status = "paid"

            # Giữ trạng thái xử lý đơn theo luồng hiện tại của MINOO.
            order.save(
                update_fields=[
                    "payment_status",
                    "updated_at",
                ]
            )

    except IntegrityError:
        # Giao dịch có thể đã được xử lý ở request đồng thời khác.
        if SePayTransaction.objects.filter(
            sepay_transaction_id=transaction_id
        ).exists():
            return JsonResponse({"success": True})

        return JsonResponse(
            {"success": False, "message": "Không thể lưu giao dịch"},
            status=500,
        )

    return JsonResponse({"success": True})
@require_GET
def bank_payment_status(request, order_id):

    allowed_order_ids = {
        str(item)
        for item in request.session.get("order_ids", [])
    }

    last_order_id = request.session.get("last_order_id")

    if last_order_id:
        allowed_order_ids.add(str(last_order_id))

    if str(order_id) not in allowed_order_ids:
        return JsonResponse(
            {
                "paid": False,
                "message": "Không có quyền truy cập",
            },
            status=403,
        )

    order = get_object_or_404(
        Order,
        id=order_id,
        payment_method="bank",
    )

    return JsonResponse({
        "paid": order.payment_status == "paid",
        "payment_status": order.payment_status,
    })