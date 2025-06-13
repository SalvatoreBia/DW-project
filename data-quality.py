import pandas as pd

df = pd.read_csv('gtd_filtered.csv')

cols_to_check = ['iyear', 'imonth', 'iday', 'nkill', 'nwound', 'success', 'suicide']

completeness = {}
validity = {}

valid_domains = {
    'imonth': list(range(0, 13)),
    'iday': list(range(0, 32)),
    'iyear': list(range(1970, 2026)),
    'success': [0, 1],
    'suicide': [0, 1]
}

for col in cols_to_check:
    completeness[col] = df[col].notnull().mean() * 100

    if col in valid_domains:
        validity[col] = df[col].isin(valid_domains[col]).mean() * 100
    elif col in ['nkill', 'nwound']:
        validity[col] = df[col].dropna().ge(0).mean() * 100
    else:
        validity[col] = '--'

quality_df = pd.DataFrame({
    'Completeness (%)': completeness,
    'Validity (%)': validity
}).round(2)

eventid_uniqueness = df['eventid'].nunique() / df['eventid'].notnull().sum() * 100
uniqueness_df = pd.DataFrame({
    'Column': ['eventid'],
    'Uniqueness (%)': [round(eventid_uniqueness, 2)]
})

print(quality_df)
print('\nUniqueness Summary:')
print(uniqueness_df)
