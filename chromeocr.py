import os
import subprocess
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import pyautogui
import pyperclip


def copy_paste_via_hotkeys():
    root = tk.Tk()
    root.withdraw()

    pdf_path = filedialog.askopenfilename(
        title="اختر ملف PDF", filetypes=[("PDF Files", "*.pdf")]
    )
    if not pdf_path:
        return

    try:
        # 1. فتح ملف الـ PDF باستخدام متصفح كروم الافتراضي للجهاز مباشرة
        # (سيفتح متصفحك الشخصي بكامل ميزاته)
        os.startfile(pdf_path)

        # الانتظار حتى يفتح المتصفح ويحمل الملف ويقوم بـ الـ OCR (تعديل حسب حجم الملف)
        time.sleep(7)

        # 2. الضغط داخل نافذة كروم للتأكد من أنها نشطة
        pyautogui.click(x=500, y=500)
        time.sleep(0.5)

        # 3. محاكاة اختصار "تحديد الكل" Ctrl + A
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.5)

        # 4. محاكاة اختصار "نسخ" Ctrl + C
        pyautogui.hotkey("ctrl", "c")
        time.sleep(1)  # وقت قصير لضمان النسخ في الحافظة

        # 5. جلب النص المنسوخ من الحافظة (Clipboard) عبر مكتبة pyperclip
        text_copied = pyperclip.paste()

        if not text_copied.strip():
            messagebox.showwarning(
                "تنبيه", "لم يتم نسخ أي نص، قد يكون المتصفح لم يحدد النص بعد."
            )
            return

        # 6. حفظ النص مباشرة في ملف على سطح المكتب
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        output_file_path = os.path.join(desktop_path, "copied_text.txt")

        with open(output_file_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(text_copied)

        messagebox.showinfo(
            "نجاح", f"تم نسخ النص وحفظه بنجاح على سطح المكتب:\n{output_file_path}"
        )

    except Exception as e:
        messagebox.showerror("خطأ", str(e))


if __name__ == "__main__":
    copy_paste_via_hotkeys()