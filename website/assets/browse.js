
function setFacetDisclosure(compact){
  for(const facets of document.querySelectorAll('.facets')){
    // Collapsing the rail with focus inside would strand the caret on a hidden
    // control, so focus the summary that replaces it first.
    if(compact && facets.contains(document.activeElement)){
      facets.querySelector('summary')?.focus();
    }
    facets.open = !compact;
  }
}

function setUpFacetDisclosure(){
  const compactFacets = matchMedia('(max-width: COMPACT_PX)');
  setFacetDisclosure(compactFacets.matches);
  compactFacets.addEventListener(
    'change',
    (event) => setFacetDisclosure(event.matches),
  );
}
// Python has already evaluated every Range and Term declaration. The browser's
// entire filter rule is ordinary set logic: OR inside a group, AND across groups.
function rowMatches(row, groups, term){
  return (!term || row.values.instance.toLowerCase().includes(term))
    && groups.every((group) => group.some((key) => row.matches.has(key)));
}

function setUpBrowseTable(payload){
  const rail = document.querySelector('.facets');
  const table = document.querySelector('.table-wrap table');
  const body = table.tBodies[0];
  const result = document.querySelector('.result-count');
  const selectedLabel = rail.querySelector('.facet-selected');
  const search = document.getElementById('instance-search');
  const searchWrap = document.querySelector('.table-search');
  const sortNote = document.querySelector('.sort-note');
  const rows = payload.rows.map((record, index) => ({
    element: body.rows[index],
    values: record.values,
    matches: new Set(record.matches),
  }));
  let sortedBy = null;
  let ascending = true;

  function checkedIn(group){
    return [...group.querySelectorAll('input[data-k]:checked')]
      .map((box) => box.dataset.k);
  }

  function checkedByParam(){
    const chosen = new Map();
    for(const group of rail.querySelectorAll('.facet')){
      const keys = checkedIn(group);
      if(keys.length) chosen.set(group.dataset.param, keys);
    }
    return chosen;
  }

  // A filtered, sorted view is an address worth sharing. replaceState keeps the
  // Back button about navigation rather than individual checkbox changes.
  function writeUrl(){
    const params = new URLSearchParams();
    const term = search.value.trim();
    if(term) params.set('q', term);
    for(const [param, keys] of checkedByParam()){
      params.set(param, keys.map((key) => key.slice(param.length + 1)).join(','));
    }
    if(sortedBy){
      params.set('sort', sortedBy);
      if(!ascending) params.set('dir', 'desc');
    }
    const query = params.toString();
    history.replaceState(null, '', query ? `?${query}` : location.pathname);
  }

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

  function apply(){
    const term = search.value.trim().toLowerCase();
    const groups = [...rail.querySelectorAll('.facet')]
      .map(checkedIn)
      .filter((selected) => selected.length > 0);
    let shown = 0;
    for(const row of rows){
      const visible = rowMatches(row, groups, term);
      row.element.hidden = !visible;
      if(visible) shown++;
    }
    const checked = rail.querySelectorAll('input[data-k]:checked').length;
    selectedLabel.textContent = checked ? `${checked} selected` : 'None selected';
    const total = String(rows.length);
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
    body.append(...rows.map((row) => row.element));
    const th = button.closest('th');
    for(const cell of th.parentNode.cells) cell.removeAttribute('aria-sort');
    th.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
  }

  table.addEventListener('click', (event) => {
    const button = event.target.closest?.('button[data-sort]');
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
  search.addEventListener('input', narrow);
  window.addEventListener('pageshow', apply);

  const opening = readUrl();
  apply();
  if(opening) sortTo(opening.field, opening.ascending);

  // A script failure leaves a readable table, not half-working controls.
  for(const control of rail.querySelectorAll('input[data-k]')) control.disabled = false;
  for(const button of table.querySelectorAll('button[data-sort]')) button.disabled = false;
  searchWrap.hidden = false;
  sortNote.hidden = false;
}

function initialiseBrowse(){
  const browseData = document.getElementById('browse-data');
  if(!browseData) return;
  try{
    setUpFacetDisclosure();
    setUpBrowseTable(JSON.parse(browseData.textContent));
  }catch(error){
    console.error('Browse enhancements are unavailable:', error);
  }
}

if(typeof document !== 'undefined') initialiseBrowse();

if(typeof module !== 'undefined' && module.exports){
  module.exports = {rowMatches};
}
