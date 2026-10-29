/* =====================================================
   MINOO – CHATBOT (chatwidget.js)
   Bot trả lời nhanh các câu hỏi thường gặp.
   Khi khách nhắn nội dung riêng -> xin tên + SĐT -> lưu vào admin.
===================================================== */
(function () {
    var root = document.getElementById('cw');
    if (!root) return;

    var cfg    = root.dataset;
    var body   = root.querySelector('.cw-body');
    var form   = root.querySelector('.cw-form');
    var input  = root.querySelector('.cw-input');
    var sendBtn = root.querySelector('.cw-send');
    var openBtn = root.querySelector('.cw-btn-chat');
    var closeBtn = root.querySelector('.cw-close');
    var token  = (root.querySelector('[name=csrfmiddlewaretoken]') || {}).value || '';

    var stage = 'idle';      // idle | ask_name | ask_phone
    var pending = '';        // tin nhắn đầu tiên chờ gửi
    var greeted = false;
    var user = loadUser();

    function loadUser() {
        try { return JSON.parse(localStorage.getItem('minoo_chat_user')) || {}; }
        catch (e) { return {}; }
    }
    function saveUser() {
        try { localStorage.setItem('minoo_chat_user', JSON.stringify(user)); } catch (e) {}
    }

    function el(tag, cls) {
        var n = document.createElement(tag);
        if (cls) n.className = cls;
        return n;
    }

    function addMsg(text, who, links) {
        var row = el('div', 'cw-msg ' + who);
        var bubble = el('div', 'cw-bubble');
        bubble.textContent = text;                       // textContent: chống chèn mã độc
        (links || []).forEach(function (l) {
            bubble.appendChild(document.createElement('br'));
            var a = el('a', 'cw-link');
            a.href = l.href;
            a.textContent = l.label;
            if (l.ext) { a.target = '_blank'; a.rel = 'noopener noreferrer'; }
            bubble.appendChild(a);
        });
        row.appendChild(bubble);
        body.appendChild(row);
        body.scrollTop = body.scrollHeight;
    }

    var replies = {
        address: function () {
            addMsg('MINOO Eyewear ở ' + cfg.address + '.', 'bot',
                [{ label: 'Chỉ đường trên Google Maps', href: cfg.map, ext: true }]);
        },
        products: function () {
            addMsg('Bạn có thể xem các mẫu gọng kính tại đây:', 'bot',
                [{ label: 'Xem gọng kính', href: cfg.products }]);
        },
        policy: function () {
            addMsg('Chính sách thanh toán, giao hàng, đổi trả, bảo hành và bảo mật:', 'bot',
                [{ label: 'Xem chính sách', href: cfg.policies }]);
        },
        hotline: function () {
            addMsg('Bạn có thể gọi hotline ' + cfg.hotline + ' để được hỗ trợ.', 'bot',
                [{ label: 'Gọi ngay', href: 'tel:' + cfg.hotlineRaw }]);
        },
        staff: function () {
            addMsg('Bạn cứ nhập nội dung cần tư vấn ở ô bên dưới, MINOO sẽ liên hệ lại với bạn.', 'bot');
            input.focus();
        }
    };

    root.querySelectorAll('.cw-chip').forEach(function (chip) {
        chip.addEventListener('click', function () {
            addMsg(chip.textContent, 'user');
            replies[chip.dataset.key]();
        });
    });

    function openChat() {
        root.classList.add('open', 'opened');
        openBtn.setAttribute('aria-expanded', 'true');
        if (!greeted) {
            greeted = true;
            addMsg('Xin chào! MINOO Eyewear có thể giúp gì cho bạn? Bạn chọn nhanh bên dưới hoặc nhắn trực tiếp nhé.', 'bot');
        }
        setTimeout(function () { input.focus(); }, 50);
    }
    function closeChat() {
        root.classList.remove('open');
        openBtn.setAttribute('aria-expanded', 'false');
        openBtn.focus();
    }

    openBtn.addEventListener('click', function () {
        root.classList.contains('open') ? closeChat() : openChat();
    });
    closeBtn.addEventListener('click', closeChat);
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && root.classList.contains('open')) closeChat();
    });

    function send(message) {
        sendBtn.disabled = true;
        fetch(cfg.endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
            body: JSON.stringify({ name: user.name, phone: user.phone, message: message })
        })
        .then(function (r) { return r.json().then(function (d) { return { status: r.status, data: d }; }); })
        .then(function (res) {
            if (res.data && res.data.ok) {
                addMsg('MINOO đã nhận được tin nhắn và sẽ liên hệ lại với bạn sớm nhất. Cảm ơn bạn!', 'bot');
            } else {
                addMsg((res.data && res.data.error) || 'Chưa gửi được tin nhắn, bạn vui lòng thử lại hoặc gọi hotline ' + cfg.hotline + '.', 'bot');
            }
        })
        .catch(function () {
            addMsg('Chưa gửi được tin nhắn, bạn vui lòng thử lại hoặc gọi hotline ' + cfg.hotline + '.', 'bot');
        })
        .then(function () { sendBtn.disabled = false; input.focus(); });
    }

    form.addEventListener('submit', function (e) {
        e.preventDefault();
        var text = input.value.trim();
        if (!text) return;
        input.value = '';
        addMsg(text, 'user');

        if (stage === 'ask_name') {
            user.name = text.slice(0, 100);
            stage = 'ask_phone';
            addMsg('Cảm ơn ' + user.name + '! Cho MINOO xin số điện thoại để liên hệ lại nhé.', 'bot');
            return;
        }
        if (stage === 'ask_phone') {
            var p = text.replace(/[\s.]/g, '');
            if (!/^\d{9,11}$/.test(p)) {
                addMsg('Số điện thoại chưa đúng, bạn kiểm tra lại giúp MINOO nhé.', 'bot');
                return;
            }
            user.phone = p;
            saveUser();
            stage = 'idle';
            send(pending);
            pending = '';
            return;
        }
        if (!user.name || !user.phone) {
            pending = text;
            stage = 'ask_name';
            addMsg('MINOO đã nhận được tin nhắn của bạn. Bạn cho MINOO xin họ tên nhé?', 'bot');
        } else {
            send(text);
        }
    });
})();