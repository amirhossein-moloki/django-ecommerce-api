
# گزارش ممیزی فنی پروژه فروشگاهی

## A) خلاصه مدیریتی (Executive Summary)

**وضعیت کلی سیستم:** **قابل اتکا با ریسک بالا در نگهداری (Reliable but High-Risk to Maintain)**

سیستم حاضر از نظر معماری و پیاده‌سازی منطق‌های اصلی کسب‌وکار (مانند مدیریت موجودی، قیمت‌گذاری و پردازش پرداخت) در وضعیت بسیار خوبی قرار دارد و از الگوهای مدرن و امنی استفاده می‌کند. با این حال، فقدان کامل تست‌های خودکار برای ماژول‌های حیاتی **سفارش و پرداخت**، یک ریسک عملیاتی بسیار بزرگ (P0) محسوب می‌شود. هرگونه تغییر در این بخش‌ها بدون وجود تست، می‌تواند به راحتی منجر به باگ‌های مالی یا عملیاتی شود. معماری سیستم قوی است، اما تضمین پایداری آن در بلندمدت نیازمند اقدام فوری در زمینه تست است.

**۳ ریسک حیاتی اول:**

1.  **ریسک داده/عملیاتی (P0):** فقدان تست برای ماژول‌های `orders` و `payment`. تغییرات آتی در این بخش‌ها می‌تواند منطق کسب‌وکار را دچار مشکل کرده و منجر به خطاهای مالی یا از دست رفتن سفارش‌ها شود.
2.  **ریسک داده (P1):** استفاده از Hard Delete برای محصولات. حذف یک محصول از دیتابیس باعث حذف تاریخچه آن از سفارش‌های قبلی شده و تحلیل داده‌های فروش در بلندمدت را غیرممکن می‌سازد.
3.  **ریسک امنیتی (P2):** طولانی بودن عمر Access Token (۱۵ روز). در صورت نشت توکن، مهاجم می‌تواند برای مدت طولانی به حساب کاربر دسترسی داشته باشد.

**۳ پیشنهاد فوری:**

1.  **همین هفته:** ایجاد حداقل یک تست یکپارچه (Integration Test) برای فرآیند `create_order` که سناریوی موفق ایجاد سفارش از سبد خرید تا کسر موجودی را پوشش دهد.
2.  **همین هفته:** تغییر سیاست حذف محصول از `on_delete=models.CASCADE` به `on_delete=models.PROTECT` یا `SET_NULL` و افزودن یک فیلد `is_active` به مدل `Product` برای غیرفعال کردن محصولات به جای حذف کامل آنها.
3.  **همین هفته:** کاهش `ACCESS_TOKEN_LIFETIME` به یک مقدار کوتاه‌تر (مانند ۱ ساعت) و اطمینان از اینکه اپلیکیشن کلاینت به درستی از Refresh Token برای تمدید آن استفاده می‌کند.

---

## B) نقشه سیستم (System Map)

**Tech Stack & Entry Points**

*   **فریم‌ورک:** Django
*   **ORM/DB Driver:** Django ORM / `psycopg` for PostgreSQL
*   **Queue:** Celery
*   **Cache:** Redis (`django-redis`)
*   **Payment SDKs:** یک Gateway سفارشی برای زیبال (`payment/gateways.py`)
*   **نقاط ورود اصلی (URLs):**
    *   `ecommerce_api/urls.py`: نقطه ورود اصلی
    *   `/api/v1/`: مسیر اصلی API که شامل ماژول‌های زیر است:
        *   `shop.urls` (محصولات، دسته‌بندی‌ها، نظرات)
        *   `orders.urls` (مدیریت سفارش‌ها)
        *   `cart.urls` (مدیریت سبد خرید)
        *   `coupons.urls` (مدیریت کوپن‌ها)
    *   `/auth/`: مسیرهای احراز هویت (مبتنی بر OTP و JWT)
    *   `/payment/`: مسیرهای مربوط به پرداخت (ایجاد و تایید پرداخت، وب‌هوک)
*   **Middlewares اصلی:**
    *   `django_prometheus.middleware.*`: جمع‌آوری متریک‌ها
    *   `corsheaders.middleware.CorsMiddleware`: مدیریت CORS
    *   `cart.middleware.CartSessionMiddleware`: مدیریت سبد خرید در سشن

**Domain Modules**

*   **محصولات/SKU:**
    *   **مسیر:** `shop/models.py` -> `Product`, `Category`
    *   **توابع کلیدی:** `ProductViewSet` در `shop/views.py`، سرویس جستجو در `shop/utils.py`
*   **موجودی/انبار:**
    *   **مسیر:** فیلد `stock` در `shop/models.py` -> `Product`
    *   **توابع کلیدی:** منطق کاهش موجودی در `orders/serializers.py` -> `OrderCreateSerializer.save`
*   **سبد خرید:**
    *   **مسیر:** `cart/cart.py` -> `Cart`, `cart/models.py` -> `Cart`, `CartItem`
    *   **توابع کلیدی:** متدهای `add`, `remove`, `get_total_price`
*   **سفارش‌ها:**
    *   **مسیر:** `orders/models.py` -> `Order`, `OrderItem`
    *   **توابع کلیدی:** `create_order` در `orders/services.py` و `OrderCreateSerializer` در `orders/serializers.py`
*   **پرداخت:**
    *   **مسیر:** `payment/views.py`, `payment/services.py`
    *   **توابع کلیدی:** `PaymentWebhookAPIView` برای پردازش پاسخ درگاه، `verify_payment` برای تایید نهایی.
*   **ارسال:**
    *   **مسیر:** `shipping/` (ادغام با Postex)
    *   **توابع کلیدی:** `create_postex_shipment_task` در `shipping/tasks.py`
*   **تخفیف/کوپن:**
    *   **مسیر:** `coupons/models.py` -> `Coupon`
    *   **توابع کلیدی:** منطق اعتبارسنجی و اعمال کوپن در `orders/serializers.py` -> `OrderCreateSerializer.validate`

---

## C) ممیزی صحت دامنه (Domain Correctness Audit)

*   **Pricing:**
    *   **منبع قیمت و جلوگیری از دستکاری:** `OK`. قیمت از فیلد `price` در مدل `Product` خوانده می‌شود. منطق `Cart` و `OrderCreateSerializer` مستقیماً از این مقدار دیتابیسی استفاده کرده و هیچ ورودی از کلاینت نمی‌پذیرند.
    *   **محاسبه تخفیف‌ها:** `OK`. تخفیف بر اساس درصد کوپن و روی قیمت کل سبد خرید که از دیتابیس خوانده شده، محاسبه می‌شود.
*   **Inventory & Oversell Prevention:**
    *   **قفل/رزرو موجودی:** `OK`. فرآیند ایجاد سفارش از `select_for_update()` برای قفل کردن ردیف‌های محصولات در دیتابیس استفاده می‌کند که از race condition جلوگیری می‌کند.
    *   **Rollback در خطای پرداخت:** `OK`. کل فرآیند ایجاد سفارش در یک `transaction.atomic` قرار دارد. اگر پرداخت در درگاه ناموفق باشد، سفارش در وضعیت `PENDING` باقی می‌ماند.
    *   **سیاست Stock Reservation Expiry:** `OK`. یک تسک سلری (`cancel_pending_orders`) سفارش‌های `PENDING` را پس از ۲۰ دقیقه کنسل می‌کند. منطق `restore_stock` در متد `save` مدل `Order` تضمین می‌کند که موجودی محصولات به انبار بازگردانده می‌شود.
*   **Cart → Order Integrity:**
    *   **Snapshot گرفتن از قیمت/نام/sku:** `OK`. در زمان ایجاد `OrderItem`، مقادیر `product_name`, `product_sku` و `price` از محصول کپی و ذخیره می‌شوند.
    *   **جلوگیری از Stale Cart:** `OK`. سریالایزر `OrderCreateSerializer` در لحظه خرید، قیمت آیتم در سبد خرید را با قیمت لحظه‌ای محصول در دیتابیس مقایسه می‌کند (`if item['price'] != product.price:`).
*   **Order State Machine:**
    *   **State های رسمی و انتقال‌های مجاز:** `OK`. وضعیت‌ها در `Order.Status` تعریف شده و یک دیکشنری `_transitions` به همراه متد `clean` در مدل `Order` از انتقال‌های نامعتبر جلوگیری می‌کند.
    *   **Audit Trail:** `OK`. پروژه از `django-simple-history` برای ثبت تمام تغییرات روی مدل `Order` استفاده می‌کند.
*   **Payment Integration:**
    *   **وجود Webhook Handler و اعتبارسنجی امضا:** `OK`. ویوی `PaymentWebhookAPIView` پاسخ درگاه را دریافت کرده و با استفاده از `hmac.compare_digest` و `ZIBAL_WEBHOOK_SECRET` امضا را اعتبارسنجی می‌کند.
    *   **جلوگیری از پرداخت تکراری (Idempotency):** `OK`. وب‌هوک قبل از پردازش، `order.payment_status` را چک می‌کند و اگر `SUCCESS` باشد، از پردازش مجدد جلوگیری می‌کند.
    *   **Mapping Payment Status → Order Status:** `OK`. سرویس `verify_payment` پس از تایید پرداخت، `order.status` را به `PAID` و `order.payment_status` را به `SUCCESS` تغییر می‌دهد.

---

## D) ممیزی امنیتی (Security Audit)

*   **AuthN/AuthZ:**
    *   **روش احراز هویت:** `OK`. JWT با `simple-jwt` و `djoser`.
    *   **کنترل دسترسی و IDOR Check:** `OK`. `OrderViewSet` با فیلتر کردن کوئری بر اساس `request.user` (`Order.objects.filter(user=user)`) به طور مؤثری از دسترسی غیرمجاز به سفارش‌های دیگران جلوگیری می‌کند.
*   **Input Validation:**
    *   **Schema Validation:** `OK`. استفاده از DRF Serializers به طور پیش‌فرض از Mass Assignment جلوگیری می‌کند.
    *   **File Upload Validation:** `OK`. ولیدیتور سفارشی در `shop/validators.py` از کتابخانه `python-magic` برای تشخیص نوع فایل بر اساس محتوای آن استفاده می‌کند که بسیار امن است.
*   **Injection & SSRF:**
    *   **SQL Injection:** `OK`. هیچ استفاده‌ای از کوئری خام (`.raw()`) در کد مشاهده نشد. تمام کوئری‌ها از طریق Django ORM انجام می‌شوند.
*   **Secrets & Crypto:**
    *   **نگهداری Secrets:** `OK`. استفاده از `django-environ` و فایل `.env` که در `.gitignore` نادیده گرفته شده است.
    *   **رمزنگاری درست:** `OK`. پروژه از سیستم هشینگ پسورد داخلی و امن جنگو استفاده می‌کند.
    *   **Token Expiry:** `PARTIAL`. عمر Access Token به مدت ۱۵ روز تنظیم شده که کمی طولانی است. (به بخش یافته‌ها مراجعه شود).
*   **Rate limiting / Abuse:**
    *   **جلوگیری Brute-force Login/OTP:** `OK`. اندپوینت `RequestOTP` دارای Rate Limit بر اساس IP و شماره تلفن است. اندپوینت `VerifyOTP` نیز پس از ۵ تلاش ناموفق، کد را غیرفعال می‌کند.

---

## E) لایه داده و پایداری (Data Layer & Consistency)

*   **Schema Constraints:** `OK`. استفاده صحیح از `unique`, `FK` در مدل‌ها.
*   **Indexes:** `OK`. ایندکس‌ها روی فیلدهای کلیدی و پرتکرار در کوئری‌ها (مانند `slug`, `user`, `order_date`) تعریف شده‌اند.
*   **Transaction Boundaries:** `OK`. استفاده صحیح از `transaction.atomic` برای عملیات حساس مانند ایجاد سفارش.
*   **N+1 و Pagination:** `OK`. صفحه‌بندی به درستی پیاده‌سازی شده و از `prefetch_related` برای جلوگیری از مشکل N+1 در کوئری‌های پیچیده (مانند واکشی سفارش‌ها و آیتم‌هایشان) استفاده شده است.
*   **Soft Delete vs Hard Delete:** `BROKEN`. پروژه از Hard Delete برای مدل‌های حساس مانند `Product` استفاده می‌کند که می‌تواند منجر به از دست رفتن یکپارچگی داده‌های تاریخی شود. (به بخش یافته‌ها مراجعه شود).

---

## F) قابلیت اطمینان و مشاهده‌پذیری (Reliability / Observability)

*   **Error Handling استاندارد:** `OK`. یک Exception Handler سفارشی و یک Renderer سفارشی برای استانداردسازی پاسخ‌های خطا وجود دارد.
*   **Logging ساخت‌یافته:** `OK`. استفاده از `python-json-logger` برای تولید لاگ‌های JSON.
*   **Tracing/Metrics:** `OK`. ادغام موفق با `django-prometheus` برای متریک‌ها و `OpenTelemetry` برای تریسنگ توزیع‌شده.
*   **Retries/Timeouts:** `OK`. تسک‌های سلری (مانند ارسال ایمیل) با سیاست تلاش مجدد (retry policy) تعریف شده‌اند.
*   **Correlation ID:** `PARTIAL`. زیرساخت لاگینگ آماده است، اما هیچ Middleware ای برای تزریق خودکار Correlation ID به لاگ‌ها وجود ندارد. (به بخش یافته‌ها مراجعه شود).

---

## G) کارایی و مقیاس‌پذیری (Performance & Scalability)

*   **Caching Strategy:** `OK`. استراتژی کشینگ و ابطال آن به خوبی برای اندپوینت‌های لیست محصولات، جزئیات محصول و دسته‌بندی‌ها با استفاده از `django-redis` پیاده‌سازی شده است.
*   **Queue/Background Jobs:** `OK`. استفاده گسترده و صحیح از Celery برای انجام کارهای زمان‌بر در پس‌زمینه (ارسال ایمیل، پردازش پرداخت، کنسل کردن سفارش‌ها).
*   **Hot Paths & Bottlenecks:** `OK`.
    *   **جستجوی محصول:** با استفاده از `TrigramSimilarity` در PostgreSQL به شکل بسیار کارآمدی پیاده‌سازی شده است.
    *   **ایجاد سفارش:** به دلیل نیاز به قفل تراکنشی، می‌تواند یک گلوگاه بالقوه باشد، اما این یک Trade-off ضروری برای حفظ صحت داده است و نه یک ضعف طراحی.

---

## H) تست‌پذیری و پوشش کد (Testability & Coverage)

*   **تست‌های واحد/یکپارچه:** `BROKEN`. پوشش تست بسیار ضعیف است.
    *   **`orders` و `payment`:** هیچ تستی برای این دو ماژول حیاتی وجود ندارد. این یک ریسک بزرگ است. (به بخش یافته‌ها مراجعه شود).
    *   **`shop`:** این ماژول تست‌های خوبی دارد که شامل تست‌های امنیتی برای کنترل دسترسی نیز می‌شود.
*   **تست برای Race-condition:** `NOT FOUND IN CODE`.
*   **تست‌های امنیتی:** `PARTIAL`. تست‌های خوبی برای کنترل دسترسی در `shop` وجود دارد، اما برای سایر بخش‌ها وجود ندارد.

---

## یافته‌های کلیدی (Actionable Findings)

**[Severity: P0] فقدان کامل تست برای ماژول‌های حیاتی Orders و Payment**

*   **Evidence:** `orders/` و `payment/` -> عدم وجود پوشه `tests`.
    *   هیچ تست خودکاری برای پوشش منطق ایجاد سفارش، کاهش موجودی، اعمال کوپن، پردازش وب‌هوک پرداخت و تغییر وضعیت سفارش وجود ندارد.
*   **Impact:** **مالی / داده.** هرگونه تغییر کوچک در این ماژول‌ها می‌تواند به راحتی منجر به باگ‌های فاجعه‌بار شود؛ مانند محاسبه اشتباه قیمت نهایی، عدم کاهش موجودی (Oversell)، یا پردازش نکردن پرداخت‌های موفق. نگهداری و توسعه این بخش از کد در بلندمدت بسیار پرخطر است.
*   **Exploit/Repro:** یک توسعه‌دهنده در آینده یک فیلد به `OrderItem` اضافه می‌کند که باعث اختلال در `OrderCreateSerializer` می‌شود. از آنجایی که تستی وجود ندارد، این باگ تنها در محیط پروداکشن و پس از شکایت کاربران کشف می‌شود.
*   **Fix:**
    1.  ایجاد فایل `orders/tests.py`.
    2.  نوشتن یک `APITestCase` برای `OrderViewSet`.
    3.  پیاده‌سازی یک تست (`test_create_order_successfully`) که یک کاربر را احراز هویت کرده، محصولی را به سبد خرید اضافه کرده، و سپس با فراخوانی اندپوینت `POST /api/v1/orders/` یک سفارش موفق ایجاد می‌کند.
    4.  درون تست باید assert شود که کد وضعیت 201 است، یک آبجکت `Order` و `OrderItem` در دیتابیس ساخته شده، و `product.stock` به درستی کم شده است.
*   **Regression tests:** خود تستی که اضافه می‌شود، رگرسیون را پوشش خواهد داد.

**[Severity: P1] استفاده از Hard Delete برای محصولات و ریسک از دست رفتن داده‌های تاریخی**

*   **Evidence:** `shop/models.py` -> `Product` & `orders/models.py` -> `OrderItem`.
    *   فیلد `product` در مدل `OrderItem` دارای `on_delete=models.CASCADE` است. این یعنی اگر یک محصول از دیتابیس حذف شود، تمام رکوردهای `OrderItem` مرتبط با آن نیز حذف می‌شوند.
*   **Impact:** **داده.** این طراحی باعث می‌شود که تاریخچه سفارش‌ها ناقص شود. اگر یک محصول حذف شود، دیگر نمی‌توان گزارش‌های دقیقی از فروش آن محصول در گذشته تهیه کرد، زیرا تمام ردپاهای آن از سفارش‌ها پاک می‌شود.
*   **Exploit/Repro:**
    1.  یک محصول "لپ‌تاپ مدل X" در ۱۰۰ سفارش مختلف فروخته شده است.
    2.  ادمین تصمیم می‌گیرد این محصول را از فروشگاه حذف کند و رکورد `Product` آن را از پنل ادمین پاک می‌کند.
    3.  بلافاصله، ۱۰۰ رکورد `OrderItem` مربوط به این محصول از دیتابیس حذف می‌شوند.
    4.  در گزارش فروش ماهانه، دیگر هیچ اثری از فروش این ۱۰۰ لپ‌تاپ وجود ندارد.
*   **Fix:**
    1.  تغییر `on_delete=models.CASCADE` به `on_delete=models.SET_NULL` (یا `PROTECT`) در مدل `OrderItem`.
    2.  افزودن یک فیلد `is_active = models.BooleanField(default=True)` به مدل `Product`.
    3.  تغییر کوئری‌ست پیش‌فرض مدیر مدل (`Product.objects`) تا فقط محصولات فعال را برگرداند: `Product.objects.filter(is_active=True)`.
    4.  در پنل ادمین، اکشن "حذف" را با اکشنی برای غیرفعال کردن محصول جایگزین کنید.
*   **Regression tests:**
    1.  یک تست بنویسید که یک محصول را حذف (غیرفعال) می‌کند.
    2.  Assert کنید که `OrderItem` های مرتبط با آن محصول هنوز در دیتابیس وجود دارند.

**[Severity: P2] عمر طولانی (۱۵ روز) برای Access Token**

*   **Evidence:** `ecommerce_api/settings/base.py` -> `SIMPLE_JWT`.
    *   `'ACCESS_TOKEN_LIFETIME': timedelta(days=15)`
*   **Impact:** **امنیتی.** اگر یک Access Token به سرقت برود (مثلاً از طریق حمله XSS یا بدافزار روی دستگاه کاربر)، مهاجم می‌تواند تا ۱۵ روز کامل به حساب کاربری آن شخص دسترسی داشته باشد، حتی اگر کاربر رمز عبور خود را تغییر دهد.
*   **Exploit/Repro:**
    1.  یک مهاجم از طریق یک افزونه مرورگر مخرب، Access Token یک کاربر را از Local Storage او کپی می‌کند.
    2.  مهاجم تا ۱۵ روز آینده می‌تواند با استفاده از این توکن، از طرف کاربر سفارش ثبت کرده یا اطلاعات شخصی او را مشاهده کند.
*   **Fix:**
    ```python
    # ecommerce_api/settings/base.py
    SIMPLE_JWT = {
        'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),  # e.g., 1 hour
        'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
        # ... other settings
    }
    ```
*   **Regression tests:** یک تست یکپارچه که لاگین کرده، پس از گذشت زمان `ACCESS_TOKEN_LIFETIME` با Access Token قدیمی به یک اندپوینت محافظت‌شده درخواست می‌زند و انتظار پاسخ 401 (Unauthorized) دارد. سپس با Refresh Token یک توکن جدید گرفته و با آن با موفقیت درخواست می‌دهد.

**[Severity: P2] عدم وجود Correlation ID خودکار در لاگ‌ها**

*   **Evidence:** `ecommerce_api/settings/base.py` -> `MIDDLEWARE`.
    *   هیچ Middleware ای برای تولید و تزریق یک ID منحصر به فرد به هر درخواست (Request ID یا Correlation ID) وجود ندارد.
*   **Impact:** **عملیاتی/دیباگینگ.** در صورت بروز خطا در یک سیستم پیچیده، ردیابی کامل یک درخواست از ابتدا تا انتها در میان لاگ‌های مختلف بسیار دشوار می‌شود. نمی‌توان به راحتی تمام لاگ‌های مربوط به یک درخواست خاص را به هم مرتبط کرد.
*   **Exploit/Repro:** دو کاربر به صورت همزمان با خطای مشابهی در فرآیند پرداخت مواجه می‌شوند. تیم پشتیبانی برای دیباگ کردن، لاگ‌ها را بررسی می‌کند اما نمی‌تواند به راحتی تشخیص دهد کدام لاگ‌ها مربوط به کدام کاربر است، که این امر فرآیند عیب‌یابی را کند می‌کند.
*   **Fix:** یک Middleware ساده بنویسید که:
    1.  در ابتدای هر درخواست، یک `uuid.uuid4()` تولید کند.
    2.  این ID را به یک متغیر `thread-local` یا به آبجکت `request` اضافه کند.
    3.  تنظیمات `LOGGING` را طوری تغییر دهید که این ID را در تمام لاگ‌های JSON به صورت خودکار ثبت کند.
*   **Regression tests:** یک تست که یک درخواست به یک اندپوینت می‌زند و `caplog` (از pytest) را بررسی می‌کند تا مطمئن شود که لاگ‌های تولید شده در طول آن درخواست، همگی دارای یک Correlation ID یکسان هستند.
