import sys
import json
import requests

from . import compute, agent

def main():
    if len(sys.argv) < 2:
        print('error: incorrect arguments')
        exit()

    if len(sys.argv) >= 3:
        headers = {'User-Agent': 'example@example.com'}

        data = requests.get(
            'https://www.sec.gov/files/company_tickers.json',
            headers=headers
        ).json()

        tickers = list(data.values())

        cik = next(
            (
                str(t['cik_str']).zfill(10)
                for t in tickers
                if t['ticker'] == sys.argv[2]
            ),
            None
        )

        if not cik:
            print('error: invalid ticker')
            exit()

        facts = requests.get(
            f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json',
            headers=headers
        ).json()
    else:
        with open('data.json') as f:
            facts = json.load(f)

    computed = compute.compute(facts)

    if sys.argv[1] == 'out':
        compute.write(computed)
    elif sys.argv[1] == 'agent':
        agent.run(facts, computed)
