import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Font: Noto Sans KR (provided by the Noto Sans CJK KR family on Linux: apt install fonts-noto-cjk)
from matplotlib import font_manager
_names = {f.name for f in font_manager.fontManager.ttflist}
FONT = next((n for n in ["Noto Sans KR", "Noto Sans CJK KR"] if n in _names), "sans-serif")
plt.rcParams["font.family"] = FONT
plt.rcParams["mathtext.fontset"] = "custom"
plt.rcParams["mathtext.rm"] = FONT
plt.rcParams["axes.unicode_minus"] = False

# (name, capacity GB, bandwidth GB/s, unit/basis, color, estimated?)
# NOTE: point positions were placed manually per user's sketch (not raw spec values)
# Values were originally per single device: HBM = 1 stack, GDDR = 1 chip, LPDDR = 1 package, DDR = 1 DIMM
data = [
    ("NVIDIA 3D Stacked DRAM", 4.5, 9200, "stack", "#d62728", True),
    ("HBM4\n(12-Hi 36GB, 2048b @ 11Gbps)", 26, 7400, "stack", "#1f77b4", False),
    ("HBM3E\n(12-Hi 36GB, 1024b @ 9.6Gbps)", 16.4, 3100, "stack", "#1f77b4", False),
    ("HBM3\n(12-Hi 24GB, 1024b @ 6.4Gbps)", 11.2, 2100, "stack", "#1f77b4", False),
    ("GDDR7\n(24Gb chip, x32 @ 32Gbps)", 4.9, 650, "chip", "#2ca02c", False),
    ("GDDR6X\n(16Gb chip, x32 @ 21Gbps)", 3.2, 380, "chip", "#2ca02c", False),
    ("LPDDR6\n(16GB pkg, x96 @ 10.667Gbps)", 7.7, 275, "package", "#9467bd", False),
    ("LPDDR5X\n(16GB pkg, x64 @ 8.533Gbps)", 7.7, 165, "package", "#9467bd", False),
    ("LPDDR4X\n(8GB pkg, x64 @ 4.266Gbps)", 3.9, 82, "package", "#9467bd", False),
    ("DDR5\n(64GB RDIMM, DDR5-6400)", 57, 465, "DIMM", "#ff7f0e", False),
    ("DDR4\n(32GB RDIMM, DDR4-3200)", 42, 485, "DIMM", "#ff7f0e", False),
]


fig, ax = plt.subplots(figsize=(11, 7.5), dpi=150)
for name, cap, bw, unit, color, est in data:
    ax.scatter(cap, bw, s=280 if est else 140, color="white" if est else color, edgecolors=color,
               linewidths=2, zorder=3, hatch=None)
    label = name.split("\n")[0]
    off, ha, va = {"NVIDIA 3D Stacked DRAM": ((-6, 14), "left", "bottom"),
                   "DDR4": ((-10, 0), "right", "center")}.get(label, ((10, 0), "left", "center"))
    ax.annotate(label, (cap, bw), textcoords="offset points",
                xytext=off, ha=ha, fontsize=32 if est else 16, color=color, va=va,
                fontweight="bold" if est else "normal")

import numpy as np
xs = np.array([1, 200])
for k in [1000, 100, 20, 10, 1]:
    ax.plot(xs, k * xs, ls="--", lw=1.2, color="#4a6fd6", alpha=0.7, zorder=1)
    xl = min(200, 26000 / k) / 1.15
    ax.text(xl, k * xl * 1.05, f"{k}/s", color="#4a6fd6", fontsize=12, ha="right", va="bottom",
            rotation=0)
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(1, 200); ax.set_ylim(15, 30000)
ax.set_xlabel("Capacity per device (GB)  [log]", fontsize=11)
ax.set_ylabel("Bandwidth per device (GB/s)  [log]", fontsize=11)
ax.set_title("Memory Capacity vs Bandwidth (per stack / chip / package / DIMM)", fontsize=13)
ax.grid(True, which="both", alpha=0.25)

plt.tight_layout()
plt.savefig("memory_capacity_vs_bandwidth.png")
