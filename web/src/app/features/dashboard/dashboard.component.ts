import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { RouterModule } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { catchError, of } from 'rxjs';

interface KpiData {
  valid_rate: number;
  total_releases: number;
  avg_verification_minutes: number;
  top_failed_rule?: string;
}

interface RecentRelease {
  id: string;
  name: string;
  verdict: string;
  organization_name?: string;
  created_at: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="dashboard-page">
      <div class="page-header">
        <h1 class="page-title">Dashboard</h1>
        <span *ngIf="isAdmin" class="global-badge">Vista global</span>
      </div>

      <!-- KPI Cards -->
      <div class="kpi-grid">
        <div class="kpi-card" *ngIf="kpiLoading()">
          <div class="skeleton skeleton-label"></div>
          <div class="skeleton skeleton-value"></div>
        </div>
        <div class="kpi-card" *ngIf="kpiLoading()">
          <div class="skeleton skeleton-label"></div>
          <div class="skeleton skeleton-value"></div>
        </div>
        <div class="kpi-card" *ngIf="kpiLoading()">
          <div class="skeleton skeleton-label"></div>
          <div class="skeleton skeleton-value"></div>
        </div>
        <div class="kpi-card" *ngIf="kpiLoading()">
          <div class="skeleton skeleton-label"></div>
          <div class="skeleton skeleton-value"></div>
        </div>

        <ng-container *ngIf="!kpiLoading() && kpi()">
          <div class="kpi-card">
            <div class="kpi-label">Tasa de entregas válidas</div>
            <div class="kpi-value" [class.kpi-value-good]="kpi()!.valid_rate >= 80" [class.kpi-value-warn]="kpi()!.valid_rate < 80 && kpi()!.valid_rate >= 50" [class.kpi-value-bad]="kpi()!.valid_rate < 50">
              {{ kpi()!.valid_rate | number:'1.0-1' }}%
            </div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Total de entregas</div>
            <div class="kpi-value">{{ kpi()!.total_releases | number }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Tiempo medio de verificación</div>
            <div class="kpi-value">{{ kpi()!.avg_verification_minutes | number:'1.0-1' }} min</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">Regla más fallida</div>
            <div class="kpi-value kpi-value-mono">{{ kpi()!.top_failed_rule ?? '—' }}</div>
          </div>
        </ng-container>

        <ng-container *ngIf="!kpiLoading() && kpiError()">
          <div class="kpi-error">{{ kpiError() }}</div>
        </ng-container>
      </div>

      <!-- Recent Releases -->
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">Entregas recientes</h2>
        </div>

        <div *ngIf="releasesLoading()" class="skeleton-list">
          <div class="skeleton skeleton-row" *ngFor="let i of [1,2,3,4,5]"></div>
        </div>

        <div *ngIf="!releasesLoading() && releasesError()" class="error-msg">{{ releasesError() }}</div>

        <table class="data-table" *ngIf="!releasesLoading() && !releasesError() && recentReleases().length > 0">
          <thead>
            <tr>
              <th>ID / Nombre</th>
              <th *ngIf="isAdmin">Organización</th>
              <th>Veredicto</th>
              <th>Fecha</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let r of recentReleases()" [routerLink]="['/app/releases', r.id]" class="clickable-row">
              <td>
                <code class="mono-sm">{{ r.id | slice:0:8 }}</code>
                <span class="release-name" *ngIf="r.name"> &mdash; {{ r.name }}</span>
              </td>
              <td *ngIf="isAdmin" class="cell-muted">{{ r.organization_name ?? '—' }}</td>
              <td>
                <span class="verdict-badge" [ngClass]="verdictClass(r.verdict)">
                  {{ r.verdict }}
                </span>
              </td>
              <td class="cell-muted">{{ r.created_at | date:'dd MMM yyyy, HH:mm' }}</td>
            </tr>
          </tbody>
        </table>

        <div *ngIf="!releasesLoading() && !releasesError() && recentReleases().length === 0" class="empty-state">
          No hay entregas registradas.
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }

    .dashboard-page { padding: 0; }

    .page-header {
      display: flex;
      align-items: baseline;
      gap: var(--spacing-md);
      margin-bottom: var(--spacing-lg);
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

    .global-badge {
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

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: var(--spacing-md);
      margin-bottom: var(--spacing-lg);
    }

    .kpi-card {
      background: var(--surface-raised);
      border: 1px solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
    }

    .kpi-label {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: var(--spacing-sm);
    }

    .kpi-value {
      font-family: var(--font-display);
      font-size: 2rem;
      font-weight: 400;
      line-height: 1.1;
      letter-spacing: -0.02em;
      color: var(--ink);
    }

    .kpi-value-mono {
      font-family: var(--font-mono);
      font-size: 1.125rem;
    }

    .kpi-value-good { color: var(--verdict-valid); }
    .kpi-value-warn { color: var(--verdict-warning); }
    .kpi-value-bad  { color: var(--verdict-invalid); }

    .kpi-error {
      grid-column: 1 / -1;
      font-size: 0.8125rem;
      color: var(--verdict-invalid);
    }

    .card {
      background: var(--surface-raised);
      border: 1px solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
    }

    .card-header {
      margin-bottom: var(--spacing-md);
    }

    .card-title {
      font-family: var(--font-display);
      font-size: 1.5rem;
      font-weight: 400;
      line-height: 1.2;
      letter-spacing: -0.01em;
      margin: 0;
      color: var(--ink);
    }

    .data-table {
      width: 100%;
      border-collapse: collapse;
    }

    .data-table th {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      padding: var(--spacing-sm) var(--spacing-md) var(--spacing-sm) 0;
      text-align: left;
      border-bottom: 1px solid var(--border);
    }

    .data-table td {
      font-size: 0.8125rem;
      color: var(--ink);
      padding: var(--spacing-sm) var(--spacing-md) var(--spacing-sm) 0;
      border-bottom: 1px solid var(--border);
      vertical-align: middle;
      height: 44px;
    }

    .data-table tr:last-child td { border-bottom: none; }

    .clickable-row { cursor: pointer; }
    .clickable-row:hover td { background: var(--paper-secondary); }

    .cell-muted { color: var(--muted); }

    .mono-sm {
      font-family: var(--font-mono);
      font-size: 0.6875rem;
      color: var(--muted);
    }

    .release-name {
      font-size: 0.8125rem;
    }

    .verdict-badge {
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

    .verdict-valid {
      color: var(--verdict-valid);
      background: var(--verdict-valid-bg);
      border-color: var(--verdict-valid-border);
    }

    .verdict-warning {
      color: var(--verdict-warning);
      background: var(--verdict-warning-bg);
      border-color: var(--verdict-warning-border);
    }

    .verdict-invalid {
      color: var(--verdict-invalid);
      background: var(--verdict-invalid-bg);
      border-color: var(--verdict-invalid-border);
    }

    .verdict-unevaluated {
      color: var(--verdict-unevaluated);
      background: var(--verdict-unevaluated-bg);
      border-color: var(--verdict-unevaluated-border);
    }

    .skeleton-list { display: flex; flex-direction: column; gap: var(--spacing-sm); }

    .skeleton {
      border-radius: var(--rounded-md);
      background: linear-gradient(90deg, var(--paper-secondary) 25%, #e5e2db 50%, var(--paper-secondary) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.6s linear infinite;
    }

    .skeleton-row { height: 44px; }
    .skeleton-label { height: 12px; width: 60%; margin-bottom: var(--spacing-sm); }
    .skeleton-value { height: 32px; width: 40%; }

    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .error-msg {
      font-size: 0.8125rem;
      color: var(--verdict-invalid);
      padding: var(--spacing-md) 0;
    }

    .empty-state {
      padding: var(--spacing-xl) 0;
      text-align: center;
      font-size: 0.8125rem;
      color: var(--muted);
    }
  `],
})
export class DashboardComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);

  readonly isAdmin = this.authService.isAdmin();

  kpi = signal<KpiData | null>(null);
  kpiLoading = signal(true);
  kpiError = signal<string | null>(null);

  recentReleases = signal<RecentRelease[]>([]);
  releasesLoading = signal(true);
  releasesError = signal<string | null>(null);

  ngOnInit(): void {
    this.loadKpi();
    this.loadRecentReleases();
  }

  private loadKpi(): void {
    const url = '/api/v1/stats/kpi';
    this.http.get<KpiData>(url)
      .pipe(catchError(() => { this.kpiError.set('Error al cargar métricas'); return of(null); }))
      .subscribe(data => { this.kpi.set(data); this.kpiLoading.set(false); });
  }

  private loadRecentReleases(): void {
    const params = '?limit=10';
    this.http.get<RecentRelease[]>(`/api/v1/releases${params}`)
      .pipe(catchError(() => { this.releasesError.set('Error al cargar entregas'); return of([]); }))
      .subscribe(data => { this.recentReleases.set(data); this.releasesLoading.set(false); });
  }

  verdictClass(verdict: string): Record<string, boolean> {
    return {
      'verdict-valid': verdict === 'VALID',
      'verdict-warning': verdict === 'WITH_WARNINGS',
      'verdict-invalid': verdict === 'INVALID',
      'verdict-unevaluated': verdict === 'NOT_EVALUATED' || !verdict,
    };
  }
}
