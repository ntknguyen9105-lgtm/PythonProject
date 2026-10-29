def cart_count(request):
    """
    Tính tổng số lượng sản phẩm trong giỏ hàng
    từ session của người dùng.
    """

    cart = request.session.get("cart", {})

    total = 0

    for item in cart.values():

        try:
            quantity = int(item.get("quantity", 0))
        except (ValueError, TypeError):
            quantity = 0

        if quantity > 0:
            total += quantity

    return {
        "cart_count": total,
    }