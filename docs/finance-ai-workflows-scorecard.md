# 20 Finance Workflows Worth Automating with AI

Scored as CFO + Big 4 Partner + Finance Director + VC.

**Bias:** repetitive, rule-based, evidence-heavy processes where Accounting / Audit / Risk / AI / Python backgrounds are an unfair advantage — not generic chatbot wrappers.

**Scoring model**

| Dimension | Weight | Meaning |
|---|---|---|
| Ease of building | 25% | Data access, rule vs judgment mix, ERP burden, regulatory surface |
| Probability of paying customers | 40% | Budget owner urgency, measurable ROI, existing spend |
| Long-term market potential | 35% | Category size, suite expansion, switching costs, defensibility |

Composite = `0.25×ease + 0.40×pay + 0.35×ltp` (each score 1–10).

Savings bands are directional mid-market / enterprise estimates for prioritization, not audited benchmarks.

---

## Investment thesis

Buyers do not pay for “AI.” They pay to compress close cycles, survive audit, stop cash leakage, and avoid restatement / control / covenant disasters. Winning products own the evidence trail (inputs → rules/models → human override → immutable output). Crowded horizontal AP OCR is a feature war; audit-grade revenue, billing evidence, PBC, flux narrative, and covenant packs still have white space.

---

## Founder shortlist

1. **Usage billing validation & dispute evidence** — highest long-term fit; Decimal / idempotency / audit instincts.
2. **Flux narrative + close evidence** — high ease, Controllers buy fast; pair with close checklist.
3. **Audit PBC + SOX evidence** — seasonal urgency lands deals; year-round evidence library expands.

**Recommended wedge sequence:** billing correctness → flux/close evidence → PBC/SOX. Avoid generic ChatGPT-for-Excel and head-on AP OCR wars.

**Pricing hint:** MVP ~$1–2k/mo mid-market or per-invoice audited; enterprise on entity + volume with SOC2 and immutable audit logs as table stakes.

---

## Ranked scorecard (by composite)

| Rank | Workflow | Category | Ease | Pay | LTP | Composite | Fit |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | Month-end flux analysis & narrative packs | FP&A / Close | 8 | 8 | 9 | 8.4 | core |
| 2 | External audit PBC request response | Audit | 7 | 9 | 8 | 8.3 | core |
| 3 | Usage billing validation & dispute evidence packs | Revenue / Billing | 6 | 8 | 10 | 8.2 | core |
| 4 | Close checklist orchestration with evidence | Close | 8 | 8 | 7 | 7.7 | core |
| 4 | Board / investor reporting pack assembly | FP&A | 7 | 8 | 8 | 7.8 | core |
| 6 | AP invoice capture, coding & 3-way match | Procure-to-Pay | 6 | 9 | 8 | 8.0 | adjacent |
| 7 | Duplicate / erroneous payment recovery | Procure-to-Pay | 7 | 9 | 6 | 7.6 | adjacent |
| 8 | SOX / ICFR control evidence automation | Risk / Audit | 5 | 8 | 9 | 7.7 | core |
| 9 | ASC 606 / IFRS 15 revenue workpapers | Revenue | 3 | 9 | 9 | 7.5 | core |
| 10 | T&E / expense policy audit | Spend | 7 | 8 | 7 | 7.5 | adjacent |
| 11 | Bank & cash reconciliation | Treasury / Close | 7 | 8 | 7 | 7.5 | adjacent |
| 12 | Debt covenant compliance certificates | Treasury / FP&A | 5 | 8 | 8 | 7.3 | core |
| 13 | Balance-sheet account reconciliations (certs) | Close / Controls | 5 | 8 | 8 | 7.3 | core |
| 14 | Accrual estimation, posting & auto-reversal tracking | Close | 7 | 7 | 7 | 7.0 | adjacent |
| 15 | Intercompany matching, eliminations & settlements | Consolidation | 4 | 7 | 8 | 6.6 | adjacent |
| 16 | Tax provision & deferred tax rollforwards | Tax | 3 | 7 | 8 | 6.4 | stretch |
| 17 | Payroll-to-GL reconciliation & wage accrual | Close / HRIS | 6 | 7 | 6 | 6.5 | adjacent |
| 18 | Vendor / customer master data risk & sanctions screening | Risk / Compliance | 5 | 7 | 7 | 6.5 | stretch |
| 19 | ASC 842 / IFRS 16 lease accounting | Technical Accounting | 4 | 7 | 6 | 5.9 | stretch |
| 20 | Fixed asset capitalization & depreciation workpapers | Technical Accounting | 6 | 6 | 5 | 5.7 | stretch |

*Fit* = relevance to Accounting + Audit + Risk + AI/Python (and billing correctness DNA): `core` / `adjacent` / `stretch`.

---

## Workflow deep dives

### 1. AP invoice capture, coding & 3-way match

| Field | Detail |
|---|---|
| **Category** | Procure-to-Pay |
| **Scores** | Ease 6 · Pay 9 · LTP 8 · Composite 8.0 · Fit adjacent |
| **Current process** | Invoices arrive by email/portal PDF; AP clerks OCR or key data, code GL/cost center, match to PO/receipt, route approvals, post to ERP. |
| **Pain point** | High volume, exception-heavy, duplicate payments, slow close, vendor friction. Typical mid-market AP team spends 40–60% of time on touch labor. |
| **Estimated savings** | Mid-market: $180k–$600k/yr (2–6 FTE + early-pay discounts recovered). Enterprise: $1M–$5M+. |
| **Competitors** | Bill.com, Tipalti, AvidXchange, Coupa, SAP Concur Invoice, Ramp Bill Pay, Vic.ai, Rossum, Veryfi. |
| **Why customers pay** | Direct P&L hit via headcount + cash leakage; CFO owns AP metrics; ROI measurable in weeks. |
| **MVP** | Email inbox → OCR → suggested GL codes from history → PO match score → exception queue with audit log of every edit. |
| **Enterprise** | ERP-native posting, multi-entity tax/VAT rules, supplier portals, duplicate detection, continuous controls monitoring, SOX evidence packs. |
| **Monetization** | Per invoice processed + platform fee; or % of recovered duplicates/early-pay. |

### 2. Bank & cash reconciliation

| Field | Detail |
|---|---|
| **Category** | Treasury / Close |
| **Scores** | Ease 7 · Pay 8 · LTP 7 · Composite 7.5 · Fit adjacent |
| **Current process** | Daily/weekly download of bank files; match to GL cash/AR/AP clearings in Excel or ERP; investigate unmatched items; prepare recon schedules for close. |
| **Pain point** | Manual matching, timing differences, FX, uncleared items aging. Controllers treat cash recon as non-negotiable close bottleneck. |
| **Estimated savings** | Mid-market: $80k–$250k/yr. Multi-entity treasury: $400k–$1.5M. |
| **Competitors** | HighRadius, Kyriba, BlackLine, FloQast Cash, Autorec, ERP native modules. |
| **Why customers pay** | Cash is sacred; auditors focus here; daily cash visibility funds working-capital decisions. |
| **MVP** | Ingest BAI2/MT940/CSV + GL extracts; fuzzy match rules; aging of unmatched; export signed recon PDF with hash of source files. |
| **Enterprise** | Multi-bank, multi-currency, in-transit forecasting, continuous recon, treasury workstation integration, SOC2 evidence. |
| **Monetization** | Per bank account / entity / month. |

### 3. Balance-sheet account reconciliations (certs)

| Field | Detail |
|---|---|
| **Category** | Close / Controls |
| **Scores** | Ease 5 · Pay 8 · LTP 8 · Composite 7.3 · Fit core |
| **Current process** | Accountants build Excel recons for every BS account; attach support; preparer/reviewer sign-offs; controllers chase completeness at close. |
| **Pain point** | Version chaos, missing evidence, late reviews, audit findings on incomplete recons. Classic BlackLine beachhead. |
| **Estimated savings** | Mid-market: $150k–$400k. Enterprise: $1M–$4M (FTE + audit fees avoided). |
| **Competitors** | BlackLine, FloQast, Trintech Cadency, Account Reconciliation in NetSuite/Workday. |
| **Why customers pay** | SOX/ICFR and external audit demand certified recons; boards care about control deficiencies. |
| **MVP** | Templates + auto-pull ERP balances + checklist of attachments + dual sign-off + immutable history. |
| **Enterprise** | Risk-based frequency, auto-certify low-risk, variance thresholds, Big 4-ready PBC export, multi-GAAP. |
| **Monetization** | Per entity + per recon / seat (SaaS). |

### 4. Month-end flux analysis & narrative packs

| Field | Detail |
|---|---|
| **Category** | FP&A / Close |
| **Scores** | Ease 8 · Pay 8 · LTP 9 · Composite 8.4 · Fit core |
| **Current process** | FP&A pulls trial balance MoM/YoY; analysts investigate variances in Excel; write commentary for CFO pack; iterate late into close week. |
| **Pain point** | Repetitive, judgment-light after thresholds set, commentary quality inconsistent, nights lost before board meetings. |
| **Estimated savings** | Mid-market: $100k–$300k. Enterprise: $500k–$2M (analyst time + faster decisions). |
| **Competitors** | Pigment, Anaplan, Workday Adaptive, Cube, Mosaic, Datarails, Chat-on-ERP startups. |
| **Why customers pay** | CFO time is scarce; better narratives reduce board surprises; close compression is a KPI. |
| **MVP** | Ingest TB + prior period; threshold rules; LLM drafts first-pass commentary citing account moves; human edit with tracked changes. |
| **Enterprise** | Driver-based bridge (volume/price/FX/mix), linked to operational systems, multi-entity consolidation view, board-ready slides. |
| **Monetization** | Seat + usage (narrative generations) or close-cycle subscription. |

### 5. ASC 606 / IFRS 15 revenue workpapers

| Field | Detail |
|---|---|
| **Category** | Revenue |
| **Scores** | Ease 3 · Pay 9 · LTP 9 · Composite 7.5 · Fit core |
| **Current process** | Rev accountants read contracts, identify performance obligations, allocate SSP, build waterfalls, post journals, maintain SSP catalogs. |
| **Pain point** | Contract variability, amendments, usage/credits, audit-sensitive judgments. Errors = restatement risk. |
| **Estimated savings** | Mid-market SaaS: $200k–$800k. Enterprise: $1M–$5M+ (plus restatement avoidance). |
| **Competitors** | Zuora RevPro, Chargebee RevRec, Salesforce Revenue Cloud, Orb, Metronome (adjacent). |
| **Why customers pay** | Revenue is the #1 audit focus area for growth companies; investors punish restatements. |
| **MVP** | Contract PDF → extract POBs/pricing → suggest allocation vs SSP table → waterfall schedule + journal draft + evidence binder. |
| **Enterprise** | ERP/CRM/billing sync, amendment handling, multi-element arrangements, ASC 340 costs, SOX controls. |
| **Monetization** | Platform + % of ARR under management or per contract analyzed. |

### 6. Usage billing validation & dispute evidence packs

| Field | Detail |
|---|---|
| **Category** | Revenue / Billing |
| **Scores** | Ease 6 · Pay 8 · LTP 10 · Composite 8.2 · Fit core |
| **Current process** | Usage events metered; invoices generated; customers dispute quantities/rates; finance rebuilds evidence from logs, pricing versions, and contracts. |
| **Pain point** | Opaque meters, pricing version drift, late usage, shadow invoices vs prod. High support cost and churn risk. |
| **Estimated savings** | Usage-heavy SaaS: $150k–$1M+ (dispute labor + write-offs + retention). Enterprise infra: multi-million. |
| **Competitors** | Metronome, Orb, Stripe Billing, Chargebee, Lago, Amberflo; few own the audit-evidence layer. |
| **Why customers pay** | Incorrect bills destroy trust; CFOs of AI/infra companies need Decimal-correct, idempotent metering with replayable evidence. |
| **MVP** | Ingest usage events + priced invoices; recompute expected amount with versioned plans; diff report; export dispute evidence PDF. |
| **Enterprise** | Shadow billing, late-usage adjustments (immutable finalized invoices), outbox reliability metrics, customer-facing evidence portal. |
| **Monetization** | Per event re-priced or per invoice audited + enterprise license. |

### 7. Intercompany matching, eliminations & settlements

| Field | Detail |
|---|---|
| **Category** | Consolidation |
| **Scores** | Ease 4 · Pay 7 · LTP 8 · Composite 6.6 · Fit adjacent |
| **Current process** | Entities bill each other; accountants match AR/AP IC balances; investigate breaks; post eliminations; settle cash. |
| **Pain point** | Timing, FX, tax, incomplete counterparties. Breaks dominate close for multi-entity groups. |
| **Estimated savings** | Multi-entity groups: $200k–$1.5M. |
| **Competitors** | BlackLine Intercompany, Trintech, OneStream, Oracle FCCS, HighRadius. |
| **Why customers pay** | Prevents delayed close and consolidation errors that auditors flag aggressively. |
| **MVP** | Bilateral match engine on IC invoices/journals; break aging; suggested eliminating entries; evidence pack. |
| **Enterprise** | Netting centers, multi-currency, tax-aware settlements, continuous matching, ERP posting bots. |
| **Monetization** | Per entity pair / settlement volume. |

### 8. T&E / expense policy audit

| Field | Detail |
|---|---|
| **Category** | Spend |
| **Scores** | Ease 7 · Pay 8 · LTP 7 · Composite 7.5 · Fit adjacent |
| **Current process** | Employees submit expenses; managers approve; auditors sample for policy breaches (alcohol, class of travel, missing receipts). |
| **Pain point** | Sampling misses fraud; manual review doesn't scale; policy documents ignored in practice. |
| **Estimated savings** | Mid-market: $50k–$200k leakage + review time. Enterprise: $500k–$3M. |
| **Competitors** | Expensify, Concur, Ramp, Brex, Navan, AppZen, Oversight. |
| **Why customers pay** | Fraud + policy leakage is board-visible; AI 100% testing beats sampling for internal audit. |
| **MVP** | Ingest expense lines + receipts; rule engine + LLM receipt check; risk score; exception queue with audit trail. |
| **Enterprise** | Continuous monitoring, card feed integration, vendor graph fraud, IA workpapers, policy version control. |
| **Monetization** | Per employee / per $ spend audited. |

### 9. SOX / ICFR control evidence automation

| Field | Detail |
|---|---|
| **Category** | Risk / Audit |
| **Scores** | Ease 5 · Pay 8 · LTP 9 · Composite 7.7 · Fit core |
| **Current process** | Control owners screenshot systems, fill Excel RCMs, store in SharePoint; IA/external audit sample and retest. |
| **Pain point** | Evidence stale, incomplete, last-minute fire drills; material weakness risk is existential for public cos. |
| **Estimated savings** | Public mid-cap: $300k–$1.5M (IA + Big 4 hours + management time). |
| **Competitors** | Workiva, AuditBoard, Diligent, LogicGate, ServiceNow GRC, Vanta (lighter). |
| **Why customers pay** | Avoid material weaknesses; reduce Big 4 fees; continuous evidence beats annual scramble. |
| **MVP** | Map key controls → auto-collect system logs/exports → attach to control → preparer/reviewer sign-off → PBC zip. |
| **Enterprise** | Risk-ranked testing, population completeness proofs, deficiency workflow, PCAOB-ready packages. |
| **Monetization** | Per control / per entity SaaS + professional services. |

### 10. External audit PBC request response

| Field | Detail |
|---|---|
| **Category** | Audit |
| **Scores** | Ease 7 · Pay 9 · LTP 8 · Composite 8.3 · Fit core |
| **Current process** | Auditors send hundreds of PBC requests; finance hunts files across ERP/Drive/email; uploads to portal; iterates on follow-ups. |
| **Pain point** | Seasonal hell; lost documents; duplicate asks; burns controller bandwidth for 8–12 weeks. |
| **Estimated savings** | Mid-market: $80k–$250k/yr equivalent. Repeat audits compound. |
| **Competitors** | Confirmation.com (narrow), Workiva, FloQast AI, AuditBoard, Datasnipper (auditor side). |
| **Why customers pay** | Controllers will pay to reclaim Q1; CFOs see faster filings and lower audit overruns. |
| **MVP** | Ingest PBC list; map to prior-year evidence; auto-assemble packets; gap list; immutable delivery log. |
| **Enterprise** | Multi-auditor portals, population pulls from ERP APIs, continuous year-round evidence library. |
| **Monetization** | Seasonal project fee + annual evidence library subscription. |

### 11. Duplicate / erroneous payment recovery

| Field | Detail |
|---|---|
| **Category** | Procure-to-Pay |
| **Scores** | Ease 7 · Pay 9 · LTP 6 · Composite 7.6 · Fit adjacent |
| **Current process** | AP or internal audit periodically searches for duplicate vendors/invoices; recovery letters sent after the fact. |
| **Pain point** | Silent cash leakage; hard to prove without clean vendor master and invoice graph. |
| **Estimated savings** | Often 0.05–0.3% of AP spend recovered = six–seven figures for many firms. |
| **Competitors** | AP auditors (KPMG/PwC/EY/Deloitte RAS), AppZen, Oversight, MineralTree analytics. |
| **Why customers pay** | Contingency/shared-savings models sell themselves; CFO loves found money. |
| **MVP** | Vendor+invoice graph dedupe; ranked recovery candidates; evidence packet per claim; letter templates. |
| **Enterprise** | Real-time blocking before payment, master data stewardship, continuous monitoring dashboards. |
| **Monetization** | Success fee (% recovered) + optional prevention SaaS. |

### 12. ASC 842 / IFRS 16 lease accounting

| Field | Detail |
|---|---|
| **Category** | Technical Accounting |
| **Scores** | Ease 4 · Pay 7 · LTP 6 · Composite 5.9 · Fit stretch |
| **Current process** | Lease abstracts in Excel; calculate ROU/liability; modify for amendments; disclose maturity tables. |
| **Pain point** | Spreadsheets break on amendments; disclosure footnotes painful; auditors dig deep. |
| **Estimated savings** | Mid-market: $100k–$400k. Portfolio with hundreds of leases: $500k–$2M. |
| **Competitors** | LeaseQuery, CoStar RealPage, Nakisa, Visual Lease, Oracle Lease Accounting. |
| **Why customers pay** | Technical compliance with measurable close risk; less sexy but sticky. |
| **MVP** | Lease PDF abstract → terms extraction → schedule calc → journal + disclosure draft + evidence. |
| **Enterprise** | Portfolio amendments, subleases, impairment, multi-GAAP, ERP posting, Big 4 calc tie-outs. |
| **Monetization** | Per lease asset under management. |

### 13. Close checklist orchestration with evidence

| Field | Detail |
|---|---|
| **Category** | Close |
| **Scores** | Ease 8 · Pay 8 · LTP 7 · Composite 7.7 · Fit core |
| **Current process** | Excel/Smartsheet close checklist; owners update status; binders assembled separately. |
| **Pain point** | Status ≠ evidence; dependencies opaque; late tasks cascade; new hires struggle. |
| **Estimated savings** | Mid-market: $60k–$200k + days off close cycle (board/investor value). |
| **Competitors** | FloQast, BlackLine Task Management, Numeric, SolveXia, Excel forever. |
| **Why customers pay** | Days-to-close is a vanity+real KPI; PE portfolio cos buy this early. |
| **MVP** | Task graph + owners + auto-attach ERP exports/recon links + blockers + daily CFO digest. |
| **Enterprise** | Multi-entity rollups, SLA analytics, integration to recon/flux tools, auditor read-only mode. |
| **Monetization** | Per entity SaaS seats. |

### 14. Tax provision & deferred tax rollforwards

| Field | Detail |
|---|---|
| **Category** | Tax |
| **Scores** | Ease 3 · Pay 7 · LTP 8 · Composite 6.4 · Fit stretch |
| **Current process** | Tax team builds Excel provision (current/deferred), ETR bridge, uncertain tax positions; ties to GL. |
| **Pain point** | High expertise, brittle models, late inputs from Controllership; audit adjustments common. |
| **Estimated savings** | Mid-market: $150k–$500k. Multinational: $1M+. |
| **Competitors** | Bloomberg Tax Provision, Longview, Vertex, CSC Corptax, Thomson Reuters. |
| **Why customers pay** | Provision errors hit earnings; Big 4 tax fees are painful. |
| **MVP** | Trial balance → book-tax difference checklist → deferred rollforward draft → ETR bridge narrative. |
| **Enterprise** | Multi-jurisdiction, FTC, GILTI/Pillar 2 hooks, provision-to-return, workflow with Controllership. |
| **Monetization** | Per entity / jurisdiction SaaS + expert review marketplace. |

### 15. Debt covenant compliance certificates

| Field | Detail |
|---|---|
| **Category** | Treasury / FP&A |
| **Scores** | Ease 5 · Pay 8 · LTP 8 · Composite 7.3 · Fit core |
| **Current process** | FP&A recalculates leverage/interest coverage from definitions in credit agreements; drafts certificate for lenders. |
| **Pain point** | Definitions ≠ GAAP; add-backs debated; missed breach can trigger default — existential. |
| **Estimated savings** | Hard $: $50k–$150k labor. Soft $: avoided default/waiver fees ($500k–$5M+ events). |
| **Competitors** | Kyriba (partial), Excel+counsel, niche covenant tools emerging. |
| **Why customers pay** | CFOs/PE sponsors pay for early warning; lenders trust independent calc packs. |
| **MVP** | Parse credit agreement definitions → map GL accounts → compute covenants → red/yellow/green + certificate PDF. |
| **Enterprise** | Scenario forecasts, multi-facility, amendment tracking, lender portal, counsel collaboration. |
| **Monetization** | Per facility subscription + alert premium. |

### 16. Accrual estimation, posting & auto-reversal tracking

| Field | Detail |
|---|---|
| **Category** | Close |
| **Scores** | Ease 7 · Pay 7 · LTP 7 · Composite 7.0 · Fit adjacent |
| **Current process** | Accountants estimate period-end accruals (ops, legal, bonuses); post; reverse next period; hope nothing double-counts. |
| **Pain point** | Tribal knowledge; inconsistent methods; missing reversals create noise and audit issues. |
| **Estimated savings** | Mid-market: $80k–$250k. High-transaction cos: $400k+. |
| **Competitors** | ERP workflows, FloQast, BlackLine journals, custom scripts. |
| **Why customers pay** | Cleaner close, fewer P&L surprises, auditable estimation policy. |
| **MVP** | Policy library per accrual type; suggest amounts from run-rate/PO/open tickets; JE draft; reversal calendar; evidence. |
| **Enterprise** | ML estimation with explainability, threshold approvals, continuous true-up vs actuals. |
| **Monetization** | Per JE / per entity SaaS. |

### 17. Fixed asset capitalization & depreciation workpapers

| Field | Detail |
|---|---|
| **Category** | Technical Accounting |
| **Scores** | Ease 6 · Pay 6 · LTP 5 · Composite 5.7 · Fit stretch |
| **Current process** | Capex requests reviewed vs policy; assets set up in subledger; depreciation run; CIP transfers; impairment checks. |
| **Pain point** | Expense-vs-capitalize debates; CIP aging; depreciation mismatches to GL; audit samples painful. |
| **Estimated savings** | Mid-market: $60k–$200k. Capex-heavy: $300k–$1M. |
| **Competitors** | ERP FA modules, Sage Fixed Assets, IBM Maximo (ops), BlackLine (partial). |
| **Why customers pay** | Capex policy compliance + clean FA rollforward for auditors. |
| **MVP** | Invoice/capex request → capitalize vs expense recommendation with policy cites → asset record draft → dep schedule. |
| **Enterprise** | Componentization, impairment triggers, multi-book, tax depreciation bridge, physical verification apps. |
| **Monetization** | Per asset under management + policy engine license. |

### 18. Payroll-to-GL reconciliation & wage accrual

| Field | Detail |
|---|---|
| **Category** | Close / HRIS |
| **Scores** | Ease 6 · Pay 7 · LTP 6 · Composite 6.5 · Fit adjacent |
| **Current process** | Payroll register vs GL salary/tax/benefit accounts; investigate mapping breaks; accrue unpaid wages/bonuses. |
| **Pain point** | Every pay period; mapping drift after HRIS changes; multi-country complexity. |
| **Estimated savings** | Mid-market: $70k–$200k. Global employers: $400k–$1.2M. |
| **Competitors** | ERP + payroll vendors (ADP, Workday), custom Excel, BlackLine templates. |
| **Why customers pay** | Payroll is material; recon failures = control findings and employee trust issues. |
| **MVP** | Ingest payroll register + GL; mapping rules; break report; wage accrual suggestion; signed recon. |
| **Enterprise** | Multi-country statutory, benefits/equity, continuous recon, HRIS change detection. |
| **Monetization** | Per employee / per pay run analyzed. |

### 19. Board / investor reporting pack assembly

| Field | Detail |
|---|---|
| **Category** | FP&A |
| **Scores** | Ease 7 · Pay 8 · LTP 8 · Composite 7.8 · Fit core |
| **Current process** | FP&A stitches ERP, CRM, billing, bank data into slides/Excel; CFO edits Sunday night before board. |
| **Pain point** | Manual, error-prone numbers, version hell, inconsistent definitions of ARR/burn/runway. |
| **Estimated savings** | Startup/scale-up: $80k–$250k + founder/CFO hours. PE portfolio: multiplied across cos. |
| **Competitors** | Pigment, Drivetraker, Causal, Baremetrics/ChartMogul (metrics), PowerPoint humans. |
| **Why customers pay** | Board quality = fundraising/governance outcomes; PE operating partners standardize packs. |
| **MVP** | Connect GL + billing + bank; KPI dictionary; auto-draft pack with source-linked numbers; comment layer. |
| **Enterprise** | Multi-portfolio rollup for PE, audit-ready KPI definitions, scenario tabs, permissioned investor views. |
| **Monetization** | Seat SaaS + per board pack generation; PE portfolio pricing. |

### 20. Vendor / customer master data risk & sanctions screening workflow

| Field | Detail |
|---|---|
| **Category** | Risk / Compliance |
| **Scores** | Ease 5 · Pay 7 · LTP 7 · Composite 6.5 · Fit stretch |
| **Current process** | Master data created in ERP with light checks; periodic KYC/sanctions/PEP screening; exceptions handled ad hoc. |
| **Pain point** | Regulatory fines, fraud via vendor bank-account changes, audit findings on incomplete due diligence. |
| **Estimated savings** | Avoided fraud/fines dominate; process savings $50k–$200k; one prevented BEC fraud pays for years. |
| **Competitors** | Refinitiv, Dow Jones Risk, ComplyAdvantage, SAP MDG, Tipalti (payments side). |
| **Why customers pay** | Treasury/CFO own payment fraud risk; compliance owns sanctions — dual budget. |
| **MVP** | New vendor/customer intake → screening + bank change verification workflow → evidence dossier → ERP gate. |
| **Enterprise** | Continuous rescreening, beneficial ownership, multi-jurisdiction lists, payment-time re-check. |
| **Monetization** | Per screening + platform; premium for payment-time API. |

---

## VC kill criteria (what not to build first)

| Trap | Why it fails early | Better angle |
|---|---|---|
| Generic ChatGPT for Excel | No workflow owner, no evidence, no switching cost | Own a named close/audit artifact end-to-end |
| Head-on AP OCR vs Tipalti/Coupa | Brutal distribution + incumbent bundling | Niche on exceptions, duplicates, or vertical invoices |
| Full ASC 606 platform on day one | Deep ERP + judgment + long sales cycle | Start with contract → waterfall evidence pack |
| Success-fee only recovery | Lumpy revenue, hard to value for VC | Prevention SaaS + shared savings hybrid |

---

## Disclaimer

Savings and scores are expert estimates for prioritization, not audited benchmarks or customer commitments. Validate with 10–15 Controller / CFO discovery calls before committing build capital.
