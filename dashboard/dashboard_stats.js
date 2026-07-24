import {
  parseTs,
  bucketKey,
  observedTokens,
  eventOptimizationSavings,
  isSubagentLaunch,
  rowGitCacheHit,
  rowGitCacheTokensPreserved,
  rowGuardrailIntercepted,
  rowGuardrailLoopHalt,
  rowGuardrailAvoidedTokens,
  rowIdempotentInjected,
  num,
} from './dashboard_utils.js';

export function summarizeStackKpis(events) {
  const sessionUsage = {};
  events.forEach((e) => {
    if (e.event === 'afterAgentResponse') {
      for (const k of ['generation_id', 'session_id', 'conversation_id']) {
        const refId = e[k];
        if (typeof refId === 'string' && refId.trim()) {
          sessionUsage[refId.trim()] = e;
        }
      }
    }
  });

  const launches = events.filter(isSubagentLaunch);
  const gitHits = launches.filter(rowGitCacheHit).length;
  const gitPreserved = launches
    .filter(rowGitCacheHit)
    .reduce((sum, e) => sum + rowGitCacheTokensPreserved(e, sessionUsage), 0);
  const intercepts = launches.filter(rowGuardrailIntercepted).length;
  const halts = launches.filter(rowGuardrailLoopHalt).length;
  const avoided = launches.reduce((sum, e) => sum + rowGuardrailAvoidedTokens(e), 0);
  const idem = launches.filter(rowIdempotentInjected).length;
  return {
    launches: launches.length,
    gitHits,
    gitPreserved,
    intercepts,
    halts,
    avoided,
    idem,
  };
}

export function rtkDailyMap(rtkGain) {
  const map = {};
  const g = rtkGain?.global;
  if (g?.ok !== true || !Array.isArray(g.daily)) return map;
  g.daily.forEach((row) => {
    const date = String(row.date || '').trim();
    if (!date) return;
    map[date] = num(row.saved_tokens);
  });
  return map;
}

export function buildConsumptionComparison(events, mode, rtkGain) {
  const observed = {};
  const hookAndDiff = {};
  const hoursByDay = {};
  const daysInLog = new Set();

  events.forEach((e) => {
    const d = parseTs(e.ts);
    if (!d) return;
    const k = bucketKey(d, mode);
    const day = bucketKey(d, 'day');
    daysInLog.add(day);
    const obs = observedTokens(e);
    if (obs > 0) {
      observed[k] = (observed[k] || 0) + obs;
      if (mode === 'hour') {
        if (!hoursByDay[day]) hoursByDay[day] = new Set();
        hoursByDay[day].add(k);
      }
    }
    const save = eventOptimizationSavings(e);
    if (save > 0) hookAndDiff[k] = (hookAndDiff[k] || 0) + save;
  });

  const rtkMap = rtkDailyMap(rtkGain);
  const rtkInBuckets = {};

  if (mode === 'day') {
    daysInLog.forEach((day) => {
      const rtk = rtkMap[day] || 0;
      if (rtk > 0) rtkInBuckets[day] = rtk;
    });
  } else {
    Object.entries(hoursByDay).forEach(([day, hours]) => {
      const rtk = rtkMap[day] || 0;
      if (!rtk || !hours.size) return;
      const perHour = rtk / hours.size;
      hours.forEach((h) => {
        rtkInBuckets[h] = (rtkInBuckets[h] || 0) + perHour;
      });
    });
  }

  const keys = new Set([
    ...Object.keys(observed),
    ...Object.keys(hookAndDiff),
    ...Object.keys(rtkInBuckets),
  ]);
  const labels = [...keys].sort();
  const actualData = labels.map((l) => Math.round(observed[l] || 0));
  const savingsData = labels.map((l) => Math.round((hookAndDiff[l] || 0) + (rtkInBuckets[l] || 0)));
  const counterfactualData = labels.map((l, i) => actualData[i] + savingsData[i]);
  return { labels, actualData, savingsData, counterfactualData };
}

export function buildDailyGainPct(events, rtkGain) {
  const comp = buildConsumptionComparison(events, 'day', rtkGain);
  const rtkMap = rtkDailyMap(rtkGain);
  const hookDiffByDay = {};

  events.forEach((e) => {
    const d = parseTs(e.ts);
    if (!d) return;
    const day = bucketKey(d, 'day');
    const save = eventOptimizationSavings(e);
    if (save > 0) hookDiffByDay[day] = (hookDiffByDay[day] || 0) + save;
  });

  const indices = comp.labels
    .map((_, i) => i)
    .filter((i) => (comp.actualData[i] || 0) > 0 || (comp.savingsData[i] || 0) > 0);

  const labels = indices.map((i) => comp.labels[i]);
  const actualData = indices.map((i) => comp.actualData[i] || 0);
  const savingsData = indices.map((i) => comp.savingsData[i] || 0);
  const rtkData = indices.map((i) => rtkMap[comp.labels[i]] || 0);
  const hookDiffData = indices.map((i) => hookDiffByDay[comp.labels[i]] || 0);
  const pctData = indices.map((i) => {
    const sav = comp.savingsData[i] || 0;
    const cf = (comp.actualData[i] || 0) + sav;
    if (cf <= 0) return 0;
    return Math.round((1000 * sav) / cf) / 10;
  });

  return { labels, pctData, actualData, savingsData, rtkData, hookDiffData };
}

export function summarizeOptimizationTotals(events, rtkGain) {
  let observed = 0;
  let hookDiff = 0;
  events.forEach((e) => {
    observed += observedTokens(e);
    hookDiff += eventOptimizationSavings(e);
  });
  const rtkMap = rtkDailyMap(rtkGain);
  const days = new Set();
  events.forEach((e) => {
    const d = parseTs(e.ts);
    if (d) days.add(bucketKey(d, 'day'));
  });
  let rtk = 0;
  days.forEach((day) => {
    rtk += rtkMap[day] || 0;
  });
  const savings = hookDiff + rtk;
  const counterfactual = observed + savings;
  const pct = counterfactual > 0 ? (100 * savings) / counterfactual : 0;
  return { observed, savings, counterfactual, pct, hookDiff, rtk };
}

export function summarizeComplianceKpis(events) {
  const responses = events.filter((e) => e.event === 'afterAgentResponse');
  const respN = responses.length;
  const withReport = responses.filter((e) => e.consumption_present === true).length;
  const complete = responses.filter((e) => e.consumption_complete === true).length;

  const briefEvents = events.filter((e) => e.event === 'taskBriefValidation');
  const briefDenied = briefEvents.filter((e) => e.brief_valid === false).length;

  const launches = events.filter(isSubagentLaunch).length;
  const briefAttempts = launches + briefDenied;
  const briefPassRate = briefAttempts > 0 ? Math.round((100 * launches) / briefAttempts) : 0;

  const consoHookEvents = events.filter((e) => e.event === 'consumptionReportCompliance');
  const consoFollowups = consoHookEvents.filter((e) => e.consumption_enforced === true).length;
  const consoGiveups = consoHookEvents.filter(
    (e) => e.consumption_complete === false && Number(e.loop_count || 0) >= 2
  ).length;
  const consoOkHook = consoHookEvents.filter((e) => e.consumption_complete === true).length;

  const stack = summarizeStackKpis(events);

  return {
    consumption: {
      responses: respN,
      present: withReport,
      complete,
      present_pct: respN > 0 ? Math.round((100 * withReport) / respN) : 0,
      complete_pct: respN > 0 ? Math.round((100 * complete) / respN) : 0,
      hook_checks: consoHookEvents.length,
      hook_followups: consoFollowups,
      hook_ok: consoOkHook,
      hook_giveups: consoGiveups,
    },
    task_brief: {
      launches,
      denied: briefDenied,
      attempts: briefAttempts,
      pass_rate_pct: briefPassRate,
    },
    idempotency: {
      injected: stack.idem,
      launches: stack.launches,
      pct: stack.launches > 0 ? Math.round((100 * stack.idem) / stack.launches) : 0,
    },
  };
}

export function summarizeAbTest(events) {
  const launches = events.filter(isSubagentLaunch);
  let controlLaunches = 0;
  let controlInputTokens = 0;
  let controlAfterTokens = 0;
  let treatmentLaunches = 0;
  let treatmentInputTokens = 0;
  let treatmentAfterTokens = 0;

  launches.forEach((e) => {
    const ab = e.ab_group || 'treatment';
    const inp = num(e.compression_input_tokens);
    const aft = num(e.compression_after_tokens) || num(e.approx_tokens);
    if (ab === 'control') {
      controlLaunches++;
      controlInputTokens += inp;
      controlAfterTokens += aft;
    } else {
      treatmentLaunches++;
      treatmentInputTokens += inp;
      treatmentAfterTokens += aft;
    }
  });

  const treatmentReduction = treatmentInputTokens - treatmentAfterTokens;
  const treatmentSavedPct =
    treatmentInputTokens > 0 ? (100 * treatmentReduction) / treatmentInputTokens : 0;

  return {
    control: {
      launches: controlLaunches,
      input_tokens: controlInputTokens,
      after_tokens: controlAfterTokens,
      saved_tokens: 0,
      saved_pct: 0,
    },
    treatment: {
      launches: treatmentLaunches,
      input_tokens: treatmentInputTokens,
      after_tokens: treatmentAfterTokens,
      saved_tokens: treatmentReduction,
      saved_pct: Math.round(treatmentSavedPct * 100) / 100,
    },
  };
}
