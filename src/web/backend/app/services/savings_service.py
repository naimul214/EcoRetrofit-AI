from dataclasses import dataclass
from statistics import median

from app.models.telemetry import CostBreakdown, SavingsSummary, TelemetryPoint
from app.services.tou_pricing import TouPeriod, TouPricingService


@dataclass(frozen=True)
class EnergyModelConfig:
    baseline_hvac_kw: float
    baseline_deadband_c: float
    min_power_factor: float
    max_power_factor: float
    fallback_interval_minutes: int


class SavingsService:
    """Converts telemetry setpoints into a proxy HVAC cost and savings estimate."""

    def __init__(self, pricing_service: TouPricingService, model_config: EnergyModelConfig) -> None:
        self._pricing_service = pricing_service
        self._config = model_config

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))

    def _estimate_ai_power_kw(self, point: TelemetryPoint) -> float:
        deadband_c = max(point.cooling_setpoint - point.heating_setpoint, 0.25)
        unbounded_factor = self._config.baseline_deadband_c / deadband_c
        bounded_factor = self._clamp(
            value=unbounded_factor,
            minimum=self._config.min_power_factor,
            maximum=self._config.max_power_factor,
        )
        return self._config.baseline_hvac_kw * bounded_factor

    def _compute_intervals_hours(self, ordered_points: list[TelemetryPoint]) -> list[float]:
        fallback_hours = max(self._config.fallback_interval_minutes / 60.0, 1.0 / 60.0)
        if not ordered_points:
            return []
        if len(ordered_points) == 1:
            return [fallback_hours]

        observed_deltas: list[float] = []
        for index in range(len(ordered_points) - 1):
            delta_hours = (
                ordered_points[index + 1].timestamp - ordered_points[index].timestamp
            ).total_seconds() / 3600.0
            if delta_hours > 0.0:
                observed_deltas.append(delta_hours)

        trailing_fallback = median(observed_deltas) if observed_deltas else fallback_hours

        intervals: list[float] = []
        for index in range(len(ordered_points) - 1):
            delta_hours = (
                ordered_points[index + 1].timestamp - ordered_points[index].timestamp
            ).total_seconds() / 3600.0
            intervals.append(delta_hours if delta_hours > 0.0 else trailing_fallback)

        intervals.append(trailing_fallback)
        return intervals

    def estimate_summary(self, points: list[TelemetryPoint]) -> SavingsSummary:
        if not points:
            empty_cost = CostBreakdown(off_peak_cad=0.0, mid_peak_cad=0.0, on_peak_cad=0.0)
            return SavingsSummary(
                point_count=0,
                estimated_ai_energy_kwh=0.0,
                estimated_baseline_energy_kwh=0.0,
                estimated_ai_cost_cad=0.0,
                estimated_baseline_cost_cad=0.0,
                estimated_savings_cad=0.0,
                estimated_savings_percent=0.0,
                cost_breakdown_ai=empty_cost,
                cost_breakdown_baseline=empty_cost,
            )

        ordered_points = sorted(points, key=lambda telemetry_point: telemetry_point.timestamp)
        intervals_hours = self._compute_intervals_hours(ordered_points)

        ai_costs: dict[TouPeriod, float] = {"off_peak": 0.0, "mid_peak": 0.0, "on_peak": 0.0}
        baseline_costs: dict[TouPeriod, float] = {"off_peak": 0.0, "mid_peak": 0.0, "on_peak": 0.0}

        total_ai_energy = 0.0
        total_baseline_energy = 0.0

        for point, interval_hours in zip(ordered_points, intervals_hours):
            effective_interval = max(interval_hours, 0.0)
            ai_power_kw = self._estimate_ai_power_kw(point)
            baseline_power_kw = self._config.baseline_hvac_kw

            ai_energy_kwh = ai_power_kw * effective_interval
            baseline_energy_kwh = baseline_power_kw * effective_interval

            period = self._pricing_service.period_for_timestamp(point.timestamp)
            rate = self._pricing_service.rate_for_period(period)

            ai_costs[period] += ai_energy_kwh * rate
            baseline_costs[period] += baseline_energy_kwh * rate

            total_ai_energy += ai_energy_kwh
            total_baseline_energy += baseline_energy_kwh

        total_ai_cost = ai_costs["off_peak"] + ai_costs["mid_peak"] + ai_costs["on_peak"]
        total_baseline_cost = (
            baseline_costs["off_peak"] + baseline_costs["mid_peak"] + baseline_costs["on_peak"]
        )
        savings_cad = total_baseline_cost - total_ai_cost
        savings_percent = (savings_cad / total_baseline_cost * 100.0) if total_baseline_cost > 0.0 else 0.0

        return SavingsSummary(
            point_count=len(ordered_points),
            estimated_ai_energy_kwh=round(total_ai_energy, 4),
            estimated_baseline_energy_kwh=round(total_baseline_energy, 4),
            estimated_ai_cost_cad=round(total_ai_cost, 4),
            estimated_baseline_cost_cad=round(total_baseline_cost, 4),
            estimated_savings_cad=round(savings_cad, 4),
            estimated_savings_percent=round(savings_percent, 2),
            cost_breakdown_ai=CostBreakdown(
                off_peak_cad=round(ai_costs["off_peak"], 4),
                mid_peak_cad=round(ai_costs["mid_peak"], 4),
                on_peak_cad=round(ai_costs["on_peak"], 4),
            ),
            cost_breakdown_baseline=CostBreakdown(
                off_peak_cad=round(baseline_costs["off_peak"], 4),
                mid_peak_cad=round(baseline_costs["mid_peak"], 4),
                on_peak_cad=round(baseline_costs["on_peak"], 4),
            ),
        )
