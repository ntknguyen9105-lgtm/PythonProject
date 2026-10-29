from django.urls import path

from . import views
from . import chat_views


urlpatterns = [

    # =====================================================
    # TRANG CHỦ
    # =====================================================

    path(
        "",
        views.home,
        name="home"
    ),


    # =====================================================
    # SẢN PHẨM
    # =====================================================

    path(
        "gong-kinh/",
        views.products,
        name="products"
    ),

    path(
        "gong-kinh/<int:product_id>/",
        views.product_detail,
        name="product_detail"
    ),
    path(
    "tim-kinh-bang-anh/",
    views.customer_visual_search,
    name="customer_visual_search",
    ),


    # =====================================================
    # GIỎ HÀNG
    # =====================================================

    path(
        "gio-hang/",
        views.cart,
        name="cart"
    ),

    path(
        "gio-hang/chon-san-pham/",
        views.update_cart_selection,
        name="update_cart_selection"
    ),

    path(
        "gio-hang/them/<int:product_id>/",
        views.add_to_cart,
        name="add_to_cart"
    ),
    path(
        "mua-ngay/<int:product_id>/",
        views.buy_now,
        name="buy_now"
    ),
    path(
        "gio-hang/cap-nhat/<str:cart_key>/",
        views.update_cart,
        name="update_cart"
    ),

    path(
        "gio-hang/xoa/<str:cart_key>/",
        views.remove_from_cart,
        name="remove_from_cart"
    ),


    # =====================================================
    # THANH TOÁN / ĐẶT HÀNG
    # =====================================================

    path(
        "thanh-toan/",
        views.checkout,
        name="checkout"
    ),

    path(
        "thanh-toan-chuyen-khoan/<int:order_id>/",
        views.bank_payment,
        name="bank_payment"
    ),

    path(
        "thanh-toan-chuyen-khoan/<int:order_id>/xac-nhan/",
        views.confirm_bank_payment,
        name="confirm_bank_payment"
    ),
path(
    "api/sepay/webhook/",
    views.sepay_webhook,
    name="sepay_webhook",
),

path(
    "thanh-toan/chuyen-khoan/<int:order_id>/status/",
    views.bank_payment_status,
    name="bank_payment_status",
),

    path(
        "dat-hang-thanh-cong/",
        views.order_success,
        name="order_success"
    ),


    # =====================================================
    # ĐƠN HÀNG CỦA TÔI
    # =====================================================

    # Danh sách tất cả đơn hàng khách đã đặt
    path(
        "theo-doi-don-hang/",
        views.order_tracking,
        name="order_tracking"
    ),
    path(
        "theo-doi-don-hang/<int:order_id>/danh-gia/<int:item_id>/",
        views.submit_product_review,
        name="submit_product_review"
    ),

    # Chi tiết / theo dõi một đơn hàng
    path(
        "theo-doi-don-hang/<int:order_id>/",
        views.order_tracking_detail,
        name="order_tracking_detail"
    ),
    path(
        "theo-doi-don-hang/<int:order_id>/huy/",
        views.cancel_order,
        name="cancel_order"
    ),

    path(
    'trong-kinh/',
    views.lenses,
    name='lenses'
    ),
    # =====================================================
    # CHÍNH SÁCH
    # =====================================================

    path(
        "chinh-sach/",
        views.policy_index,
        name="policies"
    ),

    path(
        "chinh-sach/<slug:policy_slug>/",
        views.policy_detail,
        name="policy_detail"
    ),


    # =====================================================
    # VỀ CHÚNG TÔI
    # =====================================================

    path(
        "ve-chung-toi/",
        views.about,
        name="about"
    ),


    # =====================================================
    # LIÊN HỆ
    # =====================================================

    path(
        "lien-he/",
        views.contact,
        name="contact"
    ),


    # =====================================================
    # CHATBOT
    # =====================================================

    path(
        "chat/send/",
        chat_views.chat_send,
        name="chat_send"
    ),
    path(
        'nhan-uu-dai/',
        views.claim_discount,
        name='claim_discount'
    ),
    path(
    'dang-ky/',
    views.register_view,
    name='register'
    ),

    path(
    'dang-nhap/',
    views.login_view,
    name='login'
    ),

    path(
    'dang-xuat/',
    views.logout_view,
    name='logout'
    ),
    path(
    "ap-dung-ma-giam-gia/",
    views.apply_discount_coupon,
    name="apply_discount_coupon"
    ),
]

