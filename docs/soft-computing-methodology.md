# Soft computing methodology

Implementation: `backend/optimizer.py`. This is a transparent research prototype, not an empirically validated ranking system.

## Fuzzy inference

Inputs are normalized proficiency against task requirements, experience / 5 (clipped), availability fit, difficulty / 5 and category preference. Unknown skill entries count as level zero. Only candidates covering the whole task window pass eligibility, so eligible candidates currently have availability fit 1; incomplete availability is excluded rather than fuzzily accepted.

For x in [0,1]: low(x)=max(0,1−2x); medium(x)=triangle(x;0,0.5,1); high(x)=max(0,2x−1). These are shoulder/triangular sets. Eight explicit rules include low availability → low, low proficiency → low, medium proficiency and high difficulty → low, medium proficiency and high availability → medium, and high proficiency and availability → high. Inspect the source for the full readable rule list.

Mamdani inference uses minimum for AND/implication, maximum for output aggregation, and numerical centroid over 101 equally spaced output points. Output sets use the same low/medium/high membership families. If no rule activates, suitability is 0.5. The returned trace includes input memberships and every activated rule with its strength. Self-report warnings remain visible.

Mandatory requirements gate eligibility before fuzzy scoring. Verified mandatory requirements require the explicit verification flag. High fuzzy scores never override qualifications, time windows, weekly hour limits, capacity or overlaps.

## Genetic algorithm

The chromosome maps task IDs to volunteer-ID lists. Initialization produces repaired randomized feasible teams plus a greedy candidate. Tournament selection samples three parents. Uniform task-level crossover combines their team lists. Mutation replaces one task team with a random candidate subset. Two elites survive. Every child is repaired and may undergo feasible refill. Fixed seed/config/input produce identical allocations and fitness traces; runtime varies.

Repair starts with protected assignments, then adds candidates subject to hard gates and per-ISO-week hours. Overlapping task windows cannot share a volunteer. An infeasible locked assignment raises a truthful failure rather than being silently removed. Dependencies are scheduled before dependent task windows at task validation, and actual task progress is blocked until prerequisites complete.

Greedy sorts candidates by fuzzy suitability in descending task priority; random fills in randomized order. Both share candidate gates, repair and fitness metrics. Minimum staffing and aggregate team coverage are soft objectives; report deficits explicitly.

## Research limitations

Fairness captures utilization dispersion only; it is not comprehensive ethical fairness. Learning rewards an existing goal with minimum proficiency, not newly invented expertise or supervision. There are no protected-characteristic ranking inputs. Self-reported experience is not certification. Repeated-seed experiments use fictional demonstration data and establish implementation behavior, not real-world effectiveness. Obtain consented representative data and independent evaluation before operational adoption.
