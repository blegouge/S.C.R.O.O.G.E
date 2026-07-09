import { t } from './dashboard_translations.js';
import {
  fmtNum,
  fmtCompact,
  parseTs,
  fmtDateUtcCell,
  eventColor,
  isSubagentLaunch,
  EVENT_COLORS,
  num,
} from './dashboard_utils.js';

export function buildToolRankings(events, limit = 24) {
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

export function renderTables(events) {
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

export function renderComplianceTable(events) {
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

export function renderCrgTable(events) {
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
