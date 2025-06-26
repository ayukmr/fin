import sys
import json
import requests

from . import compute, agent

def main():
    if len(sys.argv) < 2:
        print('error: incorrect arguments')
        exit()

    if len(sys.argv) >= 3:
        facts = requests.get(
            f'https://data.sec.gov/api/xbrl/companyfacts/CIK{sys.argv[2]}.json',
            headers={'User-Agent': '-'}
        ).json()
    else:
        with open('data.json') as f:
            facts = json.load(f)

    computed = compute.compute(facts)

    if sys.argv[1] == 'out':
        compute.write(computed)
    elif sys.argv[1] == 'agent':
        agent.run(facts, computed)
