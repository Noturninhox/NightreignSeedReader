"""Parâmetros do motor de reconhecimento (derivado de nightreign-overlay-helper, AGPL-3.0)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MapDetectionSettings:
    poi_algorithm: str = "cnn"
    earth_shifting_algorithm: str = "ncc"
    fixed_map_overlay_draw_size: tuple[int, int] | None = None
    map_overlay_draw_size_ratio: float | None = 1.0
    english_text_width_percent: int = 50
    full_map_hough_circle_thres: tuple[int, ...] = (150, 200, 250)
    full_map_error_threshold: float = 20
    map_stability_change_threshold: float = 2.0
    map_stability_duration: float = 0.6
    earth_shifting_ncc_threshold: float = 0.2
    earth_shifting_error_threshold: float = 50
    subicon_template_match_threshold: float = 0.06
    poi_match_sample_ratio_w_nightlord: float = 1.0
    poi_match_sample_ratio_wo_nightlord: float = 1.0
