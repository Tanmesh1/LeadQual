# Lead Qualification Platform Database Schema

This schema is normalized around buyers, buyer-specific leads, lead scoring history,
activity timelines, and outcome labels for analytics and machine learning.

## buyers

Stores buyer/customer profiles and their qualification preferences.

| Column | Type | Constraints |
| --- | --- | --- |
| id | UUID | Primary key |
| name | VARCHAR(255) | Not null |
| domain | VARCHAR(255) | Unique index, nullable |
| website_url | VARCHAR(500) | Nullable |
| industry | VARCHAR(150) | Nullable |
| employee_count_min | INTEGER | Nullable, `>= 0` |
| employee_count_max | INTEGER | Nullable, `>= employee_count_min` |
| annual_revenue_usd | NUMERIC(18, 2) | Nullable, `>= 0` |
| target_markets | JSONB | Not null, default `{}` |
| ideal_customer_profile | JSONB | Not null, default `{}` |
| is_active | BOOLEAN | Not null, default `true` |
| created_at | TIMESTAMPTZ | Not null, default `now()` |
| updated_at | TIMESTAMPTZ | Not null, default `now()` |

Indexes: `ix_buyers_name`, unique `ix_buyers_domain`, `ix_buyers_industry`.

## leads

Stores buyer-owned lead records. Email is unique per buyer, not globally unique.

| Column | Type | Constraints |
| --- | --- | --- |
| id | UUID | Primary key |
| buyer_id | UUID | FK to `buyers.id`, not null, `ON DELETE RESTRICT` |
| email | VARCHAR(320) | Not null |
| first_name | VARCHAR(100) | Nullable |
| last_name | VARCHAR(100) | Nullable |
| job_title | VARCHAR(255) | Nullable |
| phone | VARCHAR(50) | Nullable |
| linkedin_url | VARCHAR(500) | Nullable |
| source | VARCHAR(100) | Nullable |
| status | VARCHAR(50) | Not null, allowed: `new`, `contacted`, `qualified`, `disqualified`, `converted`, `archived` |
| company_name | VARCHAR(255) | Nullable |
| company_domain | VARCHAR(255) | Nullable |
| company_website_url | VARCHAR(500) | Nullable |
| company_industry | VARCHAR(150) | Nullable |
| company_employee_count | INTEGER | Nullable, `>= 0` |
| company_annual_revenue_usd | NUMERIC(18, 2) | Nullable, `>= 0` |
| country | VARCHAR(100) | Nullable |
| region | VARCHAR(100) | Nullable |
| city | VARCHAR(100) | Nullable |
| timezone | VARCHAR(100) | Nullable |
| raw_payload | JSONB | Not null, default `{}` |
| created_at | TIMESTAMPTZ | Not null, default `now()` |
| updated_at | TIMESTAMPTZ | Not null, default `now()` |

Indexes and constraints: unique `uq_leads_buyer_email`, `ix_leads_buyer_id`,
`ix_leads_email`, `ix_leads_company_name`, `ix_leads_status`, `ix_leads_source`,
`ix_leads_created_at`.

## lead_scores

Stores immutable scoring events, enabling score trend analysis and model comparison.

| Column | Type | Constraints |
| --- | --- | --- |
| id | UUID | Primary key |
| lead_id | UUID | FK to `leads.id`, not null, `ON DELETE CASCADE` |
| score_value | NUMERIC(5, 2) | Not null, `0 <= value <= 100` |
| score_band | VARCHAR(50) | Nullable, allowed: `cold`, `warm`, `hot`, `qualified` |
| scoring_method | VARCHAR(100) | Not null |
| model_name | VARCHAR(150) | Nullable |
| model_version | VARCHAR(100) | Nullable |
| feature_snapshot | JSONB | Not null, default `{}` |
| explanation | TEXT | Nullable |
| scored_at | TIMESTAMPTZ | Not null, default `now()` |
| created_at | TIMESTAMPTZ | Not null, default `now()` |

Indexes: `ix_lead_scores_lead_id`, `ix_lead_scores_scored_at`,
`ix_lead_scores_model`, `ix_lead_scores_lead_scored_at`,
GIN `ix_lead_scores_feature_snapshot_gin`.

## lead_activity_logs

Stores time-series lead engagement and system activity.

| Column | Type | Constraints |
| --- | --- | --- |
| id | UUID | Primary key |
| lead_id | UUID | FK to `leads.id`, not null, `ON DELETE CASCADE` |
| activity_type | VARCHAR(100) | Not null |
| actor_type | VARCHAR(50) | Not null, allowed: `system`, `user`, `lead`, `buyer`, `integration` |
| actor_id | VARCHAR(255) | Nullable |
| channel | VARCHAR(50) | Nullable, allowed: `email`, `phone`, `sms`, `web`, `chat`, `crm`, `social`, `event`, `other` |
| subject | VARCHAR(255) | Nullable |
| description | TEXT | Nullable |
| external_id | VARCHAR(255) | Nullable |
| activity_metadata | JSONB | Not null, default `{}` |
| occurred_at | TIMESTAMPTZ | Not null |
| created_at | TIMESTAMPTZ | Not null, default `now()` |

Indexes: `ix_lead_activity_logs_lead_id`, `ix_lead_activity_logs_activity_type`,
`ix_lead_activity_logs_channel`, `ix_lead_activity_logs_occurred_at`,
`ix_lead_activity_logs_lead_occurred_at`, GIN `ix_lead_activity_logs_metadata_gin`.

## lead_outcomes

Stores qualification and conversion labels. Multiple historical outcomes are allowed,
with one current outcome per lead enforced by a partial unique index.

| Column | Type | Constraints |
| --- | --- | --- |
| id | UUID | Primary key |
| lead_id | UUID | FK to `leads.id`, not null, `ON DELETE CASCADE` |
| outcome_type | VARCHAR(50) | Not null, allowed: `qualified`, `disqualified`, `converted`, `lost`, `nurture`, `duplicate`, `invalid` |
| outcome_reason | VARCHAR(255) | Nullable |
| notes | TEXT | Nullable |
| deal_value_usd | NUMERIC(18, 2) | Nullable, `>= 0` |
| confidence | NUMERIC(4, 3) | Nullable, `0 <= confidence <= 1` |
| label_source | VARCHAR(100) | Nullable |
| is_current | BOOLEAN | Not null, default `true` |
| outcome_metadata | JSONB | Not null, default `{}` |
| closed_at | TIMESTAMPTZ | Nullable |
| created_at | TIMESTAMPTZ | Not null, default `now()` |
| updated_at | TIMESTAMPTZ | Not null, default `now()` |

Indexes: `ix_lead_outcomes_lead_id`, `ix_lead_outcomes_outcome_type`,
`ix_lead_outcomes_closed_at`, `ix_lead_outcomes_label_source`,
partial unique `uq_lead_outcomes_current_lead`, GIN `ix_lead_outcomes_metadata_gin`.
## IndiaMART Leads

`indiamart_leads` stores raw IndiaMART Buy Leads extracted by the Playwright automation worker.
Rows are idempotent by `lead_fingerprint`, a deterministic SHA-256 generated from the IndiaMART
lead id and buyer/product/location fields when the source does not expose a stable id.

Key columns:

- `product_name`, `product_category`, `quantity`, `order_value`, `purpose`, `lead_time`
- `buyer_name`, `business_name`
- `phone_available`, `email_available`, `whatsapp_available`, `business_available`,
  `address_available`
- `years_active`, `requirements_count`, `replies_count`
- `city`, `state`, `source_url`, `raw_payload`, `extracted_at`

Indexes cover product, buyer, business, city/state, extraction time, and JSONB raw payload search.
