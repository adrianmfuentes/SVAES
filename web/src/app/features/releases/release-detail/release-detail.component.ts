import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { catchError, forkJoin, of, switchMap } from 'rxjs';

interface ReleaseDetail {
  id: string;
  name: string;
  version: string;
  description: string;
  status: string;
  project_id: string;
  profile_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  project_name?: string;
  organization_name?: string;
}

interface Artifact {
  id: string;
  release_id: string;
  connector_instance_id: string;
  connector_implementation: string;
  artifact_type: string;
  external_ref: string;
  description?: string;
  metadata?: Record<string, unknown>;
  created_at?: string;
}

interface RuleResult {
  rule_id: string;
  rule_name: string;
  connector?: string;
  result: string;
  evidence?: string;
  severity?: string;
  message?: string;
}

interface VerificationResult {
  id: string;
  release_id: string;
  verdict: string;
  rule_results: RuleResult[];
  summary: Record<string, number>;
  profile_snapshot?: Record<string, unknown>;
  duration_ms: number;
  executed_at: string;
}

@Component({
  selector: 'app-release-detail',
  standalone: true,
  imports: [CommonModule, RouterModule],
  template: `
    <div class="detail-page">
      <div class="page-header">
        <div class="page-header-left">
          <a routerLink="/app/releases" class="back-link">&larr; Entregas</a>
          <h1 class="page-title">{{ release()?.name || 'Cargando…' }}</h1>
        </div>
        <div class="page-header-actions">
          <button
            class="btn-accent"
            [disabled]="verifying()"
            (click)="launchVerification()">
            @if (verifying()) { Verificando… } @else { Verificar }
          </button>
          <button class="btn-secondary" (click)="exportPdf()">
            Exportar PDF
          </button>
        </div>
      </div>

      @if (loading()) {
        <div class="skeleton-block">
          <div class="skeleton skeleton-banner"></div>
          <div class="skeleton skeleton-card"></div>
          <div class="skeleton skeleton-row" *ngFor="let i of [1,2,3,4,5]"></div>
        </div>
      }

      @if (error() && !loading()) {
        <div class="error-banner">{{ error() }}</div>
      }

      @if (!loading() && !error() && release()) {
        <!-- Verdict banner -->
        @if (latestVerdict) {
          <div class="verdict-banner" [ngClass]="verdictBannerClass()">
            <span class="verdict-icon">{{ verdictIcon() }}</span>
            <span class="verdict-badge" [ngClass]="verdictBadgeClass()">{{ verdictLabel() }}</span>
            <code class="verdict-release-id">{{ release()!.id | slice:0:8 }}</code>
            <span class="verdict-separator">|</span>
            <span class="verdict-timestamp">{{ latestResult()?.executed_at | date:'dd MMM yyyy, HH:mm:ss' }}</span>
          </div>
        }

        <!-- Release info card -->
        <div class="card info-card">
          <h2 class="card-title">{{ release()!.name }}</h2>
          <div class="info-grid">
            <div class="info-field">
              <span class="info-label">Versi&oacute;n</span>
              <span class="info-value">{{ release()!.version }}</span>
            </div>
            <div class="info-field">
              <span class="info-label">Estado</span>
              <span class="verdict-badge-sm" [ngClass]="statusBadgeClass()">{{ release()!.status }}</span>
            </div>
            <div class="info-field">
              <span class="info-label">Proyecto</span>
              <span class="info-value">{{ release()!.project_name || release()!.project_id | slice:0:8 }}</span>
            </div>
            <div class="info-field">
              <span class="info-label">Organizaci&oacute;n</span>
              <span class="info-value text-muted">{{ release()!.organization_name || '—' }}</span>
            </div>
            <div class="info-field">
              <span class="info-label">Creado</span>
              <span class="info-value text-muted">{{ release()!.created_at | date:'dd MMM yyyy, HH:mm' }}</span>
            </div>
            <div class="info-field">
              <span class="info-label">Actualizado</span>
              <span class="info-value text-muted">{{ release()!.updated_at | date:'dd MMM yyyy, HH:mm' }}</span>
            </div>
          </div>
          @if (release()!.description) {
            <div class="info-description">
              <span class="info-label">Descripci&oacute;n</span>
              <p class="info-description-text">{{ release()!.description }}</p>
            </div>
          }
        </div>

        <!-- Verification rule results table -->
        @if (latestResult(); as result) {
          <div class="card rules-section">
            <h2 class="card-title">Resultados de verificaci&oacute;n</h2>
            <div class="data-table-wrap">
              <table class="data-table rules-table">
                <thead>
                  <tr>
                    <th class="col-id">ID</th>
                    <th class="col-name">Regla</th>
                    <th class="col-connector">Conector</th>
                    <th class="col-result">Resultado</th>
                    <th class="col-evidence">Evidencia</th>
                  </tr>
                </thead>
                <tbody>
                  @for (rule of result.rule_results; track rule.rule_id; let i = $index) {
                    <tr
                      [class.expanded]="expandedRule() === i"
                      (click)="toggleEvidence(i)">
                      <td><code class="mono-sm">{{ rule.rule_id | slice:0:8 }}</code></td>
                      <td class="cell-primary">{{ rule.rule_name }}</td>
                      <td class="cell-muted">{{ rule.connector || '—' }}</td>
                      <td>
                        <span class="verdict-badge" [ngClass]="ruleResultClass(rule.result)">
                          {{ rule.result }}
                        </span>
                      </td>
                      <td class="cell-evidence" (click)="$event.stopPropagation()">
                        @if (rule.evidence) {
                          <span>{{ rule.evidence | slice:0:100 }}{{ rule.evidence.length > 100 ? '…' : '' }}</span>
                          @if (rule.evidence.length > 100) {
                            <button class="btn-expand" (click)="toggleEvidence(i)">Ver m&aacute;s</button>
                          }
                        } @else {
                          <span class="cell-muted">—</span>
                        }
                      </td>
                    </tr>
                    @if (expandedRule() === i && rule.evidence) {
                      <tr class="evidence-row">
                        <td colspan="5">
                          <pre class="evidence-block">{{ rule.evidence }}</pre>
                        </td>
                      </tr>
                    }
                  }
                </tbody>
              </table>
            </div>
            @if (result.summary) {
              <div class="summary-bar">
                <span class="summary-label">Resumen:</span>
                @for (item of summaryItems(result.summary); track item[0]) {
                  <span class="summary-chip" [ngClass]="ruleResultClass(item[0])">
                    {{ item[1] }} {{ item[0] }}
                  </span>
                }
                <span class="summary-duration text-muted">{{ result.duration_ms }}ms</span>
              </div>
            }
          </div>
        }

        <!-- Artifacts section -->
        @if (artifacts().length > 0) {
          <div class="card artifacts-section">
            <h2 class="card-title">Artefactos ({{ artifacts().length }})</h2>
            <div class="data-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Tipo</th>
                    <th>Conector</th>
                    <th>Ref. externa</th>
                    <th>Descripci&oacute;n</th>
                  </tr>
                </thead>
                <tbody>
                  @for (a of artifacts(); track a.id) {
                    <tr>
                      <td>
                        <span class="artifact-type-badge">{{ a.artifact_type }}</span>
                      </td>
                      <td class="cell-muted">{{ a.connector_implementation }}</td>
                      <td><code class="mono-sm">{{ a.external_ref }}</code></td>
                      <td class="cell-muted">{{ a.description || '—' }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
        }

        <!-- Verification history -->
        @if (verificationHistory().length > 1) {
          <div class="card history-section">
            <h2 class="card-title">Historial de verificaciones</h2>
            <div class="data-table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Veredicto</th>
                    <th>Duraci&oacute;n</th>
                    <th>Ejecutada</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  @for (h of verificationHistory(); track h.id) {
                    <tr>
                      <td>
                        <span class="verdict-badge" [ngClass]="verdictBadgeMap(h.verdict)">
                          {{ verdictLabelMap(h.verdict) }}
                        </span>
                      </td>
                      <td class="cell-muted">{{ h.duration_ms }}ms</td>
                      <td class="cell-muted">{{ h.executed_at | date:'dd MMM yyyy, HH:mm' }}</td>
                      <td class="cell-action">
                        <button class="btn-ghost" (click)="loadResultDetail(h.id)">Ver</button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>
        }

        @if (!latestResult() && artifacts().length === 0) {
          <div class="card empty-card">
            <p class="empty-text">Esta entrega a&uacute;n no tiene artefactos ni verificaciones.</p>
            <button class="btn-accent" [disabled]="verifying()" (click)="launchVerification()">
              @if (verifying()) { Verificando… } @else { Iniciar verificaci&oacute;n }
            </button>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    :host { display: block; }

    .detail-page { padding: 0; }

    .page-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      margin-bottom: var(--spacing-lg);
      flex-wrap: wrap;
      gap: var(--spacing-md);
    }

    .page-header-left {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-xs);
    }

    .back-link {
      font-family: var(--font-sans);
      font-size: 0.8125rem;
      color: var(--muted);
      text-decoration: none;
      transition: color 0.12s ease;
    }

    .back-link:hover { color: var(--ink); }

    .page-title {
      font-family: var(--font-display);
      font-size: 2.25rem;
      font-weight: 400;
      line-height: 1.1;
      letter-spacing: -0.02em;
      margin: 0;
      color: var(--ink);
    }

    .page-header-actions {
      display: flex;
      gap: var(--spacing-sm);
    }

    /* Verdict banner */
    .verdict-banner {
      height: 56px;
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 0 24px;
      border-radius: var(--rounded-md);
      margin-bottom: var(--spacing-lg);
      border: 1px solid;
    }

    .verdict-banner-valid {
      background: var(--verdict-valid-bg);
      border-color: var(--verdict-valid-border);
      border-left: 4px solid var(--verdict-valid);
    }

    .verdict-banner-warning {
      background: var(--verdict-warning-bg);
      border-color: var(--verdict-warning-border);
      border-left: 4px solid var(--verdict-warning);
    }

    .verdict-banner-invalid {
      background: var(--verdict-invalid-bg);
      border-color: var(--verdict-invalid-border);
      border-left: 4px solid var(--verdict-invalid);
    }

    .verdict-banner-unevaluated {
      background: var(--verdict-unevaluated-bg);
      border-color: var(--verdict-unevaluated-border);
      border-left: 4px solid var(--verdict-unevaluated);
    }

    .verdict-icon {
      font-size: 16px;
      width: 16px;
      text-align: center;
      flex-shrink: 0;
    }

    .verdict-valid-icon { color: var(--verdict-valid); }
    .verdict-warning-icon { color: var(--verdict-warning); }
    .verdict-invalid-icon { color: var(--verdict-invalid); }
    .verdict-unevaluated-icon { color: var(--verdict-unevaluated); }

    .verdict-banner .verdict-badge {
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

    .verdict-badge-valid { color: var(--verdict-valid); background: var(--verdict-valid-bg); border-color: var(--verdict-valid-border); }
    .verdict-badge-warning { color: var(--verdict-warning); background: var(--verdict-warning-bg); border-color: var(--verdict-warning-border); }
    .verdict-badge-invalid { color: var(--verdict-invalid); background: var(--verdict-invalid-bg); border-color: var(--verdict-invalid-border); }
    .verdict-badge-unevaluated { color: var(--verdict-unevaluated); background: var(--verdict-unevaluated-bg); border-color: var(--verdict-unevaluated-border); }

    .verdict-release-id {
      font-family: var(--font-mono);
      font-size: 0.8125rem;
      color: var(--ink);
    }

    .verdict-separator {
      color: var(--border-strong);
    }

    .verdict-timestamp {
      font-size: 0.8125rem;
      color: var(--muted);
    }

    /* Card */
    .card {
      background: var(--surface-raised);
      border: 1px solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
      margin-bottom: var(--spacing-lg);
    }

    .card-title {
      font-family: var(--font-display);
      font-size: 1.5rem;
      font-weight: 400;
      line-height: 1.2;
      letter-spacing: -0.01em;
      margin: 0 0 var(--spacing-md);
      color: var(--ink);
    }

    /* Info grid */
    .info-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: var(--spacing-md);
    }

    .info-field {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    .info-label {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .info-value {
      font-size: 0.9375rem;
      color: var(--ink);
    }

    .info-description {
      margin-top: var(--spacing-md);
      padding-top: var(--spacing-md);
      border-top: 1px solid var(--border);
    }

    .info-description-text {
      font-size: 0.9375rem;
      line-height: 1.65;
      color: var(--ink);
      margin: var(--spacing-xs) 0 0;
    }

    .verdict-badge-sm {
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
      align-self: flex-start;
    }

    .status-borrador { color: var(--verdict-unevaluated); background: var(--verdict-unevaluated-bg); border-color: var(--verdict-unevaluated-border); }
    .status-pendiente { color: var(--verdict-unevaluated); background: var(--verdict-unevaluated-bg); border-color: var(--verdict-unevaluated-border); }
    .status-en_verificacion { color: var(--verdict-warning); background: var(--verdict-warning-bg); border-color: var(--verdict-warning-border); }
    .status-valida { color: var(--verdict-valid); background: var(--verdict-valid-bg); border-color: var(--verdict-valid-border); }
    .status-con_advertencias { color: var(--verdict-warning); background: var(--verdict-warning-bg); border-color: var(--verdict-warning-border); }
    .status-no_valida { color: var(--verdict-invalid); background: var(--verdict-invalid-bg); border-color: var(--verdict-invalid-border); }
    .status-archivada { color: var(--verdict-unevaluated); background: var(--verdict-unevaluated-bg); border-color: var(--verdict-unevaluated-border); }

    /* Verification rule table */
    .data-table-wrap {
      border: 1px solid var(--border);
      border-radius: var(--rounded-md);
      overflow: hidden;
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

    .data-table tbody tr:hover td { background: var(--paper-secondary); }
    .data-table tbody tr { cursor: default; }

    .col-id { width: 80px; }
    .col-connector { width: 140px; }
    .col-result { width: 120px; }

    .cell-primary { font-weight: 500; }
    .cell-muted { color: var(--muted); }
    .cell-evidence { max-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .cell-action { text-align: right; }

    .mono-sm {
      font-family: var(--font-mono);
      font-size: 0.6875rem;
      color: var(--muted);
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

    .result-valid { color: var(--verdict-valid); background: var(--verdict-valid-bg); border-color: var(--verdict-valid-border); }
    .result-warning { color: var(--verdict-warning); background: var(--verdict-warning-bg); border-color: var(--verdict-warning-border); }
    .result-invalid { color: var(--verdict-invalid); background: var(--verdict-invalid-bg); border-color: var(--verdict-invalid-border); }
    .result-unevaluated { color: var(--verdict-unevaluated); background: var(--verdict-unevaluated-bg); border-color: var(--verdict-unevaluated-border); }

    .btn-expand {
      font-size: 0.6875rem;
      color: var(--accent-dark);
      background: none;
      border: none;
      cursor: pointer;
      padding: 0;
      margin-left: var(--spacing-sm);
    }

    .btn-expand:hover { color: var(--ink); }

    .evidence-row td {
      padding: 0 var(--spacing-md) var(--spacing-md);
      border-bottom: 1px solid var(--border);
      height: auto;
    }

    .evidence-block {
      font-family: var(--font-mono);
      font-size: 0.8125rem;
      line-height: 1.6;
      color: var(--ink);
      background: var(--paper);
      border: 1px solid var(--border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-md);
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      max-height: 400px;
      overflow-y: auto;
    }

    /* Summary bar */
    .summary-bar {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
      margin-top: var(--spacing-md);
      padding: var(--spacing-md);
      background: var(--paper);
      border-radius: var(--rounded-md);
      border: 1px solid var(--border);
      flex-wrap: wrap;
    }

    .summary-label {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-right: var(--spacing-sm);
    }

    .summary-chip {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      padding: 2px 8px;
      border-radius: var(--rounded-sm);
      border: 1px solid;
    }

    .summary-duration { margin-left: auto; font-size: 0.8125rem; }

    .artifact-type-badge {
      display: inline-flex;
      align-items: center;
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

    .btn-ghost {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      background: none;
      border: 1px solid var(--border);
      border-radius: var(--rounded-md);
      padding: 5px 12px;
      cursor: pointer;
      transition: color 0.12s ease, background-color 0.12s ease;
    }

    .btn-ghost:hover { color: var(--ink); background: var(--paper-secondary); }

    .error-banner {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 1px solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    /* Skeleton */
    .skeleton-block { display: flex; flex-direction: column; gap: var(--spacing-md); }

    .skeleton {
      border-radius: var(--rounded-md);
      background: linear-gradient(90deg, var(--paper-secondary) 25%, #e5e2db 50%, var(--paper-secondary) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.6s linear infinite;
    }

    .skeleton-banner { height: 56px; }
    .skeleton-card { height: 200px; }
    .skeleton-row { height: 44px; }

    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .empty-card {
      text-align: center;
      padding: var(--spacing-xxl) var(--spacing-lg);
    }

    .empty-text {
      font-size: 0.9375rem;
      color: var(--muted);
      margin: 0 0 var(--spacing-md);
    }
  `],
})
export class ReleaseDetailComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly route = inject(ActivatedRoute);

  release = signal<ReleaseDetail | null>(null);
  artifacts = signal<Artifact[]>([]);
  latestResult = signal<VerificationResult | null>(null);
  verificationHistory = signal<VerificationResult[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);
  verifying = signal(false);
  expandedRule = signal<number | null>(null);

  private releaseId = '';

  ngOnInit(): void {
    this.route.paramMap
      .pipe(
        switchMap((params) => {
          const id = params.get('id');
          if (!id) {
            this.loading.set(false);
            this.error.set('ID de entrega no encontrado en la ruta.');
            return of(null);
          }
          this.releaseId = id;
          return forkJoin({
            release: this.http.get<ReleaseDetail>(`/api/v1/releases/${id}`).pipe(
              catchError(() => { this.error.set('Error al cargar la entrega'); return of(null); }),
            ),
            artifacts: this.http.get<Artifact[]>(`/api/v1/releases/${id}/artifacts`).pipe(
              catchError(() => of([] as Artifact[])),
            ),
            results: this.http.get<VerificationResult[]>(`/api/v1/releases/${id}/results`).pipe(
              catchError(() => of([] as VerificationResult[])),
            ),
          });
        }),
      )
      .subscribe((data) => {
        if (!data) return;
        this.release.set(data.release);
        this.artifacts.set(data.artifacts || []);
        const results = data.results || [];
        this.verificationHistory.set(results);
        if (results.length > 0) {
          this.latestResult.set(results[0]);
        }
        this.loading.set(false);
      });
  }

  launchVerification(): void {
    if (!this.releaseId || this.verifying()) return;
    this.verifying.set(true);
    this.http
      .post<{ task_id: string; status: string }>(`/api/v1/releases/${this.releaseId}/verify`, {})
      .pipe(
        catchError(() => {
          this.error.set('Error al lanzar la verificación');
          this.verifying.set(false);
          return of(null);
        }),
      )
      .subscribe((result) => {
        if (result) {
          this.verifying.set(false);
          this.loading.set(true);
          this.error.set(null);
          this.ngOnInit();
        }
      });
  }

  loadResultDetail(resultId: string): void {
    this.http
      .get<VerificationResult>(`/api/v1/releases/${this.releaseId}/results/${resultId}`)
      .pipe(catchError(() => of(null)))
      .subscribe((result) => {
        if (result) {
          this.latestResult.set(result);
        }
      });
  }

  exportPdf(): void {
    const result = this.latestResult();
    if (!result) return;
    window.open(`/api/v1/releases/${this.releaseId}/results/${result.id}/export?format=pdf`, '_blank');
  }

  toggleEvidence(index: number): void {
    this.expandedRule.update((current) => (current === index ? null : index));
  }

  get latestVerdict(): string | null {
    return this.latestResult()?.verdict || null;
  }

  verdictBannerClass(): Record<string, boolean> {
    const v = this.latestVerdict;
    return {
      'verdict-banner-valid': v === 'VALID',
      'verdict-banner-warning': v === 'WITH_WARNINGS' || v === 'VALID_WITH_WARNINGS',
      'verdict-banner-invalid': v === 'INVALID',
      'verdict-banner-unevaluated': !v || v === 'NOT_EVALUATED',
    };
  }

  verdictBadgeClass(): Record<string, boolean> {
    const v = this.latestVerdict;
    return {
      'verdict-badge-valid': v === 'VALID',
      'verdict-badge-warning': v === 'WITH_WARNINGS' || v === 'VALID_WITH_WARNINGS',
      'verdict-badge-invalid': v === 'INVALID',
      'verdict-badge-unevaluated': !v || v === 'NOT_EVALUATED',
    };
  }

  verdictIcon(): string {
    const v = this.latestVerdict;
    if (v === 'VALID') return '\u2713';
    if (v === 'WITH_WARNINGS' || v === 'VALID_WITH_WARNINGS') return '\u26A0';
    if (v === 'INVALID') return '\u2715';
    return '\u2014';
  }

  verdictLabel(): string {
    const v = this.latestVerdict;
    if (v === 'VALID') return 'VALID';
    if (v === 'WITH_WARNINGS' || v === 'VALID_WITH_WARNINGS') return 'WITH_WARNINGS';
    if (v === 'INVALID') return 'INVALID';
    return 'NOT_EVALUATED';
  }

  statusBadgeClass(): Record<string, boolean> {
    const s = (this.release()?.status || '').toLowerCase();
    return {
      'status-borrador': s === 'borrador',
      'status-pendiente': s === 'pendiente',
      'status-en_verificacion': s === 'en_verificacion',
      'status-valida': s === 'valida',
      'status-con_advertencias': s === 'con_advertencias',
      'status-no_valida': s === 'no_valida',
      'status-archivada': s === 'archivada',
    };
  }

  ruleResultClass(result: string): Record<string, boolean> {
    const r = result?.toUpperCase() || '';
    return {
      'result-valid': r === 'VALID' || r === 'PASSED' || r === 'SUCCESS',
      'result-warning': r === 'WITH_WARNINGS' || r === 'WARNING' || r === 'VALID_WITH_WARNINGS',
      'result-invalid': r === 'INVALID' || r === 'FAILED' || r === 'ERROR',
      'result-unevaluated': !r || r === 'NOT_EVALUATED' || r === 'SKIPPED',
    };
  }

  verdictBadgeMap(verdict: string): Record<string, boolean> {
    return this.ruleResultClass(verdict);
  }

  verdictLabelMap(verdict: string): string {
    const v = verdict?.toUpperCase() || '';
    if (v === 'VALID') return 'VALID';
    if (v === 'WITH_WARNINGS' || v === 'VALID_WITH_WARNINGS') return 'WITH_WARNINGS';
    if (v === 'INVALID') return 'INVALID';
    return 'NOT_EVALUATED';
  }

  summaryItems(summary: Record<string, number>): [string, number][] {
    return Object.entries(summary).sort((a, b) => b[1] - a[1]);
  }
}
