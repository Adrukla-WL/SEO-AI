"""
Export Service
Handles exporting data to Excel and XML formats.
"""

import io
import xml.etree.ElementTree as ET
import pandas as pd

def export_to_excel(data: list):
    """
    Converts list of dicts to Excel bytes.
    """
    df = pd.DataFrame(data)
    output = io.BytesIO()
    # using openpyxl engine
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
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
