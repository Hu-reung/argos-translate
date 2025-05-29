#!/usr/bin/env python
# coding: utf-8

import PyPDF2
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTFigure
import pdfplumber
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
import os

def text_extraction(element):
    line_text = element.get_text()
    line_formats = []
    for text_line in element:
        if isinstance(text_line, LTTextContainer):
            for character in text_line:
                if isinstance(character, LTChar):
                    line_formats.append(character.fontname)
                    line_formats.append(character.size)
    return (line_text, list(set(line_formats)))

#표 참고 추출 방식 변경
def table_converter(table, pagenum=None, table_num=None):
    table_title_dict = {
        2: "논문 표 참고 - Table 1. Performance Comparison on DFDC Dataset.",
        3: "논문 표 참고 - Table 2. Model Performance on DeepFakeTIMIT Dataset.",
        3.1: "논문 표 참고 - Table 3. Performance Comparison."
    }
    return table_title_dict.get(pagenum + 1, f"(논문 표 참고 - Table {table_num + 1})")

def extract_table(pdf_path, page_num, table_num):
    with pdfplumber.open(pdf_path) as pdf:
        return pdf.pages[page_num].extract_tables()[table_num]

def is_element_inside_any_table(element, page, tables):
    x0, y0up, x1, y1up = element.bbox
    y0 = page.bbox[3] - y1up
    y1 = page.bbox[3] - y0up
    for table in tables:
        tx0, ty0, tx1, ty1 = table.bbox
        if tx0 <= x0 <= x1 <= tx1 and ty0 <= y0 <= y1 <= ty1:
            return True
    return False

def find_table_for_element(element, page, tables):
    x0, y0up, x1, y1up = element.bbox
    y0 = page.bbox[3] - y1up
    y1 = page.bbox[3] - y0up
    for i, table in enumerate(tables):
        tx0, ty0, tx1, ty1 = table.bbox
        if tx0 <= x0 <= x1 <= tx1 and ty0 <= y0 <= y1 <= ty1:
            return i
    return None

def ocr_entire_pdf(pdf_path):
    poppler_path = r"C:\\Users\\학교계정_김현송\\Desktop\\poppler-24.08.0\\Library\\bin"
    pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    pages = convert_from_path(pdf_path, poppler_path=poppler_path)
    all_text = ""
    for idx, image in enumerate(pages):
        image_file = f"ocr_page_{idx}.png"
        image.save(image_file, 'PNG')
        ocr_text = pytesseract.image_to_string(image, lang='eng')
        all_text += f"\n==== OCR_Page_{idx} ====\n{ocr_text}\n"
        os.remove(image_file)
    return all_text

pdf_path = 'test_eng_treatise.pdf'
pdfFileObj = open(pdf_path, 'rb')
pdfReaded = PyPDF2.PdfReader(pdfFileObj)

text_per_page = {}

for pagenum, page in enumerate(extract_pages(pdf_path)):
    pageObj = pdfReaded.pages[pagenum]
    page_text = []
    line_format = []
    text_from_tables = []
    page_content = []

    with pdfplumber.open(pdf_path) as pdf:
        tables = pdf.pages[pagenum].find_tables()
    table_in_page = 0 if tables else -1

    for table_num in range(len(tables)):
        table = extract_table(pdf_path, pagenum, table_num)
        table_string = table_converter(table, pagenum, table_num)
        text_from_tables.append(table_string)

    page_elements = [(element.y1, element) for element in page._objs]
    page_elements.sort(key=lambda a: a[0], reverse=True)

    for i, component in enumerate(page_elements):
        element = component[1]

        if table_in_page != -1 and is_element_inside_any_table(element, page, tables):
            table_found = find_table_for_element(element, page, tables)
            if table_found == table_in_page and table_found is not None:
                page_content.append(text_from_tables[table_in_page])
                page_text.append('table')
                line_format.append('table')
                table_in_page += 1
            continue

        if not is_element_inside_any_table(element, page, tables):
            if isinstance(element, LTTextContainer):
                line_text, format_per_line = text_extraction(element)
                if 'Fig.' in line_text or 'Figure' in line_text:
                    page_content.append("[그림 설명] " + line_text.strip())
                else:
                    page_content.append(line_text)
                page_text.append(line_text)
                line_format.append(format_per_line)
            elif isinstance(element, LTFigure):
                image_caption = "[이미지는 본문 참조]\n"
                if i + 1 < len(page_elements):
                    next_element = page_elements[i + 1][1]
                    if isinstance(next_element, LTTextContainer):
                        caption_text, _ = text_extraction(next_element)
                        if 'Fig.' in caption_text or 'Figure' in caption_text:
                            image_caption += f"{caption_text.strip()}\n"
                page_content.append(image_caption)
                page_text.append(image_caption)
                line_format.append('image')
                continue

    dctkey = 'Page_' + str(pagenum + 1)
    text_per_page[dctkey] = [page_text, line_format, [], text_from_tables, page_content]

pdfFileObj.close()

print("\n===== PDF 텍스트 추출 결과 =====\n")
for page_key in sorted(text_per_page.keys(), key=lambda x: int(x.split('_')[1])):
    print(f"{page_key}")
    print("-" * 50)
    print(''.join(text_per_page[page_key][4]))
    print("\n")

if all(len(text_per_page[page_key][4]) < 10 for page_key in text_per_page):
    print("\n===== 백업 텍스트 추출 =====\n")
    print(ocr_entire_pdf(pdf_path))
else:
    print("pdf 구조 기반 추출 성공, OCR 백업 생략.")
