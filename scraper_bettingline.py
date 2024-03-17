#!/usr/bin/python3
# Note: this doesn't work on campus because BYU has it blocked as a gambling website. Must use VPN, cellular data, or off-campus Wi-Fi
import requests
import pandas as pd
import numpy as np

TEAM_CODES = {
  "Atlanta": "ATL",
  "Boston": "BOS",
  "Brooklyn": "BKN",
  "Charlotte": "CHA",
  "Chicago": "CHI",
  "Cleveland": "CLE",
  "Dallas": "DAL",
  "Denver": "DEN",
  "Detroit": "DET",
  "GoldenState": "GSW",
  "Houston": "HOU",
  "Indiana": "IND",
  "LAClippers": "LAC",
  "LALakers": "LAL",
  "Memphis": "MEM",
  "Miami": "MIA",
  "Milwaukee": "MIL",
  "Minnesota": "MIN",
  "NewJersey": "BKN",
  "NewOrleans": "NOP",
  "NewYork": "NYK",
  "OklahomaCity": "OKC",
  "Orlando": "ORL",
  "Philadelphia": "PHI",
  "Phoenix": "PHX",
  "Portland": "POR",
  "Sacramento": "SAC",
  "SanAntonio": "SAS",
  "Seattle": "OKC",
  "Toronto": "TOR",
  "Utah": "UTA",
  "Washington": "WAS"
}

MINIMUM_DATE_FOR_UNDERFLOW = (10, 15)
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
BASE_URL = 'https://www.sportsbookreviewsonline.com/scoresoddsarchives/nba-odds-$YL-$YH/'
BASE_YEAR = 2007
MAX_YEAR = 2022

def get_team_code(team_name):
  return TEAM_CODES[team_name]

def get_date(date_string, season_base_year):
  day = int(date_string[-2:])
  month = int(date_string[:-2])
  year = season_base_year

  if month < MINIMUM_DATE_FOR_UNDERFLOW[0] or (month == MINIMUM_DATE_FOR_UNDERFLOW[0] and day < MINIMUM_DATE_FOR_UNDERFLOW[1]):
    year += 1
  
  return f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"

if __name__ == "__main__":
  all_data = []
  urls = [BASE_URL.replace('$YL', str(i)).replace('$YH', str(i+1)[-2:]) for i in range(BASE_YEAR, MAX_YEAR+1)]
  
  for n, i in enumerate(urls):
    r = requests.get(i, headers={
      'User-agent': USER_AGENT
    }).text
    
    # fix header row
    df = pd.read_html(r)[0]
    df.columns = df.iloc[0]
    df = df[1:]

    # tiebreaker string
    df["Close"] = df["Close"].replace('pk', '0').replace('PK', '0')
    df["Close"] = df["Close"].astype(float)

    for i in range(0, df.shape[0], 2):
      x = df.iloc[i:i+2, :]
      json_obj = {}
      json_obj["AwayTeam"] = get_team_code(x["Team"].iloc[0].replace(' ', ''))
      json_obj["HomeTeam"] = get_team_code(x["Team"].iloc[1].replace(' ', ''))
      json_obj["Date"] = get_date(x["Date"].iloc[0], BASE_YEAR+n)

      # if [0]=0, then home favored, else if [0]=1 then away favored
      spread_attr_ord = np.argsort(x["Close"])
      spread_attr_coeff = spread_attr_ord.iloc[1]*2-1

      json_obj["HomeSpread"] = x["Close"].iloc[spread_attr_ord.iloc[0]] * spread_attr_coeff
      all_data.append(json_obj)
  
  all_data_df = pd.DataFrame(all_data)
  all_data_df['InnerJoinCode'] = all_data_df.apply(lambda r: f'{r["AwayTeam"]}{r["HomeTeam"]}{r["Date"].replace("-", "")}', axis=1)
  all_data_df.to_csv('bettingline_out.csv', index=False)