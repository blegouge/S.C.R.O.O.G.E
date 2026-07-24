import { persistLayoutPrefs } from './dashboard_api.js';

export const DEFAULT_SECTION_ORDER = [
  'kpi-summary',
  'kpi-savings',
  'kpi-editing',
  'kpi-subagents',
  'kpi-stack',
  'kpi-compliance',
  'kpi-ab-test',
  'table-subagents',
  'table-compliance',
  'table-crg',
  'charts',
  'tables-lists',
];

function resizeVisibleCharts() {
  window.dispatchEvent(new Event('resize-charts'));
}

export function collectLayoutState(container) {
  return {
    order: [...container.querySelectorAll('.dash-section')].map((s) => s.dataset.sectionId),
    collapsed: [...document.querySelectorAll('.dash-section.is-collapsed')].map(
      (s) => s.dataset.sectionId
    ),
  };
}

export function applySectionOrder(container, order) {
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

export function applySectionCollapsed(collapsed) {
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

export function toggleDashSection(section, container) {
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

export function bindPointerSectionReorder(container) {
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
