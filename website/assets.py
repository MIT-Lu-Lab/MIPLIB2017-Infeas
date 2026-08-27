"""The stylesheet and the client-side scripts, written out as two files."""

import hashlib

# The faces the stylesheet asks for, shipped with the site. build_site copies
# fonts/ into the output, so a build is self-contained and a reader loads
# nothing from a third party.
#
# These are subsets of IBM Plex, cut to the 191 glyphs the pages set, by
# scripts/subset_fonts.py. They are not named "IBM Plex": the OFL counts
# removing glyphs as a Modified Version, and the Reserved Font Name "Plex" may
# not be used for one. The stacks below still name IBM Plex after this family,
# which asks for an unmodified copy if the reader has one installed.
#
# The subset is not a font CDN's Latin one: the pages set U+2192, U+2193,
# U+2264 and U+2265, which that subset drops, so the arrows and the
# inequalities in every branch recipe used to fall back to whatever the reader
# happened to have installed. A test holds every character the pages set
# against what these files carry.
FONT_FAMILY = "Infeas"

FONT_FACES = (
    ("Mono", "Regular", 400), ("Mono", "Medium", 500), ("Mono", "SemiBold", 600),
    ("Sans", "Regular", 400), ("Sans", "Medium", 500), ("Sans", "SemiBold", 600),
    ("Serif", "Regular", 400), ("Serif", "SemiBold", 600),
)


def font_file(family: str, style: str) -> str:
    """The shipped file for one face, relative to fonts/."""
    return f"{FONT_FAMILY}{family}-{style}.woff2"


def font_face(up=""):
    """The @font-face rules, with paths relative to a page `up` levels down."""
    return "".join(
        f"@font-face{{font-family:'{FONT_FAMILY} {family}';font-style:normal;"
        f"font-weight:{weight};font-display:swap;"
        f"src:url({up}fonts/{font_file(family, style)}) format('woff2')}}"
        for family, style, weight in FONT_FACES)


STYLESHEET = """
/* One value per token, not three. The dark palette was written out twice, once
   under prefers-color-scheme and once under [data-theme="dark"], and the light
   one had to be repeated in the guard between them. light-dark() resolves
   against the used colour scheme, so a manual override is the scheme itself.
   Nothing sets data-theme today; the two lines below are what a toggle would
   need, instead of a third copy of the palette. */
:root{
  color-scheme:light dark;

  --paper:light-dark(#FAFAFB,#0F1116);
  --raise:light-dark(#FFFFFF,#161922);
  --ink:light-dark(#14161D,#E6E8EF);
  --muted:light-dark(#676C7C,#959BAC);
  --muted-strong:light-dark(#4E5361,#B2B8C7);
  --rule:light-dark(#DEE0E7,#272B37);
  --rule-soft:light-dark(#EBECF1,#1E222C);
  --primal:light-dark(#3B4CC0,#8B99EC);
  --primal-wash:light-dark(#EEF0FC,#1B1F35);
  --dual:light-dark(#B45309,#E0A458);
  --dual-wash:light-dark(#FBF1E5,#2A2015);
  --shared:light-dark(#166534,#6BD48F);
  --shared-wash:light-dark(#E8F3EB,#13251A);
  --on-view:light-dark(#FFFFFF,#0F1116);

  /* light-dark() takes a colour, and a shadow is a list, so the two colours in
     it are the tokens and the geometry is stated once */
  --shadow-near:light-dark(rgba(20,22,29,.05),rgba(0,0,0,.4));
  --shadow-far:light-dark(rgba(20,22,29,.25),rgba(0,0,0,.8));
  --shadow:0 1px 2px var(--shadow-near),0 8px 24px -16px var(--shadow-far);

  /* the top bar's height, which the sticky offsets below are measured from */
  --topbar-h:56px;

  /* One column width, shared by the top bar and the pages that fill it, so the
     wordmark sits over the heading below it and the bar does not jump sideways
     from page to page. The number is what the widest browse table needs: its
     columns come to 992px, and the facet rail, the gap and the page's padding
     add 272 more. The rest is slack, because a browser lays text out slightly
     wider than the font metrics add up to. Under this the table scrolls inside
     .table-wrap with its last column off-screen. The reading pages take a
     narrower column of their own inside the same bar. */
  --page:1320px;

  --f-serif:"Infeas Serif","IBM Plex Serif",Georgia,"Times New Roman",serif;
  --f-sans:"Infeas Sans","IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",
    Roboto,sans-serif;
  --f-mono:"Infeas Mono","IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,
    monospace;
}
:root[data-theme="light"]{color-scheme:light}
:root[data-theme="dark"]{color-scheme:dark}

/* min-width:0 below is on flex and grid items only. A grid or flex item's
   automatic minimum is its content's min-content, which is what kept the browse
   column from shrinking under the browse table and pushed the page sideways.
   On anything that is not such an item the property does nothing, and ten of
   them were doing nothing. */
*{box-sizing:border-box}
html,body{max-width:100%}
body{
  margin:0;
  background:var(--paper);
  color:var(--ink);
  font-family:var(--f-sans);
  font-size:15px;
  line-height:1.6;
  -webkit-font-smoothing:antialiased;
  overflow-x:clip;
}
a{color:inherit}

/* Blue names the primal half, orange the dual half, green what belongs to both.
   Every accent below resolves through --view, so a control takes the colour of
   the set it acts on instead of whichever the stylesheet reached for first. */
body{--view:var(--shared);--view-wash:var(--shared-wash)}
body[data-view="primal"]{--view:var(--primal);--view-wash:var(--primal-wash)}
body[data-view="dual"]{--view:var(--dual);--view-wash:var(--dual-wash)}
h1,h2,h3{font-family:var(--f-serif);text-wrap:balance;margin:0;font-weight:600;letter-spacing:-.01em}
.mono{font-family:var(--f-mono);font-variant-numeric:tabular-nums}
.num{font-family:var(--f-mono);font-variant-numeric:tabular-nums;text-align:right}
.sr-only{
  position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;
  clip:rect(0,0,0,0);white-space:nowrap;border:0;
}
html{scroll-padding-top:72px}
:focus-visible{outline:2px solid var(--view);outline-offset:2px;border-radius:2px}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}

/* ---------- chrome ---------- */
.topbar{
  position:sticky;top:0;z-index:20;
  background:var(--paper);
  background:color-mix(in srgb,var(--paper) 88%,transparent);
  backdrop-filter:blur(8px);
  border-bottom:1px solid var(--rule);
}
.skip-link{
  position:fixed;z-index:100;top:8px;left:8px;padding:8px 12px;border-radius:5px;
  background:var(--ink);color:var(--paper);font-weight:600;text-decoration:none;
  transform:translateY(calc(-100% - 16px));
}
.skip-link:focus{transform:none}
.topbar-inner{
  max-width:var(--page);margin:0 auto;padding:0 24px;
  height:var(--topbar-h);display:flex;align-items:center;gap:28px;min-width:0;
}
.wordmark{font-family:var(--f-mono);font-weight:600;font-size:14px;letter-spacing:.02em;text-decoration:none;white-space:nowrap}
.wordmark .dash{color:var(--muted)}
nav.top{display:flex;gap:2px;margin-left:auto;flex-wrap:wrap;min-width:0}
nav.top a{
  font:inherit;font-size:13.5px;color:var(--muted);text-decoration:none;
  background:none;border:0;cursor:pointer;
  padding:7px 11px;border-radius:5px;transition:color .12s,background .12s;
}
nav.top a:hover{color:var(--ink);background:var(--rule-soft)}
nav.top a[aria-current="page"]{color:var(--ink);font-weight:500}
/* both labels ship on every link that has two; only one is ever displayed */
.nav-short{display:none}
/* the duality hairline: which side of the pair you are looking at */
.hairline{height:2px;display:flex}
.hairline span{flex:1;background:var(--rule);transition:background .2s}
body[data-view="primal"] .hairline span:first-child{background:var(--primal)}
body[data-view="dual"] .hairline span:last-child{background:var(--dual)}

/* One line length for running text, owned by the column rather than restated by
   every block that wants one. A wide page caps a line; a narrow page already is
   the cap. The number is in rem, not ch, so one measure is one column: ch
   resolves against the element's own font, so the same 66ch handed each text
   size a different width, and every block needed its own opt-out of the cap on
   a narrow page. The citation note never got one, and wrapped short. */
main{--measure:34rem;width:100%;max-width:var(--page);margin:0 auto;padding:44px 24px 96px}
main.narrow{--measure:none;--page:900px}
.prose,.note,.cite-note,.masthead .sub,.browse-head .desc{
  max-width:var(--measure);overflow-wrap:break-word;
}
.prose p{margin:0 0 14px}
.muted{color:var(--muted)}
.note{font-size:13px;color:var(--muted);margin-top:26px}
.cite-note{font-size:13px;color:var(--muted);margin-top:12px}
.cite-note a,.hint a{color:var(--view);overflow-wrap:anywhere}

.eyebrow{
  font-family:var(--f-mono);font-size:11px;font-weight:500;
  letter-spacing:.09em;text-transform:uppercase;color:var(--muted);
}

/* ---------- home ---------- */
/* the following block owns the gap; the masthead adding its own stacked the two */
.masthead{display:flex;flex-direction:column;gap:14px}
.masthead + .pair{margin-top:32px}
.masthead + .section{margin-top:38px}
.masthead h1{font-size:40px;line-height:1.12}
.masthead .sub{font-size:18px;color:var(--muted);font-family:var(--f-serif)}
.masthead .sub a{color:var(--view);text-decoration:none;border-bottom:1px solid var(--rule)}
.masthead .sub a:hover{border-bottom-color:var(--view)}


/* The raised surface: a bordered, rounded panel on the page's ground. Five
   blocks carried these three declarations verbatim; each still adds its own
   padding, radius override or overflow below. */
.subset,.file,.table-wrap,.panel,.card{
  border:1px solid var(--rule);border-radius:8px;background:var(--raise);
}

/* intrinsic, so the pair holds two columns until the cards genuinely stop
   fitting rather than at whatever width the other grids happen to need */
.pair{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:18px;margin:34px 0}
.subset{
  padding:20px 22px 18px;display:flex;flex-direction:column;gap:11px;
  border-top:3px solid var(--accent);text-align:left;font:inherit;color:var(--ink);cursor:pointer;
  text-decoration:none;transition:box-shadow .14s,transform .14s;min-width:0;
}
.subset:hover{box-shadow:var(--shadow);transform:translateY(-1px)}
.subset.p{--accent:var(--primal)}
.subset.d{--accent:var(--dual)}
.subset h2,.subset h3{font-size:20px}
.subset .count{font-family:var(--f-mono);font-variant-numeric:tabular-nums;font-size:13px;color:var(--accent);font-weight:500}
.subset p{margin:0;font-size:14px;color:var(--muted);line-height:1.55}
.subset .go{font-size:13px;color:var(--accent);font-weight:500;margin-top:auto}

.section{margin-top:52px}
.section > h2{font-size:24px;margin-bottom:6px}
.section > .eyebrow{margin-bottom:10px}

/* file cards */
.files{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:16px;margin-top:18px}
.file{padding:16px 18px;min-width:0}
.file .fn{font-family:var(--f-mono);font-size:12.5px;color:var(--view);margin-bottom:9px;overflow-wrap:anywhere}
.file p{margin:0;font-size:13.5px;color:var(--muted);line-height:1.55}

.cite{
  margin-top:20px;border:1px solid var(--rule);border-left:3px solid var(--muted);
  border-radius:0 6px 6px 0;background:var(--raise);padding:15px 18px;
  font-family:var(--f-mono);font-size:12.5px;line-height:1.7;color:var(--muted);
  overflow-wrap:anywhere;
}

/* ---------- browse ---------- */
.browse-head{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;flex-wrap:wrap;margin-bottom:22px}
.browse-head > *{min-width:0}
.browse-head h1{font-size:29px}
.browse-head .desc{font-size:14px;color:var(--muted);margin-top:5px}
/* minmax(0,...), not a bare 1fr: a track's automatic minimum is its content's
   min-content, and a browse table's is the full width of its columns, so the
   column refused to shrink below that and took the whole page sideways. The
   table is meant to scroll inside .table-wrap instead, taking neither the
   sticky facets nor the header out of view with it. */
.browse{display:grid;grid-template-columns:196px minmax(0,1fr);gap:28px;align-items:start}
.browse > *{min-width:0}
.facets{position:sticky;top:calc(var(--topbar-h) + 22px);min-width:0}
.facets > summary{display:none}
.facet-groups{display:flex;flex-direction:column;gap:22px}
.facet{border:0;margin:0;padding:0;min-inline-size:0}
.facet-selected{margin-left:auto;font-family:var(--f-mono);font-size:11.5px;color:var(--muted);font-weight:400}
.facet .eyebrow{margin-bottom:8px;display:block}
.facet label{display:flex;align-items:center;gap:8px;font-size:13.5px;padding:3px 0;cursor:pointer;color:var(--muted)}
.facet label:hover{color:var(--ink)}
.facet input{accent-color:var(--view);margin:0}
.facet .n{margin-left:auto;font-family:var(--f-mono);font-size:11.5px;font-variant-numeric:tabular-nums}

.table-search{margin-bottom:12px}
.search-input{
  width:100%;max-width:320px;font:inherit;font-size:13.5px;
  padding:8px 11px;border:1px solid var(--rule);border-radius:6px;
  background:var(--raise);color:var(--ink);
}
.search-input::placeholder{color:var(--muted)}
.table-wrap{max-width:100%;overflow-x:auto}
.table-wrap:focus-visible{outline-offset:3px}
table{border-collapse:collapse;width:100%;font-size:13.5px}
/* A heading wraps; the numbers under it do not. "Bounds tightened" held its
   column open to 149px while the widest count in it wanted 83, and the two
   dual headings did the same, so a table 990px wide carried about a hundred
   pixels of heading and its last column fell off a 1280px screen. Bottom
   aligned, so a heading that takes two lines still sits on the line its
   neighbours sit on. */
thead th{
  position:sticky;top:var(--topbar-h);z-index:5;background:var(--raise);
  font-family:var(--f-sans);font-weight:500;font-size:11.5px;letter-spacing:.05em;
  text-transform:uppercase;color:var(--muted);text-align:left;vertical-align:bottom;
  padding:11px 13px;border-bottom:1px solid var(--rule);
}
thead th.r{text-align:right}
.sort-button{
  display:block;margin:0;padding:0;border:0;background:none;color:inherit;
  font:inherit;letter-spacing:inherit;text-transform:inherit;text-align:inherit;cursor:pointer;
}
thead th.r .sort-button{margin-left:auto}
.sort-button:hover{color:var(--ink)}
.sort-button:focus-visible{outline-offset:3px}
/* a no-break space, so the arrow cannot come to rest alone on a heading's
   second line, now that a heading has one */
thead th[aria-sort="ascending"] .sort-button::after{content:"\\00a0\\2191"}
thead th[aria-sort="descending"] .sort-button::after{content:"\\00a0\\2193"}
tbody th,tbody td{padding:9px 13px;border-bottom:1px solid var(--rule-soft);white-space:nowrap}
tbody th{font-weight:400;text-align:left}
tbody tr:last-child th,tbody tr:last-child td{border-bottom:0}
tbody tr:hover th,tbody tr:hover td{background:var(--rule-soft)}
th.name a{font-family:var(--f-mono);font-size:13px;text-decoration:none;color:var(--ink);border-bottom:1px solid var(--rule)}
th.name a:hover{border-bottom-color:var(--view);color:var(--view)}
.dl{
  font-family:var(--f-mono);font-size:12px;text-decoration:none;color:var(--view);
  border:1px solid var(--rule);border-radius:4px;padding:3px 8px;white-space:nowrap;
}
.dl:hover{background:var(--view-wash);border-color:var(--view)}
.dl[aria-disabled="true"]{color:var(--muted);border-style:dashed;cursor:not-allowed}
.dl[aria-disabled="true"]:hover{background:transparent;border-color:var(--rule)}
.table-foot{font-size:12.5px;color:var(--muted);margin-top:11px}

/* ---------- detail ---------- */
.detail-head{border-bottom:1px solid var(--rule);padding-bottom:20px;margin-bottom:26px}
.crumb{font-size:12.5px;color:var(--muted);margin-bottom:9px;overflow-wrap:anywhere}
.crumb a{color:var(--muted)}
.detail-head h1{font-family:var(--f-mono);font-size:30px;font-weight:600;letter-spacing:-.02em;overflow-wrap:anywhere}
.badges{display:flex;gap:7px;margin-top:11px;flex-wrap:wrap}
.badge{
  font-family:var(--f-mono);font-size:11.5px;padding:3px 9px;border-radius:11px;
  border:1px solid var(--accent);color:var(--accent);background:var(--wash);
}
.badge.p{--accent:var(--primal);--wash:var(--primal-wash)}
.badge.d{--accent:var(--dual);--wash:var(--dual-wash)}
.badge.n{--accent:var(--rule);--wash:transparent;color:var(--muted)}

.detail{display:grid;grid-template-columns:minmax(0,1fr) 292px;gap:30px;align-items:start}
.detail > *,.aside{min-width:0}
.panel{min-width:0;margin-bottom:18px;overflow:hidden}
.panel > header{
  padding:13px 18px;border-bottom:1px solid var(--rule-soft);
  display:flex;align-items:baseline;justify-content:space-between;gap:12px;
}
.panel > header h2{min-width:0;font-size:15px;font-family:var(--f-sans);font-weight:600;overflow-wrap:anywhere}
.panel > header .eyebrow{flex:none}
.panel .body{padding:16px 18px}
.lede{margin:0 0 13px;font-size:13.5px;color:var(--muted)}

.kv{display:grid;grid-template-columns:minmax(0,max-content) minmax(0,1fr);gap:0;min-width:0}
.kv dt{font-size:13px;color:var(--muted);padding:7px 0;border-bottom:1px solid var(--rule-soft)}
.kv dd{
  margin:0;padding:7px 0;text-align:right;border-bottom:1px solid var(--rule-soft);
  min-width:0;font-family:var(--f-mono);font-variant-numeric:tabular-nums;font-size:13px;
  overflow-wrap:anywhere;
}
.kv dt:last-of-type,.kv dd:last-of-type{border-bottom:0}

.recipe{
  font-family:var(--f-mono);font-size:13px;line-height:1.85;
  background:var(--view-wash);border:1px solid var(--rule);border-radius:6px;
  padding:13px 15px;margin-bottom:14px;overflow-wrap:anywhere;
}
.recipe .k{color:var(--muted)}
.recipe b{font-weight:600}

/* intrinsic: at most three columns, none narrower than a bound entry, so
   the count follows the space instead of three viewport breakpoints */
.path{font-family:var(--f-mono);font-size:12.5px;line-height:1.9;columns:11rem 3;column-gap:22px}
.path span{display:block;color:var(--muted);overflow-wrap:anywhere;break-inside:avoid}
.path span b{color:var(--ink);font-weight:500}
.more{font-size:12.5px;color:var(--muted);margin-top:12px;border-top:1px solid var(--rule-soft);padding-top:11px}
.more a{color:var(--view)}

.aside{position:sticky;top:calc(var(--topbar-h) + 22px);display:flex;flex-direction:column;gap:18px}
.card{min-width:0;overflow:hidden}
.card.p{--view:var(--primal);--view-wash:var(--primal-wash)}
.card.d{--view:var(--dual);--view-wash:var(--dual-wash)}
.card > header{padding:12px 16px;border-bottom:1px solid var(--rule-soft)}
.card > header .eyebrow{display:block}
.card .body{padding:14px 16px}
.btn{
  display:flex;align-items:center;justify-content:space-between;gap:10px;
  text-decoration:none;font-size:13.5px;font-weight:500;
  padding:11px 14px;border-radius:6px;border:1px solid var(--view);
  min-width:0;color:var(--on-view);background:var(--view);transition:filter .12s;
}
.btn-label{min-width:0;overflow-wrap:anywhere}
.btn:hover{filter:brightness(1.08)}
.btn .sz{flex:none;font-family:var(--f-mono);font-size:12px;font-weight:400}
.btn[aria-disabled="true"]{
  color:var(--muted-strong);background:var(--rule-soft);border-color:var(--rule);
  cursor:not-allowed;
}
.btn[aria-disabled="true"]:hover{filter:none}
.btn.ghost{background:transparent;color:var(--ink);border-color:var(--rule);margin-top:9px}
.btn.ghost:hover{background:var(--rule-soft);filter:none}
.card .hint{font-size:12px;color:var(--muted);margin-top:11px;line-height:1.5;overflow-wrap:anywhere}
.fields{display:grid;grid-template-columns:1fr;gap:0;margin-top:16px}
.fields dt{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;
padding:14px 0 5px;border-top:1px solid var(--rule-soft)}
.fields dt .mono{font-size:13px;color:var(--ink);font-weight:500}
.fields .ftype{font-size:11px;color:var(--muted);letter-spacing:.04em}
.fields dd{margin:0 0 16px;font-size:13.5px;line-height:1.65}
.srctags{display:flex;flex-wrap:wrap;gap:5px;margin:11px 0 4px}
.srctag{font-family:var(--f-mono);font-size:11.5px;letter-spacing:.02em;
padding:3px 7px;border-radius:3px;background:var(--rule-soft);color:var(--muted-strong)}
/* no opacity here: muted already carries the de-emphasis, and multiplying the
   two put this below the contrast floor */
.credit{font-size:11.5px;font-style:italic;color:var(--muted-strong);margin-top:6px}
.src-row{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;min-width:0;font-size:13px;padding:5px 0}
.src-row span:first-child{flex:none;color:var(--muted)}
.src-row span:last-child{min-width:0;text-align:right;overflow-wrap:anywhere;font-family:var(--f-mono);font-variant-numeric:tabular-nums}
/* the Terms row's value: mono like the rest of the column, a link when the
   licence has a canonical text to point at */
.src-row>a:last-child{min-width:0;text-align:right;overflow-wrap:anywhere;font-family:var(--f-mono);font-size:13px;color:var(--view);text-decoration:none;border-bottom:1px solid var(--rule)}
.src-row>a:last-child:hover{border-bottom-color:var(--view)}
/* why an instance has no licence, in MIPLIB's own words, under the row it explains */
.terms-note{margin-top:2px;padding-bottom:4px}
.extlink{
  display:inline-block;margin-top:12px;font-size:12.5px;color:var(--view);
  text-decoration:none;border-bottom:1px solid var(--rule);
}
.extlink:hover{border-bottom-color:var(--view)}
.crosslink{
  display:flex;align-items:center;flex-wrap:wrap;gap:10px;min-width:0;text-decoration:none;
  border:1px solid var(--rule);border-left:3px solid var(--to);border-radius:0 6px 6px 0;
  background:var(--raise);padding:12px 15px;font-size:13.5px;
}
.crosslink > span:first-child{min-width:0;overflow-wrap:anywhere}
.crosslink.p{--to:var(--primal);--to-wash:var(--primal-wash)}
.crosslink.d{--to:var(--dual);--to-wash:var(--dual-wash)}
.crosslink:hover{background:var(--to-wash)}
.crosslink .mono{flex:none;font-size:12.5px;color:var(--muted);margin-left:auto}

/* .pair and .files size themselves, so they are not listed here */
/* Touch targets. The desktop density is deliberate, so the taller hit areas are
   scoped to pointers that cannot land on a 25px row. */
@media (pointer:coarse){
  nav.top a{padding:12px 13px}
  .facet label{min-height:44px;padding:0}
  .facet input{width:18px;height:18px}
  .dl{display:inline-flex;align-items:center;min-height:40px;padding:0 12px}
  .search-input{min-height:44px}
  tbody th,tbody td{padding:13px}
  th.name a{display:inline-block;padding:6px 0}
  .extlink{display:inline-flex;align-items:center;min-height:44px}
}
@media (max-width:880px){
  .detail{grid-template-columns:minmax(0,1fr)}
  .aside{position:static}
}
@media (max-width:COMPACT_PX){
  .browse{grid-template-columns:minmax(0,1fr)}
  .facets{position:static;border:1px solid var(--rule);border-radius:8px;background:var(--raise)}
  .facets > summary{
    display:flex;align-items:center;gap:10px;min-height:46px;padding:10px 14px;
    cursor:pointer;list-style:none;font-weight:500;
  }
  .facets > summary::-webkit-details-marker{display:none}
  .facets > summary::after{content:"+";margin-left:2px;font-family:var(--f-mono);color:var(--view)}
  .facets[open] > summary{border-bottom:1px solid var(--rule-soft)}
  .facets[open] > summary::after{content:"-"}
  .facet-groups{gap:18px;padding:14px 16px 16px}
  thead th{position:static}
  html{scroll-padding-top:0}
  .topbar{position:static}
  .topbar-inner{
    height:auto;min-height:var(--topbar-h);padding:8px 16px 7px;
    display:grid;grid-template-columns:minmax(0,1fr);gap:4px;
  }
  .wordmark{display:block;width:max-content;max-width:100%;justify-self:start}
  nav.top{
    width:100%;margin:0;display:grid;
    grid-template-columns:repeat(3,minmax(0,1fr));gap:2px;
  }
  nav.top a{
    min-width:0;min-height:44px;padding:10px 2px;
    display:flex;align-items:center;justify-content:center;
    font-size:clamp(11px,3.2vw,12.5px);line-height:1.2;white-space:nowrap;
  }
  nav.top .nav-full{display:none}
  nav.top .nav-short{display:inline}
  main{padding:32px 16px 72px}
}
@media (max-width:640px){.masthead h1{font-size:32px}}
@media (max-width:460px){
  .kv{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
}
"""

# The rail is a plain list on a wide screen and a disclosure on a narrow one. The
# width at which that changes is COMPACT_PX, filled in below: a media query cannot
# read a custom property, so the stylesheet and this script each name the same
# placeholder instead of each carrying the number.
DISCLOSURE_SCRIPT = """
const compactFacets = matchMedia('(max-width: COMPACT_PX)');

function setFacetDisclosure(compact){
  for(const facets of document.querySelectorAll('.facets')){
    // collapsing the rail with the focus inside it would drop the caret on a
    // hidden control, so the summary that replaces it takes the focus first
    if(compact && facets.contains(document.activeElement)){
      facets.querySelector('summary')?.focus();
    }
    facets.open = !compact;
  }
}

// The desktop rail stays open. On a phone it collapses into a native disclosure
// as soon as the deferred script runs, leaving the table in the first viewport
// without making filtering depend on a custom button implementation.
setFacetDisclosure(compactFacets.matches);
compactFacets.addEventListener('change', (event) => setFacetDisclosure(event.matches));
"""

# The table is rendered by the build and is never re-rendered here. The page
# ships the values behind its rows and the facet declaration they are filtered
# by; this decides which rows to show and in what order, and moves the elements
# the build produced. One renderer, and it is in Python.
BROWSE_SCRIPT = """
// The mirror of Range.holds and Term.holds in website/facets.py. A bucket is
// that declaration serialised: a range carries lo and hi, a term the value it
// selects, and a field holding a list is held by any term the list contains.
function bucketHolds(bucket, value){
  if(value === undefined || value === null) return false;
  if(bucket.kind === 'term'){
    return Array.isArray(value) ? value.includes(bucket.value) : value === bucket.value;
  }
  return (bucket.lo === undefined || value >= bucket.lo)
      && (bucket.hi === undefined || value < bucket.hi);
}

function setUpBrowseTable(payload){
  // The rail, the table, the search field and the count are rendered by the
  // same template as this payload. None of them is checked for: if one is
  // missing that is a build error, and it should say so here rather than leave
  // a page that quietly filters nothing.
  const rail = document.querySelector('.facets');
  const table = document.querySelector('.table-wrap table');
  const body = table.tBodies[0];
  // the build emits one row per entry, in this order; the pairing is made once
  // and after that the elements are only hidden and moved
  const rows = [...body.rows].map((element, index) => ({
    element, values: payload.rows[index],
  }));
  // a checkbox's data-k is its facet and its bucket, which is also how the two
  // appear in the query string; both are carried here so neither has to be
  // parsed back out of the key
  const selectable = new Map();
  for(const facet of payload.facets){
    for(const bucket of facet.buckets){
      selectable.set(`${facet.param}-${bucket.value}`,
                     {param: facet.param, value: bucket.value, field: facet.field, bucket});
    }
  }
  const result = document.querySelector('.result-count');
  const selectedLabel = rail.querySelector('.facet-selected');
  // a name is what a reader arrives knowing, so searching for one is another
  // condition on the same rows rather than a mechanism of its own
  const search = document.getElementById('instance-search');
  document.querySelector('.table-search').hidden = false;
  let sortedBy = null;
  let ascending = true;

  function checkedByParam(){
    const chosen = new Map();
    for(const box of rail.querySelectorAll('input[data-k]:checked')){
      const entry = selectable.get(box.dataset.k);
      if(!entry) continue;
      if(!chosen.has(entry.param)) chosen.set(entry.param, []);
      chosen.get(entry.param).push(entry.value);
    }
    return chosen;
  }

  /* A filtered, sorted table is a view worth sending to someone, so it has an
     address. replaceState rather than pushState: Back should leave the page
     rather than undo a checkbox, and what a reader wants to keep is the link. */
  function writeUrl(){
    const params = new URLSearchParams();
    const term = search.value.trim();
    if(term) params.set('q', term);
    for(const [param, values] of checkedByParam()) params.set(param, values.join(','));
    if(sortedBy){
      params.set('sort', sortedBy);
      if(!ascending) params.set('dir', 'desc');
    }
    const query = params.toString();
    history.replaceState(null, '', query ? `?${query}` : location.pathname);
  }

  // The address is what the page opens as, so a box the query does not name is
  // cleared rather than left as the browser restored it.
  function readUrl(){
    const params = new URLSearchParams(location.search);
    const wanted = new Set();
    search.value = params.get('q') ?? '';
    for(const [param, value] of params){
      if(param === 'q' || param === 'sort' || param === 'dir') continue;
      for(const one of value.split(',')) wanted.add(`${param}-${one}`);
    }
    for(const box of rail.querySelectorAll('input[data-k]')){
      box.checked = wanted.has(box.dataset.k);
    }
    const field = params.get('sort');
    return field ? {field, ascending: params.get('dir') !== 'desc'} : null;
  }

  function checkedIn(group){
    return [...group.querySelectorAll('input[data-k]:checked')]
      .map((box) => selectable.get(box.dataset.k))
      .filter(Boolean);
  }

  function apply(){
    const term = search.value.trim().toLowerCase();
    const groups = [...rail.querySelectorAll('.facet')].map(checkedIn)
      .filter((selected) => selected.length > 0);
    let shown = 0;
    for(const row of rows){
      // a row has to carry the term, and satisfy every group that has a box
      // checked, by any one of that group's checked buckets
      const ok = (!term || row.values.instance.toLowerCase().includes(term))
        && groups.every((selected) =>
          selected.some(({field, bucket}) => bucketHolds(bucket, row.values[field])));
      row.element.hidden = !ok;
      if(ok) shown++;
    }
    const checked = rail.querySelectorAll('input[data-k]:checked').length;
    selectedLabel.textContent = checked ? `${checked} selected` : 'None selected';
    const total = result.dataset.total;
    if(!groups.length && !term){
      result.textContent = `${total} ${total === '1' ? 'instance' : 'instances'}.`;
    }else if(shown === 0){
      result.textContent = 'No instances match these filters.';
    }else{
      result.textContent = `${shown} of ${total} instances shown.`;
    }
  }

  function sortTo(field, ascendingNow){
    const button = table.querySelector(`button[data-sort="${CSS.escape(field)}"]`);
    if(!button) return;
    sortedBy = field;
    ascending = ascendingNow;
    rows.sort((a, b) => {
      const x = a.values[field], y = b.values[field];
      return (x < y ? -1 : x > y ? 1 : 0) * (ascending ? 1 : -1);
    });
    // one mutation, not one per row
    body.append(...rows.map((row) => row.element));
    const th = button.closest('th');
    for(const cell of th.parentNode.cells) cell.removeAttribute('aria-sort');
    th.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
  }

  table.addEventListener('click', (event) => {
    // A native button supplies Enter and Space without a second key handler that
    // would fire once here and once again through the button's synthetic click.
    const button = event.target.closest('button[data-sort]');
    if(!button) return;
    const field = button.dataset.sort;
    sortTo(field, field === sortedBy ? !ascending : true);
    writeUrl();
  });
  function narrow(){
    apply();
    writeUrl();
  }

  rail.addEventListener('change', narrow);
  // 229 rows is a filter per keystroke, not a reason for a debounce
  search.addEventListener('input', narrow);
  // Browsers restore checkbox state on reload and when the page comes back from
  // the back/forward cache, so the table has to be brought in line with the boxes
  // before the first change event. pageshow covers both; DOMContentLoaded misses
  // the cache.
  window.addEventListener('pageshow', apply);

  const opening = readUrl();
  apply();
  if(opening) sortTo(opening.field, opening.ascending);
}

const browseData = document.getElementById('browse-data');
if(browseData) setUpBrowseTable(JSON.parse(browseData.textContent));
"""

# The one width at which the layout stops being a desktop layout. Both the
# stylesheet and the script have to know it and neither can read the other's
# copy, so each writes COMPACT_PX and it is filled in once, here.
COMPACT_WIDTH = 780


def _fill(text: str) -> str:
    return text.replace("COMPACT_PX", f"{COMPACT_WIDTH}px")


SITE_CSS = _fill(font_face("../") + STYLESHEET)
SITE_JS = _fill(DISCLOSURE_SCRIPT + BROWSE_SCRIPT)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


CSS_NAME = f"site.{_digest(SITE_CSS)}.css"
JS_NAME = f"site.{_digest(SITE_JS)}.js"
