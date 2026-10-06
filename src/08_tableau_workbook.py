"""
STEP 08 (optional) - Build the packaged Tableau workbook from the step-07 extracts.

WHY THIS APPROACH
- Building the dashboard by hand takes about 45 minutes (docs/tableau_guide.md) and
  drifts from the data every time the pipeline reruns. Writing the workbook from code
  keeps the dashboard reproducible: rerun the pipeline, rerun this step, republish.
- Tableau Public only accepts extracts, so each CSV is converted to a .hyper file
  with Tableau's Hyper API and packaged with the workbook XML into one .twbx.

WHAT YOU GET
- Six dashboards (Overview, Brands, Geography, Prescribers, Forecast, Targeting) and a
  story, "GLP-1 Market Story", whose caption buttons switch between them.
- Quick filters: year (brand share), brand (forecast), segment / state / top brand
  (target list).

Usage:
    pip install tableauhyperapi
    python src/08_tableau_workbook.py      # -> outputs/tableau/glp1_dashboard.twbx
Then open the .twbx in Tableau Public and use File > Save to Tableau Public.
"""
from xml.sax.saxutils import quoteattr, escape

from config import TABLEAU_DIR

DATA_DIR = TABLEAU_DIR
OUT = DATA_DIR / "glp1_dashboard.twbx"
BUILD = OUT.parent / "_twbx_build"
CSV_DIR_IN_PKG = "Data/tableau"
EXTRACT_DIR_IN_PKG = "Data/Extracts"

q = quoteattr

CLAIMS_FMT = "n#,##0,,.0M;-#,##0,,.0M"

# ---------------------------------------------------------------- data sources
# (field, datatype, role, type, extra attrs)
SOURCES = {
    "brand": ("1_market_by_brand_year", [
        ("Year", "integer", "dimension", "ordinal", {}),
        ("Brand", "string", "dimension", "nominal", {}),
        ("Molecule", "string", "dimension", "nominal", {}),
        ("Manufacturer", "string", "dimension", "nominal", {}),
        ("Claims", "integer", "measure", "quantitative", {"default-format": CLAIMS_FMT}),
        ("Gross Drug Cost", "real", "measure", "quantitative", {"default-format": 'c"$"#,##0'}),
        ("Prescribers", "integer", "measure", "quantitative", {"default-format": "n#,##0"}),
        ("Beneficiaries (lower bound)", "real", "measure", "quantitative", {"default-format": "n#,##0"}),
        ("Cost per Claim", "real", "measure", "quantitative", {"default-format": 'c"$"#,##0'}),
        ("Claim Share", "real", "measure", "quantitative", {"default-format": "p0%"}),
        ("Claims YoY", "real", "measure", "quantitative", {"default-format": "p0%"}),
    ]),
    "state": ("2_market_by_state", [
        ("State", "string", "dimension", "nominal", {"semantic-role": "[State].[Name]"}),
        ("Claims", "integer", "measure", "quantitative", {"default-format": CLAIMS_FMT}),
        ("Gross Drug Cost", "real", "measure", "quantitative", {"default-format": 'c"$"#,##0'}),
        ("Prescribers", "integer", "measure", "quantitative", {"default-format": "n#,##0"}),
        ("Cost per Claim", "real", "measure", "quantitative", {"default-format": 'c"$"#,##0'}),
        ("Claims YoY", "real", "measure", "quantitative", {"default-format": "p0%"}),
        ("Claims per Prescriber", "real", "measure", "quantitative", {"default-format": "n#,##0"}),
        ("Claim Share", "real", "measure", "quantitative", {"default-format": "p0.0%"}),
        ("Emerging Prescribers", "integer", "measure", "quantitative", {"default-format": "n#,##0"}),
        ("High-value Prescribers", "integer", "measure", "quantitative", {"default-format": "n#,##0"}),
        ("Low-adopter Prescribers", "integer", "measure", "quantitative", {"default-format": "n#,##0"}),
        ("Claims (Emerging)", "integer", "measure", "quantitative", {"default-format": "n#,##0"}),
        ("Claims (High-value)", "integer", "measure", "quantitative", {"default-format": "n#,##0"}),
        ("Claims (Low-adopter)", "integer", "measure", "quantitative", {"default-format": "n#,##0"}),
    ]),
    "spec": ("3_market_by_specialty", [
        ("Specialty", "string", "dimension", "nominal", {}),
        ("Claims", "integer", "measure", "quantitative", {"default-format": CLAIMS_FMT}),
        ("Gross Drug Cost", "real", "measure", "quantitative", {"default-format": 'c"$"#,##0'}),
        ("Prescribers", "integer", "measure", "quantitative", {"default-format": "n#,##0"}),
        ("Cost per Claim", "real", "measure", "quantitative", {"default-format": 'c"$"#,##0'}),
        ("Claims per Prescriber", "real", "measure", "quantitative", {"default-format": "n#,##0"}),
        ("Claim Share", "real", "measure", "quantitative", {"default-format": "p0.0%"}),
    ]),
    "seg": ("4_prescriber_segments", [
        ("NPI", "string", "dimension", "nominal", {}),
        ("Claims (latest yr)", "integer", "measure", "quantitative", {"default-format": "n#,##0"}),
        ("Claims (prior yr)", "integer", "measure", "quantitative", {"default-format": "n#,##0"}),
        ("Claims YoY", "real", "measure", "quantitative", {"default-format": "p0%"}),
        ("New Prescriber", "boolean", "dimension", "nominal", {}),
        ("City", "string", "dimension", "nominal", {}),
        ("State", "string", "dimension", "nominal", {"semantic-role": "[State].[Name]"}),
        ("Specialty", "string", "dimension", "nominal", {}),
        ("Top Brand", "string", "dimension", "nominal", {}),
        ("Novo Nordisk Share", "real", "measure", "quantitative", {"default-format": "p0%"}),
        ("Eli Lilly Share", "real", "measure", "quantitative", {"default-format": "p0%"}),
        ("Gross Drug Cost (latest yr)", "real", "measure", "quantitative", {"default-format": 'c"$"#,##0'}),
        ("Segment", "string", "dimension", "nominal", {}),
        ("Prescriber", "string", "dimension", "nominal", {}),
    ]),
    "fc": ("5_forecast", [
        ("Brand", "string", "dimension", "nominal", {}),
        ("Molecule", "string", "dimension", "nominal", {}),
        ("Year", "integer", "dimension", "ordinal", {}),
        ("Scenario", "string", "dimension", "nominal", {}),
        ("Claims", "real", "measure", "quantitative", {"default-format": CLAIMS_FMT}),
    ]),
}


BRAND_COLORS = {
    "Ozempic": "#2a78d6", "Rybelsus": "#7fb0ea", "Wegovy": "#1e4f8f", "Mounjaro": "#eb6834",
    "Zepbound": "#f4a582", "Trulicity": "#1baf7a", "Victoza": "#eda100", "Saxenda": "#f5c85c",
    "Generic Liraglutide": "#c9a227", "Byetta": "#e87ba4", "Bydureon": "#f2b5cc", "Bydureon Bcise": "#c2508a"}
DS_COLORS = {
    "brand": [("Brand", BRAND_COLORS)],
    "seg": [("Segment", {"High-value": "#2a78d6", "Emerging": "#eb6834", "Low-adopter": "#b4b2a9"}),
            ("Top Brand", BRAND_COLORS)],
    "fc": [("Scenario", {"Actual": "#3d3d3a", "Base": "#2a78d6", "High": "#9ec5f0", "Low": "#9ec5f0"}),
           ("Brand", BRAND_COLORS)],
}


def ds_name(key):
    return f"federated.{key}"


def field(key, name):
    for f in SOURCES[key][1]:
        if f[0] == name:
            return f
    raise KeyError((key, name))


def col_xml(f, indent):
    name, dtype, role, typ, extra = f
    attrs = {"datatype": dtype, "name": f"[{name}]", "role": role, "type": typ, **extra}
    return indent + "<column " + " ".join(f"{k}={q(v)}" for k, v in sorted(attrs.items())) + " />"


def datasource_xml(key):
    caption, fields = SOURCES[key]
    lines = [
        f"    <datasource caption={q(caption)} inline='true' name={q(ds_name(key))} version='18.1'>",
        "      <connection class='federated'>",
        "        <named-connections>",
        f"          <named-connection caption={q(caption)} name={q('textscan.' + key)}>",
        f"            <connection class='textscan' directory={q(CSV_DIR_IN_PKG)} filename={q(caption + '.csv')} password='' server='' />",
        "          </named-connection>",
        "        </named-connections>",
        f"        <relation connection={q('textscan.' + key)} name={q(caption + '.csv')} table={q('[' + caption + '#csv]')} type='table'>",
        "          <columns character-set='UTF-8' header='yes' locale='en_US' separator=','>",
    ]
    for i, (name, dtype, *_ ) in enumerate(fields):
        lines.append(f"            <column datatype={q(dtype)} name={q(name)} ordinal={q(str(i))} />")
    lines += [
        "          </columns>",
        "        </relation>",
        "      </connection>",
        "      <aliases enabled='yes' />",
    ]
    for f in fields:
        lines.append(col_xml(f, "      "))
    lines += [
        "      <column datatype='integer' name='[Number of Records]' role='measure' type='quantitative' user:auto-column='numrec'>",
        "        <calculation class='tableau' formula='1' />",
        "      </column>",
    ]
    for fname, _ in DS_COLORS.get(key, []):
        lines.append(f"      <column-instance column={q('[' + fname + ']')} derivation='None' name={q('[none:' + fname + ':nk]')} pivot='key' type='nominal' />")
    lines += [
        "      <extract count='-1' enabled='true' units='records'>",
        f"        <connection access_mode='readonly' authentication='auth-none' author-locale='en_US' class='hyper' dbname={q(EXTRACT_DIR_IN_PKG + '/' + caption + '.hyper')} default-settings='yes' schema='Extract' sslmode='' tablename='Extract' username='tableau_internal_user'>",
        "          <relation name='Extract' table='[Extract].[Extract]' type='table' />",
        "          <refresh increment-key='' incremental-updates='false' />",
        "        </connection>",
        "      </extract>",
        "      <layout dim-ordering='alphabetic' dim-percentage='0.5' measure-ordering='alphabetic' measure-percentage='0.4' show-structure='true' />",
    ]
    if key in DS_COLORS:
        lines.append("      <style>")
        for fname, mapping in DS_COLORS[key]:
            lines.append("        " + color_map(f"[none:{fname}:nk]", mapping))
        lines.append("      </style>")
    lines += [
        "      <semantic-values>",
        "        <semantic-value key='[Country].[Name]' value='&quot;United States&quot;' />",
        "      </semantic-values>",
        "    </datasource>",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------- worksheets
DERIV = {"none": ("None", None), "sum": ("Sum", "qk"), "ctd": ("CountD", "qk")}


def inst(kind, fname, ftype):
    """Column-instance name, e.g. [sum:Claims:qk], [none:Year:ok], [none:Brand:nk]."""
    if kind == "none":
        suffix = {"nominal": "nk", "ordinal": "ok", "quantitative": "qk"}[ftype]
    else:
        suffix = "qk"
    return f"[{kind}:{fname}:{suffix}]"


class Sheet:
    def __init__(self, name, key, mark):
        self.name, self.key, self.mark = name, key, mark
        self.instances = {}  # inst name -> xml
        self.rows, self.cols = [], []
        self.encodings = []
        self.filters = []
        self.sorts = []
        self.slices = []
        self.styles = []
        self.title = name
        self.is_map = mark == "Multipolygon"
        self.label_fields = None

    def use(self, kind, fname, as_type=None):
        f = field(self.key, fname)
        ftype = as_type or (f[3] if kind == "none" else "quantitative")
        name = inst(kind, fname, ftype)
        deriv = DERIV[kind][0]
        self.instances[name] = (f"<column-instance column={q('[' + fname + ']')} derivation={q(deriv)} "
                                f"name={q(name)} pivot='key' type={q(ftype)} />")
        self.deps = getattr(self, "deps", {})
        self.deps[fname] = f
        return f"[{ds_name(self.key)}].{name}"

    def ref(self, raw):
        return f"[{ds_name(self.key)}].{raw}"

    def xml(self):
        d = ds_name(self.key)
        caption = SOURCES[self.key][0]
        out = [f"    <worksheet name={q(self.name)}>",
               "      <layout-options>",
               f"        <title><formatted-text><run bold='true' fontcolor='#1f2a44' fontsize='12'>{escape(self.title)}</run></formatted-text></title>",
               "      </layout-options>",
               "      <table>",
               "        <view>",
               "          <datasources>",
               f"            <datasource caption={q(caption)} name={q(d)} />",
               "          </datasources>"]
        if self.is_map:
            out += ["          <mapsources>", "            <mapsource name='Tableau' />", "          </mapsources>"]
        out += [
               f"          <datasource-dependencies datasource={q(d)}>"]
        for fname, f in sorted(self.deps.items()):
            out.append(col_xml(f, "            "))
        for name in sorted(self.instances):
            out.append("            " + self.instances[name])
        out.append("          </datasource-dependencies>")
        out += ["          " + x for x in self.filters]
        out += ["          " + x for x in self.sorts]
        if self.slices:
            out.append("          <slices>")
            out += [f"            <column>{escape(s)}</column>" for s in self.slices]
            out.append("          </slices>")
        out += ["          <aggregation value='true' />",
                "        </view>"]
        if self.is_map:
            self.styles.append("<style-rule element='map'><format attr='washout' value='0.0' /><format attr='map-style' value='light' /></style-rule>")
        if self.styles:
            out.append("        <style>")
            out += ["          " + x for x in self.styles]
            out.append("        </style>")
        else:
            out.append("        <style />")
        out += ["        <panes>",
                "          <pane selection-relaxation-option='selection-relaxation-allow'>",
                "            <view>",
                "              <breakdown value='auto' />",
                "            </view>",
                f"            <mark class={q(self.mark)} />"]
        if self.encodings:
            out.append("            <encodings>")
            out += [f"              <{tag} column={q(c)} />" for tag, c in self.encodings]
            out.append("            </encodings>")
            if any(tag == "text" for tag, _ in self.encodings) and self.mark != "Text":
                out.append("            <style><style-rule element='mark'><format attr='mark-labels-show' value='true' /></style-rule></style>")
        out += ["          </pane>",
                "        </panes>",
                f"        <rows>{escape(' / '.join(self.rows))}</rows>",
                f"        <cols>{escape(' / '.join(self.cols))}</cols>",
                "      </table>",
                "    </worksheet>"]
        return "\n".join(out)


def member_filter(col, level, member):
    return (f"<filter class='categorical' column={q(col)}>"
            f"<groupfilter function='member' level={q(level)} member={q(member)} "
            f"user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' />"
            f"</filter>")


def all_filter(col, level):
    return (f"<filter class='categorical' column={q(col)}>"
            f"<groupfilter function='level-members' level={q(level)} user:ui-enumeration='all' user:ui-marker='enumerate' />"
            f"</filter>")


def top_filter(col, level, n, expr):
    return (f"<filter class='categorical' column={q(col)}>"
            f"<groupfilter count={q(str(n))} end='top' function='end' units='records' user:ui-marker='end' user:ui-top-by-field='true'>"
            f"<groupfilter direction='DESC' expression={q(expr)} function='order' user:ui-marker='order'>"
            f"<groupfilter function='level-members' level={q(level)} user:ui-enumeration='all' user:ui-marker='enumerate' />"
            f"</groupfilter></groupfilter></filter>")


US_STATES = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']


def union_filter(col, level, members):
    inner = "".join(f"<groupfilter function='member' level={q(level)} member={q(chr(34) + m + chr(34))} />" for m in members)
    return (f"<filter class='categorical' column={q(col)}>"
            f"<groupfilter function='union' user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate'>"
            f"{inner}</groupfilter></filter>")


def sort(col, using):
    return f"<sort class='computed' column={q(col)} direction='DESC' using={q(using)} />"


def color_map(field_ref, mapping):
    s = f"<style-rule element='mark'><encoding attr='color' field={q(field_ref)} type='palette'>"
    for member, color in mapping.items():
        s += f"<map to={q(color)}><bucket>&quot;{escape(member)}&quot;</bucket></map>"
    return s + "</encoding></style-rule>"


sheets = []

# 1. Brand trend (top 6 brands)
s = Sheet("Claims by Brand", "brand", "Line")
s.title = "GLP-1 Part D claims by brand, 2020-2024"
s.cols = [s.use("none", "Year")]
s.rows = [s.use("sum", "Claims")]
brand = s.use("none", "Brand")
s.encodings = [("color", brand), ("text", brand), ("tooltip", s.use("sum", "Claims YoY"))]
s.filters = [top_filter(brand, "[none:Brand:nk]", 6, "SUM([Claims])")]
sheets.append(s)

# 2. Brand share for a chosen year (Year quick filter, default 2024)
s = Sheet("Brand Share", "brand", "Bar")
s.title = "Share of GLP-1 claims by brand"
year = s.use("none", "Year")
brand = s.use("none", "Brand")
share = s.use("sum", "Claim Share")
s.rows, s.cols = [brand], [share]
s.filters = [member_filter(year, "[none:Year:ok]", "2024")]
s.sorts = [sort(brand, share)]
s.slices = [year]
s.encodings = [("color", brand), ("text", share), ("tooltip", s.use("sum", "Claims")),
               ("tooltip", s.use("sum", "Claims YoY"))]
sheets.append(s)

# 3. State map
s = Sheet("Claims by State", "state", "Multipolygon")
s.title = "Where the volume is: claims by state (latest year)"
st = s.use("none", "State")
claims = s.use("sum", "Claims")
s.rows, s.cols = [s.ref("[Latitude (generated)]")], [s.ref("[Longitude (generated)]")]
s.filters = [union_filter(st, "[none:State:nk]", [x for x in US_STATES if x not in ("AK", "HI")])]
s.encodings = [("color", claims), ("lod", st), ("tooltip", s.use("sum", "Claims YoY")),
               ("tooltip", s.use("sum", "Prescribers")), ("tooltip", s.use("sum", "High-value Prescribers")),
               ("tooltip", s.use("sum", "Emerging Prescribers")), ("geometry", s.ref("[Geometry (generated)]"))]
sheets.append(s)

# 4. Top 10 states bar (complements the map)
s = Sheet("Top States", "state", "Bar")
s.title = "Top 10 states by claims"
st = s.use("none", "State")
claims = s.use("sum", "Claims")
s.rows, s.cols = [st], [claims]
s.filters = [top_filter(st, "[none:State:nk]", 10, "SUM([Claims])")]
s.sorts = [sort(st, claims)]
s.encodings = [("text", claims), ("tooltip", s.use("sum", "Claims YoY"))]
sheets.append(s)

# 5. Specialty top 10
s = Sheet("Top 10 Specialties", "spec", "Bar")
s.title = "Top 10 prescriber specialties by claims"
sp = s.use("none", "Specialty")
claims = s.use("sum", "Claims")
s.rows, s.cols = [sp], [claims]
s.filters = [top_filter(sp, "[none:Specialty:nk]", 10, "SUM([Claims])")]
s.sorts = [sort(sp, claims)]
s.encodings = [("text", claims), ("tooltip", s.use("sum", "Claims per Prescriber")),
               ("tooltip", s.use("sum", "Prescribers"))]
sheets.append(s)

# 6. Segments
s = Sheet("Prescriber Segments", "seg", "Bar")
s.title = "Prescriber segments: claims in the latest year"
seg = s.use("none", "Segment")
claims = s.use("sum", "Claims (latest yr)")
s.rows, s.cols = [seg], [claims]
s.sorts = [sort(seg, claims)]
s.encodings = [("color", seg), ("text", claims), ("tooltip", s.use("ctd", "NPI"))]
s.styles = [f"<style-rule element='cell'><format attr='text-format' field={q(claims)} value={q(CLAIMS_FMT)} /></style-rule>"]
sheets.append(s)

# 7. Forecast (Brand quick filter)
s = Sheet("Forecast 2025", "fc", "Line")
s.title = "2025 claims forecast: base, high and low scenarios"
yr = s.use("none", "Year")
scen = s.use("none", "Scenario")
brand = s.use("none", "Brand")
s.cols, s.rows = [yr], [s.use("sum", "Claims")]
s.encodings = [("color", scen), ("text", scen)]
s.filters = [all_filter(brand, "[none:Brand:nk]")]
s.slices = [brand]
sheets.append(s)

# 7b. Forecast by brand (2025 base case with low-high range in the tooltip)
s = Sheet("Forecast by Brand", "fc", "Bar")
s.title = "2025 base-case claims by brand"
yr = s.use("none", "Year")
scen = s.use("none", "Scenario")
brand = s.use("none", "Brand")
claims = s.use("sum", "Claims")
s.rows, s.cols = [brand], [claims]
s.filters = [member_filter(yr, "[none:Year:ok]", "2025"), member_filter(scen, "[none:Scenario:nk]", '"Base"'),
             top_filter(brand, "[none:Brand:nk]", 6, "SUM([Claims])")]
s.sorts = [sort(brand, claims)]
s.slices = [yr, scen]
s.encodings = [("color", brand), ("text", claims)]
sheets.append(s)

# 8. Target list
s = Sheet("Target List", "seg", "Text")
s.title = "Prescriber target list (sorted by latest-year claims)"
seg = s.use("none", "Segment")
st = s.use("none", "State")
claims = s.use("sum", "Claims (latest yr)")
pres = s.use("none", "Prescriber")
s.rows = [pres, s.use("none", "Specialty"), s.use("none", "City"), st, s.use("none", "Top Brand")]
s.cols = []
s.encodings = [("text", claims)]
tb = s.use("none", "Top Brand")
s.filters = [member_filter(seg, "[none:Segment:nk]", '"High-value"'), all_filter(st, "[none:State:nk]"),
             all_filter(tb, "[none:Top Brand:nk]")]
s.sorts = [sort(pres, claims)]
s.slices = [seg, st, tb]
sheets.append(s)

# ---------------------------------------------------------------- dashboards
U = 100000
NAVY, MUTED_TXT, TILE_BG = "#1f2a44", "#52514e", "#f2f5fa"


def zone(zid, x, y, w, h, **kw):
    attrs = {"h": str(h), "id": str(zid), **kw, "w": str(w), "x": str(x), "y": str(y)}
    return "<zone " + " ".join(f"{k}={q(v)}" for k, v in attrs.items()) + " />"


def text_zone(zid, x, y, w, h, runs):
    body = "".join(f"<run{(' ' + a) if a else ''}>{escape(t)}</run>" for t, a in runs)
    return (f"<zone h={q(str(h))} id={q(str(zid))} type-v2='text' w={q(str(w))} x={q(str(x))} y={q(str(y))}>"
            f"<formatted-text>{body}</formatted-text></zone>")


def filter_zone(zid, x, y, w, h, sheet, key, fname, mode):
    return zone(zid, x, y, w, h, mode=mode, name=sheet, param=f"[{ds_name(key)}].[none:{fname}:{'ok' if fname == 'Year' else 'nk'}]",
                **{"type-v2": "filter"})


def kpi(zid, x, y, w, h, value, label):
    return text_zone(zid, x, y, w, h, [(value + "\n", f"bold='true' fontcolor='{NAVY}' fontsize='22'"),
                                       (label, f"fontcolor='{MUTED_TXT}' fontsize='10'")])


SOURCE_NOTE = ("Source: CMS Medicare Part D Prescribers by Provider and Drug, 2020-2024. Rows with fewer than 11 claims are "
               "suppressed by CMS. Drug cost is gross, before rebates. Medicare only (65+ and disabled).")


class Dash:
    def __init__(self, name, title, subtitle, w=1200, h=780):
        self.name, self.w, self.h = name, w, h
        self.zones, self.sheets, self.tiles = [], [], []
        self.next_id = 2
        self.add_text(0, 0, U, 7000, [(title, f"bold='true' fontcolor='{NAVY}' fontsize='18'")])
        self.add_text(0, 7000, U, 4500, [(subtitle, f"fontcolor='{MUTED_TXT}' fontsize='10'")])

    def nid(self):
        self.next_id += 1
        return self.next_id

    def add_text(self, x, y, w, h, runs):
        self.zones.append(text_zone(self.nid(), x, y, w, h, runs))

    def add_sheet(self, name, x, y, w, h):
        self.zones.append(zone(self.nid(), x, y, w, h, name=name))
        self.sheets.append(name)

    def add_filter(self, x, y, w, h, sheet, key, fname, mode):
        self.zones.append(filter_zone(self.nid(), x, y, w, h, sheet, key, fname, mode))

    def add_kpi(self, x, y, w, h, value, label):
        zid = self.nid()
        self.zones.append(kpi(zid, x, y, w, h, value, label))
        self.tiles.append(zid)

    def xml(self):
        inner = "\n".join("          " + z for z in self.zones)
        style = ""
        if self.tiles:
            fmts = "".join(f"<format attr='background-color' id='dash-zone_{t}' value='{TILE_BG}' />"
                           f"<format attr='border-style' id='dash-zone_{t}' value='solid' />"
                           f"<format attr='border-color' id='dash-zone_{t}' value='#d9e1ec' />" for t in self.tiles)
            style = f"<style-rule element='dash-container'>{fmts}</style-rule>"
        return (f"    <dashboard name={q(self.name)}>\n"
                f"      <style>{style}</style>\n"
                f"      <size maxheight='{self.h}' maxwidth='{self.w}' minheight='{self.h}' minwidth='{self.w}' />\n"
                "      <zones>\n"
                f"        <zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>\n{inner}\n"
                "        </zone>\n"
                "      </zones>\n"
                "    </dashboard>")


dashes = []

# Overview: KPI tiles + key charts
d = Dash("Overview", "GLP-1 Market Opportunity, Segmentation & Forecast (US Medicare Part D)", SOURCE_NOTE, h=800)
kpis = [("19.6M", "GLP-1 claims in 2024"), ("$24.6B", "gross drug cost in 2024"), ("+39%", "claims growth vs 2023"),
        ("59%", "of claims from the top 20% of prescribers"), ("27.5M", "claims forecast for 2025 (base)")]
for i, (v, l) in enumerate(kpis):
    d.add_kpi(i * 20000 + 500, 12500, 19000, 11000, v, l)
d.add_sheet("Claims by Brand", 0, 24500, 50000, 37500)
d.add_sheet("Brand Share", 50000, 24500, 50000, 37500)
d.add_sheet("Prescriber Segments", 0, 62000, 50000, 38000)
d.add_sheet("Forecast 2025", 50000, 62000, 50000, 38000)
dashes.append(d)

d = Dash("Brands", "Market by brand: Mounjaro is taking most of the new volume",
         "Ozempic still leads with 51% of 2024 claims; Mounjaro reached 24% in its second full year while Trulicity fell 21%. Pick a year to compare shares.")
d.add_sheet("Claims by Brand", 0, 12000, 55000, 88000)
d.add_filter(56000, 12000, 20000, 7500, "Brand Share", "brand", "Year", "dropdown")
d.add_sheet("Brand Share", 55000, 19500, 45000, 80500)
dashes.append(d)

d = Dash("Geography", "Market by state: volume is concentrated in the largest states",
         "Texas and California each hold about 8% of claims. Hover a state for growth and prescriber counts (map shows the 48 contiguous states and DC).")
d.add_sheet("Claims by State", 0, 12000, 62000, 88000)
d.add_sheet("Top States", 62000, 12000, 38000, 55000)
zid = d.nid()
d.zones.append(text_zone(zid, 63000, 69000, 36000, 29000, [
    ("California is the biggest gap\n", f"bold='true' fontcolor='{NAVY}' fontsize='13'"),
    ("2nd-largest state (8.4% of claims, +42% growth), but Mounjaro holds only 15% of its GLP-1 claims vs 24% nationally. "
     "Matching the national share would add about 140K claims. Pennsylvania (19%), Illinois (21%) and New York (21%) show smaller versions of the same gap.",
     f"fontcolor='{MUTED_TXT}' fontsize='10'")]))
d.tiles.append(zid)
dashes.append(d)

d = Dash("Prescribers", "Prescriber segmentation: a small group drives the market",
         "Prescribers segmented by claim volume and year-on-year growth. High-value = top 20% by volume (59% of claims); Emerging = mid-volume and growing faster than the market; Low-adopter = the rest. Primary care (FP, IM, NP, PA) writes 82% of claims.")
d.add_sheet("Prescriber Segments", 0, 12000, 45000, 88000)
d.add_sheet("Top 10 Specialties", 45000, 12000, 55000, 88000)
dashes.append(d)

d = Dash("Forecast", "2025 forecast by brand: 27.5M claims in the base case",
         "Base = lower of 3-year CAGR and latest YoY per molecule (Mounjaro repeats last year's absolute gain); high/low = +/-10 points. Dark = actual, blue = base, light blue = high/low.")
d.add_sheet("Forecast 2025", 0, 12000, 50000, 88000)
d.add_filter(50000, 12000, 15000, 50000, "Forecast 2025", "fc", "Brand", "checklist")
d.add_sheet("Forecast by Brand", 65000, 12000, 35000, 55000)
zid = d.nid()
d.zones.append(text_zone(zid, 66000, 69000, 33000, 29000, [
    ("What drives the forecast\n", f"bold='true' fontcolor='{NAVY}' fontsize='13'"),
    ("Ozempic 15.1M (14.1M-16.1M), Mounjaro 7.9M (7.4M-8.3M), Trulicity 3.0M (2.6M-3.4M). "
     "Mounjaro rises from 24% to about 29% of claims while Trulicity falls from 19% to about 11%. "
     "Brand forecasts split each molecule by its 2024 brand shares and add back to the 27.5M total.",
     f"fontcolor='{MUTED_TXT}' fontsize='10'")]))
d.tiles.append(zid)
dashes.append(d)

d = Dash("Targeting", "So what: where the Mounjaro sales force should focus",
         "Recommendations from the brand-team memo (docs/memo.md). Use the filters to build a call list for each priority.")
d.add_sheet("Target List", 0, 12000, 64000, 88000)
d.add_filter(65000, 12000, 17000, 15000, "Target List", "seg", "Segment", "radiolist")
d.add_filter(83000, 12000, 17000, 7500, "Target List", "seg", "State", "checkdropdown")
d.add_filter(83000, 19500, 17000, 7500, "Target List", "seg", "Top Brand", "checkdropdown")
SO_WHAT = [
    ("So what for the brand team\n", f"bold='true' fontcolor='{NAVY}' fontsize='13'"),
    ("1. Convert high-value Ozempic loyalists. ", f"bold='true' fontcolor='{NAVY}' fontsize='10'"),
    ("27,407 of 40,232 high-value prescribers write mostly Ozempic. Filter: High-value + Top Brand = Ozempic.\n\n", f"fontcolor='{MUTED_TXT}' fontsize='10'"),
    ("2. Keep Trulicity patients inside Lilly. ", f"bold='true' fontcolor='{NAVY}' fontsize='10'"),
    ("Trulicity lost about 1M claims in 2024; 8,881 high-value and emerging prescribers still write mostly Trulicity.\n\n", f"fontcolor='{MUTED_TXT}' fontsize='10'"),
    ("3. Fix the California gap. ", f"bold='true' fontcolor='{NAVY}' fontsize='10'"),
    ("California holds 8.4% of claims but Mounjaro's share there is 15% vs 24% nationally: about 140K claims of upside.\n\n", f"fontcolor='{MUTED_TXT}' fontsize='10'"),
    ("4. Build the emerging pipeline. ", f"bold='true' fontcolor='{NAVY}' fontsize='10'"),
    ("37,422 emerging prescribers are growing faster than the market; 12,619 write no visible Mounjaro.\n\n", f"fontcolor='{MUTED_TXT}' fontsize='10'"),
    ("5. Use endocrinologists for influence, not reach. ", f"bold='true' fontcolor='{NAVY}' fontsize='10'"),
    ("They write 4-5x more per head but only 13% of claims.", f"fontcolor='{MUTED_TXT}' fontsize='10'"),
]
zid = d.nid()
d.zones.append(text_zone(zid, 65000, 28500, 35000, 71500, SO_WHAT))
d.tiles.append(zid)
dashes.append(d)

# Story: caption buttons switch between the focused dashboards
STORY = "GLP-1 Market Story"
points = [("Market sizing: 19.6M claims, $24.6B", "Overview"),
          ("By brand: Mounjaro takes new volume", "Brands"),
          ("By state: where the claims are", "Geography"),
          ("By specialty & segment: who drives volume", "Prescribers"),
          ("Forecast by brand: base, high, low", "Forecast"),
          ("So what: sales force targeting", "Targeting")]
sp_xml = "".join(f"<story-point caption={q(c)} captured-sheet={q(sh)} id='{i}' />" for i, (c, sh) in enumerate(points, 1))
story_xml = (f"    <dashboard name={q(STORY)} type='storyboard'>\n"
             f"      <layout-options><title><formatted-text><run bold='true' fontcolor='{NAVY}' fontsize='16'>GLP-1 Market Opportunity, Segmentation &amp; Forecast</run></formatted-text></title></layout-options>\n"
             "      <style><style-rule element='story-point-caption'><format attr='background-color' value='#e8eef7' /></style-rule></style>\n"
             "      <size maxheight='1060' maxwidth='1220' minheight='1060' minwidth='1220' />\n"
             "      <zones>\n"
             "        <zone h='100000' id='2' type-v2='layout-basic' w='100000' x='0' y='0'>\n"
             "          <zone h='100000' id='1' param='vert' removable='false' type-v2='layout-flow' w='100000' x='0' y='0'>\n"
             "            <zone h='5000' id='3' type-v2='title' w='100000' x='0' y='0' />\n"
             "            <zone fixed-size='90' h='9000' id='4' is-fixed='true' paired-zone-id='5' removable='false' type-v2='flipboard-nav' w='100000' x='0' y='5000' />\n"
             "            <zone h='86000' id='5' paired-zone-id='4' removable='false' type-v2='flipboard' w='100000' x='0' y='14000'>\n"
             f"              <flipboard active-id='1' nav-type='caption' show-nav-arrows='true'><story-points>{sp_xml}</story-points></flipboard>\n"
             "            </zone>\n"
             "          </zone>\n"
             "        </zone>\n"
             "      </zones>\n"
             "    </dashboard>")


def window_xml(name, cls, sheets_in=(), hidden=False):
    if cls == "dashboard":
        vps = "".join(f"<viewpoint name={q(n)} />" if n == "Target List"
                      else f"<viewpoint name={q(n)}><zoom type='entire-view' /></viewpoint>" for n in sheets_in)
        return (f"    <window class='dashboard' {'maximized' + chr(61) + chr(39) + 'true' + chr(39) + ' ' if not hidden else ''}name={q(name)}>\n"
                f"      <viewpoints>{vps}</viewpoints>\n      <active id='-1' />\n      <device-preview />\n    </window>")
    return (f"    <window class='worksheet' hidden='true' name={q(name)}>\n"
            "      <cards>\n"
            "        <edge name='left'><strip size='160'><card type='pages' /><card type='filters' /><card type='marks' /></strip></edge>\n"
            "        <edge name='top'><strip size='2147483647'><card type='columns' /></strip><strip size='2147483647'><card type='rows' /></strip><strip size='31'><card type='title' /></strip></edge>\n"
            "      </cards>\n"
            "    </window>")


xml = ["<?xml version='1.0' encoding='utf-8' ?>",
       "<workbook original-version='18.1' source-build='2018.1.0 (20181.18.0404.1916)' source-platform='mac' version='18.1' "
       "xmlns:user='http://www.tableausoftware.com/xml/user'>",
       "  <preferences>",
       "    <preference name='ui.encoding.shelf.height' value='24' />",
       "    <preference name='ui.shelf.height' value='26' />",
       "  </preferences>",
       "  <datasources>"]
xml += [datasource_xml(k) for k in SOURCES]
xml += ["  </datasources>", "  <mapsources>", "    <mapsource name='Tableau' />", "  </mapsources>", "  <worksheets>"]
xml += [s.xml() for s in sheets]
xml += ["  </worksheets>", "  <dashboards>"]
xml += [d.xml() for d in dashes]
xml += [story_xml, "  </dashboards>", "  <windows>"]
xml += [window_xml(s.name, "worksheet") for s in sheets]
xml += [window_xml(d.name, "dashboard", d.sheets) for d in dashes]
xml += [window_xml(STORY, "dashboard")]
xml += ["  </windows>", "</workbook>", ""]

# ---------------------------------------------------------------- package
import shutil, zipfile
import pandas as pd
from tableauhyperapi import (HyperProcess, Telemetry, Connection, CreateMode, TableDefinition,
                             SqlType, TableName, Inserter, NULLABLE)

if BUILD.exists():
    shutil.rmtree(BUILD)
(BUILD / CSV_DIR_IN_PKG).mkdir(parents=True)
(BUILD / EXTRACT_DIR_IN_PKG).mkdir(parents=True)
HTYPE = {"integer": SqlType.big_int(), "real": SqlType.double(), "string": SqlType.text(), "boolean": SqlType.bool()}
# Hyper writes its log into the temporary build folder, which is deleted below
with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU,
                  parameters={"log_dir": str(BUILD)}) as hyper:
    for key, (caption, fields) in SOURCES.items():
        src = DATA_DIR / f"{caption}.csv"
        shutil.copy(src, BUILD / CSV_DIR_IN_PKG / src.name)
        df = pd.read_csv(src, dtype={f[0]: str for f in fields if f[1] == "string"})
        table = TableDefinition(TableName("Extract", "Extract"),
                                [TableDefinition.Column(f[0], HTYPE[f[1]], NULLABLE) for f in fields])
        with Connection(hyper.endpoint, BUILD / EXTRACT_DIR_IN_PKG / f"{caption}.hyper",
                        CreateMode.CREATE_AND_REPLACE) as con:
            con.catalog.create_schema("Extract")
            con.catalog.create_table(table)
            rows = []
            for rec in df[[f[0] for f in fields]].itertuples(index=False):
                row = []
                for val, f in zip(rec, fields):
                    if pd.isna(val):
                        row.append(None)
                    elif f[1] == "integer":
                        row.append(int(val))
                    elif f[1] == "real":
                        row.append(float(val))
                    elif f[1] == "boolean":
                        row.append(bool(val))
                    else:
                        row.append(str(val))
                rows.append(row)
            with Inserter(con, table) as ins:
                ins.add_rows(rows)
                ins.execute()
        print(f"extract {caption}: {len(rows):,} rows")

twb_name = OUT.stem + ".twb"
(BUILD / twb_name).write_text("\n".join(xml), encoding="utf-8")
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(BUILD / twb_name, twb_name)
    for f in sorted((BUILD / "Data").rglob("*")):
        if f.is_file():
            z.write(f, f.relative_to(BUILD).as_posix())
shutil.rmtree(BUILD)
print(f"wrote {OUT} ({OUT.stat().st_size / 1e6:.1f} MB)")
