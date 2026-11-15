"""
Sensitivity run: archetype A with a LEVEL-DEPENDENT surface area taken from the
Gangrel level-storage relation derived from CWC bulletins (quadratic fit).
Everything else (sensor noise, radio, storms, attacks) is still synthetic.
"""
import json, numpy as np, pandas as pd
import testbed_sim as T

df = pd.read_csv(T.ROOT / "data" / "gangrel_cwc_weekly.csv")
H = df.level_m.values; S = df.live_storage_bcm.values * 1e9
Q = np.polyfit(H, S, 2)                      # S(h) in m3, h in m (CWC datum)
dQ = np.polyder(Q)
area = lambda h: np.maximum(np.polyval(dQ, h), 5e6)   # m2, floor to avoid nonsense below data range
hgrid = np.linspace(336.0, 349.5, 4000); Sgrid = np.polyval(Q, hgrid)
inv = lambda s: np.interp(s, Sgrid, hgrid)   # S -> h

def make_truth_area(h0, days=7, seed=3):
    r = np.random.default_rng(seed); n = days * 288; t = np.arange(n) * 300.0
    qin = np.full(n, 60.0)
    for _ in range(4):
        t0 = r.uniform(0.5, days - 1) * 86400; peak = r.uniform(300, 700); dur = r.uniform(8, 16) * 3600
        qin += peak * np.exp(-0.5 * ((t - t0 - dur / 2) / (dur / 5)) ** 2)
    qout = np.empty(n)
    for d in range(days): qout[d*288:(d+1)*288] = r.uniform(25, 90)
    s = float(np.polyval(Q, h0)); h = np.empty(n); h[0] = h0
    for k in range(1, n):
        s += (qin[k-1] - qout[k-1] - 1.0) * 300.0
        h[k] = inv(s)
    return t, h, qin, qout

def residual_area(level, qi, qo):
    n = level.size; res = np.full(n, np.nan); W = T.W
    net = (qi - qo) * 300.0
    cs = np.concatenate([[0], np.cumsum(net)])
    for k in range(W, n):
        A = area(0.5 * (level[k] + level[k - W])) * (1 + T.ASSUMPTIONS["area_error_in_detector"])
        res[k] = (level[k] - level[k - W]) - (cs[k] - cs[k - W]) / A
    return res

if __name__ == "__main__":
    T.residual = residual_area
    out = {"fit": {"R2": float(1 - ((S - np.polyval(Q, H))**2).sum() / ((S - S.mean())**2).sum()),
                   "area_km2": {str(h): round(float(area(h))/1e6, 1) for h in (338, 340, 343, 346, 348.7)}}}
    for h0 in (340.0, 343.0, 346.0):
        T.make_truth = lambda days=7, seed=3, h0=h0: make_truth_area(h0, days, seed)
        t, h, qin, qout = T.make_truth()
        res = {"start_level_m": h0, "area_km2_at_start": round(float(area(h0))/1e6, 1),
               "level_range_m": [round(float(h.min()),2), round(float(h.max()),2)],
               "false_alarms": T.run_false_alarms(runs=40)["combined"], "attacks": {}}
        for name, kind, mag in (("step_0.03","step_offset",0.03),("step_0.05","step_offset",0.05),("step_0.10","step_offset",0.10),
                                ("ramp_-0.10_2h","ramp_offset",-0.10),("replay_24h","replay",0.0),("stuck","stuck",0.0),("spike_0.5","spike",0.5)):
            e = T.run_attack_eval(kind, mag, trials=100)
            res["attacks"][name] = dict(rate=e["detection_rate"]["combined"], balance=e["detection_rate"]["balance"], mean_delay_min=e["mean_delay_min"])
        out[f"h0_{int(h0)}"] = res
        print(json.dumps(res), flush=True)
    json.dump(out, open(T.ROOT / "results" / "sim_results_area.json", "w"), indent=2)
