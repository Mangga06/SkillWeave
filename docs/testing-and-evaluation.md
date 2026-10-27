# Testing and evaluation

Automated backend tests cover session login/invalid login/logout, missing sessions, request header protection, role and cross-tenant denial, profile changes, required skills/dates/capacity, project cancellation, optimizer execution/publication, volunteer acceptance, hours approval, assigned leader progress, scenario non-mutation/staleness, CSV/atomic import, formula injection and last-admin safeguards.

Algorithm tests cover membership boundaries, activated rules and score bounds, mandatory verification, availability, seeded reproducibility, elites/nondecreasing best fitness, mutation repair, capacity/overlap/hour feasibility, duplicate prevention, protected assignments, baseline metrics, infeasible tasks and scenario copy behavior. Genetic operators are exercised through actual runs, not mirrored implementation assertions.

Frontend Vitest tests cover theme persistence/application, error propagation, unauthenticated redirect and volunteer role navigation. Playwright scripts cover coordinator login, theme changes, optimization history, downloads, mobile layout, reduced motion and 2D fallback. These require running local servers and Chrome.

Run `python -m backend.evaluate --seeds 5` for recorded repeated-seed metrics from the current database. Report mean/sample standard deviation for each method and seed; never infer empirical efficacy from fictional data. Hard-constraint violation output is zero because all algorithms use repair; tests independently check overlapping volunteer assignment pairs and capacity/hour constraints.

## Execution record

The initial sandbox run encountered a Windows temporary-directory permission error; in-memory test databases avoid that dependency. The sandbox also blocks Python's Windows event loop local socket pair. Running the test command with authorized local execution resolved this environment issue.

- Backend: 31 tests passed (one installed Starlette/httpx deprecation warning).
- TypeScript and Vite production build: passed. Initial interrupted dependency extraction was repaired. Vite reports large main/3D chunks; scene loading is lazy but more route-level splitting remains advisable.
- Frontend: 4 Vitest tests passed. Playwright: coordinator login/theme persistence/optimization/CSV download, mobile reduced-motion/2D fallback/no overflow, and every available role screen in both themes passed (3 browser tests). The initial mobile test used an ambiguous selector, fixed by targeting the hero network. No page JavaScript errors were reported. Docker Compose configuration validates, but the Docker daemon is stopped, so container/PostgreSQL execution was not tested.

Repeated-seed evaluation: three seeds, 30 candidates, 40 generations were executed against the fictional local database; raw records, means and sample standard deviations are in `evaluation-results.json`. These describe the seeded scenario only. Additional regression tests protect completed work during new publication, organization invitation consumption, and existing personal-workspace joining.

Expanded demo-history verification: 31 backend tests passed, including complete relational history, repeated-seed count stability, preservation of edited projects, scoped profile history, approved totals and optimization feasibility around current assignments. A dedicated Playwright browser test passed for volunteer profile history and coordinator directory history. Historical records are fictional seed fixtures; the 102 hours are demonstration records, not measured community outcomes.
