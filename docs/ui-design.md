# Workspace UI redesign

The workspace now uses white and slate surfaces, cobalt blue controls, and a navy project summary. The same
visual system covers the dashboard, navigation, catalogs, record details, forms, evidence, reports, and login.
Dark mode uses slate and navy surfaces with separately tuned text and accent colors.

## Layout and hierarchy

- The light sidebar groups the analyst workflow, integration work, and delivery governance. Blue selection
  states identify the current page; incident counts retain a semantic alert color.
- The project overview starts with the active project, its actual requirement/integration/test counts, completion,
  and target date. A single four-column metric strip replaces the separate colored statistic cards.
- Release readiness and quality results share the first dashboard row. Priority items and delivery progress
  follow, with the integration landscape arranged horizontally across the lower section.
- Larger table text, clearer headings, consistent controls, and quieter borders improve scanning. Page titles
  identify their function directly: Project overview, Traceability matrix, Project reports, and Administration.
- At smaller widths, navigation becomes a drawer and the dashboard stacks into one column. The drawer supports
  Escape, exposes its expanded state, and removes its links from keyboard navigation while closed.
- The reduced-motion preference is honored. DM Sans is served locally; the unused second font was removed.

## Color roles

| Role                 | Light theme | Dark theme |
| -------------------- | ----------- | ---------- |
| Workspace background | `#F4F6FA`   | `#0C1220`  |
| Surface              | `#FFFFFF`   | `#141E30`  |
| Primary text         | `#172033`   | `#EDF2FA`  |
| Secondary text       | `#59677D`   | `#A5B4CB`  |
| Primary action       | `#245CE2`   | `#3268DB`  |
| Project summary      | `#12213E`   | `#172B50`  |

Successful states still use green, warnings use amber, and failures use red. These colors express record status;
blue identifies actions, navigation, and progress. The shared palette lives in `frontend/src/styles.css`.

## Screenshots

- [Project overview](screenshots/dashboard.png)
- [Dark overview](screenshots/dashboard-dark.png)
- [Mobile overview](screenshots/dashboard-mobile.png)
- [Requirement catalog](screenshots/requirements.png)
- [Login](screenshots/login.png)

## Verification

The existing Playwright suite covers the real authoring, SOAP failure/correction/retest, UAT, attachment,
change, release, search, reporting, and navigation workflows. The redesign extends its existing accessibility
test to scan both light and dark dashboards, and its mobile test to verify Escape and inactive drawer behavior.
The screenshots were inspected at desktop and mobile sizes. The earlier backend delivery results remain in
`verification.md`; this change does not alter backend behavior or reset project data.

| Check                              | Observed result                                                                                                                           |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Complete Playwright workflow suite | **25 passed**, 0 failed, 0 skipped, 0 flaky, 95.60 seconds                                                                                |
| Dashboard accessibility            | Light and dark WCAG A/AA scans passed                                                                                                     |
| Deployed accessibility checks      | Login, light dashboard, dark dashboard, requirements, integrations, reports, and mobile requirements: **0 violations across seven scans** |
| Deployed browser errors            | 0 uncaught page errors during inspection                                                                                                  |
| Mobile containment                 | Document width 390 px at a 390 px viewport                                                                                                |
| TypeScript and Vite                | Production build passed                                                                                                                   |
| Frontend dependency audit          | 0 known vulnerabilities reported                                                                                                          |
| Formatting                         | Prettier check passed                                                                                                                     |
| Docker                             | Rebuilt frontend served at `http://127.0.0.1:8080`; services healthy                                                                      |

Machine-readable results are retained in [ui-verification-results.json](ui-verification-results.json).
The accessibility scans cover the listed views, not a complete accessibility certification. A separate
focused check of keyboard access, both themes, and the visible dark-mode skip link passed against the final
Docker build: **1 passed in 5.1 seconds**. No data reset was performed during this redesign.
