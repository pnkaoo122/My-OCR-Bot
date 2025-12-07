import os
import telebot
import sqlite3
import uuid
import datetime
from flask import Flask, request, render_template_string, redirect, url_for, session, send_from_directory
import pytesseract
from PIL import Image
from functools import wraps

# ------------------- إعدادات البوت والسيرفر -------------------
# تم تحديث التوكن هنا 👇
API_TOKEN = '8552676786:AAEjb7deDTJDaXttXxu7Mio6Qqsalw6v7SY'

# ده الآيدي بتاعك اللي هيوصل عليه الرسايل (لو عايز تغيره قولي)
ADMIN_ID = '605310602'

# إعدادات المشرف (اليوزر والباسورد للدخول للوحة التحكم)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "123"  # غير الباسورد ده للأمان

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)
app.secret_key = 'super_secret_key_change_this'  # مهم عشان الـ Sessions

# مسار برنامج Tesseract
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# مسار حفظ الصور وقاعدة البيانات
UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

DB_NAME = 'installations.db'

# ------------------- خريطة الأكواد -------------------
CODE_MAP = {
    "receipt1": "Code 16", "receipt2": "Code 17",
    "receipt3": "Code 15", "receipt4": "Code 5",
    "receipt5": "Code 13", "receipt6": "Code 12",
    "receipt7": "Code 18", "receipt8": "Code 19"
}

# ------------------- دوال قاعدة البيانات -------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS installs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  tech_name TEXT,
                  customer_name TEXT,
                  mobile TEXT,
                  receipt_type TEXT,
                  image_path TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# ------------------- حماية لوحة التحكم -------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ------------------- HTML TEMPLATES -------------------

# 1. صفحة تسجيل الدخول
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تسجيل دخول المشرف</title>
    <style>
        body { font-family: sans-serif; background: #f4f4f9; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .box { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); width: 300px; text-align: center; }
        input { width: 90%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
        button { width: 100%; padding: 10px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }
        .error { color: red; font-size: 14px; }
    </style>
</head>
<body>
    <div class="box">
        <h2>دخول المشرفين</h2>
        {% if error %}<p class="error">{{ error }}</p>{% endif %}
        <form method="post">
            <input type="text" name="username" placeholder="اسم المستخدم" required>
            <input type="password" name="password" placeholder="كلمة المرور" required>
            <button type="submit">دخول</button>
        </form>
    </div>
</body>
</html>
"""

# 2. صفحة لوحة التحكم (Dashboard)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>لوحة التحكم</title>
    <style>
        body { font-family: sans-serif; padding: 20px; background: #f9f9f9; }
        table { width: 100%; border-collapse: collapse; background: white; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: center; }
        th { background: #333; color: white; }
        img { width: 80px; height: auto; border-radius: 5px; cursor: pointer; }
        .header { display: flex; justify-content: space-between; align-items: center; background: #fff; padding: 15px; border-radius: 5px; }
        .logout { background: #dc3545; color: white; padding: 8px 15px; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h2>📊 سجل التركيبات الناجحة</h2>
        <a href="/logout" class="logout">تسجيل خروج</a>
    </div>
    
    <table>
        <thead>
            <tr>
                <th>التاريخ</th>
                <th>اسم الفني</th>
                <th>اسم العميل</th>
                <th>الموبايل</th>
                <th>نوع الإيصال</th>
                <th>صورة الإيصال</th>
            </tr>
        </thead>
        <tbody>
            {% for row in rows %}
            <tr>
                <td>{{ row[6] }}</td>
                <td>{{ row[1] }}</td>
                <td>{{ row[2] }}</td>
                <td>{{ row[3] }}</td>
                <td>{{ row[4] }}</td>
                <td><a href="/uploads/{{ row[5] }}" target="_blank"><img src="/uploads/{{ row[5] }}"></a></td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

# 3. صفحة الفورم (للفنيين)
FORM_HTML = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نظام تسليم التركيبات</title>
    <style>
        body { font-family: sans-serif; background: #f4f4f9; padding: 20px; }
        .container { max-width: 500px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        input, select, button { width: 100%; padding: 10px; margin: 10px 0; border-radius: 5px; border: 1px solid #ddd; box-sizing: border-box; }
        button { background: #28a745; color: white; border: none; cursor: pointer; font-size: 16px; }
        button:hover { background: #218838; }
        .error { color: red; font-weight: bold; text-align: center;}
    </style>
</head>
<body>
    <div class="container">
        <h2 style="text-align:center;">تسليم تركيب جديد</h2>
        {% if error_message %}<p class="error">{{ error_message }}</p>{% endif %}
        <form action="/submit" method="post" enctype="multipart/form-data">
            
            <label>بيانات الفني والعميل:</label>
            <input type="text" name="tech_name" placeholder="اسم الفني (اللي ركب)" required>
            <input type="text" name="customer_name" placeholder="اسم العميل" required>
            <input type="tel" name="mobile" placeholder="رقم الموبايل" required>
            
            <label>بيانات الإيصال:</label>
            <select name="receipt_type" required>
                <option value="" disabled selected>-- اختر نوع الإيصال --</option>
                <option value="receipt1">نوع 1 (كود 16)</option>
                <option value="receipt2">نوع 2 (كود 17)</option>
                <option value="receipt3">نوع 3 (كود 15)</option>
                <option value="receipt4">نوع 4 (كود 5)</option>
                <option value="receipt5">نوع 5 (كود 13)</option>
                <option value="receipt6">نوع 6 (كود 12)</option>
                <option value="receipt7">نوع 7 (كود 18)</option>
                <option value="receipt8">نوع 8 (كود 19)</option>
            </select>
            
            <label>صورة الإيصال:</label>
            <input type="file" name="receipt_photo" accept="image/*" capture="camera" required>
            
            <button type="submit">فحص وإرسال</button>
        </form>
    </div>
</body>
</html>
"""

# ------------------- Routes (مسارات الموقع) -------------------

@app.route('/', methods=['GET'])
def index():
    return render_template_string(FORM_HTML)

# مسار تسجيل الدخول للمشرف
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = 'بيانات الدخول غير صحيحة!'
    return render_template_string(LOGIN_HTML, error=error)

# مسار لوحة التحكم (محمي)
@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # جلب البيانات مرتبة من الأحدث للأقدم
    c.execute("SELECT * FROM installs ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return render_template_string(DASHBOARD_HTML, rows=rows)

# مسار تسجيل الخروج
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# مسار لعرض الصور المحفوظة
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/submit', methods=['POST'])
def submit_form():
    tech_name = request.form.get('tech_name')
    customer_name = request.form.get('customer_name')
    mobile = request.form.get('mobile')
    receipt_type = request.form.get('receipt_type')
    file = request.files['receipt_photo']

    if not file: return "No file"
    
    # حفظ الصورة باسم فريد
    filename = f"{uuid.uuid4()}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    
    # OCR Process
    try:
        text = pytesseract.image_to_string(Image.open(filepath))
        expected_code = CODE_MAP.get(receipt_type)
        
        if expected_code in text:
            # 1. إرسال للتليجرام
            caption = f"✅ **تم التركيب بنجاح**\n👨‍🔧 الفني: {tech_name}\n👤 العميل: {customer_name}\n📱 {mobile}\n🧾 كود: {expected_code}"
            with open(filepath, 'rb') as ph:
                bot.send_photo(ADMIN_ID, ph, caption=caption)
            
            # 2. حفظ في قاعدة البيانات للمشرف
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("INSERT INTO installs (tech_name, customer_name, mobile, receipt_type, image_path) VALUES (?, ?, ?, ?, ?)",
                      (tech_name, customer_name, mobile, expected_code, filename))
            conn.commit()
            conn.close()

            return "<h2>✅ تم الإرسال وحفظ البيانات بنجاح!</h2><a href='/'>عودة</a>"
        else:
            # os.remove(filepath)
            return render_template_string(FORM_HTML, error_message=f"❌ خطأ! الصورة لا تحتوي على {expected_code}")
    except Exception as e:
        return f"Error: {e}"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
