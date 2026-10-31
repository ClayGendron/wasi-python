# 164: Output while the guest runs, and stdin for a turn

## Changelog

### New

- **See a guest's output while it runs.** `run`, `run_async` and a session's turns take `on_output`, called with each chunk of stdout and stderr as it arrives; `OutputFeed` iterates them from async code. On the command line, `--stream` prints a JSON line per chunk. [Read output while the guest runs](https://claygendron.github.io/wasi-python/how-to/output-while-it-runs/)
- **Keep the end of a long output.** `output_keep="tail"` keeps a stream's last bytes past `output_bytes`, after a line counting what was cut, so the traceback at the end is kept; `--output-keep tail` on the command line. [Keep the end of a long output](https://claygendron.github.io/wasi-python/how-to/output-while-it-runs/#keep-the-end-of-a-long-output)
- **Answer a turn's `input()`.** `Session.run` and `Session.run_async` take `stdin`, that turn's standard input, which `sys.stdin` and `input()` read. [Give a turn its standard input](https://claygendron.github.io/wasi-python/how-to/output-while-it-runs/#give-a-turn-its-standard-input)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "164"
new = ["tests/unit/test_runner_streaming.py", "tests/unit/test_home.py"]
units = 30
grows = [
  "tests/checks/test_v1_1_artifact_set.py::test_binary_is_a_core_wasm_module[plain]",
  "tests/checks/test_v1_1_artifact_set.py::test_binary_is_a_core_wasm_module[snapshot]",
  "tests/checks/test_v1_1_artifact_set.py::test_regex_is_builtin_at_manifest_version[plain]",
  "tests/checks/test_v1_1_artifact_set.py::test_stdlib_c_modules_are_builtin[plain]",
  "tests/checks/test_v1_1_artifact_set.py::test_stdlib_c_modules_are_builtin[snapshot]",
  "tests/checks/test_v1_2_hostile_guest.py::test_dup_is_refused_as_not_supported[plain]",
  "tests/checks/test_v1_2_hostile_guest.py::test_dup_is_refused_as_not_supported[snapshot]",
  "tests/checks/test_v1_2_hostile_guest.py::test_extra_preopens_work_on_the_snapshot[data first]",
  "tests/checks/test_v1_2_hostile_guest.py::test_extra_preopens_work_on_the_snapshot[root first]",
  "tests/checks/test_v1_2_hostile_guest.py::test_recursion_through_python_raises[cmp-to-key-snapshot]",
  "tests/checks/test_v1_2_hostile_guest.py::test_recursion_through_python_raises[format-snapshot]",
  "tests/checks/test_v1_2_hostile_guest.py::test_recursion_through_python_raises[getattr-snapshot]",
  "tests/checks/test_v1_2_hostile_guest.py::test_recursion_through_python_raises[lru-cache-snapshot]",
  "tests/checks/test_v1_2_hostile_guest.py::test_recursion_through_python_raises[min-key-snapshot]",
  "tests/checks/test_v1_2_hostile_guest.py::test_recursion_through_python_raises[np-vectorize-snapshot]",
  "tests/checks/test_v1_2_hostile_guest.py::test_recursion_through_python_raises[pd-map-snapshot]",
  "tests/checks/test_v1_2_hostile_guest.py::test_recursion_through_python_raises[pickle-partial-plain]",
  "tests/checks/test_v1_2_hostile_guest.py::test_recursion_through_python_raises[pickle-partial-snapshot]",
  "tests/checks/test_v1_2_hostile_guest.py::test_recursion_through_python_raises[pickle-reduce-snapshot]",
  "tests/checks/test_v1_2_hostile_guest.py::test_recursion_through_python_raises[reduce-snapshot]",
  "tests/checks/test_v1_2_hostile_guest.py::test_recursion_through_python_raises[repr-plain]",
  "tests/checks/test_v1_2_hostile_guest.py::test_recursion_through_python_raises[setrecursionlimit-plain]",
  "tests/checks/test_v1_2_hostile_guest.py::test_recursion_through_python_raises[sorted-key-snapshot]",
  "tests/checks/test_v1_2_hostile_guest.py::test_recursion_through_python_raises[str-snapshot]",
  "tests/checks/test_v1_2_hostile_guest.py::test_the_string_hash_is_siphash13[plain]",
  "tests/checks/test_v1_2_hostile_guest.py::test_the_string_hash_is_siphash13[snapshot]",
  "tests/checks/test_v1_2_portable_and_sealed.py::test_guest_has_no_network",
  "tests/checks/test_v1_2_portable_and_sealed.py::test_guest_runs_here[plain]",
  "tests/checks/test_v1_2_portable_and_sealed.py::test_guest_sees_only_its_root",
  "tests/checks/test_v1_3_data_stack.py::test_a_singular_matrix_raises_linalgerror[plain]",
  "tests/checks/test_v1_3_data_stack.py::test_a_singular_matrix_raises_linalgerror[snapshot]",
  "tests/checks/test_v1_3_data_stack.py::test_gzip_round_trips",
  "tests/checks/test_v1_3_data_stack.py::test_hardware_floating_point_signals_stay_silent_as_documented[snapshot]",
  "tests/checks/test_v1_3_data_stack.py::test_longdouble_parses",
  "tests/checks/test_v1_3_data_stack.py::test_npy_files_round_trip[plain]",
  "tests/checks/test_v1_3_data_stack.py::test_numpy_and_pandas_are_builtin_at_manifest_versions[plain]",
  "tests/checks/test_v1_3_data_stack.py::test_numpy_and_pandas_are_builtin_at_manifest_versions[snapshot]",
  "tests/checks/test_v1_3_data_stack.py::test_numpy_is_built_on_the_sets_openblas[plain]",
  "tests/checks/test_v1_3_data_stack.py::test_numpy_linalg_errors_are_native_numpy_on_openblas[snapshot]",
  "tests/checks/test_v1_3_data_stack.py::test_numpys_own_floating_point_signals_reach_errstate[snapshot]",
  "tests/checks/test_v1_3_data_stack.py::test_packages_carry_their_metadata[plain]",
  "tests/checks/test_v1_3_data_stack.py::test_random_matches_native",
  "tests/checks/test_v1_3_data_stack.py::test_sqlite_job_matches_native",
  "tests/checks/test_v1_3_data_stack.py::test_stdlib_debugging_tools_import",
  "tests/checks/test_v1_3_data_stack.py::test_the_snapshot_pre_imports_no_package",
  "tests/checks/test_v1_3_default_profile.py::test_formula_engines_run_pure[plain]",
  "tests/checks/test_v1_3_default_profile.py::test_machine_learning_job_matches_native[snapshot]",
  "tests/checks/test_v1_3_default_profile.py::test_scikit_learn_reads_its_files_from_the_zip[plain]",
  "tests/checks/test_v1_3_default_profile.py::test_statsmodels_reads_its_datasets_from_the_zip[snapshot]",
  "tests/checks/test_v1_3_default_profile.py::test_the_default_profile_runs_its_pure_python_paths[plain]",
  "tests/checks/test_v1_3_default_profile.py::test_threadpoolctl_finds_no_native_pools[plain]",
  "tests/checks/test_v1_3_lxml.py::test_files_by_path_in_grants[plain]",
  "tests/checks/test_v1_3_lxml.py::test_gb18030_is_never_silently_wrong[plain]",
  "tests/checks/test_v1_3_lxml.py::test_isoschematron_is_left_out_and_schematron_validates[plain]",
  "tests/checks/test_v1_3_lxml.py::test_libxml2_has_no_zlib[plain]",
  "tests/checks/test_v1_3_lxml.py::test_lxml_xml_job_matches_native",
  "tests/checks/test_v1_3_lxml.py::test_read_html_uses_lxml_by_default[plain]",
  "tests/checks/test_v1_3_lxml.py::test_stylesheets_and_entities_reach_only_grants[snapshot]",
  "tests/checks/test_v1_3_matplotlib.py::test_a_cycle_through_kiwisolver_objects_is_collected[snapshot]",
  "tests/checks/test_v1_3_matplotlib.py::test_kiwisolver_raises_unsatisfiable_constraint[plain]",
  "tests/checks/test_v1_3_matplotlib.py::test_kiwisolver_raises_unsatisfiable_constraint[snapshot]",
  "tests/checks/test_v1_3_matplotlib.py::test_plot_contour_job_matches_native[plain]",
  "tests/checks/test_v1_3_regex.py::test_regex_features_job_matches_native[plain]",
  "tests/checks/test_v1_3_regex.py::test_the_five_patched_callbacks_answer[plain]",
  "tests/checks/test_v1_3_scipy.py::test_ndarray_ctypes_gives_the_arrays_address[plain]",
  "tests/checks/test_v1_3_scipy.py::test_ndarray_ctypes_gives_the_arrays_address[snapshot]",
  "tests/checks/test_v1_3_scipy.py::test_scipy_edges_job_matches_native[plain]",
  "tests/checks/test_v1_3_scipy.py::test_scipy_numeric_job_matches_native[snapshot]",
  "tests/checks/test_v1_3_scipy.py::test_scipy_odr_is_left_out_by_name[plain]",
  "tests/checks/test_v1_3_scipy.py::test_scipy_odr_is_left_out_by_name[snapshot]",
  "tests/checks/test_v1_3_scipy.py::test_scipy_solvers_job_matches_native[snapshot]",
  "tests/checks/test_v1_3_scipy.py::test_sobol_needs_nothing_writable[snapshot]",
  "tests/checks/test_v1_3_the_zips_directory.py::test_the_fast_reader_builds_zipimports_dict[prepended]",
  "tests/checks/test_v1_3_the_zips_directory.py::test_the_fast_reader_builds_zipimports_dict[zip64]",
  "tests/checks/test_v1_3_the_zips_directory.py::test_the_zip_reader_is_ours_from_the_first_import[plain]",
  "tests/checks/test_v1_3_upstream_suites.py::test_upstream_suite[cpython-fs]",
  "tests/checks/test_v1_4_embedding.py::test_a_file_dropped_into_a_stage_changes_nothing[plain]",
  "tests/checks/test_v1_4_embedding.py::test_a_forged_frame_is_validated_first",
  "tests/checks/test_v1_4_embedding.py::test_a_program_sees_real_entropy_and_file_metadata[plain]",
  "tests/checks/test_v1_4_embedding.py::test_door_round_trips_bytes_through_a_host[plain]",
  "tests/checks/test_v1_4_embedding.py::test_door_round_trips_bytes_through_a_host[snapshot]",
  "tests/checks/test_v1_4_embedding.py::test_door_without_a_host_says_so[plain]",
  "tests/checks/test_v1_4_embedding.py::test_door_without_a_host_says_so[snapshot]",
  "tests/checks/test_v1_4_embedding.py::test_exit_status_is_a_process_status[plain]",
  "tests/checks/test_v1_4_embedding.py::test_file_facts_cost_the_same_on_every_run[plain]",
  "tests/checks/test_v1_4_embedding.py::test_file_facts_cost_the_same_on_every_run[snapshot]",
  "tests/checks/test_v1_4_embedding.py::test_fuel_does_not_follow_the_stdlib_zips_link_count[plain]",
  "tests/checks/test_v1_4_embedding.py::test_fuel_does_not_follow_the_stdlib_zips_link_count[snapshot]",
  "tests/checks/test_v1_4_embedding.py::test_fuel_is_exact_across_tool_calls",
  "tests/checks/test_v1_4_embedding.py::test_main_starts_as_native[plain]",
  "tests/checks/test_v1_4_embedding.py::test_main_starts_as_native[snapshot]",
  "tests/checks/test_v1_4_embedding.py::test_run_keeps_a_file_the_stdlib_reaches[snapshot]",
  "tests/checks/test_v1_4_embedding.py::test_run_keeps_an_unclosed_files_bytes[plain]",
  "tests/checks/test_v1_4_embedding.py::test_run_reads_argv_and_environment_each_call[plain]",
  "tests/checks/test_v1_4_embedding.py::test_run_returns_the_exit_code[plain]",
  "tests/checks/test_v1_4_embedding.py::test_run_returns_the_exit_code[snapshot]",
  "tests/checks/test_v1_4_embedding.py::test_unbuffered_output_survives_a_hard_exit[plain]",
  "tests/checks/test_v1_4_embedding.py::test_uncaught_errors_print_as_native[plain]",
  "tests/checks/test_v1_4_prepare.py::test_a_hung_writer_is_flushed",
  "tests/checks/test_v1_4_prepare.py::test_a_trapped_prepare_leaves_nothing_callable",
  "tests/checks/test_v1_4_prepare.py::test_the_everything_prelude_prepares",
  "tests/checks/test_v1_4_prepare.py::test_the_makings_import_path_is_gone",
  "tests/checks/test_v1_4_starting_image.py::test_a_session_starts_from_a_snapshot",
]
growth = "the reactor carries a turn's stdin (the bootstrap reads it, the export turn_input takes it, and prepare frees a held one): the plain binary loads that bootstrap at every start and the snapshot's heap shifts, so every call's fuel moves 0.01 to 13 percent (the most, 454 to 514, a trapped prepare) and each binary grows by a few kilobytes (0.002 and 0.004 percent); the acceptance after the merge recorded them, at be87f12a"
[claim.judge]
"tests/checks/test_rules.py" = "LONG_FUNCTIONS: runner.py:run 156 to 173 and run_async 181 to 208 take on_output and output_keep with their docstrings, and run_async the feed's try and finally around its body and the late exception's holder; Session.run_async 81 to 102 takes stdin, on_output and output_keep, the same finally and holder; _sessions.py:_open_session 142 to 143 sets takes_stdin; _call.py:_instance falls 157 to 147 as _completed takes its end"
"tests/release_shards.toml" = "the two new unit files, test_runner_streaming.py and test_home.py, join the own-runner shard on all three systems, as every runner unit file is in a files shard"
"tests/public_api.txt" = "the public names OutputChunk and OutputFeed, and the keywords on_output and output_keep on run, run_async, Session.run and Session.run_async, and stdin on the two Session methods"
```
