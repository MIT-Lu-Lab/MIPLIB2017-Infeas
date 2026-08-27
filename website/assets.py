"""The stylesheet and the client-side scripts, written out as two files."""

import hashlib

# The faces the stylesheet asks for, shipped with the site. build_site copies
# fonts/ into the output, so a build is self-contained and a reader loads
# nothing from a third party.
#
# These are the complete faces rather than the Latin subsets a font CDN serves:
# the pages set U+2192, U+2264 and U+2265, which that subset drops, so the arrows
# and the inequalities in every branch recipe used to fall back to whatever the
# reader happened to have installed.
FONT_FACES = (
    ("Mono", "Regular", 400), ("Mono", "Medium", 500), ("Mono", "SemiBold", 600),
    ("Sans", "Regular", 400), ("Sans", "Medium", 500), ("Sans", "SemiBold", 600),
    ("Serif", "Regular", 400), ("Serif", "SemiBold", 600),
)


def font_face(up=""):
    """The @font-face rules, with paths relative to a page `up` levels down."""
    return "".join(
        f"@font-face{{font-family:'IBM Plex {family}';font-style:normal;"
        f"font-weight:{weight};font-display:swap;"
        f"src:url({up}fonts/IBMPlex{family}-{style}.woff2) format('woff2')}}"
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

  --f-serif:"IBM Plex Serif",Georgia,"Times New Roman",serif;
  --f-sans:"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  --f-mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
:root[data-theme="light"]{color-scheme:light}
:root[data-theme="dark"]{color-scheme:dark}

/* min-width:0 below is on flex and grid items only. A grid or flex item's
   automatic minimum is its content's min-content, which is what kept the browse
   column from shrinking under a 970px table and pushed the whole page sideways.
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
  max-width:1180px;margin:0 auto;padding:0 24px;
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
main{--measure:34rem;width:100%;max-width:1180px;margin:0 auto;padding:44px 24px 96px}
main.narrow{--measure:none;max-width:900px}
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
   min-content, and the widest table here is 970px, so the column refused to
   shrink below that and pushed the whole page into a horizontal scroll. The
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

.table-wrap{max-width:100%;overflow-x:auto}
.table-wrap:focus-visible{outline-offset:3px}
table{border-collapse:collapse;width:100%;font-size:13.5px}
thead th{
  position:sticky;top:var(--topbar-h);z-index:5;background:var(--raise);
  font-family:var(--f-sans);font-weight:500;font-size:11.5px;letter-spacing:.05em;
  text-transform:uppercase;color:var(--muted);text-align:left;
  padding:11px 13px;border-bottom:1px solid var(--rule);white-space:nowrap;
}
thead th.r{text-align:right}
.sort-button{
  display:block;margin:0;padding:0;border:0;background:none;color:inherit;
  font:inherit;letter-spacing:inherit;text-transform:inherit;white-space:nowrap;cursor:pointer;
}
thead th.r .sort-button{margin-left:auto}
.sort-button:hover{color:var(--ink)}
.sort-button:focus-visible{outline-offset:3px}
thead th[aria-sort="ascending"] .sort-button::after{content:" \\2191"}
thead th[aria-sort="descending"] .sort-button::after{content:" \\2193"}
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

SORT_SCRIPT = """
function sortByButton(button){
  if(!button) return;
  const th = button.closest('th');
  const body = th.closest('table').tBodies[0];
  const index = th.cellIndex;
  const ascending = th.getAttribute('aria-sort') !== 'ascending';
  const numeric = button.dataset.sort === 'num';
  const rows = [...body.rows].sort((a, b) => {
    let x = a.cells[index].dataset.v, y = b.cells[index].dataset.v;
    if(numeric){ x = parseFloat(x); y = parseFloat(y); }
    return (x < y ? -1 : x > y ? 1 : 0) * (ascending ? 1 : -1);
  });
  // one mutation, not one per row: the table is reordered in a single insertion
  // rather than reflowed once for each of 334 rows
  body.append(...rows);
  for(const cell of th.parentNode.cells) cell.removeAttribute('aria-sort');
  th.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
}

document.addEventListener('click', (event) => {
  // A native button supplies Enter and Space without a second key handler that
  // would fire once here and once again through the button's synthetic click.
  sortByButton(event.target.closest('button[data-sort]'));
});
"""

# The rail is a plain list on a wide screen and a disclosure on a narrow one. The
# width at which that changes is COMPACT_PX, filled in below: a media query cannot
# read a custom property, so the stylesheet and this script each name the same
# placeholder instead of each carrying the number.
FILTER_SCRIPT = """
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

function applyFacets(facets){
  const wrap = facets.parentNode;
  const table = wrap.querySelector('table');
  if(!table) return;
  const selectedLabel = facets.querySelector('.facet-selected');
  if(selectedLabel){
    const selected = facets.querySelectorAll('input[data-k]:checked').length;
    selectedLabel.textContent = selected ? `${selected} selected` : 'None selected';
  }
  const groups = [...facets.querySelectorAll('.facet')]
    .map((group) => [...group.querySelectorAll('input[data-k]:checked')]
      .map((box) => box.dataset.k))
    .filter((keys) => keys.length > 0);
  let shown = 0;
  for(const row of table.tBodies[0].rows){
    const have = (row.getAttribute('data-f') || '').split(' ');
    const ok = groups.every((keys) => keys.some((key) => have.includes(key)));
    row.hidden = !ok;
    if(ok) shown++;
  }
  const result = wrap.querySelector('.result-count');
  if(!result) return;
  const total = result.dataset.total;
  if(!groups.length){
    result.textContent = `${total} ${total === '1' ? 'instance' : 'instances'}.`;
  }else if(shown === 0){
    result.textContent = 'No instances match these filters.';
  }else{
    result.textContent = `${shown} of ${total} instances shown.`;
  }
}

document.addEventListener('change', (event) => {
  const box = event.target.closest('.facets input[data-k]');
  if(box) applyFacets(box.closest('.facets'));
});

// Browsers restore checkbox state on reload and when the page comes back from the
// back/forward cache, so the table has to be brought in line with the boxes before
// the first change event. pageshow covers both; DOMContentLoaded misses the cache.
window.addEventListener('pageshow', () => {
  document.querySelectorAll('.facets').forEach(applyFacets);
});
"""

# The one width at which the layout stops being a desktop layout. Both the
# stylesheet and the script have to know it and neither can read the other's
# copy, so each writes COMPACT_PX and it is filled in once, here.
COMPACT_WIDTH = 780


def _fill(text: str) -> str:
    return text.replace("COMPACT_PX", f"{COMPACT_WIDTH}px")


SITE_CSS = _fill(font_face("../") + STYLESHEET)
SITE_JS = _fill(SORT_SCRIPT + FILTER_SCRIPT)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


CSS_NAME = f"site.{_digest(SITE_CSS)}.css"
JS_NAME = f"site.{_digest(SITE_JS)}.js"
