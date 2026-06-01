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

print("[+] الرجاء اختيار مجلد يحتوي على ملفات PDF من النافذة المنبثقة...")
folder_path = filedialog.askdirectory(
    title="اختر مجلد يحتوي على ملفات PDF لاستخراج النصوص"
)

if not folder_path:
    print("[-] لم يتم اختيار أي مجلد. إغلاق البرنامج.")
    exit()

pdf_files = []
for root_dir, dirs, files in os.walk(folder_path):
    for file in files:
        if file.lower().endswith('.pdf'):
            pdf_files.append(os.path.join(root_dir, file))

if not pdf_files:
    print("[-] لم يتم العثور على أي ملفات PDF في المجلد المختار.")
    exit()

output_path = os.path.join(folder_path, "all_pdfs_extracted_text.txt")
print(f"[+] تم العثور على {len(pdf_files)} ملفات PDF. سيتم الحفظ في: {output_path}")

# فتح الملف للكتابة المباشرة (Append mode) لتفريغ النص أولاً بأول
with open(output_path, "w", encoding="utf-8") as out_f:
    out_f.write(f"=== بدء استخراج النصوص لعدد {len(pdf_files)} ملفات ===\n\n")


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


# 4. معالجة الملفات والصفحات
with open(output_path, "a", encoding="utf-8") as out_f:
    for pdf_idx, pdf_path in enumerate(pdf_files):
        print(f"\n[+] جاري استخراج النصوص من الملف ({pdf_idx + 1}/{len(pdf_files)}): {pdf_path}")
        out_f.write(f"\n{'='*50}\n")
        out_f.write(f"=== الملف: {os.path.basename(pdf_path)} ===\n")
        out_f.write(f"{'='*50}\n\n")
        out_f.flush()

        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"[-] خطأ في فتح الملف {pdf_path}: {e}")
            out_f.write(f"[-] خطأ في فتح الملف: {e}\n\n")
            continue
            
        for page_num in range(len(doc)):
            print(f"  [>] معالجة الصفحة {page_num + 1} من {len(doc)}...")
            page = doc[page_num]
            
            # تحويل الصفحة إلى صورة بدقة عالية
            pix = page.get_pixmap(dpi=340)
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
            page_content = f"{page_header}\n{page_text}"
            
            # كتابة الصفحة مباشرة للملف لتسريع العملية وحفظ البيانات أولاً بأول
            out_f.write(page_content + "\n\n")
            out_f.flush()
            
        doc.close()

print(f"\n[+] تم الانتهاء بنجاح! حُفظت جميع النتائج في: {output_path}")