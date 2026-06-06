# FIFA 2026 Fantasy Draft — Spreadsheet Preview
# This shows what each tab looks like after running `python -m src.seed_data`

================================================================================
TAB 1: "Scoring Rules"
================================================================================

| Category         | Event              | Points | Notes                                    |
|------------------|--------------------|--------|------------------------------------------|
|                  |                    |        |                                          |
| GROUP STAGE      |                    |        |                                          |
|                  | Win                | 3.0    | Team wins the match                      |
|                  | Draw               | 1.5    | Match ends in a draw                     |
|                  | Goal Scored        | 0.5    | Per goal in regular time                 |
|                  | Goal Conceded      | -0.25  | Per goal conceded                        |
|                  |                    |        |                                          |
| KNOCKOUT ROUNDS  |                    |        |                                          |
|                  | Win                | 3.0    | Team wins (regular/ET)                   |
|                  | Draw (to Penalties)| 1.5    | If match goes to shootout               |
|                  | Goal Scored        | 0.75   | Per goal in regular/extra time           |
|                  | Goal Conceded      | -0.25  | Per goal conceded                        |
|                  |                    |        |                                          |
| IMPORTANT NOTES  |                    |        |                                          |
|                  | Penalty Shootout   | N/A    | Penalty goals do NOT count for scoring   |
|                  | Extra Time Goals   | Count  | Goals in extra time count as regular goals|


================================================================================
TAB 2: "Draft Picks"
================================================================================

| Player   | Team 1   | Team 2      | Team 3    | Team 4  | Team 5      | Team 6   | Team 7  | Team 8  | Team 9 | Team 10  |
|----------|----------|-------------|-----------|---------|-------------|----------|---------|---------|--------|----------|
| Player 1 | Brazil   | France      | Argentina | England | Spain       | Netherlands | Portugal | Germany | Belgium | Uruguay |
| Player 2 | Colombia | Italy       | Croatia   | Denmark | Japan       | South Korea | Mexico | Switzerland | USA  | Senegal  |
| Player 3 | Canada   | Australia   | Morocco   | Nigeria | Ecuador     | Serbia   | Poland  | Sweden  | Wales  | Ghana    |
| Player 4 | Cameroon | Tunisia     | Saudi Arabia | Iran | Costa Rica  | Qatar    | Peru    | Chile   | Egypt  | Algeria  |


================================================================================
TAB 3: "Match Schedule" (showing first 20 of 104 matches)
================================================================================

| Date       | Stage | Group | Home Team | Away Team | Home Goals | Away Goals | Home Penalties | Away Penalties | Status    | Home Points | Away Points |
|------------|-------|-------|-----------|-----------|------------|------------|----------------|----------------|-----------|-------------|-------------|
| 2026-06-11 | group | A     | USA       | Group A2  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-11 | group | B     | Group B1  | Group B2  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-12 | group | A     | Group A3  | Group A4  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-12 | group | B     | Group B3  | Group B4  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-12 | group | C     | Mexico    | Group C2  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-13 | group | C     | Group C3  | Group C4  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-13 | group | D     | Group D1  | Group D2  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-13 | group | D     | Group D3  | Group D4  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-14 | group | E     | Canada    | Group E2  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-14 | group | E     | Group E3  | Group E4  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-14 | group | F     | Group F1  | Group F2  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-15 | group | F     | Group F3  | Group F4  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-15 | group | G     | Group G1  | Group G2  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-15 | group | G     | Group G3  | Group G4  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-15 | group | H     | Group H1  | Group H2  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-16 | group | A     | USA       | Group A3  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-16 | group | H     | Group H3  | Group H4  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-16 | group | I     | Group I1  | Group I2  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-16 | group | I     | Group I3  | Group I4  |            |            |                |                | scheduled | 0           | 0           |
| 2026-06-17 | group | A     | Group A2  | Group A4  |            |            |                |                | scheduled | 0           | 0           |
| ...        | ...   | ...   | ...       | ...       |            |            |                |                |           |             |             |

--- KNOCKOUT STAGE (starts after group stage) ---

| Date       | Stage        | Group | Home Team           | Away Team           | Home Goals | Away Goals | Home Pen | Away Pen | Status    | Home Pts | Away Pts |
|------------|--------------|-------|---------------------|---------------------|------------|------------|----------|----------|-----------|----------|----------|
| 2026-07-01 | round_of_32  |       | R32 Match 1 - TBD   | R32 Match 1 - TBD   |            |            |          |          | scheduled | 0        | 0        |
| 2026-07-01 | round_of_32  |       | R32 Match 2 - TBD   | R32 Match 2 - TBD   |            |            |          |          | scheduled | 0        | 0        |
| 2026-07-01 | round_of_32  |       | R32 Match 3 - TBD   | R32 Match 3 - TBD   |            |            |          |          | scheduled | 0        | 0        |
| 2026-07-01 | round_of_32  |       | R32 Match 4 - TBD   | R32 Match 4 - TBD   |            |            |          |          | scheduled | 0        | 0        |
| ...        |              |       |                     |                     |            |            |          |          |           |          |          |
| 2026-07-05 | round_of_16  |       | R16 Match 1 - TBD   | R16 Match 1 - TBD   |            |            |          |          | scheduled | 0        | 0        |
| ...        |              |       |                     |                     |            |            |          |          |           |          |          |
| 2026-07-09 | quarter_final|       | QF Match 1 - TBD    | QF Match 1 - TBD    |            |            |          |          | scheduled | 0        | 0        |
| ...        |              |       |                     |                     |            |            |          |          |           |          |          |
| 2026-07-13 | semi_final   |       | SF Match 1 - TBD    | SF Match 1 - TBD    |            |            |          |          | scheduled | 0        | 0        |
| 2026-07-14 | semi_final   |       | SF Match 2 - TBD    | SF Match 2 - TBD    |            |            |          |          | scheduled | 0        | 0        |
| 2026-07-18 | third_place  |       | 3rd Place - TBD     | 3rd Place - TBD     |            |            |          |          | scheduled | 0        | 0        |
| 2026-07-19 | final        |       | Final - TBD         | Final - TBD         |            |            |          |          | scheduled | 0        | 0        |


================================================================================
TAB 3 — AFTER SCORES ARE FILLED IN (example of what it looks like mid-tournament)
================================================================================

| Date       | Stage | Group | Home Team | Away Team | Home Goals | Away Goals | Home Pen | Away Pen | Status   | Home Points | Away Points |
|------------|-------|-------|-----------|-----------|------------|------------|----------|----------|----------|-------------|-------------|
| 2026-06-11 | group | A     | USA       | Group A2  | 2          | 1          |          |          | finished | 3.75        | 0.0         |
| 2026-06-11 | group | B     | Group B1  | Group B2  | 0          | 0          |          |          | finished | 1.5         | 1.5         |
| 2026-06-12 | group | A     | Group A3  | Group A4  | 1          | 1          |          |          | finished | 1.75        | 1.75        |
| 2026-06-12 | group | C     | Mexico    | Group C2  | 3          | 0          |          |          | finished | 4.5         | -0.75       |

Scoring breakdown for "USA 2-1 Group A2":
  - USA:      Win(3) + 2 goals(2×0.5=1.0) + 1 conceded(1×-0.25=-0.25) = 3.75
  - Group A2: Loss(0) + 1 goal(1×0.5=0.5) + 2 conceded(2×-0.25=-0.5)  = 0.0

Scoring breakdown for "Group B1 0-0 Group B2":
  - Both:     Draw(1.5) + 0 goals(0) + 0 conceded(0) = 1.5


================================================================================
TAB 4: "Leaderboard" (initial — all zeros before tournament starts)
================================================================================

| Rank | Player   | Total Points | Team 1           | Team 2          | Team 3          | Team 4         | Team 5           | Team 6          | Team 7         | Team 8            | Team 9        | Team 10        |
|------|----------|--------------|------------------|-----------------|-----------------|----------------|------------------|-----------------|----------------|-------------------|---------------|----------------|
| 1    | Player 1 | 0.0          | Brazil (0.0)     | France (0.0)    | Argentina (0.0) | England (0.0)  | Spain (0.0)      | Netherlands (0.0)| Portugal (0.0) | Germany (0.0)     | Belgium (0.0) | Uruguay (0.0)  |
| 2    | Player 2 | 0.0          | Colombia (0.0)   | Italy (0.0)     | Croatia (0.0)   | Denmark (0.0)  | Japan (0.0)      | South Korea (0.0)| Mexico (0.0)   | Switzerland (0.0) | USA (0.0)     | Senegal (0.0)  |
| 3    | Player 3 | 0.0          | Canada (0.0)     | Australia (0.0) | Morocco (0.0)   | Nigeria (0.0)  | Ecuador (0.0)    | Serbia (0.0)    | Poland (0.0)   | Sweden (0.0)      | Wales (0.0)   | Ghana (0.0)    |
| 4    | Player 4 | 0.0          | Cameroon (0.0)   | Tunisia (0.0)   | Saudi Arabia (0.0)| Iran (0.0)   | Costa Rica (0.0) | Qatar (0.0)     | Peru (0.0)     | Chile (0.0)       | Egypt (0.0)   | Algeria (0.0)  |


================================================================================
TAB 4: "Leaderboard" — EXAMPLE MID-TOURNAMENT (after some matches played)
================================================================================

| Rank | Player   | Total Points | Team 1           | Team 2          | Team 3            | Team 4          | ... |
|------|----------|--------------|------------------|-----------------|-------------------|-----------------|-----|
| 1    | Player 1 | 28.5         | Brazil (8.25)    | France (6.0)    | Argentina (5.75)  | England (3.75)  | ... |
| 2    | Player 2 | 22.75        | Colombia (5.5)   | Italy (4.5)     | Croatia (4.25)    | Denmark (3.0)   | ... |
| 3    | Player 3 | 18.0         | Canada (4.5)     | Australia (3.75)| Morocco (3.5)     | Nigeria (2.25)  | ... |
| 4    | Player 4 | 12.25        | Cameroon (3.0)   | Tunisia (2.75)  | Saudi Arabia (2.5)| Iran (1.5)      | ... |


================================================================================
MATCH COUNT SUMMARY
================================================================================

Stage             | Matches | Dates
------------------|---------|------------------
Group Stage       | 72      | June 11 - June 26
Round of 32       | 16      | July 1 - July 4
Round of 16       | 8       | July 5 - July 8
Quarter Finals    | 4       | July 9 - July 10
Semi Finals       | 2       | July 13 - July 14
Third Place       | 1       | July 18
Final             | 1       | July 19
------------------|---------|------------------
TOTAL             | 104     |
