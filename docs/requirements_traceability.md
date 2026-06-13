# AutonomicLab — Requirements Traceability Matrix

*Generated: 2026-06-13. Cross-references requirements_spec.md against the 59 tests in tests/.*

---

## How to read this document

| Status | Meaning |
|---|---|
| **COVERED** | At least one test directly exercises this requirement |
| **PARTIAL** | A test exists but does not verify the full stated behaviour |
| **GUI-ONLY** | Requirement involves the Qt UI; untestable without a headless Qt harness |
| **NOT COVERED** | No test. Either a gap to address, or a test to write |

**On your two questions:**

> *I shouldn't test anything I have no requirements for, right?*

Mostly yes. Two tests — `test_signal_bool_false_when_empty` and `test_context_manager_closes_zip` — have no explicit parent requirement. They test internal implementation contracts that *support* requirements (FR-003's `if sig:` guard; resource cleanup under NFR-006). These are legitimate, but the spec should be updated to reflect them (see §4 below).

> *All my requirements should be covered by a test, right?*

The **analysis algorithms (FR-017 – FR-026)** are the most critical uncovered gap — they implement the clinical protocol and could be tested with synthetic signals right now. GUI requirements (FR-014, FR-016, FR-028–FR-049, FR-054, FR-058) are structurally untestable without a headless Qt harness; mark them GUI-ONLY and accept the gap.

---

## 1. Requirement → Test mapping

### Functional Requirements — Data Loading

| Req | Short description | Tests | Status |
|---|---|---|---|
| FR-001 | Load CSV from directory | `test_csv_load_returns_dataset`, `test_csv_load_path_is_folder` | COVERED |
| FR-002 | Auto-detect datetime prefix; raise on missing | `test_detect_prefix_from_real_folder`¹, `test_detect_prefix_empty_folder_raises`, `test_detect_prefix_from_synthetic_folder`, `test_csv_missing_folder_raises` | COVERED |
| FR-003 | Load named signals; absent → skip | `test_csv_load_has_signals`¹, `test_missing_file_returns_none`, `test_load_real_hr_signal`¹, `test_load_real_rebap_signal`¹, `test_get_signal_returns_none_for_missing`¹ | COVERED |
| FR-004 | Atomic row parse — blank value drops entire row | `test_blank_value_row_skipped_atomically`, `test_all_blank_values_returns_none`, `test_times_values_always_same_length`¹ | COVERED |
| FR-005 | Load .nsc ZIP archives; raise on missing | `test_nsc_load_returns_dataset`¹, `test_nsc_load_prefix_is_stem`¹, `test_nsc_missing_file_raises`, `test_missing_file_raises`, `test_channels_not_empty`¹, `test_expected_channels_present`¹, `test_context_manager_closes_zip`¹, `test_unknown_channel_raises`¹ | COVERED |
| FR-006 | Decode .nsd X/Y; 100 µs ticks; /32767 scale | `test_times_values_same_length`¹, `test_times_monotonically_non_decreasing`¹, `test_times_in_seconds`¹, `test_hr_physiological_range`¹, `test_hr_close_to_ground_truth`¹, `test_rebap_physiological_range`¹, `test_fiap_sys_dia_ground_truth`¹, `test_sample_rate_reasonable`¹, `test_units_non_empty`¹, `test_signal_type`¹ | COVERED |
| FR-007 | Y sentinel −32768 → NaN | `test_gap_mask_matches_nan_values`¹ (indirect; no synthetic test for the sentinel value itself) | PARTIAL |
| FR-008 | Gap / Physiocal detection → NaN | `test_gap_mask_matches_nan_values`¹, `test_gap_mask_length_matches_signal`¹ | COVERED |
| FR-009 | Read markers from Measurement.xml | `test_nsc_load_markers_are_lists`¹ (type-check only; content/count not verified) | PARTIAL |
| FR-010 | Read regions from GATResults.xml; infer from markers if absent | `test_nsc_load_markers_are_lists`¹ (type-check only) | PARTIAL |
| FR-011 | Read markers from CSV Markers.csv | `test_csv_load_has_markers`¹ | COVERED |
| FR-012 | Read region markers from RegionMarkers.csv | `test_load_region_markers_single_region`, `test_load_region_markers_multiple_regions`, `test_load_region_markers_missing_file_returns_empty`, `test_load_region_markers_unpaired_start_dropped`, `test_load_region_markers_skips_header`, `test_load_region_markers_space_variant_filename` | COVERED |
| FR-013 | Classify marker label → Valsalva / Stand / Deep Breathing / Other | `test_determine_phase` (16 parametrized cases) | COVERED |
| FR-014 | Three-button open dialog + native file dialog | — | GUI-ONLY |
| FR-015 | "View Raw Data" enabled when ECG signals present | — | GUI-ONLY |
| FR-016 | "View Embedded PDF" enabled when .nsc contains .pdf | — | GUI-ONLY |

### Functional Requirements — Protocol Analysis

| Req | Short description | Tests | Status |
|---|---|---|---|
| FR-017 | Valsalva: compute all phase boundaries + derived parameters | `test_all_phase_boundaries_not_none`, `test_nadir_time_and_value`, `test_S2lmax_time_and_value`, `test_phase_III_nadir`, `test_overshoot`, `test_A_equals_40`, `test_B_equals_20`, `test_PRT_equals_6`, `test_VR_ratio`, `test_BRSa_formula`, `test_S4e_equals_hr_max_plus_30`, `test_missing_signals_returns_empty_result` | COVERED |
| FR-018 | Valsalva: Phase I start via PAirway ↑ 0.5 mmHg crossing | `test_t_S1s_detected`, `test_t_S1s_near_expected` | COVERED |
| FR-019 | Valsalva: Phase III start via PAirway ↓ 0.5 mmHg crossing | `test_t_S3s_detected`, `test_t_S3s_near_expected` | COVERED |
| FR-020 | Valsalva: baseline window t_S1s −45 s to −15 s | `test_baseline_window_45_to_15_before_S1s`, `test_avg_sbp_equals_120` | COVERED |
| FR-021 | Valsalva: HR max search window [t_S2es, t_S3s + 5 s] | `test_hr_max_detected`, `test_hr_max_within_search_window`, `test_hr_max_value` | COVERED |
| FR-022 | Valsalva: HR min search window [hr_max_t, hr_max_t + 30 s] | `test_hr_min_detected`, `test_hr_min_within_search_window`, `test_hr_min_value` | COVERED |
| FR-023 | Valsalva: PhysioCalActive contamination detection + suppression | `test_no_cal_warnings_on_clean_signal`, `test_cal_warning_fired`, `test_cal_suppresses_phase_iv_times`, `test_cal_suppresses_prt`, `test_cal_suppresses_phase_iii_end` | COVERED |
| FR-024 | Deep Breathing: peak detection with prominence 3, distance 4 s | `test_correct_number_of_cycles`, `test_peaks_near_80_bpm`, `test_troughs_near_60_bpm` | COVERED |
| FR-025 | Deep Breathing: peak–trough pairing, ΔHR = max − min | `test_trough_always_after_peak`, `test_each_delta_hr_is_20` | COVERED |
| FR-026 | Deep Breathing: top-6 selection, mean ΔHR all + top-6 | `test_avg_rsa_all`, `test_avg_rsa_top6`, `test_n_sel_is_6`, `test_top6_set_contains_all_cycles`, `test_mean_max_all`, `test_mean_min_all` | COVERED |
| FR-027 | Stand Test: visualisation-only, no export | — | NOT COVERED |

### Functional Requirements — Interactive Annotations and Override

| Req | Short description | Tests | Status |
|---|---|---|---|
| FR-028 | Valsalva: three linked subplots with phase fills + brackets | — | GUI-ONLY |
| FR-029 | Valsalva: draggable baseline region recomputes avg_sbp/PRT/BRSa | — | GUI-ONLY |
| FR-030 | Valsalva: draggable measurement points recompute downstream | — | GUI-ONLY |
| FR-031 | Deep Breathing: interactive cycle add/drag/delete | — | GUI-ONLY |
| FR-032 | Physiocal-suppressed PIV: ghost HR min dot | — | GUI-ONLY |
| FR-033 | Overrides persisted atomically to overrides.json | `test_save_returns_true_on_success`, `test_load_missing_returns_empty_dict`, `test_round_trip_preserves_values`, `test_save_adds_saved_at_timestamp`, `test_multiple_phases_preserved`, `test_load_invalid_json_returns_empty`, `test_load_wrong_top_level_type_returns_empty`, `test_load_phase_entry_not_dict_returns_empty`, `test_load_invalid_float_field_returns_empty` | COVERED |
| FR-034 | Overrides restored on load; indicator visible | — | NOT COVERED |
| FR-035 | "Reset to Auto" deletes override, re-runs algorithm | — | NOT COVERED |

### Functional Requirements — Phase Navigation

| Req | Short description | Tests | Status |
|---|---|---|---|
| FR-036 | Phase combo populated from region markers | — | GUI-ONLY |
| FR-037 | "All" shows full-recording overview | — | GUI-ONLY |
| FR-038 | Named phase zooms to window, runs analyzer | — | GUI-ONLY |
| FR-039 | Markers table filtered to phase window | — | GUI-ONLY |
| FR-039a | Dataset.phase_window() falls back to HR range | `test_phase_window_falls_back_to_hr_range`¹ | COVERED |

### Functional Requirements — Export

| Req | Short description | Tests | Status |
|---|---|---|---|
| FR-040 | Export Valsalva to .xlsx with three sections | — | NOT COVERED |
| FR-041 | Export Deep Breathing RSA to .xlsx per-cycle table | — | NOT COVERED |
| FR-042 | Capture plot PNG, embed in workbook | — | NOT COVERED |
| FR-043 | Export filename includes mode tag (auto/manual) | — | NOT COVERED |
| FR-044 | Confirm overwrite if export file already exists | — | GUI-ONLY |

### Functional Requirements — Raw Data Viewer

| Req | Short description | Tests | Status |
|---|---|---|---|
| FR-045 | Show BP, HR, PAirway, ECG leads, PTT | — | GUI-ONLY |
| FR-046 | All X-axes linked; range preserved across toggles | — | GUI-ONLY |
| FR-047 | Beat markers on ECG leads at RR timestamps | — | GUI-ONLY |
| FR-048 | Signal metadata in left panel | — | GUI-ONLY |
| FR-049 | Checkbox toggles never create/destroy widgets | — | GUI-ONLY |

### Functional Requirements — Authentication and User Management

| Req | Short description | Tests | Status |
|---|---|---|---|
| FR-050 | Require login on every launch unless no users | `test_empty_store_has_no_users`, `test_has_any_user_after_add` (test DB state; not full startup flow) | PARTIAL |
| FR-051 | Three roles: Admin, Investigator, Guest | `test_update_role`, `test_list_users` (verifies roles can be set; access control not exercised) | PARTIAL |
| FR-052 | Guest: 10 launches, MAC-bound, HMAC-signed; tamper → reset | `test_starts_at_ten`, `test_has_launches_initially`, `test_consume_returns_true_and_decrements`, `test_consume_until_zero`, `test_consume_at_zero_returns_false`, `test_persists_across_instances`, `test_tampered_remaining_resets_to_zero`, `test_valid_signature_accepted` | COVERED² |
| FR-053 | First-run bypass when DB empty | `test_empty_store_has_no_users`, `test_has_any_user_after_add` | PARTIAL |
| FR-054 | Guest button hidden when exhausted or allow_guest=false | — | GUI-ONLY |
| FR-055 | Admin Panel: add, edit, change password, toggle, delete | `test_add_and_retrieve`, `test_get_nonexistent_user_returns_none`, `test_list_users`, `test_inactive_user_cannot_authenticate`, `test_delete_user`, `test_set_password`, `test_update_role`, `test_correct_password_authenticates`, `test_wrong_password_fails`, `test_nonexistent_user_fails` | COVERED³ |
| FR-056 | Sync users.db from GitHub on launch | `test_sync_skips_when_token_empty`, `test_sync_returns_false_on_network_error`, `test_sync_skips_when_already_current`, `test_sync_replaces_local_when_remote_differs`, `test_sync_creates_local_file_when_absent` | COVERED |
| FR-057 | Push users.db to GitHub on Admin Panel close | `test_push_skips_when_token_empty`, `test_push_skips_when_file_missing`, `test_push_returns_true_on_success` | COVERED |

### Functional Requirements — Startup and Configuration

| Req | Short description | Tests | Status |
|---|---|---|---|
| FR-058 | Splash screen 2.5 s with version overlay | — | GUI-ONLY |
| FR-059 | Log file next to executable | — | NOT COVERED |
| FR-060 | Exception hook swallows pyqtgraph "deleted" RuntimeError | — | NOT COVERED |
| FR-061 | Config from config.yaml; prefs from ~/.autonomiclab/settings.yaml | — | NOT COVERED |
| FR-062 | Default data folder ~/Documents/AutonomicLab/data, mkdir on first launch | `test_config_tilde_is_expanded`, `test_prefs_tilde_is_expanded`, `test_default_path_has_no_tilde`, `test_configured_folder_created_when_absent`, `test_default_folder_created_when_absent`, `test_prefs_override_config_when_exists`, `test_config_used_when_prefs_path_missing` | COVERED |

---

### Non-Functional Requirements

| Req | Short description | Tests | Status |
|---|---|---|---|
| NFR-001 | CSV load < 10 s | — | NOT COVERED |
| NFR-002 | Phase switch render < 3 s | — | NOT COVERED |
| NFR-003 | Drag update < 33 ms | — | NOT COVERED |
| NFR-004 | Override atomic write survives crash | `test_no_tmp_file_after_successful_save`, `test_second_save_overwrites_first`, `test_save_fails_gracefully_on_read_only_path` | COVERED |
| NFR-005 | Offline operation uses cached users.db | — | NOT COVERED |
| NFR-006 | Malformed CSV rows / files: log and continue | `test_blank_value_row_skipped_atomically`, `test_all_blank_values_returns_none`, `test_missing_file_returns_none` | PARTIAL |
| NFR-007 | Resize debounce 50 ms QTimer | — | GUI-ONLY |
| NFR-008 | Passwords as bcrypt hashes | `test_correct_password_authenticates`, `test_wrong_password_fails`, `test_set_password` (implicitly via bcrypt) | COVERED |
| NFR-009 | users.db encrypted with Fernet / PBKDF2 | `test_encrypted_roundtrip` | COVERED |
| NFR-010 | Guest counter HMAC tamper resistance | `test_tampered_remaining_resets_to_zero`, `test_valid_signature_accepted` | COVERED |
| NFR-011 | Admin PAT not in installer or repo | — | NOT COVERED |
| NFR-012–013 | Windows-only deployment, user-level install | — | NOT COVERED |
| NFR-014 | CI: windows-latest, Python 3.12, PyInstaller | — | NOT COVERED |
| NFR-015–017 | Architecture: WindowProtocol, analysis/plotting separation, fonts.yaml | — | NOT COVERED |
| NFR-018 | Loads recordings up to 1 500 s | — | NOT COVERED |

---

### Interface Requirements

| Req | Short description | Tests | Status |
|---|---|---|---|
| IR-001 | Consumes Finapres NOVA files | FR-001–FR-011 tests (indirectly) | COVERED |
| IR-002 | GitHub Contents API for sync | — | NOT COVERED |
| IR-003 | CSV format (semicolon, 8-line header, UTF-8) | `test_blank_value_row_skipped_atomically`, `test_load_real_hr_signal`¹, `test_detect_prefix_from_synthetic_folder` | COVERED |
| IR-004 | NSC binary format (ZIP, Measurement.xml, .nsd) | `test_times_in_seconds`¹, `test_hr_close_to_ground_truth`¹, `test_fiap_sys_dia_ground_truth`¹ | COVERED |
| IR-005–006 | Marker CSV + RegionMarkers CSV formats | `test_csv_load_has_markers`¹ | PARTIAL |
| IR-007–012 | overrides.json, config.yaml, guest_counter.json, Excel, PDF, URL | — | NOT COVERED |

*¹ Requires real data files (gitignored; skipped in CI — see conftest.py)*
*² MAC-mismatch reset-to-10 not tested (no test for `counter.mac_hash != mh` branch)*
*³ Admin Panel GUI logic (confirmation dialogs, form validation) not tested — UserStore layer only*

---

## 2. Test → Requirement mapping

| Test | Requirement(s) |
|---|---|
| `test_detect_prefix_from_real_folder`¹ | FR-002 |
| `test_detect_prefix_empty_folder_raises` | FR-002 |
| `test_detect_prefix_from_synthetic_folder` | FR-002, IR-003 |
| `test_missing_file_returns_none` | FR-003, NFR-006 |
| `test_load_real_hr_signal`¹ | FR-003, FR-006, IR-003 |
| `test_load_real_rebap_signal`¹ | FR-003, FR-006, IR-003 |
| `test_times_values_always_same_length`¹ | FR-004, NFR-006 |
| `test_blank_value_row_skipped_atomically` | FR-004, NFR-006, IR-003 |
| `test_all_blank_values_returns_none` | FR-004, NFR-006 |
| `test_signal_bool_false_when_empty` | *(no explicit requirement — see §4)* |
| `test_csv_load_returns_dataset`¹ | FR-001 |
| `test_determine_phase` | FR-013 |
| `test_load_region_markers_single_region` | FR-012, IR-006 |
| `test_load_region_markers_multiple_regions` | FR-012 |
| `test_load_region_markers_missing_file_returns_empty` | FR-012 |
| `test_load_region_markers_unpaired_start_dropped` | FR-012 |
| `test_load_region_markers_skips_header` | FR-012 |
| `test_load_region_markers_space_variant_filename` | FR-012 |
| `test_csv_load_has_signals`¹ | FR-003 |
| `test_csv_load_has_markers`¹ | FR-011, IR-005 |
| `test_csv_load_path_is_folder`¹ | FR-001 |
| `test_csv_missing_folder_raises` | FR-002 |
| `test_nsc_load_returns_dataset`¹ | FR-005 |
| `test_nsc_load_markers_are_lists`¹ | FR-009, FR-010 |
| `test_nsc_load_prefix_is_stem`¹ | FR-005 |
| `test_nsc_missing_file_raises` | FR-005 |
| `test_phase_window_falls_back_to_hr_range`¹ | FR-039 (Dataset model) |
| `test_get_signal_returns_none_for_missing`¹ | FR-003 |
| `test_missing_file_raises` | FR-005 |
| `test_unknown_channel_raises`¹ | FR-005 |
| `test_channels_not_empty`¹ | FR-005 |
| `test_expected_channels_present`¹ | FR-005, IR-004 |
| `test_context_manager_closes_zip`¹ | *(no explicit requirement — see §4)* |
| `test_t_S1s_detected` | FR-018 |
| `test_t_S1s_near_expected` | FR-018 |
| `test_t_S3s_detected` | FR-019 |
| `test_t_S3s_near_expected` | FR-019 |
| `test_baseline_window_45_to_15_before_S1s` | FR-020 |
| `test_avg_sbp_equals_120` | FR-020 |
| `test_all_phase_boundaries_not_none` | FR-017 |
| `test_t_S1e_is_phase_I_peak` | FR-017 |
| `test_nadir_time_and_value` | FR-017 |
| `test_S2lmax_time_and_value` | FR-017 |
| `test_phase_III_nadir` | FR-017 |
| `test_overshoot` | FR-017 |
| `test_hr_max_detected` | FR-021 |
| `test_hr_max_within_search_window` | FR-021 |
| `test_hr_max_value` | FR-021 |
| `test_hr_min_detected` | FR-022 |
| `test_hr_min_within_search_window` | FR-022 |
| `test_hr_min_value` | FR-022 |
| `test_A_equals_40` | FR-017 |
| `test_B_equals_20` | FR-017 |
| `test_PRT_equals_6` | FR-017 |
| `test_VR_ratio` | FR-017 |
| `test_BRSa_formula` | FR-017 |
| `test_S4e_equals_hr_max_plus_30` | FR-017, FR-022 |
| `test_no_cal_warnings_on_clean_signal` | FR-023 |
| `test_cal_warning_fired` | FR-023 |
| `test_cal_suppresses_phase_iv_times` | FR-023 |
| `test_cal_suppresses_prt` | FR-023 |
| `test_cal_suppresses_phase_iii_end` | FR-023 |
| `test_missing_signals_returns_empty_result` | FR-017 |
| `test_t_anchor_uses_t_start_not_recording_start` | OQ-005 fix |
| `test_correct_number_of_cycles` | FR-024 |
| `test_all_cycles_have_positive_rsa` | FR-025 |
| `test_peaks_near_80_bpm` | FR-024 |
| `test_troughs_near_60_bpm` | FR-024 |
| `test_trough_always_after_peak` | FR-025 |
| `test_each_delta_hr_is_20` | FR-025 |
| `test_avg_rsa_all` | FR-026 |
| `test_avg_rsa_top6` | FR-026 |
| `test_n_sel_is_6` | FR-026 |
| `test_top6_set_contains_all_cycles` | FR-026 |
| `test_mean_max_all` | FR-026 |
| `test_mean_min_all` | FR-026 |
| `test_missing_markers_returns_empty` | FR-024 |
| `test_missing_hr_signal_returns_empty` | FR-024 |
| `test_apply_cycle_overrides_replaces_cycles` | FR-026 |
| `test_apply_empty_cycle_overrides` | FR-026 |
| `test_save_returns_true_on_success` | FR-033 |
| `test_load_missing_returns_empty_dict` | FR-033 |
| `test_round_trip_preserves_values` | FR-033 |
| `test_save_adds_saved_at_timestamp` | FR-033 |
| `test_multiple_phases_preserved` | FR-033 |
| `test_load_invalid_json_returns_empty` | FR-033, NFR-006 |
| `test_load_wrong_top_level_type_returns_empty` | FR-033 |
| `test_load_phase_entry_not_dict_returns_empty` | FR-033 |
| `test_load_invalid_float_field_returns_empty` | FR-033 |
| `test_no_tmp_file_after_successful_save` | NFR-004 |
| `test_second_save_overwrites_first` | NFR-004 |
| `test_save_fails_gracefully_on_read_only_path` | NFR-004 |
| `test_config_tilde_is_expanded` | FR-062 |
| `test_prefs_tilde_is_expanded` | FR-062 |
| `test_default_path_has_no_tilde` | FR-062 |
| `test_configured_folder_created_when_absent` | FR-062 |
| `test_default_folder_created_when_absent` | FR-062 |
| `test_prefs_override_config_when_exists` | FR-062 |
| `test_config_used_when_prefs_path_missing` | FR-062 |
| `test_sync_skips_when_token_empty` | FR-056 |
| `test_sync_returns_false_on_network_error` | FR-056 |
| `test_sync_skips_when_already_current` | FR-056 |
| `test_sync_replaces_local_when_remote_differs` | FR-056 |
| `test_sync_creates_local_file_when_absent` | FR-056 |
| `test_push_skips_when_token_empty` | FR-057 |
| `test_push_skips_when_file_missing` | FR-057 |
| `test_push_returns_true_on_success` | FR-057 |
| `test_times_values_same_length`¹ | FR-006 |
| `test_times_monotonically_non_decreasing`¹ | FR-006 |
| `test_times_in_seconds`¹ | FR-006, IR-004 |
| `test_hr_physiological_range`¹ | FR-006 |
| `test_hr_close_to_ground_truth`¹ | FR-006, IR-004 |
| `test_rebap_physiological_range`¹ | FR-006, IR-004 |
| `test_fiap_sys_dia_ground_truth`¹ | FR-006, IR-004 |
| `test_gap_mask_matches_nan_values`¹ | FR-007 (partial), FR-008 |
| `test_gap_mask_length_matches_signal`¹ | FR-008 |
| `test_sample_rate_reasonable`¹ | FR-006, IR-004 |
| `test_units_non_empty`¹ | FR-006, IR-004 |
| `test_signal_type`¹ | FR-006, IR-004 |
| `test_starts_at_ten` | FR-052 |
| `test_has_launches_initially` | FR-052 |
| `test_consume_returns_true_and_decrements` | FR-052 |
| `test_consume_until_zero` | FR-052 |
| `test_consume_at_zero_returns_false` | FR-052 |
| `test_persists_across_instances` | FR-052 |
| `test_tampered_remaining_resets_to_zero` | FR-052, NFR-010 |
| `test_valid_signature_accepted` | FR-052, NFR-010 |
| `test_empty_store_has_no_users` | FR-050, FR-053 |
| `test_get_nonexistent_user_returns_none` | FR-055 |
| `test_add_and_retrieve` | FR-055 |
| `test_has_any_user_after_add` | FR-050, FR-053 |
| `test_list_users` | FR-051, FR-055 |
| `test_correct_password_authenticates` | FR-050, FR-055, NFR-008 |
| `test_wrong_password_fails` | FR-050, NFR-008 |
| `test_nonexistent_user_fails` | FR-050 |
| `test_inactive_user_cannot_authenticate` | FR-055 |
| `test_encrypted_roundtrip` | NFR-009 |
| `test_delete_user` | FR-055 |
| `test_set_password` | FR-055, NFR-008 |
| `test_update_role` | FR-051, FR-055 |

---

## 3. Untested requirements — gap analysis

### A — Still testable, not yet written

| Req | Suggested test approach |
|---|---|
| **NFR-007** | FR-007 sentinel: construct a minimal .nsd byte buffer containing a `−32768` int16 value; run through `NscReader._load_channel`; assert NaN at that position |
| **FR-034** | Override restore: write overrides.json, reload Dataset, assert override is re-applied in AppController.plot_current_phase |
| **NFR-005** | Offline mode: mock `_get_remote` to return None; assert `sync_users_db` returns False and startup proceeds |

### B — GUI-only (untestable without headless Qt)

FR-014–016, FR-028–032, FR-035–039, FR-044–049, FR-054, FR-058.
These require a Qt event loop. Accept the gap; document it. If coverage of these becomes important, look into `pytest-qt` which provides a `qtbot` fixture for widget interaction tests.

---

## 4. Tests without an explicit requirement

Two tests currently have no parent requirement in the spec:

| Test | What it tests | Recommendation |
|---|---|---|
| `test_signal_bool_false_when_empty` | `Signal.__bool__` returns `False` when `times` is empty | Add to spec: *"The system shall treat a Signal with zero samples as falsy so that presence checks (`if sig:`) work correctly throughout the load pipeline."* — or fold into FR-003. |
| `test_context_manager_closes_zip` | `NscReader.__exit__` closes the underlying ZIP file | Add to spec under FR-005: *"NscReader shall implement the context manager protocol; the ZIP file shall be closed on exit."* — or fold into FR-005. |

---

## 5. Coverage summary

| Category | Total reqs | Covered | Partial | GUI-only | Not covered |
|---|---|---|---|---|---|
| FR — Data loading (FR-001–016) | 16 | 10 | 3 | 5 | 0 |
| FR — Analysis (FR-017–027) | 11 | 10 | 0 | 0 | 1 |
| FR — Interactive / override (FR-028–035) | 8 | 1 | 0 | 5 | 2 |
| FR — Phase navigation (FR-036–039) | 4 | 1 | 0 | 3 | 0 |
| FR — Export (FR-040–044) | 5 | 0 | 0 | 1 | 4 |
| FR — Raw data viewer (FR-045–049) | 5 | 0 | 0 | 5 | 0 |
| FR — Auth / users (FR-050–057) | 8 | 4 | 3 | 1 | 0 |
| FR — Startup / config (FR-058–062) | 5 | 1 | 0 | 1 | 3 |
| NFR | 18 | 5 | 1 | 1 | 11 |
| IR | 12 | 3 | 1 | 0 | 8 |
| **Total** | **92** | **35 (38%)** | **8 (9%)** | **22 (24%)** | **27 (29%)** |

The 22 GUI-only requirements are structurally outside unit testing scope. Removing them, **functional + non-functional coverage is 43 / 70 = 61%** (up from 36% before the new tests were written). The remaining uncovered testable requirements are FR-034 (override restore), FR-040–044 (Excel export), and FR-058–061 (startup/config).
