import { t } from './dashboard_translations.js';
import { fmtNum, eventColor } from './dashboard_utils.js';
import { buildConsumptionComparison, buildDailyGainPct } from './dashboard_stats.js';

let trendChart = null;
let gainPctChart = null;
let donutChart = null;

export function destroyCharts() {
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

export function buildEventTotals(events) {
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

export function areaGradient(ctx, chartArea, isDark) {
  const g = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
  if (isDark) {
    g.addColorStop(0, 'rgba(255, 79, 216, 0)');
    g.addColorStop(0.45, 'rgba(255, 79, 216, 0.14)');
    g.addColorStop(1, 'rgba(78, 240, 224, 0.18)');
  } else {
    g.addColorStop(0, 'rgba(91, 141, 255, 0)');
    g.addColorStop(0.5, 'rgba(91, 141, 255, 0.14)');
    g.addColorStop(1, 'rgba(214, 61, 184, 0.12)');
  }
  return g;
}

export function renderCharts(events, bucketMode, isDark, rtkGain) {
  destroyCharts();

  if (typeof Chart === 'undefined') {
    console.warn('Chart.js is not loaded; skipping chart rendering.');
    return;
  }

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
