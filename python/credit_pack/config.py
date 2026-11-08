"""All user-facing inputs and data column names. Policy inputs are illustrative."""

from pathlib import Path

# CONFIG: paths, sources, names, and illustrative model assumptions.
ROOT = Path(__file__).resolve().parents[2]
EXTENSION_README = ROOT / "docs" / "readme_extension.md"
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
WORKBOOK = ROOT / "excel" / "credit_pack.xlsx"
QA = ROOT / ".qa"
AUTHOR = "Yazad Madan"
SEED = 20261021
AS_OF = "2026-10-21"
LTV_SOURCE_CURRENT_THROUGH = "2026-10-19"
YEARS = 5
TICKERS = ("HAS", "WHR", "KSS")
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
SEC_API_URL = "https://www.sec.gov/search-filings/edgar-application-programming-interfaces"
SEC_ACCESS_URL = "https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data"
LTV_SOURCE = "https://www.ecfr.gov/current/title-12/chapter-II/subchapter-A/part-208/appendix-Appendix%20C%20to%20Part%20208"
SEC_USER_AGENT = "CreditMonitoringResearch contact=replace-with-your-email@example.com"
REQUEST_INTERVAL = 0.2
REQUEST_TIMEOUT = 30
ANNUAL_MIN_DAYS = 330
ANNUAL_MAX_DAYS = 380
FORM = "10-K"
FISCAL_PERIOD = "FY"
UNIT = "USD"
DEMO_YEARS = tuple(range(2021, 2026))
DAYS_IN_YEAR = 365
MONTHS_IN_YEAR = 12
DEMO_SOURCE = "SYNTHETIC illustrative companyfacts fixture, not SEC data"
REAL_SOURCE = "SEC companyfacts snapshot"


class C:
    """Stable names for financial data and output columns."""

    TICKER = "ticker"
    YEAR = "fiscal_year"
    END = "period_end"
    SOURCE = "source"
    METRIC = "metric"
    VALUE = "value"
    TAG = "tag"
    FLAGS = "flags"
    FILED = "filed"
    ACCESSION = "accession"
    START = "start"
    REVENUE = "revenue"
    COGS = "cogs"
    OP_INCOME = "operating_income"
    DA = "depreciation_amortization"
    INTEREST = "interest_expense"
    TAX = "cash_taxes"
    CASH = "cash"
    AR = "accounts_receivable"
    INVENTORY = "inventory"
    AP = "accounts_payable"
    DEBT_LONG = "long_term_debt"
    DEBT_CURRENT = "current_debt"
    DEBT_SHORT = "short_term_borrowings"
    DEBT = "total_debt"
    EQUITY = "equity"
    CFO = "cash_from_operations"
    CAPEX = "capex"
    CURRENT_ASSETS = "current_assets"
    CURRENT_LIABILITIES = "current_liabilities"
    EBITDA = "ebitda"
    LEVERAGE = "total_leverage"
    NET_LEVERAGE = "net_leverage"
    COVERAGE = "interest_coverage"
    FCCR = "fccr"
    PRINCIPAL = "scheduled_principal"
    CAPITALIZATION = "debt_to_capitalization"
    CURRENT_RATIO = "current_ratio"
    GROSS_MARGIN = "gross_margin"
    MARGIN = "ebitda_margin"
    MARGIN_STABILITY = "margin_stability"
    FCF_DEBT = "fcf_to_debt"
    DSO = "dso"
    DIO = "dio"
    DPO = "dpo"
    GRADE = "grade"
    PRIOR_GRADE = "prior_grade"
    CHANGE = "grade_change"
    PD = "pd"
    CLASSIFICATION = "classification"
    SCORE = "weighted_score"
    FACTOR_SCORE = "factor_score"
    FACTOR = "factor"
    WEIGHT = "weight"
    INDUSTRY_RISK = "industry_risk"
    MANAGEMENT = "management"
    POSITION = "market_position"
    POLICY = "financial_policy"
    LGD = "lgd"
    SENIORITY = "seniority"
    COLLATERAL = "collateral"
    FACILITY = "facility"
    COMMITMENT = "commitment"
    OUTSTANDING = "outstanding"
    REVOLVER = "revolver_commitment"
    TERM = "term_loan"
    PROPOSED_DEBT = "proposed_debt"
    MAX_LEVERAGE = "max_leverage"
    MIN_FCCR = "min_fccr"
    LEVERAGE_HEADROOM = "leverage_headroom_pct"
    FCCR_HEADROOM = "fccr_headroom_pct"
    CUSHION = "ebitda_cushion"
    BREAK_EVEN = "break_even_ebitda_decline"
    LEVERAGE_BREACH = "leverage_breach"
    FCCR_BREACH = "fccr_breach"
    BREACH = "covenant_breach"
    DOWN_REVENUE = "downside_revenue"
    DOWN_EBITDA = "downside_ebitda"
    DOWN_LEVERAGE = "downside_leverage"
    DOWN_FCCR = "downside_fccr"
    DOWN_BREACH = "downside_breach"
    REVENUE_STRESS = "downside_revenue_change"
    MARGIN_STRESS = "downside_margin_change"
    REVOLVER_UTILIZATION = "revolver_utilization"
    RECOMMENDATION = "recommendation"
    PROPERTY = "property"
    PROPERTY_TYPE = "property_type"
    CATEGORY = "category"
    QUANTITY = "units_or_sqft"
    RENT = "in_place_annual_rent"
    MARKET_RENT = "market_annual_rent"
    VACANCY = "vacancy_credit_loss"
    OTHER_INCOME = "other_income"
    OPEX = "operating_expenses"
    RESERVES = "reserves"
    PGI = "potential_gross_income"
    EGI = "effective_gross_income"
    NOI = "noi"
    CAP_RATE = "cap_rate"
    LTV_LIMIT = "ltv_limit"
    DSCR_MIN = "dscr_min"
    RATE = "annual_rate"
    AMORT_YEARS = "amortization_years"
    YIELD_MIN = "debt_yield_min"
    DEBT_CONSTANT = "debt_constant"
    LTV_LOAN = "ltv_loan"
    DSCR_LOAN = "dscr_loan"
    YIELD_LOAN = "debt_yield_loan"
    LOAN = "sized_loan"
    BINDING = "binding_constraint"
    LTV = "ltv"
    DSCR = "dscr"
    DEBT_YIELD = "debt_yield"
    STRESS_DSCR = "stressed_dscr"
    SUPERVISORY_LIMIT = "supervisory_ltv_limit"
    SUPERVISORY_FLAG = "supervisory_ltv_exception"
    LINE = "budget_line"
    MONTH = "month"
    BUDGET = "budget"
    COMPLETE = "inspector_pct_complete"
    REQUEST = "requested_draw"
    APPROVED = "approved_draw"
    RETAINAGE = "retainage"
    RETAINED = "retained_amount"
    FUNDED = "funded_draw"
    EQUITY_FUNDED = "equity_funded"
    LOAN_FUNDED = "loan_funded"
    CUM_APPROVED = "cumulative_approved"
    CUM_FUNDED = "cumulative_funded"
    CUM_EQUITY = "cumulative_equity"
    CUM_LOAN = "cumulative_loan"
    COST_COMPLETE = "cost_to_complete"
    UNDISBURSED = "undisbursed_loan"
    REMAINING_EQUITY = "remaining_required_equity"
    SHORTFALL = "balance_shortfall"
    EQUITY_CALL = "equity_call"
    CONTINGENCY_LEFT = "contingency_remaining"
    INTEREST_LEFT = "interest_reserve_remaining"
    INTEREST_REQUIRED = "interest_reserve_required"
    CUSTOMER = "customer"
    CURRENT = "current"
    AGE31 = "days_31_60"
    AGE61 = "days_61_90"
    AGE90 = "over_90"
    AFFILIATE = "affiliate"
    FOREIGN = "foreign"
    CONTRA = "contra"
    GROSS_AR = "gross_ar"
    CROSS_AGED = "cross_aged"
    PRE_CONCENTRATION = "pre_concentration_eligible"
    CONCENTRATION_EXCESS = "concentration_excess"
    ELIGIBLE_AR = "eligible_ar"
    INELIGIBLE_AR = "ineligible_ar"
    COST = "cost"
    NOLV = "nolv"
    ELIGIBLE = "eligible"
    ELIGIBLE_COST = "eligible_cost"
    ELIGIBLE_NOLV = "eligible_nolv"
    INVENTORY_ADVANCE = "inventory_advance"
    AR_ADVANCE = "ar_advance"
    BASE = "borrowing_base"
    AVAILABILITY = "excess_availability"
    SPRINGING = "springing_fccr_test"
    FCCR_TESTED = "fccr_tested"
    OPENING = "opening_outstanding"
    DRAW = "draw"
    PAYDOWN = "paydown"
    LOAN_ID = "loan_id"
    LOAN_TYPE = "loan_type"
    QUARTER = "quarter"
    INDUSTRY = "industry"
    BALANCE = "balance"
    WATCHLIST = "watchlist"
    TRIGGERS = "watchlist_triggers"
    WATCH_BALANCE = "watchlist_balance"
    WATCH_COUNT = "watchlist_count"
    LOAN_COUNT = "loan_count"
    SHARE = "balance_share"
    FROM_GRADE = "from_grade"
    TO_GRADE = "to_grade"
    COUNT = "count"
    PROBABILITY = "probability"


TAGS = {
    C.REVENUE: ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"),
    C.COGS: ("CostOfGoodsAndServicesSold", "CostOfRevenue"),
    C.OP_INCOME: ("OperatingIncomeLoss",),
    C.DA: ("DepreciationDepletionAndAmortization", "DepreciationAndAmortization"),
    C.INTEREST: ("InterestExpense", "InterestExpenseNonoperating"),
    C.TAX: ("IncomeTaxesPaidNet",),
    C.CASH: ("CashAndCashEquivalentsAtCarryingValue",),
    C.AR: ("AccountsReceivableNetCurrent", "AccountsNotesAndLoansReceivableNetCurrent"),
    C.INVENTORY: ("InventoryNet",), C.AP: ("AccountsPayableCurrent",),
    C.DEBT_LONG: ("LongTermDebtNoncurrent",),
    C.DEBT_CURRENT: ("LongTermDebtCurrent",),
    C.DEBT_SHORT: ("ShortTermBorrowings",), C.EQUITY: ("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
    C.CFO: ("NetCashProvidedByUsedInOperatingActivities",),
    C.CAPEX: ("PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"),
    C.CURRENT_ASSETS: ("AssetsCurrent",), C.CURRENT_LIABILITIES: ("LiabilitiesCurrent",),
}
INSTANT_METRICS = frozenset((C.CASH, C.AR, C.INVENTORY, C.AP, C.DEBT_LONG,
                           C.DEBT_CURRENT, C.DEBT_SHORT, C.EQUITY,
                           C.CURRENT_ASSETS, C.CURRENT_LIABILITIES))
DEBT_COMPONENTS = (C.DEBT_LONG, C.DEBT_CURRENT, C.DEBT_SHORT)
AGING_COLUMNS = (C.CURRENT, C.AGE31, C.AGE61, C.AGE90)

# All following numeric policy and scenario parameters are illustrative.
MAX_LEVERAGE = 3.5
MIN_FCCR = 1.25
REVOLVER_MULTIPLE = 0.75
TERM_MULTIPLE = 1.5
TERM_YEARS = 5
FACILITY_RATE = 0.075
REVOLVER_UTILIZATION = 0.5
REVENUE_STRESS = -0.15
MARGIN_STRESS = -0.03
APPROVE_MAX_GRADE = 5
CONDITIONAL_MAX_GRADE = 7
GRADE_FLOOR = 1
GRADE_CEILING = 10
QUANT_WEIGHT = 0.70
QUAL_WEIGHT = 0.30
QUANT_WEIGHTS = {C.LEVERAGE: .30, C.COVERAGE: .25, C.REVENUE: .15,
                 C.MARGIN_STABILITY: .15, C.CURRENT_RATIO: .15}
QUAL_WEIGHTS = {C.INDUSTRY_RISK: .30, C.MANAGEMENT: .25,
                C.POSITION: .25, C.POLICY: .20}
# Scores are one through ten; equal boundaries receive the better score.
BANDS = {
    C.LEVERAGE: (False, (.5, 1, 1.5, 2, 2.5, 3, 3.5, 4.5, 6)),
    C.COVERAGE: (True, (1, 1.25, 1.5, 2, 3, 4, 6, 8, 12)),
    C.REVENUE: (True, (50e6, 100e6, 250e6, 500e6, 1e9, 2e9, 5e9, 10e9, 20e9)),
    C.MARGIN_STABILITY: (False, (.005, .01, .015, .02, .025, .03, .04, .05, .08)),
    C.CURRENT_RATIO: (True, (.6, .8, 1, 1.1, 1.25, 1.5, 1.75, 2, 2.5)),
}
PD_SCALE = dict(enumerate((.0002, .0005, .001, .0025, .005, .01,
                          .025, .08, .25, 1.0), start=1))
CLASSIFICATION = {**dict.fromkeys(range(1, 7), "Pass"), 7: "Special Mention",
                  8: "Substandard", 9: "Doubtful", 10: "Loss"}
LGD_TABLE = {("senior", "cash"): .10, ("senior", "receivables_inventory"): .25,
             ("senior", "all_assets"): .40, ("senior", "unsecured"): .60,
             ("subordinated", "unsecured"): .80}
BORROWERS = {
    "HAS": {C.INDUSTRY: "Consumer products", "summary": "Illustrative branded consumer products scenario.",
            "base_revenue": 4.5e9, "base_margin": .18, "debt_multiple": 2.0,
            "growth": .025, "volatility": .008,
            "qualitative": {C.INDUSTRY_RISK: 4, C.MANAGEMENT: 3, C.POSITION: 3, C.POLICY: 4},
            "risk": "Demand seasonality and product concentration.",
            "mitigant": "Quarterly covenant review and liquidity reserve."},
    "WHR": {C.INDUSTRY: "Durable manufacturing", "summary": "Illustrative durable manufacturing scenario.",
            "base_revenue": 17e9, "base_margin": .10, "debt_multiple": 3.3,
            "growth": -.02, "volatility": .012,
            "qualitative": {C.INDUSTRY_RISK: 6, C.MANAGEMENT: 5, C.POSITION: 4, C.POLICY: 6},
            "risk": "Cyclical demand and input cost exposure.",
            "mitigant": "Amortization and limits on incremental debt."},
    "KSS": {C.INDUSTRY: "Retail", "summary": "Illustrative department store retail scenario.",
            "base_revenue": 15e9, "base_margin": .065, "debt_multiple": 5.0,
            "growth": -.04, "volatility": .015,
            "qualitative": {C.INDUSTRY_RISK: 8, C.MANAGEMENT: 6, C.POSITION: 7, C.POLICY: 7},
            "risk": "Sales contraction and inventory markdown risk.",
            "mitigant": "Collateral verification and a required debt reduction."},
}
DEMO_BALANCE_RATIOS = {C.COGS: .65, C.DA: .035, C.CASH: .07, C.AR: .10,
                      C.INVENTORY: .16, C.AP: .09, C.EQUITY: .35,
                      C.CAPEX: .025, C.CURRENT_ASSETS: .37, C.CURRENT_LIABILITIES: .22}
DEMO_INTEREST_RATE = .065
DEMO_CASH_TAX_RATE = .18
DEMO_CFO_CONVERSION = .70
DEMO_CURRENT_DEBT_SHARE = .10
DEMO_DEBT_TREND = .02

CRE_RATE = .06
CRE_AMORT_YEARS = 30
CRE_DSCR_MIN = 1.25
CRE_LTV_LIMIT = .75
CRE_YIELD_MIN = .09
CRE_RATE_STRESS = .02
CRE_NOI_STRESS = -.10
# Regulatory limits verified on eCFR, not illustrative policy assumptions.
SUPERVISORY_LTV = {"raw_land": .65, "land_development": .75,
                   "construction_commercial_multifamily": .80,
                   "construction_residential_1_4": .85, "improved_property": .85,
                   "owner_occupied_1_4_home_equity": None}
PROPERTIES = (
    {C.PROPERTY: "Maple Apartments", C.PROPERTY_TYPE: "multifamily", C.CATEGORY: "improved_property",
     C.QUANTITY: 120, C.RENT: 18000, C.MARKET_RENT: 19000, C.VACANCY: .06,
     C.OTHER_INCOME: 90000, C.OPEX: 800000, C.RESERVES: 60000, C.CAP_RATE: .06},
    {C.PROPERTY: "Cedar Office", C.PROPERTY_TYPE: "office", C.CATEGORY: "improved_property",
     C.QUANTITY: 80000, C.RENT: 32, C.MARKET_RENT: 34, C.VACANCY: .18,
     C.OTHER_INCOME: 50000, C.OPEX: 1050000, C.RESERVES: 80000, C.CAP_RATE: .075},
)
CONSTRUCTION_BUDGET = {"land": 2e6, "hard_costs": 6e6, "soft_costs": 1.2e6,
                       "contingency": .5e6, "interest_reserve": .3e6}
CONSTRUCTION_COMMITMENT = 7.5e6
CONSTRUCTION_EQUITY = 2.5e6
RETAINAGE = .10
CONSTRUCTION_MONTHS = 12
CONSTRUCTION_RATE = .08
CONSTRUCTION_OVERRUN = .15
CONSTRUCTION_CONTINGENCY_USE = .5e6
CONSTRUCTION_RESERVE_NEED = .35e6
CONSTRUCTION_INSPECTOR_LAG = .04
CONSTRUCTION_LAND_LINE = "land"
CONSTRUCTION_HARD_LINE = "hard_costs"
CONSTRUCTION_CONTINGENCY_LINE = "contingency"
CONSTRUCTION_INTEREST_LINE = "interest_reserve"

AR_ADVANCE = .85
INVENTORY_COST_ADVANCE = .50
INVENTORY_NOLV_ADVANCE = .85
CROSS_AGING_THRESHOLD = .50
CONCENTRATION_LIMIT = .20
SPRINGING_THRESHOLD = .10
ABL_COMMITMENT = 2e6
ABL_OPENING = 850000
ABL_RESERVES = 75000
ABL_FCCR = 1.15
ABL_MONTHS = 12
ABL_CUSTOMERS = 10
ABL_AR_MIN = 180000
ABL_AR_MAX = 600000
ABL_AGE_SHARES = (.70, .15, .10, .05)
ABL_CROSS_AGE_SHARES = (.20, .10, .10, .60)
ABL_AFFILIATE_CUSTOMER = "Customer 09"
ABL_FOREIGN_CUSTOMER = "Customer 10"
ABL_CONTRA = 15000
ABL_MONTHLY_GROWTH = -.015
ABL_MONTHLY_VOLATILITY = .015
ABL_DRAW = 70000
ABL_PAYDOWN = 30000
INVENTORY_INPUTS = (
    {C.CATEGORY: "finished_goods", C.COST: 900000, C.NOLV: 540000, C.ELIGIBLE: True},
    {C.CATEGORY: "raw_materials", C.COST: 450000, C.NOLV: 270000, C.ELIGIBLE: True},
    {C.CATEGORY: "obsolete", C.COST: 150000, C.NOLV: 15000, C.ELIGIBLE: False},
)
PORTFOLIO_LOANS = 40
PORTFOLIO_QUARTERS = 8
PORTFOLIO_START = "2024Q1"
LOAN_TYPES = ("corporate", "cre", "abl")
PORTFOLIO_INDUSTRIES = ("Consumer products", "Manufacturing", "Retail", "Real estate", "Distribution")
PORTFOLIO_PROPERTY_TYPES = ("multifamily", "office", "construction")
PORTFOLIO_BALANCE_RANGE = (1e6, 12e6)
PORTFOLIO_GRADE_RANGE = (2, 8)
PORTFOLIO_BALANCE_DECAY = .015
PORTFOLIO_GRADE_MOVES = (-1, 0, 1, 2)
PORTFOLIO_GRADE_PROBS = (.10, .65, .20, .05)
PORTFOLIO_REVENUE_RANGE = (8e6, 40e6)
PORTFOLIO_MARGIN_RANGE = (.12, .24)
PORTFOLIO_EBITDA_SHOCK = .08
PORTFOLIO_DEBT_MULTIPLE_RANGE = (2.0, 4.2)
PORTFOLIO_LTV_RANGE = (.60, .86)
PORTFOLIO_CRE_NOI_SHOCK = .10
PORTFOLIO_ABL_UTILIZATION = (.40, .95)
PORTFOLIO_CONSTRUCTION_COMPLETION = (.05, .95)
WATCH_DOWNGRADE = 2
WATCH_DSCR = 1.0
TOLERANCE = 1e-8
PLOT_DPI = 150
PLOT_SIZE = (8, 4)
DOC_FONT = "Calibri"
DOC_FONT_SIZE = 10
DOC_MARGIN_INCHES = .65
LIBREOFFICE_NAMES = ("soffice", "libreoffice")
LIBREOFFICE_PATHS = (Path("C:/Program Files/LibreOffice/program/soffice.exe"),)
EXCEL_TOLERANCE = .02
HISTORICAL_PRINCIPAL = 0.0
PORTFOLIO_PRINCIPAL_RATE = .04
PORTFOLIO_CAPEX_RATE = .025
PORTFOLIO_TAX_RATE = .02
PORTFOLIO_BASE_DSCR_RANGE = (1.05, 1.65)
PORTFOLIO_CONSTRUCTION_BUFFER = .1e6
PORTFOLIO_CONSTRUCTION_OVERRUN = .35e6
PORTFOLIO_CONSTRUCTION_SHOCK = .2e6
PORTFOLIO_AR_SCALE = .7
PORTFOLIO_CRE_INDUSTRY = "Real estate"
PORTFOLIO_ABL_INDUSTRY = "Distribution"
MODE_DEMO = "demo"
MODE_SNAPSHOTS = "snapshots"
DEFAULT_MODE = MODE_DEMO
NUMERIC_FORMAT = "#,##0.00;(#,##0.00);0.00"
PERCENT_FORMAT = "0.00%"
EXCEL_FONT_SIZE = 10
EXCEL_MAX_WIDTH = 32
EXCEL_MIN_WIDTH = 16
EXCEL_HEADER_HEIGHT = 40
DOC_TABLE_SIZE = 8
QA_RENDER_TIMEOUT = 120
DOC_HEADING_SIZES = {"Title": 20, "Heading 1": 15, "Heading 2": 13, "Heading 3": 12}
DOC_PARAGRAPH_SPACE = 5
DOC_TABLE_SPACE = 2
MONEY_DECIMALS = 2
WEIGHT_DECIMALS = 3
STABILITY_DECIMALS = 4
EXCEL_LINE_HEIGHT = 13
EXCEL_MIN_HEIGHT = 16
PERCENTAGE_OUTPUT_METRICS = frozenset((C.LEVERAGE_HEADROOM, C.FCCR_HEADROOM, C.CUSHION,
                                      C.BREAK_EVEN, C.LGD, C.RATE, C.REVOLVER_UTILIZATION))
