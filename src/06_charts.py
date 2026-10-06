"""
STEP 06 - Static Matplotlib charts for the README and memo.

Design choices: one message per chart, titles that state the takeaway's subject,
direct labels instead of legends where possible, one colour per molecule kept
consistent across every chart.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mtick  # noqa: E402
import pandas as pd  # noqa: E402

from config import CHARTS_DIR, TABLES_DIR  # noqa: E402

# Fixed colour per molecule (colour-blind-checked categorical palette)
MOLECULE_COLORS = {
    "Semaglutide": "#2a78d6", "Tirzepatide": "#eb6834", "Dulaglutide": "#1baf7a",
    "Liraglutide": "#eda100", "Exenatide": "#e87ba4",
}
BAR = "#2a78d6"
MUTED = "#52514e"

plt.rcParams.update({
    "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#bdbcb6", "axes.grid": True, "grid.color": "#e8e7e2",
    "grid.linewidth": 0.6, "axes.axisbelow": True, "figure.dpi": 150,
})

def _fmt(x, _=None):
    """Readable axis numbers: 1.25M, 350K, 900."""
    if abs(x) >= 1e6:
        return f"{x / 1e6:.2f}".rstrip("0").rstrip(".") + "M"
    if abs(x) >= 1e3:
        return f"{x / 1e3:,.0f}K"
    return f"{x:,.0f}"


millions = thousands = mtick.FuncFormatter(_fmt)


def spread_labels(values, min_gap):
    """Nudge end-of-line label positions apart so they never overlap."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    pos = list(values)
    for a, b in zip(order, order[1:]):
        if pos[b] - pos[a] < min_gap:
            pos[b] = pos[a] + min_gap
    return pos


def save(fig, name):
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / name, bbox_inches="tight")
    plt.close(fig)
    print(f"saved outputs/charts/{name}")


def claims_by_molecule():
    m = pd.read_csv(TABLES_DIR / "market_by_molecule_year.csv")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ends = []
    for mol, g in m.groupby("Gnrc_Name"):
        c = MOLECULE_COLORS.get(mol, MUTED)
        ax.plot(g["Year"], g["claims"], color=c, lw=2, marker="o", ms=4)
        ends.append((mol, g["Year"].iloc[-1], g["claims"].iloc[-1]))
    ys = spread_labels([e[2] for e in ends], m["claims"].max() * 0.05)
    for (mol, x, _), y in zip(ends, ys):
        ax.annotate(f" {mol}", (x, y), color=MUTED, va="center", fontsize=9)
    ax.yaxis.set_major_formatter(millions)
    ax.set_xticks(sorted(m["Year"].unique()))
    ax.set_title("Medicare Part D GLP-1 claims by molecule", loc="left", fontweight="bold")
    ax.set_ylabel("Claims")
    ax.margins(x=0.12)
    save(fig, "01_claims_by_molecule.png")


def brand_share():
    b = pd.read_csv(TABLES_DIR / "market_by_brand_year.csv")
    latest = b["Year"].max()
    b = b[b["Year"] == latest].sort_values("claim_share")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(b["Brnd_Name"], b["claim_share"], color=BAR, height=0.6)
    for y, v in enumerate(b["claim_share"]):
        ax.text(v, y, f" {v:.1%}", va="center", fontsize=9, color=MUTED)
    ax.xaxis.set_major_formatter(mtick.PercentFormatter(1, decimals=0))
    ax.set_title(f"Share of GLP-1 claims by brand, {latest}", loc="left", fontweight="bold")
    ax.grid(axis="y", visible=False)
    save(fig, "02_brand_share.png")


def top_bar(file, label_col, title, out, n=15):
    t = pd.read_csv(TABLES_DIR / file).nlargest(n, "claims").iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, 0.32 * n + 1.2))
    ax.barh(t[label_col], t["claims"], color=BAR, height=0.6)
    ax.xaxis.set_major_formatter(thousands)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.grid(axis="y", visible=False)
    save(fig, out)


def segments():
    s = pd.read_csv(TABLES_DIR / "segment_summary.csv")
    x = range(len(s))
    w = 0.38
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar([i - w / 2 for i in x], s["pct_prescribers"], w - 0.02, color="#9a9992", label="% of prescribers")
    ax.bar([i + w / 2 for i in x], s["pct_claims"], w - 0.02, color=BAR, label="% of GLP-1 claims")
    for i, (pp, pc) in enumerate(zip(s["pct_prescribers"], s["pct_claims"])):
        ax.text(i - w / 2, pp, f"{pp:.0%}", ha="center", va="bottom", fontsize=9, color=MUTED)
        ax.text(i + w / 2, pc, f"{pc:.0%}", ha="center", va="bottom", fontsize=9, color=MUTED)
    ax.set_xticks(list(x), s["segment"])
    ax.yaxis.set_major_formatter(mtick.PercentFormatter(1, decimals=0))
    ax.set_title("Prescriber segments: share of prescribers vs share of volume", loc="left", fontweight="bold")
    ax.legend(frameon=False)
    ax.grid(axis="x", visible=False)
    save(fig, "05_segments.png")


def forecast():
    f = pd.read_csv(TABLES_DIR / "forecast_long.csv")
    tot = f.groupby(["Year", "scenario"])["claims_value"].sum().unstack()
    hist = tot["Actual"].dropna()
    nxt = hist.index.max() + 1
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(hist.index, hist.values, color=BAR, lw=2, marker="o", ms=4)
    last_y, last_v = hist.index.max(), hist.iloc[-1]
    for scen, style in [("High", "--"), ("Base", "-"), ("Low", "--")]:
        v = tot.loc[nxt, scen]
        ax.plot([last_y, nxt], [last_v, v], color=BAR, lw=2 if scen == "Base" else 1.2, ls=style)
        ax.annotate(f" {scen}: {_fmt(v)}", (nxt, v), va="center", fontsize=9, color=MUTED)
    ax.fill_between([last_y, nxt], [last_v, tot.loc[nxt, "Low"]], [last_v, tot.loc[nxt, "High"]],
                    color=BAR, alpha=0.12, lw=0)
    ax.yaxis.set_major_formatter(millions)
    ax.set_xticks(list(hist.index) + [nxt])
    ax.set_title(f"Total GLP-1 Part D claims: actuals and {nxt} scenarios", loc="left", fontweight="bold")
    ax.margins(x=0.12)
    save(fig, "06_forecast.png")


def main():
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    claims_by_molecule()
    brand_share()
    top_bar("market_by_state.csv", "Prscrbr_State_Abrvtn", "Top 15 states by GLP-1 claims (latest year)", "03_top_states.png")
    top_bar("market_by_specialty.csv", "Prscrbr_Type", "Top 10 prescriber specialties by GLP-1 claims (latest year)",
            "04_top_specialties.png", n=10)
    segments()
    forecast()


if __name__ == "__main__":
    main()
