import sys
import json
import os
import openpyxl

def read_excel_list(filepath):
    """خواندن ستون اول فایل اکسل و برگرداندن یک لیست تمیز و یکتا."""
    if not os.path.exists(filepath):
        return []
    wb = openpyxl.load_workbook(filepath, read_only=True)
    ws = wb.active
    values = set()
    # اگر فایل‌های شما سرستون دارند، min_row=2 بگذارید، در غیر این‌صورت min_row=1
    for row in ws.iter_rows(min_row=1, min_col=1, max_col=1, values_only=True):
        val = row[0]
        if val is not None and str(val).strip():
            values.add(str(val).strip())
    wb.close()
    return sorted(values)

if len(sys.argv) < 2:
    print("❌ لطفاً نام کارخانه را وارد کنید.")
    print("مثال: python convert_excel_to_json.py \"کارخانه ۱\"")
    sys.exit(1)

factory_name = sys.argv[1]
base_data = os.path.join('data', factory_name)
output_dir = os.path.join('json_data', factory_name)
os.makedirs(output_dir, exist_ok=True)

# ========= CNC =========
cnc = {
    'product_names': read_excel_list(os.path.join(base_data, 'cnc', 'products.xlsx')),
    'part_sizes': read_excel_list(os.path.join(base_data, 'cnc', 'sizes.xlsx')),
    'machine_codes': read_excel_list(os.path.join(base_data, 'cnc', 'machines.xlsx')),
    'operation_stage_codes': read_excel_list(os.path.join(base_data, 'cnc', 'operations.xlsx')),
}
with open(os.path.join(output_dir, 'cnc_options.json'), 'w', encoding='utf-8') as f:
    json.dump(cnc, f, ensure_ascii=False, indent=2)

# ========= ManAll =========
manall = {
    'product_names': read_excel_list(os.path.join(base_data, 'manall', 'products.xlsx')),
    'machine_codes': read_excel_list(os.path.join(base_data, 'manall', 'machines.xlsx')),
    'operation_stage_codes': read_excel_list(os.path.join(base_data, 'manall', 'operations.xlsx')),
    'manual_titles': read_excel_list(os.path.join(base_data, 'manall', 'titles.xlsx')),
}
with open(os.path.join(output_dir, 'manall_options.json'), 'w', encoding='utf-8') as f:
    json.dump(manall, f, ensure_ascii=False, indent=2)

# ========= Stoppage =========
stoppage = {
    'machine_codes': read_excel_list(os.path.join(base_data, 'stoppage', 'machines.xlsx')),
    'stop_codes': read_excel_list(os.path.join(base_data, 'stoppage', 'stopcodes.xlsx')),
}
with open(os.path.join(output_dir, 'stoppage_options.json'), 'w', encoding='utf-8') as f:
    json.dump(stoppage, f, ensure_ascii=False, indent=2)

print(f"✅ فایل‌های JSON برای «{factory_name}» در پوشه {output_dir} ساخته شدند.")