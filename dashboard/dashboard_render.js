import { getLanguage, t } from './dashboard_translations.js';
import {
  fmtNum,
  fmtCompact,
  parseTs,
  isSubagentLaunch,
  hookSavedTokens,
  hookSavedPct,
  EVENT_COLORS,
  fmtDateUtcCell,
  renderLaunchOptBadges,
  compressionSummary,
} from './dashboard_utils.js';
import { computeReportSummary, applyReportSummary } from './dashboard_report.js';
import {
  summarizeStackKpis,
  summarizeOptimizationTotals,
  summarizeComplianceKpis,
  summarizeAbTest,
} from './dashboard_stats.js';

export function renderSubagentStats(events) {
  applyReportSummary(computeReportSummary(events));
}

export function renderSubagentTable(events, globalSessionUsage) {
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
    renderLaunchOptBadges(launch, cBadges, globalSessionUsage);

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

export function renderHookCompressionStats(events) {
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

export function renderRtkGainStats(rtkGain, hookSavedTokens) {
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
      pSaved: fmtCompact(pSaved),
      pPct: ppct,
    });
    totalSubEl.textContent = t('rtkGlobalHook', { hook: fmtCompact(hookSavedTokens || 0) });
  } else {
    subEl.textContent = t('gOnly', { gPct: gpct });
    totalSubEl.textContent = t('rtkGlobalHook', { hook: fmtCompact(hookSavedTokens || 0) });
  }
}

export function renderEditStats(events) {
  const fileEdits = events.filter((e) => e.event === 'afterFileEdit');
  const totalEdits = fileEdits.length;
  const totalAdded = fileEdits.reduce((sum, e) => sum + Number(e.lines_added || 0), 0);
  const totalRemoved = fileEdits.reduce((sum, e) => sum + Number(e.lines_removed || 0), 0);

  const tabEdits = events.filter((e) => e.event === 'afterTabFileEdit');
  const tabCount = tabEdits.length;
  const tabAdded = tabEdits.reduce((sum, e) => sum + Number(e.lines_added || 0), 0);

  document.getElementById('kpiEditAdded').textContent = fmtNum(totalAdded);
  document.getElementById('kpiEditRemoved').textContent = fmtNum(totalRemoved);
  document.getElementById('kpiEditSub').textContent = t('editSummarySub', {
    count: fmtNum(totalEdits),
  });

  document.getElementById('kpiTabAccepted').textContent = fmtNum(tabCount);
  document.getElementById('kpiTabAdded').textContent = fmtNum(tabAdded);
  document.getElementById('kpiTabSub').textContent = t('tabSummarySub', {
    count: fmtNum(tabCount),
  });
}

export function renderConsumptionStats(events) {
  const summary = computeReportSummary(events);
  const cov = summary.consumption_coverage || {};

  document.getElementById('kpiResponseN').textContent = fmtNum(cov.responses || 0);
  document.getElementById('kpiResponseWith').textContent = fmtNum(cov.with_report || 0);
  document.getElementById('kpiResponseComplete').textContent = fmtNum(cov.complete || 0);

  const missing = (cov.responses || 0) - (cov.with_report || 0);
  document.getElementById('kpiResponseSub').textContent = t('responseCoverageSub', {
    missing: fmtNum(missing),
  });
}

export function setComplianceChipState(chipId, pct, warnBelow = 70) {
  const chip = document.getElementById(chipId);
  if (!chip) return;
  chip.textContent = `${pct}%`;
  chip.className = 'compliance-chip';
  if (pct >= 90) chip.classList.add('green');
  else if (pct >= warnBelow) chip.classList.add('orange');
  else chip.classList.add('red');
}

export function renderComplianceStats(events) {
  const compliance = summarizeComplianceKpis(events);

  setComplianceChipState('kpiComplianceOverall', compliance.overall_score_pct);
  setComplianceChipState('kpiComplianceMypy', compliance.mypy_run_pct);
  setComplianceChipState('kpiCompliancePrecommit', compliance.precommit_run_pct);
  setComplianceChipState('kpiComplianceConsumption', compliance.consumption_present_pct);
  setComplianceChipState('kpiComplianceComplete', compliance.consumption_complete_pct);

  document.getElementById('kpiComplianceOverallSub').textContent = t('complianceSummaryScoreSub', {
    score: compliance.overall_score_pct,
  });

  const missing = compliance.total_responses - compliance.precommit_run_responses;
  document.getElementById('kpiCompliancePrecommitSub').textContent = t('complianceMissingRuns', {
    missing: fmtNum(missing),
  });
}

export function renderAbTestKpis(events, abReportSummary) {
  const elTotal = document.getElementById('kpiAbTotalSaved');
  const elDelta = document.getElementById('kpiAbDelta');
  const elDeltaSub = document.getElementById('kpiAbDeltaSub');

  if (!abReportSummary || abReportSummary.ok !== true) {
    elTotal.textContent = '—';
    elDelta.textContent = '—';
    elDeltaSub.textContent = t('abTestNoSessionData');
    return;
  }

  const s = abReportSummary.summary || {};
  elTotal.textContent = fmtCompact(s.total_saved_tokens || 0);
  const delta = Number(s.savings_delta_pct || 0);
  const direction = delta >= 0 ? '+' : '';
  elDelta.textContent = `${direction}${delta.toFixed(1)}%`;
  elDeltaSub.textContent = t('abTestConfidenceSub', {
    samples: fmtNum(s.treatment_samples || 0),
    controlSamples: fmtNum(s.control_samples || 0),
  });
}

export function renderOptimizationKpis(events, rtkGain) {
  const summary = summarizeOptimizationTotals(events, rtkGain);

  document.getElementById('kpiTotalSaved').textContent = fmtCompact(summary.total_saved);
  if (summary.avg_savings_pct > 0) {
    document.getElementById('kpiTotalSub').textContent = t('gainPercentageAvgSub', {
      pct: summary.avg_savings_pct.toFixed(1),
    });
  } else {
    document.getElementById('kpiTotalSub').textContent = t('optimizationTotalsEmpty');
  }
}

export function renderLayerKpis(layerPayload) {
  if (!layerPayload || layerPayload.ok !== true) {
    document.getElementById('kpiStackProxySaved').textContent = '—';
    document.getElementById('kpiStackProxySub').textContent = t('failedToResolveStackLayer');
    return;
  }
  const s = layerPayload.summary || {};
  document.getElementById('kpiStackProxySaved').textContent = fmtCompact(s.total_saved_tokens || 0);
  document.getElementById('kpiStackProxySub').textContent = t('stackSavedSub', {
    saves: fmtNum(s.saves_count || 0),
  });
}

export function renderStackKpis(events) {
  const stackSummary = summarizeStackKpis(events);
  document.getElementById('kpiStackProxySaved').textContent = fmtCompact(
    stackSummary.total_saved || 0
  );
  document.getElementById('kpiStackProxySub').textContent = t('stackSavedSub', {
    saves: fmtNum(stackSummary.saves || 0),
  });
}
