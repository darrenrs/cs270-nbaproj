#!/usr/bin/python3
import pandas as pd
import numpy as np
import argparse
import math
from tqdm import tqdm

# Hyperparameters; see https://fivethirtyeight.com/features/how-we-calculate-nba-elo-ratings/
ELO_MEAN = 1500
ELO_RMEAN = 1505
ELO_RWEIGHT = 0.25
ELO_K = 20
ELO_HOMEADV = 100

# default value for rolling avg
ROLLING_AVG_LAST_X = [0.4, 0.3, 0.2, 0.1]

FEATURES = [
  'MIN',
  'PTS',
  'FGM',
  'FGA',
  'FG_PCT',
  'FG3M',
  'FG3A',
  'FG3_PCT',
  'FTM',
  'FTA',
  'FT_PCT',
  'OREB',
  'DREB',
  'REB',
  'AST',
  'STL',
  'BLK',
  'TOV',
  'PF',
  'PLUS_MINUS'
]
DROP_FINAL = [
  'MIN',
  'FGM',
  'FGA',
  'FG_PCT',
  'FG3M',
  'FG3A',
  'FG3_PCT',
  'FTM',
  'FTA',
  'FT_PCT',
  'OREB',
  'DREB',
  'REB',
  'AST',
  'STL',
  'BLK',
  'TOV',
  'PF',
  'PLUS_MINUS'
]
TEAM_CODES = [
  "ATL",
  "BOS",
  "BKN",
  "CHA",
  "CHI",
  "CLE",
  "DAL",
  "DEN",
  "DET",
  "GSW",
  "HOU",
  "IND",
  "LAC",
  "LAL",
  "MEM",
  "MIA",
  "MIL",
  "MIN",
  "NOP",
  "NYK",
  "OKC",
  "ORL",
  "PHI",
  "PHX",
  "POR",
  "SAC",
  "SAS",
  "TOR",
  "UTA",
  "WAS"
]

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

def weight_multi(v):
  return sum([x*y for x, y in zip(v, ROLLING_AVG_LAST_X)])

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('-w', nargs="+", type=float, default=ROLLING_AVG_LAST_X)
  args = parser.parse_args()
  
  # reverse because we process weights in a stack. Append to list at the end. Pop from beginning
  ROLLING_AVG_LAST_X = list(reversed(args.w))

  if sum(ROLLING_AVG_LAST_X) > 1+1e-6 or sum(ROLLING_AVG_LAST_X) < 1-1e-6:  # slight error due to floating point inaccuracies
    print("Sum of pre-game weights must be 1")
    exit(1)
  
  with open('bettingline_out.csv', 'r') as f:
    spread = pd.read_csv(f)
    spread = spread.drop('AwayTeam', axis=1)\
                  .drop('HomeTeam', axis=1)\
                  .drop('Date', axis=1)

  with open('stats_out.csv', 'r') as f:
    stats = pd.read_csv(f)

  df = pd.merge(stats, spread, how='left', on='InnerJoinCode')
  df = df.drop('InnerJoinCode', axis=1)
  df['HomeSpreadActual'] = np.nan
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

    df.at[i, 'HomeSpreadActual'] = current_game['PTS_AWAY'] - current_game['PTS_HOME']

  # generate rolling average of team performance
  for i in FEATURES:
    df[i+'_AWAY_RA'] = np.nan
    df[i+'_HOME_RA'] = np.nan

  memory = {}

  for i in TEAM_CODES:
    features = {}
    for j in FEATURES:
      features[j] = []
    memory[i] = features

  for i, current_game in tqdm(df.iterrows()):
    home_team = current_game['HomeTeam']
    away_team = current_game['AwayTeam']

    for j in FEATURES:
      memory[home_team][j].append( df.at[i, j+'_HOME'] )
      memory[away_team][j].append( df.at[i, j+'_AWAY'] )

      # pop excess
      if len(memory[home_team][j]) > len(ROLLING_AVG_LAST_X) + 1:
        memory[home_team][j].pop(0)

      if len(memory[away_team][j]) > len(ROLLING_AVG_LAST_X) + 1:
        memory[away_team][j].pop(0)
      
      # full length of stack obtained, add average weight
      if len(memory[home_team][j]) == len(ROLLING_AVG_LAST_X) + 1:
        df.at[i, j+'_HOME_RA'] = weight_multi(memory[home_team][j][:-1])

      if len(memory[away_team][j]) == len(ROLLING_AVG_LAST_X) + 1:
        df.at[i, j+'_AWAY_RA'] = weight_multi(memory[away_team][j][:-1])

  df = df.drop([x+'_AWAY' for x in DROP_FINAL], axis=1)
  df = df.drop([x+'_HOME' for x in DROP_FINAL], axis=1)
  df['HomeSpreadCorrectDirection'] = df['HomeSpreadActual'] > df['HomeSpread']
  df['HomeSpreadCorrectDirection'] = df['HomeSpreadCorrectDirection'].astype(int)
  
  df.to_csv('combined_out.csv', index=False)

  print("== ELO Sorted ==")
  for k, v in sorted(team_elo.items(), key=lambda x: x[1], reverse=True):
    print(k, round(v))