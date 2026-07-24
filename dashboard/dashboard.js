import { getLanguage, setLanguage, t, applyTranslations } from './dashboard_translations.js';
import { fmtNum, fmtCompact, updateNavPeriod } from './dashboard_report.js';
import {
  getSource,
  loadApi,
  loadRtkGain,
  loadLayerKpis,
  loadReportSummary,
  loadProviders,
  loadLayoutPrefs,
} from './dashboard_api.js';
import { renderCharts } from './dashboard_charts.js';
import { renderTables, renderComplianceTable, renderCrgTable } from './dashboard_tables.js';
import {
  applySectionOrder,
  applySectionCollapsed,
  toggleDashSection,
  bindPointerSectionReorder,
} from './dashboard_layout.js';
import {
  renderSubagentStats,
  renderSubagentTable,
  renderHookCompressionStats,
  renderRtkGainStats,
  renderEditStats,
  renderConsumptionStats,
  renderComplianceStats,
  renderAbTestKpis,
  renderOptimizationKpis,
  renderLayerKpis,
  renderStackKpis,
} from './dashboard_render.js';

// Controller/Module state
let currentEvents = [];
let rtkGainData = null;
let globalSessionUsage = {};
let refreshTimerId = null;
let refreshIntervalMs = 0;
let fileOverride = false;
let availableProviders = [];

const LS_REFRESH = 'cursor_telemetry_auto_refresh_ms';

function resizeVisibleCharts() {
  window.dispatchEvent(new Event('resize-charts'));
}

// Bind custom events to decouple module actions
window.addEventListener('sync-refresh-menu', (ev) => {
  syncRefreshMenuRadios(ev.detail);
});

window.addEventListener('update-header-title', () => {
  updateHeaderTitle();
});

function renderAll(events) {
  globalSessionUsage = {};
  events.forEach((e) => {
    if (e.event === 'afterAgentResponse') {
      for (const k of ['generation_id', 'session_id', 'conversation_id']) {
        const refId = e[k];
        if (typeof refId === 'string' && refId.trim()) {
          globalSessionUsage[refId.trim()] = e;
        }
      }
    }
  });

  const sumTok = events.reduce((s, e) => s + (e.approx_tokens || 0), 0);
  const sumTc = events.reduce((s, e) => s + (e.text_chars || 0), 0);

  document.getElementById('kpiEvents').textContent = fmtNum(events.length);
  document.getElementById('kpiTokens').textContent = fmtNum(sumTok);
  document.getElementById('kpiChars').textContent = fmtNum(sumTc);
  updateNavPeriod(events);

  renderEditStats(events);
  renderConsumptionStats(events);
  renderComplianceStats(events);
  renderComplianceTable(events);
  renderCrgTable(events);
  renderSubagentStats(events);
  renderSubagentTable(events, globalSessionUsage);
  renderStackKpis(events);
  const hookSummary = renderHookCompressionStats(events);
  renderRtkGainStats(rtkGainData, hookSummary.savedTokens);
  renderOptimizationKpis(events, rtkGainData);
  loadLayerKpis().then((lp) => renderLayerKpis(lp));
  loadReportSummary()
    .then((summary) => renderAbTestKpis(events, summary))
    .catch((err) => {
      console.warn('Failed to load AB report summary config:', err);
      renderAbTestKpis(events, null);
    });

  const isDark = !document.documentElement.classList.contains('theme-light');
  const bucket = document.getElementById('bucketSelect').value;
  renderCharts(events, bucket, isDark, rtkGainData);
  renderTables(events);
  resizeVisibleCharts();
}

async function initDashboardSections() {
  const container = document.getElementById('dashboardSections');
  if (!container) return;

  const prefs = await loadLayoutPrefs();
  applySectionOrder(container, prefs.order);
  applySectionCollapsed(prefs.collapsed);

  container.querySelectorAll('.dash-section').forEach((section) => {
    const toggle = section.querySelector('.dash-section-toggle');
    toggle?.addEventListener('click', (ev) => {
      ev.stopPropagation();
      toggleDashSection(section, container);
    });
  });

  bindPointerSectionReorder(container);
}

function clearAutoRefreshLoop() {
  if (refreshTimerId !== null) {
    clearInterval(refreshTimerId);
    refreshTimerId = null;
  }
}

function scheduleAutoRefreshLoop() {
  clearAutoRefreshLoop();
  if (refreshIntervalMs <= 0 || fileOverride) return;
  refreshTimerId = setInterval(() => {
    void silentRefreshFromApi();
  }, refreshIntervalMs);
}

function setRefreshMenuExpanded(open) {
  const dd = document.getElementById('refreshDropdown');
  const caret = document.getElementById('btnRefreshMenu');
  dd.hidden = !open;
  caret.setAttribute('aria-expanded', String(open));
}

function syncRefreshMenuRadios(activeMs) {
  document.querySelectorAll('#refreshDropdown button[data-interval-ms]').forEach((btn) => {
    const v = parseInt(btn.getAttribute('data-interval-ms'), 10);
    const on = v === activeMs;
    btn.setAttribute('data-active', on ? 'true' : 'false');
    btn.setAttribute('aria-checked', on ? 'true' : 'false');
  });
  const label = document.querySelector(`#refreshDropdown button[data-interval-ms="${activeMs}"]`);
  const short = label ? label.getAttribute('data-short') || label.textContent : '—';
  const labelEl = document.getElementById('refreshIntervalLabel');
  if (labelEl) labelEl.textContent = short;
}

function setRefreshInterval(ms) {
  const allowed = new Set([0, 300000, 1800000, 3600000]);
  refreshIntervalMs = allowed.has(ms) ? ms : 0;
  window.__refreshIntervalMs = refreshIntervalMs;
  try {
    localStorage.setItem(LS_REFRESH, String(refreshIntervalMs));
  } catch (_) {
    /* ignore */
  }
  syncRefreshMenuRadios(refreshIntervalMs);
  scheduleAutoRefreshLoop();
}

function restoreRefreshFromStorage() {
  let saved = 0;
  try {
    saved = parseInt(localStorage.getItem(LS_REFRESH) || '0', 10);
  } catch (_) {
    saved = 0;
  }
  const allowed = new Set([0, 300000, 1800000, 3600000]);
  refreshIntervalMs = allowed.has(saved) ? saved : 0;
  window.__refreshIntervalMs = refreshIntervalMs;
  syncRefreshMenuRadios(refreshIntervalMs);
  scheduleAutoRefreshLoop();
}

async function silentRefreshFromApi() {
  if (fileOverride) return;
  try {
    const rows = await loadApi();
    try {
      rtkGainData = await loadRtkGain();
    } catch (_) {
      rtkGainData = null;
    }
    currentEvents = rows;
    renderAll(currentEvents);
  } catch (_) {
    /* keep last good data */
  }
}

async function manualRefreshFromApi() {
  const svg = document.querySelector('#btnRefreshNow .refresh-ico');
  svg?.classList.add('refresh-ico-spin');
  try {
    const rows = await loadApi();
    try {
      rtkGainData = await loadRtkGain();
    } catch (_) {
      rtkGainData = null;
    }
    fileOverride = false;
    currentEvents = rows;
    renderAll(currentEvents);
    scheduleAutoRefreshLoop();
  } catch (e) {
    document.getElementById('kpiEvents').textContent = '!';
    updateNavPeriod(
      [],
      e.message === 'Failed to fetch' ? t('runServeDashboard') : String(e.message)
    );
  } finally {
    svg?.classList.remove('refresh-ico-spin');
  }
}

function readFilePromise(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result || ''));
    r.onerror = () => reject(r.error);
    r.readAsText(file);
  });
}

function parseJsonl(text) {
  const rows = [];
  text.split(/\r?\n/).forEach((line) => {
    line = line.trim();
    if (!line) return;
    try {
      rows.push(JSON.parse(line));
    } catch (_) {
      /* skip */
    }
  });
  return { rows };
}

document.getElementById('bucketSelect').addEventListener('change', () => {
  if (currentEvents.length) renderAll(currentEvents);
});

document.getElementById('btnRefreshNow').addEventListener('click', () => {
  void manualRefreshFromApi();
});

document.getElementById('btnRefreshMenu').addEventListener('click', (ev) => {
  ev.stopPropagation();
  const dd = document.getElementById('refreshDropdown');
  setRefreshMenuExpanded(dd.hidden);
});

document.querySelectorAll('#refreshDropdown button[data-interval-ms]').forEach((btn) => {
  btn.addEventListener('click', (ev) => {
    ev.stopPropagation();
    const ms = parseInt(btn.getAttribute('data-interval-ms'), 10);
    setRefreshInterval(ms);
    setRefreshMenuExpanded(false);
  });
});

document.addEventListener('click', (ev) => {
  const split = document.getElementById('refreshSplit');
  if (split && !split.contains(ev.target)) setRefreshMenuExpanded(false);
});

document.addEventListener('keydown', (ev) => {
  if (ev.key === 'Escape') setRefreshMenuExpanded(false);
});

document.getElementById('btnTheme').addEventListener('click', () => {
  document.documentElement.classList.toggle('theme-light');
  if (currentEvents.length) renderAll(currentEvents);
});

document.getElementById('btnReload').addEventListener('click', () => {
  document.getElementById('fileIn').click();
});

document.getElementById('fileIn').addEventListener('change', async (ev) => {
  const file = ev.target.files && ev.target.files[0];
  if (!file) return;
  const text = await readFilePromise(file);
  const { rows } = parseJsonl(text);
  currentEvents = rows;
  fileOverride = true;
  setRefreshInterval(0);
  renderAll(currentEvents);
  ev.target.value = '';
});

function showNoProvidersError() {
  const overlay = document.createElement('div');
  overlay.id = 'no-providers-error';
  overlay.innerHTML = `
        <div class="error-icon">⚠️</div>
        <h1>${t('noProvidersTitle')}</h1>
        <p>${t('noProvidersMessage')}</p>
        <pre><code># .env
TELEMETRY_CLAUDE_ENABLED=1
TELEMETRY_CURSOR_ENABLED=1
TELEMETRY_CODEX_ENABLED=1</code></pre>
      `;

  const style = document.createElement('style');
  style.textContent = `
        #no-providers-error {
          position: fixed !important;
          inset: 0 !important;
          z-index: 99999 !important;
          display: flex !important;
          flex-direction: column !important;
          align-items: center !important;
          justify-content: center !important;
          background: #1a1a2e !important;
          color: #fff !important;
          font-family: system-ui, sans-serif !important;
          text-align: center !important;
          padding: 2rem !important;
        }
        #no-providers-error .error-icon {
          font-size: 5rem !important;
          margin-bottom: 1.5rem !important;
        }
        #no-providers-error h1 {
          font-size: 2rem !important;
          margin: 0 0 1rem !important;
          color: #ff6b6b !important;
        }
        #no-providers-error p {
          font-size: 1.1rem !important;
          max-width: 500px !important;
          line-height: 1.6 !important;
          margin: 0 0 2rem !important;
        }
        #no-providers-error pre {
          background: rgba(0,0,0,0.4) !important;
          padding: 1.5rem 2rem !important;
          border-radius: 8px !important;
          font-size: 1rem !important;
          text-align: left !important;
          border: 1px solid rgba(255,255,255,0.2) !important;
          margin: 0 !important;
          color: #fff !important;
        }
      `;
  document.head.appendChild(style);
  document.body.appendChild(overlay);
}

function populateProviderSelect(providers, selectedId) {
  const select = document.getElementById('sourceSelect');
  if (!select) return;

  select.innerHTML = '';
  providers.forEach((provider) => {
    const option = document.createElement('option');
    option.value = provider.id;
    option.textContent = provider.label;
    select.appendChild(option);
  });

  if (providers.find((p) => p.id === selectedId)) {
    select.value = selectedId;
  } else if (providers.length > 0) {
    select.value = providers[0].id;
    try {
      localStorage.setItem('cursor_telemetry_source', providers[0].id);
    } catch (_) {}
  }
}

async function switchSource() {
  const source = getSource();
  try {
    localStorage.setItem('cursor_telemetry_source', source);
  } catch (_) {}

  updateHeaderTitle();

  const container = document.getElementById('dashboardSections');
  if (container) {
    try {
      const prefs = await loadLayoutPrefs();
      applySectionOrder(container, prefs.order);
      applySectionCollapsed(prefs.collapsed);
    } catch (e) {
      console.error('Failed to load layout preferences:', e);
    }
  }

  void manualRefreshFromApi();
}

function updateHeaderTitle() {
  const source = getSource();
  const titleEl = document.querySelector('.brand h1');
  if (titleEl) {
    const base = t('brandTitle');
    const provider = availableProviders.find((p) => p.id === source);
    const suffix = provider ? `(${provider.label})` : '(Cursor)';
    titleEl.textContent = `${base} ${suffix}`;
  }
}

document.getElementById('sourceSelect').addEventListener('change', () => {
  void switchSource();
});

window.addEventListener('resize-charts', () => {
  resizeVisibleCharts();
});

(async function init() {
  const lang = getLanguage();
  applyTranslations(lang);

  document.getElementById('langSelect').addEventListener('change', (ev) => {
    setLanguage(ev.target.value);
    if (currentEvents.length) renderAll(currentEvents);
    else applyTranslations(ev.target.value);
  });

  const providers = await loadProviders();

  if (providers.length === 0) {
    showNoProvidersError();
    return;
  }

  availableProviders = providers;

  let activeSource = 'cursor';
  try {
    activeSource = localStorage.getItem('cursor_telemetry_source') || 'cursor';
  } catch (_) {}

  populateProviderSelect(providers, activeSource);
  updateHeaderTitle();

  document.querySelector('.app').style.opacity = '1';

  await initDashboardSections();
  try {
    currentEvents = await loadApi();
    try {
      rtkGainData = await loadRtkGain();
    } catch (_) {
      rtkGainData = null;
    }
    renderAll(currentEvents);
    restoreRefreshFromStorage();
  } catch (e) {
    document.getElementById('kpiEvents').textContent = '!';
    updateNavPeriod(
      [],
      e.message === 'Failed to fetch' ? t('runServeDashboard') : String(e.message)
    );
    syncRefreshMenuRadios(0);
  }
})();
