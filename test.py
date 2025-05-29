import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
import fitz  # PyMuPDF
import argostranslate.package
import argostranslate.translate
import time
import os

from common import file_path, ocr_result1

# 모델 설치 (이미 설치했다면 주석 처리해도 됨)
model_path = r"C:\Users\hureu\Downloads\translate-en_ko-1_1.argosmodel"
if os.path.exists(model_path):
    argostranslate.package.install_from_path(model_path)

# 번역 모델 준비
installed_languages = argostranslate.translate.get_installed_languages()
from_lang = next((lang for lang in installed_languages if lang.code == "en"), None)
to_lang = next((lang for lang in installed_languages if lang.code == "ko"), None)

if not from_lang or not to_lang:
    messagebox.showerror("오류", "영어-한국어 번역 모델이 설치되지 않았습니다.")
    exit()

translation = from_lang.get_translation(to_lang)

translated_results = []

from pdf_reader_python import extracted_text

# PDF 열기 
def load_pdf():
    file_path = filedialog.askopenfilename(filetypes=[("PDF 파일", "*.pdf")])
    if not file_path:
        return
    try:
        input_textbox.delete("1.0", tk.END)
        input_textbox.insert(tk.END, extracted_text)
        messagebox.showinfo("성공", "PDF 텍스트 추출 완료!")
        
    except Exception as e:
        messagebox.showerror("오류", f"텍스트 추출 실패:\n{e}")

# 번역 함수
def translate_texts():
    input_text = input_textbox.get("1.0", tk.END).strip()
    if not input_text:
        messagebox.showwarning("경고", "번역할 내용이 없습니다.")
        return

    pages = input_text.split("===== Page ")
    output_textbox.delete("1.0", tk.END)
    translated_results.clear()

    for page in pages:
        if not page.strip():
            continue
        if page.startswith("1") or page[0].isdigit():
            try:
                split_idx = page.find("=====")
                page_num = page[:split_idx].strip()
                page_content = page[split_idx + 5:].strip()

                translated = translation.translate(page_content)
                result = f"===== Page {page_num} 번역 =====\n{translated}\n\n"
            except Exception as e:
                result = f"[Page {page_num} 번역 오류: {e}]\n\n"
        else:
            # 구분자 없이 그냥 들어온 첫 페이지
            try:
                translated = translation.translate(page.strip())
                result = f"===== 번역 결과 =====\n{translated}\n\n"
            except Exception as e:
                result = f"[번역 오류: {e}]\n\n"

        output_textbox.insert(tk.END, result)
        output_textbox.see(tk.END)
        translated_results.append(result)
        root.update()
        time.sleep(0.01)

    save_button.config(state=tk.NORMAL)

# ✅ 저장 함수
def save_results():
    if not translated_results:
        messagebox.showwarning("경고", "저장할 내용이 없습니다.")
        return
    file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                             filetypes=[("텍스트 파일", "*.txt"), ("모든 파일", "*.*")])
    if file_path:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(translated_results)
            messagebox.showinfo("성공", f"파일이 저장되었습니다:\n{file_path}")
        except Exception as e:
            messagebox.showerror("오류", f"파일 저장 중 오류:\n{e}")

# ✅ GUI 설정
root = tk.Tk()
root.title("PDF 영어 → 한국어 번역기")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

load_button = tk.Button(frame, text="PDF 열기", command=load_pdf)
load_button.grid(row=0, column=0, padx=5)

translate_button = tk.Button(frame, text="번역 시작", command=translate_texts)
translate_button.grid(row=0, column=1, padx=5)

save_button = tk.Button(frame, text="결과 저장", command=save_results, state=tk.DISABLED)
save_button.grid(row=0, column=2, padx=5)

tk.Label(root, text="PDF에서 불러온 원문:").pack()
input_textbox = scrolledtext.ScrolledText(root, width=100, height=12)
input_textbox.pack(padx=10, pady=5)

tk.Label(root, text="번역 결과:").pack()
output_textbox = scrolledtext.ScrolledText(root, width=100, height=15)
output_textbox.pack(padx=10, pady=5)

root.mainloop()
