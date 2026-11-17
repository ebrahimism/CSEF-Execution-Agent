# راهنمای عملی تأیید دو API واقعی در CSEF

این راهنما برای آزمایش اتصال مستقیم OpenAI Responses و Anthropic Messages بدون نیاز به Codex است.

**وضعیت فعلی:** کدهای دو API و آزمایش‌های شبیه‌سازی‌شده وجود دارند. نتیجهٔ واقعی فقط بعد از اجرای این ابزار با کلیدهای API متعلق به خودتان مشخص می‌شود. هیچ کلید یا رمز عبوری را در GitHub، Issue، PR یا این گفت‌وگو وارد نکنید.

## نتیجهٔ مورد انتظار

ابزار، یک درخواست کوچک به هر سرویس می‌فرستد و انتظار دارد JSON زیر را برگردانند:

    {"ok": true, "proof": "csef-live-check"}

گزارش خروجی فقط وضعیت، نام مدل، تعداد توکن (در صورت اعلام سرویس)، و زمان اجرا را نمایش می‌دهد. برای مصرف دلاری مقدار null ثبت می‌شود؛ این مقدار **به معنای رایگان بودن نیست**. نتیجهٔ PASS فقط اتصال و پاسخ ساختاریافتهٔ این دو مدل را ثابت می‌کند، نه امکان اجرای ایمن کد یا خودتوسعهٔ کامل را.

## Windows 11 / PowerShell

اگر مخزن را قبلاً دریافت نکرده‌اید:

    git clone https://github.com/ebrahimism/CSEF-Execution-Agent.git
    cd CSEF-Execution-Agent

برای اجرای نسخهٔ آزمایشی قبل از ادغام PR:

    git fetch origin
    git switch --track origin/validation/live-provider-smoke

اگر شاخهٔ محلی از قبل وجود دارد، از git switch validation/live-provider-smoke استفاده کنید. بعد:

    python --version
    python -m pip install -e .
    python -m pip install pytest
    python -m pytest -q tests/providers

کلیدهای API را به‌صورت خصوصی وارد کنید. در این روش متن کلید داخل تاریخچهٔ دستورهای PowerShell نوشته نمی‌شود:

    $openaiSecret = Read-Host "OpenAI API key" -AsSecureString
    $anthropicSecret = Read-Host "Anthropic API key" -AsSecureString
    $env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new("", $openaiSecret).Password
    $env:ANTHROPIC_API_KEY = [System.Net.NetworkCredential]::new("", $anthropicSecret).Password

در فرمان زیر YOUR_OPENAI_MODEL و YOUR_ANTHROPIC_MODEL را با شناسهٔ دقیق مدلی که در حساب API خودتان فعال است جایگزین کنید:

    python -m csef_gate.providers.smoke --openai-model YOUR_OPENAI_MODEL --anthropic-model YOUR_ANTHROPIC_MODEL

پس از پایان، حتی در صورت شکست:

    Remove-Item Env:\OPENAI_API_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:\ANTHROPIC_API_KEY -ErrorAction SilentlyContinue
    Remove-Variable openaiSecret,anthropicSecret -ErrorAction SilentlyContinue

نکته: کلید در زمان اجرا به‌صورت موقت در محیط همان نشست وجود دارد؛ از رایانهٔ مورد اعتماد استفاده کنید و کلید را در فایل .env یا فایل قابل‌انتشار Git ذخیره نکنید.

## Ubuntu / Bash

در پوشهٔ همین شاخه و پس از نصب پروژه:

    python3 -m pip install -e .
    read -r -s -p 'OpenAI API key: ' OPENAI_API_KEY; echo
    read -r -s -p 'Anthropic API key: ' ANTHROPIC_API_KEY; echo
    export OPENAI_API_KEY ANTHROPIC_API_KEY
    python3 -m csef_gate.providers.smoke --openai-model YOUR_OPENAI_MODEL --anthropic-model YOUR_ANTHROPIC_MODEL
    unset OPENAI_API_KEY ANTHROPIC_API_KEY

بهتر است این آزمایش را در یک محیط مجازی Python انجام دهید.

## معیار پذیرش و توقف

- باید هر دو درخواست به مدل واقعی ارسال و خروجی JSON مطابق schema دریافت شود.
- اگر یکی از کلیدها وارد نشده باشد، قبل از ارسال اولین درخواست برنامه متوقف می‌شود.
- در خطای شبکه یا API، برنامه تلاش دوبارهٔ خودکار انجام نمی‌دهد؛ اجرای مجدد ممکن است هزینهٔ دیگری ایجاد کند.
- پیام خطای HTTP 401، 403 یا 429 لزوماً به معنی خرابی CSEF نیست؛ می‌تواند از اعتبار کلید، دسترسی مدل یا محدودیت حساب باشد.
- در خروجی FAILED، ادعای موفقیت دو API نکنید.
- تا پیش از تکمیل محیط اجرای مستقل و آزمون مرز امنیتی، این آزمایش اجازهٔ PASS نهایی Gate یا انتشار خودکار نمی‌دهد.

## بعد از نتیجه

فقط خروجی **غیرمحرمانهٔ** وضعیت و شمارنده‌های استفاده را در Issue پروژه ثبت کنید. کلیدها، درخواست‌های خصوصی، دادهٔ کاربر یا فایل‌های محلی را پیوست نکنید.

Issue برنامهٔ توسعه: https://github.com/ebrahimism/CSEF-Execution-Agent/issues/1
