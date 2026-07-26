# بستهٔ آمادهٔ اصلاح Ruff و CI

این بسته هفت فایل اصلاح‌شده و یک اسکریپت خودکار دارد. اسکریپت بدون دست‌کاری دستی فایل‌ها:

1. مخزن محلی را بررسی می‌کند.
2. شاخهٔ `main` را به‌روز می‌کند.
3. شاخهٔ `fix/ruff-ci` را می‌سازد.
4. هفت فایل آماده را جایگزین می‌کند.
5. بررسی‌های محلی در دسترس را اجرا می‌کند.
6. Commit و Push انجام می‌دهد.
7. صفحهٔ ساخت Pull Request را باز می‌کند یا با GitHub CLI آن را می‌سازد.

## روش ساده در ویندوز

فایل زیر را دوبار کلیک کنید:

```text
APPLY_FIX.cmd
```

وقتی مسیر مخزن را خواست، این مسیر یا مسیر واقعی خودتان را Paste کنید:

```text
C:\Faramarz\GitHub\11-HeatSafe\heatsafe-climate-air-quality-lab
```

اگر مرورگر باز شد، فقط دکمهٔ **Create pull request** را بزنید. عنوان و متن Pull Request از قبل آماده است.

## فایل‌های اصلاح‌شده

- `scripts/check_links.py`
- `scripts/check_secrets.py`
- `scripts/generate_demo_data.py`
- `scripts/package_release.py`
- `tests/test_core.py`
- `tests/test_data_and_connectors.py`
- `tests/test_research.py`

## نتیجهٔ بررسی پیش از بسته‌بندی

- ۳۰ تست موفق
- Python compilation موفق
- Link check موفق
- Secret check موفق
- هیچ الگوریتم علمی، API، Frontend یا Docker تغییر نکرده است
