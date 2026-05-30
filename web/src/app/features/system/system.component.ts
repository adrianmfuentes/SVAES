import { Component, inject, OnInit, OnDestroy, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { RouterModule } from '@angular/router';
import { catchError, forkJoin, map, of, interval, Subscription, Observable } from 'rxjs';

interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

interface Org {
  id: string;
  name: string;
  slug: string;
  plan?: string;
}

interface AdminUser {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
}

type ServiceStatus = 'up' | 'down' | 'unknown';

interface ServiceCard {
  name: string;
  status: ServiceStatus;
  detail?: string;
}

@Component({
  selector: 'app-system',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="system-page">
      <div class="page-header">
        <div class="page-header-left">
          <h1 class="page-title">Visi&oacute;n general</h1>
          <span class="system-badge">Sistema</span>
        </div>
        <div class="refresh-controls">
          <span class="refresh-label" *ngIf="!loading()">Actualizado hace {{ secondsSince() }}s</span>
          <button class="btn-refresh" (click)="loadAll()" [disabled]="loading()">
            <svg width="11" height="11" viewBox="0 0 12 12" fill="none" [class.spinning]="loading()">
              <path d="M10.5 6A4.5 4.5 0 1 1 6 1.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
              <path d="M6.5 1L9 3.5 6.5 6" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            {{ loading() ? 'Cargando…' : 'Actualizar' }}
          </button>
        </div>
      </div>

      <!-- Service status -->
      <div class="section-label">Estado de servicios</div>
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
            <div class="skeleton sk-md" style="margin-top:10px"></div>
          </div>
        </div>
      </ng-template>

      <!-- Metrics -->
      <div class="section-label" style="margin-top:var(--spacing-lg)">M&eacute;tricas del sistema</div>
      <div class="metrics-grid" *ngIf="!loading(); else metricsSkeleton">
        <div class="metric-card">
          <div class="metric-label">Organizaciones</div>
          <div class="metric-value">{{ orgs().length }}</div>
          <div class="metric-sub">activas en el sistema</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Usuarios totales</div>
          <div class="metric-value">{{ users().length }}</div>
          <div class="metric-sub">{{ activeUserCount() }} activos</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">Usuarios inactivos</div>
          <div class="metric-value">{{ users().length - activeUserCount() }}</div>
          <div class="metric-sub">cuentas desactivadas</div>
        </div>
        <div class="metric-card" *ngIf="apiVersion()">
          <div class="metric-label">Versi&oacute;n API</div>
          <div class="metric-value metric-mono">{{ apiVersion() }}</div>
          <div class="metric-sub">en producci&oacute;n</div>
        </div>
      </div>
      <ng-template #metricsSkeleton>
        <div class="metrics-grid">
          <div class="metric-card" *ngFor="let i of [1,2,3,4]">
            <div class="skeleton sk-sm"></div>
            <div class="skeleton sk-lg" style="margin-top:10px"></div>
          </div>
        </div>
      </ng-template>

      <!-- Organizations overview -->
      <div class="section-label" style="margin-top:var(--spacing-lg)">Organizaciones registradas</div>
      <div *ngIf="loading()" class="skeleton-list">
        <div class="skeleton sk-row" *ngFor="let i of [1,2,3]"></div>
      </div>
      <div *ngIf="!loading()" class="data-table-wrap">
        <table class="data-table" *ngIf="orgs().length > 0; else orgsEmpty">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Identificador</th>
              <th>Plan</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let org of orgs()">
              <td class="cell-primary">{{ org.name }}</td>
              <td><code class="mono-sm">{{ org.slug }}</code></td>
              <td class="cell-muted">{{ org.plan ?? 'default' }}</td>
            </tr>
          </tbody>
        </table>
        <ng-template #orgsEmpty>
          <div class="empty-state">No hay organizaciones en el sistema.</div>
        </ng-template>
      </div>

      <!-- Users overview (anonymized) -->
      <div class="section-label" style="margin-top:var(--spacing-lg)">
        Usuarios del sistema
        <span class="anon-note">— identificadores enmascarados</span>
      </div>
      <div *ngIf="loading()" class="skeleton-list">
        <div class="skeleton sk-row" *ngFor="let i of [1,2,3,4]"></div>
      </div>
      <div *ngIf="!loading()" class="data-table-wrap">
        <table class="data-table" *ngIf="users().length > 0; else usersEmpty">
          <thead>
            <tr>
              <th>ID (parcial)</th>
              <th>Rol</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let u of users()">
              <td><code class="mono-sm">{{ maskId(u.id) }}</code></td>
              <td class="cell-muted">{{ u.role }}</td>
              <td>
                <span class="status-badge" [class.badge-active]="u.is_active" [class.badge-inactive]="!u.is_active">
                  {{ u.is_active ? 'Activo' : 'Inactivo' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
        <ng-template #usersEmpty>
          <div class="empty-state">No hay usuarios en el sistema.</div>
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
      border: 1px solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 2px 8px;
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
      gap: 5px;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      background: none;
      border: 1px solid var(--border);
      border-radius: var(--rounded-md);
      padding: 5px 10px;
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
      border: 1px solid var(--border);
      border-left-width: 3px;
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
      gap: 7px;
    }

    .service-dot {
      display: inline-block;
      width: 7px;
      height: 7px;
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
      margin-top: 4px;
    }

    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: var(--spacing-md);
    }

    .metric-card {
      background: var(--surface-raised);
      border: 1px solid var(--border);
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
      margin-top: 4px;
    }

    .data-table-wrap {
      background: var(--surface-raised);
      border: 1px solid var(--border);
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
      border-bottom: 1px solid var(--border);
      background: var(--paper-secondary);
    }

    .data-table td {
      font-size: 0.8125rem;
      color: var(--ink);
      padding: var(--spacing-sm) var(--spacing-md);
      border-bottom: 1px solid var(--border);
      vertical-align: middle;
      height: 44px;
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
      padding: 2px 8px;
      border: 1px solid;
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

    .sk-sm { height: 10px; width: 45%; }
    .sk-md { height: 20px; width: 60%; }
    .sk-lg { height: 28px; width: 50%; }
    .sk-row { height: 44px; }

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
  `],
})
export class SystemComponent implements OnInit, OnDestroy {
  private readonly http = inject(HttpClient);

  loading = signal(true);
  apiVersion = signal<string | null>(null);
  services = signal<ServiceCard[]>([]);
  orgs = signal<Org[]>([]);
  users = signal<AdminUser[]>([]);

  activeUserCount = computed(() => this.users().filter(u => u.is_active).length);

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
               catchError(() => of({ data: null as T | null, ok: false as const })));

    forkJoin({
      health:    probe(this.http.get<HealthResponse>('/health')),
      orgs:      probe(this.http.get<Org[]>('/api/v1/organizations')),
      users:     probe(this.http.get<AdminUser[]>('/api/v1/admin/users?limit=200')),
      connTypes: probe(this.http.get<unknown[]>('/api/v1/connectors/types')),
    }).subscribe(({ health, orgs, users, connTypes }) => {
      // /health is at root and may not be proxied — data calls are primary signals
      const dataOk  = orgs.ok || users.ok;
      const apiUp   = health.ok || dataOk;
      const dbUp    = dataOk;
      const engUp   = connTypes.ok;

      this.apiVersion.set(health.data?.version ?? null);

      this.services.set([
        {
          name: 'API REST',
          status: apiUp ? 'up' : 'down',
          detail: health.ok
            ? `${(health.data as HealthResponse).service} v${(health.data as HealthResponse).version}`
            : (dataOk ? 'Respondiendo' : 'Sin respuesta'),
        },
        {
          name: 'Base de datos',
          status: dbUp ? 'up' : (apiUp ? 'unknown' : 'down'),
          detail: dbUp ? 'Accesible' : (apiUp ? 'Sin datos' : 'Inaccesible'),
        },
        {
          name: 'Motor de verificación',
          status: engUp ? 'up' : (apiUp ? 'unknown' : 'down'),
          detail: engUp
            ? (Array.isArray(connTypes.data) ? `${connTypes.data.length} tipos cargados` : 'Respondiendo')
            : (apiUp ? 'Sin datos' : 'Inaccesible'),
        },
        {
          name: 'Cola / Redis',
          status: apiUp ? 'up' : 'unknown',
          detail: apiUp ? 'Inferido de API' : 'No verificable',
        },
      ]);

      this.orgs.set((orgs.data as Org[] | null) ?? []);
      this.users.set((users.data as AdminUser[] | null) ?? []);
      this.loading.set(false);
    });
  }

  statusLabel(status: ServiceStatus): string {
    const map: Record<ServiceStatus, string> = {
      up: 'Operativo',
      down: 'Caído',
      unknown: 'Desconocido',
    };
    return map[status] ?? status;
  }

  maskId(id: string): string {
    if (!id || id.length < 8) return '••••••••';
    return id.slice(0, 6) + '••••' + id.slice(-4);
  }
}
