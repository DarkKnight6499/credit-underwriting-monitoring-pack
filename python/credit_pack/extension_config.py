"""Extension inputs, named columns, and explicitly illustrative policy terms."""

from dataclasses import dataclass

from . import config as base
from .config import C

# CONFIG: extension paths, dates, seed, units, and scenario assumptions.
OUTPUT = base.ROOT / "examples" / "output"
INPUT = base.ROOT / "data" / "extension"
WORKBOOK = base.ROOT / "excel" / "credit_extension.xlsx"
SEED = base.SEED
AS_OF = "2026-11-08"
SOURCE_DATE = "2026-11-08"
SYNTHETIC = "Seeded synthetic scenario"
EPSILON = 1e-7
MONTHS = base.MONTHS_IN_YEAR
DAYS = base.DAYS_IN_YEAR
PRICE_PAR = 100.0
PRICE_TOLERANCE = 1.0
MAX_TRADE_AGE_DAYS = 7
CURVE_TENORS = (0.25, 1.0, 3.0, 5.0, 10.0, 20.0)
CURVE_RATES = (.035, .036, .038, .040, .043, .045)
REVENUE_STRESSES = (-.20, -.10, 0.0, .10)
RATE_STRESSES = (0.0, .01, .02)
TAX_RATES = (0.0, .24, .32, .37)
WAREHOUSE_LOANS = 120
WAREHOUSE_MONTHS = 12
LOAN_BALANCE_RANGE = (5000.0, 25000.0)
LOAN_SCORE_RANGE = (590, 801)
LOAN_DPD_CHOICES = (0, 15, 31, 61)
LOAN_DPD_PROBS = (.82, .10, .06, .02)
LOAN_APR_RANGE = (.10, .24)
LOAN_STATES = ("CA", "TX", "NY", "FL", "IL")
LOAN_GRADES = ("A", "B", "C")
LOAN_REMAINING_RANGE = (6, 61)
POOL_UNVERIFIED_SHARE = .05
POOL_FRAUD_SHARE = .02
POOL_INITIAL_DEFAULT_SHARE = .01
POOL_AMORTIZATION = .025
POOL_DEFAULT_RATE = .003
POOL_STRESS_MONTH = 7
POOL_STRESS_DEFAULT_RATE = .08
WAREHOUSE_DRAW_REQUEST = 90000.0
WAREHOUSE_VOLUNTARY_PAYDOWN = 10000.0
PROJECT_CAPEX_WEIGHTS = (.04, .06, .08, .10, .12, .12, .12, .10, .09, .07, .06, .04)
PROJECT_CAPACITY_MW = 100.0
PROJECT_CAPACITY_FACTOR = .32
PROJECT_HOURS_PER_YEAR = 8760
PROJECT_ENERGY_PRICE = 70.0
PROJECT_PRICE_ESCALATION = .02
PROJECT_DEGRADATION = .004
PROJECT_OPEX = 5500000.0
PROJECT_TAX = 900000.0
PROJECT_MAINTENANCE = 700000.0
PROJECT_OPEX_ESCALATION = .015
PROJECT_YEARS = 15
MAINTENANCE_CYCLE = 5
SCORE_BUY_MAX = 2.0
SCORE_HOLD_MAX = 2.5
SCORE_MIN_SPREAD = .001
SCORE_FACTORS = {
    "corporate": {C.FCF_DEBT: (True, (.2, .5, .8)), C.LEVERAGE: (False, (.8, 1.5, 2.5))},
    "gsib": {"cet1_ratio": (True, (.10, .12, .14)), "lcr": (True, (1.05, 1.15, 1.25))},
    "go": {"fund_balance_ratio": (True, (.05, .10, .20)), "operating_balance_ratio": (True, (-.01, 0, .03))},
    "revenue": {"operating_margin_before_depreciation": (True, (.15, .30, .45)), "debt_to_revenue": (False, (4, 6, 8))},
}


class X(C):
    """Reuse existing names and add extension-specific fields."""

    CFADS = "cfads"
    ENERGY_MWH = "generation_mwh"
    POWER_PRICE = "power_price_per_mwh"
    SERVICE = "debt_service"
    CLOSING = "closing_balance"
    DSRA_OPEN = "dsra_opening"
    DSRA_TARGET = "dsra_target"
    DSRA_DRAW = "dsra_draw"
    DSRA_TOPUP = "dsra_topup"
    DSRA_RELEASE = "dsra_release"
    DSRA_CLOSE = "dsra_closing"
    RESERVE_SHORT = "reserve_shortfall"
    MAINT_OPEN = "maintenance_opening"
    MAINT_CONTRIB = "maintenance_contribution"
    MAINT_SPEND = "maintenance_spending"
    MAINT_CLOSE = "maintenance_closing"
    DISTRIBUTION = "distribution"
    UNPAID = "unpaid_debt_service"
    CAPACITY = "debt_capacity"
    IDC = "construction_interest"
    INITIAL_DSRA = "initial_dsra"
    REVENUE_CHANGE = "revenue_change"
    RATE_CHANGE = "rate_change"
    MIN_DSCR = "minimum_dscr"
    SCORE_INPUT = "credit_score"
    STATE = "state"
    APR = "apr"
    DPD = "days_past_due"
    REMAINING = "remaining_months"
    VERIFIED = "income_verified"
    FRAUD = "fraud_flag"
    DEFAULT = "defaulted"
    PRE_ELIGIBLE = "pre_concentration_balance"
    ADJUSTED = "adjusted_eligible_balance"
    ADVANCE = "advance_amount"
    STATE_EXCESS = "state_excess"
    GRADE_EXCESS = "grade_excess"
    ELIGIBLE_BALANCE = "eligible_balance"
    INELIGIBLE_BALANCE = "ineligible_balance"
    WEIGHTED_APR = "weighted_apr"
    DEFAULT_RATE = "default_rate"
    CUM_DEFAULT_RATE = "cumulative_default_rate"
    DELINQUENCY = "delinquency_rate"
    POOL_COLLECTIONS = "principal_collections"
    INTEREST_COLLECTIONS = "interest_collections"
    LOSSES = "principal_losses"
    REQUESTED_PAYDOWN = "requested_paydown"
    MANDATORY_PAYDOWN = "mandatory_paydown"
    COLLECTION_PAYDOWN = "collection_paydown"
    CASH_SHORT = "paydown_cash_shortfall"
    BLOCK_DRAW = "draw_blocked"
    ISSUER = "issuer"
    KIND = "issuer_type"
    SECURITY = "security_id"
    YIELD = "yield"
    TAX_RATE = "tax_rate"
    TEY = "tax_equivalent_yield"
    TAXABLE_YIELD = "taxable_comparator_yield"
    TEY_SPREAD = "tey_spread"
    MUNI_RATIO = "muni_taxable_ratio"
    CET1 = "cet1_ratio"
    LCR = "lcr"
    FUND_BALANCE = "available_fund_balance"
    FUND_RATIO = "fund_balance_ratio"
    DEBT_REVENUE = "debt_to_revenue"
    DAYS_CASH = "days_cash"
    OPERATING_BALANCE = "operating_balance_ratio"
    CASH_MARGIN = "operating_margin_before_depreciation"
    ASSESSED_VALUE = "assessed_value"
    DEBT_VALUE = "debt_to_assessed_value"
    COLLECTION_RATE = "tax_collection_rate"
    SCORE_AVG = "average_factor_score"
    SPREAD = "spread"
    MATURITY = "maturity_days"
    MARKET_VALUE = "market_value"
    USD = "usd_denominated"
    CREDIT_REVIEW = "minimal_credit_risk_review"
    GOVERNMENT = "direct_us_government"
    DAILY = "daily_liquid"
    WEEKLY = "weekly_liquid"
    ILLIQUID = "illiquid"
    SUPPORTED = "supported_plain_instrument"
    STATUS = "screen_status"
    WAM = "wam_days"
    WAL = "wal_days"
    DAILY_SHARE = "daily_liquid_share"
    WEEKLY_SHARE = "weekly_liquid_share"
    ILLIQUID_SHARE = "illiquid_share"
    ISSUER_SHARE = "issuer_share"
    COUPON = "coupon_rate"
    FREQUENCY = "payments_per_year"
    TENOR = "maturity_years"
    ACCRUED = "accrued_interest"
    MODEL_CLEAN = "model_clean_price"
    MODEL_DIRTY = "model_dirty_price"
    TRADE_PRICE = "trade_clean_price"
    TRADE_DATE = "trade_date"
    CURVE_DATE = "curve_date"
    VENUE = "venue"
    PRICE_DIFF = "price_difference"
    PRICE_BREAK = "price_break"
    STALE = "stale_trade"
    DURATION = "modified_duration"
    CONVEXITY = "convexity"
    CALLABLE = "callable"
    TAX_EXEMPT = "tax_exempt"
    PERIOD_END = C.END


@dataclass(frozen=True)
class ProjectTerms:
    cost: float = 100000000.0
    rate: float = .065
    target_dscr: float = 1.35
    covenant_dscr: float = 1.20
    max_cost_leverage: float = .70
    dsra_years: float = .50


@dataclass(frozen=True)
class WarehouseTerms:
    commitment: float = 1600000.0
    reserve: float = 35000.0
    opening: float = 700000.0
    min_score: int = 640
    max_dpd: int = 30
    max_remaining: int = 60
    state_limit: float = .30
    grade_c_limit: float = .25
    advances: tuple = (("A", .85), ("B", .80), ("C", .70))
    max_delinquency: float = .12
    max_cumulative_default: float = .08
    min_apr: float = .12
    annual_rate: float = .07


@dataclass(frozen=True)
class MoneyMarketRules:
    """Verified subset of 17 CFR 270.2a-7; no regulatory rating cutoff."""

    max_maturity: int = 397
    max_wam: int = 60
    max_wal: int = 120
    max_issuer_share: float = .05
    min_daily: float = .25
    min_weekly: float = .50
    max_illiquid: float = .05


PROJECT = ProjectTerms()
WAREHOUSE = WarehouseTerms()
MONEY_MARKET = MoneyMarketRules()
