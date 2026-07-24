import { getLanguage, t } from './dashboard_translations.js';

export const EVENT_COLORS = {
  systemEvent: '#4ef0e0',
  postToolUse: '#ff4fd8',
  afterAgentResponse: '#6b9fff',
  userMessage: '#b5ff6b',
  afterFileEdit: '#ffb347',
  afterTabFileEdit: '#c77dff',
  preToolUseCompression: '#ffd166',
  subagentLaunch: '#ffd166',
  subagentStop: '#ff9f6b',
  subagentPostToolUse: '#f472b6',
  taskBriefValidation: '#f87171',
  consumptionReportCompliance: '#a78bfa',
  codeReviewGraph: '#10b981',
};

export function fmtNum(n) {
  return Number(n || 0).toLocaleString(getLanguage() === 'fr' ? 'fr-FR' : 'en-US');
}

export function fmtCompact(n) {
  const v = Number(n || 0);
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return fmtNum(v);
}

export function parseTs(ts) {
  if (!ts) return null;
  const d = new Date(ts.endsWith('Z') ? ts : ts + 'Z');
  return isNaN(d.getTime()) ? null : d;
}

export function fmtDateUtcCell(iso) {
  const d = parseTs(iso);
  if (!d) return '—';
  const locale = getLanguage() === 'fr' ? 'fr-FR' : 'en-US';
  try {
    return d.toLocaleString(locale, {
      timeZone: 'UTC',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3,
    });
  } catch (_) {
    return d.toLocaleString(locale, {
      timeZone: 'UTC',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  }
}

export function eventColor(ev) {
  return EVENT_COLORS[ev] || '#9aa3c4';
}

export function num(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

export function isDiffOnlyEvent(e) {
  return String(e.event || '').startsWith('diffOnlyApply');
}

export function diffOnlySavings(e) {
  const d = e.diff_only;
  if (!d || typeof d !== 'object') return 0;
  return Math.ceil(num(d.estimated_chars_saved) / 4);
}

export function bucketKey(d, mode) {
  const y = d.getUTCFullYear();
  const mo = String(d.getUTCMonth() + 1).padStart(2, '0');
  const dy = String(d.getUTCDate()).padStart(2, '0');
  if (mode === 'day') return `${y}-${mo}-${dy}`;
  const h = String(d.getUTCHours()).padStart(2, '0');
  return `${y}-${mo}-${dy} ${h}:00`;
}

export function isSubagentLaunch(e) {
  return e.event === 'subagentLaunch' || e.event === 'preToolUseCompression';
}

export function rowGitCacheHit(e) {
  return e.compression_git_cache_hit === true || e.git_cache_hit === true;
}

export function rowGitCacheTokensPreserved(e, sessionUsage) {
  const keys = [
    'git_cache_block2_tokens_preserved',
    'compression_block2_tokens_preserved',
    'block2_tokens_preserved',
  ];
  for (const key of keys) {
    const v = Number(e[key]);
    if (Number.isFinite(v) && v > 0) return v;
  }
  if (sessionUsage) {
    for (const k of ['generation_id', 'session_id', 'conversation_id']) {
      const refId = e[k];
      if (typeof refId === 'string' && refId.trim()) {
        const usageRow = sessionUsage[refId.trim()];
        if (usageRow) {
          const cRead = Number(usageRow.cache_read_tokens);
          if (Number.isFinite(cRead)) return cRead;
        }
      }
    }
  }
  if (rowGitCacheHit(e)) {
    const after = Number(e.compression_after_tokens || e.approx_tokens || 0);
    return after > 0 ? Math.max(0, Math.round(after * 0.12)) : 0;
  }
  return 0;
}

export function rowGuardrailLoopHalt(e) {
  return e.guardrail_loop_halt === true;
}

export function rowGuardrailIntercepted(e) {
  if (e.guardrail_intercepted === true) return true;
  if (rowGuardrailLoopHalt(e)) return true;
  return e.guardrail_roi_gate === true && String(e.guardrail_risk || '').toLowerCase() === 'high';
}

export function rowGuardrailAvoidedTokens(e) {
  const v = Number(e.guardrail_avoided_tokens);
  if (Number.isFinite(v) && v > 0) return v;
  if (!rowGuardrailIntercepted(e)) return 0;
  const inputTok = Number(e.compression_input_tokens || 0);
  const afterTok = Number(e.compression_after_tokens || e.approx_tokens || 0);
  if (rowGuardrailLoopHalt(e)) {
    const streak = Number(e.guardrail_failure_streak || 2);
    const cycles = Math.max(1, 4 - streak);
    return cycles * (inputTok + Math.max(afterTok, Math.floor(inputTok / 3)));
  }
  return Math.floor(inputTok * 0.35 + Math.max(afterTok, Math.floor(inputTok / 4)));
}

export function rowIdempotentInjected(e) {
  return e.idempotent_context_injected === true;
}

export function hookSavedTokens(e) {
  const legacy = Number(e.compression_saved_tokens || 0);
  const inputTok = Number(e.compression_input_tokens || 0);
  const afterTok = Number(e.compression_after_tokens || e.approx_tokens || 0);
  const endToEnd = Number(e.compression_end_to_end_saved_tokens);
  if (Number.isFinite(endToEnd) && endToEnd > 0) {
    return Math.max(legacy, endToEnd);
  }
  if (inputTok > 0) {
    return Math.max(legacy, Math.max(0, inputTok - afterTok));
  }
  return legacy;
}

export function hookSavedPct(e) {
  const inputTok = Number(e.compression_input_tokens || 0);
  if (inputTok > 0) {
    return (100 * hookSavedTokens(e)) / inputTok;
  }
  return Number(e.compression_saved_pct || 0);
}

export function compressionSummary(e) {
  const claw = e.compression_used_claw_compactor === true;
  const llm = e.compression_used_llmlingua === true;
  const backend = String(e.compression_backend || '').trim() || '—';
  const saved = hookSavedTokens(e);
  const pct = hookSavedPct(e);
  let label = '—';
  if (claw && llm) label = 'claw+llm';
  else if (claw) label = 'claw';
  else if (llm) label = 'llm';

  const parts = [];
  if (label !== '—') parts.push(label);
  if (backend !== '—') parts.push(backend);
  const details = parts.join(' · ');

  return saved > 0
    ? t('hookSummarySub', {
        count: fmtCompact(saved),
        pct: Math.round(pct),
        claw: claw ? 'Y' : 'N',
        llm: llm ? 'Y' : 'N',
        backend: details !== '—' ? ` · ${details}` : '',
      })
    : t('none');
}

export function cacheReadWeight(modelName) {
  if (!modelName) return 0.1;
  const name = String(modelName).toLowerCase();
  if (name.includes('claude')) return 0.1;
  if (name.includes('gpt') || name.includes('o1') || name.includes('o3')) return 0.5;
  if (name.includes('gemini')) return 0.1;
  return 0.1;
}

export function observedTokens(e) {
  if (e.event === 'afterFileEdit' || e.event === 'afterTabFileEdit') return 0;
  if (isDiffOnlyEvent(e)) return 0;
  if (e.event === 'afterAgentResponse') {
    const inp = num(e.input_tokens);
    const out = num(e.output_tokens);
    const cRead = num(e.cache_read_tokens);
    if (cRead > 0) {
      const w = cacheReadWeight(e.model);
      const adjIn = Math.max(0, inp - cRead) + cRead * w;
      return Math.round(adjIn + out);
    }
    const billed = num(e.billed_total_tokens);
    if (billed > 0) return billed;
    if (inp > 0 || out > 0) return inp + out;
  }

  if (isSubagentLaunch(e)) {
    return num(e.compression_after_tokens) || num(e.approx_tokens);
  }
  if (e.event === 'subagentStop') return num(e.approx_tokens);
  if (e.event === 'postToolUse') return num(e.approx_tokens);
  return num(e.approx_tokens);
}

export function eventOptimizationSavings(e) {
  if (isSubagentLaunch(e) || e.event === 'preToolUseCompression') {
    return hookSavedTokens(e);
  }
  if (isDiffOnlyEvent(e)) return diffOnlySavings(e);
  if (e.event === 'codeReviewGraph') {
    return num(e.saved_tokens);
  }
  return 0;
}

export function makeOptBadge(label, className, title) {
  const pill = document.createElement('span');
  pill.className = `opt-badge ${className}`;
  pill.textContent = label;
  if (title) pill.title = title;
  return pill;
}

export function renderLaunchOptBadges(launch, container, sessionUsage) {
  container.replaceChildren();
  const parts = [];
  if (rowGitCacheHit(launch)) {
    const preserved = rowGitCacheTokensPreserved(launch, sessionUsage);
    parts.push(
      makeOptBadge(
        'Git Cache Hit',
        'git-cache',
        preserved > 0
          ? `BLOCK_2 reused · ≈${fmtCompact(preserved)} tok preserved`
          : 'BLOCK_2 loaded from Git cache'
      )
    );
  }
  if (rowGuardrailIntercepted(launch)) {
    const avoided = rowGuardrailAvoidedTokens(launch);
    const halt = rowGuardrailLoopHalt(launch);
    parts.push(
      makeOptBadge(
        halt ? 'Guardrail halt' : 'Guardrail',
        'guardrail',
        `avoided cost≈${fmtCompact(avoided)} tok · streak ${launch.guardrail_failure_streak ?? '?'}`
      )
    );
  }
  if (rowIdempotentInjected(launch)) {
    parts.push(
      makeOptBadge('Idempotent', 'idempotent', 'Brief with [IDEMPOTENT_CONTEXT_INJECTED]')
    );
  }
  if (!parts.length) {
    parts.push(makeOptBadge('—', 'muted', 'no stack signal'));
  }
  parts.forEach((pill) => container.appendChild(pill));
}
