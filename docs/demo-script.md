# Demonstration script

1. Run migration and explicit seed; start API and frontend. State that all people, projects and activity are fictional.
2. Show the landing network and its labeled illustrative preview. Toggle Light/Dark/System. Use 2D view and accessible node list.
3. Sign in as coordinator (`coordinator@demo.skillweave.test`, `WeaveDemo!2026`). Overview includes explicitly fictional seeded history: four completed past projects, one ongoing project, 102 approved hours, attendance and feedback. Existing live records are preserved.
4. Open Projects, create a new project and a task within its dates. Select required skill thresholds, priority and staffing. Invalid capacities/dates produce validation errors.
5. Open the volunteer directory. Compare skills, verified flags, weekly hours and complete availability windows.
6. Open Optimization Lab. Use seed 42, population 30, generations 40. Start; wait for actual completion. Show recorded generation history, teams, gaps, objective breakdown, exclusions and baseline comparison. Accessible information is intentionally understaffed because sign language is absent.
7. Publish only after reviewing gaps. Open assignments and inspect invitations. Lock one proposed assignment to demonstrate preservation.
8. Sign out and sign in as a volunteer who actually appears in the published allocation. Accept an invitation; submit hours for that accepted assignment. Show that the volunteer cannot approve hours or access administration.
9. Sign in as the assigned team leader (check project details/seed). Record attendance and progress. A different leader cannot access the project.
10. Sign in as coordinator and approve the hours. Analytics now shows the approved record. Export assignments/hours CSV; review audit history.
11. Open What-if simulator. Choose an unconfirmed volunteer withdrawal or reduced task capacity. Preview leaves live assignments untouched. A scenario conflicting with accepted/locked assignments fails explicitly. Apply a feasible completed scenario after review. Changing source records makes old runs stale.
12. Show own skill/availability editing, private feedback, in-app notifications and first verified contribution badge. Review README limitations openly; this is a functional prototype, not completed production software.

Expanded history: open a volunteer in the directory, or sign in as a volunteer and open Skills & availability. Project contributions & work history lists their past projects, responsibilities, assignment states and approved hours. Browse Projects with status completed to inspect Riverbank renewal, Back-to-school bridge, Neighborhood wellness weekend, and Community harvest festival. Digital confidence week supplies current progress, invitations, a withdrawal/replacement example and a pending 2-hour record. Re-running `python -m backend.seed` adds no duplicates and does not reset edits.
