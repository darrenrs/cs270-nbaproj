#!/usr/bin/python3
import pandas as pd
import math
from tqdm import tqdm

# Hyperparameters; see https://fivethirtyeight.com/features/how-we-calculate-nba-elo-ratings/
ELO_MEAN = 1500
ELO_RMEAN = 1505
ELO_RWEIGHT = 0.25
ELO_K = 20
ELO_HOMEADV = 100

MINIMUM_DATE_FOR_UNDERFLOW = (10, 15)

def get_date(d):
  year = d[:4]
  month = d[5:7]
  day = d[8:]
  
  return (int(year), int(month), int(day))

def elo_prob(a, b):
  return 1 / (1 + math.pow(10, (b - a) / 400))

def elo_change(p, a):
  return ELO_K * (a - p)

with open('bettingline_out.csv', 'r') as f:
  spread = pd.read_csv(f)
  spread = spread.drop('AwayTeam', axis=1)\
                 .drop('HomeTeam', axis=1)\
                 .drop('Date', axis=1)

with open('stats_out.csv', 'r') as f:
  stats = pd.read_csv(f)

df = pd.merge(stats, spread, how='left', on='InnerJoinCode')
df = df.drop('InnerJoinCode', axis=1)
df['ELO_AWAY'] = 0
df['ELO_HOME'] = 0

# generate ELO
# we start 3 years before testable/trainable data to build up accurate ELO (discard all rows between 2004-11-02 and 2007-10-29)
last_game_date = get_date(df['Date'][0])
team_elo = {}

for i in df["HomeTeam"].copy().drop_duplicates():
  team_elo[i] = ELO_MEAN

for i, current_game in tqdm(df.iterrows()):
  current_game_date = get_date(current_game['Date'])
  if current_game_date[1] > MINIMUM_DATE_FOR_UNDERFLOW[0] or (current_game_date[1] == MINIMUM_DATE_FOR_UNDERFLOW[0] and current_game_date[2] >= MINIMUM_DATE_FOR_UNDERFLOW[1]):
    if last_game_date[1] < MINIMUM_DATE_FOR_UNDERFLOW[0] or (last_game_date[1] == MINIMUM_DATE_FOR_UNDERFLOW[0] and last_game_date[2] < MINIMUM_DATE_FOR_UNDERFLOW[1]):
      for j in team_elo:
        team_elo[j] = (team_elo[j] * (1 - ELO_RWEIGHT)) + (ELO_RMEAN * ELO_RWEIGHT)

  last_game_date = current_game_date

  home_team = current_game['HomeTeam']
  away_team = current_game['AwayTeam']

  home_result = 0 if current_game['WL_HOME'] == 'L' else 1
  away_result = 0 if current_game['WL_AWAY'] == 'L' else 1

  home_elo = team_elo[home_team]
  away_elo = team_elo[away_team]

  elo_prob_home = elo_prob(home_elo + ELO_HOMEADV, away_elo)
  elo_prob_away = elo_prob(away_elo, home_elo + ELO_HOMEADV)

  home_elo += elo_change(elo_prob_home, home_result)
  away_elo += elo_change(elo_prob_away, away_result)
  
  team_elo[home_team] = home_elo
  team_elo[away_team] = away_elo

  df.at[i, 'ELO_HOME'] = home_elo
  df.at[i, 'ELO_AWAY'] = away_elo

df.to_csv('combined_out.csv', index=False)