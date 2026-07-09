import { getLanguage, setLanguage, t, applyTranslations } from './dashboard_translations.js';

import {
  fmtNum,
  fmtCompact,
  parseTs,
  fmtDateUtcCell,
  isSubagentLaunch,
  EVENT_COLORS,
  renderLaunchOptBadges,
  compressionSummary,
  hookSavedTokens,
  hookSavedPct,
} from './dashboard_utils.js';

import {
  getSource,
  loadApi,
  loadRtkGain,
  loadLayerKpis,
  loadProviders,
  persistLayoutPrefs,
  loadLayoutPrefs,
} from './dashboard_api.js';

import {
  summarizeStackKpis,
  summarizeOptimizationTotals,
  summarizeComplianceKpis,
} from './dashboard_stats.js';

import { renderCharts } from './dashboard_charts.js';

import { renderTables, renderComplianceTable, renderCrgTable } from './dashboard_tables.js';

// Controller/Module state
let currentEvents = [];
let rtkGainData = null;
let refreshTimerId = null;
let refreshIntervalMs = 0;
let fileOverride = false;
let availableProviders = [];

const LS_REFRESH = 'cursor_telemetry_auto_refresh_ms';
const DEFAULT_SECTION_ORDER = [
  'kpi-summary',
  'kpi-savings',
  'kpi-editing',
  'kpi-subagents',
  'kpi-stack',
  'kpi-compliance',
  'table-subagents',
  'table-compliance',
  'table-crg',
  'charts',
  'tables-lists',
];

function resizeVisibleCharts() {
  // Chart references will trigger chart resize event
  window.dispatchEvent(new Event('resize-charts'));
}

// Bind custom events to decouple module actions
window.addEventListener('sync-refresh-menu', (ev) => {
  syncRefreshMenuRadios(ev.detail);
});

window.addEventListener('update-header-title', () => {
  updateHeaderTitle();
});

function latestSessionKey(events) {
  const responses = events
    .filter((e) => e.event === 'afterAgentResponse')
    .sort((a, b) => (parseTs(b.ts)?.getTime() || 0) - (parseTs(a.ts)?.getTime() || 0));
  const latest = responses[0];
  if (!latest) return '';
  return latest.session_id || latest.conversation_id || '';
}

function eventsForCurrentTour(events) {
  const key = latestSessionKey(events);
  if (!key) {
    const cutoff = Date.now() - 2 * 60 * 60 * 1000;
    return events.filter((e) => {
      const d = parseTs(e.ts);
      return d && d.getTime() >= cutoff;
    });
  }
  return events.filter((e) => e.session_id === key || e.conversation_id === key);
}

function computeReportSummary(events) {
  let agentAdd = 0;
  let agentRem = 0;
  let agentPass = 0;
  let tabN = 0;
  let tabAdd = 0;
  let hookRuns = 0;
  let hookSaved = 0;
  let hookClaw = 0;
  let hookLlm = 0;
  let subLaunch = 0;
  let subStop = 0;
  let subStopHook = 0;
  let subStopFallback = 0;
  let subPromptTok = 0;
  let subOutTok = 0;
  let respN = 0;
  let respWithReport = 0;
  let respComplete = 0;
  let billedSum = 0;
  let adjustedBilledSum = 0;
  let billedN = 0;
  let cacheReadSum = 0;
  let cacheWriteSum = 0;
  let latestBilled = null;
  let latestAdjustedBilled = null;
  let latestIn = 0;
  let latestOut = 0;
  let latestCacheRead = 0;
  let latestCacheWrite = 0;

  const responses = events.filter((e) => e.event === 'afterAgentResponse');
  if (responses.length) {
    const latest = responses.reduce((a, b) =>
      (parseTs(b.ts)?.getTime() || 0) >= (parseTs(a.ts)?.getTime() || 0) ? b : a
    );
    if (typeof latest.billed_total_tokens === 'number') {
      latestBilled = latest.billed_total_tokens;
      latestIn = Number(latest.input_tokens || 0);
      latestOut = Number(latest.output_tokens || 0);
      latestCacheRead = Number(latest.cache_read_tokens || 0);
      latestCacheWrite = Number(latest.cache_write_tokens || 0);
      latestAdjustedBilled = Math.round(
        Math.max(0, latestIn - latestCacheRead) + latestCacheRead * 0.1 + latestOut
      );
    }
  }

  events.forEach((e) => {
    if (e.event === 'afterFileEdit') {
      agentAdd += Number(e.lines_added || 0);
      agentRem += Number(e.lines_removed || 0);
      agentPass++;
    }
    if (e.event === 'afterTabFileEdit') {
      tabN++;
      tabAdd += Number(e.lines_added || 0);
    }
    if (e.event === 'afterAgentResponse') {
      respN++;
      if (e.consumption_present === true) respWithReport++;
      if (e.consumption_complete === true) respComplete++;
      if (typeof e.billed_total_tokens === 'number') {
        billedSum += e.billed_total_tokens;
        billedN++;
        const inp = Number(e.input_tokens || 0);
        const out = Number(e.output_tokens || 0);
        const cRead = Number(e.cache_read_tokens || 0);
        const cWrite = Number(e.cache_write_tokens || 0);
        cacheReadSum += cRead;
        cacheWriteSum += cWrite;
        const adjIn = Math.max(0, inp - cRead) + cRead * 0.1;
        adjustedBilledSum += Math.round(adjIn + out);
      }
    }
    if (isSubagentLaunch(e)) {
      hookRuns++;
      hookSaved += hookSavedTokens(e);
      if (e.compression_used_claw_compactor === true) hookClaw++;
      if (e.compression_used_llmlingua === true) hookLlm++;
      subLaunch++;
      subPromptTok += Number(e.compression_after_tokens || e.approx_tokens || 0);
    }
    if (e.event === 'subagentStop') {
      subStop++;
      subOutTok += Number(e.approx_tokens || 0);
      const src = String(e.subagent_stop_source || '');
      if (src === 'hook') subStopHook++;
      else if (src === 'postToolUse_fallback') subStopFallback++;
    }
  });

  const tour = eventsForCurrentTour(events);
  const tourLaunches = tour.filter(isSubagentLaunch).length;
  const tourStops = tour.filter((e) => e.event === 'subagentStop').length;

  return {
    edit: {
      lines_added: agentAdd,
      lines_removed: agentRem,
      passes: agentPass,
      tab_accepted: tabN,
      tab_lines_added: tabAdd,
    },
    consumption_coverage: {
      with_report: respWithReport,
      complete: respComplete,
      responses: respN,
    },
    hook_compression: {
      runs: hookRuns,
      saved_tokens: hookSaved,
      claw: hookClaw,
      llmlingua: hookLlm,
    },
    subagents: {
      launch: subLaunch,
      stop: subStop,
      stop_hook: subStopHook,
      stop_post_tool_fallback: subStopFallback,
      prompt_proxy_tokens: subPromptTok,
      out_proxy_tokens: subOutTok,
      coverage_pct: subLaunch > 0 ? Math.round((100 * subStop) / subLaunch) : 0,
    },
    compliance: summarizeComplianceKpis(events),
    parent_billed: {
      sum: billedSum,
      adjusted_sum: adjustedBilledSum,
      avg: billedN ? Math.floor(billedSum / billedN) : 0,
      adjusted_avg: billedN ? Math.floor(adjustedBilledSum / billedN) : 0,
      count: billedN,
      latest: latestBilled,
      latest_adjusted: latestAdjustedBilled,
      latest_input: latestIn,
      latest_output: latestOut,
      cache_read_sum: cacheReadSum,
      cache_write_sum: cacheWriteSum,
    },
    tour: { launches: tourLaunches, stops: tourStops },
  };
}

function applyReportSummary(summary) {
  if (!summary) return;
  const sub = summary.subagents || {};
  const billed = summary.parent_billed || {};
  const tour = summary.tour || {};

  document.getElementById('kpiSubLaunch').textContent = fmtNum(sub.launch || 0);
  document.getElementById('kpiSubStop').textContent = fmtNum(sub.stop || 0);
  document.getElementById('kpiSubStopSub').textContent =
    sub.stop > 0
      ? t('subStopSubVal', {
          hook: fmtNum(sub.stop_hook || 0),
          fallback: fmtNum(sub.stop_post_tool_fallback || 0),
        })
      : 'subagentStop · postToolUse';
  document.getElementById('kpiSubLaunchSub').textContent =
    tour.launches !== sub.launch
      ? t('subLaunchSubVal', { tour: fmtNum(tour.launches) })
      : t('alignedReport');

  if (billed.count) {
    if (billed.cache_read_sum > 0) {
      document.getElementById('kpiParentBilled').textContent = fmtCompact(billed.adjusted_avg || 0);
      document.getElementById('kpiParentBilledSub').textContent = t('avgSumLatestCacheAdjusted', {
        sum: fmtCompact(billed.sum || 0),
        adjSum: fmtCompact(billed.adjusted_sum || 0),
        count: fmtNum(billed.count),
        latest: fmtCompact(billed.latest || 0),
        latestAdj: fmtCompact(billed.latest_adjusted || 0),
      });
    } else {
      document.getElementById('kpiParentBilled').textContent = fmtCompact(billed.avg || 0);
      document.getElementById('kpiParentBilledSub').textContent = t('avgSumLatest', {
        sum: fmtCompact(billed.sum || 0),
        count: fmtNum(billed.count),
        latest: fmtCompact(billed.latest || 0),
      });
    }
  } else {
    document.getElementById('kpiParentBilled').textContent = '—';
    document.getElementById('kpiParentBilledSub').textContent = t('notExposed');
  }

  document.getElementById('kpiSubPromptTok').textContent = fmtCompact(sub.prompt_proxy_tokens || 0);
  document.getElementById('kpiSubOutTok').textContent = fmtCompact(sub.out_proxy_tokens || 0);
  document.getElementById('kpiSubPromptSub').textContent = t('launchCount', {
    count: fmtNum(sub.launch || 0),
  });
  document.getElementById('kpiSubOutSub').textContent = t('stopCount', {
    count: fmtNum(sub.stop || 0),
  });
}

function renderSubagentStats(events) {
  applyReportSummary(computeReportSummary(events));
}

function renderSubagentTable(events) {
  const list = document.getElementById('subagentList');
  const head = document.getElementById('subagentHead');
  const empty = document.getElementById('emptySubagents');
  list.replaceChildren();

  const launches = events
    .filter(isSubagentLaunch)
    .sort((a, b) => (parseTs(b.ts)?.getTime() || 0) - (parseTs(a.ts)?.getTime() || 0))
    .slice(0, 40);
  const stopsByTs = events
    .filter((e) => e.event === 'subagentStop')
    .sort((a, b) => (parseTs(a.ts)?.getTime() || 0) - (parseTs(b.ts)?.getTime() || 0));

  const rows = launches
    .map((launch) => {
      const launchTs = parseTs(launch.ts)?.getTime() || 0;
      const stop = stopsByTs.find((s) => (parseTs(s.ts)?.getTime() || 0) >= launchTs);
      return { launch, stop };
    })
    .sort((a, b) => (parseTs(b.launch.ts)?.getTime() || 0) - (parseTs(a.launch.ts)?.getTime() || 0))
    .slice(0, 20);

  empty.hidden = rows.length > 0;
  list.hidden = rows.length === 0;
  head.hidden = rows.length === 0;

  rows.forEach(({ launch, stop }) => {
    const row = document.createElement('div');
    row.className = 'feed-row';
    row.style.setProperty('--accent', EVENT_COLORS.subagentLaunch);
    const bar = document.createElement('div');
    bar.className = 'feed-row-accent';
    const cols = document.createElement('div');
    cols.className = 'feed-cols subagent-row-cols';

    const cDate = document.createElement('div');
    cDate.className = 'mono cell-wide';
    cDate.textContent = fmtDateUtcCell(launch.ts);

    const cType = document.createElement('div');
    const typePill = document.createElement('span');
    typePill.className = 'tool-pill';
    typePill.textContent = launch.subagent_type || 'Task';
    cType.appendChild(typePill);

    const cSkill = document.createElement('div');
    const skillPill = document.createElement('span');
    skillPill.className = 'evt-pill';
    skillPill.textContent = launch.skill_hint || '—';
    cSkill.appendChild(skillPill);

    const cDesc = document.createElement('div');
    cDesc.className = 'mono cell-wide';
    cDesc.textContent = (launch.subagent_description || '—').slice(0, 120);

    const cBadges = document.createElement('div');
    cBadges.className = 'cell-badges';
    cBadges.style.display = 'flex';
    cBadges.style.flexWrap = 'wrap';
    cBadges.style.gap = '0.25rem';
    renderLaunchOptBadges(launch, cBadges);

    const cCompress = document.createElement('div');
    const comp = compressionSummary(launch);
    const compressPill = document.createElement('span');
    compressPill.className = 'evt-pill compress-pill';
    if (launch.compression_used_claw_compactor && launch.compression_used_llmlingua)
      compressPill.classList.add('claw');
    else if (launch.compression_used_claw_compactor) compressPill.classList.add('claw');
    else if (launch.compression_used_llmlingua) compressPill.classList.add('llm');
    else compressPill.classList.add('none');

    const savedVal = hookSavedTokens(launch);
    const pctVal = hookSavedPct(launch);
    const pctLabel = savedVal > 0 ? ` −${pctVal.toFixed(0)}%` : '';
    compressPill.textContent = `${savedVal > 0 ? 'opt' : 'none'}${pctLabel}`;
    compressPill.title = comp;
    cCompress.appendChild(compressPill);

    const cPrompt = document.createElement('div');
    cPrompt.className = 'num strong';
    const afterTok = launch.compression_after_tokens || launch.approx_tokens || 0;
    const inputTok = launch.compression_input_tokens || 0;
    cPrompt.textContent = fmtNum(afterTok);
    if (inputTok > 0 && inputTok !== afterTok) {
      cPrompt.title = `input≈${fmtNum(inputTok)} → sent≈${fmtNum(afterTok)}`;
    }

    const cOut = document.createElement('div');
    cOut.className = 'num';
    cOut.textContent = stop ? fmtNum(stop.approx_tokens || 0) : '—';

    const cStatus = document.createElement('div');
    const statusPill = document.createElement('span');
    statusPill.className = 'evt-pill';
    statusPill.textContent = stop?.subagent_status || 'running?';
    cStatus.appendChild(statusPill);

    cols.appendChild(cDate);
    cols.appendChild(cType);
    cols.appendChild(cSkill);
    cols.appendChild(cDesc);
    cols.appendChild(cBadges);
    cols.appendChild(cCompress);
    cols.appendChild(cPrompt);
    cols.appendChild(cOut);
    cols.appendChild(cStatus);
    row.appendChild(bar);
    row.appendChild(cols);
    list.appendChild(row);
  });
}

function renderHookCompressionStats(events) {
  const rows = events.filter(isSubagentLaunch);
  const count = rows.length;
  const savedTokens = rows.reduce((sum, e) => sum + hookSavedTokens(e), 0);
  const usedClaw = rows.filter((e) => e.compression_used_claw_compactor === true).length;
  const usedLingu = rows.filter((e) => e.compression_used_llmlingua === true).length;
  const backends = {};
  rows.forEach((e) => {
    const b = String(e.compression_backend || 'unknown');
    backends[b] = (backends[b] || 0) + 1;
  });
  let avgPct = 0;
  if (count) {
    avgPct = rows.reduce((sum, e) => sum + hookSavedPct(e), 0) / count;
  }

  document.getElementById('kpiHookSaved').textContent = fmtCompact(savedTokens);
  if (!count) {
    document.getElementById('kpiHookSub').textContent = t('noHookMeasurements');
  } else {
    const backendHint = Object.entries(backends)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 2)
      .map(([k, n]) => `${k}×${n}`)
      .join(' · ');
    document.getElementById('kpiHookSub').textContent = t('hookSummarySub', {
      count: fmtNum(count),
      pct: avgPct.toFixed(1),
      claw: fmtNum(usedClaw),
      llm: fmtNum(usedLingu),
      backend: backendHint ? ` · ${backendHint}` : '',
    });
  }
  return { savedTokens };
}

function renderRtkGainStats(rtkGain, hookSavedTokens) {
  const savedEl = document.getElementById('kpiRtkSaved');
  const subEl = document.getElementById('kpiRtkSub');
  const totalEl = document.getElementById('kpiTotalSaved');
  const totalSubEl = document.getElementById('kpiTotalSub');
  if (!rtkGain || typeof rtkGain !== 'object') {
    savedEl.textContent = '—';
    subEl.textContent = t('rtkUnavailable');
    totalEl.textContent = fmtCompact(hookSavedTokens || 0);
    totalSubEl.textContent = t('hookOnlyRtkUnavailable');
    return;
  }

  const g = rtkGain.global || {};
  const p = rtkGain.project || {};
  const gs = g.summary || {};
  const ps = p.summary || {};

  if (g.ok !== true || typeof gs.total_saved !== 'number') {
    savedEl.textContent = '—';
    const err = String(g.error || t('globalUnavailable')).slice(0, 64);
    subEl.textContent = t('globalUnavailableErr', { err });
    totalEl.textContent = fmtCompact(hookSavedTokens || 0);
    totalSubEl.textContent = t('hookOnlyGlobalUnavailable');
    return;
  }

  const gSaved = Number(gs.total_saved || 0);
  savedEl.textContent = fmtCompact(gSaved);
  const totalSaved = gSaved + Number(hookSavedTokens || 0);
  totalEl.textContent = fmtCompact(totalSaved);

  const gpct = Number(gs.avg_savings_pct || 0).toFixed(1);
  if (p.ok === true && typeof ps.total_saved === 'number') {
    const pSaved = Number(ps.total_saved || 0);
    const ppct = Number(ps.avg_savings_pct || 0).toFixed(1);
    subEl.textContent = t('gProjects', {
      gPct: gpct,
      gSaved: fmtCompact(gSaved),
      pPct: ppct,
      pSaved: fmtCompact(pSaved),
    });
    totalSubEl.textContent = t('rtkGlobalHook', { hook: fmtCompact(hookSavedTokens || 0) });
  } else {
    subEl.textContent = t('gOnly', { gPct: gpct });
    totalSubEl.textContent = t('rtkGlobalHook', { hook: fmtCompact(hookSavedTokens || 0) });
  }
}

function periodLabel(events) {
  const dates = events
    .map((e) => parseTs(e.ts))
    .filter(Boolean)
    .sort((a, b) => a - b);
  if (!dates.length) return '—';
  const a = dates[0];
  const b = dates[dates.length - 1];
  const locale = getLanguage() === 'fr' ? 'fr-FR' : 'en-US';
  const fmt = (d) =>
    d.toLocaleDateString(locale, {
      day: 'numeric',
      month: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  return `${fmt(a)} → ${fmt(b)}`;
}

function updateNavPeriod(events, overrideText) {
  const el = document.getElementById('navPeriod');
  if (!el) return;
  if (overrideText !== undefined) {
    el.textContent = overrideText;
    el.removeAttribute('datetime');
    el.removeAttribute('title');
    return;
  }
  const label = periodLabel(events);
  el.textContent = label;
  const dates = events
    .map((e) => parseTs(e.ts))
    .filter(Boolean)
    .sort((a, b) => a - b);
  if (dates.length) {
    el.setAttribute(
      'datetime',
      `${dates[0].toISOString()}/${dates[dates.length - 1].toISOString()}`
    );
    el.setAttribute('title', label);
  } else {
    el.removeAttribute('datetime');
    el.removeAttribute('title');
  }
}

function renderEditStats(events) {
  let agentAdd = 0;
  let agentRem = 0;
  let agentPass = 0;
  let tabN = 0;
  let tabAdd = 0;
  events.forEach((e) => {
    const isEditEvent =
      e.event === 'afterFileEdit' ||
      (e.event === 'postToolUse' &&
        (e.tool === 'Edit' || e.tool === 'Write') &&
        (e.lines_added || e.lines_removed));
    if (isEditEvent) {
      agentAdd += Number(e.lines_added || 0);
      agentRem += Number(e.lines_removed || 0);
      agentPass++;
    }
    if (e.event === 'afterTabFileEdit') {
      tabN++;
      tabAdd += Number(e.lines_added || 0);
    }
  });
  document.getElementById('kpiAgentAdd').textContent = fmtNum(agentAdd);
  document.getElementById('kpiAgentRem').textContent = fmtNum(agentRem);
  document.getElementById('kpiAgentPass').textContent = fmtNum(agentPass);
  document.getElementById('kpiTabN').textContent = fmtNum(tabN);
  document.getElementById('kpiTabLines').textContent = fmtNum(tabAdd);
}

function renderConsumptionStats(events) {
  const c = summarizeComplianceKpis(events).consumption;
  const total = c.responses;
  const complete = c.complete;

  document.getElementById('kpiConso').textContent =
    total > 0 ? `${fmtNum(complete)} / ${fmtNum(total)}` : '—';
  if (!total) {
    document.getElementById('kpiConsoSub').textContent = t('noAgentResponses');
  } else {
    document.getElementById('kpiConsoSub').textContent = t('completeFields', {
      pct: c.complete_pct,
    });
  }
}

function setComplianceChipState(chipId, pct, warnBelow = 70) {
  const chip = document.getElementById(chipId);
  if (!chip) return;
  chip.classList.remove('compliance-ok', 'compliance-warn');
  if (pct >= warnBelow) chip.classList.add('compliance-ok');
  else if (pct > 0) chip.classList.add('compliance-warn');
}

function renderComplianceStats(events) {
  const comp = summarizeComplianceKpis(events);
  const c = comp.consumption;
  const b = comp.task_brief;

  document.getElementById('kpiConsoComplete').textContent =
    c.responses > 0 ? `${fmtNum(c.complete)} / ${fmtNum(c.responses)}` : '—';
  document.getElementById('kpiConsoCompleteSub').textContent =
    c.responses > 0
      ? t('completeHookChecks', { pct: c.complete_pct, checks: fmtNum(c.hook_checks) })
      : 'afterAgentResponse';

  document.getElementById('kpiConsoPresent').textContent =
    c.responses > 0 ? `${fmtNum(c.present)} / ${fmtNum(c.responses)}` : '—';
  document.getElementById('kpiConsoPresentSub').textContent =
    c.responses > 0 ? t('blockDetectedPartial', { pct: c.present_pct }) : t('partialIncomplete');

  document.getElementById('kpiConsoHookFollowups').textContent = fmtNum(c.hook_followups);
  document.getElementById('kpiConsoHookSub').textContent = t('consoHookSub', {
    ok: fmtNum(c.hook_ok),
    giveups: fmtNum(c.hook_giveups),
  });

  document.getElementById('kpiBriefPass').textContent =
    b.attempts > 0 ? `${fmtNum(b.launches)} / ${fmtNum(b.attempts)}` : fmtNum(b.launches);
  document.getElementById('kpiBriefPassSub').textContent =
    b.attempts > 0 ? t('passRate', { pct: b.pass_rate_pct }) : t('noTaskAttempts');

  document.getElementById('kpiBriefDenied').textContent = fmtNum(b.denied);
  document.getElementById('kpiBriefDeniedSub').textContent =
    b.denied > 0 ? t('briefRejected') : t('noBlocks');

  setComplianceChipState('chipConsoComplete', c.complete_pct, 80);
  setComplianceChipState('chipBriefPass', b.pass_rate_pct, 85);
}

function renderOptimizationKpis(events, rtkGain) {
  const tData = summarizeOptimizationTotals(events, rtkGain);
  document.getElementById('kpiObserved').textContent = fmtCompact(tData.observed);
  document.getElementById('kpiCounterfactual').textContent = fmtCompact(tData.counterfactual);
  document.getElementById('kpiOptSaved').textContent = fmtCompact(tData.savings);
  document.getElementById('kpiOptPct').textContent =
    tData.counterfactual > 0 ? `${tData.pct.toFixed(1)} %` : '—';
  document.getElementById('kpiObservedSub').textContent = t('billedSubagentProxies');
  document.getElementById('kpiOptSavedSub').textContent = t('rtkHookDiff', {
    rtk: fmtCompact(tData.rtk),
    hook: fmtCompact(tData.hookDiff),
  });
  document.getElementById('kpiOptPctSub').textContent =
    tData.counterfactual > 0
      ? t('savedOutOf', {
          savings: fmtCompact(tData.savings),
          counterfactual: fmtCompact(tData.counterfactual),
        })
      : t('insufficientData');
}

function renderLayerKpis(layerPayload) {
  const host = document.getElementById('kpiLayersTable');
  const hint = document.getElementById('kpiLayersHint');
  if (!host) return;
  if (!layerPayload || !layerPayload.layers) {
    host.innerHTML = `<p class="hint">${t('layersUnavailable')}</p>`;
    return;
  }
  const layers = layerPayload.layers;
  const blended = layerPayload.blended || {};
  const legacy = layerPayload.legacy_global || {};
  const chat = layerPayload.chat_parent || {};
  const rows = [
    ['rtk_shell', t('rtk_shell')],
    ['task_compression', t('task_compression')],
    ['guardrail_read', t('guardrail_read')],
    ['guardrail_task', t('guardrail_task')],
    ['diff_only', t('diff_only')],
    ['code_review_graph', t('code_review_graph')],
  ];
  let html = `<div class="layers-head"><span>${t('layer')}</span><span>${t('savings')}</span><span>${t('observed')}</span><span>${t('pctLayer')}</span></div>`;
  rows.forEach(([key, label]) => {
    const L = layers[key] || {};
    const pct = Number(L.pct || 0).toFixed(1);
    const avail =
      L.available === false ? (getLanguage() === 'fr' ? ' (RTK désactivé)' : ' (RTK off)') : '';
    html += `<div class="layers-row"><span>${label}${avail}</span><span>${fmtCompact(L.savings_tokens || 0)}</span><span>${fmtCompact(L.observed_tokens || 0)}</span><span>${pct}%</span></div>`;
  });
  html += `<div class="layers-row layers-blend"><span>${t('blendExcludingChat')}</span><span>${fmtCompact(blended.savings_tokens || 0)}</span><span>${fmtCompact(blended.observed_tokens || 0)}</span><span>${Number(blended.pct || 0).toFixed(1)}%</span></div>`;
  html += `<div class="layers-row layers-legacy"><span>${t('legacyGlobal')}</span><span>${fmtCompact(legacy.savings_tokens || 0)}</span><span>${fmtCompact(legacy.observed_tokens || 0)}</span><span>${Number(legacy.pct || 0).toFixed(1)}%</span></div>`;
  html += `<div class="layers-row layers-chat"><span>${t('parentChatInfo')}</span><span>—</span><span>${fmtCompact(chat.observed_tokens || 0)}</span><span>—</span></div>`;
  host.innerHTML = html;
  if (hint && blended.note) {
    hint.textContent = blended.note + ' · ' + (legacy.note || '');
  }
}

function renderStackKpis(events) {
  const s = summarizeStackKpis(events);
  document.getElementById('kpiGitCacheHits').textContent = fmtNum(s.gitHits);
  document.getElementById('kpiGitCacheSub').textContent =
    s.launches > 0
      ? t('gitCacheHitsSub', {
          hits: s.gitHits,
          launches: s.launches,
          preserved: fmtCompact(s.gitPreserved),
        })
      : t('noTaskLaunches');
  document.getElementById('kpiGuardrailIntercepts').textContent = fmtNum(s.intercepts);
  document.getElementById('kpiGuardrailSub').textContent =
    s.launches > 0
      ? t('guardrailSub', { intercepts: s.intercepts, launches: s.launches, halts: s.halts })
      : t('tokenBudgetGuardrail');
  document.getElementById('kpiGuardrailAvoided').textContent = fmtCompact(s.avoided);
  document.getElementById('kpiGuardrailAvoidedSub').textContent =
    s.avoided > 0 ? t('inOutAvoided') : t('noInterceptsRecorded');
  const idemPct = s.launches > 0 ? Math.round((100 * s.idem) / s.launches) : 0;
  document.getElementById('kpiIdempotent').textContent =
    s.launches > 0 ? `${fmtNum(s.idem)} / ${fmtNum(s.launches)}` : '—';
  document.getElementById('kpiIdempotentSub').textContent =
    s.launches > 0 ? t('briefsTagged', { pct: idemPct }) : t('idempotentContext');
}

function renderAll(events) {
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
  renderSubagentTable(events);
  renderStackKpis(events);
  const hookSummary = renderHookCompressionStats(events);
  renderRtkGainStats(rtkGainData, hookSummary.savedTokens);
  renderOptimizationKpis(events, rtkGainData);
  loadLayerKpis().then((lp) => renderLayerKpis(lp));

  const isDark = !document.documentElement.classList.contains('theme-light');
  const bucket = document.getElementById('bucketSelect').value;
  renderCharts(events, bucket, isDark, rtkGainData);
  renderTables(events);
  resizeVisibleCharts();
}

function collectLayoutState(container) {
  return {
    order: [...container.querySelectorAll('.dash-section')].map((s) => s.dataset.sectionId),
    collapsed: [...document.querySelectorAll('.dash-section.is-collapsed')].map(
      (s) => s.dataset.sectionId
    ),
  };
}

function applySectionOrder(container, order) {
  if (!Array.isArray(order)) order = DEFAULT_SECTION_ORDER.slice();
  const known = new Set(
    [...container.querySelectorAll('.dash-section')].map((s) => s.dataset.sectionId)
  );
  order = order.filter((id) => known.has(id));
  DEFAULT_SECTION_ORDER.forEach((id) => {
    if (known.has(id) && !order.includes(id)) order.push(id);
  });
  order.forEach((id) => {
    const el = container.querySelector(`[data-section-id="${id}"]`);
    if (el) container.appendChild(el);
  });
}

function applySectionCollapsed(collapsed) {
  if (!Array.isArray(collapsed)) collapsed = [];
  const set = new Set(collapsed);
  document.querySelectorAll('.dash-section').forEach((section) => {
    const id = section.dataset.sectionId;
    const isCollapsed = set.has(id);
    section.classList.toggle('is-collapsed', isCollapsed);
    const btn = section.querySelector('.dash-section-toggle');
    if (btn) btn.setAttribute('aria-expanded', String(!isCollapsed));
  });
}

function toggleDashSection(section, container) {
  const willCollapse = !section.classList.contains('is-collapsed');
  section.classList.toggle('is-collapsed', willCollapse);
  const btn = section.querySelector('.dash-section-toggle');
  if (btn) btn.setAttribute('aria-expanded', String(!willCollapse));
  persistLayoutPrefs(container, collectLayoutState);
  if (!willCollapse) resizeVisibleCharts();
}

function sectionDropTarget(container, clientY, dragging) {
  const sections = [...container.querySelectorAll('.dash-section')].filter((s) => s !== dragging);
  let closest = { offset: Number.NEGATIVE_INFINITY, element: null, after: false };
  for (const child of sections) {
    const box = child.getBoundingClientRect();
    const offset = clientY - box.top - box.height / 2;
    if (offset < 0 && offset > closest.offset) {
      closest = { offset, element: child, after: false };
    }
  }
  if (!closest.element && sections.length) {
    const last = sections[sections.length - 1];
    const box = last.getBoundingClientRect();
    if (clientY > box.bottom - 8) {
      return { element: last, after: true };
    }
  }
  return closest.element ? { element: closest.element, after: closest.after } : null;
}

function bindPointerSectionReorder(container) {
  let dragging = null;
  let marker = null;

  function clearDragUi() {
    dragging?.classList.remove('is-pointer-dragging');
    dragging = null;
    marker?.remove();
    marker = null;
    container.querySelectorAll('.dash-section').forEach((s) => s.classList.remove('is-drag-over'));
  }

  function placeMarker(target, after) {
    if (!marker) {
      marker = document.createElement('div');
      marker.className = 'dash-section-drop-marker';
      marker.setAttribute('aria-hidden', 'true');
    }
    if (!target) {
      container.appendChild(marker);
      return;
    }
    if (after) target.after(marker);
    else target.before(marker);
  }

  container.querySelectorAll('.dash-section-drag-handle').forEach((handle) => {
    handle.addEventListener('pointerdown', (ev) => {
      if (ev.button !== 0) return;
      dragging = handle.closest('.dash-section');
      if (!dragging) return;
      dragging.classList.add('is-pointer-dragging');
      handle.setPointerCapture(ev.pointerId);
      ev.preventDefault();
    });
    handle.addEventListener('pointermove', (ev) => {
      if (!dragging || !handle.hasPointerCapture(ev.pointerId)) return;
      const target = sectionDropTarget(container, ev.clientY, dragging);
      if (!target) {
        placeMarker(null, true);
        return;
      }
      target.element.classList.add('is-drag-over');
      container.querySelectorAll('.dash-section').forEach((s) => {
        if (s !== target.element) s.classList.remove('is-drag-over');
      });
      placeMarker(target.element, target.after);
    });
    handle.addEventListener('pointerup', (ev) => {
      if (!dragging) return;
      try {
        handle.releasePointerCapture(ev.pointerId);
      } catch (_) {
        /* ignore */
      }
      if (marker && marker.parentNode) {
        marker.parentNode.insertBefore(dragging, marker);
      } else {
        const target = sectionDropTarget(container, ev.clientY, dragging);
        if (target?.element) {
          if (target.after) target.element.after(dragging);
          else target.element.before(dragging);
        }
      }
      clearDragUi();
      persistLayoutPrefs(container, collectLayoutState);
      resizeVisibleCharts();
    });
    handle.addEventListener('pointercancel', () => {
      clearDragUi();
    });
  });
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

// Window resize listener to trigger Chart.js resizes dynamically
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
