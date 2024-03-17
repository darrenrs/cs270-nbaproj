#!/usr/bin/python3
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.stats.library.parameters import SeasonType
import pandas as pd
from tqdm import tqdm

# REQUIRED format for dates; split into segments because of 30k response limit
DATES = [
  ('01/01/2018', '01/16/2023'),
  ('01/01/2013', '12/31/2017'),
  ('10/30/2007', '12/31/2012')
]
PROPS = [
  'WL',
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

def modern_team_id(team_id):
  if team_id == 'NOH':
    return 'NOP'
  elif team_id == 'NJN':
    return 'BKN'
  elif team_id == 'SEA':
    return 'OKC'

  return team_id

if __name__ == "__main__":
  primary_df = pd.DataFrame()
  
  for i in DATES:
    all_games = leaguegamefinder.LeagueGameFinder(date_from_nullable=i[0],
                                                  date_to_nullable=i[1],
                                                  league_id_nullable='00').get_data_frames()[0]

    all_games['SEASON_ID_TYPE'] = all_games['SEASON_ID'].str[0]
    rs_games = all_games.loc[(all_games['SEASON_ID_TYPE'] == '2') | (all_games['SEASON_ID_TYPE'] == '4') | (all_games['SEASON_ID_TYPE'] == '5')]

    primary_df = pd.concat([primary_df, rs_games], ignore_index=True)
  
  primary_df['IS_HOME_TEAM'] = primary_df.apply(lambda r: 0 if '@' in r['MATCHUP'] else 1, axis=1)
  primary_df.sort_values('GAME_ID', inplace=True)
  combined = []

  for i in tqdm(range(0, primary_df.shape[0], 2)):
    x = primary_df.iloc[i:i+2, :].copy()
    x.sort_values('IS_HOME_TEAM', inplace=True)
    
    away_row = x.iloc[0]
    home_row = x.iloc[1]
    
    json_obj = {"AwayTeam": modern_team_id(away_row["TEAM_ABBREVIATION"]),
                "HomeTeam": modern_team_id(home_row["TEAM_ABBREVIATION"]),
                "Date": away_row["GAME_DATE"],
                "InnerJoinCode": f'{modern_team_id(away_row["TEAM_ABBREVIATION"])}{modern_team_id(home_row["TEAM_ABBREVIATION"])}{away_row["GAME_DATE"].replace("-", "")}',
                }
    
    for j, n in enumerate(['AWAY', 'HOME']):
      for k in PROPS:
        json_obj[f"{k}_{n}"] = x.iloc[j][k]
    
    combined.append(json_obj)

  all_data_df = pd.DataFrame(combined)
  all_data_df.sort_values('Date', inplace=True)
  all_data_df.to_csv('stats_out.csv', index=False)