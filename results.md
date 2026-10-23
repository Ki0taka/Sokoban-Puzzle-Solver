# Sokoban Search Benchmark

Expansion safety cap: 500000 nodes per run. `limit` means the cap was reached before the frontier was exhausted; it is not a completed result.

| Level | Algorithm | Solution cost | Expanded | Generated | Max frontier | Time (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Example 1 | BFS | 4 | 11 | 32 | 5 | 0.000109 |
| Example 1 | A* (h1) | 4 | 11 | 32 | 5 | 0.000144 |
| Example 1 | A* (h2) | 4 | 8 | 24 | 6 | 0.000109 |
| Example 1 | A* (h3) | 4 | 5 | 15 | 6 | 0.000162 |
| Example 2 | BFS | 29 | 1079 | 3246 | 89 | 0.007941 |
| Example 2 | A* (h1) | 29 | 1079 | 3246 | 89 | 0.017163 |
| Example 2 | A* (h2) | 29 | 679 | 2080 | 78 | 0.009291 |
| Example 2 | A* (h3) | 29 | 135 | 431 | 65 | 0.004839 |
| Example 3 | BFS | 20 | 1854 | 5163 | 244 | 0.012687 |
| Example 3 | A* (h1) | 20 | 1701 | 4750 | 218 | 0.017933 |
| Example 3 | A* (h2) | 20 | 650 | 1835 | 159 | 0.009548 |
| Example 3 | A* (h3) | 20 | 327 | 925 | 123 | 0.011497 |
| Example 4 | BFS | 19 | 3446 | 9969 | 955 | 0.029726 |
| Example 4 | A* (h1) | 19 | 2115 | 6161 | 679 | 0.026035 |
| Example 4 | A* (h2) | 19 | 632 | 1854 | 220 | 0.011925 |
| Example 4 | A* (h3) | 19 | 439 | 1310 | 207 | 0.023193 |
| Example 5 | BFS | 30 | 315127 | 1029632 | 41050 | 4.615901 |
| Example 5 | A* (h1) | 30 | 213074 | 699183 | 40459 | 4.773721 |
| Example 5 | A* (h2) | 30 | 24394 | 81189 | 9947 | 0.680104 |
| Example 5 | A* (h3) | 30 | 9537 | 32865 | 6499 | 0.686106 |
