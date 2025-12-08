# گزارش حسابرسی فنی پروژه فروشگاهی

## A) خلاصه اجرایی

**وضعیت کلی سیستم:** **نیازمند اصلاحات.** معماری سیستم بر پایه یک Monolith ماژولار با استفاده از Django استوار است که انتخاب مناسبی برای این پروژه است. استفاده از Celery برای کارهای پس‌زمینه، Redis برای کش و PostgreSQL به عنوان پایگاه داده، زیرساخت قابل قبولی را فراهم کرده است. با این حال، چندین ریسک امنیتی و منطقی شناسایی شده که نیازمند توجه فوری هستند. همچنین، فقدان تست‌های خودکار یک ضعف اساسی است که قابلیت اطمینان و نگهداری‌پذیری سیستم را به شدت کاهش می‌دهد.

**۳ ریسک حیاتی اول:**
1.  **ریسک امنیتی (P0):** وجود OTP ثابت (`123456`) در حالت `DEBUG` که می‌تواند در صورت تنظیمات اشتباه در محیط‌های غیرمحلی، منجر به دسترسی غیرمجاز به حساب‌های کاربری شود.
2.  **ریسک داده/مالی (P1):** عدم وجود مکانیسم تلاش مجدد (retry) در پردازش وب‌هوک پرداخت، که ممکن است در شرایط خاص (مانند دریافت وب‌هوک قبل از ذخیره کامل سفارش) منجر به عدم ثبت پرداخت و از دست رفتن سفارش شود.
3.  **ریسک قابلیت اطمینان (P1):** نبود کامل تست‌های خودکار (unit/integration) که باعث می‌شود هر تغییری در کد مستعد ایجاد رگرسیون (regression) باشد و هزینه‌های نگهداری و توسعه را در بلندمدت به شدت افزایش دهد.

**۳ پیشنهاد فوری:**
1.  **حذف OTP ثابت:** کد مربوط به OTP ثابت در `account/views.py` را فوراً حذف کرده و از OTPهای تصادفی در همه محیط‌ها استفاده کنید. برای تست، از مکانیزم‌های دیگری مانند لاگ کردن OTP در کنسول در حالت `DEBUG` بهره بگیرید.
2.  **پیاده‌سازی Retry در وب‌هوک پرداخت:** تسک Celery مربوط به پردازش وب‌هوک پرداخت در `payment/tasks.py` را به گونه‌ای اصلاح کنید که در صورت عدم یافتن سفارش، با یک تاخیر کوتاه (مثلاً چند ثانیه) مجدداً تلاش کند.
3.  **ایجاد زیرساخت تست:** فریم‌ورک تست را با `pytest` راه‌اندازی کرده و اولین تست‌های حیاتی را برای فرآیندهای احراز هویت (OTP) و ایجاد سفارش بنویسید تا از کارکرد صحیح این مسیرهای کلیدی اطمینان حاصل شود.

---

## B) نقشه سیستم

**Tech Stack & Entry Points:**
*   **فریم‌ورک:** Django
*   **ORM/DB Driver:** Django ORM / `psycopg`
*   **Queue:** Celery
*   **Cache:** Redis (`django-redis`)
*   **Payment SDK:** یکپارچه‌سازی مستقیم با درگاه زیبال (کد سفارشی)
*   **نقاط ورود اصلی:**
    *   `docker-compose.yml`: سرویس `web` با Gunicorn روی پورت 8000 و `nginx` به عنوان reverse proxy روی پورت 80.
    *   `ecommerce_api/urls.py`: تعریف مسیرهای اصلی API که به اپلیکیشن‌های مختلف Django ارجاع داده می‌شوند.
*   **Middlewares/Guards:**
    *   `django-cors-headers` برای مدیریت CORS.
    *   احراز هویت مبتنی بر `djangorestframework-simplejwt` (JWT).
    *   کنترل دسترسی سفارشی در ویوها (مانند `IsAdminOrOwner` در `orders/permissions.py`).

**Domain Modules:**
*   **محصولات/دسته‌بندی:**
    *   `shop/models.py`: مدل‌های `Product` و `Category`.
    *   `shop/views.py`: `ProductViewSet` و `CategoryViewSet` برای عملیات CRUD.
    *   توابع کلیدی: `Product.update_rating_and_reviews_count`.
*   **موجودی/انبار:**
    *   `shop/models.py`: فیلد `stock` در مدل `Product`.
    *   `orders/serializers.py`: منطق کاهش موجودی در متد `save` از `OrderCreateSerializer` با استفاده از `select_for_update`.
*   **سبد خرید:**
    *   `cart/cart.py`: کلاس `Cart` که منطق سبد خرید را با استفاده از session مدیریت می‌کند.
    *   `cart/views.py`: `CartAPIView` برای افزودن، حذف و نمایش آیتم‌ها.
*   **سفارش‌ها:**
    *   `orders/models.py`: مدل‌های `Order` و `OrderItem`.
    *   `orders/services.py`: تابع `create_order` که فرآیند ایجاد سفارش را مدیریت می‌کند.
    *   `orders/serializers.py`: `OrderCreateSerializer` برای اعتبارسنجی و ساخت سفارش از روی سبد خرید.
*   **پرداخت:**
    *   `payment/views.py`: `PaymentProcessAPIView` برای شروع پرداخت و `PaymentWebhookAPIView` برای دریافت callback از درگاه.
    *   `payment/services.py`: توابع `process_payment` و `verify_payment`.
    *   `payment/tasks.py`: تسک `process_successful_payment` برای پردازش ناهمزمان پرداخت.
*   **ارسال:**
    *   `shipping/tasks.py`: تسک `create_postex_shipment_task` برای ثبت بارنامه پس از پرداخت موفق.
*   **تخفیف/کوپن:**
    *   `coupons/models.py`: مدل `Coupon`.
    *   `coupons/models.py`: متد `increment_usage_count` با استفاده از `F()` expression برای جلوگیری از race condition.
*   **مرجوعی/ریفاند:** **NOT FOUND IN CODE**
*   **کیف پول/اعتبار:** **NOT FOUND IN CODE**

---

## C) Domain Correctness Audit

*   **Pricing:**
    *   **منبع قیمت و جلوگیری از دستکاری:** **OK.** قیمت از مدل `Product.price` در سمت سرور خوانده می‌شود (`orders/serializers.py` در متد `save` از `OrderCreateSerializer`). این از دستکاری قیمت توسط کلاینت جلوگیری می‌کند.
    *   **محاسبه تخفیف‌ها و ارز:** **PARTIAL.** تخفیف در `OrderCreateSerializer` محاسبه و در سفارش ذخیره می‌شود. واحد پول (currency) در مدل `Order` وجود دارد اما به نظر می‌رسد به صورت hard-code شده و مکانیزم چندارزی پیاده‌سازی نشده است. سیاست گرد کردن (rounding) مشخص نیست.
    *   **مالیات/ارسال:** **PARTIAL.** هزینه ارسال و مالیات در `orders/serializers.py` به صورت مقادیر ثابت (`Decimal('15.00')` و `Decimal('0.09')`) محاسبه می‌شوند که در یک سیستم واقعی باید داینامیک باشند.
*   **Inventory & Oversell Prevention:**
    *   **قفل/رزرو موجودی:** **OK.** در `orders/serializers.py`، متد `save` از `transaction.atomic` و `select_for_update` برای قفل کردن رکوردهای محصول قبل از کاهش موجودی استفاده می‌کند که روش درستی برای جلوگیری از oversell است.
    *   **رقابت همزمان (Concurrency):** **OK.** استفاده از `select_for_update` و تراکنش اتمیک، رفتار سیستم را در شرایط رقابت همزمان امن می‌کند.
    *   **Rollback در خطای پرداخت:** **BROKEN.** سفارش قبل از پرداخت ایجاد شده و موجودی از انبار کسر می‌شود. اگر کاربر پرداخت را انجام ندهد، موجودی به انبار باز نمی‌گردد. این می‌تواند منجر به قفل شدن موجودی شود.
    *   **سیاست Stock Reservation Expiry:** **NOT FOUND IN CODE.** هیچ سیاستی برای آزادسازی موجودی سفارش‌های پرداخت‌نشده وجود ندارد.
*   **Cart → Order Integrity:**
    *   **تبدیل سبد به سفارش (Snapshot):** **OK.** در `orders/serializers.py`، هنگام ساخت `OrderItem`، قیمت محصول مستقیماً از مدل `Product` در لحظه ایجاد سفارش خوانده و ذخیره می‌شود. این یک snapshot صحیح از قیمت است.
    *   **جلوگیری از Stale Cart:** **OK.** قبل از ایجاد `OrderItem`، قیمت آیتم در سبد با قیمت فعلی محصول مقایسه می‌شود و در صورت مغایرت، خطا برگردانده می‌شود (`orders/serializers.py`).
    *   **Validation نهایی:** **OK.** اعتبارسنجی نهایی برای کوپن، آدرس و موجودی انبار در `OrderCreateSerializer` قبل از ساخت سفارش انجام می‌شود.
*   **Order State Machine:**
    *   **State های رسمی:** **PARTIAL.** State های سفارش و پرداخت در مدل `Order` (`Status` و `PaymentStatus`) تعریف شده‌اند. اما هیچ مکانیزم رسمی برای مدیریت انتقال وضعیت‌ها (transition logic) وجود ندارد و تغییرات مستقیماً با فراخوانی `.save()` انجام می‌شود.
    *   **Audit Trail:** **NOT FOUND IN CODE.** هیچ لاگ یا تاریخی از تغییرات وضعیت سفارش و کاربری که آن را تغییر داده، ثبت نمی‌شود.
    *   **Idempotency:** **OK.** در `payment/views.py`، وب‌هوک پرداخت با چک کردن وضعیت سفارش، از پردازش تکراری جلوگیری می‌کند که یک پیاده‌سازی خوب برای idempotency است.
*   **Payment Integration:**
    *   **Webhook/Callback Handler:** **OK.** `PaymentWebhookAPIView` در `payment/views.py` به عنوان هندلر وب‌هوک عمل می‌کند.
    *   **اعتبارسنجی امضا/Secret:** **OK.** وب‌هوک با استفاده از `X-Zibal-Secret` و `hmac.compare_digest` اعتبارسنجی می‌شود. همچنین IP منبع نیز کنترل می‌گردد.
    *   **جلوگیری از پرداخت تکراری:** **OK.** از طریق بررسی `order.payment_status` در وب‌هوک، از پردازش مجدد پرداخت موفق جلوگیری می‌شود.
    *   **Mapping Payment → Order Status:** **OK.** در `payment/services.py`، تابع `verify_payment` پس از تایید پرداخت، وضعیت سفارش را به `PAID` تغییر می‌دهد.
    *   **Handling تایم‌اوت/Partial Failure:** **BROKEN.** منطقی برای مدیریت سناریوهایی مانند عدم دریافت وب‌هوک از درگاه یا خطاهای شبکه در ارتباط با درگاه وجود ندارد.
    *   **Refund:** **NOT FOUND IN CODE.**

---

## D) Security Audit

*   **AuthN/AuthZ:**
    *   **روش احراز هویت:** **OK.** سیستم از OTP مبتنی بر شماره تلفن برای ورود و JWT (`simple-jwt`) برای مدیریت session استفاده می‌کند.
    *   **کنترل دسترسی روی منابع:** **OK.** در `orders/views.py`، با استفاده از `IsAdminOrOwner`، دسترسی به سفارش‌ها به درستی به مالک سفارش یا ادمین محدود شده است.
    *   **IDOR Check:** **OK.** کوئری `get_queryset` در `OrderViewSet` (`orders/views.py`) نتایج را بر اساس کاربر لاگین‌کرده فیلتر می‌کند و از دسترسی یک کاربر به سفارش‌های دیگران جلوگیری می‌کند.
*   **Input Validation:**
    *   **Schema Validation:** **OK.** `Django Rest Framework Serializers` در تمام ماژول‌ها برای اعتبارسنجی داده‌های ورودی استفاده می‌شود.
    *   **File Upload Validation:** **OK.** در `shop/models.py`، یک `FileValidator` سفارشی برای کنترل حجم و نوع فایل تصویر محصول استفاده شده است.
    *   **Mass Assignment:** **OK.** استفاده از `serializers` به جای `request.POST` یا موارد مشابه، از آسیب‌پذیری Mass Assignment جلوگیری می‌کند.
*   **Injection & SSRF:**
    *   **SQL Injection:** **OK.** استفاده از Django ORM در تمام کوئری‌های مشاهده‌شده، ریسک SQL Injection را به حداقل می‌رساند.
    *   **SSRF/Command Injection:** **NOT FOUND IN CODE.** کدی که URL خارجی دریافت کند یا از shell exec استفاده کند، مشاهده نشد.
*   **Secrets & Crypto:**
    *   **نگهداری Secrets:** **OK.** استفاده از فایل `.env` و `django-environ` برای مدیریت متغیرهای محیطی، روش استانداردی است.
    *   **رمزنگاری:** **PARTIAL.** مدل `UserAccount` از `AbstractBaseUser` ارث‌بری می‌کند و Django به صورت پیش‌فرض از hash الگوریتم‌های قوی مانند PBKDF2 برای رمزنگاری پسورد استفاده می‌کند. اما در این پروژه، کاربران پسورد ندارند و ورود فقط با OTP است که ریسک‌های خاص خود را دارد.
    *   **Token Rotation/Expiry:** **OK.** `simple-jwt` به صورت پیش‌فرض مکانیزم expiry برای توکن‌ها دارد و refresh token نیز پیاده‌سازی شده است.
*   **Rate Limiting / Abuse:**
    *   **Brute-force Login/OTP:** **OK.** در `account/views.py`، پس از ۵ تلاش ناموفق برای وارد کردن OTP، کد غیرفعال می‌شود که یک اقدام پیشگیرانه خوب است.
    *   **Rate limit روی Checkout/Payment:** **NOT FOUND IN CODE.** هیچ rate limit مشخصی روی اندپوینت‌های حساس مانند ایجاد سفارش یا پرداخت مشاهده نشد.
    *   **Captcha/Lockout Policy:** **NOT FOUND IN CODE.**

---

## E) Data Layer & Consistency

*   **Schema Constraints:** **OK.** استفاده مناسب از `unique`, `ForeignKey` و `check constraints` (از طریق `validators`) در مدل‌ها مشاهده می‌شود (مانند `unique_user_product_review` در `shop/models.py`).
*   **Index‌ها:** **OK.** ایندکس‌های مناسبی روی فیلدهای پرتکرار در کوئری‌ها (مانند `slug`, `name`, `category`) در مدل `Product` تعریف شده است.
*   **Transaction Boundaries:** **OK.** فرآیند ایجاد سفارش در `orders/serializers.py` داخل یک `transaction.atomic` قرار دارد که تضمین‌کننده atomicity است.
*   **N+1:** **OK.** در `orders/services.py`، تابع `get_user_orders` از `prefetch_related` برای جلوگیری از مشکل N+1 در هنگام خواندن آیتم‌های سفارش استفاده کرده است.
*   **Soft Delete vs Hard Delete:** **PARTIAL.** سیستم از Hard Delete استفاده می‌کند. این موضوع می‌تواند در آینده برای گزارش‌گیری و تحلیل داده‌ها مشکل‌ساز شود. به طور مثال، اگر محصولی حذف شود، تاریخچه آن در سفارش‌های قدیمی باقی می‌ماند اما خود محصول دیگر در دسترس نیست.

---

## F) Reliability / Observability

*   **Error Handling:** **PARTIAL.** یک `ApiResponse` استاندارد برای پاسخ‌های موفق و ناموفق وجود دارد، اما error code های مشخصی برای انواع خطاها تعریف نشده است.
*   **Logging:** **OK.** استفاده از `python-json-logger` و `OpenTelemetry` (بر اساس `requirements.txt`) نشان‌دهنده وجود لاگ‌گیری ساخت‌یافته و tracing است که برای قابلیت مشاهده‌پذیری بسیار مفید است.
*   **Tracing/Metrics:** **OK.** وجود `django-prometheus` و `OpenTelemetry` نشان‌دهنده جمع‌آوری متریک‌ها و trace هاست.
*   **Retries/Timeouts/Circuit Breaker:** **BROKEN.** در تعامل با سرویس‌های خارجی (پرداخت، پیامک، پست) هیچ‌گونه مکانیزم retry یا timeout handling مشاهده نشد. این موضوع می‌تواند در صورت بروز اختلال در این سرویس‌ها، سیستم را با مشکل مواجه کند.

---

## G) Performance & Scalability

*   **Caching Strategy:** **PARTIAL.** `Redis` در زیرساخت پروژه وجود دارد اما هیچ استراتژی کش مشخصی در لایه اپلیکیشن (مانند کش کردن کوئری‌های سنگین یا صفحات) مشاهده نشد.
*   **Queue/Background Jobs:** **OK.** استفاده از `Celery` برای کارهای زمان‌بر مانند ارسال ایمیل تایید سفارش (`orders/services.py`) و پردازش پرداخت (`payment/views.py`) یک اقدام موثر برای بهبود پرفورمنس و پاسخ‌دهی API است.
*   **Hot Paths & Bottlenecks:**
    *   **ایجاد سفارش:** فرآیند ایجاد سفارش (`OrderCreateSerializer.save`) به دلیل استفاده از `select_for_update` می‌تواند در ترافیک بالا به یک bottleneck تبدیل شود، زیرا ردیف‌های جدول محصول را قفل می‌کند. این طراحی برای دقت داده ضروری است اما باید برای مقیاس‌پذیری بالا مانیتور شود.

---

## H) Testability & Coverage

*   **تست‌های واحد/یکپارچه:** **BROKEN.** هیچ فایل تستی در پروژه یافت نشد. این یک ریسک بزرگ برای پایداری و نگهداری پروژه است.
*   **تست برای Race-condition و Idempotency:** **NOT FOUND IN CODE.**
*   **تست‌های امنیتی:** **NOT FOUND IN CODE.**

---

## Actionable Findings

**[Severity: P0] OTP ثابت در حالت DEBUG یک حفره امنیتی بزرگ است.**
*   **Evidence:** `account/views.py` → `generate_otp`
    ```python
    def generate_otp():
        if settings.DEBUG:
            return "123456"
        return str(random.randint(100000, 999999))
    ```
*   **Impact:** امنیتی. اگر `DEBUG=True` به اشتباه در محیط production یا staging فعال شود، هر کسی می‌تواند با شماره تلفن دیگران و کد `123456` وارد حساب آن‌ها شود.
*   **Repro:** ۱. سرور را با `DEBUG=True` اجرا کنید. ۲. شماره تلفن هر کاربری را در صفحه لاگین وارد کنید. ۳. کد `123456` را وارد کرده و به حساب او دسترسی پیدا کنید.
*   **Fix:** کد ثابت را حذف کنید. برای محیط توسعه، OTP را در کنسول لاگ کنید.
    ```python
    def generate_otp():
        otp = str(random.randint(100000, 999999))
        if settings.DEBUG:
            logger.info(f"Generated OTP for development: {otp}")
        return otp
    ```
*   **Regression tests:** یک تست بنویسید که اطمینان حاصل کند تابع `generate_otp` در حالت `DEBUG=False` هرگز مقدار ثابت برنمی‌گرداند.

**[Severity: P1] عدم آزادسازی موجودی در صورت عدم پرداخت سفارش.**
*   **Evidence:** `orders/serializers.py` → `OrderCreateSerializer.save`
    موجودی محصول بلافاصله پس از ایجاد سفارش و قبل از پرداخت، از انبار کسر می‌شود.
*   **Impact:** داده/UX. اگر کاربر پرداخت را تکمیل نکند، موجودی محصول به اشتباه در سیستم رزرو شده باقی می‌ماند و برای فروش در دسترس نخواهد بود.
*   **Repro:** ۱. محصولی را به سبد خرید اضافه کنید. ۲. سفارش را ثبت کنید تا به صفحه پرداخت منتقل شوید. ۳. از پرداخت انصراف دهید. ۴. موجودی محصول را چک کنید، خواهید دید که کم شده است.
*   **Fix:** یک تسک Celery دوره‌ای (periodic) ایجاد کنید تا سفارش‌های پرداخت‌نشده‌ای که از زمان ایجادشان مثلا ۱۰ دقیقه گذشته را پیدا کرده، وضعیت آن‌ها را به `CANCELED` تغییر داده و موجودی محصولاتشان را به انبار بازگرداند.
*   **Regression tests:** تستی بنویسید که سناریوی بالا را شبیه‌سازی کرده و بررسی کند که پس از زمان مشخص، موجودی به حالت اولیه بازمی‌گردد.

**[Severity: P1] عدم وجود تست‌های خودکار.**
*   **Evidence:** کل پروژه. هیچ فایل تستی (مانند `tests.py`) در هیچ یک از اپلیکیشن‌ها وجود ندارد.
*   **Impact:** قابلیت اطمینان/نگهداری. هر تغییری در کد می‌تواند منجر به شکستن عملکردهای موجود شود (regression). توسعه فیچرهای جدید کند و پرخطر خواهد بود.
*   **Repro:** هر تغییری در کد بدهید، هیچ راهی برای اطمینان از صحت عملکرد سیستم به جز تست دستی وجود ندارد.
*   **Fix:** `pytest-django` را به پروژه اضافه کنید. برای شروع، تست‌هایی برای مسیرهای حیاتی (critical paths) مانند ثبت‌نام با OTP، لاگین، افزودن به سبد خرید و ایجاد سفارش بنویسید.
*   **Regression tests:** (Not applicable)

**[Severity: P1] ریسک Race Condition در پردازش وب‌هوک پرداخت.**
*   **Evidence:** `payment/views.py` → `PaymentWebhookAPIView.post`
    کد تلاش می‌کند سفارش را با `track_id` پیدا کند و در `except Order.DoesNotExist` به سادگی عبور می‌کند، با این فرض که تسک Celery آن را مدیریت خواهد کرد. اما تسک نیز بلافاصله آن را پردازش می‌کند.
*   **Impact:** مالی/داده. اگر وب‌هوک پرداخت از درگاه، سریع‌تر از commit تراکنش ایجاد سفارش به دیتابیس برسد، `Order.DoesNotExist` رخ داده و پرداخت موفق هرگز در سیستم ثبت نمی‌شود.
*   **Repro:** این سناریو به سختی قابل بازتولید است و به زمان‌بندی (timing) بستگی دارد اما در سیستم‌های با بار زیاد محتمل است.
*   **Fix:** تسک Celery `process_successful_payment` در `payment/tasks.py` را با مکانیزم retry پیاده‌سازی کنید.
    ```python
    @shared_task(bind=True, max_retries=3, default_retry_delay=10)
    def process_successful_payment(self, track_id: str, success: bool):
        if not success:
            return
        try:
            order = Order.objects.get(payment_track_id=track_id)
            # ... process payment
        except Order.DoesNotExist:
            self.retry()
        except Exception as e:
            logger.error(...)
    ```
*   **Regression tests:** یک تست یکپارچه بنویسید که `process_successful_payment` را فراخوانی کند در حالی که سفارش هنوز در دیتابیس وجود ندارد و بررسی کند که تسک مجدداً تلاش می‌کند.

**[Severity: P2] هزینه‌های ثابت مالیات و ارسال.**
*   **Evidence:** `orders/serializers.py` → `OrderCreateSerializer.save`
*   **Impact:** منطق کسب‌وکار. این مقادیر باید داینامیک و قابل تنظیم باشند (مثلاً بر اساس آدرس کاربر یا وزن محصولات).
*   **Fix:** یک ماژول جدید برای حمل‌ونقل و مالیات ایجاد کنید که بر اساس قوانین کسب‌وکار، این مقادیر را محاسبه کند.
*   **Regression tests:** تستی بنویسید که با ورودی‌های مختلف (آدرس، وزن) هزینه ارسال و مالیات متفاوتی محاسبه شود.

**[Severity: P2] عدم وجود Audit Trail برای وضعیت سفارش.**
*   **Evidence:** `orders/models.py`. مدل `Order` تاریخچه تغییرات وضعیت را ذخیره نمی‌کند.
*   **Impact:** پشتیبانی/داده. در صورت بروز اختلاف با مشتری، هیچ سابقه‌ای برای پیگیری اینکه وضعیت سفارش چه زمانی و توسط چه کسی تغییر کرده، وجود ندارد.
*   **Fix:** از کتابخانه‌ای مانند `django-simple-history` برای ثبت تاریخچه تغییرات مدل `Order` استفاده کنید.
*   **Regression tests:** تستی بنویسید که وضعیت یک سفارش را تغییر دهد و بررسی کند که یک رکورد تاریخچه برای آن ثبت شده است.

**[Severity: P2] عدم وجود Rate Limiting روی اندپوینت‌های حساس.**
*   **Evidence:** `orders/views.py`, `payment/views.py`.
*   **Impact:** امنیتی/پایداری. اندپوینت‌های ایجاد سفارش و پرداخت می‌توانند مورد حمله DoS یا سوءاستفاده برای تست کارت‌های اعتباری سرقتی قرار گیرند.
*   **Fix:** از `django-rest-framework-simple-api-key` یا `throttling` داخلی DRF برای اعمال محدودیت درخواست بر اساس IP یا کاربر روی این اندپوینت‌ها استفاده کنید.
*   **Regression tests:** تستی بنویسید که نشان دهد پس از تعداد معینی درخواست، خطای `429 Too Many Requests` بازگردانده می‌شود.

**[Severity: P2] غیرفعال کردن Endpoints به جای حذف کامل.**
*   **Evidence:** `account/views.py` → `UserViewSet`
    متدهایی مانند `create`, `activation`, `set_password` فقط `404 NOT FOUND` برمی‌گردانند.
*   **Impact:** امنیتی/نگهداری. این کدها سطح حمله (attack surface) را بی‌دلیل افزایش داده و کد را پیچیده‌تر می‌کنند.
*   **Fix:** این متدها را به طور کامل از `UserViewSet` حذف کنید.
*   **Regression tests:** تستی بنویسید که اطمینان حاصل کند درخواست به این URLها (مثلاً `POST /auth/users/`) با موفقیت `404` دریافت می‌کند.

**[Severity: P2] عدم مدیریت خطای شبکه در ارتباط با سرویس‌های خارجی.**
*   **Evidence:** `payment/services.py`, `sms/providers.py`.
    درخواست‌ها به سرویس‌های خارجی (زیبال، sms.ir) داخل بلوک `try...except` برای خطاهای شبکه (مانند `requests.exceptions.Timeout`) قرار ندارند.
*   **Impact:** پایداری. در صورت عدم دسترسی به این سرویس‌ها، برنامه با یک exception کنترل‌نشده crash می‌کند.
*   **Fix:** تمام تماس‌های شبکه‌ای را در بلوک `try...except` مناسب قرار داده و خطاهای احتمالی را به شکل مناسب مدیریت کنید.
*   **Regression tests:** با استفاده از `mocking`، یک خطای شبکه را شبیه‌سازی کرده و بررسی کنید که برنامه به درستی آن را مدیریت می‌کند.

**[Severity: P2] استفاده از Hard Delete برای مدل‌های اصلی.**
*   **Evidence:** تمام مدل‌های پروژه.
*   **Impact:** داده. حذف فیزیکی رکوردها (مانند یک محصول) می‌تواند گزارش‌های گذشته را بی‌معنی کند و امکان بازیابی داده را از بین ببرد.
*   **Fix:** برای مدل‌های مهمی مانند `Product` و `Order`، از استراتژی Soft Delete (با افزودن یک فیلد `is_deleted` و یک manager سفارشی) استفاده کنید.
*   **Regression tests:** تستی بنویسید که یک شی را soft delete کرده و بررسی کند که دیگر در کوئری‌های پیش‌فرض ظاهر نمی‌شود اما در دیتابیس وجود دارد.
