"""
Simulation testbed for the Cyber-Secure IoT-GIS reservoir framework.

IMPORTANT: everything here is SYNTHETIC. Reservoir hydrology, sensor noise models,
LoRa radio behaviour and backhaul delays are ASSUMED (see ASSUMPTIONS).
Results show how the framework's mechanisms behave under these assumptions.
They are NOT field measurements from Ravishankar Sagar (Gangrel Dam).
"""
import json, math
import numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent   # repository root
(ROOT / "results").mkdir(exist_ok=True)

SEED = 2026
rng = np.random.default_rng(SEED)

ASSUMPTIONS = dict(
    reservoir_area_m2=40e6, area_error_in_detector=0.05,
    level_noise_sigma_m=0.01, flow_noise_rel=0.02,
    uplink_interval_s=300, samples_per_uplink=5,
    lora_bw_hz=125e3, lora_cr=1, lora_preamble=8, lorawan_overhead_B=13, app_payload_B=20,
    lora_channels=3, p_fade_loss=0.02, node_distance_km=(0.3, 6.0),
    sf_by_distance_km={2.0: 7, 3.5: 8, 4.5: 9, 6.0: 10},
    backhaul_lognormal_median_s=0.08, backhaul_lognormal_sigma=0.5,
    gw_proc_s=(0.005, 0.020), ingest_lognormal_median_s=0.05, ingest_sigma=0.5,
    dashboard_push_s=(0.10, 0.40),
    raw_overhead_B={"https_per_uplink": 460, "mqtt_per_uplink": 150},
    edge_batch_overhead_B=80, edge_binary_reading_B=20, edge_batch_period_s=60,
)

# ---------------------------------------------------------------- LoRa helpers
def airtime_s(sf, pl_bytes, bw=125e3, cr=1, npre=8, crc=1, ih=0):
    tsym = (2 ** sf) / bw
    de = 1 if (sf >= 11 and bw == 125e3) else 0
    num = 8 * pl_bytes - 4 * sf + 28 + 16 * crc - 20 * ih
    npay = 8 + max(math.ceil(num / (4 * (sf - 2 * de))) * (cr + 4), 0)
    return (npre + 4.25 + npay) * tsym

def sf_for_distance(d):
    for lim, sf in sorted(ASSUMPTIONS["sf_by_distance_km"].items()):
        if d <= lim:
            return sf
    return 10

def simulate_radio(n_nodes, hours=24, seed=0):
    r = np.random.default_rng(seed)
    A = ASSUMPTIONS
    dist = r.uniform(*A["node_distance_km"], n_nodes)
    sf = np.array([sf_for_distance(d) for d in dist])
    pl = A["lorawan_overhead_B"] + A["app_payload_B"]
    toa = np.array([airtime_s(s, pl) for s in sf])
    T = A["uplink_interval_s"]
    n_ups = int(hours * 3600 / T)
    offs = r.uniform(0, T, n_nodes)
    starts, node_id = [], []
    for k in range(n_ups):
        t = offs + k * T + r.uniform(-10, 10, n_nodes)
        starts.append(t); node_id.append(np.arange(n_nodes))
    starts = np.concatenate(starts); node_id = np.concatenate(node_id)
    ch = r.integers(0, A["lora_channels"], starts.size)
    s_arr, a_arr = sf[node_id], toa[node_id]
    lost = np.zeros(starts.size, bool)
    for c in range(A["lora_channels"]):
        for s in np.unique(sf):
            idx = np.where((ch == c) & (s_arr == s))[0]
            if idx.size < 2: continue
            idx = idx[np.argsort(starts[idx])]
            st, en = starts[idx], starts[idx] + a_arr[idx]
            ov = st[1:] < en[:-1]
            lost[idx[1:][ov]] = True; lost[idx[:-1][ov]] = True
    lost |= r.random(starts.size) < A["p_fade_loss"]
    delivered = ~lost
    return dict(starts=starts, node=node_id, toa=a_arr, delivered=delivered, sf=sf)

def latency_samples(res, seed=1):
    r = np.random.default_rng(seed); A = ASSUMPTIONS
    d = res["delivered"]; n = d.sum()
    lat = (res["toa"][d]
           + r.uniform(*A["gw_proc_s"], n)
           + r.lognormal(math.log(A["backhaul_lognormal_median_s"]), A["backhaul_lognormal_sigma"], n)
           + r.lognormal(math.log(A["ingest_lognormal_median_s"]), A["ingest_sigma"], n)
           + r.uniform(*A["dashboard_push_s"], n))
    return lat

# ---------------------------------------------------------------- reservoir truth
def make_truth(days=7, seed=3):
    r = np.random.default_rng(seed); A = ASSUMPTIONS
    n = days * 24 * 12  # 5-min steps
    t = np.arange(n) * 300.0
    qin = np.full(n, 60.0)
    for _ in range(4):
        t0 = r.uniform(0.5, days - 1) * 86400
        peak = r.uniform(300, 700); dur = r.uniform(8, 16) * 3600
        qin += peak * np.exp(-0.5 * ((t - t0 - dur / 2) / (dur / 5)) ** 2)
    qout = np.empty(n); lvl = 40.0
    for d in range(days):
        lvl = r.uniform(25, 90)
        qout[d * 288:(d + 1) * 288] = lvl
    loss = 1.0
    h = np.empty(n); h[0] = 10.0
    for k in range(1, n):
        h[k] = h[k - 1] + (qin[k - 1] - qout[k - 1] - loss) * 300.0 / A["reservoir_area_m2"]
    return t, h, qin, qout

def make_streams(h, qin, qout, seed):
    """Uplink-level measurements: level = median of 5 samples, flows = 5-min mean."""
    r = np.random.default_rng(seed); A = ASSUMPTIONS
    sig_med = A["level_noise_sigma_m"] * 1.25 / math.sqrt(A["samples_per_uplink"])
    level = h + r.normal(0, sig_med, h.size)
    qi = qin * (1 + r.normal(0, A["flow_noise_rel"] / math.sqrt(5), h.size))
    qo = qout * (1 + r.normal(0, A["flow_noise_rel"] / math.sqrt(5), h.size))
    return level, qi, qo

# ---------------------------------------------------------------- detectors
W = 12  # 1-hour window of 5-min uplinks

def residual(level, qi, qo):
    A = ASSUMPTIONS["reservoir_area_m2"] * (1 + ASSUMPTIONS["area_error_in_detector"])
    n = level.size; res = np.full(n, np.nan)
    net = (qi - qo) * 300.0 / A
    cs = np.concatenate([[0], np.cumsum(net)])
    for k in range(W, n):
        res[k] = (level[k] - level[k - W]) - (cs[k] - cs[k - W])
    return res

def calibrate(level, qi, qo, cal_steps):
    res = residual(level, qi, qo)[:cal_steps]
    res = res[~np.isnan(res)]
    d = np.diff(level[:cal_steps])
    return dict(res_sigma=res.std(), d_sigma=d.std(), lo=level[:cal_steps].min() - 1.0,
                hi=level[:cal_steps].max() + 5.0)

def detect(level, qi, qo, cal, k_sigma=4.0, consecutive=2):
    n = level.size; flags = {k: np.zeros(n, bool) for k in ("range_rate", "zscore", "balance", "stuck")}
    d = np.concatenate([[0], np.diff(level)])
    flags["range_rate"] = (level < cal["lo"]) | (level > cal["hi"]) | (np.abs(d) > 8 * cal["d_sigma"] + 0.05)
    # rolling z-score of first difference (12-sample window)
    for k in range(W, n):
        w = d[k - W:k]
        if w.std() > 0 and abs(d[k] - w.mean()) > 5 * max(w.std(), cal["d_sigma"]):
            flags["zscore"][k] = True
    res = residual(level, qi, qo)
    raw = np.abs(res) > k_sigma * cal["res_sigma"]
    raw[np.isnan(res)] = False
    for k in range(consecutive - 1, n):
        flags["balance"][k] = raw[k - consecutive + 1:k + 1].all()
    for k in range(W, n):
        if np.ptp(level[k - W + 1:k + 1]) < 1e-9:
            flags["stuck"][k] = True
    flags["combined"] = np.logical_or.reduce([flags[k] for k in ("range_rate", "zscore", "balance", "stuck")])
    return flags

# ---------------------------------------------------------------- attacks
def inject(level, kind, start, dur, mag, h_ref=None):
    x = level.copy(); end = start + dur
    if kind == "step_offset":
        x[start:end] += mag
    elif kind == "ramp_offset":
        ramp = np.linspace(0, mag, min(24, dur)); x[start:start + ramp.size] += ramp
        x[start + ramp.size:end] += mag
    elif kind == "replay":
        x[start:end] = level[start - 288:end - 288]  # application-layer replay of values from 24 h earlier
    elif kind == "stuck":
        x[start:end] = x[start - 1]
    elif kind == "spike":
        x[start] += mag
    return x

def run_attack_eval(kind, mag, trials=200, dur_steps=36, seed=11):
    t, h, qin, qout = make_truth(); n = h.size
    cal_steps = 2 * 288
    hits = {k: 0 for k in ("range_rate", "zscore", "balance", "stuck", "combined")}
    delays = []
    r = np.random.default_rng(seed)
    for i in range(trials):
        level, qi, qo = make_streams(h, qin, qout, seed=1000 + i)
        cal = calibrate(level, qi, qo, cal_steps)
        s = int(r.integers(cal_steps + 300, n - dur_steps - 5))
        x = inject(level, kind, s, dur_steps if kind != "spike" else 1, mag)
        fl = detect(x, qi, qo, cal)
        win = slice(s, s + dur_steps + 12)
        any_c = False
        for k in hits:
            if fl[k][win].any():
                hits[k] += 1
        if fl["combined"][win].any():
            delays.append((np.argmax(fl["combined"][win])) * 5.0)
    return dict(kind=kind, magnitude_m=mag, trials=trials,
                detection_rate={k: round(v / trials, 3) for k, v in hits.items()},
                mean_delay_min=round(float(np.mean(delays)), 1) if delays else None,
                median_delay_min=round(float(np.median(delays)), 1) if delays else None)

def run_false_alarms(runs=100):
    t, h, qin, qout = make_truth(); cal_steps = 2 * 288
    steps_eval = h.size - cal_steps
    per_day = {k: [] for k in ("range_rate", "zscore", "balance", "stuck", "combined")}
    fpr = {k: [] for k in per_day}
    for i in range(runs):
        level, qi, qo = make_streams(h, qin, qout, seed=5000 + i)
        cal = calibrate(level, qi, qo, cal_steps); fl = detect(level, qi, qo, cal)
        for k in per_day:
            f = fl[k][cal_steps:]
            fpr[k].append(f.mean())
            # distinct alarm episodes per day
            ep = ((f[1:] & ~f[:-1]).sum() + int(f[0])) / (steps_eval / 288)
            per_day[k].append(ep)
    return {k: dict(fpr=round(float(np.mean(fpr[k])), 5), alarm_episodes_per_day=round(float(np.mean(per_day[k])), 3))
            for k in per_day}

# ---------------------------------------------------------------- DoS / silence rule
def run_dos(n_nodes=40, jam_min=30, trials=100, seed=21):
    r = np.random.default_rng(seed); T = ASSUMPTIONS["uplink_interval_s"]
    delays, fa_days = [], []
    for i in range(trials):
        res = simulate_radio(n_nodes, hours=24, seed=7000 + i)
        # network-level rule: alarm if >=50% of nodes have missed >=3 consecutive expected uplinks at a given time grid
        grid = np.arange(0, 24 * 3600, 60.0)
        last_rx = np.zeros(n_nodes)  # all nodes assumed heard at t=0 (avoids cold-start artefact)
        order = np.argsort(res["starts"]); st = res["starts"][order]; nd = res["node"][order]; dv = res["delivered"][order]
        j = 0; false_alarm = 0; prev_alarm = False
        jam_start = r.uniform(6, 20) * 3600; jam_end = jam_start + jam_min * 60
        detect_t = None
        for g in grid:
            while j < st.size and st[j] <= g:
                if dv[j] and not (jam_start <= st[j] < jam_end):
                    last_rx[nd[j]] = st[j]
                j += 1
            silent = (g - last_rx) > 3 * T
            alarm = silent.mean() >= 0.5
            if alarm and not prev_alarm:
                if jam_start <= g <= jam_end + 4 * T:
                    if detect_t is None: detect_t = g - jam_start
                else:
                    false_alarm += 1
            prev_alarm = alarm
        if detect_t is not None: delays.append(detect_t / 60.0)
        fa_days.append(false_alarm)
    return dict(jam_minutes=jam_min, trials=trials, detection_rate=round(len(delays) / trials, 3),
                mean_delay_min=round(float(np.mean(delays)), 1) if delays else None,
                false_alarms_per_day=round(float(np.mean(fa_days)), 3))

# ---------------------------------------------------------------- accuracy of edge filtering
def run_accuracy(seed=33, days=3):
    r = np.random.default_rng(seed); n = days * 1440
    t = np.arange(n) / 1440.0
    truths = dict(
        level_m=10 + 0.5 * np.sin(2 * np.pi * t / 3) + 0.01 * np.cumsum(r.normal(0, 0.05, n)) * 0,
        turbidity_NTU=15 + 5 * np.sin(2 * np.pi * t) + np.maximum(0, 30 * np.exp(-0.5 * ((t - 1.5) / 0.15) ** 2)),
        pH=7.6 + 0.25 * np.sin(2 * np.pi * (t - 0.3)),
        do_mgL=8.0 + 1.2 * np.sin(2 * np.pi * (t - 0.4)))
    noise = dict(level_m=(0.010, 0.5), turbidity_NTU=(0.8, 15.0), pH=(0.05, 0.8), do_mgL=(0.15, 3.0))  # (sigma, spike magnitude)
    out = {}
    for name, tr in truths.items():
        sg, sp = noise[name]
        x = tr + r.normal(0, sg, n)
        spikes = r.random(n) < 0.003
        x[spikes] += r.choice([-1, 1], spikes.sum()) * sp
        # edge: median of 5 consecutive samples (uplink = 1 per 5 samples)
        m = np.median(x[: n // 5 * 5].reshape(-1, 5), axis=1)
        ref = tr[: n // 5 * 5].reshape(-1, 5).mean(axis=1)
        raw_err = x - tr
        edge_err = m - ref
        out[name] = dict(raw_MAE=round(float(np.abs(raw_err).mean()), 4), raw_RMSE=round(float(np.sqrt((raw_err ** 2).mean())), 4),
                         edge_MAE=round(float(np.abs(edge_err).mean()), 4), edge_RMSE=round(float(np.sqrt((edge_err ** 2).mean())), 4))
    return out

# ---------------------------------------------------------------- main
if __name__ == "__main__":
    results = dict(assumptions=ASSUMPTIONS, seed=SEED)

    # radio scalability
    scal = {}
    for n in (20, 40, 80, 160, 320):
        pdrs = [simulate_radio(n, 24, seed=s)["delivered"].mean() for s in range(20)]
        scal[n] = dict(pdr_mean=round(float(np.mean(pdrs)), 4), pdr_std=round(float(np.std(pdrs)), 4))
    results["pdr_vs_nodes"] = scal

    # latency for 40-node case
    base = simulate_radio(40, 24, seed=99)
    lat = latency_samples(base)
    results["latency_40_nodes_s"] = dict(mean=round(float(lat.mean()), 3), median=round(float(np.median(lat)), 3),
                                          p95=round(float(np.percentile(lat, 95)), 3), p99=round(float(np.percentile(lat, 99)), 3),
                                          n=int(lat.size))
    results["airtime_s_by_sf"] = {sf: round(airtime_s(sf, 33), 4) for sf in range(7, 11)}
    results["sf_distribution_40_nodes"] = {int(s): int((base["sf"] == s).sum()) for s in np.unique(base["sf"])}

    # backhaul bandwidth
    A = ASSUMPTIONS; n_nodes = 40
    ups_per_min = n_nodes * 60 / A["uplink_interval_s"]
    edge_per_min = A["edge_batch_overhead_B"] + A["edge_binary_reading_B"] * ups_per_min
    bw = {}
    for name, ov in A["raw_overhead_B"].items():
        raw_per_min = (ov + A["app_payload_B"] * 3) * ups_per_min  # JSON expansion x3 assumed
        bw[name] = dict(raw_B_per_day=int(raw_per_min * 1440), edge_B_per_day=int(edge_per_min * 1440),
                        reduction_pct=round(100 * (1 - edge_per_min / raw_per_min), 1))
    results["backhaul_bandwidth"] = bw

    results["accuracy_edge_median_filter"] = run_accuracy()
    results["false_alarms_clean_stream"] = run_false_alarms(runs=60)

    atk = []
    for mag in (0.02, 0.05, 0.10, 0.30):
        atk.append(run_attack_eval("step_offset", mag))
    for mag in (-0.05, -0.30):
        atk.append(run_attack_eval("ramp_offset", mag))
    atk.append(run_attack_eval("replay", 0.0))
    atk.append(run_attack_eval("stuck", 0.0))
    atk.append(run_attack_eval("spike", 0.5))
    results["attacks"] = atk
    results["dos_gateway_jam"] = run_dos()

    with open(ROOT / "results" / "sim_results.json", "w") as f:
        json.dump(results, f, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(json.dumps({k: v for k, v in results.items() if k != "assumptions"}, indent=1, default=str)[:9000])
