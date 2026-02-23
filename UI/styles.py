"""
styles.py

"""

import os
import sys

def get_resource_path(relative_path):
    
    if hasattr(sys, "_MEIPASS"):
        base_path = getattr(sys, "_MEIPASS")
    else:
        
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path).replace("\\", "/")


ICON_CLOSED_PATH = get_resource_path("UI/arrowright.svg")
ICON_OPEN_PATH = get_resource_path("UI/arrowdown.svg")

STYLE_TEMPLATE = """
/* ================== ================== */
QMainWindow {{
    background-color: #1A1A1A;
}}

/* ================== TreeWidget ================== */
QTreeWidget {{
    background-color: #242424;
    border: none;
    color: #EEE;
    font-size: {font_size}px;
    outline: none;
}}

QTreeWidget::item {{
    padding: {padding}px;
    border-bottom: 1px solid #2D2D2D;
    min-height: {item_height}px;
}}

QTreeWidget::item:selected,
QTreeWidget::item:selected:active,
QTreeWidget::item:selected:!active {{
    background-color: #333333;
}}

/* ==================  ================== */

QTreeView::branch {{
    background: transparent;
    border-image: none;
    image: none;
    width: {branch_size}px;
    height: {branch_size}px;
}}


QTreeView::branch:has-children:closed {{
    image: url('{branch_closed}');
}}

QTreeView::branch:has-children:open {{
    image: url('{branch_open}');
}}


QHeaderView::section {{
    background-color: #2D2D2D;
    color: white;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #333;
    font-size: {font_size}px;
}}

QCheckBox {{
    background: transparent;
}}

QCheckBox::indicator {{
    width: {check_size}px;
    height: {check_size}px;
    border: 2px solid #555;
    border-radius: 4px;
}}

QCheckBox::indicator:checked {{
    background-color: #0078D4;
    border: 2px solid #0078D4;
}}

QPushButton {{
    background-color: #3A3A3A;
    color: white;
    border-radius: 4px;
    padding: {btn_v_padding}px {btn_h_padding}px;
    font-weight: bold;
    font-size: {font_size}px;
}}

QPushButton:hover {{
    background-color: #4A4A4A;
}}

#btn_delete {{
    background-color: #7D0000;
}}

#btn_delete:hover {{
    background-color: #C5000A;
}}

#PathBar {{
    background-color: #242424;
    border-radius: 6px;
    padding: 10px;
}}

#PathLabel {{
    color: #AAA;
    font-size: {small_font}px;
}}

QLineEdit {{
    padding: {btn_v_padding}px;
    background-color: #2D2D2D;
    color: white;
    border: 1px solid #444;
    border-radius: 5px;
    font-size: {font_size}px;
}}

QScrollBar:vertical {{
    background: #1A1A1A;
    width: {scroll_width}px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: #4F4F4F;
    min-height: 30px;
    border-radius: {scroll_radius}px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background: #666666;
}}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
}}
"""
