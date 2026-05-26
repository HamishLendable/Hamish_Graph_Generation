# Snowflake conventions — reference for `motor_graphs/data/snowflake.py`

Locked by Hamish at Batch 1.4 sign-off. Mirror the `credit.auto-monthly-monitoring` patterns precisely.

## Auth pattern

Lentils-managed Okta SSO. No password, no API key in `.env`.

```python
from lentils.snowflake import SnowflakeReader

reader = SnowflakeReader.from_connection(
    authenticator="okta",
    database="PROD",
    warehouse="READER_PROD",
    role="READER_PROD",
)
```

`.env` keys (note `USERNAME`, not `USER`):

```
SNOWFLAKE_ACCOUNT="bh70701.eu-west-1"
SNOWFLAKE_USERNAME=your.name@lendable.co.uk
```

Lentils reads `SNOWFLAKE_*`-prefixed env vars automatically.

## Connection pool (mirror verbatim from reference `data_loader.py`)

Thread-safe singleton with 30-min idle TTL, double-checked locking.

```python
import threading
import time
import pandas as pd
from lentils.snowflake import SnowflakeReader


class SnowflakeConnectionPool:
    _instance = None
    _lock = threading.Lock()
    _reader = None
    _last_used = None
    _connection_timeout = 1800  # 30 min

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def get_reader(self) -> SnowflakeReader:
        current_time = time.time()
        if (self._reader is None or self._last_used is None
            or current_time - self._last_used > self._connection_timeout):
            with self._lock:
                if (self._reader is None or self._last_used is None
                    or current_time - self._last_used > self._connection_timeout):
                    self._reader = SnowflakeReader.from_connection(
                        authenticator="okta",
                        database="PROD",
                        warehouse="READER_PROD",
                        role="READER_PROD",
                    )
                    self._last_used = current_time
        self._last_used = current_time
        return self._reader


_pool = SnowflakeConnectionPool()


def run_query(sql: str) -> pd.DataFrame:
    df = _pool.get_reader().read_to_dataframe(query_string=sql)
    df.columns = df.columns.str.lower()  # mandatory normalisation
    return df
```

## Caching (NEW — added to motor-graph-generation)

Reference has none. Add an opt-in pickle cache at `~/.cache/motor-graphs/`, keyed on SHA256 of the SQL string.

```python
from functools import wraps
import hashlib
import pickle
import time
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "motor-graphs"

def cached(ttl_hours: int = 24):
    def deco(fn):
        @wraps(fn)
        def wrapper(sql: str, *args, **kwargs):
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            key = hashlib.sha256(sql.encode()).hexdigest()[:16]
            path = CACHE_DIR / f"{key}.pkl"
            if path.exists() and (time.time() - path.stat().st_mtime) < ttl_hours * 3600:
                with path.open("rb") as f:
                    return pickle.load(f)
            df = fn(sql, *args, **kwargs)
            with path.open("wb") as f:
                pickle.dump(df, f)
            return df
        return wrapper
    return deco
```

Opt-in only — wrap `run_query` with `@cached(ttl_hours=24)` if the recipe wants caching.

## Canonical tables

Schema constants:

```python
DB = "PROD"
PRS_MOTOR = f"{DB}.PRS_MOTOR"
MRT_MOTOR = f"{DB}.MRT_MOTOR"
INT_MOTOR = f"{DB}.INT_MOTOR"
STG_MOTOR_LENDABLE = f"{DB}.STG_MOTOR_LENDABLE"
MRT_OPENBANKING = f"{DB}.MRT_OPENBANKING"
RAW_PRODUCTION = "RAW_PRODUCTION"
```

| Fully-qualified | Purpose | Join keys |
|---|---|---|
| `PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR` | Application/loan master | `APPLICATION_ID`, `LOAN_ID` |
| `PROD.PRS_MOTOR.PRS__CREDIT_SEGMENTS__MOTOR` | CCE / scorecard segmentation | `APPLICATION_ID` |
| `PROD.MRT_MOTOR.MRT__DELINQUENCY_FLAGS_BY_MONTH__MOTOR` | Per-loan DQ flags at MOB 1/3/6/9 | `LOAN_ID` |
| `PROD.MRT_MOTOR.MRT__LOAN__MOTOR` | Loan state (live / terminated / VT) | `LOAN_ID` |
| `PROD.MRT_MOTOR.MRT__REPAYMENT__MOTOR` | Actual repayment events | `LOAN_ID`, `SCHEDULEDPAYMENT_ID` |
| `PROD.MRT_MOTOR.MRT__REPAYMENT_AUDIT__MOTOR` | Typed repayment audit (overpayments) | `LOAN_ID`, `DATE_MONTH` |
| `PROD.INT_MOTOR.INT__CONTRACTUAL_PAYMENTARREARS__MOTOR` | Per-loan per-MOB arrears spine | `LOAN_ID`, `MONTH_INDEX`, `ORIGINATIONDATE` |
| `PROD.MRT_OPENBANKING.MRT__DATA_PULL_SUMMARY__OPENBANKING` | OB data pulls | `DATAPULL_ID` |
| `PROD.STG_MOTOR_LENDABLE.stg__openbankingcustomerdata__motor_lendable` | App ↔ OB pull link | `LOANAPPLICATION_ID`, `DATAPULL_ID` |
| `PROD.STG_MOTOR_LENDABLE.STG__FULL_LOAN_METRICS__MOTOR_IRR` | IRR loan×MOB expectations | `loan_id`, `mob` |
| `PROD.STG_MOTOR_LENDABLE.STG__GROUPED_METRICS__MOTOR_IRR` | IRR grade-level snapshot | `risk_grade` |
| `PROD.STG_MOTOR_LENDABLE.STG__HIREPURCHASELOAN__MOTOR_LENDABLE` | Raw loan state | `ID`, `SECONDARYSTATE` |
| `PROD.STG_MOTOR_LENDABLE.STG__SCHEDULEDPAYMENT__MOTOR_LENDABLE` | Scheduled payment amounts | `ID` |
| `PROD.STG_MOTOR_LENDABLE.STG__TERMINATED_PAYMENTS__MOTOR_LENDABLE` | Termination recoveries | `LOAN_ID` |
| `PROD.STG_MOTOR_LENDABLE.STG__VT_PAYMENTS__MOTOR_LENDABLE` | VT recovery flows | `LOAN_ID` |
| `RAW_PRODUCTION.MOTOR_UK_LENDABLE.hirepurchaseloan` | Raw loan product (for `IS_DEALER`) | `id`, `loanproduct_id` |

## Canonical column conventions

### Flag columns

All 1/0 — coerce in pandas: `.fillna(0).astype(bool)` (except `FLAG_*_OB` which stays numeric to preserve nulls).

| Column | Semantics |
|---|---|
| `FLAG_QUOTED` | App reached quote stage |
| `FLAG_ORIGINATED` | Loan booked |
| `FLAG_ORIGINATED_AND_NOT_CANCELLED` | Originated and still active. **Preferred filter**: `COALESCE(FLAG_ORIGINATED_AND_NOT_CANCELLED, FLAG_ORIGINATED) = TRUE` |
| `FLAG_APPLICATION_FINISHED` | Final app state reached |
| `FLAG_APPLY_PAGE_VISITED`, `FLAG_LOAN_CONTRACT_ACCEPTED` | Funnel milestones |
| `FLAG_BASIC_CHECK_RULES_PASSED` | Pre-bureau check pass |
| `FLAG_EXPERIAN_CREDIT_CHECK_PASSED`, `FLAG_TRANSUNION_CREDIT_CHECK_PASSED` | Bureau pass |
| `FLAG_AFFORDABILITY_CHECK_PASSED_ANY_QUOTE`, `FLAG_INSERTION_AFFORDABILITY_CHECK_PASSED` | Affordability |
| `FLAG_OPEN_BANKING_REQUIRED_AT_INSERTION`, `FLAG_PASSED_OB` | OB (numeric, not bool) |
| `FLAG_FIRST_QUOTE_COUNTER_OFFERED`, `FLAG_FINAL_QUOTE_COUNTER_OFFERED` | Counter-offer markers |
| `FLAG_HINTON_DECLINE_ON_DECISIONED_SCORECARD` | Hinton (non-Carrera) decline |
| `IS_DEALER` | Derived in SQL: `loanproduct_id IN (whitelist)` → 1 |

Derived in pandas:

```python
df["is_cce"] = df["flag_hinton_decline_on_decisioned_scorecard"].isna() | (df["flag_hinton_decline_on_decisioned_scorecard"] == 0) | (df["primary_scorecard"] == "carrera")
df["bad_ob_check"] = (df["n_transactions"] < 50) | (df["n_current_accounts"] == 0) | (df["latest_transaction_age"] >= 29)
df["is_cce_with_good_ob"] = df["is_cce"] & ~df["bad_ob_check"]
```

### Origination metadata

| Column | Type | Notes |
|---|---|---|
| `APPLICATION_CREATED_DATETIME` | timestamp | Primary app-date filter |
| `ORIGINATION_DATETIME` | timestamp | Cohort source |
| `ORIGINATION_RISK_GRADE`, `INSERTION_RISK_GRADE` | str (`A`, `B^`, `F*^`, …) | Coerce `'nan' / 'None' / 'null' / ''` → `pd.NA` |
| `ORIGINATION_SIMPLIFIED_RISK_GRADE`, `INSERTION_SIMPLIFIED_RISK_GRADE` | str | Server-side pre-simplified |
| `FINAL_GROSS_AMOUNT` | float £ | **Use for GBV / £-weighting** — `ORIGINATION_AMOUNT` does NOT exist |
| `FINAL_NET_AMOUNT`, `INSERTION_NET_AMOUNT`, `APP_AMOUNT` | float £ | |
| `FINAL_ORIGINATION_FEE`, `COMMISSION` | float £ | |
| `FINAL_TERM` | months | `ORIGINATION_TERM_MONTHS` does NOT exist |
| `INSERTION_REQUESTED_TERM`, `FINAL_QUOTE_REQUESTED_TERM` | months | |
| `FINAL_APR`, `FINAL_INTEREST_RATE` | float | |
| `DELPHI_SCORE`, `GAUGE_SCORE2` | float | Bureau scores |
| **No `ORIGINATION_PD` column** | — | Use `input_90_in_9` from `STG__FULL_LOAN_METRICS__MOTOR_IRR` as a PD substitute |

### Delinquency (rename in pandas after pull)

| Source col | Renamed to | Semantics |
|---|---|---|
| `DQ_30_1` | `is_30dpd_at_mob1` | 30+ DPD by MOB 1 |
| `DQ_30_3` | `is_30dpd_at_mob3` | 30+ DPD by MOB 3 |
| `DQ_60_6` | `is_60dpd_at_mob6` | 60+ DPD by MOB 6 |
| `DQ_90_BY_9` | `is_gross_90_default_at_mob9` | 90+ DPD by MOB 9 (gross default proxy) |

No `90@12` flag exists. If 90@12 is needed, compute from `MRT__LOAN__MOTOR` state changes.

Arrears spine columns (`INT__CONTRACTUAL_PAYMENTARREARS__MOTOR`): `LOAN_ID`, `MONTH_INDEX` (= MOB), `PAYMENT_DEADLINE`, `PAYMENT_DATE`, `ORIGINATIONDATE`, `MONTHS_IN_ARREARS`, `ADJUSTED_MONTHS_IN_ARREARS`, `PRINCIPAL_OUTSTANDING`.

### Vehicle

| Column | Notes |
|---|---|
| `FINAL_VEHICLE_ID`, `INSERTION_VEHICLE_ID` | ID only |
| `FINAL_VEHICLE_VALUE` | £ |
| `FINAL_VEHICLE_FUEL_TYPE` | str |
| `FINAL_VEHICLE_AGE_IN_MONTHS` | numeric |

No BEV/PHEV flag or mileage column in `data_loader.py` — these are derived elsewhere or absent.

### Channel / introducer

| Column | Notes |
|---|---|
| `INTRODUCER` | Raw introducer name |
| `introducer_category` | Normalised in pandas via `normalize_introducer_category` to one of `{Broker, Aggregator, Direct}` |
| `IS_DEALER` | Derived from `loanproduct_id` whitelist |

The 5-category introducer taxonomy (Aggregator / Broker - Dealer led / Broker - Online led / Dealer / Direct) used in EV charts is a richer raw taxonomy — apply by NOT calling `normalize_introducer_category`.

### Cashflow / payment

| Column | Source | Notes |
|---|---|---|
| `TOTAL`, `PAIDDATE`, `STATE`, `DELETEDAT`, `PAYMENTMETHOD`, `SCHEDULEDPAYMENT_ID` | `MRT__REPAYMENT__MOTOR` | Filter: `STATE IN ('paid','charged back') AND DELETEDAT IS NULL AND LOWER(PAYMENTMETHOD) != 'balance adjustment credit'` |
| `TYPE_DETAILED`, `total`, `DATE_MONTH` | `MRT__REPAYMENT_AUDIT__MOTOR` | Prepayments: `TYPE_DETAILED='overpayment_other'` |
| `SECONDARYSTATE`, `SECONDARYSTATECHANGEDATE` | `MRT__LOAN__MOTOR` / `STG__HIREPURCHASELOAN__MOTOR_LENDABLE` | States: `'terminated'`, `'voluntary terminated'` |
| IRR cashflow cols | `STG__FULL_LOAN_METRICS__MOTOR_IRR` | `a_*` = £ amounts, `n_*` = counts/probs: `a_principal_default_flow`, `n_default_flow`, `a_early_settlement_flow`, `a_voluntary_termination_flow`, `a_prepayment_flow`, `a_interest_repayment_flow`, `a_principal_outstanding_bop/eop`, `a_contractual_repayment_flow`, `input_90_in_9` |

## Cohort filtering pattern

Half-open: `col >= 'YYYY-MM-DD' AND col < 'YYYY-MM-DD'`.

Filter column varies by intent:

- Applications, enriched loans → `APPLICATION_CREATED_DATETIME`
- Originated, prepayment, cashflow → `ORIGINATION_DATETIME` / `ORIGINATIONDATE`
- Roll-rate → `PAYMENT_DEADLINE` (snapshot-month, not cohort)

Cohort month derivation (pandas):

```python
df["cohort_month"] = df["origination_datetime"].dt.strftime("%Y-%m")
```

`load_actual_cashflows` builds `cohort_month` and `cohort_quarter` server-side via `DATE_TRUNC('month', ...)` and `DATE_TRUNC('quarter', ...)`.

Cohorts can be arbitrary date ranges — charts most commonly pass whole months.

## Risk-grade helpers (mirror from `charts/vt_assumptions.py`)

```python
def simplify_risk_grade(grade):
    """Strip ^ suffix, preserve F/F*/F** distinction.

    A^→A, B^→B, ..., F^→F, F*^→F*, F**^→F**. Unknown grade → None.
    """
    if pd.isna(grade):
        return None
    g = str(grade).strip().replace("^", "")
    if g in {"A", "B", "C", "D", "E", "F", "F*", "F**"}:
        return g
    if g and g[0] in {"A", "B", "C", "D", "E"}:
        return g[0]
    return None


RISK_GRADE_GROUPS = {
    "A-B": ["A", "B"],
    "C-E": ["C", "D", "E"],
    "F+":  ["F", "F*", "F**"],
}

# Cashflow variant
CASHFLOW_GRADE_GROUPS = {
    "A-C": ["A", "B", "C"],
    "D-E": ["D", "E"],
    "F+":  ["F", "F*", "F**"],
}
```

`regression_expectations.py` has its own `_map_grade` which is more aggressive (collapses every `*` / `**` / `^` variant of A-E to the base letter). Use the version above unless porting regression-validation specifically.

## Sample query templates (verbatim from `data_loader.py`)

### A) Originations with flags + IS_DEALER

```sql
SELECT a.APPLICATION_ID, a.USER_ID, a.LOAN_ID, ...,
       a.FLAG_QUOTED, a.FLAG_ORIGINATED, a.FINAL_GROSS_AMOUNT,
       a.ORIGINATION_RISK_GRADE, ...,
       IFF(l.loanproduct_id IN (14,25,54,73,125,199, ..., 277), 1, 0) AS IS_DEALER
FROM PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR a
LEFT JOIN RAW_PRODUCTION.MOTOR_UK_LENDABLE.hirepurchaseloan l
  ON a.LOAN_ID = l.id
WHERE a.APPLICATION_CREATED_DATETIME >= '{start}'
  AND a.APPLICATION_CREATED_DATETIME <  '{end}'
ORDER BY a.APPLICATION_CREATED_DATETIME DESC;
```

### B) DQ-by-MOB enriched (canonical join pattern)

```sql
WITH ob_detail AS (
    SELECT prs.application_id, dp.DATAPULL_ID, dp.NUMBER_OF_TRANSACTIONS,
           dp.NUMBER_OF_CURRENT_ACCOUNTS,
           DATEDIFF('day', dp.latest_transaction_timestamp, dp.CREATED_AT) AS latest_transaction_age,
           ROW_NUMBER() OVER (PARTITION BY prs.application_id ORDER BY dp.created_at DESC) AS rn
    FROM prod.STG_MOTOR_LENDABLE.stg__openbankingcustomerdata__motor_lendable mot
    INNER JOIN PROD.MRT_OPENBANKING.MRT__DATA_PULL_SUMMARY__OPENBANKING dp ON mot.DATAPULL_ID = dp.DATAPULL_ID
    INNER JOIN PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR prs ON prs.APPLICATION_ID = mot.LOANAPPLICATION_ID
    WHERE dp.RADON_SCORE IS NOT NULL
      AND prs.APPLICATION_CREATED_DATETIME >= '{start}'
      AND prs.APPLICATION_CREATED_DATETIME <  '{end}'
),
ob_stats AS (
    SELECT application_id,
           IFF(number_of_transactions >= 50 AND number_of_current_accounts > 0
               AND latest_transaction_age < 29, 0, 1) AS bad_ob_check
    FROM ob_detail WHERE rn = 1
)
SELECT a.APPLICATION_ID, a.LOAN_ID, ..., a.ORIGINATION_SIMPLIFIED_RISK_GRADE,
       IFF(l.loanproduct_id IN (...), 1, 0) AS IS_DEALER,
       dq.DQ_30_1, dq.DQ_30_3, dq.DQ_60_6, dq.DQ_90_BY_9,
       ls.SECONDARYSTATE, ls.SECONDARYSTATECHANGEDATE,
       cce.FLAG_HINTON_DECLINE_ON_DECISIONED_SCORECARD, cce.PRIMARY_SCORECARD,
       ob.bad_ob_check
FROM PROD.PRS_MOTOR.PRS__APPLICATION__MOTOR a
LEFT JOIN RAW_PRODUCTION.MOTOR_UK_LENDABLE.hirepurchaseloan l ON a.LOAN_ID = l.id
LEFT JOIN PROD.MRT_MOTOR.MRT__DELINQUENCY_FLAGS_BY_MONTH__MOTOR dq ON a.LOAN_ID = dq.LOAN_ID
LEFT JOIN PROD.MRT_MOTOR.MRT__LOAN__MOTOR ls ON a.LOAN_ID = ls.LOAN_ID
LEFT JOIN PROD.PRS_MOTOR.PRS__CREDIT_SEGMENTS__MOTOR cce ON a.APPLICATION_ID = cce.APPLICATION_ID
LEFT JOIN ob_stats ob ON a.APPLICATION_ID = ob.APPLICATION_ID
WHERE a.APPLICATION_CREATED_DATETIME >= '{start}'
  AND a.APPLICATION_CREATED_DATETIME <  '{end}'
  AND COALESCE(a.FLAG_ORIGINATED_AND_NOT_CANCELLED, a.FLAG_ORIGINATED) = TRUE
ORDER BY a.APPLICATION_CREATED_DATETIME DESC;
```

### C) Cashflow / prepayment

```sql
SELECT a.LOAN_ID,
       a.ORIGINATIONDATE AS origination_datetime,
       a.MONTH_INDEX     AS mob,
       COALESCE(SUM(CASE WHEN rep.TYPE_DETAILED = 'overpayment_other'
                         THEN rep.total ELSE 0 END), 0) AS amount
FROM PROD.INT_MOTOR.INT__CONTRACTUAL_PAYMENTARREARS__MOTOR a
LEFT JOIN PROD.MRT_MOTOR.MRT__REPAYMENT_AUDIT__MOTOR rep
  ON a.LOAN_ID = rep.LOAN_ID
 AND DATE_TRUNC('month', a.PAYMENT_DATE) = DATE_TRUNC('month', rep.DATE_MONTH)
WHERE a.ORIGINATIONDATE >= '{start}'
  AND a.ORIGINATIONDATE <  '{end}'
GROUP BY a.LOAN_ID, a.ORIGINATIONDATE, a.MONTH_INDEX
ORDER BY a.LOAN_ID, a.MONTH_INDEX;
```

### D) IRR grade-level snapshot

```sql
SELECT risk_grade, pct_of_portfolio, target_90_in_9, glr, nlr, nvtr,
       wa_interest, wa_fee, wa_commission,
       irr_net_of_premium, irr_net_of_servicing,
       net_origination_amount, gross_origination_amount,
       assumption_version, calculated_datetime
FROM PROD.STG_MOTOR_LENDABLE.STG__GROUPED_METRICS__MOTOR_IRR
WHERE calculated_datetime = (
    SELECT MAX(calculated_datetime)
    FROM PROD.STG_MOTOR_LENDABLE.STG__GROUPED_METRICS__MOTOR_IRR
);
```

## Top-level loader functions (mirror in `motor_graphs/recipes/*` as needed)

| Function | Signature | Returns | Used by |
|---|---|---|---|
| `read_snowflake` | `(query: str) -> DataFrame` | Lowercased-column DF | All |
| `load_application_data` | `(start_date=None, end_date=None, app_ids=None)` | Apps + IS_DEALER | App funnel recipes |
| `load_enriched_originated_loans` | `(start_date, end_date)` | Originated + DQ + state + CCE + OB | Primary loader |
| `load_roll_rate_data` | `(start_date, end_date)` | `loan_id, payment_deadline, months_in_arrears, principal_outstanding` | Roll-rate recipes |
| `load_loan_state_data` | `(loan_ids=None)` | `loan_id, secondarystate, secondarystatechangedate` | VT recipes |
| `load_irr_full_loan_metrics` | `(loan_ids=None)` | Loan×MOB IRR expectations | VT assumptions, regression |
| `load_irr_grouped_metrics` | `()` | Latest grade-level IRR snapshot | Scorecard recipes |
| `load_data_for_analysis` | `(start_date, end_date, expectations_path=None)` | `(merged_df, expectations_df)` | Orchestrator recipe |
| `load_prepayment_data` | `(start_date, end_date)` | `loan_id, origination_datetime, mob, amount` | Prepay recipe |
| `load_actual_cashflows` | `(start_date, end_date)` | Loan×MOB actuals + flags | Cashflow recipes |
| `normalize_introducer_category` | `(category) -> str` | `'Broker' \| 'Aggregator' \| 'Direct'` | All loaders |

## Stubs to skip

`load_cce_data`, `load_ob_check_data`, `load_delinquency_data` exist in reference as back-compat empty stubs. Do not reimplement.

## Parallelism

Reference does NOT parallelise queries — single shared reader, sequential `read_to_dataframe` calls. Mirror this. If parallelism is later needed, add a `ThreadPoolExecutor` wrapper but treat as out-of-scope for v0.1.

## `expectations.yaml` format (mirror as-is)

YAML list of records keyed by `(riskgrade, mob, metric_type) → expected_rate`. Grades cover `A`, `B`, `C`, `D`, `E`, `F^`, `F*^`, `F**^` at MOBs 1, 2, 3, 4, 6, 9. Metrics: `30+`, `60+`, `default`.

```yaml
expectations:
- riskgrade: A
  mob: 9
  metric_type: default
  expected_rate: 0.015
- riskgrade: A
  mob: 1
  metric_type: 30+
  expected_rate: 0.00429
# ...
```

Powers the dashed expected lines on DQ charts (styles #1, #2, #3, #4, #5, #6). Bundle a copy of the reference's `expectations.yaml` into `motor_graphs/data/expectations.yaml` so v0.1 works without re-extracting it from Snowflake.
