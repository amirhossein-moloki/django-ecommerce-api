#
# --- مرحله ۱: Builder ---
# از یک ایمیج پایه سبک پایتون برای ساخت وابستگی‌ها استفاده می‌کنیم.
#
FROM python:3.11-slim-bookworm AS builder

# متغیرهای محیطی برای جلوگیری از ایجاد فایل‌های .pyc و اطمینان از خروجی مستقیم در ترمینال.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# آرگومان بیلد برای تشخیص محیط توسعه.
ARG DEV=false

# نصب وابستگی‌های سیستمی مورد نیاز برای ساخت پکیج‌های پایتون (مثل psycopg2).
# libmagic1 برای کتابخانه python-magic نیاز است.
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential libpq-dev libmagic1 && \
    rm -rf /var/lib/apt/lists/*

# تنظیم دایرکتوری کاری داخل کانتینر.
WORKDIR /app

# کپی کردن فایل‌های وابستگی‌ها و نصب آن‌ها.
# این کار به ما اجازه می‌دهد تا از کش لایه‌های داکر به بهترین شکل استفاده کنیم.
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
# اگر در محیط توسعه هستیم (DEV=true)، وابستگی‌های توسعه را نیز نصب می‌کنیم.
RUN if [ "$DEV" = "true" ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

#
# --- مرحله ۲: Final ---
# از یک ایمیج پایه تمیز برای محیط نهایی استفاده می‌کنیم تا حجم ایمیج نهایی کمتر باشد.
#
FROM python:3.11-slim-bookworm AS final

# نصب وابستگی‌های سیستمی که در زمان اجرا نیاز هستند.
RUN apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 && \
    rm -rf /var/lib/apt/lists/*

# تنظیم متغیرهای محیطی برای ایمیج نهایی.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=ecommerce_api.settings.production

WORKDIR /app

# ایجاد یک کاربر و گروه غیر-root برای اجرای برنامه به دلایل امنیتی.
RUN addgroup --system django && \
    adduser --system --ingroup django django

# کپی کردن پکیج‌های نصب شده پایتون از مرحله builder.
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# کپی کردن کدهای برنامه به ایمیج نهایی.
COPY . .

# اطمینان از اجرایی بودن اسکریپت‌های entrypoint و wait-for-it.
RUN chmod +x /app/entrypoint.sh && \
    chmod +x /app/wait-for-it.sh

# تغییر مالکیت فایل‌های برنامه به کاربر غیر-root.
RUN chown -R django:django /app

# سوییچ به کاربر غیر-root.
USER django

# باز کردن پورت ۸۰۰۰ برای دسترسی به برنامه.
EXPOSE 8000

# تنظیم entrypoint کانتینر.
ENTRYPOINT ["/app/entrypoint.sh"]

# دستور پیش‌فرض برای اجرای برنامه (gunicorn در محیط پروداکشن).
CMD ["gunicorn", "ecommerce_api.wsgi:application", "--bind", "0.0.0.0:8000"]
