# گزارش حسابرسی فنی سیستم فروشگاهی

## A) خلاصه مدیریتی

**وضعیت کلی سیستم:** **قابل اتکا (Reliable)**

سیستم حاضر یک پلتفرم فروشگاهی خوش‌ساخت و مدرن است که بر پایه Django و ابزارهای استاندارد صنعتی توسعه یافته است. معماری ماژولار، استفاده صحیح از transactionها برای جلوگیری از oversell، و پیاده‌سازی امن مکانیزم پرداخت، نقاط قوت کلیدی آن هستند. با این حال، فقدان یک مکانیزم صریح برای ردگیری تغییرات وضعیت سفارش و تست‌های ناکافی برای وب‌هوک پرداخت، ریسک‌های اصلی محسوب می‌شوند که نیازمند توجه فوری هستند.

**۳ ریسک حیاتی اول:**

1.  **ریسک داده:** فقدان ردپای حسابرسی (Audit Trail) برای تغییرات وضعیت سفارش، پیگیری خطاها و اختلافات مالی در آینده را دشوار می‌کند (`orders/models.py`).
2.  **ریسک مالی:** عدم وجود تست‌های خودکار برای وب‌هوک پرداخت (`payment/views.py`) می‌تواند منجر به عدم پردازش صحیح پرداخت‌ها در صورت بروز تغییرات ناخواسته در کد شود.
3.  **ریسک داده:** عدم وجود محدودیت در اندازه فایل آپلود شده برای تصویر محصول، پتانسیل حملات Denial-of-Service را با پر کردن فضای دیسک سرور فراهم می‌کند.

**۳ پیشنهاد فوری:**

1.  **فعال‌سازی Audit Trail:** با استفاده از کتابخانه `django-simple-history` که از قبل نصب شده، تاریخچه تغییرات مدل `Order` را برای مانیتورینگ دقیق وضعیت سفارش‌ها فعال کنید.
2.  **توسعه تست وب‌هوک:** تست‌های یکپارچه (integration tests) برای `PaymentWebhookAPIView` بنویسید تا سناریوهای مختلف پرداخت (موفق، ناموفق، داده ناقص) پوشش داده شوند.
3.  **محدودیت حجم آپلود:** یک اعتبارسنج (validator) برای فیلد `thumbnail` در مدل `Product` اضافه کنید تا حجم فایل‌های آپلودی به یک مقدار معقول (مثلاً 2MB) محدود شود.

---

## B) نقشه سیستم

**Tech Stack & Entry Points:**

*   **فریم‌ورک:** Django
*   **ORM/DB Driver:** Django ORM / `psycopg` for PostgreSQL
*   **Queue:** Celery with Redis broker
*   **Cache:** Redis (`django-redis`)
*   **Payment SDKs:** یکپارچه‌سازی مستقیم با درگاه پرداخت زیبال (بدون SDK مجزا)
*   **نقطه ورود درخواست‌ها:** `ecommerce_api/urls.py` درخواست‌ها را به ماژول‌های اپلیکیشن (`shop`, `orders`, `payment` و غیره) توزیع می‌کند. ViewSetهای DRF (مانند `ProductViewSet`, `OrderViewSet`) به عنوان controller عمل می‌کنند.
*   **Middleware/Guards:**
    *   `django_prometheus.middleware`: جمع‌آوری متریک‌ها
    *   `corsheaders.middleware.CorsMiddleware`: مدیریت CORS
    *   `rest_framework_simplejwt.authentication.JWTAuthentication`: احراز هویت مبتنی بر JWT
    *   `orders.permissions.IsAdminOrOwner`: کنترل دسترسی در سطح object

**Domain Modules:**

*   **محصولات/دسته‌بندی:**
    *   `shop/models.py` → `Product`, `Category`
    *   `shop/views.py` → `ProductViewSet`, `CategoryViewSet`
*   **موجودی/انبار:**
    *   `shop/models.py` → `Product.stock`
    *   `orders/serializers.py` → `OrderCreateSerializer.save()` (منطق قفل و کاهش موجودی)
*   **سبد خرید:**
    *   `cart/cart.py` → `Cart` (منطق اصلی سبد خرید)
    *   `cart/views.py` → `CartViewSet`
*   **سفارش‌ها:**
    *   `orders/models.py` → `Order`, `OrderItem`
    *   `orders/views.py` → `OrderViewSet`
    *   `orders/serializers.py` → `OrderCreateSerializer`
*   **پرداخت:**
    *   `payment/views.py` → `PaymentProcessAPIView`, `PaymentWebhookAPIView`
    *   `payment/services.py` → `process_payment`, `verify_payment`
*   **کوپن تخفیت:**
    *   `coupons/models.py` → `Coupon`
    *   `orders/serializers.py` → `OrderCreateSerializer.validate()`

---

## C) Domain Correctness Audit

*   **Pricing:**
    *   **منبع قیمت و جلوگیری از دستکاری:** `OK`. قیمت از `shop.Product.price` خوانده می‌شود. `OrderCreateSerializer` در سمت سرور، قیمت محصول را در لحظه خرید مجدداً اعتبارسنجی می‌کند و از قیمت کلاینت استفاده نمی‌کند.
*   **Inventory & Oversell Prevention:**
    *   **قفل/رزرو موجودی:** `OK`. `OrderCreateSerializer` از `select_for_update()` برای قفل کردن ردیف‌های محصول در دیتابیس در طول تراکنش ساخت سفارش استفاده می‌کند که به طور موثر از oversell جلوگیری می‌کند.
    *   **Rollback در خطای پرداخت:** `OK`. کاهش موجودی بخشی از تراکنش ساخت سفارش است. اگر پرداخت با خطا مواجه شود، سفارش به وضعیت `pending` می‌رود اما موجودی کسر شده و تنها در صورت لغو دستی سفارش بازگردانده می‌شود.
*   **Cart → Order Integrity:**
    *   **تبدیل سبد به سفارش (Snapshot):** `OK`. `OrderItem` قیمت محصول (`price`) را در لحظه ایجاد سفارش ذخیره می‌کند و از تغییرات آتی قیمت محصول مصون است.
    *   **جلوگیری از Stale Cart:** `OK`. `OrderCreateSerializer` قبل از نهایی کردن سفارش، قیمت و موجودی فعلی محصول را با مقادیر موجود در سبد خرید مقایسه کرده و در صورت مغایرت، خطا برمی‌گرداند.
*   **Order State Machine:**
    *   **State های رسمی و انتقال‌های مجاز:** `PARTIAL`. وضعیت‌های سفارش در `orders.models.Order.Status` تعریف شده‌اند، اما هیچ منطق state machine برای کنترل انتقال بین وضعیت‌ها وجود ندارد (مثلاً جلوگیری از ارسال یک سفارش لغوشده).
    *   **Audit Trail تغییر وضعیت:** `BROKEN`. با وجود نصب بودن `django-simple-history`، این ابزار روی مدل `Order` فعال نشده است و هیچ ردپایی از تغییرات وضعیت سفارش و عامل تغییر وجود ندارد.
*   **Payment Integration:**
    *   **Webhook Handler و اعتبارسنجی:** `OK`. `payment/views.py` → `PaymentWebhookAPIView` به درستی از `hmac.compare_digest` برای اعتبارسنجی secret وب‌هوک و همچنین از یک لیست IP مجاز استفاده می‌کند.
    *   **جلوگیری از پرداخت تکراری:** `PARTIAL`. سیستم از `trackId` برای پیگیری پرداخت استفاده می‌کند، اما منطق صریحی برای جلوگیری از پردازش مجدد یک `trackId` موفق وجود ندارد. این کار به صورت ضمنی با چک کردن وضعیت سفارش انجام می‌شود اما می‌توانست صریح‌تر باشد.

---

## D) Security Audit

*   **AuthN/AuthZ:**
    *   **روش احراز هویت:** `OK`. سیستم از JWT با `rest_framework_simplejwt` استفاده می‌کند.
    *   **کنترل دسترسی:** `OK`. اندپوینت‌های سفارش (`OrderViewSet`) با استفاده از `IsAdminOrOwner` و فیلتر کردن کوئری‌ست (`get_user_orders`) به خوبی محافظت می‌شوند.
    *   **IDOR Check:** `OK`. تست‌های واحد در `orders/tests.py` (تست `test_idor_vulnerability`) به طور مشخص این مورد را پوشش داده و تایید می‌کنند که کاربر نمی‌تواند سفارش دیگران را مشاهده کند.
*   **Input Validation:**
    *   **Schema Validation:** `OK`. تمام ورودی‌های API از طریق DRF Serializerها (مانند `OrderCreateSerializer`) اعتبارسنجی می‌شوند که از mass assignment جلوگیری می‌کند.
    *   **File Upload Validation:** `PARTIAL`. آپلود تصویر محصول در `shop.models.Product.thumbnail` هیچ محدودیتی بر روی حجم یا نوع فایل اعمال نمی‌کند.
*   **Injection & SSRF:**
    *   **SQL/NoSQL injection:** `OK`. استفاده انحصاری از Django ORM و عدم وجود کوئری‌های خام (raw queries)، ریسک SQL Injection را به طور کامل از بین برده است.
    *   **SSRF:** `OK`. تمام ارتباطات با سرویس‌های خارجی (مانند `shipping/providers.py`) از URLهای پایه هاردکد شده استفاده می‌کنند و هیچ بخشی از URL توسط کاربر قابل کنترل نیست، که این امر مانع از حملات SSRF می‌شود.
    *   **Command injection:** `OK`. هیچ‌کدام از بخش‌های کد اپلیکیشن از دستورات shell استفاده نمی‌کنند.
*   **Secrets & Crypto:**
    *   **نگهداری Secrets:** `OK`. تمام اطلاعات حساس از طریق فایل `.env` مدیریت می‌شوند.
    *   **رمزنگاری درست:** `OK`. Django به طور پیش‌فرض از الگوریتم‌های هشینگ قوی (PBKDF2) برای رمزهای عبور استفاده می‌کند.
*   **Rate limiting / Abuse:**
    *   **جلوگیری brute-force login/OTP:** `OK`. سیستم دارای یک rate limit سراسری (`DEFAULT_THROTTLE_RATES`) است که در `ecommerce_api/settings/base.py` تعریف شده و تمام اندپوینت‌ها، از جمله لاگین و پرداخت، را در برابر حملات brute-force محافظت می‌کند.
    *   **Rate limit روی checkout/payment endpoints:** `OK`. این اندپوینت‌ها توسط همان rate limit سراسری پوشش داده می‌شوند.

---

## E) Data Layer & Consistency

*   **Schema Constraints:** `OK`. مدل‌ها از `ForeignKey` و `unique` به درستی استفاده کرده‌اند.
*   **Index‌ها:** `OK`. ایندکس‌های مناسبی بر روی فیلدهای کلیدی مدل‌های `Product` و `Order` (مانند `slug`, `user`, `order_date`) تعریف شده است.
*   **Transaction Boundaries:** `OK`. فرآیند حیاتی ساخت سفارش در `OrderCreateSerializer` داخل یک `transaction.atomic` قرار دارد که اتمی بودن عملیات را تضمین می‌کند.
*   **N+1 و Pagination:** `OK`. در `orders/services.py` → `get_user_orders` از `prefetch_related` برای جلوگیری از مشکل N+1 در هنگام لیست کردن سفارش‌ها استفاده شده است.

---

## F) Reliability / Observability

*   **Error Handling:** `OK`. یک `custom_exception_handler` در تنظیمات DRF تعریف شده که خطاهای استاندارد را مدیریت می‌کند.
*   **Logging:** `PARTIAL`. لاگینگ به صورت پراکنده وجود دارد (مثلاً در وب‌هوک پرداخت) اما یک استراتژی لاگینگ ساختاریافته و جامع در کل پروژه دیده نمی‌شود.
*   **Tracing/Metrics:** `OK`. پروژه با `django-prometheus` برای متریک‌ها و OpenTelemetry برای تریسنیگ به خوبی یکپارچه شده است.
*   **Retries/Timeouts:** `NOT FOUND IN CODE`. هیچ مکانیزم retry یا circuit breaker برای ارتباط با سرویس‌های خارجی (مانند درگاه پرداخت) مشاهده نشد.

---

## G) Performance & Scalability

*   **Caching Strategy:** `OK`. از Redis به عنوان بک‌اند کش استفاده می‌شود.
*   **Queue/Background Jobs:** `OK`. از Celery برای کارهای زمان‌بر مانند ارسال ایمیل تایید سفارش (`orders/tasks.py`) استفاده می‌شود که از بلاک شدن وب سرور جلوگیری می‌کند.
*   **Hot Paths:** `OK`. مسیر ساخت سفارش (`OrderCreateSerializer`) که یک hot path محسوب می‌شود، با استفاده از تراکنش و قفل دیتابیس بهینه شده است.

---

## H) Testability & Coverage

*   **تست‌های واحد/یکپارچه:** `PARTIAL`. تست‌های بسیار خوبی برای منطق سفارش، قیمت‌گذاری و جلوگیری از oversell در `orders/tests.py` وجود دارد. اما تست برای وب‌هوک پرداخت (`PaymentWebhookAPIView`) که یک جزء حیاتی است، وجود ندارد.
*   **تست برای Race-condition:** `OK`. تست `test_overselling_prevention` به طور موثر سناریوی race condition را شبیه‌سازی و صحت عملکرد سیستم را تایید می‌کند.
*   **تست‌های امنیتی ساده:** `OK`. تست `test_idor_vulnerability` یک نمونه خوب از تست امنیت برای کنترل دسترسی است.

---

## Actionable Findings

[Severity: P1] **فقدان Audit Trail برای تغییرات وضعیت سفارش**
*   **Evidence:** `orders/models.py` → `Order` model
*   **Impact:** (داده) در صورت بروز اختلاف مالی یا خطا در فرآیند، هیچ سابقه‌ای برای پیگیری اینکه چه کسی یا چه سیستمی وضعیت سفارش را تغییر داده وجود ندارد.
*   **Fix:** کتابخانه `django-simple-history` که از قبل نصب شده را روی مدل `Order` فعال کنید.
    ```python
    # orders/models.py
    from simple_history.models import HistoricalRecords

    class Order(models.Model):
        # ... existing fields
        history = HistoricalRecords()
    ```
*   **Regression tests:** یک تست بنویسید که وضعیت یک سفارش را تغییر دهد و سپس بررسی کند که یک رکورد در `order.history` ایجاد شده است.

[Severity: P1] **عدم وجود تست برای وب‌هوک پرداخت**
*   **Evidence:** `payment/views.py` → `PaymentWebhookAPIView`
*   **Impact:** (مالی) هرگونه تغییر در آینده در این بخش حیاتی، بدون وجود تست‌های خودکار، می‌تواند منجر به عدم ثبت صحیح پرداخت‌ها و ضرر مالی شود.
*   **Fix:** با استفاده از `APITestCase` و mock کردن درخواست از سمت درگاه پرداخت، سناریوهای مختلف (پرداخت موفق، ناموفق، داده‌های نامعتبر) را برای وب‌هوک تست کنید.
*   **Regression tests:** اضافه کردن تست‌های یکپارچه برای `PaymentWebhookAPIView`.

[Severity: P2] **عدم وجود منطق State Machine برای سفارش**
*   **Evidence:** `orders/models.py` → `Order` model
*   **Impact:** (داده) می‌توان یک سفارش کنسل شده را به وضعیت "ارسال شده" تغییر داد که منجر به ناهماهنگی داده‌ها و فرآیندهای کسب‌وکار می‌شود.
*   **Fix:** از یک کتابخانه مانند `django-fsm` استفاده کنید یا یک متد `transition_state(new_state)` روی مدل `Order` بنویسید که منطق انتقال مجاز را پیاده‌سازی کند.
*   **Regression tests:** تستی بنویسید که سعی کند یک انتقال وضعیت غیرمجاز (مثلاً از CANCELED به SHIPPED) را انجام دهد و از بروز خطا اطمینان حاصل کند.

[Severity: P2] **عدم محدودیت حجم فایل آپلودی**
*   **Evidence:** `shop/models.py` → `Product.thumbnail`
*   **Impact:** (امنیتی/منابع) یک کاربر مخرب می‌تواند با آپلود فایل‌های بسیار حجیم، فضای دیسک سرور را پر کرده و باعث از کار افتادن سرویس (Denial of Service) شود.
*   **Fix:** یک validator سفارشی برای محدود کردن حجم فایل به فیلد `thumbnail` اضافه کنید.
    ```python
    # shop/models.py
    from django.core.exceptions import ValidationError

    def validate_image_size(file):
        if file.size > 2 * 1024 * 1024: # 2MB
            raise ValidationError("File size cannot exceed 2MB.")

    class Product(models.Model):
        #...
        thumbnail = models.ImageField(
            #...
            validators=[validate_image_size]
        )
    ```
*   **Regression tests:** تستی بنویسید که تلاش کند فایلی با حجم بیشتر از حد مجاز آپلود کند و انتظار دریافت خطای validation را داشته باشد.

[Severity: P2] **پردازش چندباره یک پرداخت موفق (Idempotency)**
*   **Evidence:** `payment/views.py` → `PaymentWebhookAPIView`
*   **Impact:** (مالی/داده) اگر درگاه پرداخت به هر دلیلی یک وب‌هوک موفق را چندین بار ارسال کند، ممکن است منطق پردازش پرداخت (مانند ارسال ایمیل یا اطلاع به انبار) چندین بار اجرا شود.
*   **Fix:** قبل از ارسال تسک به Celery، ابتدا چک کنید که آیا سفارشی با `track_id` مشابه قبلاً به وضعیت موفق تغییر کرده است یا خیر.
    ```python
    # payment/views.py
    from orders.models import Order

    # Inside PaymentWebhookAPIView.post
    order = Order.objects.filter(payment_track_id=track_id).first()
    if order and order.payment_status == Order.PaymentStatus.SUCCESS:
        return Response({"message": "Webhook already processed."}, status=status.HTTP_200_OK)

    process_successful_payment.delay(track_id, success)
    ```
*   **Regression tests:** یک تست بنویسید که وب‌هوک موفق را دو بار برای یک `track_id` ارسال کند و بررسی کند که تسک Celery تنها یک بار اجرا می‌شود.

[Severity: P3] **نبود مکانیزم Retry برای سرویس‌های خارجی**
*   **Evidence:** `payment/services.py`, `shipping/services.py`
*   **Impact:** (قابلیت اطمینان) در صورت بروز خطای لحظه‌ای در ارتباط با درگاه پرداخت یا سرویس پست، عملیات فوراً با شکست مواجه می‌شود و تجربه کاربری را مختل می‌کند.
*   **Fix:** برای تسک‌های Celery که با سرویس‌های خارجی در ارتباط هستند، از مکانیزم `autoretry_for` استفاده کنید.
    ```python
    # payment/tasks.py
    import requests

    @shared_task(autoretry_for=(requests.exceptions.RequestException,), retry_kwargs={'max_retries': 3})
    def process_payment_task(...):
        # ...
    ```
*   **Regression tests:** با mock کردن خطای شبکه‌ای، بررسی کنید که تسک Celery به درستی مجدداً تلاش می‌کند.

[Severity: P3] **استراتژی لاگینگ غیرجامع**
*   **Evidence:** در کل پروژه
*   **Impact:** (اشکال‌زدایی) عدم وجود لاگ‌های ساختاریافته با یک `correlation_id` مشخص، اشکال‌زدایی درخواست‌های پیچیده که چندین سرویس را درگیر می‌کنند، بسیار دشوار می‌سازد.
*   **Fix:** از `python-json-logger` استفاده کنید و یک middleware برای افزودن `request_id` به تمام لاگ‌های یک درخواست پیاده‌سازی کنید.
*   **Regression tests:** نیازمند بررسی دستی لاگ‌ها است.

[Severity: P3] **عدم اعتبارسنجی نوع فایل (MIME Type)**
*   **Evidence:** `shop/models.py` → `Product.thumbnail`
*   **Impact:** (امنیتی) یک کاربر می‌تواند فایلی با پسوند `.jpg` اما محتوای مخرب (مانند HTML/JS) آپلود کند که می‌تواند منجر به حملات XSS در پنل ادمین شود.
*   **Fix:** از کتابخانه‌ای مانند `python-magic` برای اعتبارسنجی MIME type واقعی فایل در کنار validator حجم استفاده کنید.
*   **Regression tests:** تستی بنویسید که یک فایل غیر تصویری با پسوند تصویر را آپلود کرده و انتظار خطا داشته باشد.

[Severity: P3] **عدم بازگشت موجودی در صورت لغو سفارش**
*   **Evidence:** `orders/views.py` → `OrderViewSet`
*   **Impact:** (موجودی) اگر یک سفارش در وضعیت `pending` توسط ادمین لغو شود، موجودی کسر شده به انبار باز نمی‌گردد و محصول قابل فروش نخواهد بود.
*   **Fix:** یک سیگنال `post_save` یا بازنویسی متد `save` برای مدل `Order` پیاده‌سازی کنید که اگر وضعیت به `CANCELED` تغییر کرد، موجودی محصولات مرتبط را افزایش دهد.
*   **Regression tests:** یک تست بنویسید که سفارشی را ایجاد کند (موجودی کم شود)، سپس آن را کنسل کند و بررسی کند که موجودی محصول به حالت اولیه بازگشته است.

[Severity: P3] **عدم استفاده از Caching در نقاط پرتکرار**
*   **Evidence:** `shop/views.py` → `CategoryViewSet`
*   **Impact:** (کارایی) لیست دسته‌بندی‌ها که به ندرت تغییر می‌کند، در هر درخواست از دیتابیس خوانده می‌شود. این یک فرصت از دست رفته برای بهبود کارایی است.
*   **Fix:** از `django.core.cache` برای کش کردن کوئری‌ست دسته‌بندی‌ها استفاده کنید و با استفاده از سیگنال، در صورت تغییر در مدل `Category`، کش را باطل (invalidate) کنید.
*   **Regression tests:** تستی بنویسید که تعداد کوئری‌های دیتابیس را در دو بار فراخوانی لیست دسته‌بندی‌ها بشمارد و انتظار داشته باشد در فراخوانی دوم تعداد کوئری‌ها صفر باشد.
