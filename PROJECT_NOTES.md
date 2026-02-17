# Pega Attestations - Project Notes

## Overview

Internal tool for a CFO group at a major bank. Enables users to query their attestation data via natural language through an LLM-powered API. Attestations represent transits/accounts from branches that owners within the group must attest to monthly as part of an approval workflow.

**Core use cases from user perspective:** (see detailed query catalog below)

## Architecture

```
┌─────────────┐       ┌──────────────────────────────────────────────┐
│   Mock UI   │       │           Python FastAPI Service              │
│  (our dev   │──────▶│                                              │
│   mockup)   │ POST  │  1. Receive query + employee_id              │
│             │◀──────│  2. Lookup employee_id → name (user cache)   │
│  Eventually │       │  3. Filter data to user's records            │
│  replaced   │       │  4. LLM constructs SQL against filtered data │
│  by real UI │       │  5. Execute SQL, get raw records             │
│             │       │  6. LLM summarizes results                   │
│             │       │  7. Return records + summary                 │
└─────────────┘       └──────┬──────────────────┬────────────────────┘
                             │                  │
                     ┌───────▼───────┐  ┌───────▼────────┐
                     │  Cache Layer  │  │  LLM Endpoint  │
                     │  (SQLite)     │  │  (On-prem GPT) │
                     │               │  │  GPT-5 / 5.1   │
                     │ - user_dir    │  └────────────────┘
                     │ - full_data   │
                     │ - scrubbed    │
                     └───────▲───────┘
                             │ scheduled refresh
                     ┌───────┴────────┐
                     │  Data Source   │
                     │               │
                     │ Phase 1: CSV  │
                     │ Phase 2: SQL  │
                     │   (Postgres)  │
                     └───────────────┘
```

## Data Sources

### Phase 1: CSV/Excel Extracts (Current)
- Manually pulled sample data from the Pega system
- Two files: user directory table + data table
- **We cannot see these files directly** — they live on a secured work computer
- Strategy: build EDA scripts, push code to repo, run on work machine, share output back

### Phase 2: Database Connections (Future)
- Replace CSV ingestion with live Postgres (or whatever the source DB is) queries
- Same caching logic, just different data source

## Data Tables

### 1. User Directory Table
- Maps employee IDs to first/last names
- ~2,000 users
- **Cache refresh: every 1 hour**
- Used for: resolving employee_id from API call → name for filtering

### 2. Full Data Table (User-Filtered)
- ~50 columns per row
- Each row = one attestation record (transit/account someone is responsible for)
- New records added monthly (current month attestations)
- Contains some date column(s) for current vs historical filtering
- Key fields include preparer and approver columns
- **Cache refresh: every 15 minutes**
- Used for: answering user-specific queries after filtering to their records
- **Access: only the user's own records (filtered by preparer/approver match)**

### 3. Scrubbed Data Table (Public View)
- Same source as full data table, but only a subset of columns retained
- Columns chosen to answer general questions (e.g., transit assignment, approver)
- Recreated at same interval as full data table refresh
- **Cache refresh: every 15 minutes (same as full data)**
- **Access: all users can query this table**

### 4. Data Admin Mapping (Reference Data)
- Maps divisions to their data admin contacts
- Source: scraped or manually pulled from internal Connect site
- Used for: answering "who do I contact to move my lines?" queries
- **Cache refresh: manual or low-frequency (changes infrequently)**

### 5. Deadline / Process Info (Reference Data)
- Attestation deadlines by role (preparer, AM, etc.)
- Source: scraped or manually pulled from internal Connect site
- Used for: answering "when is the deadline?" queries
- Ideally scraped so the tool can answer directly with dates + link to Connect
- **Cache refresh: manual or low-frequency**

## Query Catalog

These are the known query types the tool must support, with implementation notes.

### Q1: "What lines are assigned to me this month?"
- **Type**: Personal (uses filtered full data)
- **Flow**: Lookup user → filter data by user (preparer/approver fields) + current month → return all matching lines
- **Output**: File/table of all lines assigned to the user for the current month
- **Key fields**: user identity fields, date/month column, status

### Q2: "What lines are newly assigned to me this month?"
- **Type**: Personal (uses filtered full data)
- **Flow**: Compare current month's assignments vs previous month → return lines that are new (present this month but not last month)
- **Output**: File/table of newly assigned lines only
- **Implies**: need a way to identify lines across months (some unique line/transit ID) and compare month-over-month
- **Key fields**: unique line identifier, date/month column, user identity fields

### Q3: "I am changing roles and need to move my lines. Who do I contact?"
- **Type**: Personal + reference data lookup
- **Flow**:
  1. Find user's assigned lines
  2. Check the **division** field on those lines
  3. Look up the data admin for each division (from data admin mapping)
  4. Return data admin contact names
- **Data needed**: division column in attestation data + data admin mapping table
- **Source for mapping**: Connect site (scrape or manual pull)

### Q4: "I am a new user and need Pega access. What do I do?"
- **Type**: Static/informational (no data lookup needed)
- **Flow**: Return canned response:
  1. Go to [link] to set up your account
  2. Go to the Connect site to contact the data admin for the lines you're taking over
- **Note**: This could be handled by the LLM with a system prompt containing this info, no SQL needed

### Q5: "When is the preparer/AM/etc. deadline?"
- **Type**: Reference data lookup
- **Flow**: Look up deadline dates by role from cached deadline info
- **Output**: Deadline dates + link to Connect site for full details
- **Data needed**: deadline/calendar reference table (scraped from Connect or manually maintained)
- **Ideal**: scrape Connect so the tool has actual dates and can answer directly

### Q6: "What lines are in my workbasket?"
- **Type**: Personal (uses filtered full data)
- **Flow**: Filter to user's lines → check status field for tasks pending the user's specific role
- **Output**: Lines where the workflow status indicates it's currently in the user's court
- **Key fields**: status column, user role in workflow (preparer vs approver vs AM etc.)

### Q7: "Are there any lines in my queue?"
- **Type**: Personal (uses filtered full data) — broader than Q6
- **Flow**: Check all tasks that are either:
  1. In the user's own workbasket (same as Q6), OR
  2. Lines where the user is assigned in the hierarchy BUT the status is sitting in a previous workflow user's workbasket
- **Example**: For a group head, would pick up all lines where status is `pending-attestation-new`, `pending-reassign-pr-acceptance`, etc. — anything upstream of or at their position in the flow
- **Key fields**: status column, user's role in hierarchy, workflow stage mapping
- **Implies**: need to understand the full workflow status progression and which statuses map to which roles

## Workflow Status Model (TBD — Need from EDA)

The attestation workflow has multiple stages. Each status value maps to a specific role's workbasket. Understanding this is critical for Q6 and Q7.

```
Expected flow (to be confirmed via EDA):

  [New] → Preparer → [Pending Review] → Approver/AM → [Approved] → ...

Status values observed (examples from Q7 description):
  - pending-attestation-new
  - pending-reassign-pr-acceptance
  - (others TBD)
```

**Need to map**: status value → which role it's "sitting with" → workflow ordering

## Additional Data Sources (Beyond DB)

### Connect Site (Internal)
- Contains:
  - **Data admin mapping** by division (needed for Q3)
  - **Deadline calendar** by role (needed for Q5)
  - Other process documentation
- **Strategy**: scrape or manually pull this data and store as reference tables in the cache
- This data changes infrequently — manual refresh or very low-frequency scrape is fine

### Static/Canned Responses
- Some queries (like Q4) are purely informational
- These can be embedded in the LLM system prompt or stored as a small reference table
- No SQL needed — LLM just needs to know the correct response

## Cache Strategy

- **SQLite files** on disk (not in-memory) — keeps memory footprint low, still supports SQL queries
- One SQLite DB with the following tables:

| Table | Source | Refresh |
|-------|--------|---------|
| `user_directory` | CSV → DB (Phase 2) | Every 1 hr |
| `attestation_data` | CSV → DB (Phase 2) | Every 15 min |
| `attestation_scrubbed` | Derived from attestation_data | Every 15 min (same cycle) |
| `data_admin_mapping` | Connect site scrape / manual | Manual / low-frequency |
| `deadlines` | Connect site scrape / manual | Manual / low-frequency |

- Refresh runs on independent configurable schedules
- The LLM agent constructs SQL queries against these SQLite tables
- No live DB queries during API request handling — always reads from cache
- Reference tables (data_admin_mapping, deadlines) can be loaded from small CSV/JSON files initially

## Query Flow (Detail)

1. **UI** sends POST to API: `{ "query": "what tasks are assigned to me?", "employee_id": "E12345" }`
2. **Auth**: employee_id is trusted as-is (UI/gateway handles authentication)
3. **User Lookup**: query `user_directory` cache → resolve employee_id to first_name, last_name
4. **Data Filtering**: filter `attestation_data` where preparer or approver matches user's name
5. **LLM Agent**: receives the user query + filtered data context
   - Constructs SQL to answer the specific question against the filtered data
   - Executes the SQL
   - Gets raw result records
6. **LLM Summary**: generates natural language summary of results with metadata
   - e.g., "Here are your 4 attestations — 2 are open and 2 were recently closed"
7. **Response**: return both raw records and LLM summary to UI

For **public/scrubbed queries** (e.g., "who is transit X assigned to?"):
- LLM agent recognizes this is a general query
- Queries `attestation_scrubbed` table instead
- Same SQL construction + summary flow

## Tech Stack

| Component | Choice |
|-----------|--------|
| Language | Python |
| API Framework | FastAPI |
| Cache Storage | SQLite (file-based) |
| LLM | GPT-5 / GPT-5.1 (on-prem endpoint) |
| Deployment | OpenShift (on-prem server) |
| Data Source (Phase 1) | CSV/Excel extracts |
| Data Source (Phase 2) | PostgreSQL |
| UI (Dev) | Custom mockup (we build) |
| UI (Prod) | Separate team's UI |

## Domain Context

- **Organization**: CFO group at a major Canadian bank
- **Domain**: Finance — attestation management
- **Pega Attestations**: system tracking transit/account attestations
- **Transit**: a bank branch identifier that needs periodic attestation
- **Attestation flow**: preparer creates → approver reviews → attestation completed
- **Cycle**: monthly — new attestations added throughout the month
- **Users**: ~2,000 within the group

## Open Questions / TBD

### Data Schema (Phase 0 EDA will answer most of these)
- [ ] Exact schema of user directory table (columns, ID format)
- [ ] Exact schema of data table (~50 columns — need EDA to understand)
- [ ] Which columns go into the scrubbed/public table
- [ ] How date filtering works (which column, what values = current vs historical)
- [ ] Exact format of employee_id (numeric, alphanumeric, prefixed?)
- [ ] Whether filtering is on preparer, approver, or both (or other role fields)
- [ ] What is the unique identifier for a line/transit (needed for Q2 month-over-month comparison)
- [ ] Full list of status values and what workflow stage they represent
- [ ] Which status values map to which roles in the workflow (needed for Q6/Q7)
- [ ] What the "division" field looks like (needed for Q3 data admin lookup)

### Infrastructure
- [ ] LLM endpoint URL and auth details
- [ ] Connect site URL and scrape feasibility
- [ ] Data admin mapping — can we get a CSV/table of division → admin name?
- [ ] Deadline calendar — can we get a structured version?

### Design Decisions (Post-EDA)
- [ ] How does the LLM agent decide which table to query (personal vs scrubbed vs reference)?
- [ ] How to handle Q7's "queue" logic — hardcoded workflow mapping or dynamic?
- [ ] File export format for Q1/Q2 responses (CSV download? inline table?)

## Development Phases

### Phase 0: Data Exploration (NEXT)
- Build EDA scripts that can run against the CSV/Excel sample extracts
- Generate visual reports (charts, schema info, value distributions)
- Share output back to inform schema understanding and design decisions

### Phase 1: Core MVP (CSV-backed)
- FastAPI service with SQLite cache
- CSV → SQLite cache loader with configurable refresh
- User lookup + data filtering logic
- LLM agent for SQL construction + summarization
- Mock UI for testing

### Phase 2: Database Integration
- Replace CSV loaders with Postgres connectors
- Same cache/API layer, different data source

### Phase 3: Production
- Connect to real UI (separate team)
- OpenShift deployment
- Monitoring, logging, error handling hardening
