import sys
import traceback
import os
import shutil


# تحديد مسار حفظ ملف الأخطاء في مجلد التطبيق
user_docs = os.path.expanduser('~')
LOG_FILE = os.path.join(user_docs, "app_errors.log")

def handle_exception(exc_type, exc_value, exc_traceback):
    # تجاهل إغلاق التطبيق الطبيعي
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # كتابة تفاصيل الخطأ داخل الملف النصي
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n" + "="*40 + "\n")
        traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)

# تحويل أي خطأ غير متوقع ليتم تسجيله في الملف تلقائياً
sys.excepthook = handle_exception


import flet as ft
import json
import urllib.request
import subprocess
import hashlib
from datetime import datetime, timedelta, date

try:
    from fpdf import FPDF
    import arabic_reshaper
    from bidi.algorithm import get_display
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# 🖋️ حط ملف خط عربي (مثل Amiri-Regular.ttf) بجانب البرنامج وحط اسمه هنا بالضبط

ARABIC_FONT_PATH = r"C:\PyMahmoud\Amiri-Regular.ttf"


def ar(text) -> str:
    """يهيئ النص العربي للعرض الصحيح داخل PDF (تشكيل الحروف + اتجاه الكتابة الصحيح)"""
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)

DATA_FILE     = "expenses.json"
DEBTS_FILE    = "debts.json"
SETTINGS_FILE = "settings.json"

FREE_CATEGORIES = [
    "🍔 طعام", "🚗 مواصلات", "🏠 سكن",
    "👕 ملابس", "📦 أخرى",
]
PREMIUM_CATEGORIES = [
    "💊 صحة", "🎮 ترفيه", "📚 تعليم", "💼 عمل",
]
CATEGORIES = FREE_CATEGORIES + PREMIUM_CATEGORIES
LOCKED_CATEGORY_LABEL = "🔒 فئات إضافية (ترقية)"

CURRENCIES = {"ر.س (ريال سعودي)": "ر.س", "ر.ي (ريال يمني)": "ر.ي"}

CURRENT_VERSION = "1.1.0"
VERSION_URL = "https://raw.githubusercontent.com/AbuAlhosam/mahfadati-updates./main/version.txt"
APK_URL     = "https://raw.githubusercontent.com/AbuAlhosam/mahfadati-updates./main/mahfadati.apk"

APP_NAME    = "محفظتي"
APP_OWNER   = "محمود"
APP_CONTACT = "779476749"

# ============================================================
#  نظام التجربة المجانية والاشتراك المدفوع
# ============================================================
LICENSE_FILE = "license.json"
TRIAL_DAYS   = 30

# رقم واتساب بصيغة دولية (يمن = 967)
WHATSAPP_NUMBER = "967" + APP_CONTACT

# --- كلمة سر التوليد: غيّرها لشيء خاص بك ولا تشاركها أحداً ---
LICENSE_SECRET = "MAHFADATI-2026-CHANGE-ME"


def generate_license_key(phone: str) -> str:
    """يولّد كود تفعيل فريد من رقم الجوال + السر الخاص."""
    raw = (phone.strip() + LICENSE_SECRET).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:10].upper()


def verify_license_key(phone: str, entered_key: str) -> bool:
    return generate_license_key(phone) == entered_key.strip().upper()


def _default_license():
    today_str = date.today().isoformat()
    return {
        "first_launch": today_str,
        "last_known_date": today_str,
        "activated": False,
        "phone": "",
    }


def load_license() -> dict:
    if os.path.exists(LICENSE_FILE):
        try:
            with open(LICENSE_FILE, "r", encoding="utf-8") as f:
                lic = json.load(f)
            if "first_launch" in lic and "last_known_date" in lic:
                return lic
        except Exception:
            pass
    lic = _default_license()
    save_license(lic)
    return lic


def save_license(lic: dict):
    with open(LICENSE_FILE, "w", encoding="utf-8") as f:
        json.dump(lic, f, ensure_ascii=False, indent=2)


def load_app_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"default_currency_enabled": False, "default_currency": "ر.س"}


def save_app_settings(settings: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def _fetch_real_date():
    """يجيب التاريخ الحقيقي من الإنترنت لمنع التلاعب بساعة الجهاز. يرجع None لو ما فيه نت."""
    try:
        with urllib.request.urlopen(
            "https://worldtimeapi.org/api/timezone/Etc/UTC", timeout=4
        ) as r:
            data = json.loads(r.read().decode())
        return date.fromisoformat(data["datetime"][:10])
    except Exception:
        return None


def get_safe_today(lic: dict) -> date:
    """
    يحدد التاريخ 'الآمن' لحساب أيام التجربة:
    - يحاول يجيب تاريخ حقيقي من الإنترنت.
    - يقارنه بآخر تاريخ محفوظ، ويأخذ الأحدث (يمنع الرجوع للخلف بالتاريخ).
    - يحدّث آخر تاريخ معروف ويحفظه.
    """
    system_today = date.today()
    last_known = date.fromisoformat(lic.get("last_known_date", system_today.isoformat()))

    real_today = _fetch_real_date()
    candidates = [d for d in (system_today, last_known, real_today) if d is not None]
    safe_today = max(candidates)

    if safe_today.isoformat() != lic.get("last_known_date"):
        lic["last_known_date"] = safe_today.isoformat()
        save_license(lic)

    return safe_today


def is_activated(lic: dict) -> bool:
    return bool(lic.get("activated", False))


def is_trial_active(lic: dict, today: date) -> bool:
    if is_activated(lic):
        return True
    try:
        first_launch = date.fromisoformat(lic.get("first_launch", today.isoformat()))
    except Exception:
        first_launch = today
    return (today - first_launch).days <= TRIAL_DAYS


def trial_days_left(lic: dict, today: date) -> int:
    try:
        first_launch = date.fromisoformat(lic.get("first_launch", today.isoformat()))
    except Exception:
        first_launch = today
    remaining = TRIAL_DAYS - (today - first_launch).days
    return max(0, remaining)
# ============================================================


def check_for_updates(page, update_overlay):
    try:
        with urllib.request.urlopen(VERSION_URL, timeout=5) as r:
            latest = r.read().decode().strip()
        if latest > CURRENT_VERSION:
            update_overlay.visible = True
            page.update()
    except:
        pass

#def trigger_update(page):
#    try:
#        page.snack_bar = ft.SnackBar(ft.Text("جاري تحميل التحديث..."))
#        page.snack_bar.open = True
 #       page.update()
 #       new_exe = "mahfadati_new.exe"
 #       urllib.request.urlretrieve(EXE_URL, new_exe)
 #       current_exe = os.path.basename(sys.argv[0])
 #       bat = f"@echo off\ntimeout /t 1 /nobreak > nul\ndel \"{current_exe}\"\nren \"{new_exe}\" \"{current_exe}\"\nstart \"\" \"{current_exe}\"\ndel \"%~f0\"\n"
 #       with open("updater.bat", "w") as f:
 #           f.write(bat)
 #       subprocess.Popen(["updater.bat"], shell=True)
 #       sys.exit()
 #   except Exception as e:
 #       page.snack_bar = ft.SnackBar(ft.Text(f"فشل التحديث: {e}"))
 #       page.snack_bar.open = True
#        page.update()
#لغيت الدالة فوق الخاصة بالتنفيذي ووضعت الدالة هذه اللي تحت لتحويله ل برنامج يشتغل علىالجوال
def trigger_update(page):
    # 📱 الجوال: نفتح رابط تحميل APK بالمتصفح مباشرة (توزيع يدوي بدون متجر)
    try:
        page.launch_url(APK_URL)
        page.snack_bar = ft.SnackBar(ft.Text("راح يفتح المتصفح لتحميل النسخة الجديدة، ثبتها يدوياً بعد التحميل"))
        page.snack_bar.open = True
        page.update()
    except Exception as e:
        page.snack_bar = ft.SnackBar(ft.Text(f"فشل فتح رابط التحديث: {e}"))
        page.snack_bar.open = True
        page.update()


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_debts():
    if os.path.exists(DEBTS_FILE):
        with open(DEBTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_debts(debts):
    with open(DEBTS_FILE, "w", encoding="utf-8") as f:
        json.dump(debts, f, ensure_ascii=False, indent=2)


def new_pdf():
    """ينشئ صفحة PDF جديدة مع الخط العربي إن وُجد"""
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(ARABIC_FONT_PATH):
        pdf.add_font("Arabic", "", ARABIC_FONT_PATH)
        pdf.set_font("Arabic", size=12)
    else:
        pdf.set_font("Helvetica", size=12)  # احتياط: بدون خط عربي، النص العربي ما راح يظهر صح
    return pdf


def pdf_title(pdf, text, size=16):
    pdf.set_font_size(size)
    pdf.cell(0, 12, ar(text), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font_size(12)


def pdf_line(pdf, text, size=12):
    pdf.set_font_size(size)
    pdf.multi_cell(0, 8, ar(text), align="R")
    pdf.set_font_size(12)


def pdf_table_row(pdf, cells_rtl, widths_rtl, fill=None):
    """cells_rtl و widths_rtl بترتيب القراءة من اليمين لليسار (أول عنصر = أقصى اليمين)"""
    pdf.set_font_size(9)
    cells = list(reversed(cells_rtl))
    widths = list(reversed(widths_rtl))
    if fill:
        pdf.set_fill_color(*fill)
    for cell, w in zip(cells, widths):
        pdf.cell(w, 8, ar(cell), border=1, align="C", fill=bool(fill))
    pdf.ln(8)
    pdf.set_font_size(12)

def export_text(data, debts, currency):
    lines = [f"=== تقرير محفظتي - {datetime.now().strftime('%Y-%m-%d')} ===\n"]
    lines.append(f"العملة: {currency}\n")
    filtered = [e for e in data if e.get("currency") == currency]
    total_in  = sum(e["amount"] for e in filtered if e.get("type") == "دخل")
    total_out = sum(e["amount"] for e in filtered if e.get("type") != "دخل")
    lines.append(f"إجمالي الدخل:    {total_in:.0f} {currency}")
    lines.append(f"إجمالي المصروف:  {total_out:.0f} {currency}")
    lines.append(f"الرصيد:          {total_in - total_out:.0f} {currency}\n")
    lines.append("--- المعاملات ---")
    for e in reversed(filtered):
        sign = "+" if e.get("type") == "دخل" else "-"
        lines.append(f"{e.get('date','')}  {sign}{e['amount']} {currency}  {e.get('category','')}  {e.get('desc','')}")
    lines.append("\n--- الديون ---")
    for d in debts:
        if d.get("currency") == currency:
            kind  = "دين عليك" if d.get("kind") == "عليك" else "دين لك"
            state = "✅ مسدد" if d.get("paid") else "⏳ غير مسدد"
            lines.append(f"{d.get('date','')}  {kind}  {d.get('name','')}  {d['amount']} {currency}  {state}")
    report = "\n".join(lines)
    fname = f"تقرير_محفظتي_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(report)
    return fname

def main(page: ft.Page):
    page.title = "إعدادات النظام"
    
    # عداد الضغطات السرية
    click_count = 0
    
    # مسار قاعدة البيانات الحالية ومسار النسخة الاحتياطية المخصصة للتصدير
    DB_NAME = "database.db"  # اسم قاعدة بياناتك الحالية
    BACKUP_NAME = "POS_Backup_Database.db"

    # ويدجت لوحة الصيانة (تكون مخفية في البداية)
    maintenance_panel = ft.Column(visible=False)

    # 1. دالة تصدير قاعدة البيانات لإرسالها للمطور
    def export_db(e):
        try:    
            if os.path.exists(DB_NAME):
                shutil.copy(DB_NAME, BACKUP_NAME)
                page.snack_bar = ft.SnackBar(ft.Text("تم تصدير قاعدة البيانات بنجاح"), open=True)
            else:
                page.snack_bar = ft.SnackBar(ft.Text("قاعدة البيانات غير موجودة حالياً"), open=True)
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"فشل التصدير: {ex}"), open=True)
            page.update()       
                          


    # 2. دالة الصيانة السريعة (إعادة بناء الجداول الناقصة أو المحدثة دون حذف البيانات)
    def repair_db(e):
        try:
            import sqlite3
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            # هنا تضع أوامر إنشاء الجداول التي تستخدمها دائماً لضمان عدم نقصها
            # مثال:
            cursor.execute("CREATE TABLE IF NOT EXISTS SettingsTable (CategoryName TEXT, DefaultMinStock INTEGER, ProfitMargin REAL)")
            
            conn.commit()
            conn.close()
            page.snack_bar = ft.SnackBar(ft.Text("تمت عملية فحص وإصلاح الجداول بنجاح دون المساس ببياناتك!"))
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"فشل الإصلاح: {str(ex)}"))
        page.snack_bar.open = True
        page.update()

    # 3. دالة إظهار اللوحة السرية عند الضغط 5 مرات
    def secret_trigger(e):
        nonlocal click_count
        click_count += 1
        if click_count >= 5:
            maintenance_panel.visible = True
            page.snack_bar = ft.SnackBar(ft.Text("تم تفعيل وضع المطور وأدوات الصيانة!"))
            page.snack_bar.open = True
            page.update()

    # بناء أزرار لوحة الصيانة
    maintenance_panel.controls = [
        ft.Text("أدوات الصيانة والدعم الفني:", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_700),
        ft.ElevatedButton("إصلاح وفحص قاعدة البيانات", icon=ft.Icons.BUILD, on_click=repair_db),
        ft.ElevatedButton("تصدير نسخة من البيانات لإرسالها للمطور", icon=ft.Icons.SHARE, on_click=export_db),
    ]

    # الواجهة الظاهرة للمستخدم
    page.add(
        ft.Column([
            # نص عادي جداً، لكن عند الضغط عليه 5 مرات يفتح اللوحة السرية
            ft.GestureDetector(
                content=ft.Text("إصدار التطبيق v1.0.0 (حقوق الطبع محفوظة)", color=ft.Colors.GREY_500),
                on_tap=secret_trigger
            ),
            ft.Divider(),
            maintenance_panel # اللوحة المخفية التي ستظهر عند الحاجة
        ])
    )



    
    
    page.title = "محفظتي"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0F1923"
    page.padding = 16
    page.scroll  = ft.ScrollMode.AUTO

    data   = load_data()
    debts  = load_debts()
    app_settings = load_app_settings()
    current_currency = [app_settings.get("default_currency", "ر.س")
                        if app_settings.get("default_currency_enabled") else "ر.س"]
    editing_item  = [None]
    editing_debt  = [None]
    pending_action = [None]

    # ── حالة الترخيص/التجربة ──
    license_data = load_license()
    today_safe   = get_safe_today(license_data)
    premium_ok   = [is_activated(license_data)]
    trial_ok     = [is_trial_active(license_data, today_safe)]
    days_left    = [trial_days_left(license_data, today_safe)]
    upgrade_target = ["premium"]  # يحدد نوع النافذة: premium أو activation

    def has_full_categories():
        return premium_ok[0]

    def has_trial_features():
        return premium_ok[0] or trial_ok[0]

    # ── حقول الإدخال ──
    amount_field = ft.TextField(
        label="المبلغ", keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1A2635", color="#EAEAEA",
        label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896", expand=True,
    )
    desc_field = ft.TextField(
        label="وصف (اختياري)", bgcolor="#1A2635", color="#EAEAEA",
        label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896", expand=True,
    )
    type_dropdown = ft.Dropdown(
        label="النوع", value="مصروف",
        options=[ft.dropdown.Option("مصروف"), ft.dropdown.Option("دخل")],
        bgcolor="#1A2635", color="#EAEAEA",
        label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896", width=130,
    )
    def build_category_options():
        cats = list(FREE_CATEGORIES)
        if has_full_categories():
            cats += PREMIUM_CATEGORIES
        else:
            cats.append(LOCKED_CATEGORY_LABEL)
        return [ft.dropdown.Option(c) for c in cats]

    def on_cat_change(_):
        if cat_dropdown.value == LOCKED_CATEGORY_LABEL:
            cat_dropdown.value = "📦 أخرى"
            show_upgrade("فئات إضافية")
        # الحقل ما يظهر إلا للمشترك، وإلا يبقى مخفي تماماً بدون أي مربع مقفول فوقه
        custom_cat_field.visible = (cat_dropdown.value == "📦 أخرى" and has_trial_features())
        if not custom_cat_field.visible:
            custom_cat_field.value = ""
        page.update()

    cat_dropdown = ft.Dropdown(
        label="الفئة", value="📦 أخرى",
        options=build_category_options(),
        on_select=on_cat_change,
        bgcolor="#1A2635", color="#EAEAEA",
        label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896", expand=True,
    )

    custom_cat_field = ft.TextField(
        label="✏️ اسم مخصص (اختياري)",
        bgcolor="#1A2635", color="#EAEAEA",
        label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896", expand=True,
        visible=has_trial_features(),
    )
    add_btn_text = ft.Text("✅ إضافة", color="#0F1923", weight=ft.FontWeight.BOLD)
    add_btn = ft.ElevatedButton(
        content=add_btn_text, on_click=None,
        bgcolor="#00C896",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        width=400, height=48,
    )

    # حقول الديون
    debt_name_field = ft.TextField(
        label="اسم الشخص", bgcolor="#1A2635", color="#EAEAEA",
        label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896", expand=True,
    )
    debt_amount_field = ft.TextField(
        label="المبلغ", keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#1A2635", color="#EAEAEA",
        label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896", expand=True,
    )
    debt_kind_dropdown = ft.Dropdown(
        label="النوع", value="عليك",
        options=[ft.dropdown.Option("عليك"), ft.dropdown.Option("لك")],
        bgcolor="#1A2635", color="#EAEAEA",
        label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896", width=130,
    )
    debt_btn_text = ft.Text("✅ إضافة دين", color="#0F1923", weight=ft.FontWeight.BOLD)
    debt_btn = ft.ElevatedButton(
        content=debt_btn_text, on_click=None,
        bgcolor="#00C896",
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
        width=400, height=48,
    )

    # أزرار العملة
    sar_btn = ft.ElevatedButton(
        content=ft.Text("ر.س سعودي", color="#0F1923", weight=ft.FontWeight.BOLD, size=13),
        bgcolor="#00C896", height=40, expand=True,
    )
    yer_btn = ft.ElevatedButton(
        content=ft.Text("ر.ي يمني", color="#EAEAEA", size=13),
        bgcolor="#243447", height=40, expand=True,
    )

    def switch_to_sar(_):
        current_currency[0] = "ر.س"
        sar_btn.bgcolor = "#00C896"; sar_btn.content.color = "#0F1923"
        yer_btn.bgcolor = "#243447"; yer_btn.content.color = "#EAEAEA"
        refresh_ui()

    def switch_to_yer(_):
        current_currency[0] = "ر.ي"
        yer_btn.bgcolor = "#00C896"; yer_btn.content.color = "#0F1923"
        sar_btn.bgcolor = "#243447"; sar_btn.content.color = "#EAEAEA"
        refresh_ui()

    sar_btn.on_click = switch_to_sar
    yer_btn.on_click = switch_to_yer

    # يهيّئ لون الزر المطابق للعملة المحفوظة عند فتح التطبيق
    if current_currency[0] == "ر.ي":
        yer_btn.bgcolor = "#00C896"; yer_btn.content.color = "#0F1923"
        sar_btn.bgcolor = "#243447"; sar_btn.content.color = "#EAEAEA"

    def toggle_default_currency(e):
        app_settings["default_currency_enabled"] = e.control.value
        save_app_settings(app_settings)
        default_currency_dropdown.visible = e.control.value
        page.update()

    def change_default_currency(e):
        app_settings["default_currency"] = e.control.value
        save_app_settings(app_settings)
        if e.control.value == "ر.ي":
            switch_to_yer(None)
        else:
            switch_to_sar(None)
        page.update()

    default_currency_switch = ft.Switch(
        label="تفعيل عملة افتراضية عند فتح التطبيق",
        value=app_settings.get("default_currency_enabled", False),
        active_color="#00C896",
        on_change=toggle_default_currency,
    )
    default_currency_dropdown = ft.Dropdown(
        label="العملة الافتراضية", value=app_settings.get("default_currency", "ر.س"),
        options=[ft.dropdown.Option("ر.س"), ft.dropdown.Option("ر.ي")],
        bgcolor="#1A2635", color="#EAEAEA",
        label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896",
        visible=app_settings.get("default_currency_enabled", False),
        on_select=change_default_currency,
    )

    balance_text = ft.Text("0", size=16, weight=ft.FontWeight.BOLD, color="#00C896")
    income_text  = ft.Text("0", size=14, weight=ft.FontWeight.BOLD, color="#00C896")
    expense_text = ft.Text("0", size=14, weight=ft.FontWeight.BOLD, color="#FF4D6D")

    def summary_card(title, value_text, icon):
        return ft.Container(
            expand=True, padding=10, border_radius=12, bgcolor="#1A2635",
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4,
                controls=[ft.Text(icon, size=20), ft.Text(title, size=11, color="#7A8FA6"), value_text],
            ),
        )

    summary_row = ft.Row(spacing=8, controls=[
        summary_card("الرصيد",  balance_text, "💵"),
        summary_card("الدخل",   income_text,  "📥"),
        summary_card("المصروف", expense_text, "📤"),
    ])

    list_column  = ft.Column(spacing=6)
    chart_column = ft.Column(spacing=8)
    debts_column = ft.Column(spacing=6)

    # ── Overlay: تأكيد الحذف ──
    confirm_msg = ft.Text("", color="#7A8FA6", size=13, text_align=ft.TextAlign.CENTER)
    confirm_overlay = ft.Container(
        visible=False, bgcolor="#000000CC", expand=True,
        alignment=ft.Alignment(0, 0), top=0, left=0, right=0, bottom=0,
        content=ft.Container(
            width=300, padding=20, border_radius=12, bgcolor="#1A2635",
            content=ft.Column(tight=True, spacing=16,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("⚠️ تأكيد الحذف", size=16, weight=ft.FontWeight.BOLD, color="#FF4D6D"),
                    confirm_msg,
                    ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=12, controls=[
                        ft.TextButton(content=ft.Text("إلغاء", color="#7A8FA6"),
                                      on_click=lambda _: close_confirm()),
                        ft.ElevatedButton(
                            content=ft.Text("نعم، احذف", color="white", weight=ft.FontWeight.BOLD),
                            bgcolor="#FF4D6D", on_click=lambda _: execute_action()),
                    ]),
                ],
            ),
        ),
    )

    def show_confirm(msg, action):
        pending_action[0] = action
        confirm_msg.value = msg
        confirm_overlay.visible = True
        page.update()

    def close_confirm():
        confirm_overlay.visible = False
        pending_action[0] = None
        page.update()

    def execute_action():
        confirm_overlay.visible = False
        if pending_action[0]:
            pending_action[0]()
            pending_action[0] = None
        page.update()

    # ── Overlay: تعديل معاملة ──
    edit_amount = ft.TextField(label="المبلغ", keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#0F1923", color="#EAEAEA", label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896")
    edit_desc = ft.TextField(label="الوصف", bgcolor="#0F1923", color="#EAEAEA",
        label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896")
    edit_type = ft.Dropdown(label="النوع", value="مصروف",
        options=[ft.dropdown.Option("مصروف"), ft.dropdown.Option("دخل")],
        bgcolor="#0F1923", color="#EAEAEA", label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896")
    def on_edit_cat_change(_):
        if edit_cat.value == LOCKED_CATEGORY_LABEL:
            edit_cat.value = "📦 أخرى"
            show_upgrade("فئات إضافية")
        # الحقل ما يظهر إلا للمشترك، وإلا يبقى مخفي تماماً بدون أي مربع مقفول فوقه
        edit_custom_cat_field.visible = (edit_cat.value == "📦 أخرى" and has_trial_features())
        if not edit_custom_cat_field.visible:
            edit_custom_cat_field.value = ""
        page.update()

    edit_cat = ft.Dropdown(label="الفئة", value="📦 أخرى",
        options=build_category_options(), on_select=on_edit_cat_change,
        bgcolor="#0F1923", color="#EAEAEA", label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896")

    edit_custom_cat_field = ft.TextField(
        label="✏️ اسم مخصص (اختياري)",
        bgcolor="#0F1923", color="#EAEAEA", label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896",
        visible=has_trial_features(),
    )

    edit_overlay = ft.Container(
        visible=False, bgcolor="#000000CC", expand=True,
        alignment=ft.Alignment(0, 0), top=0, left=0, right=0, bottom=0,
        content=ft.Container(
            width=320, padding=20, border_radius=12, bgcolor="#1A2635",
            content=ft.Column(tight=True, spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("✏️ تعديل المعاملة", size=16, weight=ft.FontWeight.BOLD, color="#00C896"),
                    edit_amount, edit_type, edit_cat, edit_custom_cat_field, edit_desc,
                    ft.Row(spacing=8, controls=[
                        ft.TextButton(content=ft.Text("إلغاء", color="#7A8FA6"),
                                      on_click=lambda _: close_edit()),
                        ft.ElevatedButton(
                            content=ft.Text("حفظ", color="#0F1923", weight=ft.FontWeight.BOLD),
                            bgcolor="#00C896", on_click=lambda _: save_edit()),
                    ]),
                ],
            ),
        ),
    )

    def open_edit(item):
        editing_item[0] = item
        edit_amount.value = str(item["amount"])
        edit_desc.value   = item.get("desc", "")
        edit_type.value   = item.get("type", "مصروف")
        cat_value = item.get("category", "📦 أخرى")
        if cat_value.startswith("🏷️ "):
            edit_cat.value = "📦 أخرى"
            edit_custom_cat_field.value = cat_value[len("🏷️ "):]
            edit_custom_cat_field.visible = has_trial_features()
        else:
            edit_cat.value = cat_value
            edit_custom_cat_field.value = ""
            edit_custom_cat_field.visible = (cat_value == "📦 أخرى" and has_trial_features())
        edit_overlay.visible = True
        page.update()

    def close_edit():
        edit_overlay.visible = False
        editing_item[0] = None
        page.update()

    def save_edit():
        item = editing_item[0]
        if not item:
            return
        try:
            final_category = edit_cat.value
            if (edit_cat.value == "📦 أخرى" and has_trial_features()
                    and edit_custom_cat_field.value and edit_custom_cat_field.value.strip()):
                final_category = f"🏷️ {edit_custom_cat_field.value.strip()}"
            item["amount"]   = float(edit_amount.value)
            item["desc"]     = edit_desc.value.strip()
            item["type"]     = edit_type.value
            item["category"] = final_category
            save_data(data)
            close_edit()
            refresh_ui()
        except:
            pass

    # ── Overlay: تعديل دين ──
    edit_debt_name   = ft.TextField(label="اسم الشخص", bgcolor="#0F1923", color="#EAEAEA",
        label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896")
    edit_debt_amount = ft.TextField(label="المبلغ", keyboard_type=ft.KeyboardType.NUMBER,
        bgcolor="#0F1923", color="#EAEAEA", label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896")
    edit_debt_kind   = ft.Dropdown(label="النوع", value="عليك",
        options=[ft.dropdown.Option("عليك"), ft.dropdown.Option("لك")],
        bgcolor="#0F1923", color="#EAEAEA", label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896")
    edit_debt_paid   = ft.Dropdown(label="الحالة", value="غير مسدد",
        options=[ft.dropdown.Option("غير مسدد"), ft.dropdown.Option("مسدد")],
        bgcolor="#0F1923", color="#EAEAEA", label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896")

    edit_debt_overlay = ft.Container(
        visible=False, bgcolor="#000000CC", expand=True,
        alignment=ft.Alignment(0, 0), top=0, left=0, right=0, bottom=0,
        content=ft.Container(
            width=320, padding=20, border_radius=12, bgcolor="#1A2635",
            content=ft.Column(tight=True, spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("✏️ تعديل الدين", size=16, weight=ft.FontWeight.BOLD, color="#00C896"),
                    edit_debt_name, edit_debt_amount, edit_debt_kind, edit_debt_paid,
                    ft.Row(spacing=8, controls=[
                        ft.TextButton(content=ft.Text("إلغاء", color="#7A8FA6"),
                                      on_click=lambda _: close_debt_edit()),
                        ft.ElevatedButton(
                            content=ft.Text("حفظ", color="#0F1923", weight=ft.FontWeight.BOLD),
                            bgcolor="#00C896", on_click=lambda _: save_debt_edit()),
                    ]),
                ],
            ),
        ),
    )

    def open_debt_edit(debt):
        editing_debt[0] = debt
        edit_debt_name.value   = debt.get("name", "")
        edit_debt_amount.value = str(debt["amount"])
        edit_debt_kind.value   = debt.get("kind", "عليك")
        edit_debt_paid.value   = "مسدد" if debt.get("paid") else "غير مسدد"
        edit_debt_overlay.visible = True
        page.update()

    def close_debt_edit():
        edit_debt_overlay.visible = False
        editing_debt[0] = None
        page.update()

    def save_debt_edit():
        debt = editing_debt[0]
        if not debt:
            return
        try:
            debt["name"]   = edit_debt_name.value.strip()
            debt["amount"] = float(edit_debt_amount.value)
            debt["kind"]   = edit_debt_kind.value
            debt["paid"]   = edit_debt_paid.value == "مسدد"
            save_debts(debts)
            close_debt_edit()
            refresh_ui()
        except:
            pass

    # ── Overlay: حول البرنامج ──
    about_overlay = ft.Container(
        visible=False, bgcolor="#000000CC", expand=True,
        alignment=ft.Alignment(0, 0), top=0, left=0, right=0, bottom=0,
        content=ft.Container(
            width=300, padding=20, border_radius=12, bgcolor="#1A2635",
            content=ft.Column(tight=True, spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("💼", size=36),
                    ft.Text(APP_NAME, size=20, weight=ft.FontWeight.BOLD, color="#00C896"),
                    ft.Text(f"الإصدار {CURRENT_VERSION}", size=12, color="#7A8FA6"),
                    ft.Divider(color="#243447"),
                    ft.Text(f"تطوير: {APP_OWNER}", size=13, color="#EAEAEA"),
                    ft.Text(f"للتواصل: {APP_CONTACT}", size=13, color="#EAEAEA"),
                    ft.Container(height=6),
                    ft.ElevatedButton(
                        content=ft.Text("إغلاق", color="#0F1923", weight=ft.FontWeight.BOLD),
                        bgcolor="#00C896", on_click=lambda _: close_about()),
                ],
            ),
        ),
    )

    def show_about(_):
        about_overlay.visible = True
        page.update()

    def close_about():
        about_overlay.visible = False
        page.update()

    # ── Overlay: الترقية للنسخة المدفوعة ──
    upgrade_title = ft.Text("🔒", size=16, weight=ft.FontWeight.BOLD, color="#F6AD55")
    upgrade_body  = ft.Text("", color="#7A8FA6", size=13, text_align=ft.TextAlign.CENTER)

    activate_phone_field = ft.TextField(
        label="رقم جوالك", bgcolor="#0F1923", color="#EAEAEA",
        label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896", visible=False,
    )
    activate_key_field = ft.TextField(
        label="كود التفعيل", bgcolor="#0F1923", color="#EAEAEA",
        label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896", visible=False,
    )
    activate_msg = ft.Text("", color="#FF4D6D", size=12, visible=False)

    def open_whatsapp(_):
        text = f"مرحباً، أبي أشترك في نسخة {APP_NAME} المدفوعة."
        url = f"https://wa.me/{WHATSAPP_NUMBER}?text={text}"
        page.launch_url(url)

    def show_activation_fields(_):
        activate_phone_field.visible = True
        activate_key_field.visible = True
        activate_msg.visible = False
        page.update()

    def submit_activation(_):
        phone = activate_phone_field.value.strip()
        key   = activate_key_field.value.strip()
        if not phone or not key:
            activate_msg.value = "أدخل رقم الجوال وكود التفعيل"
            activate_msg.visible = True
            page.update(); return
        if verify_license_key(phone, key):
            license_data["activated"] = True
            license_data["phone"] = phone
            save_license(license_data)
            premium_ok[0] = True
            cat_dropdown.options = build_category_options()
            edit_cat.options = build_category_options()
            report_cat_dropdown.options = build_category_options()
            custom_cat_field.visible = (cat_dropdown.value == "📦 أخرى")
            edit_custom_cat_field.visible = (edit_cat.value == "📦 أخرى")
            close_upgrade()
            show_info("✅ تم تفعيل النسخة المدفوعة، استمتع بكل الميزات!")
        else:
            activate_msg.value = "❌ الكود غير صحيح، تأكد من الرقم والكود"
            activate_msg.visible = True
            page.update()

    def show_upgrade(feature_name: str):
        upgrade_body.value = (
            f"ميزة \"{feature_name}\" تحتاج النسخة المدفوعة (اشتراك مدى الحياة).\n"
            f"تواصل معنا عبر واتساب للاشتراك، أو أدخل كود التفعيل إذا كان عندك."
        )
        activate_phone_field.visible = False
        activate_key_field.visible = False
        activate_msg.visible = False
        upgrade_overlay.visible = True
        page.update()

    def close_upgrade():
        upgrade_overlay.visible = False
        page.update()

    upgrade_overlay = ft.Container(
        visible=False, bgcolor="#000000CC", expand=True,
        alignment=ft.Alignment(0, 0), top=0, left=0, right=0, bottom=0,
        content=ft.Container(
            width=320, padding=20, border_radius=12, bgcolor="#1A2635",
            content=ft.Column(tight=True, spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("🔒 ميزة مدفوعة", size=16, weight=ft.FontWeight.BOLD, color="#F6AD55"),
                    upgrade_body,
                    ft.ElevatedButton(
                        content=ft.Text("📱 تواصل عبر واتساب", color="#0F1923", weight=ft.FontWeight.BOLD),
                        bgcolor="#00C896", on_click=open_whatsapp,
                    ),
                    ft.TextButton(
                        content=ft.Text("عندي كود تفعيل بالفعل", color="#7A8FA6", size=12),
                        on_click=show_activation_fields,
                    ),
                    activate_phone_field, activate_key_field, activate_msg,
                    ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=8, controls=[
                        ft.TextButton(content=ft.Text("إغلاق", color="#7A8FA6"),
                                      on_click=lambda _: close_upgrade()),
                        ft.ElevatedButton(
                            content=ft.Text("تفعيل", color="#0F1923", weight=ft.FontWeight.BOLD),
                            bgcolor="#00C896", on_click=submit_activation),
                    ]),
                ],
            ),
        ),
    )

    # ── Overlay: تحديث ──
    update_overlay = ft.Container(
        visible=False, bgcolor="#000000CC", expand=True,
        alignment=ft.Alignment(0, 0), top=0, left=0, right=0, bottom=0,
        content=ft.Container(
            width=300, padding=20, border_radius=12, bgcolor="#1A2635",
            content=ft.Column(tight=True, spacing=12,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("📢 تحديث جديد متاح", size=16, weight=ft.FontWeight.BOLD, color="#00C896"),
                    ft.Text("هل تريد التحديث الآن؟", color="#7A8FA6", size=13),
                    ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=8, controls=[
                        ft.TextButton(content=ft.Text("لاحقاً", color="#7A8FA6"),
                            on_click=lambda _: (setattr(update_overlay, 'visible', False) or page.update())),
                        ft.ElevatedButton(
                            content=ft.Text("تحديث", color="#0F1923", weight=ft.FontWeight.BOLD),
                            bgcolor="#00C896", on_click=lambda _: trigger_update(page)),
                    ]),
                ],
            ),
        ),
    )

    # ── refresh_ui ──
    def refresh_ui():
        cur = current_currency[0]
        total_income  = sum(e["amount"] for e in data if e.get("type") == "دخل" and e.get("currency") == cur)
        total_expense = sum(e["amount"] for e in data if e.get("type") != "دخل" and e.get("currency") == cur)
        balance = total_income - total_expense

        balance_text.value = f"{balance:.0f} {cur}"
        balance_text.color = "#00C896" if balance >= 0 else "#FF4D6D"
        income_text.value  = f"{total_income:.0f} {cur}"
        expense_text.value = f"{total_expense:.0f} {cur}"

        # رسم بياني
        chart_column.controls.clear()
        cat_totals = {}
        for e in data:
            if e.get("currency") == cur and e.get("type") != "دخل":
                cat = e.get("category", "📦 أخرى")
                cat_totals[cat] = cat_totals.get(cat, 0) + e["amount"]

        if not cat_totals:
            chart_column.controls.append(ft.Text("لا توجد بيانات", color="#7A8FA6", size=12))
        else:
            max_val = max(cat_totals.values())
            colors  = ["#00C896","#4FD1C5","#63B3ED","#F6AD55","#FC8181","#B794F4","#F687B3","#68D391","#7A8FA6"]
            for idx, (cat, val) in enumerate(sorted(cat_totals.items(), key=lambda x: -x[1])):
                chart_column.controls.append(ft.Column(spacing=3, controls=[
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                        ft.Text(cat, size=12, color="#EAEAEA"),
                        ft.Text(f"{val:.0f} {cur}", size=12, color="#7A8FA6"),
                    ]),
                    ft.ProgressBar(value=val/max_val if max_val else 0,
                                   color=colors[idx % len(colors)], bgcolor="#243447", height=10, border_radius=6),
                ]))

        # المعاملات
        list_column.controls.clear()
        filtered = [e for e in data if e.get("currency") == cur]
        if not filtered:
            list_column.controls.append(ft.Container(padding=20, content=ft.Text(
                f"لا توجد معاملات بعملة {cur}\nأضف أول معاملة! 👆",
                color="#7A8FA6", text_align=ft.TextAlign.CENTER, size=14)))
        else:
            for item in reversed(filtered):
                is_income    = item.get("type") == "دخل"
                sign         = "+" if is_income else "-"
                amount_color = "#00C896" if is_income else "#FF4D6D"
                row_bg       = "#0D2B1E" if is_income else "#2B0D1A"

                def make_delete(i):
                    def delete(_):
                        def do_delete():
                            data.remove(i); save_data(data); refresh_ui()
                        show_confirm("هل تريد حذف هذه المعاملة؟", do_delete)
                    return delete

                def make_edit(i):
                    return lambda _: open_edit(i)

                list_column.controls.append(ft.Container(
                    bgcolor=row_bg, border_radius=8,
                    padding=ft.Padding(left=12, right=12, top=8, bottom=8),
                    content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                        ft.Column(spacing=2, expand=True, controls=[
                            ft.Text(item.get("category", ""), size=13, color="#EAEAEA"),
                            ft.Text(item.get("desc") or item.get("date",""), size=11, color="#7A8FA6"),
                        ]),
                        ft.Text(f"{sign}{item['amount']} {cur}", size=13,
                                weight=ft.FontWeight.BOLD, color=amount_color),
                        ft.TextButton(content=ft.Text("✏️", size=16), on_click=make_edit(item)),
                        ft.TextButton(content=ft.Text("🗑", size=16), on_click=make_delete(item)),
                    ]),
                ))

        # الديون
        debts_column.controls.clear()
        filtered_debts = [d for d in debts if d.get("currency") == cur]
        if not filtered_debts:
            debts_column.controls.append(ft.Container(padding=20, content=ft.Text(
                "لا توجد ديون بهذه العملة\nأضف أول دين! 👆",
                color="#7A8FA6", text_align=ft.TextAlign.CENTER, size=14)))
        else:
            total_owed = sum(d["amount"] for d in filtered_debts if d.get("kind") == "عليك" and not d.get("paid"))
            total_due  = sum(d["amount"] for d in filtered_debts if d.get("kind") == "لك"    and not d.get("paid"))
            debts_column.controls.append(ft.Row(spacing=8, controls=[
                ft.Container(expand=True, padding=8, border_radius=8, bgcolor="#2B0D1A",
                    content=ft.Column(spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                        ft.Text("دين عليك", size=11, color="#7A8FA6"),
                        ft.Text(f"{total_owed:.0f} {cur}", size=13, weight=ft.FontWeight.BOLD, color="#FF4D6D"),
                    ])),
                ft.Container(expand=True, padding=8, border_radius=8, bgcolor="#0D2B1E",
                    content=ft.Column(spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                        ft.Text("دين لك", size=11, color="#7A8FA6"),
                        ft.Text(f"{total_due:.0f} {cur}", size=13, weight=ft.FontWeight.BOLD, color="#00C896"),
                    ])),
            ]))
            debts_column.controls.append(ft.Container(
                padding=ft.Padding(left=0, right=0, top=8, bottom=8),
                content=ft.ElevatedButton(
                    content=ft.Text("📄 تقرير الديون", color="#0F1923", weight=ft.FontWeight.BOLD, size=13),
                    bgcolor="#00C896", height=36, expand=True,
                    on_click=lambda _: do_export("كل الديون"),
                ),
            ))

            for d in reversed(filtered_debts):
                is_paid   = d.get("paid", False)
                kind      = d.get("kind", "عليك")
                row_bg    = "#0D2B1E" if kind == "لك" else "#2B0D1A"
                kind_text = "لك 📥" if kind == "لك" else "عليك 📤"
                state_clr = "#00C896" if is_paid else "#F6AD55"
                state_txt = "✅ مسدد" if is_paid else "⏳ غير مسدد"

                def make_debt_delete(i):
                    def delete(_):
                        def do_delete():
                            debts.remove(i); save_debts(debts); refresh_ui()
                        show_confirm("هل تريد حذف هذا الدين؟", do_delete)
                    return delete

                def make_debt_edit(i):
                    return lambda _: open_debt_edit(i)

                def make_toggle_paid(i):
                    def toggle(_):
                        i["paid"] = not i.get("paid", False)
                        save_debts(debts); refresh_ui()
                    return toggle

                debts_column.controls.append(ft.Container(
                    bgcolor=row_bg, border_radius=8,
                    padding=ft.Padding(left=12, right=12, top=8, bottom=8),
                    content=ft.Column(spacing=4, controls=[
                        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                            ft.Column(spacing=2, expand=True, controls=[
                                ft.Text(f"{d.get('name','')}  ({kind_text})", size=13, color="#EAEAEA"),
                                ft.Text(d.get("date",""), size=11, color="#7A8FA6"),
                            ]),
                            ft.Text(f"{d['amount']} {cur}", size=13,
                                    weight=ft.FontWeight.BOLD, color="#EAEAEA"),
                        ]),
                        ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                            ft.TextButton(
                                content=ft.Text(state_txt, color=state_clr, size=12),
                                on_click=make_toggle_paid(d)),
                            ft.Row(spacing=0, controls=[
                                ft.TextButton(content=ft.Text("✏️", size=16), on_click=make_debt_edit(d)),
                                ft.TextButton(content=ft.Text("🗑", size=16), on_click=make_debt_delete(d)),
                            ]),
                        ]),
                    ]),
                ))

        page.update()

    # ── إضافة معاملة ──
    def add_entry(_):
        if editing_item[0]:
            save_edit(); return
        if not amount_field.value or not amount_field.value.strip():
            page.snack_bar = ft.SnackBar(ft.Text("⚠️ الرجاء إدخال المبلغ"), bgcolor="#FF4D6D")
            page.snack_bar.open = True; page.update(); return
        try:
            amount = float(amount_field.value)
            if amount <= 0: raise ValueError
        except ValueError:
            page.snack_bar = ft.SnackBar(ft.Text("⚠️ أدخل مبلغاً صحيحاً"), bgcolor="#FF4D6D")
            page.snack_bar.open = True; page.update(); return

        final_category = cat_dropdown.value
        if (cat_dropdown.value == "📦 أخرى" and has_trial_features()
                and custom_cat_field.value and custom_cat_field.value.strip()):
            final_category = f"🏷️ {custom_cat_field.value.strip()}"

        data.append({
            "amount": amount, "type": type_dropdown.value,
            "category": final_category, "currency": current_currency[0],
            "desc": desc_field.value.strip(), "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        save_data(data)
        amount_field.value = ""; desc_field.value = ""; custom_cat_field.value = ""
        refresh_ui()

    add_btn.on_click = add_entry

    # ── إضافة دين ──
    def add_debt(_):
        if not has_trial_features():
            show_upgrade("تتبع الديون")
            return
        if not debt_name_field.value.strip():
            page.snack_bar = ft.SnackBar(ft.Text("⚠️ أدخل اسم الشخص"), bgcolor="#FF4D6D")
            page.snack_bar.open = True; page.update(); return
        try:
            amount = float(debt_amount_field.value)
            if amount <= 0: raise ValueError
        except:
            page.snack_bar = ft.SnackBar(ft.Text("⚠️ أدخل مبلغاً صحيحاً"), bgcolor="#FF4D6D")
            page.snack_bar.open = True; page.update(); return

        debts.append({
            "name": debt_name_field.value.strip(), "amount": amount,
            "kind": debt_kind_dropdown.value, "currency": current_currency[0],
            "paid": False, "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        save_debts(debts)
        debt_name_field.value = ""; debt_amount_field.value = ""
        refresh_ui()

    debt_btn.on_click = add_debt

    def confirm_clear(_):
        cur = current_currency[0]
        def do_clear():
            to_remove = [e for e in data if e.get("currency") == cur]
            for e in to_remove: data.remove(e)
            save_data(data); refresh_ui()
        show_confirm(f"حذف جميع معاملات {cur}؟", do_clear)

    info_msg = ft.Text("", color="#7A8FA6", size=13, text_align=ft.TextAlign.CENTER)
    info_overlay = ft.Container(
        visible=False, bgcolor="#000000CC", expand=True,
        alignment=ft.Alignment(0, 0), top=0, left=0, right=0, bottom=0,
        content=ft.Container(
            width=300, padding=20, border_radius=12, bgcolor="#1A2635",
            content=ft.Column(tight=True, spacing=16,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("✅ تم بنجاح", size=16, weight=ft.FontWeight.BOLD, color="#00C896"),
                    info_msg,
                    ft.ElevatedButton(
                        content=ft.Text("حسناً", color="#0F1923", weight=ft.FontWeight.BOLD),
                        bgcolor="#00C896",
                        on_click=lambda _: (setattr(info_overlay, 'visible', False) or page.update()),
                    ),
                ],
            ),
        ),
    )

    def show_info(msg):
        info_msg.value = msg
        info_overlay.visible = True
        page.update()

    # ── Overlay: اختيار نوع التقرير ──
    report_type_selected = [None]
    report_cat_selected  = [None]

    def on_report_cat_change(_):
        if report_cat_dropdown.value == LOCKED_CATEGORY_LABEL:
            report_cat_dropdown.value = FREE_CATEGORIES[0]
            show_upgrade("فئات إضافية")
        page.update()

    report_cat_dropdown = ft.Dropdown(
        label="اختر الفئة", value=FREE_CATEGORIES[0],
        options=build_category_options(), on_select=on_report_cat_change,
        bgcolor="#0F1923", color="#EAEAEA",
        label_style=ft.TextStyle(color="#7A8FA6"),
        border_color="#243447", focused_border_color="#00C896",
        visible=False,
    )

    export_cat_btn = ft.ElevatedButton(
        content=ft.Text("📄 تصدير هذه الفئة", color="#0F1923", weight=ft.FontWeight.BOLD, size=13),
        bgcolor="#00C896", height=40, visible=False,
        on_click=lambda _: do_export("فئة معينة"),
    )

    def do_export(report_type):
        if not PDF_AVAILABLE:
            show_info("⚠️ مكتبة PDF غير مثبتة (fpdf2 / arabic-reshaper / python-bidi)")
            return
        cur = current_currency[0]
        try:
            base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            fname = os.path.join(base_dir, f"تقرير_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")

            pdf = new_pdf()
            pdf_title(pdf, f"📄 تقرير محفظتي - {report_type}")
            pdf_line(pdf, f"التاريخ: {datetime.now().strftime('%Y-%m-%d')}   |   العملة: {cur}", size=11)
            pdf.ln(2)

            def transactions_table(items):
                pdf_table_row(pdf, ["التاريخ", "البيان", "الفئة", "النوع", "المبلغ"],
                              [28, 55, 35, 22, 30], fill=(0, 200, 150))
                for e in reversed(items):
                    sign = "+" if e.get("type") == "دخل" else "-"
                    pdf_table_row(pdf, [
                        e.get("date", ""), e.get("desc", "") or "-", e.get("category", ""),
                        e.get("type", ""), f"{sign}{e['amount']:.0f} {cur}",
                    ], [28, 55, 35, 22, 30])

            def debts_table(items):
                pdf_table_row(pdf, ["التاريخ", "الاسم", "النوع", "الحالة", "المبلغ"],
                              [28, 45, 30, 30, 37], fill=(0, 200, 150))
                for d in reversed(items):
                    pdf_table_row(pdf, [
                        d.get("date", ""), d.get("name", ""),
                        "دين عليك" if d.get("kind") == "عليك" else "دين لك",
                        "مسدد" if d.get("paid") else "غير مسدد",
                        f"{d['amount']:.0f} {cur}",
                    ], [28, 45, 30, 30, 37])

            if report_type == "كل شيء":
                filtered = [e for e in data if e.get("currency") == cur]
                total_in  = sum(e["amount"] for e in filtered if e.get("type") == "دخل")
                total_out = sum(e["amount"] for e in filtered if e.get("type") != "دخل")
                pdf_line(pdf, f"💰 الدخل: {total_in:.0f} {cur}   |   💸 المصروف: {total_out:.0f} {cur}   |   🟢 الرصيد: {total_in-total_out:.0f} {cur}", size=13)
                pdf.ln(3)
                pdf_line(pdf, "📊 المعاملات", size=13)
                transactions_table(filtered)
                pdf.ln(5)
                dfiltered = [d for d in debts if d.get("currency") == cur]
                total_on_me  = sum(d["amount"] for d in dfiltered if d.get("kind") == "عليك" and not d.get("paid"))
                total_for_me = sum(d["amount"] for d in dfiltered if d.get("kind") == "لك" and not d.get("paid"))
                pdf_line(pdf, f"📑 الديون  -  عليك: {total_on_me:.0f} {cur}   |   لك: {total_for_me:.0f} {cur}", size=13)
                debts_table(dfiltered)

            elif report_type == "المصروفات":
                filtered = [e for e in data if e.get("currency") == cur and e.get("type") != "دخل"]
                total = sum(e["amount"] for e in filtered)
                pdf_line(pdf, f"💸 إجمالي المصروفات: {total:.0f} {cur}", size=13)
                transactions_table(filtered)

            elif report_type == "الدخل":
                filtered = [e for e in data if e.get("currency") == cur and e.get("type") == "دخل"]
                total = sum(e["amount"] for e in filtered)
                pdf_line(pdf, f"💰 إجمالي الدخل: {total:.0f} {cur}", size=13)
                transactions_table(filtered)

            elif report_type == "فئة معينة":
                cat = report_cat_dropdown.value
                filtered = [e for e in data if e.get("currency") == cur and e.get("category") == cat and e.get("type") != "دخل"]
                total = sum(e["amount"] for e in filtered)
                pdf_line(pdf, f"الفئة: {cat}   |   الإجمالي: {total:.0f} {cur}", size=13)
                transactions_table(filtered)

            elif report_type == "ديون عليك":
                filtered = [d for d in debts if d.get("currency") == cur and d.get("kind") == "عليك"]
                total = sum(d["amount"] for d in filtered if not d.get("paid"))
                pdf_line(pdf, f"إجمالي غير مسدد: {total:.0f} {cur}", size=13)
                debts_table(filtered)

            elif report_type == "ديون لك":
                filtered = [d for d in debts if d.get("currency") == cur and d.get("kind") == "لك"]
                total = sum(d["amount"] for d in filtered if not d.get("paid"))
                pdf_line(pdf, f"إجمالي غير مسدد: {total:.0f} {cur}", size=13)
                debts_table(filtered)

            elif report_type == "كل الديون":
                filtered = [d for d in debts if d.get("currency") == cur]
                total_on_me  = sum(d["amount"] for d in filtered if d.get("kind") == "عليك" and not d.get("paid"))
                total_for_me = sum(d["amount"] for d in filtered if d.get("kind") == "لك" and not d.get("paid"))
                pdf_line(pdf, f"دين عليك: {total_on_me:.0f} {cur}   |   دين لك: {total_for_me:.0f} {cur}", size=13)
                debts_table(filtered)

            pdf.output(fname)
            report_overlay.visible = False
            show_info(f"تم حفظ التقرير:\n{os.path.basename(fname)}")
        except Exception as e:
            show_info(f"❌ فشل الحفظ: {e}")

    def on_report_type_change(report_type):
        if report_type == "فئة معينة" and not premium_ok[0]:
            show_upgrade("تقرير حسب فئة معينة")
            return
        report_cat_dropdown.visible = (report_type == "فئة معينة")
        export_cat_btn.visible = (report_type == "فئة معينة")
        page.update()

    def make_report_btn(t):
        if t == "فئة معينة":
            return ft.ElevatedButton(
                content=ft.Text(t, color="#0F1923", weight=ft.FontWeight.BOLD, size=13),
                bgcolor="#4FD1C5", height=40,
                on_click=lambda _: on_report_type_change("فئة معينة"),
            )
        return ft.ElevatedButton(
            content=ft.Text(t, color="#0F1923", weight=ft.FontWeight.BOLD, size=13),
            bgcolor="#00C896", height=40,
            on_click=(lambda rt: lambda _: do_export(rt))(t),
        )

    report_btns = ft.Column(spacing=6, controls=[
        make_report_btn(t) for t in ["كل شيء", "المصروفات", "الدخل", "فئة معينة", "ديون عليك", "ديون لك", "كل الديون"]
    ])

    # أضف dropdown الفئة بعد قائمة الأزرار
    report_btns.controls.insert(4, report_cat_dropdown)
    report_btns.controls.insert(5, export_cat_btn)

    report_overlay = ft.Container(
        visible=False, bgcolor="#000000CC", expand=True,
        alignment=ft.Alignment(0, 0), top=0, left=0, right=0, bottom=0,
        content=ft.Container(
            width=300, padding=20, border_radius=12, bgcolor="#1A2635",
            content=ft.Column(tight=True, spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text("📄 اختر نوع التقرير", size=16,
                            weight=ft.FontWeight.BOLD, color="#00C896"),
                    ft.Divider(color="#243447"),
                    report_btns,
                    ft.TextButton(
                        content=ft.Text("إلغاء", color="#7A8FA6"),
                        on_click=lambda _: (setattr(report_overlay, 'visible', False) or page.update()),
                    ),
                ],
            ),
        ),
    )

    def export_report(_):
        report_overlay.visible = True
        page.update()

    # أقسام قابلة للطي
    chart_wrapper = ft.Container(height=150, visible=False,
        content=ft.Column(scroll=ft.ScrollMode.AUTO, controls=[chart_column]))
    list_wrapper  = ft.Container(visible=False, content=list_column)
    debts_wrapper = ft.Container(visible=False, content=debts_column)

    chart_arrow = ft.Text("▾", size=14, color="#7A8FA6")
    list_arrow  = ft.Text("▾", size=14, color="#7A8FA6")
    debts_arrow = ft.Text("▾", size=14, color="#7A8FA6")

    def toggle_chart(_):
        chart_wrapper.visible = not chart_wrapper.visible
        chart_arrow.value = "▴" if chart_wrapper.visible else "▾"; page.update()

    def toggle_list(_):
        list_wrapper.visible = not list_wrapper.visible
        list_arrow.value = "▴" if list_wrapper.visible else "▾"; page.update()

    def toggle_debts(_):
        debts_wrapper.visible = not debts_wrapper.visible
        debts_arrow.value = "▴" if debts_wrapper.visible else "▾"; page.update()

    main_content = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, controls=[
        # Header
        ft.Container(
            padding=ft.Padding(left=16, right=16, top=12, bottom=12),
            border_radius=12, bgcolor="#1A2635",
            content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                ft.Text(f"💼 {APP_NAME}", size=22, weight=ft.FontWeight.BOLD, color="#00C896"),
                ft.Row(spacing=4, controls=[
                    ft.Text(
                        ("💎 مدفوع" if premium_ok[0] else
                         (f"🎁 تجربة {days_left[0]} يوم" if trial_ok[0] else "🔒 التجربة انتهت")),
                        size=11,
                        color=("#00C896" if premium_ok[0] else ("#F6AD55" if trial_ok[0] else "#FF4D6D")),
                    ),
                    ft.TextButton(content=ft.Text("ℹ️", size=18), on_click=show_about),
                ]),
            ]),
        ),
        ft.Container(height=8),
        # عملة
        ft.Container(
            padding=ft.Padding(left=12, right=12, top=8, bottom=8),
            border_radius=10, bgcolor="#1A2635",
            content=ft.Row(spacing=8, controls=[
                ft.Text("💱 العملة:", size=13, color="#7A8FA6"), sar_btn, yer_btn]),
        ),
        ft.Container(height=6),
        ft.Container(
            padding=ft.Padding(left=12, right=12, top=6, bottom=6),
            border_radius=10, bgcolor="#1A2635",
            content=ft.Column(spacing=6, controls=[
                default_currency_switch, default_currency_dropdown,
            ]),
        ),
        ft.Container(height=8),
        summary_row,
        ft.Container(
            padding=ft.Padding(left=12, right=12, top=0, bottom=8),
            content=ft.ElevatedButton(
                content=ft.Text("📄 تقرير الدخل والمصروف", color="#0F1923", weight=ft.FontWeight.BOLD, size=13),
                bgcolor="#00C896", height=38, expand=True,
                on_click=lambda _: do_export("كل شيء"),
            ),
        ),
        ft.Container(height=8),
        # إضافة معاملة
        ft.Container(padding=14, border_radius=12, bgcolor="#1A2635",
            content=ft.Column(spacing=10, controls=[
                ft.Text("➕ إضافة معاملة", size=14, weight=ft.FontWeight.BOLD, color="#EAEAEA"),
                ft.Row(controls=[amount_field, type_dropdown], spacing=8),
                cat_dropdown, custom_cat_field, desc_field, add_btn,
            ]),
        ),
        ft.Container(height=8),
        # رسم بياني
        ft.Container(border_radius=12, bgcolor="#1A2635", padding=14,
            content=ft.Column(spacing=10, controls=[
                ft.Container(on_click=toggle_chart,
                    content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                        ft.Text("📊 المصروفات حسب الفئة", size=14, weight=ft.FontWeight.BOLD, color="#EAEAEA"),
                        chart_arrow,
                    ])),
                chart_wrapper,
            ]),
        ),
        ft.Container(height=8),
        # المعاملات
        ft.Container(border_radius=12, bgcolor="#1A2635", padding=14,
            content=ft.Column(spacing=10, controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                    ft.Container(on_click=toggle_list,
                        content=ft.Row(spacing=6, controls=[
                            ft.Text("📋 المعاملات", size=14, weight=ft.FontWeight.BOLD, color="#EAEAEA"),
                            list_arrow,
                        ])),
                    ft.Row(spacing=0, controls=[
                        ft.TextButton(content=ft.Text("📄 تقرير", color="#00C896"), on_click=export_report),
                        ft.TextButton(content=ft.Text("حذف الكل", color="#FF4D6D"), on_click=confirm_clear),
                    ]),
                ]),
                list_wrapper,
            ]),
        ),
        ft.Container(height=8),
        # الديون
        ft.Container(padding=14, border_radius=12, bgcolor="#1A2635",
            content=ft.Column(spacing=10, controls=[
                ft.Container(on_click=toggle_debts,
                    content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                        ft.Text("💸 ديوني", size=14, weight=ft.FontWeight.BOLD, color="#EAEAEA"),
                        debts_arrow,
                    ])),
                debts_wrapper,
                ft.Text("➕ إضافة دين", size=13, weight=ft.FontWeight.BOLD, color="#EAEAEA"),
                ft.Row(controls=[debt_name_field, debt_kind_dropdown], spacing=8),
                debt_amount_field,
                debt_btn,
            ]),
        ),
    ])

    page.add(ft.Stack(expand=True, controls=[
        main_content, confirm_overlay, edit_overlay,
        edit_debt_overlay, about_overlay, update_overlay, report_overlay, info_overlay,
        upgrade_overlay,
    ]))
    refresh_ui()
    check_for_updates(page, update_overlay)

ft.app(target=main)




