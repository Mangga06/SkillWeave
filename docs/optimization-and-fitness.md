# Optimization and fitness

Each objective is normalized to [0,1]. The weighted average divides by total weight. API validation requires all seven known weights, each 0–1, with positive total.

| Objective | Default | Definition |
|---|---:|---|
| Coverage | .30 | Covered task/skill requirements / total task/skill requirements. A single team member must meet the threshold and any verification requirement. |
| Staffing | .20 | Priority-weighted min(1, team size / minimum staffing) across tasks. |
| Suitability | .15 | Mean Mamdani fuzzy output across assignment pairs; zero when none assigned. |
| Fairness | .15 | max(0, 1 − population standard deviation of assigned hours / (weekly hours × distinct input weeks)). Zero-availability members contribute utilization zero. |
| Preference | .05 | Fraction of assignments with project category in declared interests. |
| Learning | .05 | Fraction with a declared skill goal and existing minimum proficiency for a required skill. |
| Stability | .10 | Retained active assignment pairs / previous active pairs; one if no previous plan. |

Task windows, weekly hours, duplicate pairs, capacity and mandatory qualifications are hard constraints enforced during repair, not compensable penalties. Maximum hours are checked separately within each task's start ISO week. Cross-week tasks count in their start week; detailed hour splitting remains a limitation. Protected/accepted assignments must be feasible or the run fails.

Unfilled critical responsibilities reduce priority-weighted staffing; missing skills reduce coverage. These are separate objectives. Fuzzy proficiency and coverage intentionally describe individual versus aggregate fit but remain correlated. Do not interpret the overall fitness as accuracy or a probability of success.

Result snapshots retain allocation, input, weights, seed, generation best/mean, fuzzy traces, exclusions, missing skills, unfilled tasks, assigned hours, imbalance, symmetric assignment-pair changes, baseline results and runtime. Baseline runtime is the baseline operation; GA runtime includes baseline computation and the entire run, so runtime measurements should not be presented as isolated equal-cost algorithm benchmarks.

Scenarios copy the snapshot and edit the copy. Publication compares the original live snapshot, applies a valid hypothetical change, and updates invitations without touching protected assignments. A stale result requires a new run. Resource-loss requires a future resource model. There is no production-grade concurrent publication lock yet.
