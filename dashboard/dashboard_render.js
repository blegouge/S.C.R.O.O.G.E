import { getLanguage, t } from './dashboard_translations.js';
import {
  fmtNum,
  fmtCompact,
  safeSetText,
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

  safeSetText('kpiHookSaved', fmtCompact(savedTokens));
  if (!count) {
    safeSetText('kpiHookSub', t('noHookMeasurements'));
  } else {
    const backendHint = Object.entries(backends)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 2)
      .map(([k, n]) => `${k}×${n}`)
      .join(' · ');
    safeSetText(
      'kpiHookSub',
      t('hookSummarySub', {
        count: fmtNum(count),
        pct: Number(avgPct || 0).toFixed(1),
        claw: fmtNum(usedClaw),
        llm: fmtNum(usedLingu),
        backend: backendHint ? ` · ${backendHint}` : '',
      })
    );
  }
  return { savedTokens };
}

export function renderRtkGainStats(rtkGain, hookSavedTokens) {
  if (!rtkGain || typeof rtkGain !== 'object') {
    safeSetText('kpiRtkSaved', '—');
    safeSetText('kpiRtkSub', t('rtkUnavailable'));
    safeSetText('kpiTotalSaved', fmtCompact(hookSavedTokens || 0));
    safeSetText('kpiTotalSub', t('hookOnlyRtkUnavailable'));
    return;
  }

  const g = rtkGain.global || {};
  const p = rtkGain.project || {};
  const gs = g.summary || {};
  const ps = p.summary || {};

  if (g.ok !== true || typeof gs.total_saved !== 'number') {
    safeSetText('kpiRtkSaved', '—');
    const err = String(g.error || t('globalUnavailable')).slice(0, 64);
    safeSetText('kpiRtkSub', t('globalUnavailableErr', { err }));
    safeSetText('kpiTotalSaved', fmtCompact(hookSavedTokens || 0));
    safeSetText('kpiTotalSub', t('hookOnlyGlobalUnavailable'));
    return;
  }

  const gSaved = Number(gs.total_saved || 0);
  safeSetText('kpiRtkSaved', fmtCompact(gSaved));
  const totalSaved = gSaved + Number(hookSavedTokens || 0);
  safeSetText('kpiTotalSaved', fmtCompact(totalSaved));

  const gpct = Number(gs.avg_savings_pct || 0).toFixed(1);
  if (p.ok === true && typeof ps.total_saved === 'number') {
    const pSaved = Number(ps.total_saved || 0);
    const ppct = Number(ps.avg_savings_pct || 0).toFixed(1);
    safeSetText(
      'kpiRtkSub',
      t('gProjects', {
        gPct: gpct,
        pSaved: fmtCompact(pSaved),
        pPct: ppct,
      })
    );
    safeSetText('kpiTotalSub', t('rtkGlobalHook', { hook: fmtCompact(hookSavedTokens || 0) }));
  } else {
    safeSetText('kpiRtkSub', t('gOnly', { gPct: gpct }));
    safeSetText('kpiTotalSub', t('rtkGlobalHook', { hook: fmtCompact(hookSavedTokens || 0) }));
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

  safeSetText('kpiAgentAdd', fmtNum(totalAdded));
  safeSetText('kpiAgentRem', fmtNum(totalRemoved));
  safeSetText('kpiAgentPass', fmtNum(totalEdits));
  safeSetText('kpiTabN', fmtNum(tabCount));
  safeSetText('kpiTabLines', fmtNum(tabAdded));
}

export function renderConsumptionStats(events) {
  const summary = computeReportSummary(events);
  const cov = summary.consumption_coverage || {};

  safeSetText('kpiConso', fmtNum(cov.complete || 0));
  safeSetText(
    'kpiConsoSub',
    t('responseCoverageSub', {
      complete: fmtNum(cov.complete || 0),
      total: fmtNum(cov.responses || 0),
    })
  );
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

  setComplianceChipState('kpiConsoComplete', compliance.consumption_complete_pct);
  setComplianceChipState('kpiConsoPresent', compliance.consumption_present_pct);

  const followups = events.filter(
    (e) => e.event === 'followup_message' || e.event === 'giveup'
  ).length;
  safeSetText('kpiConsoHookFollowups', fmtNum(followups));

  const briefs = events.filter((e) => e.event === 'taskBriefValidation');
  const passBriefs = briefs.filter(
    (e) => e.status === 'pass' || e.passed === true || e.result === 'pass'
  ).length;
  const deniedBriefs = briefs.filter(
    (e) => e.status === 'deny' || e.denied === true || e.result === 'deny'
  ).length;

  safeSetText('kpiBriefPass', `${passBriefs}/${briefs.length}`);
  safeSetText('kpiBriefDenied', fmtNum(deniedBriefs));
}

export function renderAbTestKpis(events, abReportSummary) {
  if (!abReportSummary || abReportSummary.ok !== true) {
    safeSetText('kpiAbTotalSaved', '—');
    safeSetText('kpiAbDelta', '—');
    safeSetText('kpiAbDeltaSub', t('abTestNoSessionData'));
    return;
  }

  const s = abReportSummary.summary || {};
  safeSetText('kpiAbTotalSaved', fmtCompact(s.total_saved_tokens || 0));
  const delta = Number(s.savings_delta_pct || 0);
  const direction = delta >= 0 ? '+' : '';
  safeSetText('kpiAbDelta', `${direction}${delta.toFixed(1)}%`);
  safeSetText(
    'kpiAbDeltaSub',
    t('abTestConfidenceSub', {
      samples: fmtNum(s.treatment_samples || 0),
      controlSamples: fmtNum(s.control_samples || 0),
    })
  );
}

export function renderOptimizationKpis(events, rtkGain) {
  const summary = summarizeOptimizationTotals(events, rtkGain);
  const observed = summary.observed ?? summary.total_observed ?? 0;
  const counterfactual = summary.counterfactual ?? summary.total_counterfactual ?? 0;
  const savings = summary.savings ?? summary.total_saved ?? 0;
  const pct = Number(summary.pct ?? summary.avg_savings_pct ?? 0);

  safeSetText('kpiObserved', fmtCompact(observed));
  safeSetText('kpiCounterfactual', fmtCompact(counterfactual));
  safeSetText('kpiOptSaved', fmtCompact(savings));
  safeSetText('kpiOptPct', `${pct.toFixed(1)}%`);

  safeSetText('kpiTotalSaved', fmtCompact(savings));
  if (pct > 0) {
    safeSetText(
      'kpiTotalSub',
      t('gainPercentageAvgSub', {
        pct: pct.toFixed(1),
      })
    );
  } else {
    safeSetText('kpiTotalSub', t('optimizationTotalsEmpty'));
  }
}

export function renderLayerKpis(layerPayload) {
  const container = document.getElementById('kpiLayersTable');
  if (!container) return;

  if (!layerPayload || layerPayload.ok !== true || !layerPayload.layers) {
    container.innerHTML = `<div class="empty-state">${t('failedToResolveStackLayer')}</div>`;
    return;
  }

  const layers = layerPayload.layers;
  const blended = layerPayload.blended || {};
  const legacy = layerPayload.legacy_global || {};

  const layerKeys = [
    { key: 'rtk_shell', label: 'RTK Shell (gain -d)' },
    { key: 'task_compression', label: 'Task Compression (LLMLingua / Claw)' },
    { key: 'guardrail_read', label: 'Token Guardrail (Read ROI)' },
    { key: 'guardrail_task', label: 'Token Guardrail (Subagent ROI)' },
    { key: 'diff_only', label: 'Diff-Only (Compact diffs)' },
    { key: 'code_review_graph', label: 'Code Review Graph (CRG)' },
  ];

  let html = `
    <div class="layers-head">
      <span>Layer</span>
      <span>% Saved</span>
      <span>Tokens Saved</span>
      <span>Observed Tokens</span>
    </div>
  `;

  layerKeys.forEach(({ key, label }) => {
    const l = layers[key] || {};
    const pct = typeof l.pct === 'number' ? `${l.pct.toFixed(1)}%` : '—';
    const saved = fmtCompact(l.savings_tokens || 0);
    const obs = fmtCompact(l.observed_tokens || 0);

    html += `
      <div class="layers-row">
        <span>${label}</span>
        <span class="badge-pct">${pct}</span>
        <span>${saved}</span>
        <span>${obs}</span>
      </div>
    `;
  });

  if (blended && blended.pct !== undefined && blended.pct !== null) {
    const blendedPct = Number(blended.pct || 0).toFixed(1);
    html += `
      <div class="layers-row layers-blend">
        <span><strong>Blended Score (Tool/Subagent)</strong></span>
        <span class="badge-pct highlight">${blendedPct}%</span>
        <span><strong>${fmtCompact(blended.savings_tokens || 0)}</strong></span>
        <span>${fmtCompact(blended.observed_tokens || 0)}</span>
      </div>
    `;
  }

  if (legacy && legacy.pct !== undefined && legacy.pct !== null) {
    const legacyPct = Number(legacy.pct || 0).toFixed(1);
    html += `
      <div class="layers-row layers-legacy">
        <span><em>Legacy Global (Includes Chat)</em></span>
        <span>${legacyPct}%</span>
        <span>${fmtCompact(legacy.savings_tokens || 0)}</span>
        <span>${fmtCompact(legacy.observed_tokens || 0)}</span>
      </div>
    `;
  }

  container.innerHTML = html;
}

export function renderStackKpis(events) {
  const stackSummary = summarizeStackKpis(events);
  safeSetText('kpiGitCacheHits', fmtNum(stackSummary.gitHits || 0));
  safeSetText(
    'kpiGuardrailIntercepts',
    `${stackSummary.intercepts || 0} / ${stackSummary.halts || 0}`
  );
  safeSetText('kpiGuardrailAvoided', fmtCompact(stackSummary.avoided || 0));
  safeSetText('kpiIdempotent', fmtNum(stackSummary.idem || 0));
}

export function renderAgentStatus(statusData) {
  const dot = document.getElementById('agentStatusDot');
  const label = document.getElementById('agentStatusLabel');
  const nameEl = document.getElementById('popoverAgentName');
  const pathEl = document.getElementById('popoverAgentPath');
  const badgeEl = document.getElementById('popoverSummaryBadge');
  const bodyEl = document.getElementById('popoverBody');

  if (!statusData || !statusData.ok) {
    if (dot) dot.className = 'agent-status-dot dot-missing';
    if (label) label.textContent = 'Err';
    return;
  }

  const { label: agentName, home, active_count, installed_count, total_count, items } = statusData;

  if (nameEl) nameEl.textContent = agentName;
  if (pathEl) pathEl.textContent = home || '';
  if (label) label.textContent = `${active_count}/${total_count}`;
  if (badgeEl)
    badgeEl.textContent = `${active_count}/${total_count} ${t('statusActive') || 'Active'}`;

  if (dot) {
    if (active_count >= Math.ceil(total_count / 2)) {
      dot.className = 'agent-status-dot dot-active';
    } else if (installed_count > 0) {
      dot.className = 'agent-status-dot dot-installed';
    } else {
      dot.className = 'agent-status-dot dot-missing';
    }
  }

  if (bodyEl) {
    bodyEl.replaceChildren();

    items.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'agent-status-row';

      const iconCol = document.createElement('div');
      iconCol.className = 'status-row-icon';
      if (item.status === 'active') {
        iconCol.innerHTML = '<span class="status-icon active-icon">🟢</span>';
      } else if (item.status === 'installed') {
        iconCol.innerHTML = '<span class="status-icon installed-icon">🟡</span>';
      } else {
        iconCol.innerHTML = '<span class="status-icon missing-icon">🔴</span>';
      }

      const contentCol = document.createElement('div');
      contentCol.className = 'status-row-content';

      const titleLine = document.createElement('div');
      titleLine.className = 'status-row-title';
      titleLine.textContent = t(item.label_key) || item.id;

      const detailLine = document.createElement('div');
      detailLine.className = 'status-row-detail';
      detailLine.textContent = item.detail;

      contentCol.appendChild(titleLine);
      contentCol.appendChild(detailLine);

      const statusBadge = document.createElement('span');
      statusBadge.className = `status-pill status-${item.status}`;
      if (item.status === 'active') {
        statusBadge.textContent = t('statusActive') || 'Active';
      } else if (item.status === 'installed') {
        statusBadge.textContent = t('statusInstalled') || 'Installed';
      } else {
        statusBadge.textContent = t('statusMissing') || 'Missing';
      }

      row.appendChild(iconCol);
      row.appendChild(contentCol);
      row.appendChild(statusBadge);

      if (item.status !== 'active') {
        const installBtn = document.createElement('button');
        installBtn.type = 'button';
        installBtn.className = 'btn-install-component';
        installBtn.title = `${t('installRowBtn') || 'Deploy'} ${item.id}`;
        installBtn.innerHTML = `<svg class="install-icon-svg" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>`;
        installBtn.setAttribute('data-component', item.id);
        installBtn.setAttribute('data-source', statusData.source);
        row.appendChild(installBtn);
      }

      bodyEl.appendChild(row);
    });
  }

  const footerEl = document.getElementById('popoverFooter');
  if (footerEl) {
    footerEl.replaceChildren();

    const installAllBtn = document.createElement('button');
    installAllBtn.type = 'button';
    installAllBtn.id = 'btnInstallAllComponents';
    installAllBtn.className = 'btn-install-all';
    installAllBtn.innerHTML = `<svg class="install-icon-svg" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg><span>${t('installAllBtn') || 'Install Missing Components'}</span>`;
    installAllBtn.setAttribute('data-source', statusData.source);

    const tipSpan = document.createElement('span');
    tipSpan.className = 'popover-tip';
    tipSpan.textContent =
      t('agentTip') || 'Tip: Run python install_stack.py to deploy missing components';

    footerEl.appendChild(installAllBtn);
    footerEl.appendChild(tipSpan);
  }
}
