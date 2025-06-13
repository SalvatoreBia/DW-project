import sqlite3
import pandas as pd
from datetime import datetime

def parse_attack_date(iyear, imonth, iday, separate=False):
    try:
        year = int(iyear)
        month = int(imonth) if imonth > 0 and not pd.isna(imonth) else 1
        day = int(iday) if iday > 0 and not pd.isna(iday) else 1
        return datetime(year, month, day).date() if not separate else (datetime(year, month, day).date(), month, year)
    except Exception as e:
        print(f"Errore parsing data: {iyear}-{imonth}-{iday} -> {e}")
        return None

def get_or_create(cursor, table, where_cols, insert_cols, values):
    where_clause = " AND ".join([f"{col}=?" for col in where_cols])
    select_query = f"SELECT id FROM {table} WHERE {where_clause}"
    cursor.execute(select_query, tuple(values[col] for col in where_cols))
    result = cursor.fetchone()
    if result:
        return result[0]
    insert_query = f"INSERT INTO {table} ({', '.join(insert_cols)}) VALUES ({', '.join(['?' for _ in insert_cols])})"
    cursor.execute(insert_query, tuple(values[col] for col in insert_cols))
    return cursor.lastrowid

ER_DUMP = 'er-dump.txt'
ER = 'er.sqlite'
STAR = 'star_schema.sqlite'
STAR_DUMP = 'star-schema.txt'
DATASET = 'gtd_filtered.csv'

conn = sqlite3.connect(ER, check_same_thread=False)
cursor = conn.cursor()

with open(ER_DUMP, 'r') as dump:
    statements = dump.read().strip().split('~')
    for st in statements:
        cursor.execute(st)
    conn.commit()

attack_query = """
INSERT INTO Attack (
    id, date, suicide, success, nkill, nwound, propvalue, propcomment, motive, summary,
    ransom, ransomamt, hostkidoutcome, group_id, target_id, location_id
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

df = pd.read_csv(DATASET, low_memory=False)
total_rows = len(df)
for i, row in enumerate(df.itertuples(), start=1):
    location_id = get_or_create(cursor, "Location",
        ['city', 'provstate', 'region', 'country'],
        ['city', 'provstate', 'region', 'country'],
        {
            'city': row.city,
            'provstate': row.provstate,
            'region': row.region_txt,
            'country': row.country_txt
        }
    )

    target_id = get_or_create(cursor, "Target",
        ['target_name', 'target_type'],
        ['target_name', 'target_type'],
        {
            'target_name': row.target1,
            'target_type': row.targtype1_txt
        }
    )

    weapon_id = get_or_create(cursor, "Weapon",
        ['weapon_name', 'weapon_category'],
        ['weapon_name', 'weapon_category'],
        {
            'weapon_name': row.weapsubtype1_txt,
            'weapon_category': row.weaptype1_txt
        }
    )

    groups_id = get_or_create(cursor, "Groups",
        ['group_name', 'religious_fanatic', 'weapon_id'],
        ['group_name', 'religious_fanatic', 'weapon_id'],
        {
            'group_name': row.gname,
            'religious_fanatic': row.religious_fanatic_group,
            'weapon_id': weapon_id
        }
    )

    attack_date = parse_attack_date(row.iyear, row.imonth, row.iday)

    cursor.execute(attack_query, (
        row.eventid,
        attack_date,
        row.suicide,
        row.success,
        row.nkill,
        row.nwound,
        row.propvalue,
        row.propcomment,
        row.motive,
        row.summary,
        row.ransom,
        row.ransomamt,
        row.hostkidoutcome_txt,
        groups_id,
        target_id,
        location_id
    ))

    conn.commit()
    progress = (i / total_rows) * 100
    print(f'Progress: {progress:.2f}%', end='\r')

conn.close()
conn = None

conn = sqlite3.connect(STAR, check_same_thread=False)
cursor = conn.cursor()

with open(STAR_DUMP, 'r') as dump:
    statements = dump.read().strip().split('~')
    for st in statements:
        cursor.execute(st)
    conn.commit()


for i, row in enumerate(df.itertuples(), start=1):
    attack_date, month, year = parse_attack_date(row.iyear, row.imonth, row.iday, separate=True)

    date_id = get_or_create(cursor, "Date",
        ['date', 'month', 'year'],
        ['date', 'month', 'year'],
        {
            'date': attack_date,
            'month': month,
            'year': year
        }
    )

    target_id = get_or_create(cursor, "Target",
        ['target_type'],
        ['target_type'],
        {
            'target_type': row.targtype1_txt
        }
    )

    weapon_id = get_or_create(cursor, "Weapon",
        ['weapon_name', 'weapon_category'],
        ['weapon_name', 'weapon_category'],
        {
            'weapon_name': row.weapsubtype1_txt,
            'weapon_category': row.weaptype1_txt
        }
    )

    suicide_id = get_or_create(cursor, "Suicide",
        ['suicide'],
        ['suicide'],
        {
            'suicide': row.suicide
        }
    )

    religious_id = get_or_create(cursor, "Religious",
        ['religious_fanatic'],
        ['religious_fanatic'],
        {
            'religious_fanatic': row.religious_fanatic_group
        }
    )

    location_id = get_or_create(cursor, "Location",
        ['city', 'provstate', 'region', 'country'],
        ['city', 'provstate', 'region', 'country'],
        {
            'city': row.city,
            'provstate': row.provstate,
            'region': row.region_txt,
            'country': row.country_txt
        }
    )

    group_id = get_or_create(cursor, "Groups",
        ['group_name'],
        ['group_name'],
        {
            'group_name': row.gname
        }
    )

    cursor.execute("""
        INSERT OR IGNORE INTO Attack (
            id, date_id, target_id, weapon_id, suicide_id, religious_fanatic_id,
            location_id, group_id, attack_type, success, nkill, nwound
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        row.eventid,
        date_id,
        target_id,
        weapon_id,
        suicide_id,
        religious_id,
        location_id,
        group_id,
        row.attacktype1_txt,
        row.success,
        row.nkill,
        row.nwound
    ))

    conn.commit()
    progress = (i / total_rows) * 100
    print(f'Progress: {progress:.2f}%', end='\r')

conn.close()
