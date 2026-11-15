"""
Multi-scenario evaluation: runs the same framework logic (testbed_sim.py) on four
SYNTHETIC reservoir archetypes. All hydrology, sensor and radio parameters are ASSUMED.
Results are simulation outputs, not field measurements.
"""
import json, math
import numpy as np
import testbed_sim as T

ARCH = {
    "A_large_monsoon": dict(label="Large monsoon-fed (Gangrel-like)", area=40e6, nodes=40, dist=(0.3, 6.0),
                            base_in=60.0, storms=4, storm_peak=(300, 700), storm_hours=(8, 16), melt=0.0,
                            loss=1.0, release=(25, 90)),
    "B_small_urban": dict(label="Small urban water body", area=0.5e6, nodes=8, dist=(0.1, 1.5),
                          base_in=0.3, storms=4, storm_peak=(2, 5), storm_hours=(3, 8), melt=0.0,
                          loss=0.02, release=(0.15, 0.8)),
    "C_arid_flash": dict(label="Arid reservoir, flash floods", area=8e6, nodes=20, dist=(0.3, 4.0),
                         base_in=2.0, storms=2, storm_peak=(100, 180), storm_hours=(2, 4), melt=0.0,
                         loss=3.0, release=(1.5, 3.0)),
    "D_snowmelt": dict(label="Snowmelt-fed mountain reservoir", area=15e6, nodes=25, dist=(0.3, 5.0),
                       base_in=25.0, storms=2, storm_peak=(80, 140), storm_hours=(6, 12), melt=20.0,
                       loss=0.5, release=(30, 45)),
}

def make_truth_arch(p, days=7, seed=3):
    r = np.random.default_rng(seed)
    n = days * 288
    t = np.arange(n) * 300.0
    qin = np.full(n, p["base_in"])
    if p["melt"]:
        qin += p["melt"] * np.sin(2 * np.pi * (t - 6 * 3600) / 86400.0)  # diurnal melt cycle
    for _ in range(p["storms"]):
        t0 = r.uniform(0.5, days - 1) * 86400
        peak = r.uniform(*p["storm_peak"]); dur = r.uniform(*p["storm_hours"]) * 3600
        qin += peak * np.exp(-0.5 * ((t - t0 - dur / 2) / (dur / 5)) ** 2)
    qin = np.maximum(qin, 0.0)
    qout = np.empty(n)
    for d in range(days):
        qout[d * 288:(d + 1) * 288] = r.uniform(*p["release"])
    h = np.empty(n); h[0] = 10.0
    for k in range(1, n):
        h[k] = h[k - 1] + (qin[k - 1] - qout[k - 1] - p["loss"]) * 300.0 / p["area"]
    return t, h, qin, qout

def configure(p):
    T.ASSUMPTIONS["reservoir_area_m2"] = p["area"]
    T.ASSUMPTIONS["node_distance_km"] = p["dist"]
    T.make_truth = lambda days=7, seed=3: make_truth_arch(p, days, seed)

if __name__ == "__main__":
    out = {}
    for key, p in ARCH.items():
        configure(p)
        n = p["nodes"]
        pdr = [T.simulate_radio(n, 24, seed=s)["delivered"].mean() for s in range(15)]
        base = T.simulate_radio(n, 24, seed=99)
        lat = T.latency_samples(base)
        t, h, qin, qout = T.make_truth()
        res = dict(label=p["label"], area_km2=p["area"] / 1e6, nodes=n,
                   level_range_m=[round(float(h.min()), 3), round(float(h.max()), 3)],
                   pdr_mean=round(float(np.mean(pdr)), 4), pdr_std=round(float(np.std(pdr)), 4),
                   latency_mean_s=round(float(lat.mean()), 3), latency_p95_s=round(float(np.percentile(lat, 95)), 3),
                   false_alarms=T.run_false_alarms(runs=40)["combined"])
        att = {}
        for name, kind, mag in (("step_0.03", "step_offset", 0.03), ("step_0.05", "step_offset", 0.05),
                                ("step_0.10", "step_offset", 0.10), ("ramp_-0.10_2h", "ramp_offset", -0.10),
                                ("replay_24h", "replay", 0.0), ("stuck", "stuck", 0.0), ("spike_0.5", "spike", 0.5)):
            e = T.run_attack_eval(kind, mag, trials=100)
            att[name] = dict(rate=e["detection_rate"]["combined"], balance=e["detection_rate"]["balance"],
                             mean_delay_min=e["mean_delay_min"])
        res["attacks"] = att
        res["dos"] = T.run_dos(n_nodes=n, trials=40)
        out[key] = res
        print(key, json.dumps(res)[:1500], flush=True)
    json.dump(out, open(T.ROOT / "results" / "sim_results_multi.json", "w"), indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
