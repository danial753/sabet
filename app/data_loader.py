import os
import openpyxl
from flask import current_app

def read_list_from_excel(folder, filename):
    filepath = os.path.join(current_app.root_path, '..', 'data', folder, filename)
    if not os.path.exists(filepath):
        return []

    wb = openpyxl.load_workbook(filepath, read_only=True)
    ws = wb.active
    values = set()
    # رد شدن از ردیف اول (سرستون)
    for row in ws.iter_rows(min_row=2, min_col=1, max_col=1, values_only=True):
        val = row[0]
        if val is not None and str(val).strip():
            values.add(str(val).strip())
    wb.close()
    return sorted(list(values))

def get_cnc_lists():
    return {
        'product_names': read_list_from_excel('cnc', 'products.xlsx'),
        'part_sizes': read_list_from_excel('cnc', 'sizes.xlsx'),
        'machine_codes': read_list_from_excel('cnc', 'machines.xlsx'),
        'operation_stage_codes': read_list_from_excel('cnc', 'operations.xlsx'),
    }

def get_manall_lists():
    return {
        'product_names': read_list_from_excel('manall', 'products.xlsx'),
        'machine_codes': read_list_from_excel('manall', 'machines.xlsx'),
        'operation_stage_codes': read_list_from_excel('manall', 'operations.xlsx'),
        'manual_titles': read_list_from_excel('manall', 'titles.xlsx'),
    }

def get_stoppage_lists():
    return {
        'machine_codes': read_list_from_excel('stoppage', 'machines.xlsx'),
        'stop_codes': read_list_from_excel('stoppage', 'stopcodes.xlsx'),
    }