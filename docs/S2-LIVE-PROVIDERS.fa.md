# S2 — دو API مستقل، خروجی ساختاریافته و حسابرسی مصرف

**وضعیت: کد و آزمون آفلاین اجرا می‌شوند؛ بررسی واقعی سرویس‌ها مستلزم کلیدهای خصوصی و اجرای اختیاری روی سیستم صاحب پروژه است.** green CI یعنی قراردادهای داخلی موفق‌اند، نه اینکه APIهای واقعی در حساب شما فعال‌اند.

## مسیر اصلی / no new core

- \`OpenAI Responses\` به نشانی \`api.openai.com/v1/responses\` با \`text.format.type=json_schema\` و \`strict=true\`.
- \`Anthropic Messages\` به نشانی \`api.anthropic.com/v1/messages\` با \`output_config.format.type=json_schema\`.
- از قراردادهای \`StructuredClient.call\`، \`CodingAgent.propose\`، \`ProjectBook\` و SQLite موجود استفاده شده است؛ Codex همچنان اختیاری است.
- هر دو پاسخ از JSON و schema اصلی پروژه در کنترل‌کننده دوباره اعتبارسنجی می‌شوند. به دلیل محدودیت subsetهای رسمی، قیود \`minLength\` / \`maxItems\` / \`pattern\` فقط در validator محلی اجرا می‌شوند، نه اینکه به دروغ native-supported خوانده شوند.
- کلیدهای API در environment هستند، نه مخزن، خروجی مدل یا رسید. \`store=false\` برای Responses تنظیم شده و هیچ fallback/redirect/retry خودکاری نیست.

## ۱ — تنظیم خصوصی کلیدها

**Windows PowerShell** در ترمینال شخصی (نه در چت/گیت/CI عمومی):

\`\`\`powershell
$env:OPENAI_API_KEY = Read-Host "OpenAI API key"
$env:ANTHROPIC_API_KEY = Read-Host "Anthropic API key"
\`\`\`

**Ubuntu/Linux**: کلیدها را فقط در محیط خصوصی فرایند قرار دهید؛ هیچ‌وقت در commit، دستورهایی که در تاریخچهٔ shell می‌مانند یا فایل عمومی ذخیره نکنید.

## ۲ — آزمون زندهٔ واقعی، فقط با اجازهٔ صاحب حساب

دو شناسهٔ مدلِ واقعاً فعال در حساب خود را جایگزین کنید؛ هیچ مدلی به صورت خودکار انتخاب یا جایگزین نمی‌شود. هر اجرای موفق، دقیقاً یک فراخوانیِ قابل صورت‌حساب به هر ارائه‌دهنده دارد.

\`\`\`powershell
python -m csef_gate.providers.smoke --openai-model YOUR_OPENAI_MODEL --anthropic-model YOUR_ANTHROPIC_MODEL --receipt "$env:USERPROFILE\\csef-s2-live-evidence.json"
\`\`\`

برای محیط Linux، \`--receipt /home/USER/csef-s2-live-evidence.json\` را در مسیر خصوصی خود قرار دهید.

خروجی هر ارائه‌دهنده شامل \`requested_model\`، \`reported_model\`، \`format_contract\`، نتیجهٔ JSON/schema، \`usage\`، تأخیر و \`cost_usd: null\` است. اگر یکی از دو سرویس شکست بخورد، نتیجهٔ ترکیبی **PASS نخواهد شد** و رسید (در صورت انتخاب مسیر) با وضعیت \`INCOMPLETE\` ثبت می‌شود. مسیر رسید باید تازه باشد؛ فایل پیشین بازنویسی نمی‌شود.

این دستور در CI اجرا نمی‌شود؛ نه API رایگان فرض می‌شود و نه دسترسی واقعی ادعا می‌شود.

## ۳ — حد تعداد درخواست با دوام (نه سقف تضمینی دلار)

برای پروژه‌هایی که \`control.sqlite3\` فعلی دارند، به‌صورت اختیاری:

\`\`\`powershell
$env:CSEF_PROVIDER_MAX_CALLS = "10"
\`\`\`

پیش از ارسال به API، یک intent در جدول **موجود** \`changes\` در SQLite ثبت می‌شود؛ تراکنش مانع رزرو هم‌زمان بیشتر از حد می‌شود. نتیجهٔ نامعلوم نیز سهمیه مصرف می‌کند و بی‌اجازه تکرار نمی‌شود. اگر سقف درخواست تعیین شده ولی کنترل‌استور واحد موجود نباشد، ارسال ممنوع می‌شود. این محدودیت **تعداد فراخوانی‌ها** است و به معنی محدودیت قطعی صورت‌حساب دلاری نیست؛ سقف واقعی پولی را در کنسول ارائه‌دهنده جداگانه تنظیم کنید.

برای دیدن مصرف پروژه:

\`\`\`powershell
python -m csef_gate.providers.usage --control .\\factory-book
\`\`\`

## ۴ — تخمین هزینه فقط با نرخ تأییدشدهٔ کاربر

تخمین قیمت خودکار از توکن بدون نرخ قیمت همان مدل قابل اتکا نیست. اگر مایلید، یک فایل **خصوصی نسخه‌دار** بسازید:

\`\`\`json
{
  "version": 1,
  "models": [
    {
      "provider": "openai",
      "model": "EXACT_MODEL_ID",
      "input": "YOUR_INPUT_PRICE_PER_MILLION",
      "output": "YOUR_OUTPUT_PRICE_PER_MILLION",
      "cached_input": "YOUR_CACHED_PRICE_PER_MILLION",
      "cache_write": "0"
    }
  ]
}
\`\`\`

همهٔ مقادیر قیمت باید رشتهٔ عدد اعشاریِ درست باشند، برای مثال \`"0.50"\`. ارقام بالا placeholder هستند؛ نرخ واقعی و شرایط cache و نوع حساب را از ارائه‌دهنده بررسی کنید. برای هر مدل Anthropic هم مقادیر مناسب را جداگانه وارد کنید. سپس:

\`\`\`powershell
$env:CSEF_PROVIDER_PRICES_FILE = "C:\\private\\provider-pricing.json"
\`\`\`

در صورت نبود نرخ دقیق یا usage، هزینه \`null\` باقی می‌ماند. \`cost_estimate_usd\` تخمین حاصل از **نرخِ ارائه‌شدهٔ مالک** است، نه هزینهٔ قطعی فاکتور. هزینهٔ cache، نوع پردازش و ویژگی‌های غیرمتنی ممکن است نیازمند نرخ‌های دیگری باشند؛ این MVP فقط درخواست متنی فعلی را پوشش می‌دهد.

## شواهد و باقی‌ماندهٔ S2

کد: \`src/csef_gate/providers/direct.py\`، \`providers/usage.py\`، \`providers/smoke.py\`. تست‌ها: \`tests/providers/test_s2_controls.py\`.

- پروتکل دو API، قالب native، خطاهای schema/timeout، عدم تکرار و شمارندهٔ SQLite: قابل آزمون آفلاین.
- LIVE: اتصال واقعی OpenAI و Anthropic به حساب کاربر، دسترسی شناسه‌های مدل و تأیید تراکنش: **تأیید نشده تا اجرای opt-in.**
- مدیریت بودجه: سقف شمارش پایدار و تخمین نرخِ دستی وجود دارد؛ **سقف دلاریِ تضمین‌شده، circuit breaker سراسری، reconciliation کامل و failover سیاست‌محور** هنوز انجام نشده‌اند.
- AvalAI / OpenAI-compatible و Ollama در این برش فعال نشده‌اند، چون در هدف فعلیِ «دو API مستقیم مستقل» ضروری نیستند؛ توسعهٔ آینده فقط پشت آداپتر نسخه‌دار و با درخواست صریح انجام می‌شود.
