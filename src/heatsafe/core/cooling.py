from __future__ import annotations

from .models import CoolingCostInput, CoolingCostResult, CoolingEstimate


def _estimate(data: CoolingCostInput, duty_cycle: float) -> CoolingEstimate:
    power_kw = data.device_power_w / 1000.0
    energy = power_kw * data.daily_runtime_hours * data.number_of_days * duty_cycle
    cost = energy * data.electricity_price_per_kwh
    return CoolingEstimate(energy_kwh=round(energy, 3), estimated_cost=round(cost, 2))


def estimate_cooling_cost(data: CoolingCostInput) -> CoolingCostResult:
    low_duty = max(0.05, data.estimated_duty_cycle * 0.75)
    high_duty = min(1.0, data.estimated_duty_cycle * 1.25)
    low = _estimate(data, low_duty)
    central = _estimate(data, data.estimated_duty_cycle)
    high = _estimate(data, high_duty)

    fan_energy = (data.fan_power_w / 1000.0) * data.fan_runtime_hours * data.number_of_days
    fan_cost = fan_energy * data.electricity_price_per_kwh

    assisted_duty = max(0.05, data.estimated_duty_cycle * (1 - data.fan_assisted_duty_cycle_reduction))
    assisted = _estimate(data, assisted_duty)
    assisted_total_cost = assisted.estimated_cost + fan_cost

    zone_factor = {
        "whole-home": 1.0,
        "zone": max(0.35, min(0.85, 1 / max(data.number_of_rooms, 1) + 0.25)),
        "single-room": max(0.25, min(0.70, 1 / max(data.number_of_rooms, 1) + 0.15)),
    }[data.cooling_strategy]

    return CoolingCostResult(
        low=low,
        central=central,
        high=high,
        fan_energy_kwh=round(fan_energy, 3),
        fan_cost=round(fan_cost, 2),
        zone_cooling_comparison={
            "whole_home_reference_cost": central.estimated_cost,
            "selected_strategy_estimated_cost": round(central.estimated_cost * zone_factor, 2),
            "fan_assisted_total_cost": round(assisted_total_cost, 2),
        },
        assumptions=[
            "Electrical input power is treated as average rated draw while the compressor or cooling stage is active.",
            "Duty cycle is an estimate; real cycling depends on sizing, weather, thermostat, envelope, and maintenance.",
            "Low and high scenarios use 75% and 125% of the entered duty cycle, bounded to plausible limits.",
            "Zone-cooling comparisons are qualitative scenario factors, not guaranteed savings.",
        ],
        sensitivity={
            "cost_per_additional_runtime_hour_per_day": round(
                (data.device_power_w / 1000.0)
                * data.number_of_days
                * data.estimated_duty_cycle
                * data.electricity_price_per_kwh,
                2,
            ),
            "cost_if_electricity_price_rises_10_percent": round(central.estimated_cost * 1.10, 2),
            "cost_if_duty_cycle_falls_10_percent": round(central.estimated_cost * 0.90, 2),
        },
        currency=data.currency.upper(),
        limitations=[
            "This is an engineering estimate, not a utility-bill prediction.",
            "Taxes, tiered tariffs, standby power, demand charges, and equipment degradation are not modeled.",
        ],
    )
