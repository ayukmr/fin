from agents import Agent, Runner, function_tool
from typing import Optional, Literal, TypedDict

from . import compute

FACTS = {}
COMPUTED = {}

STATS = {
    'revenue',
    'cogs',
    'gross_profit',
    'r_and_d',
    's_and_m',
    'g_and_a',
    'operating_expenses',
    'operating_income',
    'depreciation',
    'amortization',
    'ebitda',
    'net_income',
    'diluted_shares',
    'eps_diluted',
    'operating_cash_flow',
    'capital_expenditures',
    'free_cash_flow'
}

def run(facts, computed):
    global FACTS, COMPUTED

    FACTS = facts
    COMPUTED = computed

    agent = Agent(
        name='Assistant',
        model='gpt-4o-mini',
        tools=[
            next_blanks,
            fill_blanks,
            all_fact_keys,
            search_fact_keys,
            get_fact_pts,
            # get_fact_pt,
            # get_computed_keys,
            get_computed,
            # get_computed_facts,
            # get_computed_fact,
            compute_values
        ]
    )

    prompt = """You are an AI assistant completing missing values in a financial dataset.

Repeat the following until there are no more missing values:
1. Call `next_blanks` to get a batch of missing entries (key, year, quarter).
2. For each entry, aggressively attempt to determine the correct value using the following order:
    - Always try `get_computed` first.
    - If seeked data is unavailable, immediately try `get_fact_pts`.
        - Call `search_fact_keys` to find relevant keys for this data source.
    - If neither works, make every reasonable effort to derive the value using known data via `compute_values`.
    - Only use '~' if all inference and derivation attempts have been thoroughly exhausted.
        - This will mark a blank as abandoned, meaning it will no longer be present in batches.
3. Once all entries have been processed, call `fill_blanks` with the list of (key, year, quarter, value) entries.
    - Fill in as many blanks as possible in each batch. Avoid individual updates.
4. Repeat this if the call to `next_blanks` gives more missing values.

Guidance:
- The keys are all case-sensitive.
- Using `all_fact_keys` to understand how the fact keys look is recommended. Then, `search_fact_keys` can be used.
    - Remember, `search_fact_keys` works on partial queries. It just checks if the query is within the keys returned.
    - If no keys are being returned when trying a `search_fact_keys` search, try changing the query to a different thing.
    - If all else doesn't work, just resort to using `all_fact_keys` in order to find a good key to use.
- `...fact...` and `...computed...` represent two different data sources.
    - The sources use DIFFERENT keys. Do NOT query `get_fact_pts` using a key from the computed data.
    - The normal facts are sourced from the SEC filing data.
    - The computed data is calculated directly based on the SEC filing data.
    - Both sources are trustworthy, but the computed is more condensed.
- Actively seek opportunities to compute values from existing data.
    - However, NEVER generate or hallucinate false values.
    - Only use the `compute` tool for doing math on values.
- Treat '~' as a last resort—derive or deduce whenever feasible.
- Try to do as much as possible at once, as you have a maximum number of steps.

Do not output anything. Just fill in the data using the tools provided."""

    try:
        res = Runner.run_sync(
            agent,
            prompt,
            max_turns=100
        )

        print(res.final_output)
    except Exception as e:
        print(f'Agent run failed: {e}')

    compute.write(COMPUTED)

class Blank(TypedDict):
    key: str
    year: int
    quarter: str

@function_tool
def next_blanks() -> list[Blank]:
    """Get the next 25 blank data points that are required to be filled."""

    blanks = []

    for fx, data in COMPUTED.items():
        diff = STATS - data.keys()

        if diff:
            key = next(iter(diff))

            blanks.append({
                'key': key,
                'year': int('20' + fx[:2]),
                'quarter': fx[2:]
            })

            if len(blanks) == 25:
                return blanks

    return blanks

class BlankEntry(TypedDict):
    key: str
    year: int
    quarter: str
    value: float | Literal['~']

@function_tool
def fill_blanks(values: list[BlankEntry]):
    """Fills multiple blank data points with multiple values.

    Args:
        values: The values to fill, as a list of {'year': <year>, 'quarter': <quarter>, 'value': <value>}."""

    for entry in values:
        fy = str(entry['year'])[2:]

        COMPUTED[fy + entry['quarter']][entry['key']] = entry['value']

@function_tool
def all_fact_keys() -> list[str]:
    """Get all he fact keys available for reading from the SEC filing data."""

    return list(FACTS['facts']['us-gaap'].keys())

@function_tool
def search_fact_keys(query: str) -> list[str]:
    """Search the fact keys available for reading from the SEC filing data."""

    keys = list(FACTS['facts']['us-gaap'].keys())

    return [k for k in keys if query.lower() in k.lower()]

@function_tool
def get_fact_pts(key: str) -> Optional[dict[str, float]]:
    """Read the points for a given fact key from the SEC filing data.

    Args:
        key: A valid fact key in the SEC filing data."""

    data = FACTS['facts']['us-gaap'].get(key)

    if not data:
        return

    facts = next(iter(data['units'].values()), None)

    if not facts:
        return

    points = {}

    for fact in facts:
        fy = fact['fy']
        fp = fact['fp']

        if fy and fp:
            points[str(fy)[2:] + fp] = fact['val']

    return points

@function_tool
def get_fact_pt(key: str, year: int, quarter: str) -> Optional[float]:
    """Read the fact for a given year and quarter from the SEC filing data.

    Args:
        key: A valid fact key in the SEC filing data.
        year: Requested year for the fact. Formatted as four digit integer, e.g. 2025.
        quarter: Requested financial quarter for the fact. One of: Q1, Q2, Q3, Q4."""

    data = FACTS['facts']['us-gaap'].get(key)

    if not data:
        return None

    points = next(iter(data['units'].values()), None)

    if not points:
        return None

    return next((
        d['val'] for d in points
        if d['fy'] == year and d['fp'] == quarter
    ), None)

@function_tool
def get_computed_keys() -> list[str]:
    """Get the fact keys available for each computed point."""

    return list(list(COMPUTED.values())[0].keys())

@function_tool
def get_computed() -> dict[str, dict[str, float]]:
    """Read facts for all years and quarters from the computed data."""

    return dict(COMPUTED)

@function_tool
def get_computed_facts(year: int, quarter: str) -> dict[str, float]:
    """Read all facts for a given year and quarter from the computed data.

    Args:
        year: Requested year for the computed data. Formatted as four digit integer, e.g. 2025.
        quarter: Requested financial quarter for the computed data. One of Q1, Q2, Q3, Q4."""

    fy = str(year)[2:]

    return COMPUTED[fy + quarter]

@function_tool
def get_computed_fact(key: str, year: int, quarter: str) -> float:
    """Read the fact for a given year and quarter from the computed data.

    Args:
        key: A valid fact key in the computed data.
        year: Requested year for the fact. Formatted as four digit integer, e.g. 2025.
        quarter: Requested financial quarter for the fact. One of: Q1, Q2, Q3, Q4."""

    fy = str(year)[2:]

    return COMPUTED[fy + quarter].get(key)

class Equation(TypedDict):
    lhs: float
    rhs: float
    op: Literal['+'] | Literal['-'] | Literal['*'] | Literal['/'] | Literal['%']

@function_tool
def compute_values(eqs: list[Equation]) -> list[float]:
    """Compute new values based a list of two given values and operations in the form of `lhs <op> rhs`.

    Args:
        eqs: List of classes with the shape of:
            lhs: The left hand side of the computation.
            rhs: The right hand side of the computation.
            op: The operation for the computation. One of: +, -, *, /, %."""

    res = []

    for eq in eqs:
        lhs = eq['lhs']
        rhs = eq['rhs']
        op = eq['op']

        match op:
            case '+':
                res.append(lhs + rhs)
            case '-':
                res.append(lhs - rhs)
            case '*':
                res.append(lhs * rhs)
            case '/':
                res.append(lhs / rhs)
            case '%':
                res.append(lhs % rhs)
            case _:
                res.append(None)

    return res
