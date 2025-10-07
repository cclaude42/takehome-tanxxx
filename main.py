import pandas as pd

df = pd.read_json('sessions.json', lines=True)

print(df.head())

print(df.columns)

print(df.shape)

print(df.info())
