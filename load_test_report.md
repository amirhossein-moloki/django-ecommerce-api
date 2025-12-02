# گزارش تست بار (Load Testing)

## مقدمه

این گزارش، نتایج و یافته‌های تست بار انجام شده بر روی اپلیکیشن را با هدف شناسایی گلوگاه‌ها (Bottlenecks) قبل از استقرار در محیط پروداکشن، ارائه می‌دهد.

## ابزارها و سناریوها

- **ابزار تست:** Locust
- **سناریوهای تست:**
  1.  **ثبت‌نام و لاگین:** شبیه‌سازی فرآیند درخواست و تایید OTP.
  2.  **مرور و خرید:** شبیه‌سازی فرآیند جستجو، مشاهده محصول، افزودن به سبد خرید و ثبت نهایی سفارش.

## اسکریپت تست

فایل `locustfile.py` با محتوای زیر برای اجرای تست‌ها استفاده شد:

```python
import random
from locust import HttpUser, task, between, TaskSet

class AuthTaskSet(TaskSet):
    def on_start(self):
        """Called when a virtual user starts executing this TaskSet."""
        # Generate a random phone number for each user
        self.phone_number = f"0912{random.randint(1000000, 9999999)}"
        self.otp_code = None

    @task
    def request_otp(self):
        """Simulate a user requesting an OTP."""
        response = self.client.post("/auth/request-otp/", json={"phone": self.phone_number})
        if response.status_code == 200:
            self.otp_code = "123456"  # Using the fixed OTP for DEBUG mode
            self.verify_otp()

    def verify_otp(self):
        """Simulate a user verifying an OTP."""
        if not self.otp_code:
            return

        response = self.client.post("/auth/verify-otp/", json={"phone": self.phone_number, "code": self.otp_code})
        if response.status_code == 200:
            self.user.access_token = response.json().get("access")
            # After successful login, interrupt this TaskSet to start shopping
            self.interrupt()

class ShoppingTaskSet(TaskSet):
    def on_start(self):
        """Called when a virtual user starts executing this TaskSet."""
        if not self.user.access_token:
            self.interrupt() # If not logged in, go back to AuthTaskSet
            return

        self.client.headers["Authorization"] = f"Bearer {self.user.access_token}"
        self.product_slugs = []

    @task(1)
    def list_products(self):
        """Simulate a user listing products."""
        response = self.client.get("/api/v1/products/")
        if response.status_code == 200:
            products = response.json().get("results", [])
            if products:
                self.product_slugs = [p["slug"] for p in products]
                self.view_product()

    def view_product(self):
        """Simulate a user viewing a product."""
        if not self.product_slugs:
            return

        product_slug = random.choice(self.product_slugs)
        self.client.get(f"/api/v1/products/{product_slug}/")
        self.add_to_cart(product_slug)


    def add_to_cart(self, product_slug):
        """Simulate a user adding a product to the cart."""
        response = self.client.get(f"/api/v1/products/{product_slug}/")
        if response.status_code == 200:
            product_id = response.json().get("id")
            if product_id:
                self.client.post(f"/api/v1/cart/add/{product_id}/")
                self.checkout()


    def checkout(self):
        """Simulate a user checking out."""
        self.client.post("/api/v1/orders/")

class WebsiteUser(HttpUser):
    host = "http://127.0.0.1:8000"
    wait_time = between(1, 5)
    tasks = {AuthTaskSet: 1, ShoppingTaskSet: 3} # Prioritize shopping tasks
    access_token = None

    def on_start(self):
        """Called when a virtual user is started."""
        self.client.headers = {"Content-Type": "application/json"}
```

## نتایج و مشکلات

در حین اجرای تست بار، با مشکلات متعددی مواجه شدیم که مانع از اجرای موفقیت‌آمیز تست شدند. خطای اصلی که به طور مداوم با آن روبرو شدیم، `django.db.utils.OperationalError: no such table: sms_otpcode` بود.

این خطا نشان می‌دهد که جدول مربوط به مدل `OTPCode` در دیتابیس `sqlite` که برای تست استفاده می‌شد، ایجاد نشده بود. برای حل این مشکل، راه حل‌های مختلفی امتحان شد، از جمله:

-   اجرای سرور جنگو با تنظیمات تست (`ecommerce_api.settings.test`).
-   استفاده از دیتابیس `sqlite` مبتنی بر فایل به جای دیتابیس در حافظه.
-   اطمینان از توقف کامل سرورهای قدیمی قبل از اجرای سرور جدید.
-   تعریف متغیرهای محیطی به صورت `inline` برای اطمینان از بارگذاری صحیح آن‌ها.
-   اجرای `migrate` به صورت جداگانه برای اپ `sms`.

با وجود تمام این تلاش‌ها، مشکل همچنان پابرجا بود. این موضوع نشان‌دهنده یک مشکل عمیق‌تر در نحوه مدیریت تنظیمات و دیتابیس در محیط تست است که نیاز به بررسی بیشتر دارد.

## پیشنهادات

-   **بررسی دقیق تنظیمات جنگو:** لازم است که نحوه بارگذاری فایل‌های تنظیمات (`settings.py`) و متغیرهای محیطی در پروژه به دقت بررسی شود تا اطمینان حاصل شود که در محیط تست، فقط از تنظیمات مربوط به تست استفاده می‌شود.
-   **استفاده از `pytest-django`:** برای مدیریت بهتر محیط تست و دیتابیس، پیشنهاد می‌شود که از کتابخانه `pytest-django` استفاده شود. این کتابخانه ابزارهای قدرتمندی برای ایجاد و مدیریت دیتابیس‌های تستی فراهم می‌کند و می‌تواند به حل مشکل فعلی کمک کند.
-   **دیباگ `migrate`:** باید دلیل اینکه چرا دستور `migrate` جدول `sms_otpcode` را در دیتابیس `sqlite` ایجاد نمی‌کند، به دقت بررسی شود. ممکن است یک وابستگی پنهان یا مشکل در فایل‌های `migration` وجود داشته باشد.

## جمع‌بندی

با توجه به مشکلات پیش آمده، امکان اجرای کامل تست بار و به دست آوردن معیارهای عملکردی مانند تعداد درخواست قابل تحمل و Latency وجود نداشت. با این حال، این فرآیند به شناسایی یک مشکل اساسی در پیکربندی محیط تست پروژه کمک کرد که حل آن برای اطمینان از صحت و پایداری اپلیکیشن در آینده، ضروری است.
