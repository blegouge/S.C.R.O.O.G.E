const TRANSLATIONS = {
  en: {
    brandTitle: 'S.C.R.O.O.G.E.',
    brandSub: 'Smart Context Reducer & Optimized Observability Governance Engine',
    navInfoTip:
      'Local telemetry — the chart compares observed consumption (billed by Cursor when available) to an estimate without optimizations (real + RTK savings, Task compression, Diff-Only).',
    refreshNowTitle: 'Refresh from server now',
    refreshMenuTitle: 'Auto-refresh interval',
    refreshLabel: 'Refresh',
    disabled: 'Disabled',
    fiveMin: '5 minutes',
    thirtyMin: '30 minutes',
    oneHour: '1 hour',
    sourceSelectTitle: 'Telemetry data source',
    toggleTheme: 'Toggle theme',
    loadFile: 'Load file',

    // Sections
    section_kpi_summary: 'Summary',
    section_kpi_savings: 'Optimizations comparison',
    section_kpi_layers: 'Score per layer',
    section_kpi_editing: 'Editing',
    section_kpi_subagents: 'Subagents (KPI)',
    section_kpi_stack: 'Stack optimizations',
    section_kpi_compliance: 'Compliance hooks (KPI)',
    section_table_subagents: 'Recent subagents',
    section_table_compliance: 'Compliance hooks (recent)',
    section_table_crg: 'Commits (Code Review Graph)',
    section_charts: 'Charts',
    section_tables_lists: 'Lists & activity',

    // KPI labels
    events: 'Events',
    tokensProxy: 'Tokens (proxy)',
    textChars: 'Text characters',
    consoReports: 'Conso reports',
    rtkGainSaved: 'RTK gain (saved)',
    hookGainSaved: 'Hook gain (saved)',
    globalGains: 'Global gains',
    consumedObserved: 'Consumed (observed)',
    withoutOptimizations: 'Without optimizations (estimated)',
    savingsEstimated: 'Savings (estimated)',
    globalGainPct: 'Global gain',
    agentAdd: 'Agent ΔL+',
    agentRem: 'Agent ΔL−',
    agentPasses: 'Agent passes',
    tabsAccepted: 'Tabs accepted',
    tabLines: 'ΔL+ Tab',
    launchesTotal: 'Launches (total)',
    completedTotal: 'Completed (total)',
    parentBilled: 'Parent billed',
    subPromptProxy: 'Sub prompt (proxy)',
    subOutProxy: 'Sub output (proxy)',
    gitCacheHit: 'Git Cache Hit',
    guardrailCircuit: 'Guardrail circuit breaker',
    avoidedCost: 'Avoided cost',
    idempotence: 'Idempotence',
    consoComplete: 'Conso — complete (5 fields)',
    consoPresent: 'Conso — present',
    hookStopRetries: 'Hook stop — retries',
    taskBriefPass: 'Task brief — pass',
    taskBriefBlocked: 'Task brief — blocked',
    commitChecks: 'Commit Checks',
    savedTokens: 'Saved Tokens',
    avgRiskScore: 'Average Risk Score',

    // Subtexts
    validLines: 'Valid lines in log',
    completeFiveFields: 'complete · 5 fields',
    globalProject: 'global / project',
    clawLlmTask: 'Claw / LLMLingua · Task',
    rtkHook: 'RTK + hook',
    logPeriod: 'log period',
    observedSavings: 'observed + savings',
    rtkCompressionDiff: 'RTK + compression + diff-only',
    pctOfCounterfactual: '% of counterfactual',
    afterFileEdit: 'afterFileEdit',
    afterTabFileEdit: 'afterTabFileEdit',
    alignedReport: 'aligned with report.py',
    subagentStop: 'subagentStop',
    averageSum: 'average · sum',
    afterCompression: 'after compression',
    summaryTranscript: 'summary + transcript',
    block2Reused: 'BLOCK_2 reused',
    interceptsHalts: 'intercepts · halts',
    blockedLoopsExplore: 'blocked loops / explore',
    idempotentContext: '[IDEMPOTENT_CONTEXT_INJECTED]',
    consoCompleteSub: 'afterAgentResponse · hook stop',
    blockDetected: 'block detected (partial OK)',
    followupGiveup: 'followup_message · giveup',
    launchesAttempts: 'launches / attempts',
    permissionDenyHook: 'permission deny · hook Task',
    preCommitHook: 'pre-commit hook',
    viaContextReduction: 'via context reduction',
    acrossAllCommits: 'across all commits',

    // Layers table
    honestMeasurement:
      'Honest measurement: parent chat excluded from blend. Legacy = old KPI (often <1%).',
    layer: 'Layer',
    savings: 'Savings',
    observed: 'Observed',
    pctLayer: '% layer',
    blendExcludingChat: 'Blend (excluding chat)',
    legacyGlobal: 'Legacy global',
    parentChatInfo: 'Parent chat (info)',
    layersUnavailable: 'Layers unavailable',

    // Layer keys
    rtk_shell: 'RTK (Shell)',
    task_compression: 'Compression Task',
    guardrail_read: 'Guardrail Read',
    guardrail_task: 'Guardrail Task',
    diff_only: 'Diff-Only',
    code_review_graph: 'Code review graph',

    // Tables
    recentSubagentsTurn: 'Recent subagents (current turn)',
    date: 'Date',
    type: 'Type',
    skill: 'Skill',
    description: 'Description',
    badges: 'Badges',
    compression: 'Compression',
    prompt: 'Prompt',
    output: 'Output',
    status: 'Status',
    noSubagentTurn: 'No subagent on the current turn',
    recentCompliance: 'Compliance hooks (recent)',
    event: 'Event',
    detail: 'Detail',
    noComplianceEvents: 'No compliance events (brief / consumption)',
    recentCommitReports: 'Recent commit reports (Code Review Graph)',
    dateUtc: 'Date (UTC)',
    project: 'Project',
    branch: 'Branch',
    filesFns: 'Files / Fns',
    testGaps: 'Test Gaps',
    contextSaved: 'Context Saved',
    riskScore: 'Risk Score',
    noCommitReports: 'No commit reports (pre-commit)',
    topTools: 'Top tools (postToolUse)',
    noToolData: 'No tool data',
    recentActivity50: 'Recent activity (50)',
    noEventsYet: 'No events yet',

    // Charts
    gainPerDayTitle: 'Estimated gain per day',
    gainPerDayFootnote:
      '% = savings ÷ (observed + savings), aggregated per day (RTK + Task compression + Diff-Only). Readable even when Cursor billing reaches several million tokens.',
    observedVsOptTitle: 'Observed vs without optimizations',
    observedVsOptFootnote:
      'Observed: <code>billed_total_tokens</code> (agent responses), tool/subagent proxies, compressed prompt. Savings: <code>rtk gain -d</code> (per day), Task compression, Diff-Only chars ÷ 4. In hourly mode, the daily RTK gain is distributed across active hours.',
    distributionTitle: 'Distribution (proxy)',
    timeAggregation: 'Time aggregation',
    hourly: 'Hourly',
    daily: 'Daily',

    // Dynamic strings
    billedSubagentProxies: 'billed + tool/subagent proxies',
    rtkHookDiff: 'RTK {rtk} · hook {hook} · diff',
    savedOutOf: 'saved {savings} out of {counterfactual}',
    insufficientData: 'insufficient data',
    billed: 'billed {val}',
    consoOk: 'conso ok',
    consoPartial: 'conso partial',
    consoMissing: 'conso missing',
    briefRejected: 'brief rejected (deny)',
    noBlocks: 'no blocks',
    noAgentResponses: 'no agent responses',
    completeFields: '{pct}% complete (5 fields)',
    completeHookChecks: '{pct}% complete · hook checks {checks}',
    blockDetectedPartial: '{pct}% block detected',
    partialIncomplete: 'partial = incomplete',
    noTaskAttempts: 'no Task attempts',
    passRate: '{pct}% pass rate',
    consoHookSub: 'ok {ok} · giveup {giveups}',
    complianceLoopEnforced: 'loop {loop} · enforced {enforced}',
    denied: 'denied',
    ok: 'ok',
    complete: 'complete',
    incomplete: 'incomplete',
    avgSumLatest: 'sum {sum} · {count} resp. · latest {latest}',
    notExposed: 'not exposed',
    launchCount: '{count} launch(es)',
    stopCount: '{count} stop(s)',
    subStopSubVal: 'hook {hook} · fallback {fallback}',
    subLaunchSubVal: 'this turn: {tour} · file total',
    hookSummarySub: '{count} runs · {pct}% avg · claw {claw} · llm {llm}{backend}',
    gProjects: 'G {gPct}% ({gSaved}) · P {pPct}% ({pSaved})',
    gOnly: 'G {gPct}% · P unavailable',
    rtkGlobalHook: 'RTK global + hook ({hook})',
    rtkUnavailable: 'RTK unavailable',
    hookOnlyRtkUnavailable: 'hook only (RTK unavailable)',
    hookOnlyGlobalUnavailable: 'hook only (global unavailable)',
    globalUnavailableErr: 'global unavailable ({err})',
    globalUnavailable: 'global unavailable',
    runServeDashboard: 'Run serve_dashboard.py (localhost)',
    noProvidersError: 'No providers enabled. Set TELEMETRY_*_ENABLED=1 in .env (see .env.example)',
    noProvidersTitle: 'No providers configured',
    noProvidersMessage:
      'Enable at least one telemetry provider in your .env file, then restart the server.',
    chartEstimatedGain: 'Estimated gain (%)',
    chartConsumedObserved: 'Consumed (observed)',
    chartWithoutOpts: 'Without optimizations (estimated)',
    chartTooltipGain: 'Gain : {pct} %',
    chartTooltipObserved: 'Observed: {val}',
    chartTooltipSavings: 'Savings: {val}',
    chartTooltipRtk: 'RTK : {val}',
    chartTooltipHookDiff: 'Hook + Diff-Only : {val}',
    none: '(none)',
    noHookMeasurements: 'no hook measurements',
    gitCacheHitsSub: '{hits}/{launches} · BLOCK_2 ≈{preserved} tok',
    noTaskLaunches: 'no Task launches',
    guardrailSub: '{intercepts}/{launches} · halts {halts}',
    tokenBudgetGuardrail: 'token-budget-guardrail',
    inOutAvoided: 'in+out avoided (est.)',
    noInterceptsRecorded: 'no intercepts recorded',
    briefsTagged: '{pct}% briefs tagged',
  },
  fr: {
    brandTitle: 'S.C.R.O.O.G.E.',
    brandSub: 'Smart Context Reducer & Optimized Observability Governance Engine',
    navInfoTip:
      'Télémesure locale — le graphique compare la consommation observée (facturée par Cursor si disponible) à une estimation sans optimisations (gains réels + RTK, compression Task, Diff-Only).',
    refreshNowTitle: 'Actualiser depuis le serveur maintenant',
    refreshMenuTitle: "Intervalle d'auto-actualisation",
    refreshLabel: 'Actualiser',
    disabled: 'Désactivé',
    fiveMin: '5 min',
    thirtyMin: '30 min',
    oneHour: '1 h',
    sourceSelectTitle: 'Source des données de télémesure',
    toggleTheme: 'Changer le thème',
    loadFile: 'Charger un fichier',

    // Sections
    section_kpi_summary: 'Résumé',
    section_kpi_savings: 'Comparatif optimisations',
    section_kpi_layers: 'Score par couche',
    section_kpi_editing: 'Modifications',
    section_kpi_subagents: 'Sous-agents (KPI)',
    section_kpi_stack: 'Optimisations de la pile',
    section_kpi_compliance: 'Hooks de conformité (KPI)',
    section_table_subagents: 'Sous-agents récents',
    section_table_compliance: 'Hooks de conformité (récents)',
    section_table_crg: 'Commits (Code Review Graph)',
    section_charts: 'Graphiques',
    section_tables_lists: 'Listes & activité',

    // KPI labels
    events: 'Événements',
    tokensProxy: 'Tokens (proxy)',
    textChars: 'Caractères texte',
    consoReports: 'Rapports conso',
    rtkGainSaved: 'Gain RTK (économisé)',
    hookGainSaved: 'Gain hook (économisé)',
    globalGains: 'Gains globaux',
    consumedObserved: 'Consommé (observé)',
    withoutOptimizations: 'Sans optimisations (estimé)',
    savingsEstimated: 'Économies (estimées)',
    globalGainPct: 'Gain global',
    agentAdd: 'Agent ΔL+',
    agentRem: 'Agent ΔL−',
    agentPasses: 'Passages agent',
    tabsAccepted: 'Tabulations acceptées',
    tabLines: 'ΔL+ Tab',
    launchesTotal: 'Lancements (total)',
    completedTotal: 'Terminés (total)',
    parentBilled: 'Facturé parent',
    subPromptProxy: 'Prompt sub (proxy)',
    subOutProxy: 'Output sub (proxy)',
    gitCacheHit: 'Succès cache Git',
    guardrailCircuit: 'Coupe-circuit guardrail',
    avoidedCost: 'Coût évité',
    idempotence: 'Idempotence',
    consoComplete: 'Conso — complet (5 champs)',
    consoPresent: 'Conso — présent',
    hookStopRetries: 'Arrêt hook — essais',
    taskBriefPass: 'Task brief — succès',
    taskBriefBlocked: 'Task brief — bloqué',
    commitChecks: 'Vérifs de commits',
    savedTokens: 'Tokens économisés',
    avgRiskScore: 'Score de risque moyen',

    // Subtexts
    validLines: 'Lignes valides du log',
    completeFiveFields: 'complet · 5 champs',
    globalProject: 'global / projet',
    clawLlmTask: 'Claw / LLMLingua · Task',
    rtkHook: 'RTK + hook',
    logPeriod: 'période du log',
    observedSavings: 'observé + économies',
    rtkCompressionDiff: 'RTK + compression + diff-only',
    pctOfCounterfactual: '% du contrefactuel',
    afterFileEdit: 'afterFileEdit',
    afterTabFileEdit: 'afterTabFileEdit',
    alignedReport: 'aligné avec report.py',
    subagentStop: 'subagentStop',
    averageSum: 'moyenne · somme',
    afterCompression: 'après compression',
    summaryTranscript: 'résumé + transcription',
    block2Reused: 'BLOCK_2 réutilisé',
    interceptsHalts: 'intercepts · arrêts',
    blockedLoopsExplore: 'boucles bloquées / explore',
    idempotentContext: '[IDEMPOTENT_CONTEXT_INJECTED]',
    consoCompleteSub: 'afterAgentResponse · arrêt hook',
    blockDetected: 'bloc détecté (partiel OK)',
    followupGiveup: 'followup_message · abandon',
    launchesAttempts: 'lancements / essais',
    permissionDenyHook: 'permission deny · hook Task',
    preCommitHook: 'hook de pré-commit',
    viaContextReduction: 'via réduction de contexte',
    acrossAllCommits: 'sur tous les commits',

    // Layers table
    honestMeasurement:
      'Mesure honnête : chat parent exclu du blend. Legacy = ancien KPI (souvent <1%).',
    layer: 'Couche',
    savings: 'Économies',
    observed: 'Observé',
    pctLayer: '% couche',
    blendExcludingChat: 'Mélange (hors chat)',
    legacyGlobal: 'Legacy global',
    parentChatInfo: 'Chat parent (info)',
    layersUnavailable: 'Couches indisponibles',

    // Layer keys
    rtk_shell: 'RTK (Shell)',
    task_compression: 'Tâche de compression',
    guardrail_read: 'Lecture guardrail',
    guardrail_task: 'Tâche guardrail',
    diff_only: 'Diff-Only',
    code_review_graph: 'Graphe de code review',

    // Tables
    recentSubagentsTurn: 'Sous-agents récents (tour actuel)',
    date: 'Date',
    type: 'Type',
    skill: 'Compétence',
    description: 'Description',
    badges: 'Badges',
    compression: 'Compression',
    prompt: 'Prompt',
    output: 'Output',
    status: 'Statut',
    noSubagentTurn: 'Aucun sous-agent sur le tour actuel',
    recentCompliance: 'Hooks de conformité (récents)',
    event: 'Événement',
    detail: 'Détail',
    noComplianceEvents: 'Aucun événement de conformité (brief / conso)',
    recentCommitReports: 'Rapports de commits récents (Code Review Graph)',
    dateUtc: 'Date (UTC)',
    project: 'Projet',
    branch: 'Branche',
    filesFns: 'Fichiers / Fct',
    testGaps: 'Gaps de test',
    contextSaved: 'Contexte économisé',
    riskScore: 'Score de risque',
    noCommitReports: 'Aucun rapport de commit (pré-commit)',
    topTools: 'Top outils (postToolUse)',
    noToolData: "Aucune donnée d'outil",
    recentActivity50: 'Activité récente (50)',
    noEventsYet: "Aucun événement pour l'instant",

    // Charts
    gainPerDayTitle: 'Gain estimé par jour',
    gainPerDayFootnote:
      '% = économies ÷ (observé + économies), agrégé par jour (RTK + compression Task + Diff-Only). Lisible même quand la facturation de Cursor atteint plusieurs millions de tokens.',
    observedVsOptTitle: 'Observé vs sans optimisations',
    observedVsOptFootnote:
      'Observé : <code>billed_total_tokens</code> (réponses agent), proxies outil/sous-agent, prompt complet. Économies : <code>rtk gain -d</code> (par jour), compression Task, caractères Diff-Only ÷ 4. En mode horaire, le gain RTK quotidien est réparti sur les heures actives.',
    distributionTitle: 'Distribution (proxy)',
    timeAggregation: 'Agrégation temporelle',
    hourly: 'Horaire',
    daily: 'Journalier',

    // Dynamic strings
    billedSubagentProxies: 'facturé + proxies outil/sous-agent',
    rtkHookDiff: 'RTK {rtk} · hook {hook} · diff',
    savedOutOf: 'sauvé {savings} sur {counterfactual}',
    insufficientData: 'données insuffisantes',
    billed: 'facturé {val}',
    consoOk: 'conso ok',
    consoPartial: 'conso partiel',
    consoMissing: 'conso manquante',
    briefRejected: 'brief rejeté (deny)',
    noBlocks: 'aucun bloc',
    noAgentResponses: "aucune réponse de l'agent",
    completeFields: '{pct}% complet (5 champs)',
    completeHookChecks: '{pct}% complet · vérifs hook {checks}',
    blockDetectedPartial: '{pct}% bloc détecté',
    partialIncomplete: 'partiel = incomplet',
    noTaskAttempts: 'aucun essai Task',
    passRate: '{pct}% taux de succès',
    consoHookSub: 'ok {ok} · abandon {giveups}',
    complianceLoopEnforced: 'boucle {loop} · forcé {enforced}',
    denied: 'refusé',
    ok: 'ok',
    complete: 'complet',
    incomplete: 'incomplet',
    avgSumLatest: 'somme {sum} · {count} resp. · dernier {latest}',
    notExposed: 'non exposé',
    launchCount: '{count} lancement(s)',
    stopCount: '{count} arrêt(s)',
    subStopSubVal: 'hook {hook} · repli {fallback}',
    subLaunchSubVal: 'ce tour : {tour} · total fichier',
    hookSummarySub: '{count} essais · {pct}% moy · claw {claw} · llm {llm}{backend}',
    gProjects: 'G {gPct}% ({gSaved}) · P {pPct}% ({pSaved})',
    gOnly: 'G {gPct}% · P indisponible',
    rtkGlobalHook: 'RTK global + hook ({hook})',
    rtkUnavailable: 'RTK indisponible',
    hookOnlyRtkUnavailable: 'hook uniquement (RTK indisponible)',
    hookOnlyGlobalUnavailable: 'hook uniquement (global indisponible)',
    globalUnavailableErr: 'global indisponible ({err})',
    globalUnavailable: 'global indisponible',
    runServeDashboard: 'Lancer serve_dashboard.py (localhost)',
    noProvidersError:
      'Aucun provider activé. Définir TELEMETRY_*_ENABLED=1 dans .env (voir .env.example)',
    noProvidersTitle: 'Aucun provider configuré',
    noProvidersMessage:
      'Activez au moins un provider de télémétrie dans votre fichier .env, puis redémarrez le serveur.',
    chartEstimatedGain: 'Gain estimé (%)',
    chartConsumedObserved: 'Consommé (observé)',
    chartWithoutOpts: 'Sans optimisations (estimé)',
    chartTooltipGain: 'Gain : {pct} %',
    chartTooltipObserved: 'Observé : {val}',
    chartTooltipSavings: 'Économies : {val}',
    chartTooltipRtk: 'RTK : {val}',
    chartTooltipHookDiff: 'Hook + Diff-Only : {val}',
    none: '(aucun)',
    noHookMeasurements: 'aucune mesure hook',
    gitCacheHitsSub: '{hits}/{launches} · BLOCK_2 ≈{preserved} tok',
    noTaskLaunches: 'aucun lancement Task',
    guardrailSub: '{intercepts}/{launches} · arrêts {halts}',
    tokenBudgetGuardrail: 'token-budget-guardrail',
    inOutAvoided: 'in/out évitées (est.)',
    noInterceptsRecorded: 'aucun intercept détecté',
    briefsTagged: '{pct}% briefs marqués',
  },
};

function getLanguage() {
  try {
    return localStorage.getItem('cursor_telemetry_lang') || 'en';
  } catch (_) {
    return 'en';
  }
}

function setLanguage(lang) {
  try {
    localStorage.setItem('cursor_telemetry_lang', lang);
  } catch (_) {}
  applyTranslations(lang);
}

function t(key, replacements = {}) {
  const lang = getLanguage();
  let str = TRANSLATIONS[lang]?.[key] || TRANSLATIONS['en']?.[key] || key;
  Object.entries(replacements).forEach(([k, v]) => {
    str = str.replace(`{${k}}`, v);
  });
  return str;
}

function applyTranslations(lang) {
  // 1. Text elements
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.getAttribute('data-i18n');
    const val = TRANSLATIONS[lang]?.[key] || TRANSLATIONS['en']?.[key];
    if (val !== undefined) {
      el.textContent = val;
    }
  });

  // 2. HTML elements
  document.querySelectorAll('[data-i18n-html]').forEach((el) => {
    const key = el.getAttribute('data-i18n-html');
    const val = TRANSLATIONS[lang]?.[key] || TRANSLATIONS['en']?.[key];
    if (val !== undefined) {
      el.innerHTML = val;
    }
  });

  // 3. Title attribute
  document.querySelectorAll('[data-i18n-title]').forEach((el) => {
    const key = el.getAttribute('data-i18n-title');
    const val = TRANSLATIONS[lang]?.[key] || TRANSLATIONS['en']?.[key];
    if (val !== undefined) {
      el.setAttribute('title', val);
    }
  });

  // 4. Aria-label attribute
  document.querySelectorAll('[data-i18n-aria-label]').forEach((el) => {
    const key = el.getAttribute('data-i18n-aria-label');
    const val = TRANSLATIONS[lang]?.[key] || TRANSLATIONS['en']?.[key];
    if (val !== undefined) {
      el.setAttribute('aria-label', val);
    }
  });

  const select = document.getElementById('langSelect');
  if (select) select.value = lang;

  // Sync auto refresh label
  if (typeof refreshIntervalMs === 'number') {
    syncRefreshMenuRadios(refreshIntervalMs);
  }

  updateHeaderTitle();
}

const EVENT_COLORS = {
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

let trendChart = null;
let gainPctChart = null;
let donutChart = null;
let rtkGainData = null;

function fmtNum(n) {
  return Number(n || 0).toLocaleString(getLanguage() === 'fr' ? 'fr-FR' : 'en-US');
}

function fmtCompact(n) {
  const v = Number(n || 0);
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return fmtNum(v);
}

function parseTs(ts) {
  if (!ts) return null;
  const d = new Date(ts.endsWith('Z') ? ts : ts + 'Z');
  return isNaN(d.getTime()) ? null : d;
}

function fmtDateUtcCell(iso) {
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

function eventColor(ev) {
  return EVENT_COLORS[ev] || '#9aa3c4';
}

function destroyCharts() {
  if (trendChart) {
    trendChart.destroy();
    trendChart = null;
  }
  if (gainPctChart) {
    gainPctChart.destroy();
    gainPctChart = null;
  }
  if (donutChart) {
    donutChart.destroy();
    donutChart = null;
  }
}

function bucketKey(d, mode) {
  const y = d.getUTCFullYear();
  const mo = String(d.getUTCMonth() + 1).padStart(2, '0');
  const dy = String(d.getUTCDate()).padStart(2, '0');
  if (mode === 'day') return `${y}-${mo}-${dy}`;
  const h = String(d.getUTCHours()).padStart(2, '0');
  return `${y}-${mo}-${dy} ${h}:00`;
}

function buildTimeBuckets(events, mode) {
  const acc = {};
  events.forEach((e) => {
    const d = parseTs(e.ts);
    if (!d) return;
    const k = bucketKey(d, mode);
    acc[k] = (acc[k] || 0) + (e.approx_tokens || 0);
  });
  const labels = Object.keys(acc).sort();
  return { labels, values: labels.map((l) => acc[l]) };
}

function num(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function isDiffOnlyEvent(e) {
  return String(e.event || '').startsWith('diffOnlyApply');
}

function diffOnlySavings(e) {
  const d = e.diff_only;
  if (!d || typeof d !== 'object') return 0;
  return Math.ceil(num(d.estimated_chars_saved) / 4);
}

function eventOptimizationSavings(e) {
  if (isSubagentLaunch(e) || e.event === 'preToolUseCompression') {
    return hookSavedTokens(e);
  }
  if (isDiffOnlyEvent(e)) return diffOnlySavings(e);
  if (e.event === 'codeReviewGraph') {
    return num(e.saved_tokens);
  }
  return 0;
}

function observedTokens(e) {
  if (e.event === 'afterFileEdit' || e.event === 'afterTabFileEdit') return 0;
  if (isDiffOnlyEvent(e)) return 0;
  if (e.event === 'afterAgentResponse') {
    const billed = num(e.billed_total_tokens);
    if (billed > 0) return billed;
    const inp = num(e.input_tokens);
    const out = num(e.output_tokens);
    if (inp > 0 || out > 0) return inp + out;
  }
  if (isSubagentLaunch(e)) {
    return num(e.compression_after_tokens) || num(e.approx_tokens);
  }
  if (e.event === 'subagentStop') return num(e.approx_tokens);
  if (e.event === 'postToolUse') return num(e.approx_tokens);
  return num(e.approx_tokens);
}

function rtkDailyMap(rtkGain) {
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

function buildConsumptionComparison(events, mode, rtkGain) {
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

function buildDailyGainPct(events, rtkGain) {
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

function summarizeOptimizationTotals(events, rtkGain) {
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

async function loadLayerKpis() {
  try {
    const res = await fetch('/api/layer-kpis?source=' + getSource());
    if (!res.ok) return null;
    return await res.json();
  } catch (_) {
    return null;
  }
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

function buildEventTotals(events) {
  const acc = {};
  events.forEach((e) => {
    if (e.event === 'afterFileEdit' || e.event === 'afterTabFileEdit') return;
    const k = e.event || '(unknown)';
    acc[k] = (acc[k] || 0) + (e.approx_tokens || 0);
  });
  const labels = Object.keys(acc);
  const data = labels.map((l) => acc[l]);
  const colors = labels.map((l) => eventColor(l));
  return { labels, data, colors };
}

function buildToolRankings(events, limit = 24) {
  const map = {};
  events
    .filter((e) => e.event === 'postToolUse')
    .forEach((e) => {
      const t = (e.tool && String(e.tool).trim()) || '(unknown)';
      if (!map[t]) map[t] = { count: 0, tokens: 0 };
      map[t].count++;
      map[t].tokens += e.approx_tokens || 0;
    });
  return Object.entries(map)
    .map(([tool, v]) => ({ tool, ...v }))
    .sort((a, b) => b.tokens - a.tokens)
    .slice(0, limit);
}

function renderTables(events) {
  const toolList = document.getElementById('toolList');
  const recentList = document.getElementById('recentList');
  const emptyTools = document.getElementById('emptyTools');
  const emptyLines = document.getElementById('emptyLines');
  toolList.replaceChildren();
  recentList.replaceChildren();

  const ranked = buildToolRankings(events);
  emptyTools.hidden = ranked.length > 0;
  toolList.hidden = ranked.length === 0;
  ranked.forEach((r, idx) => {
    const row = document.createElement('div');
    row.className = 'feed-row';
    row.style.setProperty('--accent', EVENT_COLORS.postToolUse);
    const bar = document.createElement('div');
    bar.className = 'feed-row-accent';
    const cols = document.createElement('div');
    cols.className = 'tool-row-cols';

    const left = document.createElement('div');
    const rank = document.createElement('span');
    rank.className = 'strong';
    rank.textContent = `#${idx + 1}`;
    left.appendChild(rank);
    left.appendChild(document.createTextNode(' · '));
    const pill = document.createElement('span');
    pill.className = 'tool-pill';
    pill.textContent = r.tool;
    left.appendChild(pill);

    const mid = document.createElement('div');
    mid.className = 'mono';
    mid.textContent = `${r.count}×`;

    const right = document.createElement('div');
    right.className = 'mono num';
    right.textContent = fmtNum(r.tokens);

    cols.appendChild(left);
    cols.appendChild(mid);
    cols.appendChild(right);
    row.appendChild(bar);
    row.appendChild(cols);
    toolList.appendChild(row);
  });

  const sorted = [...events].sort((a, b) => {
    const da = parseTs(a.ts)?.getTime() || 0;
    const db = parseTs(b.ts)?.getTime() || 0;
    return db - da;
  });
  const recent = sorted.slice(0, 50);
  emptyLines.hidden = recent.length > 0;
  recentList.hidden = recent.length === 0;

  recent.forEach((e) => {
    const row = document.createElement('div');
    row.className = 'feed-row';
    row.style.setProperty('--accent', eventColor(e.event || ''));
    const bar = document.createElement('div');
    bar.className = 'feed-row-accent';
    const cols = document.createElement('div');
    cols.className = 'feed-cols';

    const cDate = document.createElement('div');
    cDate.className = 'mono cell-wide';
    cDate.textContent = fmtDateUtcCell(e.ts);

    const cEvt = document.createElement('div');
    const pill = document.createElement('span');
    pill.className = 'evt-pill';
    pill.textContent = e.event || '—';
    cEvt.appendChild(pill);

    const cTok = document.createElement('div');
    cTok.className = 'num strong';
    cTok.textContent = fmtNum(e.approx_tokens);

    const cTool = document.createElement('div');
    cTool.className = 'mono';
    if (e.event === 'afterAgentResponse') {
      const status = document.createElement('span');
      status.className = 'tool-pill';
      let label;
      if (typeof e.billed_total_tokens === 'number') {
        label = t('billed', { val: fmtCompact(e.billed_total_tokens) });
      } else if (e.consumption_complete === true) {
        label = t('consoOk');
      } else if (e.consumption_present === true) {
        label = t('consoPartial');
      } else {
        label = t('consoMissing');
      }
      status.textContent = label;
      cTool.appendChild(status);
    } else if (isSubagentLaunch(e) || e.event === 'subagentStop') {
      const tag = document.createElement('span');
      tag.className = 'tool-pill';
      tag.textContent = e.skill_hint || e.subagent_type || e.event;
      cTool.appendChild(tag);
    } else {
      const tVal = e.tool && String(e.tool).trim();
      if (tVal) {
        const tp = document.createElement('span');
        tp.className = 'tool-pill';
        tp.textContent = tVal;
        cTool.appendChild(tp);
      } else {
        cTool.textContent = '—';
      }
    }

    const cDelta = document.createElement('div');
    cDelta.className = 'num';
    const la = Number(e.lines_added || 0);
    const lr = Number(e.lines_removed || 0);
    if (la + lr === 0) {
      const em = document.createElement('span');
      em.className = 'mono';
      em.textContent = '—';
      cDelta.appendChild(em);
    } else {
      const sp1 = document.createElement('span');
      sp1.style.color = 'var(--neon-lime)';
      sp1.textContent = `+${fmtNum(la)}`;
      cDelta.appendChild(sp1);
      const mid = document.createElement('span');
      mid.className = 'mono';
      mid.textContent = ' / ';
      cDelta.appendChild(mid);
      const sp2 = document.createElement('span');
      sp2.style.color = 'var(--orange-accent)';
      sp2.textContent = `−${fmtNum(lr)}`;
      cDelta.appendChild(sp2);
    }

    const cChars = document.createElement('div');
    cChars.className = 'mono num';
    cChars.textContent = `${fmtNum(e.text_chars)} / ${fmtNum(e.raw_chars)}`;

    cols.appendChild(cDate);
    cols.appendChild(cEvt);
    cols.appendChild(cTok);
    cols.appendChild(cTool);
    cols.appendChild(cDelta);
    cols.appendChild(cChars);
    row.appendChild(bar);
    row.appendChild(cols);
    recentList.appendChild(row);
  });
}

function areaGradient(ctx, chartArea, isDark) {
  const g = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
  if (isDark) {
    g.addColorStop(0, 'rgba(107, 159, 255, 0)');
    g.addColorStop(0.45, 'rgba(255, 79, 216, 0.14)');
    g.addColorStop(1, 'rgba(78, 240, 224, 0.18)');
  } else {
    g.addColorStop(0, 'rgba(91, 141, 255, 0)');
    g.addColorStop(0.5, 'rgba(91, 141, 255, 0.14)');
    g.addColorStop(1, 'rgba(214, 61, 184, 0.12)');
  }
  return g;
}

function renderCharts(events, bucketMode, isDark, rtkGain) {
  destroyCharts();

  let comp = buildConsumptionComparison(events, bucketMode, rtkGain);
  if (!comp.labels.length) {
    comp = { labels: ['∅'], actualData: [0], counterfactualData: [0], savingsData: [0] };
  }

  let { labels: dl, data, colors } = buildEventTotals(events);
  if (!dl.length) {
    dl = [t('none')];
    data = [1];
    colors = ['#4a5870'];
  }

  const tick = isDark ? 'rgba(220,220,235,0.55)' : 'rgba(30,28,52,0.55)';
  const grid = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(91,141,255,0.08)';

  let gain = buildDailyGainPct(events, rtkGain);
  if (!gain.labels.length) {
    gain = {
      labels: ['∅'],
      pctData: [0],
      actualData: [0],
      savingsData: [0],
      rtkData: [0],
      hookDiffData: [0],
    };
  }
  const positivePct = gain.pctData.filter((p) => p > 0);
  const minGainPct = positivePct.length ? Math.min(...positivePct) : 0;
  const maxGainPct = Math.max(...gain.pctData, 0);
  const useLogGainAxis = maxGainPct > 5 && minGainPct > 0 && maxGainPct / minGainPct >= 15;
  const linearGainMax =
    maxGainPct <= 0 ? 10 : maxGainPct < 20 ? Math.ceil(maxGainPct * 1.3 * 10) / 10 : 100;
  const gainBarFill = gain.pctData.map((p) => {
    const tVal = Math.min(Math.max(p, 0), 100) / 100;
    const a = 0.28 + tVal * 0.55;
    return isDark ? `rgba(78, 240, 224, ${a})` : `rgba(26, 158, 140, ${a})`;
  });
  const gainBarBorder = isDark ? '#4ef0e0' : '#1a9e8c';
  const ctxGain = document.getElementById('gainPctChart').getContext('2d');
  gainPctChart = new Chart(ctxGain, {
    type: 'bar',
    data: {
      labels: gain.labels,
      datasets: [
        {
          label: t('chartEstimatedGain'),
          data: gain.pctData,
          backgroundColor: gainBarFill,
          borderColor: gainBarBorder,
          borderWidth: 1,
          borderRadius: 4,
          maxBarThickness: 36,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: isDark ? 'rgba(14,10,26,0.92)' : 'rgba(255,255,255,0.96)',
          titleColor: isDark ? '#fff' : '#1a1430',
          bodyColor: isDark ? '#ccc' : '#333',
          borderColor: 'rgba(107,159,255,0.35)',
          borderWidth: 1,
          callbacks: {
            label(ctx) {
              const i = ctx.dataIndex;
              return t('chartTooltipGain', { pct: gain.pctData[i] });
            },
            afterBody(items) {
              if (!items.length) return [];
              const i = items[0].dataIndex;
              return [
                t('chartTooltipObserved', { val: fmtNum(gain.actualData[i]) }),
                t('chartTooltipSavings', { val: fmtNum(gain.savingsData[i]) }),
                t('chartTooltipRtk', { val: fmtNum(gain.rtkData[i]) }),
                t('chartTooltipHookDiff', { val: fmtNum(gain.hookDiffData[i]) }),
              ];
            },
          },
        },
      },
      scales: {
        x: {
          ticks: {
            color: tick,
            maxRotation: 45,
            minRotation: 0,
            font: { size: 9, family: "'Plus Jakarta Sans'" },
          },
          grid: { display: false },
          border: { display: false },
        },
        y: {
          type: useLogGainAxis ? 'logarithmic' : 'linear',
          min: useLogGainAxis ? Math.max(0.05, minGainPct * 0.4) : 0,
          max: useLogGainAxis ? 100 : linearGainMax,
          ticks: {
            color: tick,
            font: { size: 9, family: "'Plus Jakarta Sans'" },
            callback: (v) => {
              if (v < 0.1) return '';
              return v >= 10 || Number.isInteger(v) ? `${v} %` : `${v.toFixed(1)} %`;
            },
          },
          grid: { color: grid },
          border: { display: false },
        },
      },
    },
    plugins: [
      {
        id: 'gainPctBarLabels',
        afterDatasetsDraw(chart) {
          const { ctx } = chart;
          const meta = chart.getDatasetMeta(0);
          ctx.save();
          ctx.fillStyle = tick;
          ctx.font = "600 9px 'Plus Jakarta Sans', sans-serif";
          ctx.textAlign = 'center';
          meta.data.forEach((bar, i) => {
            const v = gain.pctData[i];
            if (!v || v <= 0 || !bar) return;
            const label = v >= 10 || Number.isInteger(v) ? `${v} %` : `${v.toFixed(1)} %`;
            const y = bar.y - 5;
            if (Number.isFinite(y)) ctx.fillText(label, bar.x, y);
          });
          ctx.restore();
        },
      },
    ],
  });

  const ctxTrend = document.getElementById('trendChart').getContext('2d');
  const observedColor = isDark ? '#4ef0e0' : '#1a9e8c';
  const counterColor = isDark ? '#ff9fd4' : '#c43d9a';
  trendChart = new Chart(ctxTrend, {
    type: 'line',
    data: {
      labels: comp.labels,
      datasets: [
        {
          label: t('consumedObserved'),
          data: comp.actualData,
          fill: true,
          tension: 0.38,
          pointRadius: 0,
          pointHoverRadius: 5,
          pointHoverBackgroundColor: '#fff',
          pointHoverBorderColor: observedColor,
          borderWidth: 2,
          borderColor: observedColor,
          backgroundColor(context) {
            const ch = context.chart;
            const { chartArea } = ch;
            if (!chartArea) return null;
            return areaGradient(ch.ctx, chartArea, isDark);
          },
        },
        {
          label: t('withoutOptimizations'),
          data: comp.counterfactualData,
          fill: false,
          tension: 0.38,
          pointRadius: 0,
          pointHoverRadius: 5,
          borderWidth: 2,
          borderDash: [7, 4],
          borderColor: counterColor,
          pointHoverBorderColor: counterColor,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          align: 'end',
          labels: {
            color: tick,
            boxWidth: 14,
            font: { size: 10, family: "'Plus Jakarta Sans'" },
          },
        },
        tooltip: {
          backgroundColor: isDark ? 'rgba(14,10,26,0.92)' : 'rgba(255,255,255,0.96)',
          titleColor: isDark ? '#fff' : '#1a1430',
          bodyColor: isDark ? '#ccc' : '#333',
          borderColor: 'rgba(107,159,255,0.35)',
          borderWidth: 1,
          callbacks: {
            afterBody(items) {
              if (!items.length) return [];
              const i = items[0].dataIndex;
              const saved = comp.savingsData[i] || 0;
              if (!saved) return [];
              return [t('chartTooltipSavings', { val: fmtNum(saved) })];
            },
          },
        },
      },
      scales: {
        x: {
          ticks: {
            color: tick,
            maxRotation: 45,
            minRotation: 42,
            font: { size: 9, family: "'Plus Jakarta Sans'" },
          },
          grid: { color: grid },
          border: { display: false },
        },
        y: {
          beginAtZero: true,
          ticks: { color: tick, font: { size: 9, family: "'Plus Jakarta Sans'" } },
          grid: { color: grid },
          border: { display: false },
        },
      },
      interaction: { intersect: false, mode: 'index' },
    },
  });

  const donutBg = isDark ? 'rgba(10,6,18,0.92)' : 'rgba(255,255,255,0.85)';
  const ctxDon = document.getElementById('donutChart').getContext('2d');
  donutChart = new Chart(ctxDon, {
    type: 'doughnut',
    data: {
      labels: dl,
      datasets: [
        {
          data,
          backgroundColor: colors.map((c) => c),
          borderColor: donutBg,
          borderWidth: 3,
          hoverBorderColor: '#fff',
          hoverOffset: 6,
        },
      ],
    },
    options: {
      responsive: true,
      cutout: '62%',
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: tick,
            boxWidth: 12,
            boxHeight: 12,
            padding: 14,
            font: { size: 10, family: "'Plus Jakarta Sans', sans-serif", weight: '500' },
          },
        },
      },
    },
  });
}

function renderEditStats(events) {
  let agentAdd = 0;
  let agentRem = 0;
  let agentPass = 0;
  let tabN = 0;
  let tabAdd = 0;
  events.forEach((e) => {
    // Support both afterFileEdit and postToolUse with Edit/Write
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
  const withReport = c.present;
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

function summarizeComplianceKpis(events) {
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

function renderComplianceTable(events) {
  const list = document.getElementById('complianceList');
  const head = document.getElementById('complianceHead');
  const empty = document.getElementById('emptyCompliance');
  list.replaceChildren();

  const rows = events
    .filter((e) => e.event === 'taskBriefValidation' || e.event === 'consumptionReportCompliance')
    .sort((a, b) => (parseTs(b.ts)?.getTime() || 0) - (parseTs(a.ts)?.getTime() || 0))
    .slice(0, 40);

  empty.hidden = rows.length > 0;
  list.hidden = rows.length === 0;
  head.hidden = rows.length === 0;

  rows.forEach((e) => {
    const row = document.createElement('div');
    row.className = 'feed-row';
    row.style.setProperty('--accent', eventColor(e.event || ''));
    const bar = document.createElement('div');
    bar.className = 'feed-row-accent';
    const cols = document.createElement('div');
    cols.className = 'feed-cols compliance-row-cols';

    const cDate = document.createElement('div');
    cDate.className = 'mono cell-wide';
    cDate.textContent = fmtDateUtcCell(e.ts);

    const cEvt = document.createElement('div');
    const pill = document.createElement('span');
    pill.className = 'evt-pill';
    pill.textContent = e.event === 'taskBriefValidation' ? 'brief' : 'conso';
    cEvt.appendChild(pill);

    const cDetail = document.createElement('div');
    cDetail.className = 'mono cell-wide';
    if (e.event === 'taskBriefValidation') {
      cDetail.textContent = (e.brief_violations || e.subagent_type || '—').slice(0, 140);
      cDetail.title = String(e.brief_violations || '');
    } else {
      cDetail.textContent = t('complianceLoopEnforced', {
        loop: e.loop_count ?? '?',
        enforced: e.consumption_enforced === true,
      });
    }

    const cStatus = document.createElement('div');
    const statusPill = document.createElement('span');
    statusPill.className = 'tool-pill';
    if (e.event === 'taskBriefValidation') {
      statusPill.textContent = e.brief_valid === false ? t('denied') : t('ok');
    } else {
      statusPill.textContent = e.consumption_complete === true ? t('complete') : t('incomplete');
    }
    cStatus.appendChild(statusPill);

    cols.appendChild(cDate);
    cols.appendChild(cEvt);
    cols.appendChild(cDetail);
    cols.appendChild(cStatus);
    row.appendChild(bar);
    row.appendChild(cols);
    list.appendChild(row);
  });
}

function renderCrgTable(events) {
  const list = document.getElementById('crgList');
  const head = document.getElementById('crgHead');
  const empty = document.getElementById('emptyCrg');
  list.replaceChildren();

  const rows = events
    .filter((e) => e.event === 'codeReviewGraph')
    .sort((a, b) => (parseTs(b.ts)?.getTime() || 0) - (parseTs(a.ts)?.getTime() || 0))
    .slice(0, 40);

  empty.hidden = rows.length > 0;
  list.hidden = rows.length === 0;
  head.hidden = rows.length === 0;

  let crgSaved = 0;
  let crgRiskSum = 0.0;

  const allCrg = events.filter((e) => e.event === 'codeReviewGraph');
  allCrg.forEach((e) => {
    crgSaved += num(e.saved_tokens);
    crgRiskSum += num(e.risk_score);
  });

  document.getElementById('kpiCrgRuns').textContent = fmtNum(allCrg.length);
  document.getElementById('kpiCrgSaved').textContent = fmtCompact(crgSaved);
  document.getElementById('kpiCrgRisk').textContent =
    allCrg.length > 0 ? (crgRiskSum / allCrg.length).toFixed(2) : '—';

  rows.forEach((e) => {
    const row = document.createElement('div');
    row.className = 'feed-row';
    row.style.setProperty('--accent', '#10b981');
    const bar = document.createElement('div');
    bar.className = 'feed-row-accent';
    const cols = document.createElement('div');
    cols.className = 'feed-cols crg-row-cols';

    const cDate = document.createElement('div');
    cDate.className = 'mono cell-wide';
    cDate.textContent = fmtDateUtcCell(e.ts);

    const cRepo = document.createElement('div');
    cRepo.className = 'mono';
    cRepo.textContent = e.repo || '—';

    const cBranch = document.createElement('div');
    cBranch.className = 'mono cell-wide';
    cBranch.textContent = e.branch || '—';
    cBranch.title = e.branch || '';

    const cFilesFns = document.createElement('div');
    cFilesFns.className = 'mono';
    cFilesFns.textContent = `${e.files_changed ?? 0} / ${e.functions_changed ?? 0}`;

    const cGaps = document.createElement('div');
    cGaps.className = 'mono num';
    cGaps.textContent = fmtNum(e.test_gaps);

    const cSaved = document.createElement('div');
    cSaved.className = 'mono num strong';
    cSaved.textContent = `${fmtCompact(e.saved_tokens)} (~${e.saved_percent ?? 0}%)`;

    const cRisk = document.createElement('div');
    const riskPill = document.createElement('span');
    riskPill.className = 'tool-pill';
    const r = num(e.risk_score);
    riskPill.textContent = r.toFixed(2);
    if (r >= 0.7) {
      riskPill.style.borderColor = 'rgba(239, 68, 68, 0.4)';
      riskPill.style.color = '#ef4444';
    } else if (r >= 0.4) {
      riskPill.style.borderColor = 'rgba(245, 158, 11, 0.4)';
      riskPill.style.color = '#f59e0b';
    } else {
      riskPill.style.borderColor = 'rgba(16, 185, 129, 0.4)';
      riskPill.style.color = '#10b981';
    }
    cRisk.appendChild(riskPill);

    cols.appendChild(cDate);
    cols.appendChild(cRepo);
    cols.appendChild(cBranch);
    cols.appendChild(cFilesFns);
    cols.appendChild(cGaps);
    cols.appendChild(cSaved);
    cols.appendChild(cRisk);

    row.appendChild(bar);
    row.appendChild(cols);
    list.appendChild(row);
  });
}

function isSubagentLaunch(e) {
  return e.event === 'subagentLaunch' || e.event === 'preToolUseCompression';
}

function rowGitCacheHit(e) {
  return e.compression_git_cache_hit === true || e.git_cache_hit === true;
}

function rowGitCacheTokensPreserved(e) {
  const keys = [
    'git_cache_block2_tokens_preserved',
    'compression_block2_tokens_preserved',
    'block2_tokens_preserved',
  ];
  for (const key of keys) {
    const v = Number(e[key]);
    if (Number.isFinite(v) && v > 0) return v;
  }
  if (rowGitCacheHit(e)) {
    const after = Number(e.compression_after_tokens || e.approx_tokens || 0);
    return after > 0 ? Math.max(0, Math.round(after * 0.12)) : 0;
  }
  return 0;
}

function rowGuardrailLoopHalt(e) {
  return e.guardrail_loop_halt === true;
}

function rowGuardrailIntercepted(e) {
  if (e.guardrail_intercepted === true) return true;
  if (rowGuardrailLoopHalt(e)) return true;
  return e.guardrail_roi_gate === true && String(e.guardrail_risk || '').toLowerCase() === 'high';
}

function rowGuardrailAvoidedTokens(e) {
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

function rowIdempotentInjected(e) {
  return e.idempotent_context_injected === true;
}

function summarizeStackKpis(events) {
  const launches = events.filter(isSubagentLaunch);
  const gitHits = launches.filter(rowGitCacheHit).length;
  const gitPreserved = launches
    .filter(rowGitCacheHit)
    .reduce((sum, e) => sum + rowGitCacheTokensPreserved(e), 0);
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

function makeOptBadge(label, className, title) {
  const pill = document.createElement('span');
  pill.className = `opt-badge ${className}`;
  pill.textContent = label;
  if (title) pill.title = title;
  return pill;
}

function renderLaunchOptBadges(launch, container) {
  container.replaceChildren();
  const parts = [];
  if (rowGitCacheHit(launch)) {
    const preserved = rowGitCacheTokensPreserved(launch);
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

function hookSavedTokens(e) {
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

function hookSavedPct(e) {
  const inputTok = Number(e.compression_input_tokens || 0);
  if (inputTok > 0) {
    return (100 * hookSavedTokens(e)) / inputTok;
  }
  return Number(e.compression_saved_pct || 0);
}

function compressionSummary(e) {
  const claw = e.compression_used_claw_compactor === true;
  const llm = e.compression_used_llmlingua === true;
  const backend = String(e.compression_backend || '').trim() || '—';
  const saved = hookSavedTokens(e);
  const pct = hookSavedPct(e);
  let label = '—';
  if (claw && llm) label = 'claw+llm';
  else if (claw) label = 'claw';
  else if (llm) label = 'llm';
  else if (backend !== '—') label = backend;
  return { label, backend, claw, llm, saved, pct };
}

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

/** Mirrors telemetry_metrics.summarize_report (report.py parity). */
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
  let billedN = 0;
  let latestBilled = null;
  let latestIn = 0;
  let latestOut = 0;

  const responses = events.filter((e) => e.event === 'afterAgentResponse');
  if (responses.length) {
    const latest = responses.reduce((a, b) =>
      (parseTs(b.ts)?.getTime() || 0) >= (parseTs(a.ts)?.getTime() || 0) ? b : a
    );
    if (typeof latest.billed_total_tokens === 'number') {
      latestBilled = latest.billed_total_tokens;
      latestIn = Number(latest.input_tokens || 0);
      latestOut = Number(latest.output_tokens || 0);
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
      avg: billedN ? Math.floor(billedSum / billedN) : 0,
      count: billedN,
      latest: latestBilled,
      latest_input: latestIn,
      latest_output: latestOut,
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
    document.getElementById('kpiParentBilled').textContent = fmtCompact(billed.avg || 0);
    document.getElementById('kpiParentBilledSub').textContent = t('avgSumLatest', {
      sum: fmtCompact(billed.sum || 0),
      count: fmtNum(billed.count),
      latest: fmtCompact(billed.latest || 0),
    });
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
    if (comp.claw && comp.llm) compressPill.classList.add('claw');
    else if (comp.claw) compressPill.classList.add('claw');
    else if (comp.llm) compressPill.classList.add('llm');
    else compressPill.classList.add('none');
    const pctLabel = comp.saved > 0 ? ` −${comp.pct.toFixed(0)}%` : '';
    compressPill.textContent = `${comp.label}${pctLabel}`;
    compressPill.title = `backend=${comp.backend} · saved≈${comp.saved} tok`;
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

let currentEvents = [];

const LS_REFRESH = 'cursor_telemetry_auto_refresh_ms';
const LS_SECTION_ORDER = 'cursor_telemetry_dash_section_order';
const LS_SECTION_COLLAPSED = 'cursor_telemetry_dash_section_collapsed';
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
/** @type {ReturnType<typeof setInterval> | null} */
let refreshTimerId = null;
let refreshIntervalMs = 0;
/** Local JSONL replaces API until user hits manual refresh */
let fileOverride = false;

function resizeVisibleCharts() {
  requestAnimationFrame(() => {
    [trendChart, gainPctChart, donutChart].forEach((ch) => {
      try {
        ch?.resize();
      } catch (_) {
        /* ignore */
      }
    });
  });
}

function collectLayoutState(container) {
  return {
    order: [...container.querySelectorAll('.dash-section')].map((s) => s.dataset.sectionId),
    collapsed: [...document.querySelectorAll('.dash-section.is-collapsed')].map(
      (s) => s.dataset.sectionId
    ),
  };
}

function getSource() {
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

function persistLayoutPrefs(container) {
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

async function loadLayoutPrefs() {
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
  persistLayoutPrefs(container);
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
      persistLayoutPrefs(container);
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

async function loadApi() {
  const res = await fetch('/api/events?source=' + getSource());
  if (!res.ok) throw new Error('API ' + res.status);
  return res.json();
}

async function loadRtkGain() {
  const res = await fetch('/api/rtk-gain?source=' + getSource());
  if (!res.ok) throw new Error('RTK API ' + res.status);
  return res.json();
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
  document.getElementById('refreshIntervalLabel').textContent = short;
}

function setRefreshInterval(ms) {
  const allowed = new Set([0, 300000, 1800000, 3600000]);
  refreshIntervalMs = allowed.has(ms) ? ms : 0;
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

let availableProviders = [];

async function loadProviders() {
  try {
    const resp = await fetch('/api/providers');
    if (!resp.ok) throw new Error('Failed to load providers');
    availableProviders = await resp.json();
    return availableProviders;
  } catch (e) {
    console.error('Failed to load providers:', e);
    availableProviders = [];
    return availableProviders;
  }
}

function showNoProvidersError() {
  // Create error overlay that covers everything
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

  // Add styles
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

  // Clear existing options
  select.innerHTML = '';

  // Add options from providers
  providers.forEach((provider) => {
    const option = document.createElement('option');
    option.value = provider.id;
    option.textContent = provider.label;
    select.appendChild(option);
  });

  // Set selected value if it exists in the list, otherwise use first available
  if (providers.find((p) => p.id === selectedId)) {
    select.value = selectedId;
  } else if (providers.length > 0) {
    select.value = providers[0].id;
    // Update localStorage with the fallback
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

(async function init() {
  // Initialize language
  const lang = getLanguage();
  applyTranslations(lang);

  // Bind language selector change listener
  document.getElementById('langSelect').addEventListener('change', (ev) => {
    setLanguage(ev.target.value);
    if (currentEvents.length) renderAll(currentEvents);
    else applyTranslations(ev.target.value);
  });

  // Load available providers from API
  const providers = await loadProviders();

  // Error if no providers enabled
  if (providers.length === 0) {
    showNoProvidersError();
    return;
  }

  // Get saved source preference
  let activeSource = 'cursor';
  try {
    activeSource = localStorage.getItem('cursor_telemetry_source') || 'cursor';
  } catch (_) {}

  // Populate provider select with available providers
  populateProviderSelect(providers, activeSource);
  updateHeaderTitle();

  // Show the app now that we know providers exist
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
