import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { catchError, of } from 'rxjs';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';

interface AuditLog {
  id: string;
  timestamp: string;
  action: string;
  category: string;
  actor_id: string;
  actor_role: string;
  target_type?: string;
  target_id?: string;
  result: 'success' | 'failure' | 'denied';
  ip_address?: string;
}

interface AuditLogsResponse {
  total: number;
  logs: AuditLog[];
}

@Component({
  selector: 'app-logs',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  template: `
    <div class="logs-page">
      <div class="page-header">
        <div class="page-header-left">
          <h1 class="page-title">{{ 'logs.title' | t }}</h1>
          <span class="logs-badge">{{ 'logs.audit_badge' | t }}</span>
        </div>
      </div>

      <!-- Not implemented notice -->
      <div *ngIf="notAvailable()" class="unavailable-panel">
        <div class="unavailable-icon">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="10" r="9" stroke="currentColor" stroke-width="1.2"/>
            <path d="M10 6v5M10 13v1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="unavailable-body">
          <div class="unavailable-title">{{ 'logs.unavailable_title' | t }}</div>
          <p class="unavailable-desc">
            {{ 'logs.unavailable_desc' | t }}
            (<code class="inline-mono">GET /api/v1/audit/logs</code>)
          </p>
          <ul class="unavailable-list">
            <li>{{ 'logs.unavailable_item1' | t }}</li>
            <li>{{ 'logs.unavailable_item2' | t }}</li>
            <li>{{ 'logs.unavailable_item3' | t }}</li>
            <li>{{ 'logs.unavailable_item4' | t }}</li>
          </ul>
          <div class="unavailable-meta">{{ 'logs.unavailable_meta' | t }}</div>
        </div>
      </div>

      <!-- Loading skeleton -->
      <div *ngIf="loading()" class="skeleton-list">
        <div class="skeleton skeleton-row" *ngFor="let i of [1,2,3,4,5,6]"></div>
      </div>

      <!-- Data when available -->
      <ng-container *ngIf="!loading() && !notAvailable()">
        <div class="filters-bar">
          <select class="filter-select" [(ngModel)]="filterCategory" (ngModelChange)="applyFilters()">
            <option value="">{{ 'logs.all_categories' | t }}</option>
            <option value="auth">{{ 'logs.category_auth' | t }}</option>
            <option value="admin">{{ 'logs.category_admin' | t }}</option>
            <option value="release">{{ 'logs.category_release' | t }}</option>
            <option value="connector">{{ 'logs.category_connector' | t }}</option>
            <option value="config">{{ 'logs.category_config' | t }}</option>
          </select>
          <select class="filter-select" [(ngModel)]="filterResult" (ngModelChange)="applyFilters()">
            <option value="">{{ 'logs.all_results' | t }}</option>
            <option value="success">{{ 'logs.result_success' | t }}</option>
            <option value="failure">{{ 'logs.result_failure' | t }}</option>
            <option value="denied">{{ 'logs.result_denied' | t }}</option>
          </select>
          <button class="btn-ghost" (click)="resetFilters()">{{ 'logs.clear_btn' | t }}</button>
        </div>

        <div class="privacy-notice">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <circle cx="6" cy="6" r="5.5" stroke="currentColor" stroke-width="1"/>
            <path d="M6 5.5v3M6 3.5v.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
          </svg>
          {{ 'logs.privacy_notice' | t }}
        </div>

        <div class="data-table-wrap">
          <table class="data-table" *ngIf="paginated().length > 0; else emptyState">
            <thead>
              <tr>
                <th>{{ 'logs.col_timestamp' | t }}</th>
                <th>{{ 'logs.col_category' | t }}</th>
                <th>{{ 'logs.col_action' | t }}</th>
                <th>{{ 'logs.col_actor' | t }}</th>
                <th>{{ 'logs.col_role' | t }}</th>
                <th>{{ 'logs.col_result' | t }}</th>
                <th>{{ 'logs.col_ip' | t }}</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let log of paginated()">
                <td><code class="mono-sm">{{ log.timestamp | date:'dd/MM/yy HH:mm:ss' }}</code></td>
                <td><span class="category-chip">{{ log.category }}</span></td>
                <td class="cell-action">{{ log.action }}</td>
                <td><code class="mono-sm">{{ maskId(log.actor_id) }}</code></td>
                <td class="cell-muted">{{ log.actor_role }}</td>
                <td>
                  <span class="result-badge" [class]="'result-' + log.result">
                    {{ resultLabel(log.result) }}
                  </span>
                </td>
                <td><code class="mono-sm">{{ log.ip_address ? maskIp(log.ip_address) : '—' }}</code></td>
              </tr>
            </tbody>
          </table>
          <ng-template #emptyState>
            <div class="empty-state">{{ 'logs.empty_filter' | t }}</div>
          </ng-template>

          <div class="table-footer" *ngIf="filtered().length > 0">
            <span class="count-label">{{ 'logs.count' | t : { n: filtered().length } }}</span>
            <div class="pagination" *ngIf="filtered().length > pageSize">
              <button class="btn-ghost" [disabled]="page() === 0" (click)="prevPage()">{{ 'logs.previous' | t }}</button>
              <span class="page-info">{{ page() + 1 }} / {{ totalPages() }}</span>
              <button class="btn-ghost" [disabled]="page() >= totalPages() - 1" (click)="nextPage()">{{ 'logs.next' | t }}</button>
            </div>
          </div>
        </div>
      </ng-container>
    </div>
  `,
  styles: [`
    :host { display: block; }
    .logs-page { padding: 0; }

    .page-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: var(--spacing-lg);
    }

    .page-header-left {
      display: flex;
      align-items: baseline;
      gap: var(--spacing-md);
    }

    .page-title {
      font-family: var(--font-display);
      font-size: 2.25rem;
      font-weight: 400;
      line-height: 1.1;
      letter-spacing: -0.02em;
      margin: 0;
      color: var(--ink);
    }

    .logs-badge {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      background: var(--paper-secondary);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 0.125rem 0.5rem;
    }

    .unavailable-panel {
      display: flex;
      gap: var(--spacing-lg);
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
    }

    .unavailable-icon {
      flex-shrink: 0;
      color: var(--muted);
      margin-top: 0.125rem;
    }

    .unavailable-body { flex: 1; }

    .unavailable-title {
      font-family: var(--font-sans);
      font-size: 1rem;
      font-weight: 600;
      color: var(--ink);
      margin-bottom: var(--spacing-sm);
    }

    .unavailable-desc {
      font-size: 0.8125rem;
      color: var(--muted);
      line-height: 1.6;
      margin: 0 0 var(--spacing-sm);
    }

    .unavailable-list {
      font-size: 0.8125rem;
      color: var(--muted);
      line-height: 1.7;
      margin: 0 0 var(--spacing-sm);
      padding-left: var(--spacing-lg);
    }

    .unavailable-meta {
      font-size: 0.75rem;
      color: var(--muted);
      font-style: italic;
    }

    .inline-mono {
      font-family: var(--font-mono);
      font-size: 0.8125rem;
      background: var(--paper-secondary);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 0 0.25rem;
    }

    .filters-bar {
      display: flex;
      gap: var(--spacing-sm);
      margin-bottom: var(--spacing-sm);
    }

    .filter-select {
      font-family: var(--font-sans);
      font-size: 0.8125rem;
      color: var(--ink);
      background: var(--paper);
      border: 0.0625rem solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 0.4375rem 0.625rem;
      outline: none;
      width: auto;
    }

    .btn-ghost {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      background: none;
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-md);
      padding: 0.4375rem 0.75rem;
      cursor: pointer;
      transition: color 0.12s ease, border-color 0.12s ease;
    }

    .btn-ghost:hover:not(:disabled) { color: var(--ink); border-color: var(--border-strong); }
    .btn-ghost:disabled { opacity: 0.4; cursor: not-allowed; }

    .privacy-notice {
      display: flex;
      align-items: center;
      gap: 0.375rem;
      font-size: 0.75rem;
      color: var(--muted);
      background: var(--paper-secondary);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      margin-bottom: var(--spacing-md);
    }

    .data-table-wrap {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      overflow: hidden;
    }

    .data-table { width: 100%; border-collapse: collapse; }

    .data-table th {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      padding: var(--spacing-sm) var(--spacing-md);
      text-align: left;
      border-bottom: 0.0625rem solid var(--border);
      background: var(--paper-secondary);
      white-space: nowrap;
    }

    .data-table td {
      font-size: 0.8125rem;
      color: var(--ink);
      padding: var(--spacing-sm) var(--spacing-md);
      border-bottom: 0.0625rem solid var(--border);
      vertical-align: middle;
      height: 2.75rem;
    }

    .data-table tr:last-child td { border-bottom: none; }
    .data-table tr:hover td { background: var(--paper-secondary); }

    .cell-muted { color: var(--muted); }
    .cell-action { font-weight: 500; }

    .mono-sm {
      font-family: var(--font-mono);
      font-size: 0.6875rem;
      color: var(--muted);
    }

    .category-chip {
      font-family: var(--font-mono);
      font-size: 0.6875rem;
      color: var(--muted);
      background: var(--paper-secondary);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 0.0625rem 0.375rem;
    }

    .result-badge {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      border-radius: var(--rounded-sm);
      padding: 0.125rem 0.375rem;
      border: 0.0625rem solid;
    }

    .result-success { color: var(--verdict-valid); background: var(--verdict-valid-bg); border-color: var(--verdict-valid-border); }
    .result-failure { color: var(--verdict-invalid); background: var(--verdict-invalid-bg); border-color: var(--verdict-invalid-border); }
    .result-denied  { color: var(--verdict-warning); background: var(--verdict-warning-bg); border-color: var(--verdict-warning-border); }

    .table-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: var(--spacing-sm) var(--spacing-md);
      border-top: 0.0625rem solid var(--border);
      background: var(--paper-secondary);
    }

    .count-label { font-size: 0.75rem; color: var(--muted); }

    .pagination {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
    }

    .page-info { font-size: 0.75rem; color: var(--muted); }

    .skeleton-list { display: flex; flex-direction: column; gap: var(--spacing-sm); }

    .skeleton {
      border-radius: var(--rounded-md);
      background: linear-gradient(90deg, var(--paper-secondary) 25%, #e5e2db 50%, var(--paper-secondary) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.6s linear infinite;
    }

    .skeleton-row { height: 2.75rem; }

    @keyframes shimmer {
      0%   { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .empty-state {
      padding: var(--spacing-xl) var(--spacing-lg);
      text-align: center;
      font-size: 0.8125rem;
      color: var(--muted);
    }

    @media (max-width: 48rem) {
      .page-title { font-size: 1.75rem; }

      .filters-bar {
        flex-wrap: wrap;
        gap: var(--spacing-sm);
      }

      .data-table-wrap { overflow-x: auto; }

      .table-footer {
        flex-direction: column;
        align-items: flex-start;
        gap: var(--spacing-sm);
      }
    }
  `],
})
export class LogsComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly ts = inject(TranslationService);

  readonly pageSize = 25;

  allLogs = signal<AuditLog[]>([]);
  filtered = signal<AuditLog[]>([]);
  loading = signal(true);
  notAvailable = signal(false);
  page = signal(0);

  filterCategory = '';
  filterResult = '';

  ngOnInit(): void {
    this.http.get<AuditLogsResponse>('/api/v1/audit/logs?limit=500')
      .pipe(catchError(() => of(null)))
      .subscribe(data => {
        if (data === null) {
          this.notAvailable.set(true);
        } else {
          this.allLogs.set(data.logs);
          this.filtered.set(data.logs);
        }
        this.loading.set(false);
      });
  }

  applyFilters(): void {
    this.page.set(0);
    this.filtered.set(
      this.allLogs().filter(log => {
        const matchCat = !this.filterCategory || log.category === this.filterCategory;
        const matchResult = !this.filterResult || log.result === this.filterResult;
        return matchCat && matchResult;
      })
    );
  }

  resetFilters(): void {
    this.filterCategory = '';
    this.filterResult = '';
    this.applyFilters();
  }

  paginated(): AuditLog[] {
    const start = this.page() * this.pageSize;
    return this.filtered().slice(start, start + this.pageSize);
  }

  totalPages(): number {
    return Math.ceil(this.filtered().length / this.pageSize);
  }

  prevPage(): void { this.page.update(p => Math.max(0, p - 1)); }
  nextPage(): void { this.page.update(p => Math.min(this.totalPages() - 1, p + 1)); }

  maskId(id: string): string {
    if (!id || id.length < 8) return '••••••••';
    if (id.startsWith('sha256:')) return id.slice(0, 16) + '…';
    return id.slice(0, 4) + '••••' + id.slice(-4);
  }

  maskIp(ip: string): string {
    if (ip.startsWith('sha256:')) return ip.slice(0, 14) + '…';
    const parts = ip.split('.');
    if (parts.length === 4) return `${parts[0]}.${parts[1]}.•••.•••`;
    return ip.slice(0, 4) + '•••';
  }

  resultLabel(result: string): string {
    const map: Record<string, string> = {
      success: this.ts.translateInstant('logs.result_success'),
      failure: this.ts.translateInstant('logs.result_failure'),
      denied: this.ts.translateInstant('logs.result_denied'),
    };
    return map[result] ?? result;
  }
}
