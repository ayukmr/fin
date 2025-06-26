import csv
from collections import defaultdict, Counter

def compute(data):
    points = gen_points(data)

    add_q4(points)
    compute_higher_stats(points)

    return points

def gen_points(data):
    stats = {
        'revenue': 'RevenueFromContractWithCustomerExcludingAssessedTax',
        'cogs':    'CostOfRevenue',

        'r_and_d': 'ResearchAndDevelopmentExpense',
        's_and_m': 'SellingAndMarketingExpense',
        'g_and_a': 'GeneralAndAdministrativeExpense',

        'operating_income': 'OperatingIncomeLoss',

        'depreciation': 'Depreciation',
        'd_and_a':      'DepreciationDepletionAndAmortization',

        'net_income': 'NetIncomeLoss',

        'diluted_shares': ('WeightedAverageNumberOfDilutedSharesOutstanding', 'shares'),
        'eps_diluted':    ('EarningsPerShareDiluted', 'USD/shares'),

        'operating_cash_flow':  'NetCashProvidedByUsedInOperatingActivities',
        'capital_expenditures': 'PaymentsToAcquirePropertyPlantAndEquipment'
    }

    points = defaultdict(dict)

    for stat, v in stats.items():
        fact_pts = []

        if type(v) == tuple:
            key, unit = v
            fact_pts = get_fact_pts(data, key, unit=unit)
        else:
            fact_pts = get_fact_pts(data, v)

        for fact in fact_pts:
            fy = fact['fy']
            fp = fact['fp']

            if fy and fp:
                points[str(fy)[2:] + fp][stat] = fact['val']

    return points

def add_q4(points):
    no_add = {
        'd_and_a',
        'diluted_shares',
        'eps_diluted',
        'operating_cash_flow',
        'capital_expenditures',
        'free_cash_flow'
    }

    for fx, data in list(points.items()):
        if fx[2:] == 'FY':
            other = [d for f, d in points.items() if f[2:] != 'FY' and f[:2] == fx[:2]]
            summed = sum([Counter(d) for d in other], Counter())

            points[fx[:2] + 'Q4'] = {
                k: data[k] if k in no_add else data[k] - summed[k]
                for k in data
            }

            del points[fx]

def compute_higher_stats(points):
    for data in points.values():
        if {'revenue', 'cogs'} <= data.keys():
            data['gross_profit'] = data['revenue'] - data['cogs']

        if {'r_and_d', 's_and_m', 'g_and_a'} <= data.keys():
            data['operating_expenses'] = data['r_and_d'] + data['s_and_m'] + data['g_and_a']

        if {'d_and_a', 'depreciation'} <= data.keys():
            data['amortization'] = data['d_and_a'] - data['depreciation']

        if {'operating_income', 'depreciation', 'amortization'} <= data.keys():
            data['ebitda'] = data['operating_income'] + data['depreciation'] + data['amortization']

        if {'operating_cash_flow', 'capital_expenditures'} <= data.keys():
            data['free_cash_flow'] = data['operating_cash_flow'] - data['capital_expenditures']

def write(points):
    names = {
        'revenue': 'Revenue',
        'cogs':    'Cost of Goods Sold',

        'gross_profit': 'Gross Profits',

        'r_and_d': 'R&D',
        's_and_m': 'S&M',
        'g_and_a': 'G&A',

        'operating_expenses': 'Operating Expenses',
        'operating_income':   'Operating Income',

        'depreciation': 'Depreciation',
        'amortization': 'Amortization',

        'ebitda': 'EBITDA',

        'net_income': 'Net Income',

        'diluted_shares': 'Diluted Shares',
        'eps_diluted':    'Earning per FDS',

        'operating_cash_flow':  'Operating Cashflow',
        'capital_expenditures': 'Capital Expenditure',
        'free_cash_flow':       'Free Cashflow'
    }

    out = sorted(
        points.items(),
        key=lambda fd: (int(fd[0][:2]), int(fd[0][3])),
        reverse=True
    )

    years = [None] + [f for f, _ in out]
    rotated = [
        [names[key]] + [
            str(d[key]) if key in d else None
            for _, d in out
        ]
        for key in names.keys()
    ]

    with open('out.csv', 'w') as f:
        writer = csv.writer(f)

        writer.writerow(years)
        writer.writerows(rotated)

def get_fact_pts(data, key, unit='USD'):
    data = data['facts']['us-gaap'].get(key)

    if data:
        return data['units'][unit]
    else:
        return []
