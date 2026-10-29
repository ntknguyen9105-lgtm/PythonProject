# -*- coding: utf-8 -*-
"""
Nhận tin nhắn từ chatbot và lưu vào bảng ContactMessage (cùng nơi với form Liên hệ).
Đặt file này cạnh views.py trong app "store".
"""
import json
import time

from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import ContactMessage

MAX_PER_WINDOW = 8        # tối đa 8 tin / 10 phút cho mỗi người (chống spam)
WINDOW_SECONDS = 600


@require_POST
def chat_send(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "Dữ liệu không hợp lệ."}, status=400)

    name = (data.get("name") or "").strip()[:100]
    phone = (data.get("phone") or "").replace(" ", "").replace(".", "")
    message = (data.get("message") or "").strip()[:1000]

    if not name or not message:
        return JsonResponse({"ok": False, "error": "Vui lòng nhập đủ họ tên và nội dung."}, status=400)
    if not phone.isdigit() or not (9 <= len(phone) <= 11):
        return JsonResponse({"ok": False, "error": "Số điện thoại chưa đúng, bạn kiểm tra lại nhé."}, status=400)

    # Giới hạn tốc độ theo phiên (session)
    now = time.time()
    stamps = [t for t in request.session.get("chat_times", []) if now - t < WINDOW_SECONDS]
    if len(stamps) >= MAX_PER_WINDOW:
        return JsonResponse(
            {"ok": False, "error": "Bạn gửi hơi nhiều tin, vui lòng chờ một lát hoặc gọi hotline nhé."},
            status=429,
        )
    stamps.append(now)
    request.session["chat_times"] = stamps

    ContactMessage.objects.create(
        name=name,
        phone=phone,
        message=message,
        source="chat",
    )
    return JsonResponse({"ok": True})