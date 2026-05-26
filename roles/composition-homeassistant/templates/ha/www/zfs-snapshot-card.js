class ZfsSnapshotCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    if (!config.entity) throw new Error('entity is required');
    this.config = config;
  }

  set hass(hass) {
    if (!this.config) return;
    const entity = hass.states[this.config.entity];
    if (!entity) {
      this.shadowRoot.innerHTML = `<ha-card><div class="missing">Entity ${this.config.entity} not found</div></ha-card>`;
      return;
    }

    const attrs = entity.attributes;
    const datasets = attrs.datasets || [];
    const staleSet = new Set(attrs.stale || []);
    const isOk = entity.state === 'off';
    const host = attrs.host || this.config.entity;
    const title = this.config.title || host;
    const checkedAt = attrs.checked_at
      ? new Date(attrs.checked_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
      : '';

    const TYPES = ['hourly', 'daily', 'monthly', 'yearly'];
    const LABELS = ['H', 'D', 'M', 'Y'];

    const rows = datasets.map(d => {
      const isStale = staleSet.has(d.dataset);
      const cells = TYPES.map(t => {
        const count = d.counts[t];
        const retain = d.retention[t];
        const bad = retain > 0 && count < retain;
        return `<td class="${bad ? 'bad' : ''}">${count}<span class="retain">/${retain}</span></td>`;
      }).join('');
      return `<tr class="${isStale ? 'stale-row' : ''}">
        <td class="dataset" title="${d.dataset}">
          ${d.dataset}
          <span class="policy policy-${d.policy}">${d.policy}</span>
        </td>
        ${cells}
      </tr>`;
    }).join('');

    this.shadowRoot.innerHTML = `
      <ha-card>
        <style>
          :host {
            --ok: var(--success-color, #4caf50);
            --bad: var(--error-color, #f44336);
            --warn: var(--warning-color, #ff9800);
            --text: var(--primary-text-color);
            --muted: var(--secondary-text-color);
            --border: var(--divider-color, rgba(0,0,0,0.12));
          }
          ha-card { overflow: hidden; }
          .header {
            display: flex;
            align-items: center;
            padding: 12px 16px 10px;
            gap: 8px;
          }
          .dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            flex-shrink: 0;
            background: var(${isOk ? '--ok' : '--bad'});
          }
          .title {
            flex: 1;
            font-size: 14px;
            font-weight: 500;
            color: var(--text);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          .timestamp {
            font-size: 11px;
            color: var(--muted);
            white-space: nowrap;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
          }
          th {
            padding: 4px 8px;
            color: var(--muted);
            font-weight: 500;
            border-bottom: 1px solid var(--border);
            white-space: nowrap;
          }
          th:first-child { text-align: left; padding-left: 16px; }
          th:not(:first-child) { text-align: right; }
          td {
            padding: 3px 8px;
            color: var(--text);
            border-bottom: 1px solid var(--border);
            white-space: nowrap;
          }
          td.dataset {
            text-align: left;
            font-family: var(--code-font-family, monospace);
            font-size: 11px;
            max-width: 200px;
            overflow: hidden;
            text-overflow: ellipsis;
            padding-left: 16px;
          }
          td:not(.dataset) { text-align: right; }
          td.bad { color: var(--bad); font-weight: 500; }
          .retain { color: var(--muted); font-weight: normal; }
          .policy {
            display: inline-block;
            font-family: var(--font-family-body, sans-serif);
            font-size: 9px;
            font-weight: 600;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            padding: 1px 4px;
            border-radius: 3px;
            margin-left: 4px;
            vertical-align: middle;
            opacity: 0.75;
          }
          .policy-critical { background: rgba(244,67,54,0.15); color: var(--bad); }
          .policy-high     { background: rgba(255,152,0,0.15); color: var(--warn); }
          .policy-low      { background: rgba(33,150,243,0.15); color: var(--info-color, #2196f3); }
          .policy-none     { background: rgba(0,0,0,0.07); color: var(--muted); }
          tr.stale-row td { background: rgba(244, 67, 54, 0.06); }
          tr:last-child td { border-bottom: none; }
          .missing { padding: 16px; color: var(--bad); font-size: 13px; }
        </style>
        <div class="header">
          <div class="dot"></div>
          <span class="title">${title}</span>
          <span class="timestamp">${checkedAt}</span>
        </div>
        <table>
          <thead>
            <tr>
              <th>Dataset</th>
              ${LABELS.map(l => `<th>${l}</th>`).join('')}
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </ha-card>
    `;
  }

  getCardSize() {
    const entity = this._hass && this._hass.states[this.config && this.config.entity];
    const rows = entity ? (entity.attributes.datasets || []).length : 4;
    return Math.ceil(rows / 2) + 2;
  }
}

customElements.define('zfs-snapshot-card', ZfsSnapshotCard);
