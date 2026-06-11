import json
import os
from flask import current_app

def read_options_from_json(factory_name, filename):
    filepath = os.path.join(current_app.root_path, '..', 'json_data', factory_name, filename)
    if not os.path.exists(filepath):
        return {}
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_cnc_lists(factory_name):
    return read_options_from_json(factory_name, 'cnc_options.json')

def get_manall_lists(factory_name):
    return read_options_from_json(factory_name, 'manall_options.json')

def get_stoppage_lists(factory_name):
    return read_options_from_json(factory_name, 'stoppage_options.json')