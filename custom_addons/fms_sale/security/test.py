import csv
from collections import Counter

with open('/home/oodo3/odoo16/custom_addons/fms_sale/security/ir.model.access.csv', mode='r') as file:
    reader = csv.DictReader(file)
    ids = [row['id'] for row in reader]

duplicate_ids = [item for item, count in Counter(ids).items() if count > 1]

print(f"Duplicate ids: {duplicate_ids}")
