import requests
from bs4 import BeautifulSoup
import json

url = "https://olympics.com/en/paris-2024/medals"
headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0',
    'Accept-Language': 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7'
}

response = requests.get(url, headers=headers)
if response.status_code == 200:
    soup = BeautifulSoup(response.text, 'html.parser')
    script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
    if script_tag:
        data = json.loads(script_tag.string)
        countries = data['props']['pageProps']['initialMedals']['medalStandings']['medalsTable']
        medal_table = [
            {
                'Country': country['organisation'],
                'Gold': next((medal['gold'] for medal in country['medalsNumber'] if medal['type'] == 'Total'), 0),
                'Silver': next((medal['silver'] for medal in country['medalsNumber'] if medal['type'] == 'Total'), 0),
                'Bronze': next((medal['bronze'] for medal in country['medalsNumber'] if medal['type'] == 'Total'), 0),
                'Total': next((medal['total'] for medal in country['medalsNumber'] if medal['type'] == 'Total'), 0)
            }
            for country in countries
        ]
        for entry in medal_table:
            print(entry)
else:
    print(f"Failed to retrieve data. HTTP Status code: {response.status_code}")
