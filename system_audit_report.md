با احترام،
تحلیل جامع سیستم بر اساس کد موجود به شرح زیر ارائه می‌گردد.

### A) Executive Summary (خلاصه مدیریتی)

**وضعیت کلی سیستم:** **نیازمند اصلاحات حیاتی (Critical Fixes Required)**. معماری سیستم بر پایه Django و DRF استاندارد و قابل قبول است، اما چندین ریسک عملیاتی و امنیتی مهم در منطق اصلی فروشگاهی (Inventory, Payment) شناسایی شد که می‌توانند منجر به ضرر مالی و خدشه‌دار شدن اعتبار داده‌ها شوند. زیرساخت observability و تست ضعیف است و نیازمند توجه فوری می‌باشد.

**3 ریسک حیاتی اول:**
1.  **ریسک مالی (Overselling):** عدم وجود قفل اتمیک بر روی موجودی کالا در هنگام ثبت سفارش، امکان فروش یک کالا به چند مشتری به صورت همزمان (Race Condition) را فراهم می‌کند که مستقیماً منجر به ضرر مالی و نارضایتی مشتری می‌شود.
2.  **ریسک امنیتی/مالی (Payment Spoofing):** وب‌هوک تایید پرداخت فاقد اعتبارسنجی امضا (signature validation) است. این ضعف به مهاجم اجازه می‌دهد تا با ارسال یک درخواست جعلی، سفارش‌ها را بدون پرداخت واقعی به وضعیت "پرداخت شده" تغییر دهد.
3.  **ریسک داده (IDOR Vulnerability):** کاربران می‌توانند با حدس زدن UUID، به اطلاعات سفارش‌های دیگر کاربران دسترسی پیدا کنند که نقض حریم خصوصی و محرمانگی داده‌ها است.

**3 پیشنهاد فوری:**
1.  **پیاده‌سازی قفل موجودی:** استفاده از `select_for_update()` در ترکنش ثبت سفارش برای جلوگیری از oversell.
2.  **امن‌سازی Webhook پرداخت:** اضافه کردن مکانیزم اعتبارسنجی امضای دیجیتال یا secret key برای تمام درخواست‌های ورودی به وب‌هوک.
3.  **رفع حفره کنترل دسترسی (IDOR):** اطمینان از اینکه تمام کوئری‌های مربوط به سفارش‌ها، سبد خرید و پروفایل کاربر بر اساس `request.user` فیلتر می‌شوند.

---

### B) System Map (نقشه سیستم)

**Tech Stack & Entry Points:**
*   **فریم‌ورک:** Django, Django REST Framework (DRF)
*   **ORM/DB Driver:** Django ORM / `psycopg2-binary` (PostgreSQL)
*   **Queue:** Celery (`celery`)
*   **Cache:** Redis (`redis`)
*   **Payment SDKs:** به نظر می‌رسد یکپارچه‌سازی به صورت مستقیم و بدون SDK رسمی انجام شده است (در `payment/services.py` با `requests` کار می‌کند).
*   **نقطه ورود درخواست‌ها:** `ecommerce_api/urls.py` که درخواست‌ها را به `urls.py` هر اپلیکیشن (module) توزیع می‌کند. مثال: `/api/v1/shop/`, `/api/v1/orders/`.
*   **Middlewares/Guards:**
    *   `django.middleware.security.SecurityMiddleware`
    *   `django.contrib.auth.middleware.AuthenticationMiddleware`
    *   `django.middleware.common.CommonMiddleware`
    *   (لیست کامل در `ecommerce_api/settings/base.py` -> `MIDDLEWARE`)

**Domain Modules:**

*   **محصولات/واریانت/SKU:**
    *   `shop/models.py` -> `Product`, `ProductVariant`
    *   `shop/views.py` -> `ProductViewSet`, `ProductVariantViewSet`
*   **موجودی/انبار:**
    *   `inventory/models.py` -> `Inventory` (با ارتباط OneToOne به `ProductVariant`)
    *   منطق کاهش موجودی در `orders/services.py` -> `OrderService.create_order`
*   **سبد خرید (Cart):**
    *   `cart/models.py` -> `Cart`, `CartItem` (برای کاربران لاگین کرده)
    *   `cart/cart.py` -> `Cart` (کلاس مدیریت سبد خرید مبتنی بر session برای کاربران مهمان)
    *   `cart/views.py` -> `CartViewSet`
*   **سفارش‌ها (Orders):**
    *   `orders/models.py` -> `Order`, `OrderItem`
    *   `orders/views.py` -> `OrderViewSet`
    *   `orders/services.py` -> `OrderService` (منطق اصلی ساخت سفارش)
*   **پرداخت (Payment):**
    *   `payment/models.py` -> `Payment`
    *   `payment/views.py` -> `PaymentViewSet`, `PaymentWebhookView`
    *   `payment/services.py` -> `ZibalGateway` (ارتباط با درگاه پرداخت)
*   **ارسال (Shipping):**
    *   `shipping/models.py` -> `Shipping`, `ShippingMethod`
    *   `shipping/views.py` -> `ShippingViewSet`
    *   `shipping/services.py` -> `PostexService`
*   **تخفیف/کوپن (Coupon):**
    *   `coupon/models.py` -> `Coupon`
    *   `coupon/views.py` -> `CouponViewSet` (شامل `apply` و `unapply`)
*   **مرجوعی/ریفاند (Refund):**
    *   **NOT FOUND IN CODE**
*   **کیف پول/اعتبار (Wallet):**
    *   **NOT FOUND IN CODE**

---

### C) Domain Correctness Audit (صحت عملکرد فروشگاهی)

*   **Pricing:**
    *   **منبع قیمت و جلوگیری از دستکاری:** **OK**. قیمت از `ProductVariant` خوانده شده و در `OrderItem` در زمان ثبت سفارش کپی (snapshot) می‌شود (`orders/models.py` -> `OrderItem.price`). این کار از تغییر قیمت پس از ثبت سفارش جلوگیری می‌کند.
    *   **محاسبه تخفیف و گرد کردن:** **PARTIAL**. منطق اعمال کوپن در `coupon/services.py` -> `CouponService` وجود دارد، اما هیچ منطق مشخصی برای مدیریت rounding یا سناریوهای پیچیده مالیاتی دیده نمی‌شود.
    *   **مالیات/ارسال:** **PARTIAL**. هزینه ارسال در `Order` مدل (`shipping_cost`) ذخیره می‌شود اما منطق محاسبه آن (مثلاً بر اساس وزن یا مقصد) در `shipping/services.py` به سرویس خارجی Postex واگذار شده و شفافیت کامل از روی کد ندارد. منطق مالیات یافت نشد.

*   **Inventory & Oversell Prevention:**
    *   **قفل/رزرو موجودی:** **BROKEN**. در `orders/services.py` -> `OrderService.create_order`، موجودی (`Inventory.stock`) خوانده، چک شده و سپس کم می‌شود، اما این عملیات فاقد قفل اتمیک (مانند `select_for_update`) است که آن را در برابر race condition آسیب‌پذیر می‌کند.
    *   **رفتار در رقابت همزمان (Concurrency):** **BROKEN**. دو درخواست همزمان برای خرید آخرین قلم یک کالا می‌توانند هر دو از شرط `if item.inventory.stock < cart_item.quantity:` عبور کرده و منجر به منفی شدن موجودی یا oversell شوند.
    *   **Rollback در خطای پرداخت:** **OK**. کل فرآیند ساخت سفارش در یک `transaction.atomic` قرار دارد (`orders/services.py`). اگر در هر مرحله‌ای، از جمله ارتباط با درگاه پرداخت، خطایی رخ دهد، تمام تغییرات (شامل کاهش موجودی) باید rollback شود.
    *   **سیاست Stock Reservation Expiry:** **NOT FOUND IN CODE**. هیچ مکانیزمی برای رزرو موقت موجودی (مثلاً برای 15 دقیقه پس از ورود به صفحه پرداخت) و آزادسازی آن در صورت عدم پرداخت وجود ندارد.

*   **Cart → Order Integrity:**
    *   **تبدیل سبد به سفارش:** **OK**. در زمان ساخت `OrderItem`، اطلاعات کلیدی مانند `price`, `weight` از روی `ProductVariant` کپی (snapshot) می‌شوند.
    *   **جلوگیری از Stale Cart:** **BROKEN**. قبل از ساخت سفارش، یک اعتبارسنجی نهایی برای چک کردن تغییر قیمت یا ناموجود شدن اقلام سبد خرید انجام **نمی‌شود**. اگر مشتری سبد خرید را باز نگه دارد و در این حین قیمت کالا تغییر کند، سفارش با قیمت قدیمی ثبت خواهد شد.
    *   **Validation نهایی قبل از ساخت order:** **BROKEN**. همانطور که در مورد قبل ذکر شد، اعتبارسنجی مجدد موجودی و قیمت قبل از تبدیل سبد به سفارش وجود ندارد.

*   **Order State Machine:**
    *   **State های رسمی:** **OK**. وضعیت‌های سفارش در `orders/models.py` -> `Order.OrderStatus` به خوبی تعریف شده‌اند (`PENDING`, `PROCESSING`, `SHIPPED`, `COMPLETED`, `CANCELED`, `FAILED`).
    *   **Audit Trail تغییر وضعیت:** **NOT FOUND IN CODE**. هیچ جدولی برای ثبت تاریخچه تغییرات وضعیت سفارش و اینکه کدام کاربر یا سیستم (actor) آن را تغییر داده، وجود ندارد.
    *   **Idempotency روی عملیات‌های حساس:** **PARTIAL**. در `PaymentWebhookView`، وضعیت سفارش چک می‌شود (`if order.status == Order.OrderStatus.PENDING:`) تا از پردازش مجدد یک پرداخت جلوگیری شود. اما این منطق برای سایر عملیات‌ها مانند `cancel` یا `ship` پیاده‌سازی نشده است.

*   **Payment Integration:**
    *   **Webhook/Callback Handler و اعتبارسنجی:** **BROKEN**. در `payment/views.py` -> `PaymentWebhookView`، یک `secret` از هدر خوانده می‌شود اما صرفاً با متغیر محیطی مقایسه می‌شود. این مکانیزم در برابر حملات timing attack آسیب‌پذیر است و روش استاندارد (محاسبه هش و مقایسه) نیست. مهم‌تر از آن، بسیاری از درگاه‌ها امضای دیجیتال (signature) ارسال می‌کنند که اینجا اصلاً چک نمی‌شود.
    *   **جلوگیری از پرداخت تکراری:** **PARTIAL**. همانطور که گفته شد، وضعیت سفارش چک می‌شود، اما اگر دو درخواست وب‌هوک به صورت همزمان برسند، ممکن است race condition رخ دهد (هرچند احتمال آن کم است). استفاده از `select_for_update` روی سفارش در اینجا نیز می‌توانست امنیت را افزایش دهد.
    *   **Mapping دقیق Payment Status → Order Status:** **OK**. در `PaymentWebhookView`، پس از تایید پرداخت، وضعیت سفارش به `PROCESSING` تغییر می‌کند که منطقی است.
    *   **Handling تایم‌اوت/Partial Failure:** **NOT FOUND IN CODE**. هیچ منطقی برای مدیریت سناریوهایی که پاسخ از درگاه پرداخت با تاخیر می‌رسد یا هرگز نمی‌رسد (timeout) وجود ندارد. سفارش در وضعیت `PENDING` باقی می‌ماند.
    *   **Refund کامل/جزئی:** **NOT FOUND IN CODE**. هیچ 기능ی برای بازگشت وجه در کد مشاهده نشد.

---

### D) Security Audit (P0 محور)

*   **AuthN/AuthZ:**
    *   **روش احراز هویت:** **JWT**. از `rest_framework_simplejwt` برای صدور توکن‌های access و refresh استفاده می‌شود.
    *   **کنترل دسترسی روی منابع:** **BROKEN**. در `orders/views.py` -> `OrderViewSet`، کوئری выборки سفارش‌ها (`queryset = Order.objects.all()`) بر اساس کاربر فعلی فیلتر نشده است. این یک آسیب‌پذیری **IDOR (Insecure Direct Object Reference)** است.
    *   **IDOR Check:** **BROKEN**. کاربر احراز هویت شده می‌تواند با ارسال UUID یک سفارش در URL، به اطلاعات کامل سفارش سایر کاربران دسترسی پیدا کند.

*   **Input Validation:**
    *   **Schema Validation:** **OK**. Django REST Framework Serializers به طور موثر برای اعتبارسنجی داده‌های ورودی در تمام ViewSet ها استفاده می‌شوند.
    *   **File Upload Validation:** **NOT FOUND IN CODE**. هیچ قسمتی برای آپلود فایل توسط کاربر (مانند تصویر پروفایل یا پیوست تیکت) یافت نشد.
    *   **منع Mass Assignment:** **OK**. استفاده از Serializers با فیلدهای مشخص، ریسک Mass Assignment را به شدت کاهش می‌دهد.

*   **Injection & SSRF:**
    *   **SQL Injection:** **OK**. استفاده کامل از Django ORM ریسک SQL Injection را تقریباً به صفر می‌رساند. هیچ کوئری خامی (raw query) مشاهده نشد.
    *   **SSRF (Server-Side Request Forgery):** **P2 - LOW RISK**. در `payment/services.py` و `shipping/services.py`، درخواست‌های HTTP به URL های خارجی (درگاه پرداخت و پست) ارسال می‌شود. URL ها از تنظیمات خوانده می‌شوند و توسط کاربر قابل کنترل نیستند، بنابراین ریسک SSRF پایین است.

*   **Secrets & Crypto:**
    *   **نگهداری Secrets:** **OK**. استفاده از `python-decouple` برای خواندن متغیرها از `.env` یک رویه استاندارد و امن است. (`ecommerce_api/settings/base.py`)
    *   **رمزنگاری درست:** **OK**. Django به طور پیش‌فرض از الگوریتم‌های هشینگ قوی (مانند PBKDF2) برای نگهداری پسوردها استفاده می‌کند.
    *   **Token Rotation/Expiry:** **OK**. `simple-jwt` به طور پیش‌فرض از توکن‌های با تاریخ انقضا (expiry) استفاده می‌کند و مکانیزم refresh token را نیز پیاده‌سازی کرده است.

*   **Rate limiting / Abuse:**
    *   **جلوگیری Brute-force:** **PARTIAL**. مکانیزم rate limiting پیش‌فرض DRF (`ecommerce_api/settings/base.py` -> `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`) برای تمام اندپوینت‌ها فعال است، اما هیچ مکانیزم خاصی برای قفل کردن حساب کاربری پس از چند تلاش ناموفق وجود ندارد.
    *   **Rate limit روی Checkout/Payment:** **OK**. اندپوینت‌های حساس نیز تحت پوشش rate limit عمومی قرار دارند.
    *   **Captcha/Lockout Policy:** **NOT FOUND IN CODE**.

---

### E) Data Layer & Consistency

*   **Schema Constraints:** **OK**. مدل‌ها به خوبی از `ForeignKey`, `OneToOneField` و `unique_together` (در `inventory/models.py`) استفاده کرده‌اند که یکپارچگی داده در سطح دیتابیس را تضمین می‌کند.
*   **Index ها:** **PARTIAL**. Django به طور خودکار برای `ForeignKey` ها ایندکس می‌سازد. اما برای فیلدهایی که زیاد مورد جستجو قرار می‌گیرند (مثلاً `Order.status`) ایندکس سفارشی (`db_index=True`) تعریف نشده است.
*   **Transaction Boundaries:** **PARTIAL**. ترکنش اصلی ساخت سفارش اتمیک است (`transaction.atomic`)، اما سایر عملیات‌های حساس مانند `cancel_order` یا تغییر وضعیت‌های دیگر در ترکنش قرار ندارند.
*   **N+1 و Pagination:** **PARTIAL**. در بسیاری از لیست‌ها مانند `orders/views.py` -> `OrderViewSet`، از `select_related` یا `prefetch_related` برای بهینه‌سازی کوئری‌ها استفاده نشده است که منجر به مشکل N+1 می‌شود. Pagination به درستی پیاده‌سازی شده است.
*   **Soft Delete vs Hard Delete:** **OK**. تمام حذف‌ها به صورت Hard Delete است. در این مدل کسب‌وکار، این رویکرد قابل قبول است، هرچند Soft Delete می‌توانست برای گزارش‌گیری و تحلیل داده‌های تاریخی بهتر باشد.

---

### F) Reliability / Observability

*   **Error Handling:** **PARTIAL**. از exception handling پیش‌فرض DRF استفاده می‌شود که مناسب است، اما هیچ کلاس exception سفارشی برای خطاهای کسب‌وکار (مانند `InventoryNotAvailableError`) تعریف نشده و اکثراً با `ValidationError` مدیریت می‌شوند که تفکیک خطاها را دشوار می‌کند.
*   **Logging:** **BROKEN**. پیکربندی لاگینگ در `ecommerce_api/settings/base.py` بسیار ابتدایی است. لاگ‌ها ساختاریافته (structured) نیستند و هیچ correlation ID برای ردیابی یک درخواست در سرویس‌های مختلف وجود ندارد.
*   **Tracing/Metrics:** **OK**. پروژه از `django-prometheus` استفاده می‌کند که معیارهای پایه‌ای را در اندپوینت `/metrics` افشا می‌کند. این یک نقطه قوت است.
*   **Retries/Timeouts/Circuit Breaker:** **NOT FOUND IN CODE**. در ارتباط با سرویس‌های خارجی (`payment`, `shipping`)، هیچ مکانیزم retry یا timeout مشخصی تنظیم نشده است. این می‌تواند در صورت کندی سرویس‌های ثالث، کل سیستم را تحت تاثیر قرار دهد.

---

### G) Performance & Scalability

*   **Caching Strategy:** **PARTIAL**. Redis به عنوان کش‌بک‌اند تعریف شده، اما در کد استفاده بسیار محدودی از آن شده است. بسیاری از کوئری‌های تکراری مانند دریافت لیست محصولات یا دسته‌بندی‌ها کش نشده‌اند.
*   **Queue/Background Jobs:** **OK**. Celery برای کارهای پس‌زمینه (مانند ارسال ایمیل در `account/services.py`) استفاده شده که معماری درستی است.
*   **Hot Paths & Bottlenecks:**
    1.  **Order Creation:** `orders/services.py` -> `OrderService.create_order` به دلیل عدم وجود قفل و اعتبارسنجی مجدد، نه تنها ریسک دارد بلکه در ترافیک بالا می‌تواند به گلوگاه تبدیل شود.
    2.  **Product Listing:** `shop/views.py` -> `ProductViewSet` به دلیل عدم استفاده از `prefetch_related` برای `variants` و `images`، مستعد مشکل N+1 و کندی است.
    3.  **Cart Operations:** هر عملیات روی سبد خرید (`cart/views.py`) منجر به خواندن و نوشتن session می‌شود که می‌تواند در بار بالا به Redis فشار بیاورد.

---

### H) Testability & Coverage

*   **تست‌های واحد/یکپارچه:** **BROKEN**. پوشش تست بسیار ضعیف است. فایل `test_coverage_report.md` خود گواهی بر این مدعاست. تست‌های حیاتی برای منطق کسب‌وکار وجود ندارند.
*   **تست برای Race-condition و Idempotency:** **NOT FOUND IN CODE**. هیچ تستی برای سناریوهای همزمانی (concurrency) یا اطمینان از idempotent بودن عملیات‌ها نوشته نشده است.
*   **تست‌های امنیتی:** **NOT FOUND IN CODE**. هیچ تستی برای کنترل دسترسی و جلوگیری از IDOR وجود ندارد.

---

### Actionable Findings (یافته‌های قابل اقدام)

**[Severity: P0] Race Condition in Inventory Management Leads to Overselling**
*   **Evidence:** `orders/services.py` → `OrderService.create_order`
    *   The code checks `item.inventory.stock` and then decrements it without a database lock.
*   **Impact:** Financial (selling products that don't exist, leading to refunds and operational costs), Data Integrity, UX.
*   **Exploit/Repro:** Two users simultaneously request to purchase the last available unit of a product. Both checks might pass, resulting in a negative stock count.
*   **Fix:** Use a pessimistic lock on the inventory row within the transaction.
    ```python
    # Inside create_order, before the loop
    variant_ids = [item.variant.id for item in cart.items.all()]
    inventories = Inventory.objects.select_for_update().filter(product_variant_id__in=variant_ids)
    # ... then use this locked queryset inside the loop
    ```
*   **Regression tests:** A concurrent test using multiple threads to attempt to buy the same last item.

**[Severity: P0] Critical IDOR Allows Access to Other Users' Orders**
*   **Evidence:** `orders/views.py` → `OrderViewSet`
    *   The base queryset is `Order.objects.all()`, not filtered by the requesting user.
*   **Impact:** Security (breach of data confidentiality), Privacy.
*   **Exploit/Repro:** An authenticated user can navigate to `/api/v1/orders/<order_uuid>/` where `order_uuid` belongs to another user and view their full order details.
*   **Fix:** Override `get_queryset` to filter by user.
    ```python
    # In OrderViewSet
    from rest_framework.permissions import IsAuthenticated

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)
    ```
*   **Regression tests:** A test where User A tries to access an order belonging to User B and expects a 404 Not Found error.

**[Severity: P1] Payment Webhook Lacks Proper Signature Validation**
*   **Evidence:** `payment/views.py` → `PaymentWebhookView`
    *   It only checks a static `secret` from the header, which is insufficient and not standard practice. It doesn't validate the request body's signature.
*   **Impact:** Financial/Security. An attacker can forge a request to mark an order as "paid" without actually paying.
*   **Exploit/Repro:** Attacker creates an order, gets an `order_uuid`, and sends a fake POST request to the webhook URL with the correct `order_uuid` and a crafted body.
*   **Fix:** Implement proper signature validation based on the payment gateway's documentation (usually involves hashing the request body with a secret key).
    ```python
    # Pseudocode in PaymentWebhookView
    gateway_signature = request.headers.get('X-Gateway-Signature')
    computed_signature = hmac.new(settings.GATEWAY_SECRET.encode(), request.body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(gateway_signature, computed_signature):
        return Response(status=400, data={'detail': 'Invalid signature'})
    ```
*   **Regression tests:** A test that sends a webhook request with an invalid signature and expects a 400 error.

**[Severity: P1] Stale Data in Cart Can Lead to Incorrect Pricing at Checkout**
*   **Evidence:** `orders/services.py` → `OrderService.create_order`
    *   The service directly uses prices from cart items without re-validating them against the `ProductVariant` in the database before creating `OrderItem`.
*   **Impact:** Financial (selling at an outdated, lower price), UX (potential for confusion if price increases).
*   **Exploit/Repro:** User adds a product to their cart. Admin increases the price. User proceeds to checkout and buys the product at the old, lower price.
*   **Fix:** Before creating `OrderItem`s, iterate through cart items and verify that the price and stock status match the current state in the database.
    ```python
    # Inside create_order loop
    variant = ProductVariant.objects.get(id=cart_item.variant.id)
    if variant.price != cart_item.price or variant.inventory.stock < cart_item.quantity:
        raise ValidationError(f"Product {variant.name} details have changed. Please review your cart.")
    # Proceed with order creation using variant.price
    ```
*   **Regression tests:** A test that changes a product's price after it's added to the cart and asserts that checkout fails or uses the new price.

**[Severity: P2] N+1 Query Problem in Critical API Endpoints**
*   **Evidence:** `orders/views.py` → `OrderViewSet`, `shop/views.py` → `ProductViewSet`
    *   List endpoints do not use `select_related` or `prefetch_related` for related models (e.g., `Order` -> `user`, `Product` -> `variants`).
*   **Impact:** Performance. The number of database queries scales linearly with the number of items, leading to slow response times under load.
*   **Exploit/Repro:** Request the `/api/v1/orders/` endpoint. Using Django Debug Toolbar, observe that `N` additional queries are made, where `N` is the number of orders.
*   **Fix:** Use `prefetch_related` and `select_related` in the `get_queryset` method.
    ```python
    # In OrderViewSet
    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('items', 'items__variant')
    ```
*   **Regression tests:** A test that uses `assertNumQueries` to verify that the number of queries for the list endpoint is constant and low.

**[Severity: P2] Lack of Custom Business Logic Exceptions**
*   **Evidence:** `coupon/views.py` → `apply`, `orders/services.py` → `create_order`
    *   Business logic errors (e.g., "coupon expired", "item out of stock") are raised as generic `ValidationError`s.
*   **Impact:** Maintainability, Observability. It's hard to distinguish between user input errors and internal business rule failures, making monitoring and debugging difficult.
*   **Fix:** Define custom exception classes.
    ```python
    # in a new core/exceptions.py
    class CouponInvalidError(APIException):
        status_code = 400
        default_detail = 'The provided coupon is invalid or expired.'

    # in coupon/views.py
    raise CouponInvalidError()
    ```
*   **Regression tests:** Tests that trigger specific business errors and assert that the correct custom exception (and status code) is returned.

**[Severity: P2] Unindexed Fields for Filtering**
*   **Evidence:** `orders/models.py` → `Order.status`
    *   The `status` field is likely to be used in database queries for filtering orders, but it lacks a `db_index=True`.
*   **Impact:** Performance. Queries filtering by status on a large `Order` table will be slow.
*   **Exploit/Repro:** Populate the database with millions of orders. Run a query like `Order.objects.filter(status='PROCESSING')`. The query will perform a full table scan.
*   **Fix:** Add `db_index=True` to the field.
    ```python
    # In Order model
    status = models.CharField(..., db_index=True)
    ```
*   **Regression tests:** Not straightforward to test performance, but code review should enforce this.

**[Severity: P2] Inadequate and Unstructured Logging**
*   **Evidence:** `ecommerce_api/settings/base.py` → `LOGGING`
    *   The logging configuration is minimal. It doesn't use a structured formatter (like JSON) and lacks request/correlation IDs.
*   **Impact:** Observability. Debugging production issues is extremely difficult without the ability to trace a user's request journey or filter logs effectively.
*   **Exploit/Repro:** An error occurs in production. The logs show a traceback but provide no context about the user, the request ID, or other concurrent activities.
*   **Fix:** Implement a structured logging library (e.g., `structlog`) and add a middleware to inject a request ID into every log message.
*   **Regression tests:** A test that makes a request and captures log output to verify it's in the correct JSON format and contains a `request_id`.

**[Severity: P3] No Audit Trail for Order State Changes**
*   **Evidence:** `orders/models.py`
    *   There is no model to log the history of `Order.status` changes.
*   **Impact:** Data Integrity, Customer Support. It's impossible to know when, why, or by whom an order was cancelled, shipped, or marked as completed. This complicates dispute resolution.
*   **Fix:** Create a new model, `OrderStatusHistory`, and use a post-save signal on the `Order` model to record every status change.
    ```python
    class OrderStatusHistory(models.Model):
        order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='history')
        from_status = models.CharField(...)
        to_status = models.CharField(...)
        timestamp = models.DateTimeField(auto_now_add=True)
        actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True) # or a generic actor
    ```
*   **Regression tests:** A test that changes an order's status and asserts that a corresponding `OrderStatusHistory` record was created.

**[Severity: P3] Lack of Caching for Frequently Accessed Data**
*   **Evidence:** `shop/views.py` → `ProductViewSet`
    *   The list of products, which changes infrequently, is fetched from the database on every request.
*   **Impact:** Performance, Scalability. The database is put under unnecessary load for data that could be served from a fast in-memory cache.
*   **Exploit/Repro:** Use a load testing tool to send many requests to `/api/v1/shop/products/`. Observe high database CPU usage.
*   **Fix:** Use Django's caching framework to cache the queryset.
    ```python
    # in views.py
    from django.core.cache import cache

    def list(self, request, *args, **kwargs):
        products_cache_key = 'all_products'
        products = cache.get(products_cache_key)
        if not products:
            products = self.get_queryset()
            cache.set(products_cache_key, products, timeout=3600) # Cache for 1 hour
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)
    ```
*   **Regression tests:** Tests that check if data is served from the cache on the second request and that cache invalidation works correctly when a product is updated.
