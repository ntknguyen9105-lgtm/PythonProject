# MINOO EYEWEAR

## Nền tảng thương mại điện tử tích hợp quản lý danh mục kính

**MINOO Eyewear** là hệ thống thương mại điện tử được xây dựng nhằm hỗ trợ cửa hàng kính MINOO trong hoạt động bán hàng trực tuyến và quản lý tập trung danh mục sản phẩm.

Hệ thống cung cấp website dành cho khách hàng và khu vực quản trị dành cho nhân viên. Bên cạnh các chức năng thương mại điện tử như xem sản phẩm, giỏ hàng, checkout, đặt hàng và thanh toán, hệ thống còn hỗ trợ tìm kiếm sản phẩm bằng hình ảnh và kiểm tra mẫu kính tương tự trước khi nhân viên tạo hoặc cập nhật sản phẩm.

Dự án được phát triển bằng **Python và Django**, sử dụng **SQLite** làm cơ sở dữ liệu và được triển khai theo mô hình MVP phục vụ phát triển, kiểm thử và demo.

# 1. Bài toán của dự án

MINOO Eyewear cần giải quyết ba vấn đề chính trong hoạt động bán hàng và quản lý sản phẩm.

### Chưa có kênh bán hàng trực tuyến tập trung

Khách hàng chủ yếu tiếp cận sản phẩm qua cửa hàng hoặc các kênh mạng xã hội. Việc chưa có website thương mại điện tử riêng làm hạn chế khả năng khách hàng chủ động tìm kiếm, xem và đặt mua sản phẩm.

### Khó kiểm tra mẫu kính mới có trùng với danh mục hiện tại

Khi số lượng mẫu kính tăng, nhân viên phải dựa nhiều vào trí nhớ hoặc kiểm tra thủ công để xác định một mẫu kính mới đã tồn tại hay chưa. Điều này làm tăng thời gian xử lý và nguy cơ tạo dữ liệu sản phẩm trùng.

### Dữ liệu sản phẩm, tồn kho và đơn hàng cần được quản lý tập trung

Thông tin sản phẩm, biến thể, hình ảnh, số lượng tồn và đơn hàng cần được quản lý trên cùng một hệ thống để hạn chế sai lệch dữ liệu và hỗ trợ theo dõi hoạt động kinh doanh.

Từ các vấn đề trên, MINOO Eyewear được xây dựng theo hướng kết hợp:

**E-commerce Storefront + Catalog Management + Order Management + Image-assisted Checking**

# 2. Chức năng chính

## 2.1. Chức năng dành cho khách hàng

### Product Catalog

Khách hàng có thể:

- xem danh sách sản phẩm;
- tìm kiếm sản phẩm;
- lọc sản phẩm theo các tiêu chí được hỗ trợ;
- xem thông tin chi tiết sản phẩm;
- xem hình ảnh, giá bán, chất liệu, màu sắc và các thuộc tính liên quan;
- lựa chọn Product Variant;
- kiểm tra tình trạng còn hàng.

### Customer Visual Search

Khách hàng có thể tải hình ảnh một mẫu kính lên hệ thống để tìm các sản phẩm có hình ảnh tương tự trong danh mục.

Luồng xử lý:

```text
Customer Upload Image
        ↓
Image Processing
        ↓
Compare Product Images
        ↓
Similarity Result
        ↓
Relevant Products
```

Ảnh tìm kiếm chỉ được sử dụng để xử lý yêu cầu tìm kiếm và không tạo thành một Product mới trong Catalog.

### Shopping Cart

Khách hàng có thể:

- thêm sản phẩm vào giỏ hàng;
- lựa chọn Variant;
- cập nhật số lượng;
- xóa sản phẩm;
- kiểm tra tổng giá trị giỏ hàng.

Dữ liệu Cart được quản lý bằng Django Session.

Hệ thống kiểm tra số lượng đặt hàng để hạn chế trường hợp Quantity vượt quá Stock khả dụng.

### Customer Authentication

Khách hàng có thể duyệt sản phẩm và thao tác với Cart trước khi đăng nhập.

Khi thực hiện Checkout, khách hàng cần đăng nhập hoặc đăng ký tài khoản để tiếp tục quá trình đặt hàng.

### Checkout và Order

Tại Checkout, khách hàng cung cấp:

- họ tên;
- số điện thoại;
- email;
- địa chỉ nhận hàng;
- ghi chú nếu có;
- Coupon nếu đủ điều kiện;
- phương thức thanh toán.

Sau khi dữ liệu hợp lệ, hệ thống tạo:

- `Order`;
- các `OrderItem` tương ứng.

Đồng thời số lượng tồn kho của Product hoặc ProductVariant được cập nhật theo đơn hàng.

### Payment

Hệ thống hỗ trợ hai phương thức thanh toán:

#### Cash on Delivery – COD

Khách hàng thanh toán khi nhận hàng.

Order được tạo với phương thức thanh toán COD và tiếp tục được xử lý theo Order Status.

#### Bank Transfer / VietQR

Khách hàng có thể lựa chọn chuyển khoản ngân hàng.

Luồng xử lý:

```text
Checkout
   ↓
Create Order
   ↓
Bank Transfer / VietQR
   ↓
Customer Transfer
   ↓
SePay Webhook
   ↓
Transaction Reconciliation
   ↓
Update Payment Status
```

SePay được sử dụng để gửi thông tin giao dịch về hệ thống thông qua Webhook.

Khi giao dịch hợp lệ:

- hệ thống đối chiếu Order;
- kiểm tra số tiền;
- ghi nhận `SePayTransaction`;
- cập nhật `payment_status` của Order thành `paid`.

**Payment Status và Order Status được quản lý độc lập.**

### Order Tracking

Khách hàng có thể xem lại các đơn hàng đã tạo và theo dõi:

- Order Code;
- thông tin đơn hàng;
- tổng tiền;
- Payment Status;
- Order Status;
- chi tiết sản phẩm trong đơn.

## 2.2. Chức năng dành cho Staff/Admin

Khu vực quản trị được xây dựng trên Django Admin và các chức năng quản trị bổ sung.

Nhân viên có thể:

- đăng nhập khu vực quản trị;
- quản lý Category;
- quản lý Product;
- quản lý ProductVariant;
- quản lý ProductImage;
- quản lý giá bán;
- quản lý số lượng tồn kho;
- quản lý trạng thái hiển thị;
- xem danh sách Order;
- xem chi tiết Order;
- cập nhật trạng thái xử lý đơn hàng;
- quản lý PromotionCustomer;
- quản lý DiscountCoupon;
- theo dõi dữ liệu phục vụ Dashboard.

Dữ liệu được cập nhật trong Admin sử dụng cùng Database với Storefront nên các thay đổi về Product, Variant hoặc Stock có thể được phản ánh trực tiếp trên website khách hàng.

## 2.3. Admin Image-assisted Checking

Image-assisted Checking hỗ trợ nhân viên kiểm tra một mẫu kính mới trước khi thêm vào Product Catalog.

Quy trình:

```text
Nhập mẫu kính mới
        ↓
Chụp / Upload ảnh
        ↓
Image Processing
        ↓
Tìm sản phẩm tương tự
        ↓
Hiển thị Similarity Result
        ↓
Nhân viên kiểm tra
        ↓
     Mẫu đã có?
      /       \
    Có       Không
     ↓         ↓
  Update      Create
 Product      Product
```

Hệ thống chỉ cung cấp các sản phẩm có mức tương đồng để hỗ trợ ra quyết định.

**Quyết định một mẫu là sản phẩm đã tồn tại hay sản phẩm mới vẫn thuộc về nhân viên cửa hàng.**

Customer Visual Search và Admin Image-assisted Checking được triển khai thành hai luồng riêng:

- Customer Visual Search phục vụ tìm kiếm sản phẩm;
- Admin Image-assisted Checking phục vụ quản lý Catalog.

## 2.4. Promotion và Coupon

Hệ thống có các model:

- `PromotionCustomer`;
- `DiscountCoupon`.

PromotionCustomer lưu thông tin khách hàng tham gia chương trình ưu đãi.

DiscountCoupon được sử dụng để quản lý Coupon và các trạng thái liên quan như:

- mã Coupon;
- loại Coupon;
- phần trăm giảm giá;
- trạng thái Active;
- trạng thái đã sử dụng;
- thời điểm sử dụng.

Khi khách hàng nhập Coupon tại Checkout, Backend thực hiện kiểm tra điều kiện trước khi áp dụng giảm giá vào đơn hàng.

## 2.5. Management Dashboard

Khu vực quản trị có Dashboard tổng hợp dữ liệu trực tiếp từ Database.

Các chỉ số được tổng hợp từ các nhóm dữ liệu như:

- Order;
- OrderItem;
- PromotionCustomer;
- DiscountCoupon.

Dashboard hỗ trợ theo dõi các thông tin cơ bản như:

- số khách hàng;
- số đơn hàng hợp lệ;
- doanh thu;
- Average Order Value;
- phân khúc khách hàng;
- mức giá quan tâm;
- hiệu quả Coupon;
- sản phẩm bán nhiều;
- các đơn hàng gần đây.

Dashboard không sử dụng một bảng dữ liệu KPI riêng mà tính toán các chỉ số từ dữ liệu nghiệp vụ hiện có.

# 3. Cấu trúc dữ liệu chính

Các Entity/Model cốt lõi của hệ thống gồm:

| Model | Vai trò |
|---|---|
| User | Tài khoản khách hàng và quyền quản trị |
| Category | Danh mục sản phẩm |
| Product | Thông tin sản phẩm và Stock cấp Product |
| ProductVariant | Biến thể và Stock cấp Variant |
| ProductImage | Hình ảnh chi tiết sản phẩm |
| Order | Thông tin đơn hàng và trạng thái |
| OrderItem | Chi tiết sản phẩm thuộc Order |
| PromotionCustomer | Hồ sơ khách hàng tham gia ưu đãi |
| DiscountCoupon | Coupon và trạng thái sử dụng |
| SePayTransaction | Giao dịch SePay liên kết với Order |

Ngoài các thành phần cốt lõi, source hiện tại còn có một số model mở rộng như:

- `ProductReview`;
- `ContactMessage`;
- quan hệ Upsell/Cross-sell giữa các Product.

### Inventory

Hệ thống không sử dụng một bảng Inventory riêng.

Tồn kho được lưu trực tiếp tại:

```text
Product.stock
ProductVariant.stock
```

### Cart

Shopping Cart được quản lý bằng Django Session và không có bảng Cart vật lý trong SQLite.

### Order và Customer

Order hiện lưu trực tiếp các thông tin giao nhận như:

- `full_name`;
- `phone`;
- `email`;
- `address`.

Order hiện không sử dụng Foreign Key trực tiếp tới Django User.

# 4. Công nghệ sử dụng

| Thành phần | Công nghệ |
|---|---|
| Programming Language | Python |
| Backend Framework | Django 4.2 |
| Frontend | HTML, CSS, JavaScript |
| Template Engine | Django Templates |
| Database | SQLite |
| Database Access | Django ORM |
| Image Processing | Pillow, ImageHash |
| Authentication | Django Authentication |
| Payment Integration | SePay Webhook |
| IDE | PyCharm |
| Version Control | Git / GitHub |
| Development Server | Django Development Server |

Kiến trúc tổng quát:

```text
Customer / Admin Browser
          ↓
     URL Routing
          ↓
     Django Views
          ↓
    Business Logic
          ↓
      Django ORM
          ↓
        SQLite
```

Với Payment:

```text
Customer
   ↓
MINOO Django Application
   ↓
Order / VietQR

SePay
   ↓ Webhook
MINOO Django Application
   ↓
SePayTransaction + Order Payment Status
```

# 5. Cấu trúc project

Cấu trúc chính của project:

```text
PythonProject/
│
├── manage.py
├── db.sqlite3
│
├── minoo/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
│
├── store/
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── chat_views.py
│   ├── context_processors.py
│   ├── forms.py
│   ├── image_similarity.py
│   ├── models.py
│   ├── policies.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
│
├── templates/
├── static/
└── media/
```

## Các thành phần chính

### `minoo/`

Chứa cấu hình Django project:

- project settings;
- URL cấp project;
- ASGI;
- WSGI.

### `store/`

Application chính của MINOO Eyewear, chứa:

- Model;
- View;
- Admin;
- Forms;
- URL Routing;
- Image Similarity;
- Business Logic;
- Migration.

### `store/models.py`

Định nghĩa các model và quan hệ dữ liệu của hệ thống.

### `store/views.py`

Xử lý các nghiệp vụ phía Customer như:

- Product;
- Cart;
- Authentication;
- Checkout;
- Order;
- Payment;
- Order Tracking;
- Promotion;
- Customer Visual Search.

### `store/admin.py`

Xử lý khu vực quản trị gồm:

- Product Management;
- Variant/Stock Management;
- Order Management;
- Image-assisted Checking;
- Dashboard.

### `store/image_similarity.py`

Chứa logic hỗ trợ xử lý và so sánh hình ảnh sản phẩm.

### `store/migrations/`

Lưu lịch sử thay đổi Database Schema.

### `templates/`

Chứa các Django Template được sử dụng cho giao diện Customer.

Ví dụ:

```text
home.html
products.html
product_detail.html
visual_search.html
cart.html
checkout.html
bank_payment.html
order_success.html
order_tracking.html
order_tracking_detail.html
login.html
register.html
```

### `static/`

Chứa CSS, JavaScript và các tài nguyên tĩnh của website.

### `media/`

Chứa các file hình ảnh được upload trong quá trình sử dụng hệ thống.

### `db.sqlite3`

Cơ sở dữ liệu SQLite được sử dụng trong môi trường phát triển, kiểm thử và demo.

# Nhóm phát triển

Dự án được thực hiện bởi **nhóm 2 thành viên** trong học phần **Quản trị dự án thương mại điện tử**.

**Đề tài:**

**Phát triển nền tảng thương mại điện tử tích hợp quản lý danh mục kính cho cửa hàng MINOO Eyewear**
