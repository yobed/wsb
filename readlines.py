import pandas as pd
file_path = 'wsb_sub_processed.csv'
df = pd.read_csv(file_path)
print(df.head(20))
print(df.tail(20))
print(df.shape)
df = df['sentiment'].dropna()
print(df.head(20))
print(df.tail(20))
print(df.shape)


