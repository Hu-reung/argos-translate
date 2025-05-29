
#!/usr/bin/env python
# coding: utf-8

import PyPDF2
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTFigure
import pdfplumber
from PIL import Image
from pdf2image import convert_from_path
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
    format_per_line = list(set(line_formats))
    return (line_text, format_per_line)

def extract_table(pdf_path, page_num, table_num):
    pdf = pdfplumber.open(pdf_path)
    table_page = pdf.pages[page_num]
    table = table_page.extract_tables()[table_num]
    return table

def table_converter(table, caption=""):
    return f"(논문 표 참고) {caption}"

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
    poppler_path = r"C:\Users\학교계정_김현송\Desktop\poppler-24.08.0\Library\bin"
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    pages = convert_from_path(pdf_path, poppler_path=poppler_path)
    all_text = ""
    for idx, image in enumerate(pages):
        image_file = f"ocr_page_{idx}.png"
        image.save(image_file, 'PNG')
        ocr_text = pytesseract.image_to_string(image, lang='eng')
        all_text += f"\n==== OCR_Page_{idx} ====\n{ocr_text}\n"
        os.remove(image_file)
    return all_text

def extract_pdf_text(pdf_path):
    pdfFileObj = open(pdf_path, 'rb')
    pdfReaded = PyPDF2.PdfReader(pdfFileObj)
    text_per_page = {}

    for pagenum, page in enumerate(extract_pages(pdf_path)):
        pageObj = pdfReaded.pages[pagenum]
        page_text, line_format, text_from_tables, page_content = [], [], [], []
        table_in_page = -1
        pdf = pdfplumber.open(pdf_path)
        page_tables = pdf.pages[pagenum]
        tables = page_tables.find_tables()
        if len(tables) != 0:
            table_in_page = 0
        for table_num in range(len(tables)):
            table = extract_table(pdf_path, pagenum, table_num)
            table_string = table_converter(table, caption=f"Table {table_num + 1}")
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
                    (line_text, format_per_line) = text_extraction(element)
                    if 'Fig.' in line_text or 'Figure' in line_text:
                        page_content.append("[그림 설명] " + line_text.strip())
                    else:
                        page_content.append(line_text)
                    page_text.append(line_text)
                    line_format.append(format_per_line)
                elif isinstance(element, LTFigure):
                    image_caption = "[이미지는 본문 참조]\n"
                    if i+1 < len(page_elements):
                        next_element = page_elements[i+1][1]
                        if isinstance(next_element, LTTextContainer):
                            caption_text, _ = text_extraction(next_element)
                            if 'Fig.' in caption_text or 'Figure' in caption_text:
                                image_caption += f"{caption_text.strip()}\n"
                    page_content.append(image_caption)
                    page_text.append(image_caption)
                    line_format.append('image')

        dctkey = 'Page_' + str(pagenum)
        text_per_page[dctkey] = [page_text, line_format, [], text_from_tables, page_content]

    pdfFileObj.close()
    return text_per_page

def get_extracted_text(text_per_page):
    result = ""
    for page_key in sorted(text_per_page.keys(), key=lambda x: int(x.split('_')[1])):
        page_num = page_key.split('_')[1]
        page_content = ''.join(text_per_page[page_key][4])
        result += f"\n\n===== Page {int(page_num)+1} =====\n{page_content}"
    return result

pdf_path = 'test_eng_treatise.pdf'
text_per_page = extract_pdf_text(pdf_path)
extracted_text = get_extracted_text(text_per_page)

with open("extracted_text.txt", "w", encoding="utf-8") as f:
    f.write(extracted_text)

if all(len(text_per_page[page_key][4]) < 10 for page_key in text_per_page):
    ocr_result = ocr_entire_pdf(pdf_path)
    print(ocr_result)
else:
    print("pdf 구조 기반 추출 성공, OCR 백업 생략.")
