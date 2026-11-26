import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# (name, capacity GB, bandwidth GB/s, unit/basis, color, estimated?)
# Values are per single device: HBM = 1 stack, GDDR = 1 chip, LPDDR = 1 package, DDR = 1 DIMM
data = [
    ("NVIDIA 3D Stacked DRAM\n(est., hybrid-bonded, Feynman ~2028)", 16, 10000, "stack", "#d62728", True),
    ("HBM4\n(12-Hi 36GB, 2048b @ 11Gbps)", 36, 2800, "stack", "#1f77b4", False),
    ("HBM3E\n(12-Hi 36GB, 1024b @ 9.6Gbps)", 36, 1230, "stack", "#1f77b4", False),
    ("HBM3\n(12-Hi 24GB, 1024b @ 6.4Gbps)", 24, 819, "stack", "#1f77b4", False),
    ("GDDR7\n(24Gb chip, x32 @ 32Gbps)", 3, 128, "chip", "#2ca02c", False),
    ("GDDR6X\n(16Gb chip, x32 @ 21Gbps)", 2, 84, "chip", "#2ca02c", False),
    ("LPDDR6\n(16GB pkg, x96 @ 10.667Gbps)", 16, 114, "package", "#9467bd", False),
    ("LPDDR5X\n(16GB pkg, x64 @ 8.533Gbps)", 16, 68.3, "package", "#9467bd", False),
    ("LPDDR4X\n(8GB pkg, x64 @ 4.266Gbps)", 8, 34.1, "package", "#9467bd", False),
    ("DDR5\n(64GB RDIMM, DDR5-6400)", 64, 51.2, "DIMM", "#ff7f0e", False),
    ("DDR4\n(32GB RDIMM, DDR4-3200)", 32, 25.6, "DIMM", "#ff7f0e", False),
]


fig, ax = plt.subplots(figsize=(11, 7.5), dpi=150)
for name, cap, bw, unit, color, est in data:
    ax.scatter(cap, bw, s=140, color="white" if est else color, edgecolors=color,
               linewidths=2, zorder=3, hatch=None)
    ax.annotate(name.split("\n")[0], (cap, bw), textcoords="offset points",
                xytext=(10, 0), fontsize=16, color=color, va="center",
                fontstyle="italic" if est else "normal")

ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlim(1, 200); ax.set_ylim(15, 30000)
ax.set_xlabel("Capacity per device (GB)  [log]", fontsize=11)
ax.set_ylabel("Bandwidth per device (GB/s)  [log]", fontsize=11)
ax.set_title("Memory Capacity vs Bandwidth (per stack / chip / package / DIMM)", fontsize=13)
ax.grid(True, which="both", alpha=0.25)

plt.tight_layout()
plt.savefig("memory_capacity_vs_bandwidth.png")
