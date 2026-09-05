/**
 * Vanadhikar AI - Command Deck 2.0 Controller
 * Full-viewport WebGIS, Three.js 3D Morphing, Floating Islands & AI Intelligence
 */

const deckState = {
  mode: '2d',
  districts: [],
  claims: [],
  anomalies: [],
  selectedDistrict: '',
  selectedState: '',
  selectedType: '',
  selectedStage: 'ALL',
  anomalyOnly: false,
  triageSeverity: 'ALL',
  searchQuery: '',
  threeEngine: null,
  activeTargetMarker: null
};

// Basemap Providers
const BASEMAPS = {
  dark: L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; Carto &copy; OpenStreetMap',
    maxZoom: 19
  }),
  satellite: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
    attribution: 'Tiles &copy; Esri &mdash; Bhuvan / ISRO Cadastre',
    maxZoom: 19
  }),
  topo: L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenTopoMap &copy; OpenStreetMap',
    maxZoom: 17
  })
};

let map = null;
let currentBasemap = null;
let districtsLayer = null;
let forestLayer = null;
let claimsLayer = null;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', async () => {
  initMap();
  await loadInitialTelemetry();
});

// Map Initialization
function initMap() {
  map = L.map('webgis-map', {
    zoomControl: false,
    attributionControl: false
  }).setView([21.8, 82.5], 6);

  L.control.zoom({ position: 'bottomright' }).addTo(map);

  currentBasemap = BASEMAPS.dark.addTo(map);

  districtsLayer = L.geoJSON(null).addTo(map);
  forestLayer = L.geoJSON(null).addTo(map);
  claimsLayer = L.layerGroup().addTo(map);
}

function changeBasemap(type) {
  if (currentBasemap) map.removeLayer(currentBasemap);
  currentBasemap = BASEMAPS[type];
  currentBasemap.addTo(map);

  document.querySelectorAll('.bm-btn').forEach(btn => {
    if (btn.getAttribute('data-bm') === type) {
      btn.className = 'bm-btn py-1.5 rounded-lg bg-emerald-600/30 border border-emerald-500 text-white font-medium text-center transition';
    } else {
      btn.className = 'bm-btn py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 font-medium text-center hover:text-white transition';
    }
  });
}

// Initial Data Load
async function loadInitialTelemetry() {
  try {
    // 1. Health and Top Telemetry
    const hRes = await fetch('/health');
    const hData = await hRes.json();
    document.getElementById('top-stat-claims').textContent = Number(hData.total_claims).toLocaleString();
    document.getElementById('top-stat-anomalies').textContent = Number(hData.total_anomalies).toLocaleString();

    // 2. Districts GeoJSON
    const dRes = await fetch('/api/gis/districts');
    const dData = await dRes.json();
    deckState.districts = dData.features;
    renderDistricts(dData);
    populateDistrictSelect();

    // 3. ISRO Forest Compartments
    const fcRes = await fetch('/api/gis/forest-cover');
    const fcData = await fcRes.json();
    renderForestCover(fcData);

    // 4. Claims Layer
    await fetchAndRenderClaims();

    // 5. Triage Stream
    await fetchAndRenderTriage();

  } catch (e) {
    console.error('Failed to load initial telemetry:', e);
  }
}

function populateDistrictSelect() {
  const sel = document.getElementById('sel-district');
  sel.innerHTML = '<option value="">All 10 Tribal Districts</option>';
  deckState.districts.forEach(d => {
    const p = d.properties;
    const opt = document.createElement('option');
    opt.value = p.district_code;
    opt.textContent = `${p.district_name} (${p.state}) — Risk: ${p.metrics?.composite_risk_score ?? '--'}/100`;
    sel.appendChild(opt);
  });
}

function renderDistricts(data) {
  districtsLayer.clearLayers();
  districtsLayer.addData(data);
  districtsLayer.setStyle({
    color: '#10b981',
    weight: 1.5,
    dashArray: '3, 4',
    fillColor: '#059669',
    fillOpacity: 0.07
  });

  districtsLayer.eachLayer(layer => {
    const p = layer.feature.properties;
    layer.on('mouseover', () => layer.setStyle({ fillOpacity: 0.2, weight: 2.5 }));
    layer.on('mouseout', () => layer.setStyle({ fillOpacity: 0.07, weight: 1.5 }));
    layer.on('click', () => {
      deckState.selectedDistrict = p.district_code;
      document.getElementById('sel-district').value = p.district_code;
      map.flyTo(p.center, 9, { duration: 1.2 });
      fetchAndRenderClaims();
      openDecisionModal(p.district_code);
    });

    layer.bindTooltip(`
      <div class="font-sans text-xs">
        <strong class="text-emerald-400 font-bold">${p.district_name} (${p.state})</strong><br>
        <span class="text-slate-300">Forest: ${p.forest_cover_sqkm} sq.km | Tribal: ${p.tribal_population_pct}%</span><br>
        <span class="text-amber-400 font-bold">Composite Risk: ${p.metrics?.composite_risk_score ?? '--'}/100</span>
      </div>
    `, { sticky: true });
  });
}

function renderForestCover(data) {
  forestLayer.clearLayers();
  forestLayer.addData(data);
  forestLayer.setStyle({
    color: '#22c55e',
    weight: 1,
    fillColor: '#15803d',
    fillOpacity: 0.18,
    dashArray: '2, 5'
  });
}

// Claims Fetch & Render
async function fetchAndRenderClaims() {
  claimsLayer.clearLayers();

  let url = `/api/gis/claims?limit=1000`;
  if (deckState.selectedDistrict) url += `&district_code=${deckState.selectedDistrict}`;
  if (deckState.selectedState) url += `&state=${encodeURIComponent(deckState.selectedState)}`;
  if (deckState.selectedType) url += `&claimant_type=${deckState.selectedType}`;
  if (deckState.anomalyOnly) url += `&anomaly_only=true`;
  if (deckState.selectedStage !== 'ALL') url += `&status=${deckState.selectedStage}`;

  const res = await fetch(url);
  const data = await res.json();
  deckState.claims = data.features;

  data.features.forEach(f => {
    const [lng, lat] = f.geometry.coordinates;
    const p = f.properties;

    // Apply text search query filter if active
    if (deckState.searchQuery) {
      const q = deckState.searchQuery.toLowerCase();
      const match =
        p.claimant_name.toLowerCase().includes(q) ||
        p.tribe_name.toLowerCase().includes(q) ||
        p.village.toLowerCase().includes(q) ||
        p.claim_id.toLowerCase().includes(q);
      if (!match) return;
    }

    let fillColor = '#f59e0b'; // Amber pending
    let radius = 4;
    let strokeColor = '#ffffff';

    if (p.has_anomaly) {
      fillColor = '#f43f5e'; // Rose Anomaly
      radius = 6;
      strokeColor = '#fecdd3';
    } else if (p.status === 'TITLE_ISSUED') {
      fillColor = '#10b981'; // Emerald Approved
      radius = 4.5;
    } else if (p.status === 'REJECTED') {
      fillColor = '#64748b'; // Slate Rejected
      radius = 3.5;
    }

    const marker = L.circleMarker([lat, lng], {
      radius: radius,
      fillColor: fillColor,
      color: strokeColor,
      weight: p.has_anomaly ? 2 : 1,
      fillOpacity: 0.9
    });

    marker.on('click', () => {
      inspectClaim(p.claim_id);
    });

    claimsLayer.addLayer(marker);
  });
}

// Triage Stream Fetch & Render
async function fetchAndRenderTriage() {
  const res = await fetch('/api/analytics/triage');
  const data = await res.json();
  deckState.anomalies = data.priority_action_list;
  document.getElementById('triage-badge-count').textContent = `${data.triage_count} Flags`;
  renderTriageStream();
}

function renderTriageStream() {
  const container = document.getElementById('triage-stream');
  if (!container) return;

  let items = deckState.anomalies;
  if (deckState.triageSeverity !== 'ALL') {
    items = items.filter(i => i.severity === deckState.triageSeverity);
  }

  container.innerHTML = '';
  items.slice(0, 20).forEach(item => {
    const card = document.createElement('div');
    card.className = 'deck-card p-2.5 rounded-xl cursor-pointer hover:border-emerald-500/50 transition';
    card.onclick = () => flyToClaim(item.claim_id);

    const isCritical = item.severity === 'CRITICAL';
    const badgeBg = isCritical ? 'bg-rose-950/80 text-rose-300 border-rose-800' : 'bg-amber-950/80 text-amber-300 border-amber-800';

    card.innerHTML = `
      <div class="flex justify-between items-center mb-1">
        <span class="font-bold text-slate-100 text-xs">${item.claimant_name}</span>
        <span class="text-[9px] px-1.5 py-0.5 rounded font-mono font-bold border ${badgeBg}">${item.severity}</span>
      </div>
      <div class="text-[11px] text-slate-300 truncate">${item.title}</div>
      <div class="flex justify-between items-center text-[10px] text-slate-400 mt-1.5 font-mono">
        <span>${item.taluk_block}, ${item.state}</span>
        <span class="text-amber-400 font-bold">Risk: ${item.risk_score}/100</span>
      </div>
    `;
    container.appendChild(card);
  });
}

function setTriageSeverity(sev) {
  deckState.triageSeverity = sev;
  document.querySelectorAll('.sev-btn').forEach(b => {
    if (b.getAttribute('data-sev') === sev) {
      b.className = 'sev-btn px-2.5 py-1 rounded-lg bg-emerald-600 text-white font-semibold';
    } else {
      b.className = 'sev-btn px-2.5 py-1 rounded-lg bg-slate-900 text-slate-400 hover:text-white';
    }
  });
  renderTriageStream();
}

// Smooth Camera FlyTo Claim
async function flyToClaim(claimId) {
  const res = await fetch(`/api/gis/claim-details/${claimId}`);
  const c = await res.json();

  if (c.latitude && c.longitude) {
    map.flyTo([c.latitude, c.longitude], 14, { duration: 1.4 });

    // Target beacon animation ring
    if (deckState.activeTargetMarker) map.removeLayer(deckState.activeTargetMarker);
    deckState.activeTargetMarker = L.circleMarker([c.latitude, c.longitude], {
      radius: 18,
      color: '#f43f5e',
      weight: 2,
      fillColor: '#f43f5e',
      fillOpacity: 0.25,
      dashArray: '3, 4'
    }).addTo(map);

    setTimeout(() => {
      if (deckState.activeTargetMarker) map.removeLayer(deckState.activeTargetMarker);
    }, 6000);
  }

  inspectClaim(claimId);
}

// Slide-Over Claim Inspector
async function inspectClaim(claimId) {
  const drawer = document.getElementById('inspector-drawer');
  drawer.classList.remove('translate-x-full');

  const content = document.getElementById('inspector-content');
  content.innerHTML = `
    <div class="flex flex-col items-center justify-center py-12">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500 mb-3"></div>
      <span class="text-slate-400 text-xs">Inspecting cadastral parcel...</span>
    </div>
  `;

  const res = await fetch(`/api/gis/claim-details/${claimId}`);
  const c = await res.json();

  document.getElementById('inspector-id').textContent = c.claim_id;
  document.getElementById('inspector-avatar').textContent = c.claimant_name.slice(0, 2).toUpperCase();

  let statusBadge = '';
  if (c.status === 'TITLE_ISSUED') statusBadge = '<span class="px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-700 font-bold">TITLE ISSUED</span>';
  else if (c.status === 'REJECTED') statusBadge = '<span class="px-2 py-0.5 rounded-full bg-rose-950 text-rose-300 border border-rose-700 font-bold">REJECTED</span>';
  else statusBadge = `<span class="px-2 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-700 font-bold">${c.status}</span>`;

  let anomSection = '';
  if (c.anomalies && c.anomalies.length > 0) {
    anomSection = `
      <div class="p-3 bg-rose-950/40 border border-rose-900/60 rounded-xl space-y-2">
        <span class="font-bold text-rose-400 text-xs flex items-center gap-1">
          <span>⚠️</span> AI Anomalies Flagged (${c.anomalies.length})
        </span>
        ${c.anomalies.map(a => `
          <div class="bg-slate-900/80 p-2 rounded-lg border border-rose-900/40">
            <div class="flex justify-between font-bold text-rose-300 text-xs">
              <span>${a.title}</span>
              <span class="text-amber-400 text-[10px]">Score ${a.risk_score}</span>
            </div>
            <p class="text-slate-400 text-[11px] mt-0.5">${a.description}</p>
            <div class="text-[10px] font-mono text-emerald-400 mt-1">${a.rule_reference}</div>
          </div>
        `).join('')}
      </div>
    `;
  }

  content.innerHTML = `
    <div class="flex justify-between items-center pb-2 border-b border-white/5">
      <span class="text-slate-400">Current Status</span>
      <div>${statusBadge}</div>
    </div>

    <!-- Claimant Info Grid -->
    <div class="grid grid-cols-2 gap-2">
      <div class="deck-card p-2.5 rounded-xl">
        <span class="text-[10px] text-slate-400 font-medium">Claimant</span>
        <div class="font-bold text-slate-100 text-xs mt-0.5">${c.claimant_name}</div>
      </div>
      <div class="deck-card p-2.5 rounded-xl">
        <span class="text-[10px] text-slate-400 font-medium">Tribe / PVTG</span>
        <div class="font-bold text-slate-100 text-xs mt-0.5">${c.tribe_name} ${c.is_pvtg ? '<span class="text-rose-400 font-bold">(PVTG)</span>' : ''}</div>
      </div>
      <div class="deck-card p-2.5 rounded-xl">
        <span class="text-[10px] text-slate-400 font-medium">Claim Type</span>
        <div class="font-bold text-emerald-400 text-xs mt-0.5">${c.claimant_type}</div>
      </div>
      <div class="deck-card p-2.5 rounded-xl">
        <span class="text-[10px] text-slate-400 font-medium">Area Claimed</span>
        <div class="font-bold ${c.claimed_area_ha > 4.0 ? 'text-rose-400' : 'text-slate-100'} text-xs mt-0.5">
          ${c.claimed_area_ha} Ha ${c.claimed_area_ha > 4.0 ? '⚠️ (>4Ha)' : ''}
        </div>
      </div>
    </div>

    <!-- Hierarchy -->
    <div class="deck-card p-3 rounded-xl space-y-1">
      <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Administrative Cadastre</span>
      <div class="text-slate-200">Village: <strong>${c.village}</strong></div>
      <div class="text-slate-200">Gram Panchayat: <strong>${c.gram_panchayat}</strong></div>
      <div class="text-slate-200">Taluk: <strong>${c.taluk_block}</strong> | District: <strong>${c.district_code}</strong></div>
      <div class="text-slate-400 font-mono text-[10px] pt-1">Coordinates: [${c.latitude}, ${c.longitude}]</div>
    </div>

    <!-- Review Milestones -->
    <div class="deck-card p-3 rounded-xl space-y-1.5 text-[11px]">
      <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Statutory Timeline Journey</span>
      <div class="flex justify-between text-slate-300">
        <span>Submission:</span>
        <span class="font-mono text-slate-400">${c.claim_date}</span>
      </div>
      <div class="flex justify-between text-slate-300">
        <span>Gram Sabha:</span>
        <span class="font-mono text-slate-400">${c.gs_verification_date || 'Pending'}</span>
      </div>
      <div class="flex justify-between text-slate-300">
        <span>SDLC Review:</span>
        <span class="font-mono text-slate-400">${c.sdlc_review_date || 'Pending'}</span>
      </div>
      <div class="flex justify-between text-slate-300">
        <span>DLC Approval:</span>
        <span class="font-mono text-slate-400">${c.dlc_approval_date || 'Pending'}</span>
      </div>
      ${c.delay_days > 0 ? `
        <div class="flex justify-between pt-1 border-t border-white/5 text-amber-400 font-semibold">
          <span>Inquiry Backlog:</span>
          <span>${c.delay_days} Days Exceeded</span>
        </div>
      ` : ''}
    </div>

    ${anomSection}

    <button onclick="triggerClaimDiagnostic('${c.claim_id}')" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-2 rounded-xl shadow-lg flex items-center justify-center gap-1.5 transition">
      <span>✨</span> Run AI Legal Diagnostic
    </button>
  `;
}

function closeInspector() {
  document.getElementById('inspector-drawer').classList.add('translate-x-full');
  if (deckState.activeTargetMarker) map.removeLayer(deckState.activeTargetMarker);
}

// 2D / 3D Mode Toggle
function switchSpatialMode(mode) {
  deckState.mode = mode;
  const mapEl = document.getElementById('webgis-map');
  const threeEl = document.getElementById('three-canvas-container');
  const btn2d = document.getElementById('btn-mode-2d');
  const btn3d = document.getElementById('btn-mode-3d');

  if (mode === '3d') {
    mapEl.classList.add('hidden');
    threeEl.classList.remove('hidden');

    btn3d.className = 'px-3 py-1 rounded-lg bg-emerald-600 text-white shadow transition';
    btn2d.className = 'px-3 py-1 rounded-lg text-slate-400 hover:text-white transition';

    if (!deckState.threeEngine) {
      deckState.threeEngine = new FRA3DTerrainEngine('three-canvas-container');
    } else {
      setTimeout(() => deckState.threeEngine.onWindowResize(), 100);
    }
  } else {
    threeEl.classList.add('hidden');
    mapEl.classList.remove('hidden');

    btn2d.className = 'px-3 py-1 rounded-lg bg-emerald-600 text-white shadow transition';
    btn3d.className = 'px-3 py-1 rounded-lg text-slate-400 hover:text-white transition';

    setTimeout(() => map.invalidateSize(), 100);
  }
}

// Filter listeners
function onFilterChange() {
  deckState.selectedState = document.getElementById('sel-state').value;
  deckState.selectedDistrict = document.getElementById('sel-district').value;
  deckState.selectedType = document.getElementById('sel-type').value;
  deckState.anomalyOnly = document.getElementById('chk-anomaly-only').checked;
  fetchAndRenderClaims();
}

function onDistrictChange() {
  onFilterChange();
  if (deckState.selectedDistrict) {
    const feat = deckState.districts.find(d => d.properties.district_code === deckState.selectedDistrict);
    if (feat) map.flyTo(feat.properties.center, 9, { duration: 1.2 });
  }
}

function handleQuickSearch(val) {
  deckState.searchQuery = val;
  fetchAndRenderClaims();
}

function filterByStage(stage) {
  deckState.selectedStage = stage;
  document.querySelectorAll('.stage-pill').forEach(p => {
    if (p.getAttribute('data-stage') === stage) {
      p.className = 'stage-pill active px-3 py-1.5 rounded-xl border border-transparent text-white font-bold';
    } else {
      p.className = 'stage-pill px-3 py-1.5 rounded-xl border border-transparent text-slate-400 hover:text-white font-medium';
    }
  });
  fetchAndRenderClaims();
}

function toggleLayer(layerName, visible) {
  if (layerName === 'districts') {
    if (visible) map.addLayer(districtsLayer);
    else map.removeLayer(districtsLayer);
  } else if (layerName === 'forest') {
    if (visible) map.addLayer(forestLayer);
    else map.removeLayer(forestLayer);
  }
}

function toggleLeftDock() {
  const dock = document.getElementById('left-dock');
  dock.classList.toggle('-translate-x-72');
}

function toggleRightDock() {
  const dock = document.getElementById('right-dock');
  dock.classList.toggle('translate-x-80');
}

// AI Rescan Trigger
async function triggerRescan() {
  const btn = document.getElementById('rescan-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="animate-spin">⏳</span> Scanning...';

  const res = await fetch('/api/anomalies/scan', { method: 'POST' });
  const data = await res.json();

  btn.disabled = false;
  btn.innerHTML = '<span>⚡</span> Rescan AI';

  await loadInitialTelemetry();
  alert(`AI Anomaly Scan Complete: Analyzed ${data.scan_results.total_claims_scanned} claims and indexed ${data.scan_results.total_anomalies_detected} anomalies.`);
}

// Executive Decision Dossier Modal
async function openDecisionModal(districtCode) {
  const dist = districtCode || deckState.selectedDistrict || 'OD_MAY';
  const modal = document.getElementById('decision-modal');
  modal.classList.remove('hidden');

  document.getElementById('modal-briefing-text').innerHTML = `
    <div class="flex flex-col items-center justify-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500 mb-3"></div>
      <span class="text-slate-400 text-xs">Generating legal synthesis for ${dist}...</span>
    </div>
  `;

  const res = await fetch(`/api/ai/district-brief/${dist}`, { method: 'POST' });
  const data = await res.json();

  document.getElementById('modal-dossier-title').textContent = `Executive Decision Dossier: ${data.district_name} (${data.state})`;

  // Update circular SVG gauge
  const m = data.metrics || {};
  const score = m.composite_risk_score || 50;
  document.getElementById('gauge-score-val').textContent = score;
  document.getElementById('gauge-tier-label').textContent = (m.risk_tier || 'NORMAL').replace('_', ' ');

  // 264 is the circle circumference (2 * pi * 42)
  const offset = 264 - (264 * Math.min(score, 100)) / 100;
  const gaugeCircle = document.getElementById('gauge-circle');
  gaugeCircle.style.strokeDashoffset = offset;
  gaugeCircle.style.stroke = score >= 65 ? '#f43f5e' : (score >= 40 ? '#f59e0b' : '#10b981');

  // Key cards
  document.getElementById('modal-conv-rate').textContent = `${m.rates?.title_distribution_rate ?? 0}%`;
  document.getElementById('modal-conv-bar').style.width = `${m.rates?.title_distribution_rate ?? 0}%`;
  document.getElementById('modal-area-ha').textContent = `${m.total_approved_area_ha ?? 0} Ha`;
  document.getElementById('modal-delay-count').textContent = m.delayed_claims ?? 0;
  document.getElementById('modal-avg-delay').textContent = `${m.avg_delay_days ?? 0} Days`;

  // Briefing text
  document.getElementById('modal-briefing-text').innerHTML = formatMarkdown(data.briefing_markdown);
}

function closeDecisionModal() {
  document.getElementById('decision-modal').classList.add('hidden');
}

// Single Claim Diagnostic
async function triggerClaimDiagnostic(claimId) {
  openDecisionModal();
  document.getElementById('modal-dossier-title').textContent = `AI Legal Diagnostic: ${claimId}`;
  document.getElementById('modal-briefing-text').innerHTML = `
    <div class="flex flex-col items-center justify-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500 mb-3"></div>
      <span class="text-slate-400 text-xs">Analyzing claim statutory validity...</span>
    </div>
  `;

  const res = await fetch(`/api/ai/analyze-claim/${claimId}`, { method: 'POST' });
  const data = await res.json();
  document.getElementById('modal-briefing-text').innerHTML = formatMarkdown(data.diagnostic_markdown);
}

function formatMarkdown(md) {
  if (!md) return '';
  return md
    .replace(/^### (.*$)/gim, '<h3 class="text-base font-extrabold text-white mt-4 mb-2">$1</h3>')
    .replace(/^#### (.*$)/gim, '<h4 class="text-xs font-bold text-emerald-400 uppercase tracking-wider mt-3 mb-1">$1</h4>')
    .replace(/\*\*(.*?)\*\*/gim, '<strong class="text-white font-bold">$1</strong>')
    .replace(/\*(.*?)\*/gim, '<em class="text-slate-300">$1</em>')
    .replace(/`(.*?)`/gim, '<code class="bg-slate-900 text-amber-400 px-1.5 py-0.5 rounded font-mono text-xs border border-white/5">$1</code>')
    .replace(/^\- (.*$)/gim, '<li class="ml-4 list-disc text-slate-300 mb-1">$1</li>')
    .replace(/\n\n/gim, '<br>');
}
