#!/usr/bin/env python3
"""Merge researched business phone numbers into calls-retailcrm.json.

Usage: python3 merge_phones.py results.json
where results.json is [[id, "(xxx) xxx-xxxx", "source note"], ...]
Only fills rows that are currently missing a phone. Never overwrites existing data.
Appends the source note to the row's note field so agents can see where it came from.
"""
import json, re, sys

def has_phone(v):
    return bool(v) and len(re.sub(r'\D', '', str(v))) >= 10

def main(path):
    results = json.load(open(path))
    d = json.load(open('calls-retailcrm.json'))
    by_id = {r[0]: r for r in d['contacts']}
    filled = skipped = 0
    for item in results:
        cid, phone, src = (list(item) + ['', ''])[:3]
        row = by_id.get(int(cid))
        if not row or not has_phone(phone):
            skipped += 1
            continue
        if has_phone(row[2]):          # never overwrite a real number
            skipped += 1
            continue
        row[2] = phone
        if src:
            row[5] = (row[5] + ' · phone: ' + src).strip(' ·')
        filled += 1
    json.dump(d, open('calls-retailcrm.json', 'w'), indent=0)
    total = sum(1 for r in d['contacts'] if has_phone(r[2]))
    print(f'filled {filled}, skipped {skipped} | CRM rows with phone now: {total}/{len(d["contacts"])}')

if __name__ == '__main__':
    main(sys.argv[1])
