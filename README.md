# Lead Qualification Platform Backend

Production-ready FastAPI backend foundation using Python 3.11.9, PostgreSQL, SQLAlchemy,
Alembic, and Pydantic V2.

## Folder Structure

```text
.
+-- src/app
|   +-- api/v1              # Versioned HTTP routes
|   +-- core                # Settings and logging
|   +-- db                  # SQLAlchemy engine, sessions, base metadata
|   +-- dependencies        # FastAPI dependency providers
|   +-- models              # SQLAlchemy models package
|   +-- schemas             # Pydantic response/request schemas
|   +-- main.py             # FastAPI application factory
+-- migrations              # Alembic migration environment
+-- docker-compose.yml      # API + PostgreSQL
+-- Dockerfile              # API image
+-- alembic.ini
+-- pyproject.toml
```

## Local Installation

1. Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create your environment file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

4. Start PostgreSQL:

```bash
docker compose up -d postgres
```

5. Run migrations:

```bash
alembic upgrade head
```

6. Start the API:

```bash
PYTHONPATH=src uvicorn app.main:app --reload
```

On Windows PowerShell:

```powershell
$env:PYTHONPATH = "src"
uvicorn app.main:app --reload
```

## Docker

Create `.env` from `.env.example`, then run:

```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`.

## Health Check

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "Lead Qualification Platform",
  "environment": "local",
  "database": "ok"
}
```

## Rule-Based Lead Qualification Engine

The project includes a configurable scoring engine that accepts lead information and buyer
information, applies explainable YAML rules, normalizes the score to `0-100`, and classifies the
lead as `HOT`, `WARM`, or `COLD`.

### Architecture

```text
configs/lead_scoring.yml
        |
        v
LeadQualificationEngine
        |
        +-- evaluates lead_information rules
        +-- evaluates buyer_information rules
        +-- weights each rule section
        +-- normalizes weighted score to 0-100
        +-- classifies using YAML thresholds
        v
POST /lead-scoring/score
POST /lead-scoring/distribution
```

The engine is implemented as a pure Python service in
`src/app/services/lead_scoring.py`, with HTTP request and response models in
`src/app/schemas/lead_scoring.py`. The FastAPI route lives at
`src/app/api/v1/lead_scoring.py`.

The same engine also provides an explanation endpoint that accepts lead data and a lead score,
then returns structured JSON with:

- why the score is high
- why the score is low
- biggest positive factors
- biggest negative factors
- recommended next action

### Configuration

Scoring is configured in `configs/lead_scoring.yml`. The default weights are:

- `lead_information`: 60% of the final score
- `buyer_information`: 40% of the final score
- `HOT`: score >= 75
- `WARM`: score >= 45 and < 75
- `COLD`: score < 45

Default rule points are distributed like this:

| Section | Rule | Raw Points | What earns the points |
| --- | --- | ---: | --- |
| Lead Information | `decision_maker_title` | 25 | Job title contains founder, owner, CEO/CXO, director, head, VP, or vice president |
| Lead Information | `valid_contact_email` | 10 | Email contains `@` |
| Lead Information | `phone_available` | 8 | Phone is present |
| Lead Information | `high_intent_source` | 17 | Source is `demo_request`, `pricing_request`, `referral`, or `indiamart` |
| Buyer Information | `target_industry` | 15 | Industry is software, manufacturing, industrial automation, or logistics |
| Buyer Information | `employee_count_fit` | 12 | Employee count is between 50 and 1000 |
| Buyer Information | `revenue_fit` | 8 | Annual revenue is at least 1,000,000 USD |
| Buyer Information | `target_country` | 5 | Country is US, USA, United States, or India |

The raw rule points are normalized by section weight:

```text
section score = earned raw section points / possible raw section points * section weight
final score = sum(section scores) / sum(section weights) * 100
lost points = possible normalized points - earned normalized points
```

With the default YAML, `lead_information` contributes up to 60 normalized points and
`buyer_information` contributes up to 40 normalized points. A lead becomes `HOT` at `75+`, `WARM`
from `45-74`, and `COLD` below `45`.

Supported rule types:

- `exists`: field is present and non-empty
- `equals_any`: normalized field equals one configured value
- `contains`: normalized field contains a configured value
- `contains_any`: normalized field contains any configured value
- `range`: numeric field is between `min` and `max`
- `min`: numeric field is at least `min`
- `boolean_true`: field is exactly `true`

Set `LEAD_SCORING_CONFIG_PATH` to point the API at a different YAML file.

### API Usage

```bash
curl -X POST http://localhost:8000/lead-scoring/score \
  -H "Content-Type: application/json" \
  -d '{
    "lead_information": {
      "job_title": "Founder",
      "email": "founder@example.com",
      "source": "pricing_request"
    },
    "buyer_information": {
      "industry": "Logistics",
      "employee_count": 75,
      "annual_revenue_usd": 1200000,
      "country": "United States"
    }
  }'
```

Response:

```json
{
  "score": 92,
  "category": "HOT",
  "reasons": [
    "Decision-maker title matched.",
    "Lead has a usable email address.",
    "Lead source indicates buying intent.",
    "Buyer industry is in the target market.",
    "Buyer company size fits the ideal customer profile.",
    "Buyer revenue suggests ability to purchase.",
    "Buyer is in a supported target geography."
  ]
}
```

Get the exact points distribution for a lead:

```bash
curl -X POST http://localhost:8000/lead-scoring/distribution \
  -H "Content-Type: application/json" \
  -d '{
    "lead_information": {
      "job_title": "Founder",
      "email": "founder@example.com",
      "source": "pricing_request"
    },
    "buyer_information": {
      "industry": "Logistics",
      "employee_count": 75,
      "annual_revenue_usd": 1200000,
      "country": "United States"
    }
  }'
```

Distribution response:

```json
{
  "score": 92,
  "category": "HOT",
  "normalized_points_possible": 100.0,
  "normalized_points_earned": 92.0,
  "normalized_points_lost": 8.0,
  "sections": [
    {
      "section": "lead_information",
      "section_label": "Lead Information",
      "section_weight": 60.0,
      "raw_points_possible": 60.0,
      "raw_points_earned": 52.0,
      "raw_points_lost": 8.0,
      "normalized_points_possible": 60.0,
      "normalized_points_earned": 52.0,
      "normalized_points_lost": 8.0,
      "rules": [
        {
          "name": "decision_maker_title",
          "field": "job_title",
          "observed_value": "Founder",
          "matched": true,
          "raw_points_possible": 25.0,
          "raw_points_earned": 25.0,
          "raw_points_lost": 0.0,
          "normalized_points_possible": 25.0,
          "normalized_points_earned": 25.0,
          "normalized_points_lost": 0.0,
          "explanation": "Decision-maker title matched."
        },
        {
          "name": "phone_available",
          "field": "phone",
          "observed_value": null,
          "matched": false,
          "raw_points_possible": 8.0,
          "raw_points_earned": 0.0,
          "raw_points_lost": 8.0,
          "normalized_points_possible": 8.0,
          "normalized_points_earned": 0.0,
          "normalized_points_lost": 8.0,
          "explanation": "Phone available was not satisfied because phone is missing."
        }
      ]
    }
  ],
  "reasons": [
    "Decision-maker title matched.",
    "Lead has a usable email address.",
    "Lead source indicates buying intent.",
    "Buyer industry is in the target market.",
    "Buyer company size fits the ideal customer profile.",
    "Buyer revenue suggests ability to purchase.",
    "Buyer is in a supported target geography."
  ]
}
```

The response includes all configured sections and all rules. The shortened example above shows only
two lead rules to keep the shape readable.

Explain an existing lead score:

```bash
curl -X POST http://localhost:8000/lead-scoring/explain \
  -H "Content-Type: application/json" \
  -d '{
    "score": 92,
    "lead_information": {
      "job_title": "Founder",
      "email": "founder@example.com",
      "source": "pricing_request"
    },
    "buyer_information": {
      "industry": "Logistics",
      "employee_count": 75,
      "annual_revenue_usd": 1200000,
      "country": "United States"
    }
  }'
```

Explanation response:

```json
{
  "score": 92,
  "category": "HOT",
  "explanation": "Lead score is 92 (HOT) because Decision-maker title matched. The biggest remaining gap is: Phone available was not satisfied because phone is missing.",
  "why_score_is_high": [
    "Decision-maker title matched.",
    "Lead source indicates buying intent.",
    "Buyer industry is in the target market."
  ],
  "why_score_is_low": [
    "Phone available was not satisfied because phone is missing."
  ],
  "biggest_positive_factors": [
    {
      "name": "decision_maker_title",
      "section": "lead_information",
      "section_label": "Lead Information",
      "field": "job_title",
      "observed_value": "Founder",
      "impact": "positive",
      "points": 25,
      "explanation": "Decision-maker title matched."
    }
  ],
  "biggest_negative_factors": [
    {
      "name": "phone_available",
      "section": "lead_information",
      "section_label": "Lead Information",
      "field": "phone",
      "observed_value": null,
      "impact": "negative",
      "points": 8,
      "explanation": "Phone available was not satisfied because phone is missing."
    }
  ],
  "recommended_next_action": "Contact this lead immediately and prioritize a direct sales follow-up."
}
```

### Example Calculations

Hot lead:

- Lead section earns `52 / 60` rule points, then receives `52` weighted points.
- Buyer section earns `40 / 40` rule points, then receives `40` weighted points.
- Normalized score: `92 / 100 = 92%`.
- Classification: `HOT`.

Cold partial-fit lead:

- Lead section earns `10 / 60` rule points, then receives `10` weighted points.
- Buyer section earns `32 / 40` rule points, then receives `32` weighted points.
- Normalized score: `42 / 100 = 42%`.
- Classification: `COLD`.

## Migrations

Create a new migration after changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

## IndiaMART Lead Extraction

The project includes a Playwright worker that logs in to IndiaMART Seller, navigates to Buy
Leads, extracts lead attributes, and stores them through the FastAPI API at
`/api/v1/indiamart/leads/batch`.

1. Install Python dependencies and Playwright browsers:

```bash
pip install -r requirements.txt
playwright install chromium
```

2. Configure `.env`:

```env
INDIAMART_MOBILE_NUMBER=your_mobile_number
INDIAMART_HEADLESS=false
INDIAMART_API_BASE_URL=http://localhost:8000/api/v1
INDIAMART_MAX_PAGES=10
INDIAMART_OPEN_LEAD_DETAILS=false
```

IndiaMART login uses mobile number plus OTP. For the first run, keep
`INDIAMART_HEADLESS=false`; the worker fills `INDIAMART_MOBILE_NUMBER`, waits for you to complete
OTP verification in the browser, and saves browser state to
`.runtime/indiamart/storage_state.json`. Later runs reuse that session until IndiaMART expires it.

3. Run the API and migrations:

```powershell
$env:PYTHONPATH = "src"
alembic upgrade head
uvicorn app.main:app --reload
```

4. In another terminal, run extraction:

```powershell
$env:PYTHONPATH = "src"
python -m app.automation.indiamart
```

Selectors are configured in
`src/app/automation/indiamart/selectors/buy_leads.json`. Update that JSON when IndiaMART changes
DOM attributes or class names; the worker accepts multiple selector candidates for each field.
By default the worker does not open individual lead detail actions, buy leads, unlock contacts, or
click contact buttons. Keep `INDIAMART_OPEN_LEAD_DETAILS=false` unless you have verified that the
configured detail selector only opens a read-only panel.

Extracted fields:

- Product Name, Product Category, Quantity, Order Value, Purpose, Lead Time
- Buyer Name, Business Name
- Phone, Email, WhatsApp, Business, and Address availability flags
- Years Active, Requirements Count, Replies Count
- City and State

The extractor retries failed page/card/API operations, logs progress with the project logging
configuration, handles pagination up to `INDIAMART_MAX_PAGES`, and posts leads in configurable
batches. Reposting the same lead updates the existing row by fingerprint rather than inserting a
duplicate.

## Report Delivery Agent

The delivery agent generates `Lead_Intelligence_Report.xlsx`, validates the file, builds an
executive summary, sends the report by email and Telegram, and logs each recipient result in
`report_delivery_logs`.

1. Install dependencies and run migrations:

```powershell
pip install -r requirements.txt
alembic upgrade head
```

2. Configure delivery environment variables:

```env
REPORT_OUTPUT_PATH=Lead_Intelligence_Report.xlsx

SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SMTP_SENDER=reports@example.com
REPORT_EMAIL_RECIPIENTS=owner@example.com,sales@example.com

TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=123456789

REPORT_DELIVERY_RETRY_ATTEMPTS=3
REPORT_DELIVERY_RETRY_BACKOFF_SECONDS=2
```

3. Send one report immediately:

```powershell
$env:PYTHONPATH = "src"
python -m app.delivery.main
```

4. Enable scheduled delivery with FastAPI:

```env
REPORT_SCHEDULER_ENABLED=true
DAILY_REPORT_TIME=09:00
WEEKLY_REPORT_DAY=mon
MONTHLY_REPORT_DAY=1
```

The scheduler starts with the FastAPI lifespan when `REPORT_SCHEDULER_ENABLED=true` and registers
daily, weekly, and monthly delivery jobs using APScheduler.
