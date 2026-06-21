import { Component, inject, OnInit, OnDestroy, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { RouterModule } from '@angular/router';
import { catchError, forkJoin, map, of, interval, Subscription, Observable } from 'rxjs';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';

interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

interface Org {
  id: string;
  name: string;
  slug: string;
}

interface AdminUser {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
}

type ServiceStatus = 'up' | 'down' | 'unknown';

interface RulesReloadResult {
  success: boolean;
  rules_loaded: number;
  message: string;
}

interface ServiceCard {
  name: string;
  status: ServiceStatus;
  detail?: string;
}

interface ProbeResult<T> {
  data: T | null;
  ok: boolean;
}

@Component({
  selector: 'app-system',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslatePipe],
  template: `
    <div class="system-page">
      <div class="page-header">
        <div class="page-header-left">
          <h1 class="page-title">{{ 'system.title' | t }}</h1>
          <span class="system-badge">{{ 'system.system_badge' | t }}</span>
        </div>
        <div class="refresh-controls">
          <span class="refresh-label" *ngIf="!loading()">{{ 'system.updated_ago' | t : { n: secondsSince() } }}</span>
          <button class="btn-refresh" (click)="loadAll()" [disabled]="loading()" [title]="loading() ? ('common.disabled_tooltip.operation_in_progress' | t) : ''">
            <svg width="11" height="11" viewBox="0 0 12 12" fill="none" [class.spinning]="loading()">
              <path d="M10.5 6A4.5 4.5 0 1 1 6 1.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
              <path d="M6.5 1L9 3.5 6.5 6" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            {{ loading() ? ('common.loading' | t) : ('system.refresh_btn' | t) }}
          </button>
        </div>
      </div>

      <!-- Service status -->
      <div class="section-label">{{ 'system.service_status_section' | t }}</div>
      <div class="service-grid" *ngIf="!loading(); else servicesSkeleton">
        <div
          *ngFor="let svc of services()"
          class="service-card"
          [class.service-up]="svc.status === 'up'"
          [class.service-down]="svc.status === 'down'"
          [class.service-unknown]="svc.status === 'unknown'"
        >
          <div class="service-name">{{ svc.name }}</div>
          <div class="service-status-row">
            <span class="service-dot"></span>
            <span class="service-status-label">{{ statusLabel(svc.status) }}</span>
          </div>
          <div class="service-detail" *ngIf="svc.detail">{{ svc.detail }}</div>
        </div>
      </div>
      <ng-template #servicesSkeleton>
        <div class="service-grid">
          <div class="service-card skeleton-card" *ngFor="let i of [1,2,3,4]">
            <div class="skeleton sk-sm"></div>
            <div class="skeleton sk-md" style="margin-top:0.625rem"></div>
          </div>
        </div>
      </ng-template>

      <!-- Metrics -->
      <div class="section-label" style="margin-top:var(--spacing-lg)">{{ 'system.metrics_section' | t }}</div>
      <div class="metrics-grid" *ngIf="!loading(); else metricsSkeleton">
        <div class="metric-card">
          <div class="metric-label">{{ 'system.org_count_label' | t }}</div>
          <div class="metric-value">{{ orgs().length }}</div>
          <div class="metric-sub">{{ 'system.active_in_system' | t }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">{{ 'system.total_users_label' | t }}</div>
          <div class="metric-value">{{ users().length }}</div>
          <div class="metric-sub">{{ 'system.active_count' | t : { n: activeUserCount() } }}</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">{{ 'system.inactive_users_label' | t }}</div>
          <div class="metric-value">{{ users().length - activeUserCount() }}</div>
          <div class="metric-sub">{{ 'system.deactivated_label' | t }}</div>
        </div>
        <div class="metric-card" *ngIf="apiVersion()">
          <div class="metric-label">{{ 'system.api_version_label' | t }}</div>
          <div class="metric-value metric-mono">{{ apiVersion() }}</div>
          <div class="metric-sub">{{ 'system.in_production' | t }}</div>
        </div>
      </div>
      <ng-template #metricsSkeleton>
        <div class="metrics-grid">
          <div class="metric-card" *ngFor="let i of [1,2,3,4]">
            <div class="skeleton sk-sm"></div>
            <div class="skeleton sk-lg" style="margin-top:0.625rem"></div>
          </div>
        </div>
      </ng-template>

      <!-- Rules reload action -->
      <div class="section-label" style="margin-top:var(--spacing-lg)">{{ 'system.actions_section' | t }}</div>
      <div class="action-card">
        <div class="action-info">
          <div class="action-title">{{ 'system.rules_reload_title' | t }}</div>
          <p class="action-desc">{{ 'system.rules_reload_desc' | t }}</p>
          <div *ngIf="reloadResult()" class="reload-result" [class.reload-ok]="reloadResult()!.success" [class.reload-fail]="!reloadResult()!.success">
            <span class="result-icon">{{ reloadResult()!.success ? '✓' : '✕' }}</span>
            <span>{{ reloadResult()!.message }}</span>
            <span class="result-count" *ngIf="reloadResult()!.success">&nbsp;&mdash;&nbsp;{{ 'system.rules_loaded_count' | t : { n: reloadResult()!.rules_loaded } }}</span>
          </div>
          <div *ngIf="reloadError()" class="reload-error">{{ reloadError() }}</div>
        </div>
        <div class="action-controls">
          <ng-container *ngIf="!confirmingReload()">
            <button class="btn-secondary" (click)="confirmingReload.set(true)" [disabled]="reloading()" [title]="reloading() ? ('common.disabled_tooltip.operation_in_progress' | t) : ''">
              {{ 'system.reload_btn' | t }}
            </button>
          </ng-container>
          <ng-container *ngIf="confirmingReload()">
            <span class="confirm-label">{{ 'system.confirm_reload_label' | t }}</span>
            <button class="btn-primary" (click)="executeReload()" [disabled]="reloading()" [title]="reloading() ? ('common.disabled_tooltip.operation_in_progress' | t) : ''">
              {{ reloading() ? ('system.reloading_label' | t) : ('system.confirm_btn' | t) }}
            </button>
            <button class="btn-ghost-sm" (click)="confirmingReload.set(false)" [disabled]="reloading()" [title]="reloading() ? ('common.disabled_tooltip.operation_in_progress' | t) : ''">
              {{ 'system.cancel_btn' | t }}
            </button>
          </ng-container>
        </div>
      </div>

      <!-- Organizations overview -->
      <div class="section-label" style="margin-top:var(--spacing-lg)">{{ 'system.registered_orgs' | t }}</div>
      <div *ngIf="loading()" class="skeleton-list">
        <div class="skeleton sk-row" *ngFor="let i of [1,2,3]"></div>
      </div>
      <div *ngIf="!loading()" class="data-table-wrap">
        <table class="data-table" *ngIf="orgs().length > 0; else orgsEmpty">
          <thead>
            <tr>
              <th scope="col">{{ 'system.org_name_col' | t }}</th>
              <th scope="col">{{ 'system.org_id_col' | t }}</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let org of anonymizedOrgs()">
              <td class="cell-primary">{{ org.name }}</td>
              <td><code class="mono-sm">{{ org.slug }}</code></td>
            </tr>
          </tbody>
        </table>
        <ng-template #orgsEmpty>
          <div class="empty-state">{{ 'system.no_system_orgs' | t }}</div>
        </ng-template>
      </div>

      <!-- Users overview (anonymized) -->
      <div class="section-label" style="margin-top:var(--spacing-lg)">
        {{ 'system.system_users_section' | t }}
        <span class="anon-note">{{ 'system.masked_ids_note' | t }}</span>
      </div>
      <div *ngIf="loading()" class="skeleton-list">
        <div class="skeleton sk-row" *ngFor="let i of [1,2,3,4]"></div>
      </div>
      <div *ngIf="!loading()" class="data-table-wrap">
        <table class="data-table" *ngIf="users().length > 0; else usersEmpty">
          <thead>
            <tr>
              <th scope="col">{{ 'system.user_id_partial_col' | t }}</th>
              <th scope="col">{{ 'system.user_role_col' | t }}</th>
              <th scope="col">{{ 'system.user_status_col' | t }}</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let u of users()">
              <td><code class="mono-sm">{{ maskId(u.id) }}</code></td>
              <td class="cell-muted">{{ ts.translateInstant('user_role.' + u.role) }}</td>
              <td>
                <span class="status-badge" [class.badge-active]="u.is_active" [class.badge-inactive]="!u.is_active">
                  {{ u.is_active ? ('system.status_active' | t) : ('system.status_inactive' | t) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
        <ng-template #usersEmpty>
          <div class="empty-state">{{ 'system.no_system_users' | t }}</div>
        </ng-template>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }
    .system-page { padding: 0; }

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

    .system-badge {
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

    .refresh-controls {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
    }

    .refresh-label {
      font-size: 0.75rem;
      color: var(--muted);
    }

    .btn-refresh {
      display: inline-flex;
      align-items: center;
      gap: 0.3125rem;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      background: none;
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-md);
      padding: 0.3125rem 0.625rem;
      cursor: pointer;
      transition: color 0.12s ease, border-color 0.12s ease;
    }

    .btn-refresh:hover:not(:disabled) { color: var(--ink); border-color: var(--border-strong); }
    .btn-refresh:disabled { opacity: 0.4; cursor: not-allowed; }

    @keyframes spin { to { transform: rotate(360deg); } }
    .spinning { animation: spin 0.8s linear infinite; }

    .section-label {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: var(--spacing-sm);
    }

    .anon-note {
      font-weight: 400;
      letter-spacing: 0;
      text-transform: none;
      font-size: 0.75rem;
      color: var(--muted);
      opacity: 0.7;
    }

    .service-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: var(--spacing-md);
    }

    .service-card {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-left-width: 0.1875rem;
      border-radius: var(--rounded-lg);
      padding: var(--spacing-md);
    }

    .service-up       { border-left-color: var(--verdict-valid); }
    .service-down     { border-left-color: var(--verdict-invalid); }
    .service-unknown  { border-left-color: var(--border-strong); }
    .skeleton-card { border-left-color: var(--border) !important; }

    .service-name {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: var(--spacing-xs);
    }

    .service-status-row {
      display: flex;
      align-items: center;
      gap: 0.4375rem;
    }

    .service-dot {
      display: inline-block;
      width: 0.4375rem;
      height: 0.4375rem;
      border-radius: 50%;
    }

    .service-up       .service-dot { background: var(--verdict-valid); }
    .service-down     .service-dot { background: var(--verdict-invalid); }
    .service-unknown  .service-dot { background: var(--border-strong); }

    .service-status-label {
      font-size: 0.9375rem;
      font-weight: 500;
    }

    .service-up       .service-status-label { color: var(--verdict-valid); }
    .service-down     .service-status-label { color: var(--verdict-invalid); }
    .service-unknown  .service-status-label { color: var(--muted); }

    .service-detail {
      font-family: var(--font-mono);
      font-size: 0.6875rem;
      color: var(--muted);
      margin-top: 0.25rem;
    }

    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: var(--spacing-md);
    }

    .metric-card {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
    }

    .metric-label {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: var(--spacing-sm);
    }

    .metric-value {
      font-family: var(--font-display);
      font-size: 2rem;
      font-weight: 400;
      line-height: 1.1;
      letter-spacing: -0.02em;
      color: var(--ink);
    }

    .metric-mono {
      font-family: var(--font-mono);
      font-size: 1rem;
    }

    .metric-sub {
      font-size: 0.75rem;
      color: var(--muted);
      margin-top: 0.25rem;
    }

    .action-card {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: var(--spacing-xl);
      margin-bottom: var(--spacing-md);
    }

    .action-info { flex: 1; }

    .action-title {
      font-family: var(--font-sans);
      font-size: 1rem;
      font-weight: 600;
      color: var(--ink);
      margin-bottom: var(--spacing-xs);
    }

    .action-desc {
      font-size: 0.8125rem;
      color: var(--muted);
      line-height: 1.6;
      margin: 0 0 var(--spacing-sm);
    }

    .action-controls {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      flex-shrink: 0;
      padding-top: 0.25rem;
    }

    .confirm-label {
      font-size: 0.8125rem;
      color: var(--ink);
      white-space: nowrap;
    }

    .btn-ghost-sm {
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

    .btn-ghost-sm:hover:not(:disabled) { color: var(--ink); border-color: var(--border-strong); }
    .btn-ghost-sm:disabled { opacity: 0.4; cursor: not-allowed; }

    .reload-result {
      display: flex;
      align-items: center;
      gap: 0.375rem;
      font-size: 0.8125rem;
      border-radius: var(--rounded-md);
      padding: var(--spacing-xs) var(--spacing-sm);
      margin-top: var(--spacing-xs);
    }

    .reload-ok {
      color: var(--verdict-valid);
      background: var(--verdict-valid-bg);
      border: 0.0625rem solid var(--verdict-valid-border);
    }

    .reload-fail {
      color: var(--verdict-invalid);
      background: var(--verdict-invalid-bg);
      border: 0.0625rem solid var(--verdict-invalid-border);
    }

    .result-icon { font-weight: 700; }
    .result-count { color: inherit; opacity: 0.8; }

    .reload-error {
      font-size: 0.8125rem;
      color: var(--verdict-invalid);
      margin-top: var(--spacing-xs);
    }

    .data-table-wrap {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      overflow: hidden;
      margin-bottom: var(--spacing-md);
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

    .cell-primary { font-weight: 500; }
    .cell-muted { color: var(--muted); }

    .mono-sm {
      font-family: var(--font-mono);
      font-size: 0.6875rem;
      color: var(--muted);
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      border-radius: var(--rounded-sm);
      padding: 0.125rem 0.5rem;
      border: 0.0625rem solid;
    }

    .badge-active { color: var(--verdict-valid); background: var(--verdict-valid-bg); border-color: var(--verdict-valid-border); }
    .badge-inactive { color: var(--verdict-unevaluated); background: var(--verdict-unevaluated-bg); border-color: var(--verdict-unevaluated-border); }

    .skeleton-list { display: flex; flex-direction: column; gap: var(--spacing-sm); margin-bottom: var(--spacing-md); }

    .skeleton {
      border-radius: var(--rounded-md);
      background: linear-gradient(90deg, var(--paper-secondary) 25%, #e5e2db 50%, var(--paper-secondary) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.6s linear infinite;
    }

    .sk-sm { height: 0.625rem; width: 45%; }
    .sk-md { height: 1.25rem; width: 60%; }
    .sk-lg { height: 1.75rem; width: 50%; }
    .sk-row { height: 2.75rem; }

    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .empty-state {
      padding: var(--spacing-xl) var(--spacing-lg);
      text-align: center;
      font-size: 0.8125rem;
      color: var(--muted);
    }

    @media (max-width: 56.25rem) {
      .service-grid { grid-template-columns: repeat(2, 1fr); }
      .metrics-grid { grid-template-columns: repeat(2, 1fr); }
    }

    @media (max-width: 48rem) {
      .page-title { font-size: 1.75rem; }

      .page-header { flex-wrap: wrap; }

      .action-card {
        flex-direction: column;
        align-items: flex-start;
      }

      .action-controls { flex-wrap: wrap; }

      .data-table-wrap { overflow-x: auto; }
    }

    @media (max-width: 30rem) {
      .service-grid { grid-template-columns: 1fr; }
      .metrics-grid { grid-template-columns: 1fr; }
    }
  `],
})
export class SystemComponent implements OnInit, OnDestroy {
  private readonly http = inject(HttpClient);
  readonly ts = inject(TranslationService);

  loading = signal(true);
  apiVersion = signal<string | null>(null);
  services = signal<ServiceCard[]>([]);
  orgs = signal<Org[]>([]);
  users = signal<AdminUser[]>([]);

  reloading = signal(false);
  confirmingReload = signal(false);
  reloadResult = signal<RulesReloadResult | null>(null);
  reloadError = signal<string | null>(null);

  activeUserCount = computed(() => this.users().filter(u => u.is_active).length);

  anonymizedOrgs = computed(() =>
    this.orgs().map(org => ({
      ...org,
      name: `Organization ${this.simpleHash(org.id)}`,
    }))
  );

  secondsSince = signal(0);
  private lastRefresh = Date.now();
  private timerSub?: Subscription;

  ngOnInit(): void {
    this.loadAll();
    this.timerSub = interval(1000).subscribe(() =>
      this.secondsSince.set(Math.floor((Date.now() - this.lastRefresh) / 1000))
    );
  }

  ngOnDestroy(): void {
    this.timerSub?.unsubscribe();
  }

  loadAll(): void {
    this.loading.set(true);
    this.lastRefresh = Date.now();
    this.secondsSince.set(0);

    const probe = <T>(req: Observable<T>) =>
      req.pipe(map(d => ({ data: d, ok: true as const })),
               catchError(() => of({ data: null, ok: false as const })));

    forkJoin({
      health:    probe(this.http.get<HealthResponse>('/health')),
      orgs:      probe(this.http.get<Org[]>('/api/v1/organizations')),
      users:     probe(this.http.get<AdminUser[]>('/api/v1/admin/users?limit=200')),
      connTypes: probe(this.http.get<unknown[]>('/api/v1/connectors/types')),
    }).subscribe(({ health, orgs, users, connTypes }) => {
      const dataOk = orgs.ok || users.ok;

      this.apiVersion.set(health.data?.version ?? null);
      this.services.set(this.buildServiceCards(health, dataOk, connTypes));
      this.orgs.set(orgs.data ?? []);
      this.users.set(users.data ?? []);
      this.loading.set(false);
    });
  }

  private buildServiceCards(
    health: ProbeResult<HealthResponse>,
    dataOk: boolean,
    connTypes: ProbeResult<unknown[]>,
  ): ServiceCard[] {
    const apiUp = health.ok || dataOk;
    const dbUp = dataOk;
    const engUp = connTypes.ok;

    type Status = 'up' | 'unknown' | 'down';

    let dbStatus: Status;
    if (dbUp) {
      dbStatus = 'up';
    } else if (apiUp) {
      dbStatus = 'unknown';
    } else {
      dbStatus = 'down';
    }
    let engStatus: Status;
    if (engUp) {
      engStatus = 'up';
    } else if (apiUp) {
      engStatus = 'unknown';
    } else {
      engStatus = 'down';
    }
    const apiStatus: Status = apiUp ? 'up' : 'down';
    const redisStatus: Status = apiUp ? 'up' : 'unknown';

    return [
      { name: this.ts.translateInstant('system.service_api'), status: apiStatus, detail: this.apiDetail(health, dataOk) },
      { name: this.ts.translateInstant('system.service_db'), status: dbStatus, detail: this.dbDetail(dbUp, apiUp) },
      { name: this.ts.translateInstant('system.service_engine'), status: engStatus, detail: this.engineDetail(engUp, apiUp, connTypes) },
      { name: this.ts.translateInstant('system.service_redis'), status: redisStatus, detail: apiUp ? this.ts.translateInstant('system.detail_inferred') : this.ts.translateInstant('system.detail_not_verifiable') },
    ];
  }

  private apiDetail(health: ProbeResult<HealthResponse>, dataOk: boolean): string {
    if (health.ok) return `${health.data?.service ?? 'API'} v${health.data?.version ?? '?'}`;
    return dataOk ? this.ts.translateInstant('system.detail_responding') : this.ts.translateInstant('system.detail_no_response');
  }

  private dbDetail(dbUp: boolean, apiUp: boolean): string {
    if (dbUp) return this.ts.translateInstant('system.detail_accessible');
    return apiUp ? this.ts.translateInstant('system.detail_no_data') : this.ts.translateInstant('system.detail_inaccessible');
  }

  private engineDetail(engUp: boolean, apiUp: boolean, connTypes: ProbeResult<unknown[]>): string {
    if (engUp) {
      return Array.isArray(connTypes.data)
        ? this.ts.translateInstant('system.detail_types_loaded', { n: connTypes.data.length })
        : this.ts.translateInstant('system.detail_responding');
    }
    return apiUp ? this.ts.translateInstant('system.detail_no_data') : this.ts.translateInstant('system.detail_inaccessible');
  }

  executeReload(): void {
    this.reloading.set(true);
    this.reloadResult.set(null);
    this.reloadError.set(null);
    this.http.post<RulesReloadResult>('/api/v1/admin/rules/reload', {})
      .pipe(catchError((err: import('@angular/common/http').HttpErrorResponse) => {
        this.reloadError.set(err.error?.detail ?? this.ts.translateInstant('system.reload_error'));
        this.reloading.set(false);
        this.confirmingReload.set(false);
        return of(null);
      }))
      .subscribe(result => {
        if (result) {
          this.reloadResult.set(result);
        }
        this.reloading.set(false);
        this.confirmingReload.set(false);
      });
  }

  statusLabel(status: ServiceStatus): string {
    const map: Record<ServiceStatus, string> = {
      up: this.ts.translateInstant('system.status_healthy'),
      down: this.ts.translateInstant('system.status_unhealthy'),
      unknown: this.ts.translateInstant('system.status_unknown'),
    };
    return map[status] ?? status;
  }

  maskId(id: string): string {
    if (!id || id.length < 8) return '••••••••';
    return id.slice(0, 6) + '••••' + id.slice(-4);
  }

  private simpleHash(input: string): string {
    let hash = 0;
    for (let i = 0; i < input.length; i++) {
      const char = input.codePointAt(i)!;
      hash = ((hash << 5) - hash) + char;
      hash = Math.trunc(hash);
    }
    return Math.abs(hash).toString(16).slice(0, 8).padStart(8, '0');
  }
}
