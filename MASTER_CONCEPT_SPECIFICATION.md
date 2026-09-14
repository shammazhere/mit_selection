# 🛡️ SILENT SHIFT: Master Concept, Architecture & Feature Blueprint
> **The Definitive System Specification for Problem Statement 16: Context-Aware Insider Threat Detection & Dynamic Risk Fusion**  
> *Track: Peace, Justice, and Strong Institutions (Section 10)*

---

## 1. Executive Summary & Problem Definition

### 1.1 The Insider Threat Paradox
Traditional perimeter defense mechanisms (firewalls, anti-virus, signature-based IDS/IPS, rigid DLP rules) operate on the assumption that attackers are outsiders attempting to penetrate the network. However, **over 60% of catastrophic data exfiltrations originate from legitimate insiders** (employees, contractors, privileged administrators).

Insiders possess three characteristics that break traditional security:
1. **Authorized Credentials**: They already possess valid corporate usernames, passwords, MFA tokens, and legitimate read/write permissions. They do not trigger brute-force or intrusion alarms.
2. **Stealthy "Slow-Roll" Exfiltration**: Sophisticated adversaries avoid dumping hundreds of gigabytes at once. Instead, they exfiltrate small, incremental volumes (e.g., 20–30 MB/day) over weeks or months, staying strictly beneath static daily volume thresholds.
3. **The False-Positive & Alert Fatigue Crisis**: Traditional User Behavior Analytics (UBA) tools rely on rigid, arbitrary curfew rules (e.g., *"Flag any upload after 8:00 PM as High Risk"*). This creates severe alert fatigue for SOC analysts and unfairly targets remote workers, night owls, and employees working overtime across global timezones.

### 1.2 The Silent Shift Mission
**Silent Shift** transforms insider threat detection from static rule evaluation to **statistical behavioral drift analysis**. It determines not whether an action is prohibited, but whether an employee's behavior is **gradually drifting away from their own historical baseline and their organizational peer cohort**, fused with real-world contextual multipliers and governed by strict anti-surveillance privacy guardrails.

---

## 2. Core Philosophy & Architectural Principles

```
                           ┌─────────────────────────────────────────────────────────┐
                           │               THE SILENT SHIFT PARADIGM                 │
                           └────────────────────────────┬────────────────────────────┘
                                                        │
         ┌───────────────────────┬──────────────────────┴────────────────┬───────────────────────┐
         ▼                       ▼                                       ▼                       ▼
┌──────────────────┐    ┌──────────────────┐                   ┌──────────────────┐    ┌──────────────────┐
│  Dual-Baseline   │    │   Locked CUSUM   │                   │    Contextual    │    │  Human-in-the-   │
│  Fairness Model  │    │  Temporal Drift  │                   │  Risk Multipliers│    │ Loop Calibration │
│ (Self + Peer Z)  │    │ (Pre-Multiplier) │                   │ (Role, Time, Med)│    │ (0.4x Dampener)  │
└──────────────────┘    └──────────────────┘                   └──────────────────┘    └──────────────────┘
```

1. **Dual-Baselining (Personal Normal vs. Peer Normal)**:
   - **Self-Baseline**: Evaluates each employee against their own 90-day personal baseline using unsupervised machine learning (**Isolation Forest**).
   - **Peer-Baseline**: Compares daily activity against peers sharing the exact same role and manager using robust **median and IQR Z-scores**.
   - If an engineer routinely works late, their personal anomaly score is low. If an accountant suddenly accesses confidential source code at 2:00 AM, both baselines elevate.
2. **Locked CUSUM Temporal Drift**:
   - Implements a statistical **Cumulative Sum (CUSUM)** quality control chart over consecutive days.
   - **Crucial Mathematical Rule**: The input score is **locked prior to context multipliers**, ensuring environmental variables (e.g., working late) cannot artificially spoof temporal drift.
3. **Contextual Risk Multiplier Matrix**:
   - Dynamically scales risk using role privilege, off-hours access, removable media, and cloud exfiltration targets.
4. **Human-in-the-Loop Feedback Calibration**:
   - The AI assists human investigators but never executes autonomous punitive actions.
   - When an investigator marks legitimate business activity as a false positive, an instant **0.4× dampening factor** is applied, immediately dropping the score, re-ranking the queue, and awarding a green `✓ CALIBRATED FP` badge.
5. **Section 10 Governance & Anti-Surveillance**:
   - Strict **Data Minimization** (behavioral metadata only; zero keystroke logging, zero message/email interception, zero file content inspection).
   - **"Audit-the-Auditor"**: Every administrative query into an employee's case dossier is permanently logged in `audit_access_log` and rendered on the case page to eliminate internal snooping.
   - **Automated 90-Day Retention**: Stale telemetry and risk scores older than 90 days are automatically purged from the database.

---

## 3. Mathematical Formulation & Scoring Equations

### 3.1 Unsupervised Self-Baseline (Isolation Forest)
For user $u$ on day $t$ with daily feature vector $\mathbf{x}_{u,t} \in \mathbb{R}^d$:
$$\text{self\_score}_{u,t} = \text{clip}\left( \frac{s(\mathbf{x}_{u,t}) - s_{\min}}{s_{\max} - s_{\min}}, 0.0, 1.0 \right)$$
where $s(\mathbf{x})$ is the anomaly score output from an `IsolationForest` trained on user $u$'s past 90 days of normal activity.

### 3.2 Robust Peer-Cohort Normalization
For feature $j$ within role cohort $C$ of size $N$:
$$\text{median}_j = \text{median}(\mathbf{X}_{C, j}), \quad \text{IQR}_j = Q_3(\mathbf{X}_{C, j}) - Q_1(\mathbf{X}_{C, j})$$
$$Z_{u, t, j} = \frac{x_{u, t, j} - \text{median}_j}{\max(1.349 \times \text{IQR}_j, \epsilon)}$$
$$\text{peer\_score}_{u,t} = \text{clip}\left( \frac{1}{|J|} \sum_{j \in J} \sigma(Z_{u, t, j}), 0.0, 1.0 \right)$$
* **Small-Cohort Fallback Safeguard**: If $|C| < 5$, peer comparison automatically falls back to department-level normalization ($C_{\text{dept}}$) and flags `fallback_applied = True`.

### 3.3 Locked Pre-Multiplier Score
$$x_t = \frac{0.35 \times \text{self\_score}_{u,t} + 0.35 \times \text{peer\_score}_{u,t}}{0.70} \in [0.0, 1.0]$$
This value is locked and passed into the CUSUM engine without contextual multiplier distortion.

### 3.4 Tabular CUSUM Drift Control Chart
$$S_0 = 0, \quad S_t = \max(0, S_{t-1} + (x_t - \mu) - k)$$
* Target in-control mean: $\mu = 0.35$
* Slack allowance: $k = 0.08$
* Drift detection threshold: $h = 0.25$
* Drift Score:
$$\text{drift\_score}_{u,t} = \min\left(1.0, \frac{S_t}{0.40}\right)$$
$$\text{drift\_detected} = (S_t \ge 0.25)$$

### 3.5 Fused Risk Score & Context Multiplier Scaling
$$\text{Base Score} = 0.35 \times \text{self\_score} + 0.35 \times \text{peer\_score} + 0.30 \times \text{drift\_score}$$
$$\text{Multiplier Product} = M_{\text{role}} \times M_{\text{time}} \times M_{\text{data}} \times M_{\text{feedback}}$$
where:
* $M_{\text{role}} = 1.45$ (Admin / DevOps), $1.35$ (Financial Controller), $1.00$ (Standard)
* $M_{\text{time}} = 1.35$ (if logon/activity occurred between 20:00 and 07:00), else $1.00$
* $M_{\text{data}} = 1.35$ (removable storage attached) $\times 1.40$ (external cloud upload visited)
* $M_{\text{feedback}} = 0.40$ (if marked false positive by investigator), else $1.00$

$$\text{Final Risk Score} = \min\left(100.0, \text{Base Score} \times \text{Multiplier Product} \times 100.0\right)$$

### 3.6 Severity Classification
* **Critical** ($80.0 - 100.0$): Immediate threat requiring active containment.
* **High** ($65.0 - 79.9$): Significant sustained behavioral anomaly.
* **Medium** ($50.0 - 64.9$): Elevated activity warranting SOC monitoring.
* **Low** ($0.0 - 49.9$): Baseline or calibrated normal activity.

---

## 4. End-to-End System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. INGESTION & HYBRID SENSORS                                                               │
│    ├── A. CERT Enterprise Logs (Logon, HTTP, File, USB, Email, LDAP)                        │
│    ├── B. In-Browser WebUSB Sensor (W3C navigator.usb.requestDevice under visible consent)  │
│    └── C. Corporate Workstation Agent (curl .../agent.py | python3 -)                       │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. DETECTION ENGINE (ANOMALY & DRIFT)                                                       │
│    ├── Daily Feature Aggregator (Logons, off-hours, file count, cloud upload bytes)         │
│    ├── 90-Day Isolation Forest Self-Baseline (self_score: 0.0 - 1.0)                        │
│    ├── Role/Department Robust Z-Score Cohorts (peer_score: 0.0 - 1.0)                       │
│    ├── Small-Cohort Fallback Detector (N < 5 -> Fallback Disclosed)                         │
│    └── Locked CUSUM Drift Control Chart (Threshold: 0.25, Slack: 0.08)                      │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. RISK FUSION, GOVERNANCE & BACKEND REST API (FastAPI + SQLite scores.db)                  │
│    ├── Pre-Multiplier Score Combiner & Context Multiplier Matrix                            │
│    ├── Deterministic Natural Language Explanation Generator                                 │
│    ├── Section 10 "Audit-the-Auditor" Engine (audit_access_log)                             │
│    ├── Automated 90-Day Retention Pruning (enforce_retention_policy)                         │
│    └── Deduplicated Queue Query (INNER JOIN on MAX(date) GROUP BY user_id)                   │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. ADMIN & SOC INVESTIGATOR CONSOLE (React 19 + TypeScript + Vite)                          │
│    ├── Prioritized Risk Queue Page (KPI metrics, search, severity badges, deduplication)    │
│    ├── Case Forensic Dossier (Tri-signal gauges, active override banner, fallback badge)    │
│    ├── Interactive CUSUM Drift Area Chart (Exact timestamps, threshold line, hover tooltips)│
│    ├── Chronological Forensic Timeline (Wrapped URLs, category chips, resolution milestones)│
│    ├── 1-Click Analyst Calibration Widget (Instant 0.4x dampening & green badge)            │
│    └── Admin Access Audit Trail Card (Audit-the-Auditor proof)                              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Enterprise Role Separation & Telemetry Modes

Silent Shift establishes a strict enterprise division of responsibility:

### 5.1 The Admin / SOC Security Console (Web Application)
* **Access Control**: Strictly restricted to authorized **Security Administrators, SOC Analysts, and Forensics Investigators**.
* **Purpose**: Case triage, CUSUM drift curve inspection, evidence analysis, and false-positive recalibration.
* **Anti-Surveillance Protection**: Every query into an employee's case dossier is permanently recorded in `audit_access_log`.

### 5.2 Corporate Workstation Sensor (`backend/live_agent.py`)
* **Deployment**: Enrolled across company-owned laptops and servers using a zero-touch terminal command:
  ```bash
  curl -sSL https://<server-url>/agent.py | python3 -
  ```
* **Auto-Discovery**: Resolves OS username and machine hostname automatically (`getpass` and `socket`). No fake names typed manually.
* **Strict Data Minimization**:
  * Desktop windows monitored via `wmctrl`.
  * Browser history inspected specifically for designated external exfiltration services (`wetransfer.com`, `mega.nz`, `dropbox.com`). General browsing is discarded.
  * Removable storage mounts detected via `/run/user/$UID/gvfs`, `/media/$USER`, and `lsusb`.

### 5.3 In-Browser Live Sensor (Zero-Install / WebUSB)
* **High-Entropy Client Hints**: Auto-discovers CPU concurrency, RAM, and OS kernel tags (`navigator.userAgentData`).
* **Visible User Consent**: Uses W3C standard WebUSB (`navigator.usb.requestDevice()`) to trigger the native OS permission modal, reading authentic USB Vendor IDs and Product IDs only when explicitly permitted.

---

## 6. Section 10 Governance: Peace, Justice, and Strong Institutions

To address regulatory compliance and ethical safety:

1. **"Audit-the-Auditor" (Admin Access Auditing)**:
   - Prevents rogue administrators or analysts from snooping on coworkers undetected.
   - When an admin queries `GET /case/{user_id}`, their admin ID, timestamp, and action are permanently logged to SQLite.
   - The Case Dossier visibly displays the **"Admin Access Audit Trail"** with a `SECTION 10 COMPLIANT` badge.
2. **Automated 90-Day Retention Limits**:
   - In compliance with GDPR Article 5(1)(e), employee telemetry is not retained indefinitely.
   - The database engine executes `enforce_retention_policy(90)` on startup and via `POST /governance/retention/enforce`, purging records older than 90 days.
3. **Strict Data Minimization (Metadata Only, Zero Content Inspection)**:
   - Monitors behavioral statistical metadata (file size, USB VID/PID, exfiltration domain).
   - **Never** records keystrokes, passwords, private chats (Slack/Teams/WhatsApp), emails, webcams, or file contents.
4. **Human-in-the-Loop (No Autonomous Punishment)**:
   - The platform is strictly decision-support. It never revokes credentials or terminates employees automatically.
   - 1-click false-positive feedback drops the risk score by 60% in real time.

---

## 7. Database Schemas & Data Contracts

### 7.1 SQLite Schema (`scores.db`)
* **`risk_scores`**: `(user_id, date) PRIMARY KEY`, `self_score`, `peer_score`, `drift_score`, `pre_multiplier_score`, `raw_fusion_score`, `adjusted_fusion_score`, `risk_score`, `cohort_used`, `cohort_size`, `fallback_applied`, `role`, `name`, `team`, `cusum_path`, `multipliers_applied`, `score_components`, `severity`, `explanation_text`, `event_timeline`, `is_false_positive`, `feedback_reason`, `last_updated`.
* **`feedback`**: `id PRIMARY KEY`, `user_id`, `is_false_positive`, `reason`, `created_at`, `down_weight`.
* **`audit_access_log`**: `id PRIMARY KEY`, `timestamp`, `investigator_id`, `target_user_id`, `action`, `details`.

### 7.2 REST API Specification (Contract B)
* `GET /queue`: Returns deduplicated, prioritized list of accounts ranked by latest `risk_score`.
* `GET /case/{user_id}`: Returns full forensic dossier, tri-signals, explanation, CUSUM path, timeline, and `access_audit_log`.
* `POST /feedback`: Records analyst justification and immediately applies the $0.4\times$ multiplier.
* `POST /telemetry`: Ingests live browser/desktop endpoint telemetry and re-scores dynamically.
* `GET /agent.py`: Serves dynamically configured native workstation sensor script.
* `GET /governance/policy`: Returns Section 10 governance policy specifications and retention stats.
* `POST /governance/retention/enforce`: Manually triggers 90-day data retention cleanup.

---

## 8. Automated Verification Summary

| Test Layer | Test Target | Command | Result |
| :--- | :--- | :--- | :---: |
| **Backend Unit Tests** | Isolation Forest bounds, CUSUM math, multipliers, explanations, SQLite persistence, access auditing, and 90-day retention pruning | `.venv/bin/python3 -m unittest discover backend/tests` | **14 / 14 Passed (OK)** |
| **Frontend Adapter Tests** | REST contract adapter and mock server | `python3 frontend/test_adapter.py` | **4 / 4 Passed (OK)** |
| **Frontend Production Build** | TypeScript strict checks & Vite bundling | `npm run build` | **0 Errors (Exit 0)** |
| **Autonomous Browser Subagent** | Live queue deduplication, CUSUM tooltips, Admin Access Audit card, and Section 10 modal | Chromium Subagent | **0 Console Errors** |
