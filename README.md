# ASTRA-MIND

AI-assisted astronaut health monitoring and physiological digital twin prototype for long-duration space missions.

**All data is SYNTHETIC.** Scores show deviation from a person's own baseline. They are not disease probabilities or diagnoses, and any finding needs medical review.

## What it does

- Monitors five health domains with ten simulated signals:
  - Cardiovascular: heart rate, HRV, SpO₂
  - Musculoskeletal: grip strength, squat power
  - Immune: CRP, IL-6
  - Behavioral: sleep, stress index
  - Radiation: dose rate, plus cumulative dose
- Learns a personal baseline for each crew member.
- Flags anomalies and links alerts that appear across several domains.
- Forecasts 24 hours ahead with a 90% interval.
- Summarises status as a digital twin score per domain and overall.
- Keeps monitoring during a simulated communications outage, then syncs to the Earth side after reconnection.

## Run it

Requires Python 3.10 or newer.

```bash
pip install -r requirements.txt
cd backend
uvicorn app:app --port 8000
```

Open http://localhost:8000.

Run the tests from the project folder:

```bash
pytest tests
```

## Using the dashboard

- Choose a crew member, pause or resume, and change the simulation speed.
- **Inject event** pushes a chosen domain away from normal, for example a radiation spike.
- **Start comms outage** stops Earth-side sync. Watch the sync queue grow and alerts show "onboard only".
- **Restore link** flushes the queue to Earth.
- Click any metric to see its 24 hour forecast.
- **Reset** clears the selected crew member's data.

## Project layout

```
backend/engine.py     synthetic data, baselines, anomalies, forecast, twin
backend/app.py        FastAPI service and SQLite storage
frontend/index.html   dashboard (plain HTML, CSS, JavaScript)
tests/test_all.py     automated tests
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/state?crew=0` | Full snapshot: series, twin scores, alerts, sync counts |
| POST | `/api/step?crew=0&n=1` | Advance the simulation by n hours (max 48) |
| POST | `/api/event?domain=Radiation` | Inject a simulated event |
| POST | `/api/link?up=false` | Start or end a communications outage |
| POST | `/api/reset?crew=0` | Reset a crew member |
| GET | `/api/history?sid=hr` | Stored raw measurements for one signal |

## How it works

- **Synthetic data:** each reading is a per-person baseline plus Gaussian noise, with a daily cycle on heart rate. Slow measurements (grip, power, CRP, IL-6, sleep) update every 6 hours.
- **Personal baseline:** the median and MAD (scaled by 1.4826) of the first 72 simulated hours. The spread has a floor of 60% of the nominal value.
- **Anomalies:** robust z-score, flagged above 3.5. Repeat alerts for one signal are held back for 12 hours. A cross-domain alert fires when two or more domains alert within 8 hours.
- **Forecast:** damped-trend Holt smoothing with an interval that widens with the horizon. It is a lightweight stand-in for Chronos-2.
- **Digital twin:** each domain scores 100 minus 20 for every SD the worst signal in the last 6 hours sits beyond 1.5. At 85 and above it reads Nominal, 60 to 84 is Watch, and below 60 is Review.
- **Offline sync:** every raw measurement is stored with a provenance tag and a synced flag. During an outage the unsynced rows form the queue, and restoring the link marks them synced.

## Known limitations

- Anomaly detection is a z-score rule. Isolation Forest, XGBoost and conformal prediction are not implemented.
- Forecasting is Holt smoothing, not Chronos-2 or TimesFM.
- No MedGemma or RAG medical assistant.
- The frontend is plain JavaScript, not React and TypeScript.
- Alerts are held in memory and reset when the server restarts. Measurements persist in `backend/astra.db`.
- No Docker setup, authentication or real sensor ingestion.

## Next steps

Isolation Forest and Chronos-2, a React and TypeScript frontend, MedGemma with retrieval over approved NASA documents, and Docker deployment.

