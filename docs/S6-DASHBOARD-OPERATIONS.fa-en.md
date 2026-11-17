# داشبورد عملیاتی CSEF — S0 تا S7 / Evidence-first control board

**مخزن مجاز:** فقط \`ebrahimism/CSEF-Execution-Agent\`. این توسعه ادامهٔ S6a است؛ هستهٔ Gate، قراردادهای مدل، SQLite و backlog تاریخی بازنویسی نشده‌اند.

## هدف ثابت

CSEF یک ابزار داخلی برای ساخت نرم‌افزار واقعی از شرح‌حال مالک است؛ خودِ CSEF محصول فروشی نیست. صحت و کامل‌بودن، ممیزی، امنیت، بازیابی و تحویل بر کاهش هزینه مقدم هستند. پروندهٔ تاریخی \`docs/PROJECT-GOALS.json\` بدون تغییر باقی مانده، تصمیم به‌روزشده در \`docs/decisions/DEC-004-owner-software-factory.fa.md\` ثبت است. وضعیت مراحل باید بر پایهٔ **شواهد همان نسخه** تعیین شود.

## اجرای محلی

Windows 11 PowerShell از داخل ریشهٔ مخزن:

\`\`\`powershell
git pull origin main
python -m pip install -e .
New-Item -ItemType Directory -Force .\csef-workspace | Out-Null
python -m csef_gate.ui.server --workspace .\csef-workspace --port 8765
\`\`\`

مرورگر همان دستگاه: \`http://127.0.0.1:8765/\`. با کلید \`EN / فا\` تغییر جهت کامل LTR / RTL انجام می‌شود.

Linux: \`python3 -m csef_gate.ui.server --workspace ./csef-workspace --port 8765\` (پوشهٔ workspace باید از قبل وجود داشته باشد). **این سرویس فقط localhost است و روی VPS عمومی یا reverse proxy نباید منتشر شود**؛ فاقد احراز هویت چندکاربره و TLS است.

## اتصال هر مرحله به شواهد

| مرحله | نمایش واقعی در UI | محدودیت |
| --- | --- | --- |
| S0 | owner version/hash، تاریخچهٔ اصلاح‌ها، دلیل تغییر، journal | سوابق تاریخی تسک‌های CSEF به‌اشتباه complete نمی‌شوند |
| S1 | شرح‌حال، نیازمندی‌ها، پاسخ‌های مالک، proposal DAG، task IDs و scope | استخراج کامل معنایی تمام نیازمندی‌ها هنوز اثبات نشده |
| S6a | نمایش دوزبانه، پروژه، گراف، تغییر امن پاسخ و refresh | فقط همین دستگاه |
| S2 | پیکربندی کلید بدون نمایش آن، شمارندهٔ واقعی provider request و unknown | بدون اثبات زندهٔ دو API یا cap تضمینی دلار |
| S3 | run، تعداد تلاش، task statusهای پیشنهادی/coded_unverified/unknown، راهنمای reconciliation | Resume خودکار در وضعیت نامعلوم همچنان غیرفعال |
| S4 | Gate spec integrity، شناسهٔ آزمون‌های منجمد، evaluation، نتیجهٔ case، boundary، هش گزارش | Docker reviewed-only فقط REVIEW؛ مجوز PASS یا guest VM تأییدشده ایجاد نمی‌شود |
| S5 | checkpointهای دارای شواهد؛ export فقط بعد از تأیید کامل Gate و سنجش هش منبع | ZIP به معنای استقرار عمومی یا تست نصب روی سیستم واقعی نیست |
| S7 | صریحاً not_verified تا ساخت و نصب واقعی پروژهٔ چندماژولی | هیچ درصد ساختگی برای پایان محصول |

فیلدهای status/task از جداول موجود \`revisions\`، \`changes\`، \`runs\`، \`attempts\`، \`evaluations\`، \`checkpoints\` و \`calls\` خوانده می‌شوند. متن برنامه و پیام مدل هرگز authority نمی‌سازند. شواهد پیشین بر اساس hash هدف و graph مربوطه از برنامهٔ جاری جدا می‌شوند.

### اعمال مجاز از داشبورد

1. **ثبت/اصلاح پاسخ‌های مالک:** فرم موجود و reason؛ سرور در تراکنش واحد، version را چک و از \`ProjectBook._amend_in\` استفاده می‌کند. تغییر، مراحل/شواهد نسخهٔ قبلی را stale می‌کند.
2. **تولید proposal با API:** همان \`plan_brief\` موجود؛ انتخاب explicit ارائه‌دهنده و مدل و رضایت هزینه؛ خروجی همیشه proposed است.
3. **اجرای آزمون محدود REVIEW:** فقط روی Run موجود، پس از بررسی دستی کد، digest ثابت Docker و رضایت جداگانه. سرور فقط \`DockerReviewedExecutor\` و \`Gate.evaluate(..., measure_only=True)\` را فراخوانی می‌کند؛ هیچ اجرای بدون sandbox روی میزبان یا PASS جعلی ندارد.
4. **بسته‌بندی checkpoint قبلاً پذیرفته‌شده:** فقط \`_delivery\` موجود، دوباره‌سنجی هش گزارش/منبع، ثبت SHA-256 فایل ZIP در SQLite، دانلود فقط تا وقتی checkpoint و hash فایل و owner revision همچنان معتبر باشند.
5. **بازخوانی و عیب‌یابی:** refresh، وضعیت manual reconciliation برای تلاش نامعلوم، نمودار وابستگی و پروندهٔ شواهد قابل مشاهده. هیچ \`POST /accept\` یا \`POST /resume\` نامطمئن ارائه نشده است.

**مهم:** عبارت \`REVIEW\` نتیجهٔ آزمایشِ code از قبل بررسی‌شده است و \`PASS\` نیست؛ Docker container جای guest VM اثبات‌شده را نمی‌گیرد. اگر Docker یا image معتبر وجود نداشته باشد، عملیات با خطا متوقف می‌شود، نه fallback روی میزبان.

### امنیت و حریم خصوصی

- localhost ثابت، Host و Origin دقیق، CSRF تصادفی در حافظه، JSON محدود، CSP بدون inline/third-party، static assets همان مبدأ.
- TextContent برای متن کاربر و مدل، بدون \`innerHTML\` یا اجرای کد مدل.
- شناسه‌های پروژه و Run canonical، عدم دنبال‌کردن symlink/reparse point، بدون مسیر دلخواه export یا دانلود.
- فقط رکوردهای عملیاتی محدود به UI ارسال می‌شوند؛ مسیر فایل‌های محلی، رسید کامل مدل، stdout/stderr و کلیدهای API روی رابط افشا نمی‌شوند.
- بستهٔ خروجی دوباره با hash و نسخهٔ مالک اعتبارسنجی می‌شود؛ تغییر فایل یا تغییر هدف، دانلود را متوقف می‌کند.
- هیچ کدی در Gate/security core تغییر داده نشده؛ تنها آداپتر UI توسعه یافته است.

## آزمون‌های خودکار و واقعی مرورگر

\`\`\`powershell
python -m pytest -o addopts='' -q tests/ui/test_dashboard.py tests/ui/test_dashboard_operations.py
python -m pytest -o addopts='' -q tests
\`\`\`

Workflow جداگانهٔ \`.github/workflows/dashboard-visual.yml\` در GitHub Actions مرورگر واقعی Chromium را نصب می‌کند و screenshot کامل در چهار حالت زیر تولید می‌کند:

- Desktop 1440×900 — Persian RTL
- Desktop 1440×900 — English LTR
- Mobile 390×844 — Persian RTL
- Mobile 390×844 — English LTR

تست تعامل ثبت پروژه، نمایش S0—S7، نیازمندی، شواهد و عدم سرریز افقی صفحه را بررسی می‌کند؛ تصویرها به artifact \`csef-dashboard-browser-evidence\` پیوست می‌شوند. این آزمونِ عملی مرورگر با بررسی دستیِ طراحی روی انواع دستگاه متفاوت است؛ QA همهٔ مرورگرها ادعا نمی‌شود.

## شواهد تکمیل‌شده و باقیمانده

بعد از سبزشدن CI، نسخهٔ عملیاتیِ **داشبورد** برای مسیرهای موجود معتبر است. اما **اتمام S3، S4، S5 و S7** تا زمان آزمایش guest مستقل، بازیابی عمومی، نصب کامل چندماژولی و آزمون محصول واقعی ادعا نمی‌شود. این تفکیک در خود رابط هم قابل مشاهده است.
