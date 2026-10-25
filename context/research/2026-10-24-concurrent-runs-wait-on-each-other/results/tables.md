# Tables from the result files (generated; every number is wall-clock on one shared machine)

## curve.json (load average 7)

| threads | product: 8 in sequence / on n threads (ms) | speedup | per call in parallel | bare: in sequence / parallel | speedup | per call in parallel |
|---|---|---|---|---|---|---|
| 1 | 20.3 / 20.1 | 1.01 | 20.1 | 12.3 / 13.4 | 0.92 | 12.9 |
| 2 | 38.3 / 26.4 | 1.45 | 26.1 | 24.5 / 13.6 | 1.8 | 12.5 |
| 4 | 75.4 / 47.7 | 1.58 | 42.0 | 51.8 / 15.4 | 3.36 | 13.9 |
| 8 | 159.1 / 104.8 | 1.52 | 78.5 | 108.9 / 31.1 | 3.51 | 24.5 |

## curve-2.json (load average 17)

| threads | product: 8 in sequence / on n threads (ms) | speedup | per call in parallel | bare: in sequence / parallel | speedup | per call in parallel |
|---|---|---|---|---|---|---|
| 1 | 18.5 / 18.3 | 1.01 | 18.3 | 12.2 / 12.0 | 1.01 | 11.6 |
| 2 | 38.1 / 26.0 | 1.47 | 24.4 | 25.5 / 13.8 | 1.85 | 12.9 |
| 4 | 76.0 / 48.5 | 1.57 | 40.9 | 49.2 / 15.4 | 3.19 | 13.9 |
| 8 | 156.9 / 83.4 | 1.88 | 68.5 | 99.2 / 29.9 | 3.32 | 23.7 |

## timeline.json (load average 6): batch walls in sequence [152.1, 152.3, 154.2], on 8 threads [97.1, 83.8, 91.5], speedup 1.66

| phase | n per 8 calls | in sequence: wall ms (thread cpu) | on 8 threads: wall ms (thread cpu) | per call, sequence -> parallel |
|---|---|---|---|---|
| Thread.start | 8 | 1.1 (0.5) | 1.7 (0.5) | 0.14 -> 0.22 |
| artifacts | 8 | 2.8 (2.7) | 24.2 (5.3) | 0.35 -> 3.03 |
| check_module | 8 | 0.0 (0.0) | 0.0 (0.0) | 0.0 -> 0.0 |
| engine | 8 | 0.0 (0.0) | 0.0 (0.0) | 0.01 -> 0.01 |
| guest_body | 8 | 100.7 (99.1) | 121.5 (112.5) | 12.59 -> 15.19 |
| guest_home | 8 | 2.8 (2.6) | 8.1 (4.7) | 0.35 -> 1.01 |
| identity_check | 8 | 4.8 (4.5) | 9.6 (7.0) | 0.6 -> 1.2 |
| instantiate | 16 | 1.1 (1.0) | 1.8 (1.2) | 0.07 -> 0.11 |
| join | 8 | 0.0 (0.0) | 0.0 (0.0) | 0.0 -> 0.0 |
| module | 8 | 0.0 (0.0) | 0.0 (0.0) | 0.0 -> 0.0 |
| preopens | 8 | 22.2 (22.1) | 221.5 (41.5) | 2.78 -> 27.69 |
| private_make | 16 | 3.3 (3.1) | 5.6 (4.3) | 0.21 -> 0.35 |
| private_remove | 16 | 5.3 (5.2) | 11.6 (7.5) | 0.33 -> 0.72 |
| release_step | 24 | 8.3 (8.2) | 15.3 (10.8) | 0.35 -> 0.64 |
| run | 8 | 154.1 (52.3) | 553.5 (110.7) | 19.26 -> 69.19 |
| serve | 8 | 100.5 (0.2) | 121.4 (0.3) | 12.57 -> 15.17 |
| store_close | 24 | 2.7 (2.7) | 3.3 (2.9) | 0.11 -> 0.14 |
| sweep | 8 | 0.0 (0.0) | 0.0 (0.0) | 0.0 -> 0.0 |
| thread_start | 8 | 1.3 (0.7) | 1.9 (0.7) | 0.16 -> 0.24 |
| walk | 8 | 10.0 (9.9) | 152.2 (40.0) | 1.25 -> 19.02 |
| wasm_call | 80 | 94.7 (93.2) | 110.6 (104.2) | 1.18 -> 1.38 |
| zip | 8 | 20.5 (20.5) | 212.3 (37.1) | 2.56 -> 26.53 |

| lock | acquisitions per 8 calls | in sequence: held ms | on 8 threads: held ms | on 8 threads: waited ms (summed) | longest hold ms |
|---|---|---|---|---|---|
| cache_lock | 83 | 0.21 | 0.17 | 0.02 | 0.025 |
| held_lock | 32 | 0.04 | 0.06 | 0.01 | 0.007 |
| zip_lock | 16 | 20.7 | 59.8 | 163.06 | 8.821 |
| warnings_lock | 8 | 0.01 | 0.02 | 0.02 | 0.006 |
| stack_size_lock | 8 | 1.2 | 1.82 | 0.0 | 0.401 |
| outputs_lock | 40 | 0.12 | 0.11 | 0.02 | 0.005 |
| epoch_callback_lock | 8 | 0.01 | 0.01 | 0.0 | 0.002 |

Every run of the parallel batch (ms from the batch's start):

- run 42 (81.1 ms): artifacts[0-4] walk[4-24] zip[24-60] guest_home[62-63] guest_body[64-80] release_step[80-81] release_step[81-81] release_step[81-81]
- run 43 (51.6 ms): artifacts[0-4] walk[4-21] zip[21-31] guest_home[32-33] guest_body[34-48] release_step[48-50] release_step[50-52] release_step[52-52]
- run 44 (67.8 ms): artifacts[0-3] walk[3-23] zip[23-44] guest_home[46-47] guest_body[48-66] release_step[66-67] release_step[68-68] release_step[68-68]
- run 45 (75.3 ms): artifacts[1-4] walk[4-23] zip[23-53] guest_home[54-56] guest_body[57-73] release_step[73-75] release_step[75-76] release_step[76-76]
- run 46 (88.0 ms): artifacts[1-4] walk[4-25] zip[25-68] guest_home[69-70] guest_body[72-88] release_step[88-88] release_step[89-89] release_step[89-89]
- run 47 (55.9 ms): artifacts[1-3] walk[3-21] zip[21-36] guest_home[37-38] guest_body[39-55] release_step[55-56] release_step[56-57] release_step[57-57]
- run 48 (89.7 ms): artifacts[2-5] walk[5-25] zip[25-77] guest_home[78-78] guest_body[79-90] release_step[90-91] release_step[91-91] release_step[91-91]
- run 49 (44.1 ms): artifacts[2-4] walk[4-21] zip[21-27] guest_home[28-29] guest_body[30-43] release_step[43-45] release_step[45-46] release_step[46-46]

## timeline-2.json (load average 17): batch walls in sequence [142.9, 163.1, 155.3], on 8 threads [76.1, 101.9, 83.3], speedup 1.86

| phase | n per 8 calls | in sequence: wall ms (thread cpu) | on 8 threads: wall ms (thread cpu) | per call, sequence -> parallel |
|---|---|---|---|---|
| Thread.start | 8 | 0.7 (0.4) | 1.4 (0.5) | 0.09 -> 0.17 |
| artifacts | 8 | 2.6 (2.6) | 26.3 (6.7) | 0.32 -> 3.28 |
| check_module | 8 | 0.0 (0.0) | 0.0 (0.0) | 0.0 -> 0.0 |
| engine | 8 | 0.0 (0.0) | 0.0 (0.0) | 0.01 -> 0.0 |
| guest_body | 8 | 96.2 (95.5) | 112.1 (105.4) | 12.03 -> 14.01 |
| guest_home | 8 | 2.6 (2.5) | 6.9 (3.9) | 0.32 -> 0.87 |
| identity_check | 8 | 4.1 (3.9) | 8.7 (6.3) | 0.51 -> 1.09 |
| instantiate | 16 | 0.9 (0.9) | 1.4 (1.0) | 0.05 -> 0.09 |
| join | 8 | 0.0 (0.0) | 0.0 (0.0) | 0.0 -> 0.0 |
| module | 8 | 0.0 (0.0) | 0.0 (0.0) | 0.0 -> 0.0 |
| preopens | 8 | 29.1 (23.8) | 185.4 (35.3) | 3.64 -> 23.17 |
| private_make | 16 | 3.0 (3.0) | 5.3 (3.9) | 0.19 -> 0.33 |
| private_remove | 16 | 4.7 (4.6) | 11.7 (7.1) | 0.29 -> 0.73 |
| release_step | 24 | 8.1 (7.4) | 14.6 (9.8) | 0.34 -> 0.61 |
| run | 8 | 155.3 (52.3) | 511.0 (106.1) | 19.41 -> 63.87 |
| serve | 8 | 96.3 (0.1) | 111.7 (0.2) | 12.03 -> 13.96 |
| store_close | 24 | 3.2 (2.5) | 2.6 (2.4) | 0.13 -> 0.11 |
| sweep | 8 | 0.0 (0.0) | 0.0 (0.0) | 0.0 -> 0.0 |
| thread_start | 8 | 0.9 (0.6) | 1.6 (0.7) | 0.12 -> 0.2 |
| walk | 8 | 9.7 (9.5) | 156.5 (43.2) | 1.22 -> 19.56 |
| wasm_call | 80 | 91.0 (90.3) | 103.5 (98.4) | 1.14 -> 1.29 |
| zip | 8 | 27.4 (22.1) | 173.7 (30.5) | 3.42 -> 21.71 |

| lock | acquisitions per 8 calls | in sequence: held ms | on 8 threads: held ms | on 8 threads: waited ms (summed) | longest hold ms |
|---|---|---|---|---|---|
| cache_lock | 81 | 0.15 | 0.11 | 0.01 | 0.007 |
| held_lock | 32 | 0.04 | 0.06 | 0.01 | 0.006 |
| zip_lock | 16 | 27.55 | 47.35 | 135.57 | 7.336 |
| warnings_lock | 8 | 0.01 | 0.03 | 0.0 | 0.021 |
| stack_size_lock | 8 | 0.83 | 1.5 | 0.0 | 0.469 |
| outputs_lock | 40 | 0.09 | 0.1 | 0.02 | 0.014 |
| epoch_callback_lock | 8 | 0.01 | 0.01 | 0.0 | 0.001 |

Every run of the parallel batch (ms from the batch's start):

- run 42 (79.8 ms): artifacts[0-4] walk[4-25] zip[25-59] guest_home[61-62] guest_body[63-79] release_step[79-80] release_step[80-80] release_step[80-80]
- run 43 (49.0 ms): artifacts[0-4] walk[4-22] zip[22-31] guest_home[32-34] guest_body[34-48] release_step[48-49] release_step[49-49] release_step[49-49]
- run 44 (54.9 ms): artifacts[0-4] walk[4-22] zip[22-37] guest_home[38-39] guest_body[40-53] release_step[53-55] release_step[55-55] release_step[55-55]
- run 45 (65.7 ms): artifacts[1-4] walk[4-25] zip[25-46] guest_home[49-50] guest_body[50-64] release_step[64-66] release_step[66-66] release_step[66-66]
- run 46 (60.9 ms): artifacts[1-4] walk[4-23] zip[23-42] guest_home[43-44] guest_body[45-59] release_step[59-61] release_step[61-62] release_step[62-62]
- run 47 (47.5 ms): artifacts[1-4] walk[4-22] zip[22-28] guest_home[29-30] guest_body[31-45] release_step[45-47] release_step[47-48] release_step[48-48]
- run 48 (71.5 ms): artifacts[1-4] walk[4-25] zip[25-53] guest_home[55-56] guest_body[57-71] release_step[71-72] release_step[72-73] release_step[73-73]
- run 49 (81.6 ms): artifacts[1-5] walk[5-26] zip[26-66] guest_home[67-67] guest_body[68-82] release_step[82-83] release_step[83-83] release_step[83-83]

## fix-*.json and fix2-*.json: each fix toggled against its own baseline in one window

| fix | baseline: 8 in sequence / on 8 threads (ms), speedup | fixed: the same | bare in that window | load |
|---|---|---|---|---|
| data_scandir (fix-data_scandir.json) | 272.9 / 144.9, 1.88 | 185.8 / 97.7, 1.9 | 117.5 / 41.0, 2.86 | 37 |
| no_data_check, no_walk_judge, no_private, no_identity_check, no_stack_lock, no_ticker (fix-no_data_check,no_walk_judge,no_private,no_identity_check,no_stack_lock,no_ticker.json) | 398.3 / 270.2, 1.47 | 260.2 / 106.8, 2.44 | 150.2 / 57.0, 2.64 | 31 |
| no_data_check, no_walk_judge (fix-no_data_check,no_walk_judge.json) | 216.1 / 137.2, 1.58 | 159.8 / 61.8, 2.58 | 203.8 / 74.4, 2.74 | 30 |
| no_data_check (fix-no_data_check.json) | 159.9 / 83.7, 1.91 | 132.1 / 72.1, 1.83 | 107.1 / 25.9, 4.13 | 11 |
| no_identity_check (fix-no_identity_check.json) | 158.9 / 86.7, 1.83 | 151.1 / 90.9, 1.66 | 109.0 / 28.3, 3.85 | 11 |
| no_private (fix-no_private.json) | 155.8 / 85.2, 1.83 | 148.2 / 89.7, 1.65 | 96.4 / 24.5, 3.94 | 11 |
| no_stack_lock (fix-no_stack_lock.json) | 149.6 / 79.7, 1.88 | 149.3 / 82.4, 1.81 | 100.6 / 26.4, 3.81 | 11 |
| no_ticker (fix-no_ticker.json) | 153.4 / 88.1, 1.74 | 151.2 / 83.6, 1.81 | 97.7 / 28.3, 3.45 | 11 |
| no_walk_judge (fix-no_walk_judge.json) | 157.4 / 82.8, 1.9 | 143.7 / 62.5, 2.3 | 106.6 / 27.1, 3.93 | 10 |
| switch_fast (fix-switch_fast.json) | 175.8 / 111.2, 1.58 | 176.9 / 101.1, 1.75 | 117.4 / 42.8, 2.74 | 44 |
| switch_slow (fix-switch_slow.json) | 162.6 / 82.6, 1.97 | 155.5 / 80.3, 1.94 | 102.2 / 23.4, 4.37 | 44 |
| zip_outside, data_scandir (fix-zip_outside,data_scandir.json) | 166.1 / 95.3, 1.74 | 148.4 / 127.1, 1.17 | 101.0 / 28.4, 3.56 | 11 |
| zip_outside (fix-zip_outside.json) | 225.6 / 130.4, 1.73 | 259.9 / 161.4, 1.61 | 140.6 / 42.9, 3.28 | 41 |
| data_scandir (fix2-data_scandir.json) | 148.0 / 97.9, 1.51 | 142.5 / 70.7, 2.02 | 94.2 / 29.4, 3.21 | 17 |
| no_data_check, no_walk_judge (fix2-no_data_check,no_walk_judge.json) | 147.2 / 77.4, 1.9 | 115.3 / 46.2, 2.5 | 93.8 / 23.9, 3.92 | 17 |
| no_stack_lock, no_ticker (fix2-no_stack_lock,no_ticker.json) | 144.8 / 76.8, 1.89 | 144.2 / 79.7, 1.81 | 96.4 / 23.3, 4.14 | 16 |
| zip_outside (fix2-zip_outside.json) | 148.9 / 82.1, 1.81 | 147.0 / 103.7, 1.42 | 96.4 / 22.8, 4.23 | 17 |

## hostonly.json (load average 21): the host-side steps alone, no guest

| step | per call ms | 8 in sequence ms | 8 on 8 threads ms | parallel / sequence |
|---|---|---|---|---|
| data_intact (os.walk+pathlib, under zip_lock in the product) @switch=0.005 | 2.901 | 23.21 | 41.8 | 1.8 |
| data_intact by scandir @switch=0.005 | 1.082 | 8.66 | 14.49 | 1.67 |
| zip_folder (the lock + the check) @switch=0.005 | 2.559 | 20.47 | 33.17 | 1.62 |
| walk_grants @switch=0.005 | 1.321 | 10.57 | 25.25 | 2.39 |
| found_and_checked @switch=0.005 | 0.226 | 1.81 | 4.92 | 2.72 |
| Private make+remove @switch=0.005 | 0.629 | 5.03 | 3.21 | 0.64 |
| data_intact (os.walk+pathlib, under zip_lock in the product) @switch=0.0001 | 2.348 | 18.79 | 58.11 | 3.09 |
| data_intact by scandir @switch=0.0001 | 1.097 | 8.78 | 16.89 | 1.92 |
| zip_folder (the lock + the check) @switch=0.0001 | 2.597 | 20.77 | 30.78 | 1.48 |
| walk_grants @switch=0.0001 | 1.51 | 12.08 | 25.99 | 2.15 |
| found_and_checked @switch=0.0001 | 0.343 | 2.74 | 7.47 | 2.72 |
| Private make+remove @switch=0.0001 | 0.368 | 2.94 | 4.88 | 1.66 |

A pure bytecode loop of about the same length: 8 in sequence 10.4 ms, on 8 threads 13.25 ms.

## ops.json: os-level calls per call, counted by wrapping the os module's functions

- product: 707.0 per call: {'lstat': 458.0, 'stat': 125.0, 'open': 30.0, 'fstat': 30.0, 'close': 30.0, 'scandir': 13.0, 'readlink': 5.0, 'mkdir': 3.0, 'getcwd': 3.0, 'unlink': 3.0, 'lseek': 2.0, 'write': 2.0, 'rmdir': 2.0, 'walk': 1.0}
- bare: 5.0 per call: {'stat': 3.0, 'mkdir': 2.0}
- product_with_scandir_check: 484.0 per call: {'lstat': 236.0, 'stat': 125.0, 'open': 30.0, 'fstat': 30.0, 'close': 30.0, 'scandir': 13.0, 'readlink': 5.0, 'mkdir': 3.0, 'getcwd': 3.0, 'unlink': 3.0, 'lseek': 2.0, 'write': 2.0, 'rmdir': 2.0}

## walk.json: the grants walk alone, and with a per-call memo of ancestor identities

- walk as is: {'per_call_ms': 1.177, 'par8_ms': 31.79, 'ops_per_call': 289.0, 'lstat': 169.0, 'stat': 117.0}
- walk with the identity memo: {'per_call_ms': 1.095, 'par8_ms': 24.68, 'ops_per_call': 214.0, 'lstat': 169.0, 'stat': 42.0}
