export const TRANSLATIONS = {
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
    agentStatusTitle: 'Agent Status & Effective Capabilities',
    agentTip: 'Tip: Run python install_stack.py to deploy missing components',
    statusActive: 'Active',
    statusInstalled: 'Installed (Idle)',
    statusMissing: 'Missing',
    statusUnsupported: 'Unsupported',
    itemTelemetry: 'Telemetry & Logs',
    itemHooks: 'Hooks & Interceptors',
    itemRtk: 'RTK Token Compressor',
    itemRules: 'Context Rules (.mdc / AGENTS.md)',
    itemSkills: 'Agent Skills (SKILL.md)',
    itemCompactor: 'Token Compactor Stack',
    itemMcp: 'MCP Tools Integration',
    activeCountBadge: '{active}/{total} Active',
    installAllBtn: 'Install Missing Components',
    installRowBtn: 'Deploy',

    installSuccess: 'Installed successfully!',

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
    tokensProxy: 'Tokens (estimated)',
    textChars: 'Text characters',
    consoReports: 'Conso reports',
    rtkGainSaved: 'RTK gain (estimated)',
    hookGainSaved: 'Hook gain (estimated)',
    globalGains: 'Global gains (estimated)',
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
    subPromptProxy: 'Sub prompt (estimated)',
    subOutProxy: 'Sub output (estimated)',
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
    avgSumLatestCacheAdjusted:
      'sum {sum} (adj: {adjSum}) · {count} resp. · latest {latest} (adj: {latestAdj})',
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
    section_kpi_ab_test: 'A/B Testing & Calibration (KPI)',
    abTestStatus: 'A/B Testing Status',
    abControlGroup: 'Control (Raw A)',
    abTreatmentGroup: 'Treatment (Optimized B)',
    abSavingsGroup: 'Real Savings (B vs A)',
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
    agentStatusTitle: "Statut de l'agent & fonctionnalités effectives",
    agentTip: 'Conseil : Exécutez python install_stack.py pour déployer les composants manquants',
    statusActive: 'Actif',
    statusInstalled: 'Installé (Inactif)',
    statusMissing: 'Absent',
    statusUnsupported: 'Non supporté',
    itemTelemetry: 'Télémétrie & Logs',
    itemHooks: 'Hooks & Intercepteurs',
    itemRtk: 'Compresseur RTK',
    itemRules: 'Règles de contexte (.mdc / AGENTS.md)',
    itemSkills: "Skills de l'agent (SKILL.md)",
    itemCompactor: 'Stack Token Compactor',
    itemMcp: 'Intégration MCP Tools',
    activeCountBadge: '{active}/{total} Actifs',
    installAllBtn: 'Installer les composants manquants',
    installRowBtn: 'Déployer',

    installSuccess: 'Installation réussie !',

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
    tokensProxy: 'Tokens (estimés)',
    textChars: 'Caractères texte',
    consoReports: 'Rapports conso',
    rtkGainSaved: 'Gain RTK (estimé)',
    hookGainSaved: 'Gain hook (estimé)',
    globalGains: 'Gains globaux (estimés)',
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
    subPromptProxy: 'Prompt sub (estimé)',
    subOutProxy: 'Output sub (estimé)',
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
    avgSumLatestCacheAdjusted:
      'somme {sum} (adj : {adjSum}) · {count} resp. · dernier {latest} (adj : {latestAdj})',
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
    section_kpi_ab_test: 'A/B Testing & Calibration (KPI)',
    abTestStatus: "Statut de l'A/B Testing",
    abControlGroup: 'Contrôle (Brut A)',
    abTreatmentGroup: 'Traitement (Optimisé B)',
    abSavingsGroup: 'Économies réelles (B vs A)',
  },
};

export function getLanguage() {
  try {
    return localStorage.getItem('cursor_telemetry_lang') || 'en';
  } catch (_) {
    return 'en';
  }
}

export function setLanguage(lang) {
  try {
    localStorage.setItem('cursor_telemetry_lang', lang);
  } catch (_) {}
  applyTranslations(lang);
}

export function t(key, replacements = {}) {
  const lang = getLanguage();
  let str = TRANSLATIONS[lang]?.[key] || TRANSLATIONS['en']?.[key] || key;
  Object.entries(replacements).forEach(([k, v]) => {
    str = str.replace(`{${k}}`, v);
  });
  return str;
}

export function applyTranslations(lang) {
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
  const refreshIntervalMs = window.__refreshIntervalMs;
  if (typeof refreshIntervalMs === 'number') {
    const syncEvent = new CustomEvent('sync-refresh-menu', { detail: refreshIntervalMs });
    window.dispatchEvent(syncEvent);
  }

  // Update header title if function exists
  const updateTitleEvent = new CustomEvent('update-header-title');
  window.dispatchEvent(updateTitleEvent);
}
