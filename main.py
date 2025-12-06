import os
import telebot
from flask import Flask, request, render_template_string
import pytesseract
from PIL import Image

# ------------------- إعدادات البوت -------------------
# في Render هنحط التوكن في الإعدادات عشان الأمان، أو اكتبه هنا عادي
API_TOKEN = '5101248556:AAEC-aXai10HlBlqYV5jnWdT1uCkM4IHHOs'
ADMIN_ID = '605310602'

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# مسار برنامج Tesseract على سيرفر لينكس (مهم عشان Docker)
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# ------------------- خريطة الأكواد -------------------
CODE_MAP = {
    "receipt1": "Code 16", "receipt2": "Code 17",
    "receipt3": "Code 15", "receipt4": "Code 5",
    "receipt5": "Code 13", "receipt6": "Code 12",
    "receipt7": "Code 18", "receipt8": "Code 19"
}

# ------------------- HTML TEMPLATE -------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>نظام تسليم التركيبات</title>
    <style>
        body { font-family: sans-serif; background: #f4f4f9; padding: 20px; }
        .container { max-width: 500px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        input, select, button { width: 100%; padding: 10px; margin: 10px 0; border-radius: 5px; border: 1px solid #ddd; }
        button { background: #28a745; color: white; border: none; cursor: pointer; font-size: 16px; }
        button:hover { background: #218838; }
        .error { color: red; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h2 style="text-align:center;">تسليم تركيب جديد</h2>
        {% if error_message %}<p class="error">{{ error_message }}</p>{% endif %}
        <form action="/submit" method="post" enctype="multipart/form-data">
            <input type="text" name="customer_name" placeholder="اسم العميل" required>
            <input type="tel" name="mobile" placeholder="رقم الموبايل" required>
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

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/submit', methods=['POST'])
def submit_form():
    name = request.form.get('customer_name')
    mobile = request.form.get('mobile')
    receipt_type = request.form.get('receipt_type')
    file = request.files['receipt_photo']

    if not file: return "No file"
    
    filename = "temp.jpg"
    file.save(filename)
    
    # OCR Process
    try:
        text = pytesseract.image_to_string(Image.open(filename))
        expected_code = CODE_MAP.get(receipt_type)
        
        if expected_code in text:
            caption = f"✅ **تركيب جديد**\n👤 {name}\n📱 {mobile}\n🧾 كود: {expected_code}"
            with open(filename, 'rb') as ph:
                bot.send_photo(ADMIN_ID, ph, caption=caption)
            return "<h2>✅ تم الإرسال بنجاح!</h2>"
        else:
            return render_template_string(HTML_TEMPLATE, error_message=f"❌ خطأ! الصورة لا تحتوي على {expected_code}")
    except Exception as e:
        return f"Error: {e}"

if __name__ == '__main__':
    # Render بيحدد البورت تلقائي، لازم نستخدمه
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    