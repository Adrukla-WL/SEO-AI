"""
Export Service
Handles exporting data to Excel and XML formats.
"""

import io
import xml.etree.ElementTree as ET
import pandas as pd

def export_to_excel(data: list):
    """
    Converts list of dicts to Excel bytes with formatting.
    """
    df = pd.DataFrame(data)
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
        
        # Получаем объект openpyxl для форматирования
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        
        # Импортируем стили
        from openpyxl.styles import Alignment
        
        # Задаем ширину колонок и перенос текста
        for idx, column in enumerate(df.columns):
            col_letter = chr(65 + idx) # A, B, C...
            
            # Настраиваем ширину в зависимости от контента
            if column == "Text":
                worksheet.column_dimensions[col_letter].width = 60
            elif column in ["New Description", "Description"]:
                worksheet.column_dimensions[col_letter].width = 40
            else:
                worksheet.column_dimensions[col_letter].width = 20
                
            # Применяем перенос текста ко всей колонке (кроме заголовка - хотя можно и к нему)
            for cell in worksheet[col_letter]:
                cell.alignment = Alignment(wrap_text=True, vertical='top', horizontal='left')

    return output.getvalue()

def export_to_xml(data: list):
    """
    Converts list of dicts to simple XML bytes.
    Structure:
    <project>
      <row>
        <Title>...</Title>
        ...
      </row>
    </project>
    """
    root = ET.Element("project")

    for row in data:
        row_elem = ET.SubElement(root, "row")
        for k, v in row.items():
            # sanitation for xml tags (spaces to underscores)
            tag_name = str(k).replace(" ", "_").replace("/", "")
            child = ET.SubElement(row_elem, tag_name)
            child.text = str(v)

    # Pretty print? Minidom or just tostring
    tree = ET.ElementTree(root)
    output = io.BytesIO()
    tree.write(output, encoding='utf-8', xml_declaration=True)
    return output.getvalue()
