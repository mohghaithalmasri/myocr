from paddleocr import PaddleOCR
import os
import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageEnhance

# ----------------------------------------------------
# إعدادات المعالجة القابلة للتخصيص
INK_DARKENING_FACTOR = 1.1
# ----------------------------------------------------

ocr = PaddleOCR(
    ocr_version='PP-OCRv5',
    lang='ar',
    device="gpu",          
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    # det_limit_side_len=4500,
    # det_db_box_thresh=0.7,  # تقليل العتبة لالتقاط المزيد من الصناديق
    # det_db_unclip_ratio=1.6,  # زيادة نسبة التوسيع (مفيد للكلمات المائلة)

    
)

root = tk.Tk()
root.withdraw()

print("[+] الرجاء اختيار ملف PDF من النافذة المنبثقة...")
pdf_path = filedialog.askopenfilename(
    title="اختر ملف PDF لاستخراج النصوص",
    filetypes=[("PDF files", "*.pdf")]
)

if not pdf_path:
    print("[-] لم يتم اختيار أي ملف. إغلاق البرنامج.")
    exit()

print(f"[+] جاري معالجة الملف الممسوح ضوئياً: {pdf_path}")


# 3. الخوارزمية الهندسية الجديدة: الفرز بالاعتماد على نسبة التداخل العمودي
def structure_arabic_v5_smart(predictions): 
    for res in predictions:
        if hasattr(res, 'res'):
            data = res.res
        elif hasattr(res, 'json'):
            data = res.json
        else:
            data = res
            
        if isinstance(data, dict) and 'res' in data:
            data = data['res']
            
        if 'rec_texts' not in data or 'rec_polys' not in data:
            continue
            
        rec_texts = data['rec_texts']
        rec_polys = data['rec_polys']
        
        boxes = []
        for i in range(len(rec_texts)):
            text = rec_texts[i]
            poly = rec_polys[i] 
            
            if not text.strip(): 
                continue
                
            # حساب الأبعاد الكاملة للمربع المحيط بالكلمة
            y_coords = [p[1] for p in poly]
            x_coords = [p[0] for p in poly]
            
            y_min, y_max = min(y_coords), max(y_coords)
            x_min, x_max = min(x_coords), max(x_coords)
            
            boxes.append({
                'text': text,
                'x_min': x_min,
                'x_max': x_max,
                'y_min': y_min,
                'y_max': y_max,
                'center_y': (y_min + y_max) / 2,
                'height': y_max - y_min
            })
            
        if not boxes:
            return "لم يتم العثور على نصوص قابلة للقراءة في هذا الملف."

        # فرز مبدئي حسب المركز العمودي لتسريع العملية
        boxes.sort(key=lambda b: b['center_y'])
        
        lines = []
        for box in boxes:
            placed = False
            for line in lines:
                # حساب الحدود الرأسية للسطر الحالي
                line_y_min = min(b['y_min'] for b in line)
                line_y_max = max(b['y_max'] for b in line)
                
                # حساب مقدار التداخل العمودي بين الكلمة والسطر
                overlap = max(0, min(box['y_max'], line_y_max) - max(box['y_min'], line_y_min))
                
                # إذا تداخلت الكلمة مع السطر بنسبة 40% من ارتفاعها، فهي تابعة له
                if box['height'] > 0 and (overlap / box['height']) > 0.4:
                    line.append(box)
                    placed = True
                    break
            
            # إذا لم تتداخل مع أي سطر، أنشئ سطراً جديداً
            if not placed:
                lines.append([box])
                
        # الترتيب النهائي للأسطر من الأعلى إلى الأسفل
        lines.sort(key=lambda line: sum(b['center_y'] for b in line) / len(line))
        
        # بناء النص النهائي
        final_lines = []
        for line in lines:
            # ترتيب الكلمات داخل السطر من اليمين إلى اليسار (x_max تنازلياً)
            line.sort(key=lambda b: b['x_max'], reverse=True)
            line_string = "   ".join([b['text'] for b in line])
            final_lines.append(line_string)
            
        return "\n".join(final_lines)
        
    return "فشلت عملية استخراج البيانات هندسياً."


# 4. معالجة الصفحات
print("[+] جاري استخراج النصوص من المستند الممسوح ضوئياً...")

doc = fitz.open(pdf_path)
all_pages_text = []

for page_num in range(len(doc)):
    print(f"[+] معالجة الصفحة {page_num + 1} من {len(doc)}...")
    page = doc[page_num]
    
    # تحويل الصفحة إلى صورة بدقة عالية
    pix = page.get_pixmap(dpi=350)
    temp_img_path = f"temp_page_{page_num + 1}.png"
    pix.save(temp_img_path)
    
    # تحسين تباين الصورة لدعم الـ OCR
    img = Image.open(temp_img_path)
    img = ImageEnhance.Contrast(img).enhance(INK_DARKENING_FACTOR)
    img.save(temp_img_path)
    
    # استخراج النصوص وتمريرها للخوارزمية الذكية
    predictions = ocr.predict(input=temp_img_path)
    page_text = structure_arabic_v5_smart(predictions)
    
    if os.path.exists(temp_img_path):
        os.remove(temp_img_path)
    
    page_header = f"=== الصفحة {page_num + 1} ==="
    all_pages_text.append(f"{page_header}\n{page_text}")

formatted_output = "\n\n".join(all_pages_text)

print("\n=== النتيجة النهائية المنسقة ===\n")
print(formatted_output)

# الحفظ
output_path = os.path.splitext(pdf_path)[0] + "_ocr_smart_extracted.txt"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(formatted_output)
    
print(f"\n[+] تم بنجاح! حُفظت النتيجة في: {output_path}")