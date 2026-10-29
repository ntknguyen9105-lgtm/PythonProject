from pathlib import Path

import imagehash
from PIL import Image, UnidentifiedImageError

from django.conf import settings

from .models import Product, ProductImage, ProductVariant


# =========================================================
# CẤU HÌNH
# =========================================================

# Khoảng cách càng nhỏ = ảnh càng giống
# 0 = gần như giống hoàn toàn
SIMILARITY_THRESHOLD = 12

# Số kết quả tương đồng tối đa
MAX_RESULTS = 5


# =========================================================
# MỞ ẢNH
# =========================================================

def open_image(image_path):
    """
    Mở ảnh và chuyển sang RGB.
    """

    try:
        image = Image.open(image_path)
        image = image.convert("RGB")
        return image

    except (
        FileNotFoundError,
        UnidentifiedImageError,
        OSError,
    ):
        return None


# =========================================================
# TÍNH PERCEPTUAL HASH
# =========================================================

def calculate_image_hash(image):
    """
    Tính perceptual hash cho ảnh.

    pHash giúp nhận biết các ảnh có nội dung
    hình ảnh tương tự nhau dù kích thước hoặc
    độ nén khác nhau.
    """

    return imagehash.phash(image)


# =========================================================
# LẤY ĐƯỜNG DẪN FILE
# =========================================================

def get_field_path(field_file):
    """
    Lấy đường dẫn thật của ImageField.
    """

    if not field_file:
        return None

    try:
        return Path(field_file.path)

    except (
        ValueError,
        AttributeError,
        OSError,
    ):
        return None


# =========================================================
# TÌM ẢNH TƯƠNG ĐỒNG
# =========================================================

def find_similar_products(uploaded_file):
    """
    Tìm các sản phẩm có hình ảnh tương đồng
    với ảnh admin tải lên.

    Trả về danh sách:

    [
        {
            "product": product,
            "score": score,
            "similarity": similarity,
            "matched_image": image,
            "source": "main/gallery/variant",
        }
    ]
    """

    # -----------------------------------------------------
    # LƯU FILE TẠM THỜI
    # -----------------------------------------------------

    temp_dir = Path(settings.MEDIA_ROOT) / "image_search"

    temp_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    temp_path = (
        temp_dir
        / uploaded_file.name
    )

    with open(
        temp_path,
        "wb+"
    ) as destination:

        for chunk in uploaded_file.chunks():

            destination.write(chunk)

    # -----------------------------------------------------
    # MỞ ẢNH TÌM KIẾM
    # -----------------------------------------------------

    search_image = open_image(
        temp_path
    )

    if search_image is None:

        try:
            temp_path.unlink()
        except OSError:
            pass

        return []

    search_hash = calculate_image_hash(
        search_image
    )

    results = {}

    # =====================================================
    # DUYỆT SẢN PHẨM
    # =====================================================

    products = (
        Product.objects
        .filter(is_active=True)
        .prefetch_related(
            "images",
            "variants"
        )
    )

    for product in products:

        best_score = None
        best_image = None
        best_source = None

        # -------------------------------------------------
        # ẢNH ĐẠI DIỆN
        # -------------------------------------------------

        if product.image:

            image_path = get_field_path(
                product.image
            )

            if image_path:

                image = open_image(
                    image_path
                )

                if image:

                    image_hash = calculate_image_hash(
                        image
                    )

                    score = search_hash - image_hash

                    if (
                        best_score is None
                        or score < best_score
                    ):

                        best_score = score
                        best_image = product.image
                        best_source = "main"

        # -------------------------------------------------
        # ẢNH GALLERY
        # -------------------------------------------------

        for product_image in product.images.all():

            if not product_image.image:
                continue

            image_path = get_field_path(
                product_image.image
            )

            if not image_path:
                continue

            image = open_image(
                image_path
            )

            if not image:
                continue

            image_hash = calculate_image_hash(
                image
            )

            score = search_hash - image_hash

            if (
                best_score is None
                or score < best_score
            ):

                best_score = score
                best_image = product_image.image
                best_source = "gallery"

        # -------------------------------------------------
        # ẢNH BIẾN THỂ
        # -------------------------------------------------

        for variant in product.variants.all():

            if not variant.image:
                continue

            image_path = get_field_path(
                variant.image
            )

            if not image_path:
                continue

            image = open_image(
                image_path
            )

            if not image:
                continue

            image_hash = calculate_image_hash(
                image
            )

            score = search_hash - image_hash

            if (
                best_score is None
                or score < best_score
            ):

                best_score = score
                best_image = variant.image
                best_source = "variant"

        # -------------------------------------------------
        # KHÔNG CÓ ẢNH
        # -------------------------------------------------

        if best_score is None:
            continue

        # -------------------------------------------------
        # TÍNH % TƯƠNG ĐỒNG
        # -------------------------------------------------

        similarity = max(
            0,
            round(
                (
                    1
                    - (
                        best_score
                        / 64
                    )
                )
                * 100
            )
        )

        results[product.id] = {
            "product": product,
            "score": best_score,
            "similarity": similarity,
            "matched_image": best_image,
            "source": best_source,
        }

    # =====================================================
    # SẮP XẾP
    # =====================================================

    results = sorted(
        results.values(),
        key=lambda item: item["score"]
    )

    # =====================================================
    # LỌC NHỮNG ẢNH QUÁ KHÁC
    # =====================================================

    similar_results = [
        result
        for result in results
        if result["score"]
        <= SIMILARITY_THRESHOLD
    ]

    # =====================================================
    # GIỚI HẠN KẾT QUẢ
    # =====================================================

    similar_results = similar_results[
        :MAX_RESULTS
    ]

    # -----------------------------------------------------
    # XÓA FILE TẠM
    # -----------------------------------------------------

    try:
        temp_path.unlink()

    except OSError:
        pass

    return similar_results