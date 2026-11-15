"""Figures for the reservoir IoT-GIS manuscript. All values are copied from the manuscript tables.
Usage: python make_figures.py [daily_rainfall.csv]   (CSV columns: date,rain_mm  -> adds the rainfall panel to Fig. 3)"""
import sys, datetime as dt
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, matplotlib.dates as mdates
import numpy as np
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":8,"axes.spines.top":False,"axes.spines.right":False,
 "axes.edgecolor":"#52514e","axes.labelcolor":"#0b0b0b","xtick.color":"#52514e","ytick.color":"#52514e","axes.grid":True,"grid.color":"#e4e3df","grid.linewidth":0.6})
C = ["#2a78d6","#eb6834","#1baf7a","#eda100"]; INK="#0b0b0b"; SUB="#52514e"
NAMES = ["A. Large monsoon-fed","B. Small urban","C. Arid, flash floods","D. Snowmelt-fed"]
SHORT = ["A","B","C","D"]

# ---- Fig 2a: detection vs offset (Table 5; 2 cm from the separate smaller test, archetype A only)
fig, ax = plt.subplots(figsize=(4.6,3.2))
x=[3,5,10]; det=[[93,100,100],[95,100,100],[96,100,100],[97,100,100]]
mk=["o","s","^","D"]
for i in range(4):
    ax.plot(x,det[i],marker=mk[i],color=C[i],lw=1.6,ms=5.5,mec="white",mew=0.8,label=NAMES[i],zorder=3+i)
ax.plot([2,3],[13.5,93],ls=":",color=C[0],lw=1.2,zorder=2)
ax.plot([2],[13.5],marker="o",ms=7,mfc="white",mec=C[0],mew=1.6,ls="none",zorder=6,label="A, 2 cm (separate test, 200 trials)")
ax.annotate("13.5 %",(2,13.5),xytext=(2.15,6),fontsize=7.5,color=INK)
ax.set_xlim(1.6,10.6); ax.set_ylim(0,106); ax.set_xticks([2,3,5,10])
ax.set_xlabel("Level offset added to the level stream (cm)"); ax.set_ylabel("Combined detection rate (%)")
ax.set_title("Simulated: detection rate versus step-offset size\n(100 random trials per point)",fontsize=8.5,loc="left",color=INK)
ax.legend(frameon=False,fontsize=7,loc="center right",bbox_to_anchor=(1.0,0.45))
fig.tight_layout(); fig.savefig("fig_detection_vs_offset.png",dpi=300); plt.close(fig)

# ---- Fig 3 (b): four archetypes (Tables 3 and 5)
pdr=[97.45,97.82,97.84,97.77]; sd=[0.29,0.40,0.22,0.22]
mean=[0.61,0.48,0.53,0.58]; p95=[0.93,0.65,0.73,0.89]
replay=[53,54,100,97]; off3=[93,95,96,97]
fig,axs=plt.subplots(1,3,figsize=(7.2,3.6))
xs=np.arange(4)
ax=axs[0]
ax.bar(xs,pdr,yerr=sd,color=C,width=0.6,capsize=3,ecolor=SUB,error_kw={"lw":1})
ax.set_ylim(95,99); ax.set_xticks(xs,SHORT); ax.set_ylabel("Packet delivery ratio (%), axis from 95")
for i,v in enumerate(pdr): ax.text(i,98.55,f"{v:.2f}",ha="center",fontsize=7,color=INK)
ax.set_title("(a) PDR, mean ± SD",fontsize=8.5,loc="left")
ax=axs[1]; w=0.36
ax.bar(xs-w/2,mean,w,color=C,label="mean"); ax.bar(xs+w/2,p95,w,color=C,alpha=0.45,hatch="///",edgecolor="white",label="95th percentile")
for i in range(4):
    ax.text(i-w/2,mean[i]+0.015,f"{mean[i]:.2f}",ha="center",fontsize=6.5); ax.text(i+w/2,p95[i]+0.015,f"{p95[i]:.2f}",ha="center",fontsize=6.5)
ax.set_xticks(xs,SHORT); ax.set_ylim(0,1.15); ax.set_ylabel("End-to-end latency (s)")
ax.set_title("(b) Latency: mean (solid),\n95th percentile (hatched)",fontsize=8.5,loc="left")
ax=axs[2]
ax.bar(xs-w/2,off3,w,color=C,label="+3 cm offset"); ax.bar(xs+w/2,replay,w,color=C,alpha=0.45,hatch="///",edgecolor="white")
for i in range(4):
    ax.text(i-w/2,off3[i]+1.5,f"{off3[i]}",ha="center",fontsize=6.5); ax.text(i+w/2,replay[i]+1.5,f"{replay[i]}",ha="center",fontsize=6.5)
ax.set_xticks(xs,SHORT); ax.set_ylim(0,115); ax.set_ylabel("Detection rate (%)")
ax.set_title("(c) Detection: +3 cm (solid),\nreplay (hatched)",fontsize=8.5,loc="left")
for a in axs: a.set_xlabel("Archetype")
fig.suptitle("Simulated: four synthetic archetypes (A monsoon-fed, B urban, C arid, D snowmelt-fed)",fontsize=8.5,x=0.01,ha="left",color=INK)
fig.text(0.01,0.005,"Not shown in (c): +5 cm and +10 cm offsets, slow ramp, stuck sensor, spike and jamming were detected in 100 % of trials\nin all archetypes (Table 5). False alarms on clean data: 0 per day.\n",fontsize=6.5,color=SUB)
fig.tight_layout(rect=(0,0.07,1,0.94)); fig.savefig("fig_archetype_comparison.png",dpi=300); plt.close(fig)

# ---- Fig 4 (c): Gangrel live storage (Table 7, CWC bulletins, REAL data) + optional daily rainfall
T7="""01.02.2024 0.293
14.03.2024 0.214
12.04.2024 0.145
02.05.2024 0.114
27.06.2024 0.038
25.07.2024 0.344
01.08.2024 0.640
08.08.2024 0.692
29.08.2024 0.630
05.09.2024 0.535
12.09.2024 0.757
10.10.2024 0.629
17.10.2024 0.582
07.11.2024 0.562
14.11.2024 0.560
21.11.2024 0.557
05.12.2024 0.536
19.12.2024 0.516
26.12.2024 0.505
30.01.2025 0.457
08.05.2025 0.230"""
d=[(dt.datetime.strptime(l.split()[0],"%d.%m.%Y"),float(l.split()[1])) for l in T7.splitlines()]
rain=None
if len(sys.argv)>1:
    import csv
    rain=[(dt.datetime.fromisoformat(r["date"]),float(r["rain_mm"])) for r in csv.DictReader(open(sys.argv[1]))]
if rain: fig,(ax,ar)=plt.subplots(2,1,figsize=(6.4,4.4),sharex=True,gridspec_kw={"height_ratios":[2.2,1]})
else: fig,ax=plt.subplots(figsize=(6.4,3.3))
ax.plot([a for a,_ in d],[b for _,b in d],color=C[0],lw=1.6,marker="o",ms=4,mec="white",mew=0.7,zorder=3)
ax.axhline(0.767,color=SUB,lw=0.9,ls="--"); ax.text(d[0][0],0.775,"live capacity at FRL (348.70 m): 0.767 BCM",fontsize=7,color=SUB)
ax.set_ylabel("Live storage (BCM)"); ax.set_ylim(0,0.86)
ev=[(dt.datetime(2024,8,1),0.640,"+0.296 BCM in week to 01.08\n(181 mm in week to 25.07,\n98 mm in week to 01.08)",(-110,-10)),
    (dt.datetime(2024,9,12),0.757,"+0.222 BCM in week to 12.09\n(125 mm, incl. 65 mm on 09.09)",(25,-14))]
for t,v,txt,off in ev:
    ax.annotate(txt,(t,v),xytext=off,textcoords="offset points",fontsize=6.5,color=INK,arrowprops=dict(arrowstyle="-",color=SUB,lw=0.7))
ax.set_title("Gangrel (Ravishankar Sagar) live storage, CWC weekly bulletins, 2024 to 2025\n(observed data, not simulated)",fontsize=8,loc="left")
if rain:
    ar.bar([a for a,_ in rain],[b for _,b in rain],width=1.0,color=C[2]); ar.set_ylabel("Daily rainfall (mm)\nNASA POWER / MERRA-2")
    last=ar
else:
    last=ax
last.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); last.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
fig.tight_layout(); fig.savefig("fig_gangrel_storage_rainfall.png",dpi=300); plt.close(fig)
print("done")
