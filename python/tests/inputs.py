"""CONFIG: illustrative hand fixtures and expected independent results."""

from pathlib import Path

from credit_pack.config import C

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "companyfacts.json"
CRE_FIXTURE = {"noi": 1e6, "cap_rate": .06, "ltv_limit": .75, "dscr_min": 1.25,
               "annual_rate": .06, "amortization_years": 30, "debt_yield_min": .09}
CRE_EXPECTED = {C.VALUE: 16666666.6666667, C.DEBT_CONSTANT: .07194606301833083,
                C.LTV_LOAN: 12500000, C.DSCR_LOAN: 11119440.959488936,
                C.YIELD_LOAN: 11111111.11111111, C.LOAN: 11111111.11111111}
SUPERVISORY_CASES = (("construction_commercial_multifamily", .82, True),
                     ("improved_property", .80, False),
                     ("owner_occupied_1_4_home_equity", .99, False),
                     ("construction_commercial_multifamily", .80, False))
BALANCE_FIXTURE = (5e6, 4.2e6, .5e6)
BALANCE_SHORTFALL = .3e6
DRAW_APPROVED = 1e6
DRAW_EXPECTED = .9e6
AR_FIXTURE = (
    {C.CUSTOMER: "A", C.CURRENT: 40, C.AGE31: 0, C.AGE61: 0, C.AGE90: 60},
    {C.CUSTOMER: "B", C.CURRENT: 400, C.AGE31: 0, C.AGE61: 0, C.AGE90: 0},
    {C.CUSTOMER: "C", C.CURRENT: 120, C.AGE31: 0, C.AGE61: 0, C.AGE90: 0},
    {C.CUSTOMER: "D", C.CURRENT: 100, C.AGE31: 0, C.AGE61: 0, C.AGE90: 0},
    {C.CUSTOMER: "E", C.CURRENT: 100, C.AGE31: 0, C.AGE61: 0, C.AGE90: 0},
    {C.CUSTOMER: "F", C.CURRENT: 80, C.AGE31: 0, C.AGE61: 0, C.AGE90: 0},
    {C.CUSTOMER: "G", C.CURRENT: 100, C.AGE31: 0, C.AGE61: 0, C.AGE90: 0},
)
INV_FIXTURE = ({C.CATEGORY: "goods", C.COST: 200, C.NOLV: 80, C.ELIGIBLE: True},)
CERT_COMMITMENT = 1000
CERT_OUTSTANDING = 400
CERT_RESERVES = 50
CERT_FCCR = 1.0
CERT_EXPECTED = {C.ELIGIBLE_AR: 680, C.AR_ADVANCE: 578, C.INVENTORY_ADVANCE: 68,
                 C.BASE: 646, C.AVAILABILITY: 196, C.CONCENTRATION_EXCESS: 220}
SPRINGING_CASES = ((99.99, True), (100, False), (100.01, False), (-1, True))
COVENANT_DEBT = 300
COVENANT_EBITDA = 100
COVENANT_LEVERAGE = 3.0
COVENANT_CUSHION = 1 - 300 / 350
RATING_FINANCIAL = {C.LEVERAGE: 2.0, C.COVERAGE: 5.0, C.REVENUE: 1e9,
                    C.MARGIN_STABILITY: .02, C.CURRENT_RATIO: 1.5, C.EBITDA: 1e8}
LEVERAGE_GRID = (0, .5, 1, 1.5, 2, 2.5, 3, 3.5, 4.5, 6, 8)
FIXTURE_REVENUE = 1e6
FIXTURE_YEAR = 2025
FIXTURE_END = "2025-12-31"
INVALID_FACT_VALUE = 1e15
INVALID_FACT_FORMS = ("10-Q", "8-K", "10-K/A")
INVALID_FISCAL_PERIODS = ("Q1", "Q4")
INVALID_END = "2025-11-30"
INVALID_FILED = "2027-01-01"
FIXTURE_URL = "https://data.sec.gov/test"
FIXTURE_UA = "UnitTest Research qa@unit-test.invalid"
FIXTURE_CIKS = {"HAS": 46080, "WHR": 106640, "KSS": 885639}
DOUBLED_CUSTOMER = "A"
FILTER_CUSTOMER = "B"
RUNTIME_COLUMNS = (C.LOAN, C.VALUE, C.LTV_LOAN, C.DSCR_LOAN, C.YIELD_LOAN,
                   C.DEBT_CONSTANT, C.DSCR, C.STRESS_DSCR, C.LTV, C.SUPERVISORY_FLAG)
