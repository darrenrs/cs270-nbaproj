#!/usr/bin/python3
import pandas as pd

with open('bettingline_out.csv', 'r') as f:
  spread = pd.read_csv(f)

with open('stats_out.csv', 'r') as f:
  stats = pd.read_csv(f)
  stats = stats.drop('AwayTeam', axis=1)\
               .drop('HomeTeam', axis=1)\
               .drop('Date', axis=1)

df = pd.merge(spread, stats, on='InnerJoinCode')
df = df.drop('InnerJoinCode', axis=1)
df.to_csv('combined_out.csv', index=False)