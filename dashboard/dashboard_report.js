import { getLanguage, t } from './dashboard_translations.js';
import {
  fmtNum,
  fmtCompact,
  parseTs,
  isSubagentLaunch,
  hookSavedTokens,
  cacheReadWeight,
} from './dashboard_utils.js';
import { summarizeComplianceKpis } from './dashboard_stats.js';

export function latestSessionKey(events) {
  const responses = events
    .filter((e) => e.event === 'afterAgentResponse')
    .sort((a, b) => (parseTs(b.ts)?.getTime() || 0) - (parseTs(a.ts)?.getTime() || 0));
  const latest = responses[0];
  if (!latest) return '';
  return latest.session_id || latest.conversation_id || '';
}

export function eventsForCurrentTour(events) {
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

export function computeReportSummary(events) {
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
      const w = cacheReadWeight(latest.model);
      latestAdjustedBilled = Math.round(
        Math.max(0, latestIn - latestCacheRead) + latestCacheRead * w + latestOut
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
        const w = cacheReadWeight(e.model);
        const adjIn = Math.max(0, inp - cRead) + cRead * w;
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

export function applyReportSummary(summary) {
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

export function periodLabel(events) {
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

export function updateNavPeriod(events, overrideText) {
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
