##############################################################
# 0 · Imports & inputs
##############################################################
import pandas as pd
from collections import defaultdict
from pathlib import Path

# --  your raw data  ----------------------------------------------------------
# records : list[dict]    – already in memory
# pop_counts : dict[(str,str), int] | None

df = pd.json_normalize(records)          # handles any nested keys sensiblely
df.rename(columns=lambda c: c.replace(".", "_"), inplace=True)

# normalise missing / blank countryCode
df["classifications_countryCode"] = (
    df.get("classifications_countryCode")
      .fillna("NA")
      .replace("", "NA")
)

##############################################################
# 1 · Field-coverage by type  (sample only)
##############################################################
META = {"type", "classifications_countryCode"}
value_cols = [c for c in df.columns if c not in META]

coverage_wide = (
    df
    .groupby("type")[value_cols]
    .apply(lambda g: g.notna().mean())   # mean of True/False = % present
    .round(4)                            # keep enough precision
)

##############################################################
# 2 · Optional population-weighted coverage
##############################################################
if pop_counts:                           # -------- weighted ----------
    # sample coverage inside each (type,country)
    cov_tc = (
        df
        .groupby(["type","classifications_countryCode"])[value_cols]
        .apply(lambda g: g.notna().mean())
    )

    # put sample estimates & weights in one frame
    cov_tc = cov_tc.reset_index()
    cov_tc["N_tc"] = cov_tc.apply(
        lambda r: pop_counts.get((r["type"], r["classifications_countryCode"]), 0),
        axis=1
    )

    # weighted coverage per type
    weighted = []
    for t, g in cov_tc.groupby("type"):
        w_sum = g["N_tc"].sum()
        weights = g["N_tc"] / w_sum
        weighted.append(
            pd.Series(
                (g[value_cols].T @ weights).round(4),   # Σ w p̂
                name=t
            )
        )
    coverage_weighted = pd.DataFrame(weighted)
else:                                    # -------- no weights ----------
    coverage_weighted = pd.DataFrame()   # empty placeholder

##############################################################
# 3 · Long (tidy) version – handy for BI tools
##############################################################
coverage_long = (
    coverage_wide
    .reset_index()
    .melt(id_vars="type", var_name="field", value_name="coverage")
)
if not coverage_weighted.empty:
    coverage_long_w = (
        coverage_weighted
        .reset_index()
        .melt(id_vars="type", var_name="field", value_name="coverage_weighted")
    )
    coverage_long = coverage_long.merge(coverage_long_w,
                                        on=["type","field"], how="left")

##############################################################
# 4 · Ancillary tables: sample sizes per (type,country)
##############################################################
sample_sizes = (
    df.groupby(["type","classifications_countryCode"])
      .size()
      .reset_index(name="sample_rows")
)

##############################################################
# 5 · Export to Excel with nice formatting
##############################################################
out = Path("field_dictionary_report.xlsx")
with pd.ExcelWriter(out, engine="xlsxwriter") as xls:
    # wide tables
    coverage_wide.to_excel(xls, sheet_name="Coverage_Sample", float_format="0.0%")
    if not coverage_weighted.empty:
        coverage_weighted.to_excel(xls, sheet_name="Coverage_Weighted",
                                   float_format="0.0%")

    # long / tidy
    coverage_long.to_excel(xls, sheet_name="Coverage_Long", index=False,
                           float_format="0.0%")

    # supporting info
    sample_sizes.to_excel(xls, sheet_name="Sample_Sizes", index=False)

    # ----- light formatting for the main sheet -----
    wb  = xls.book
    pct = wb.add_format({"num_format": "0.0%", "align": "center"})
    hdr = wb.add_format({"bold": True, "bg_color": "#DDDDDD", "align": "center"})

    for sheet in ["Coverage_Sample", "Coverage_Weighted"]:
        if sheet not in xls.sheets:
            continue
        ws = xls.sheets[sheet]
        ws.freeze_panes(1, 1)
        ws.set_column(0, 0, 18, None)                     # type column
        ws.set_row(0, None, hdr)
        # set % format for every data column
        for col in range(1, coverage_wide.shape[1] + 1):
            ws.set_column(col, col, 12, pct)

print(f"✔  Report written to {out.resolve()}")
