# Group6_Summer-Project
UCD COMP47360 Team 6 - Accessibility Intelligence App for Manhattan

## Development Guidelines & Workflow

Welcome to the official repository for **ClearPath**. To ensure high code quality, robust architecture, and smooth sprint integrations, all team members are required to strictly adhere to the following development workflows.

---

## 1. Git Branching & Pull Request (PR) Policy

The `main` branch is locked and reserved strictly for stable, production-ready code. No direct pushes to `main` are allowed.

### Branch Naming Convention
When working on a backlog task, create a separate feature branch using the following shortened prefix formats:
* `feature/fe-mob-[task]` (Mobile Front-End / React Native, e.g., `feature/fe-mob-login`)
* `feature/fe-web-[task]` (Web Front-End / Dashboard, e.g., `feature/fe-web-charts`)
* `feature/be-[task]`     (Back-End / Flask & Poetry, e.g., `feature/be-clinic-api`)
* `feature/db-[task]`     (Database & Data Processing, e.g., `feature/db-nyc-scraping`)
* `bugfix/[issue]`        (For resolving broken code or system crashes)

### Pull Request & Integration Workflow
1. Commit and push your work to your remote feature branch.
2. Open a **Pull Request (PR)** on GitHub targeting the `main` branch.
3. Link your PR to the corresponding **Notion Backlog Task**.
4. **Peer Review Requirement:** Tag at least one team member to review your code. 
5. Once approved by your peer reviewer, the branch can be safely merged into `main`.

---

## 2. Code Quality & Unit Testing

To safeguard our MVP increment against unexpected crashes before project demonstrations, **all new feature implementations must include automated unit tests.**

* **Backend (Flask/Poetry):** Ensure all new RESTful API endpoints and data parsing functions have corresponding unit tests tracking status codes and expected JSON payloads. Run your tests locally via Poetry before submitting a PR.
* **Frontend (React Native):** Ensure core navigation routers and base UI helper utilities pass baseline component testing.
* **Pre-merge Check:** Do not approve or merge any PR if the local unit tests are failing.

---

## 3. Scrum Tracking & Sprint Logistics

Scrum Master will be actively monitoring repository health and metrics to update our **Notion Backlog** and **Excel Burn-Down Charts**.

* **Daily Updates:** Please report your completed tasks and actual work hours to Scrum Master daily (or within a 2-day buffer window). 
* **Completion Rate & Progress Tracking:** Your **Actual Working Hours** will be constantly cross-referenced with the **Estimated Time** allocated in the backlog. This ratio will serve as a key metric to reflect the true completeness and development velocity of each task.
* **Scope Variance Check:** If your actual work hours vary from the backlog estimate by more than 6 hours within 48 hours of the deadline or if the progress seems stuck, Scrum Master will check in with you to analyze potential scope creep, help unblock dependencies, and recalibrate our sprint estimation metrics.
