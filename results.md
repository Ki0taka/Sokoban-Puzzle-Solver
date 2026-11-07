# Sokoban Search Benchmark — Part 3 Results

Expansion safety cap: 500000 nodes per run. `limit` means the cap was reached before the frontier was exhausted; it is not a completed result.

| Level | Algorithm | Solution cost | Expanded | Generated | Max frontier | Pruned | Time (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Example 1 | BFS | 4 | 11 | 32 | 5 | 0 | 0.000073 |
| Example 1 | BFS + deadlock | 4 | 11 | 32 | 5 | 0 | 0.000076 |
| Example 1 | A* (h1) | 4 | 11 | 32 | 5 | 0 | 0.000116 |
| Example 1 | A* (h1) + deadlock | 4 | 11 | 32 | 5 | 0 | 0.000116 |
| Example 1 | A* (h2) | 4 | 8 | 24 | 6 | 0 | 0.000104 |
| Example 1 | A* (h2) + deadlock | 4 | 8 | 24 | 6 | 0 | 0.000108 |
| Example 1 | A* (h3) | 4 | 5 | 15 | 6 | 0 | 0.000076 |
| Example 1 | A* (h3) + deadlock | 4 | 5 | 15 | 6 | 0 | 0.000081 |
| Example 1 | A* (h3) + exact dead squares | 4 | 5 | 15 | 6 | 0 | 0.000076 |
| Example 2 | BFS | 29 | 1079 | 3246 | 89 | 0 | 0.006782 |
| Example 2 | BFS + deadlock | 29 | 459 | 1377 | 35 | 13 | 0.002955 |
| Example 2 | A* (h1) | 29 | 1079 | 3246 | 89 | 0 | 0.010543 |
| Example 2 | A* (h1) + deadlock | 29 | 459 | 1377 | 35 | 13 | 0.004626 |
| Example 2 | A* (h2) | 29 | 679 | 2080 | 78 | 0 | 0.008402 |
| Example 2 | A* (h2) + deadlock | 29 | 328 | 1002 | 39 | 12 | 0.004184 |
| Example 2 | A* (h3) | 29 | 353 | 1115 | 121 | 0 | 0.005342 |
| Example 2 | A* (h3) + deadlock | 29 | 135 | 431 | 65 | 12 | 0.002075 |
| Example 2 | A* (h3) + exact dead squares | 29 | 135 | 431 | 65 | 0 | 0.002020 |
| Example 3 | BFS | 20 | 1854 | 5163 | 244 | 0 | 0.011429 |
| Example 3 | BFS + deadlock | 20 | 915 | 2548 | 109 | 38 | 0.005835 |
| Example 3 | A* (h1) | 20 | 1701 | 4750 | 218 | 0 | 0.016962 |
| Example 3 | A* (h1) + deadlock | 20 | 876 | 2446 | 103 | 37 | 0.008990 |
| Example 3 | A* (h2) | 20 | 650 | 1835 | 159 | 0 | 0.008913 |
| Example 3 | A* (h2) + deadlock | 20 | 476 | 1344 | 101 | 19 | 0.006711 |
| Example 3 | A* (h3) | 20 | 445 | 1247 | 188 | 0 | 0.007471 |
| Example 3 | A* (h3) + deadlock | 20 | 327 | 925 | 123 | 17 | 0.005502 |
| Example 3 | A* (h3) + exact dead squares | 20 | 327 | 925 | 123 | 0 | 0.005046 |
| Example 4 | BFS | 19 | 3446 | 9969 | 955 | 0 | 0.023354 |
| Example 4 | BFS + deadlock | 19 | 1685 | 4905 | 390 | 105 | 0.011549 |
| Example 4 | A* (h1) | 19 | 2115 | 6161 | 679 | 0 | 0.022802 |
| Example 4 | A* (h1) + deadlock | 19 | 1192 | 3474 | 303 | 68 | 0.013259 |
| Example 4 | A* (h2) | 19 | 632 | 1854 | 220 | 0 | 0.010225 |
| Example 4 | A* (h2) + deadlock | 19 | 520 | 1533 | 149 | 19 | 0.008646 |
| Example 4 | A* (h3) | 19 | 561 | 1646 | 309 | 0 | 0.011360 |
| Example 4 | A* (h3) + deadlock | 19 | 439 | 1310 | 207 | 26 | 0.008996 |
| Example 4 | A* (h3) + exact dead squares | 19 | 439 | 1310 | 207 | 0 | 0.007425 |
| Example 5 | BFS | 30 | 315127 | 1029632 | 41050 | 0 | 2.974520 |
| Example 5 | BFS + deadlock | 30 | 122800 | 401559 | 14810 | 4467 | 1.103959 |
| Example 5 | A* (h1) | 30 | 213074 | 699183 | 40459 | 0 | 3.157172 |
| Example 5 | A* (h1) + deadlock | 30 | 87262 | 287023 | 14752 | 3471 | 1.270705 |
| Example 5 | A* (h2) | 30 | 24394 | 81189 | 9947 | 0 | 0.523801 |
| Example 5 | A* (h2) + deadlock | 30 | 14880 | 49788 | 5105 | 849 | 0.315632 |
| Example 5 | A* (h3) | 30 | 18247 | 61699 | 13163 | 0 | 0.498116 |
| Example 5 | A* (h3) + deadlock | 30 | 9537 | 32865 | 6499 | 720 | 0.245331 |
| Example 5 | A* (h3) + exact dead squares | 30 | 9537 | 32865 | 6499 | 0 | 0.205022 |
| Fig 7 Ex 1 | BFS | 41 | 2307 | 5650 | 129 | 0 | 0.013424 |
| Fig 7 Ex 1 | BFS + deadlock | 41 | 1128 | 2780 | 69 | 54 | 0.006826 |
| Fig 7 Ex 1 | A* (h1) | 41 | 2279 | 5574 | 147 | 0 | 0.021637 |
| Fig 7 Ex 1 | A* (h1) + deadlock | 41 | 1100 | 2704 | 76 | 54 | 0.010726 |
| Fig 7 Ex 1 | A* (h2) | 41 | 2228 | 5434 | 196 | 0 | 0.032170 |
| Fig 7 Ex 1 | A* (h2) + deadlock | 41 | 1047 | 2560 | 80 | 54 | 0.015467 |
| Fig 7 Ex 1 | A* (h3) | 41 | 2182 | 5321 | 204 | 0 | 0.040616 |
| Fig 7 Ex 1 | A* (h3) + deadlock | 41 | 1000 | 2459 | 120 | 54 | 0.018281 |
| Fig 7 Ex 1 | A* (h3) + exact dead squares | 41 | 1000 | 2459 | 120 | 0 | 0.014732 |
| Fig 7 Ex 2 | BFS | 55 | 54726 | 146035 | 2798 | 0 | 0.416970 |
| Fig 7 Ex 2 | BFS + deadlock | 55 | 6432 | 16983 | 302 | 829 | 0.044313 |
| Fig 7 Ex 2 | A* (h1) | 55 | 54505 | 145466 | 3008 | 0 | 0.660045 |
| Fig 7 Ex 2 | A* (h1) + deadlock | 55 | 6307 | 16663 | 317 | 824 | 0.068911 |
| Fig 7 Ex 2 | A* (h2) | 55 | 49036 | 131091 | 2815 | 0 | 1.032962 |
| Fig 7 Ex 2 | A* (h2) + deadlock | 55 | 5619 | 14914 | 322 | 758 | 0.112611 |
| Fig 7 Ex 2 | A* (h3) | 55 | 49972 | 133404 | 3704 | 0 | 1.400845 |
| Fig 7 Ex 2 | A* (h3) + deadlock | 55 | 5718 | 15186 | 444 | 790 | 0.135853 |
| Fig 7 Ex 2 | A* (h3) + exact dead squares | 55 | 5206 | 13795 | 413 | 0 | 0.089299 |

## Solutions for Figure 7 Examples

### Fig 7 Ex 1
- **BFS** (cost=41, iterations=2307):
  `D D L L L U L D D U R R R R U U L D R D L L L D L U U D R R R R D D L U R U L L L`
- **BFS + deadlock** (cost=41, iterations=1128):
  `D D L L L U L D D U R R R R U U L D R D L L L D L U U D R R R R D D L U R U L L L`
- **A* (h1)** (cost=41, iterations=2279):
  `D D L L L U L D D U R R R R U U L D R D L L L D L U U D R R R R D D L U R U L L L`
- **A* (h1) + deadlock** (cost=41, iterations=1100):
  `D D L L L U L D D U R R R R U U L D R D L L L D L U U D R R R R D D L U R U L L L`
- **A* (h2)** (cost=41, iterations=2228):
  `D D L L L U L D D U R R R R U U L D R D L L L D L U U D R R R R D D L U R U L L L`
- **A* (h2) + deadlock** (cost=41, iterations=1047):
  `D D L L L U L D D U R R R R U U L D R D L L L D L U U D R R R R D D L U R U L L L`
- **A* (h3)** (cost=41, iterations=2182):
  `D D L L L U L D D U R R R R U U L D R D L L L D L U U D R R R R D D L U R U L L L`
- **A* (h3) + deadlock** (cost=41, iterations=1000):
  `D D L L L U L D D U R R R R U U L D R D L L L D L U U D R R R R D D L U R U L L L`
- **A* (h3) + exact dead squares** (cost=41, iterations=1000):
  `D D L L L U L D D U R R R R U U L D R D L L L D L U U D R R R R D D L U R U L L L`

### Fig 7 Ex 2
- **BFS** (cost=55, iterations=54726):
  `U U L L L L D L U R R R R R D D L U R U L L R D D L U L U D R R U L U L R D D L U L L D R R R D R U R U L L L`
- **BFS + deadlock** (cost=55, iterations=6432):
  `U U L L L L D L U R R R R R D D L U R U L L R D D L U L U D R R U L U L R D D L U L L D R R R D R U R U L L L`
- **A* (h1)** (cost=55, iterations=54505):
  `U U L L L L D L U R R R R R D D L U R U L L R D D L U L U D R R U L U L R D D L U L L D R R R D R U R U L L L`
- **A* (h1) + deadlock** (cost=55, iterations=6307):
  `U U L L L L D L U R R R R R D D L U R U L L R D D L U L U D R R U L U L R D D L U L L D R R R D R U R U L L L`
- **A* (h2)** (cost=55, iterations=49036):
  `U U L L L L D L U R R R R R D D L U R U L L R D D L U L U D R R U L U L R D D L U L L D R R R D R U R U L L L`
- **A* (h2) + deadlock** (cost=55, iterations=5619):
  `U U L L L L D L U R R R R R D D L U R U L L R D D L U L U D R R U L U L R D D L U L L D R R R D R U R U L L L`
- **A* (h3)** (cost=55, iterations=49972):
  `U U L L L L D L U R R R R R D D L U R U L L R D D L U L U D R R U L U L R D D L U L L D R R R D R U R U L L L`
- **A* (h3) + deadlock** (cost=55, iterations=5718):
  `U U L L L L D L U R R R R R D D L U R U L L R D D L U L U D R R U L U L R D D L U L L D R R R D R U R U L L L`
- **A* (h3) + exact dead squares** (cost=55, iterations=5206):
  `U U L L L L D L U R R R R R D D L U R U L L R D D L U L U D R R U L U L R D D L U L L D R R R D R U R U L L L`

