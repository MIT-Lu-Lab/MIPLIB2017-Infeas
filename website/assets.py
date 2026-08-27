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
:root{
  --paper:#FAFAFB;
  --raise:#FFFFFF;
  --ink:#14161D;
  --muted:#676C7C;
  --rule:#DEE0E7;
  --rule-soft:#EBECF1;
  --primal:#3B4CC0;
  --primal-wash:#EEF0FC;
  --dual:#B45309;
  --dual-wash:#FBF1E5;
  --shared:#166534;
  --shared-wash:#E8F3EB;
  --on-view:#FFFFFF;
  --muted-strong:#4E5361;
  --shadow:0 1px 2px rgba(20,22,29,.05),0 8px 24px -16px rgba(20,22,29,.25);

  --f-serif:"IBM Plex Serif",Georgia,"Times New Roman",serif;
  --f-sans:"IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
  --f-mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --paper:#0F1116;
    --raise:#161922;
    --ink:#E6E8EF;
    --muted:#959BAC;
    --rule:#272B37;
    --rule-soft:#1E222C;
    --primal:#8B99EC;
    --primal-wash:#1B1F35;
    --dual:#E0A458;
    --dual-wash:#2A2015;
    --shared:#6BD48F;
    --shared-wash:#13251A;
    --on-view:#0F1116;
    --muted-strong:#B2B8C7;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -16px rgba(0,0,0,.8);
  }
}
:root[data-theme="dark"]{
  --paper:#0F1116;
  --raise:#161922;
  --ink:#E6E8EF;
  --muted:#959BAC;
  --rule:#272B37;
  --rule-soft:#1E222C;
  --primal:#8B99EC;
  --primal-wash:#1B1F35;
  --dual:#E0A458;
  --dual-wash:#2A2015;
  --shared:#6BD48F;
  --shared-wash:#13251A;
  --on-view:#0F1116;
  --muted-strong:#B2B8C7;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -16px rgba(0,0,0,.8);
}

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
:focus-visible{outline:2px solid var(--view);outline-offset:2px;border-radius:2px}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}

/* ---------- chrome ---------- */
.topbar{
  position:sticky;top:0;z-index:20;
  background:color-mix(in srgb,var(--paper) 88%,transparent);
  backdrop-filter:blur(8px);
  border-bottom:1px solid var(--rule);
  min-width:0;
}
.topbar-inner{
  max-width:1180px;margin:0 auto;padding:0 24px;
  height:56px;display:flex;align-items:center;gap:28px;min-width:0;
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
main{--measure:34rem;width:100%;min-width:0;max-width:1180px;margin:0 auto;padding:44px 24px 96px}
main.narrow{--measure:none;max-width:900px}
.prose,.note,.cite-note,.masthead .sub,.browse-head .desc{max-width:var(--measure)}
.prose,.note,.cite-note,.masthead .sub,.browse-head .desc{overflow-wrap:break-word}
.prose p{margin:0 0 14px}
.muted{color:var(--muted)}
.note{font-size:13px;color:var(--muted);margin-top:26px}
.cite-note{font-size:13px;color:var(--muted);margin-top:12px}

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


/* intrinsic, so the pair holds two columns until the cards genuinely stop
   fitting rather than at whatever width the other grids happen to need */
.pair{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:18px;margin:34px 0;min-width:0}
.subset{
  border:1px solid var(--rule);border-radius:8px;background:var(--raise);
  padding:20px 22px 18px;display:flex;flex-direction:column;gap:11px;
  border-top:3px solid var(--accent);text-align:left;font:inherit;color:var(--ink);cursor:pointer;
  text-decoration:none;transition:box-shadow .14s,transform .14s;min-width:0;
}
.subset:hover{box-shadow:var(--shadow);transform:translateY(-1px)}
.subset.p{--accent:var(--primal)}
.subset.d{--accent:var(--dual)}
.subset h3{font-size:20px}
.subset .count{font-family:var(--f-mono);font-variant-numeric:tabular-nums;font-size:13px;color:var(--accent);font-weight:500}
.subset p{margin:0;font-size:14px;color:var(--muted);line-height:1.55}
.subset .go{font-size:13px;color:var(--accent);font-weight:500;margin-top:auto}

.section{margin-top:52px}
.section > h2{font-size:24px;margin-bottom:6px}
.section > .eyebrow{margin-bottom:10px}

/* file cards */
.files{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:16px;margin-top:18px;min-width:0}
.file{border:1px solid var(--rule);border-radius:8px;background:var(--raise);padding:16px 18px;min-width:0}
.file .fn{font-family:var(--f-mono);font-size:12.5px;color:var(--view);margin-bottom:9px;overflow-wrap:anywhere}
.file p{margin:0;font-size:13.5px;color:var(--muted);line-height:1.55}

.cite{
  margin-top:20px;border:1px solid var(--rule);border-left:3px solid var(--muted);
  border-radius:0 6px 6px 0;background:var(--raise);padding:15px 18px;
  font-family:var(--f-mono);font-size:12.5px;line-height:1.7;color:var(--muted);
  overflow-x:auto;
}

/* ---------- browse ---------- */
.browse-head{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;flex-wrap:wrap;margin-bottom:22px;min-width:0}
.browse-head > *{min-width:0}
.browse-head h1{font-size:29px}
.browse-head .desc{font-size:14px;color:var(--muted);margin-top:5px}
/* minmax(0,...), not a bare 1fr: a track's automatic minimum is its content's
   min-content, and the widest table here is 970px, so the column refused to
   shrink below that and pushed the whole page into a horizontal scroll. The
   table is meant to scroll inside .table-wrap instead, taking neither the
   sticky facets nor the header out of view with it. */
.browse{display:grid;grid-template-columns:196px minmax(0,1fr);gap:28px;align-items:start;min-width:0}
.browse > *{min-width:0}
.facets{position:sticky;top:78px;min-width:0}
.facets > summary{display:none}
.facet-groups{display:flex;flex-direction:column;gap:22px;min-width:0}
.facet-selected{margin-left:auto;font-family:var(--f-mono);font-size:11.5px;color:var(--muted);font-weight:400}
.facet .eyebrow{margin-bottom:8px;display:block}
.facet label{display:flex;align-items:center;gap:8px;font-size:13.5px;padding:3px 0;cursor:pointer;color:var(--muted)}
.facet label:hover{color:var(--ink)}
.facet input{accent-color:var(--view);margin:0}
.facet .n{margin-left:auto;font-family:var(--f-mono);font-size:11.5px;font-variant-numeric:tabular-nums}

.table-wrap{min-width:0;max-width:100%;border:1px solid var(--rule);border-radius:8px;background:var(--raise);overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13.5px}
thead th{
  position:sticky;top:56px;z-index:5;background:var(--raise);
  font-family:var(--f-sans);font-weight:500;font-size:11.5px;letter-spacing:.05em;
  text-transform:uppercase;color:var(--muted);text-align:left;
  padding:11px 13px;border-bottom:1px solid var(--rule);white-space:nowrap;
}
thead th.r{text-align:right}
thead th[data-sort]{cursor:pointer;user-select:none}
thead th[data-sort]:focus-visible{outline:2px solid var(--view);outline-offset:-2px}
thead th[data-sort]:hover{color:var(--ink)}
thead th[aria-sort="ascending"]::after{content:" \\2191"}
thead th[aria-sort="descending"]::after{content:" \\2193"}
tbody td{padding:9px 13px;border-bottom:1px solid var(--rule-soft);white-space:nowrap}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover td{background:var(--rule-soft)}
td.name a{font-family:var(--f-mono);font-size:13px;text-decoration:none;color:var(--ink);border-bottom:1px solid var(--rule)}
td.name a:hover{border-bottom-color:var(--view);color:var(--view)}
.dl{
  font-family:var(--f-mono);font-size:12px;text-decoration:none;color:var(--view);
  border:1px solid var(--rule);border-radius:4px;padding:3px 8px;white-space:nowrap;
}
.dl:hover{background:var(--view-wash);border-color:var(--view)}
.table-foot{font-size:12.5px;color:var(--muted);margin-top:11px}

/* ---------- detail ---------- */
.detail-head{min-width:0;border-bottom:1px solid var(--rule);padding-bottom:20px;margin-bottom:26px}
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

.detail{display:grid;grid-template-columns:minmax(0,1fr) 292px;gap:30px;align-items:start;min-width:0}
.detail > *,.aside{min-width:0}
.panel{min-width:0;border:1px solid var(--rule);border-radius:8px;background:var(--raise);margin-bottom:18px;overflow:hidden}
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
  padding:13px 15px;margin-bottom:14px;overflow-x:auto;
}
.recipe .k{color:var(--muted)}
.recipe b{font-weight:600}

.path{font-family:var(--f-mono);font-size:12.5px;line-height:1.9;columns:3;column-gap:22px}
.path span{display:block;color:var(--muted);overflow-wrap:anywhere;break-inside:avoid}
.path span b{color:var(--ink);font-weight:500}
.more{font-size:12.5px;color:var(--muted);margin-top:12px;border-top:1px solid var(--rule-soft);padding-top:11px}
.more a{color:var(--view)}

.aside{position:sticky;top:78px;display:flex;flex-direction:column;gap:18px}
.card{min-width:0;border:1px solid var(--rule);border-radius:8px;background:var(--raise);overflow:hidden}
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
.btn .sz{flex:none;font-family:var(--f-mono);font-size:12px;opacity:.82;font-weight:400}
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
@media (max-width:880px){
  .detail{grid-template-columns:minmax(0,1fr)}
  .aside{position:static}
}
@media (max-width:780px){
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
}
@media (max-width:700px){.path{columns:2}}
@media (max-width:640px){.masthead h1{font-size:32px}}
@media (max-width:460px){.path{columns:1}}

/* Touch targets. The desktop density is deliberate, so the taller hit areas are
   scoped to pointers that cannot land on a 25px row. */
@media (pointer:coarse){
  nav.top a{padding:12px 13px}
  .facet label{min-height:44px;padding:0}
  .facet input{width:18px;height:18px}
  .dl{display:inline-flex;align-items:center;min-height:40px;padding:0 12px}
  tbody td{padding:13px}
  td.name a{display:inline-block;padding:6px 0}
  .extlink{display:inline-flex;align-items:center;min-height:44px}
}
@media (max-width:600px){
  .topbar-inner{
    height:auto;min-height:56px;padding:8px 16px 7px;
    display:grid;grid-template-columns:minmax(0,1fr);gap:4px;
  }
  .wordmark{justify-self:start}
  nav.top{width:100%;margin:0;flex-wrap:nowrap;gap:0}
  nav.top a{
    flex:1 1 0;min-width:0;min-height:44px;padding:10px 2px;
    display:flex;align-items:center;justify-content:center;
    font-size:clamp(11px,3.2vw,12.5px);line-height:1.2;white-space:nowrap;
  }
  main{padding:32px 16px 72px}
}
@media (max-width:560px){.path{columns:1}}
@media (max-width:460px){
  .kv{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
}
"""

SORT_SCRIPT = """
function sortByHeader(th){
  if(!th) return;
  var table = th.closest('table');
  var idx = Array.prototype.indexOf.call(th.parentNode.children, th);
  var asc = th.getAttribute('aria-sort') !== 'ascending';
  var numeric = th.dataset.sort === 'num';
  var rows = Array.prototype.slice.call(table.tBodies[0].rows);
  rows.sort(function(a,b){
    var x = a.cells[idx].dataset.v, y = b.cells[idx].dataset.v;
    if(numeric){ x = parseFloat(x); y = parseFloat(y); }
    return (x<y?-1:x>y?1:0) * (asc?1:-1);
  });
  rows.forEach(function(r){ table.tBodies[0].appendChild(r) });
  Array.prototype.forEach.call(table.tHead.rows[0].cells, function(c){
    c.removeAttribute('aria-sort') });
  th.setAttribute('aria-sort', asc?'ascending':'descending');
}

document.addEventListener('click', function(ev){
  sortByHeader(ev.target.closest('th[data-sort]'));
});

// keyboard: sortable headers are focusable, and Enter or Space sorts them
document.addEventListener('keydown', function(ev){
  if(ev.key !== 'Enter' && ev.key !== ' ') return;
  var th = ev.target.closest('th[data-sort]');
  if(!th) return;
  ev.preventDefault();
  sortByHeader(th);
});
"""

# Facet filtering: a row's `data-f` (from render_browse) lists the facet keys it
# satisfies; each checkbox carries the key it stands for as `data-k`. Every `.facet`
# group in the rail imposes its own constraint only when at least one of its boxes is
# checked; a row must then satisfy at least one checked key per active group.
FILTER_SCRIPT = """
var compactFacets = window.matchMedia('(max-width: 780px)');

function setFacetDisclosure(compact){
  Array.prototype.forEach.call(document.querySelectorAll('.facets'), function(facets){
    facets.open = !compact;
  });
}

// The desktop rail stays open. On a phone it becomes a native disclosure before
// first paint, leaving the table in the first viewport without making filtering
// dependent on a custom button implementation.
setFacetDisclosure(compactFacets.matches);
if(compactFacets.addEventListener){
  compactFacets.addEventListener('change', function(ev){ setFacetDisclosure(ev.matches); });
}else if(compactFacets.addListener){
  compactFacets.addListener(function(ev){ setFacetDisclosure(ev.matches); });
}

function applyFacets(facets){
  var wrap = facets.parentNode;
  var table = wrap.querySelector('table');
  if(!table) return;
  var selected = facets.querySelectorAll('input[data-k]:checked').length;
  var selectedLabel = facets.querySelector('.facet-selected');
  if(selectedLabel){
    selectedLabel.textContent = selected
      ? (selected + ' selected')
      : 'None selected';
  }
  var groups = Array.prototype.map.call(facets.querySelectorAll('.facet'), function(g){
    return Array.prototype.map.call(
      g.querySelectorAll('input[data-k]:checked'), function(i){ return i.dataset.k; });
  }).filter(function(keys){ return keys.length > 0; });
  var shown = 0;
  Array.prototype.forEach.call(table.tBodies[0].rows, function(row){
    var have = (row.getAttribute('data-f') || '').split(' ');
    var ok = groups.every(function(keys){
      return keys.some(function(k){ return have.indexOf(k) !== -1; });
    });
    row.hidden = !ok;
    if(ok) shown++;
  });
  var foot = wrap.querySelector('.table-foot');
  if(!foot) return;
  var total = foot.dataset.total;
  foot.textContent = groups.length
    ? (shown + ' of ' + total + ' instances shown. Every column sorts.')
    : (total + ' instances. Every column sorts.');
}

document.addEventListener('change', function(ev){
  var cb = ev.target.closest('.facets input[data-k]');
  if(cb) applyFacets(cb.closest('.facets'));
});

// Browsers restore checkbox state on reload and when the page comes back from the
// back/forward cache, so the table has to be brought in line with the boxes before
// the first change event. pageshow covers both; DOMContentLoaded misses the cache.
window.addEventListener('pageshow', function(){
  Array.prototype.forEach.call(document.querySelectorAll('.facets'), applyFacets);
});
"""


# The stylesheet and the scripts used to be inlined into every page: 18 KB carried
# 340 times, 78% of the site's HTML, and re-downloaded on every navigation. As two
# files the browser fetches them once. The name carries a digest of the contents so
# a changed stylesheet cannot be served from a cache of the old one, and so the
# pruner can tell last build's file from this one's.
SITE_CSS = font_face("../") + STYLESHEET
SITE_JS = SORT_SCRIPT + FILTER_SCRIPT


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


CSS_NAME = f"site.{_digest(SITE_CSS)}.css"
JS_NAME = f"site.{_digest(SITE_JS)}.js"
