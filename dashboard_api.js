export const LS_SECTION_ORDER = 'cursor_telemetry_dash_section_order';
export const LS_SECTION_COLLAPSED = 'cursor_telemetry_dash_section_collapsed';

export function getSource() {
  const select = document.getElementById('sourceSelect');
  if (select) {
    return select.value;
  }
  try {
    return localStorage.getItem('cursor_telemetry_source') || 'cursor';
  } catch (_) {
    return 'cursor';
  }
}

export async function loadApi() {
  const res = await fetch('/api/events?source=' + getSource());
  if (!res.ok) throw new Error('API ' + res.status);
  return res.json();
}

export async function loadRtkGain() {
  const res = await fetch('/api/rtk-gain?source=' + getSource());
  if (!res.ok) throw new Error('RTK API ' + res.status);
  return res.json();
}

export async function loadLayerKpis() {
  const res = await fetch('/api/layer-kpis?source=' + getSource());
  if (!res.ok) throw new Error('Layer KPIs API ' + res.status);
  return res.json();
}

export async function loadReportSummary() {
  const res = await fetch('/api/report-summary?source=' + getSource());
  if (!res.ok) throw new Error('Report summary API ' + res.status);
  return res.json();
}

export async function loadProviders() {
  try {
    const resp = await fetch('/api/providers');
    if (!resp.ok) throw new Error('Failed to load providers');
    return resp.json();
  } catch (e) {
    console.error('Failed to load providers:', e);
    return [];
  }
}

export function persistLayoutPrefs(container, collectLayoutState) {
  const state = collectLayoutState(container);
  try {
    localStorage.setItem(LS_SECTION_ORDER + '_' + getSource(), JSON.stringify(state.order));
    localStorage.setItem(LS_SECTION_COLLAPSED + '_' + getSource(), JSON.stringify(state.collapsed));
  } catch (_) {
    /* ignore */
  }
  void fetch('/api/dashboard-layout?source=' + getSource(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ version: 1, ...state }),
  }).catch(() => {
    /* offline or old server */
  });
}

export async function loadLayoutPrefs() {
  try {
    const res = await fetch('/api/dashboard-layout?source=' + getSource());
    if (res.ok) {
      const data = await res.json();
      if (data && (Array.isArray(data.order) || Array.isArray(data.collapsed))) {
        return {
          order: Array.isArray(data.order) ? data.order : null,
          collapsed: Array.isArray(data.collapsed) ? data.collapsed : [],
        };
      }
    }
  } catch (_) {
    /* fallback below */
  }
  let order = null;
  let collapsed = [];
  try {
    order = JSON.parse(localStorage.getItem(LS_SECTION_ORDER + '_' + getSource()) || 'null');
  } catch (_) {
    order = null;
  }
  try {
    collapsed = JSON.parse(localStorage.getItem(LS_SECTION_COLLAPSED + '_' + getSource()) || '[]');
  } catch (_) {
    collapsed = [];
  }
  return { order, collapsed };
}
