from paddleocr import PaddleOCR


ocr = PaddleOCR(
    ocr_version='PP-OCRv5',
    lang='ar',
    device="gpu",          
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
   
)

image_path = r"C:\Users\ASUS\Desktop\ocr\page_3_processed.png"

print("[+] جاري معالجة الصورة باستخدام PP-OCRv5 وتسريع كرت الشاشة...")

# 2. استدعاء وظيفة التنبؤ الجديدة (predict) دون استخدام بارامتر 'cls' المرفوض
predictions = ocr.predict(input=image_path)

# 3. دالة الفرز الذكية المعدلة خصيصاً لتناسب الهيكل الجديد لنصوص ومضلعات V5
def structure_arabic_v5(predictions, y_tolerance=25):
    for res in predictions:
        # استخراج البيانات الديناميكية من كائن المخرجات الجديد
        if hasattr(res, 'res'):
            data = res.res
        elif hasattr(res, 'json'):
            data = res.json
        else:
            data = res
            
        if isinstance(data, dict) and 'res' in data:
            data = data['res']
            
        # التأكد من وجود النصوص والمضلعات الهندسية
        if 'rec_texts' not in data or 'rec_polys' not in data:
            continue
            
        rec_texts = data['rec_texts']
        rec_polys = data['rec_polys']
        
        # دمج النصوص مع إحداثياتها لتسهيل فرزها
        combined_items = []
        for i in range(len(rec_texts)):
            text = rec_texts[i]
            poly = rec_polys[i]  # مصفوفة النقاط الـ 4 المحيطة بالكلمة
            
            if not text.strip():  # تخطي الفراغات
                continue
                
            combined_items.append({
                'text': text,
                'x': poly[0][0],  # إحداثي البداية الأفقي X
                'y': poly[0][1]   # إحداثي الارتفاع الرأسي Y
            })
            
        if not combined_items:
            return "لم يتم العثور على نصوص قابلة للقراءة في هذا الملف."

        # الفرز الرأسي الأول بناءً على الارتفاع لتجميع النصوص في "أسطر"
        sorted_by_y = sorted(combined_items, key=lambda item: item['y'])
        
        lines = []
        current_line = []
        last_y = -1
        
        for item in sorted_by_y:
            current_y = item['y']
            
            # إذا كانت الكلمة تقع ضمن نفس السطر تقريباً (حسب الهامش المقبول)
            if last_y == -1 or abs(current_y - last_y) <= y_tolerance:
                current_line.append(item)
            else:
                # ترتيب كلمات السطر الواحد من اليمين إلى اليسار (X تنازلياً) لأن النص عربي
                current_line.sort(key=lambda x: x['x'], reverse=True)
                lines.append(current_line)
                current_line = [item]
                
            last_y = current_y
            
        if current_line:
            current_line.sort(key=lambda x: x['x'], reverse=True)
            lines.append(current_line)
            
        # بناء النص النهائي المنسق
        final_lines = []
        for line in lines:
            line_string = "   ".join([item['text'] for item in line])
            final_lines.append(line_string)
            
        return "\n".join(final_lines)
        
    return "فشلت عملية استخراج البيانات هندسياً."

# 4. تشغيل الفرز وطباعة وحفظ النتيجة
formatted_output = structure_arabic_v5(predictions)

print("\n=== النتيجة النهائية المنسقة متل الملف تماماً (PP-OCRv5) ===\n")
print(formatted_output)

# حفظ النتيجة المُرتبة في ملف نصي نظيف
with open("ordered_v5_output.txt", "w", encoding="utf-8") as f:
    f.write(formatted_output)
    
print("\n[+] ممتاز! تم التخلص من الخطأ وحُفظ النص مرتباً في: ordered_v5_output.txt")