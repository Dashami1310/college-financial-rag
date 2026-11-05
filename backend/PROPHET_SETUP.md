# Prophet Forecasting Engine — Setup & Verification

## Status

Prophet is **implemented and reviewed** in `app/services/forecasting.py`
(`_prophet_forecast`), and wired into `forecast_department(df, department,
engine="prophet")`. It was **not executed** during development, because
Prophet's `cmdstanpy` backend needs to compile Stan models on first use and
requires more disk space than was available in the sandbox this project was
built in (~2-3GB free at the time). ARIMA (the default engine) and every
other module in this project **have** been run and verified — this is the
one exception, called out explicitly so you know exactly what to check.

## Installation

```bash
pip install prophet
```

The first import of `prophet` after installation triggers `cmdstanpy` to
download and compile a CmdStan toolchain (a few hundred MB, one-time,
several minutes). If that step fails, see
https://facebook.github.io/prophet/docs/installation.html for
platform-specific notes (Prophet on Windows sometimes needs a C++ build
toolchain).

## How to verify it works

1. Make sure you have a report with at least 4 periods of data for some
   department (the seeded sample data — one financial year x 4 quarters —
   qualifies).
2. Start the backend, log in, and call:
   ```bash
   curl -X GET "http://localhost:8000/api/forecast?department=AIML" \
        -H "Authorization: Bearer <your_token>"
   ```
3. Check the response's `forecast[0].engine` field:
   - `"prophet"` -> Prophet ran successfully.
   - `"arima"` or `"weighted_moving_average"` -> Prophet failed silently
     and the code fell back (check server logs for `[WARN] Prophet
     forecast failed for <dept>, falling back: <reason>` — that's the
     exact exception message to debug).

## Engine selection

`GET /api/forecast?engine=arima` (default) or `GET /api/forecast?engine=prophet`
— already wired through the API. `FORECAST_ENGINE` in `.env` sets the
default when no `engine` query param is supplied.

## Known limitations to check once you can run it

- **Short histories**: `forecast_department` only *attempts* Prophet when
  a department has 4+ historical periods — Prophet typically needs more
  data than that to produce a stable seasonal fit. With only 4 quarterly
  points (as in the seeded sample data), Prophet may produce a very wide
  confidence interval or an unstable trend; this is expected statistical
  behavior, not a bug, and will improve once more financial years are
  uploaded.
- **Synthetic date index**: because the `transactions` table stores
  `financial_year` + `quarter` as strings rather than real dates, the
  Prophet integration builds a synthetic quarterly `ds` column ending at
  "today" (`pd.date_range(..., freq="QS")`). This is fine for producing a
  next-period forecast but disables Prophet's own calendar-based
  seasonality detection (`yearly_seasonality=False` is set deliberately
  for this reason). If you want full seasonality support, add a real
  `period_start` date column to `Transaction` in a future migration.
