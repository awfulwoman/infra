class ZfsBackupCard extends HTMLElement {
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
    const stale = attrs.stale_datasets || [];
    const healthy = attrs.healthy_datasets || [];
    const isOk = entity.state === 'off';
    const host = attrs.host || this.config.entity;
    const title = this.config.title || host;
    const pulledAt = attrs.pulled_at
      ? new Date(attrs.pulled_at).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
      : '';

    const staleRows = stale.map(ds => `
      <div class="row">
        <span class="icon bad">✕</span>
        <span class="dataset bad" title="${ds}">${ds}</span>
      </div>
    `).join('');

    const healthyRows = healthy.map(ds => `
      <div class="row">
        <span class="icon ok">✓</span>
        <span class="dataset" title="${ds}">${ds}</span>
      </div>
    `).join('');

    this.shadowRoot.innerHTML = `
      <ha-card>
        <style>
          :host {
            --ok: var(--success-color, #4caf50);
            --bad: var(--error-color, #f44336);
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
          .datasets {
            padding: 0 16px 12px;
          }
          .divider {
            height: 1px;
            background: var(--border);
            margin-bottom: 8px;
          }
          .row {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 2px 0;
          }
          .icon {
            font-size: 11px;
            font-weight: 700;
            width: 12px;
            flex-shrink: 0;
          }
          .icon.ok { color: var(--ok); }
          .icon.bad { color: var(--bad); }
          .dataset {
            font-family: var(--code-font-family, monospace);
            font-size: 11px;
            color: var(--muted);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          .dataset.bad { color: var(--bad); font-weight: 500; }
          .missing { padding: 16px; color: var(--bad); font-size: 13px; }
        </style>
        <div class="header">
          <div class="dot"></div>
          <span class="title">${title}</span>
          <span class="timestamp">${pulledAt}</span>
        </div>
        <div class="datasets">
          <div class="divider"></div>
          ${staleRows}
          ${healthyRows}
        </div>
      </ha-card>
    `;
  }

  getCardSize() {
    const entity = this._hass && this._hass.states[this.config && this.config.entity];
    const attrs = entity ? entity.attributes : {};
    const rows = (attrs.stale_datasets || []).length + (attrs.healthy_datasets || []).length;
    return Math.ceil(rows / 3) + 2;
  }
}

customElements.define('zfs-backup-card', ZfsBackupCard);
