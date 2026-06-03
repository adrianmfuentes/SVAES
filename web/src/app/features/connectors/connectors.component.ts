import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { catchError, of } from 'rxjs';

interface Connector {
  id: string;
  name: string;
  type: string;
  status: 'active' | 'inactive' | 'error';
  global: boolean;
  organization_id?: string;
  organization_name?: string;
  last_tested_at?: string;
}

interface ConnectorApiItem {
  id: string;
  name: string;
  connector_type: string;
  status: string;
  created_at: string;
}

@Component({
  selector: 'app-connectors',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, TranslatePipe],
  template: `
    <div class="connectors-page">
      <div class="page-header">
        <div class="page-header-left">
          <h1 class="page-title">{{ 'connectors.title' | t }}</h1>
        </div>
        <button *ngIf="canManage" class="btn-primary" (click)="openCreate()">{{ 'connectors.new_connector' | t }}</button>
      </div>

      <div *ngIf="loading()" class="skeleton-list">
        <div class="skeleton skeleton-row" *ngFor="let i of [1,2,3]"></div>
      </div>

      <div *ngIf="error() && !loading()" class="error-banner">{{ error() }}</div>

      <div *ngIf="!loading() && !error()">
        <!-- Org connectors -->
        <div class="section-label">{{ 'connectors.org' | t }}</div>
        <div class="data-table-wrap" [class.empty-wrap]="globalConnectors().length === 0">
          <table class="data-table" *ngIf="globalConnectors().length > 0; else orgEmpty">
            <thead>
              <tr>
                <th>{{ 'connectors.table_name' | t }}</th>
                <th>{{ 'connectors.table_type' | t }}</th>
                <th>{{ 'connectors.table_status' | t }}</th>
                <th>{{ 'connectors.last_tested' | t }}</th>
                <th *ngIf="canManage"></th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let c of globalConnectors()">
                <td class="cell-primary">{{ c.name }}</td>
                <td><span class="type-chip">{{ c.type }}</span></td>
                <td>
                  <span class="status-dot" [ngClass]="'status-' + c.status"></span>
                  <span class="status-label">{{ statusLabel(c.status) }}</span>
                </td>
                <td class="cell-muted">{{ c.last_tested_at ? (c.last_tested_at | date:'dd MMM yyyy') : '—' }}</td>
                <td *ngIf="canManage" class="cell-actions">
                  <button class="btn-ghost" (click)="openEdit(c)">{{ 'connectors.edit_label' | t }}</button>
                  <button class="btn-ghost" (click)="testConnector(c)" [disabled]="testingId() === c.id">
                    {{ testingId() === c.id ? ('connectors.testing_label' | t) : ('connectors.test_label' | t) }}
                  </button>
                  <button class="btn-ghost" (click)="toggleConnector(c)">
                    {{ c.status === 'inactive' ? ('connectors.activate' | t) : ('connectors.deactivate' | t) }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
          <ng-template #orgEmpty>
            <div class="empty-state">{{ 'connectors.no_org' | t }}</div>
          </ng-template>
        </div>
      </div>
    </div>

    <!-- MODAL: Create/Edit Connector -->
    <div class="modal-overlay" *ngIf="showModal()" (click)="showModal.set(false)">
      <div class="modal-panel" (click)="$event.stopPropagation()">
        <div class="modal-header">
          <h3 class="modal-title">{{ editingConnector() ? ('connectors.edit_title' | t) : ('connectors.new_global' | t) }}</h3>
          <button class="modal-close" (click)="showModal.set(false)">&times;</button>
        </div>
        <form [formGroup]="connectorForm" (ngSubmit)="submitConnector()">
          <div class="form-group">
            <label for="conn-name">{{ 'connectors.name_label' | t }}</label>
            <input id="conn-name" type="text" formControlName="name" placeholder="GitLab CI" />
          </div>
          <div class="form-group">
            <label for="conn-type">{{ 'connectors.type_label' | t }}</label>
            <select id="conn-type" formControlName="type">
              <option value="gitlab">GitLab</option>
              <option value="github">GitHub</option>
              <option value="jira">Jira</option>
              <option value="sonarqube">SonarQube</option>
              <option value="jenkins">Jenkins</option>
              <option value="webhook">Webhook</option>
            </select>
          </div>
          <div class="form-group">
            <label for="conn-url">{{ 'connectors.base_url_label' | t }}</label>
            <input id="conn-url" type="text" formControlName="base_url" placeholder="https://gitlab.example.com" />
          </div>
          <div class="form-group">
            <label for="conn-token">{{ 'connectors.token_label' | t }}</label>
            <input id="conn-token" type="password" formControlName="token" placeholder="glpat-…" />
          </div>
          <div *ngIf="modalError()" class="error-banner error-banner-sm">{{ modalError() }}</div>
          <div class="modal-footer">
            <button type="button" class="btn-secondary" (click)="showModal.set(false)">{{ 'common.cancel' | t }}</button>
            <button type="submit" class="btn-primary" [disabled]="saving()">
              {{ saving() ? ('connectors.saving' | t) : (editingConnector() ? ('connectors.save_changes' | t) : ('connectors.create' | t)) }}
            </button>
          </div>
        </form>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }

    .connectors-page { padding: 0; }

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

    .section-label {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink);
      margin-bottom: var(--spacing-sm);
    }

    .section-label-muted { color: var(--muted); }

    .data-table-wrap {
      background: var(--surface-raised);
      border: 1px solid var(--border);
      border-radius: var(--rounded-lg);
      overflow: hidden;
      margin-bottom: var(--spacing-md);
    }

    .empty-wrap { padding: 0; }

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
    .data-table tr:hover td { background: var(--paper-secondary); }

    .cell-primary { font-weight: 500; }
    .cell-muted { color: var(--muted); }

    .cell-actions {
      text-align: right;
      display: flex;
      gap: var(--spacing-sm);
      justify-content: flex-end;
      align-items: center;
    }

    .type-chip {
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--muted);
      background: var(--paper-secondary);
      border: 1px solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 1px 6px;
    }

    .status-dot {
      display: inline-block;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      margin-right: 6px;
      vertical-align: middle;
    }

    .status-active { background: var(--verdict-valid); }
    .status-inactive { background: var(--verdict-unevaluated); }
    .status-error { background: var(--verdict-invalid); }

    .status-label {
      font-size: 0.8125rem;
      color: var(--muted);
    }

    .btn-ghost {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      background: none;
      border: 1px solid transparent;
      border-radius: var(--rounded-md);
      padding: 4px 10px;
      cursor: pointer;
      transition: color 0.12s ease, background-color 0.12s ease, border-color 0.12s ease;
    }

    .btn-ghost:hover:not(:disabled) { color: var(--ink); background: var(--paper-secondary); border-color: var(--border); }
    .btn-ghost:disabled { opacity: 0.45; cursor: not-allowed; }

    .btn-primary {
      display: inline-flex;
      align-items: center;
      background: var(--ink);
      color: var(--paper);
      border: 1px solid var(--ink);
      border-radius: var(--rounded-md);
      padding: 9px 18px;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      transition: background-color 0.15s ease;
    }

    .btn-primary:hover:not(:disabled) { background: var(--ink-secondary); }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

    .btn-secondary {
      display: inline-flex;
      align-items: center;
      background: transparent;
      color: var(--ink);
      border: 1px solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 9px 18px;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      transition: background-color 0.15s ease;
    }

    .btn-secondary:hover { background: var(--paper-secondary); }

    .error-banner {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 1px solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    .error-banner-sm { margin-bottom: 0; margin-top: var(--spacing-sm); }

    .skeleton-list { display: flex; flex-direction: column; gap: var(--spacing-sm); }

    .skeleton {
      border-radius: var(--rounded-md);
      background: linear-gradient(90deg, var(--paper-secondary) 25%, #e5e2db 50%, var(--paper-secondary) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.6s linear infinite;
    }

    .skeleton-row { height: 44px; }

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

    .modal-overlay {
      position: fixed;
      inset: 0;
      background: var(--overlay);
      z-index: 100;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .modal-panel {
      background: var(--surface-raised);
      border: 1px solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
      width: 480px;
      max-width: calc(100vw - 48px);
    }

    .modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: var(--spacing-lg);
    }

    .modal-title {
      font-family: var(--font-sans);
      font-size: 1rem;
      font-weight: 600;
      margin: 0;
    }

    .modal-close {
      font-size: 1.25rem;
      color: var(--muted);
      background: none;
      border: none;
      cursor: pointer;
      padding: 0 4px;
      line-height: 1;
    }

    .modal-close:hover { color: var(--ink); }

    .modal-footer {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: var(--spacing-sm);
      margin-top: var(--spacing-lg);
      padding-top: var(--spacing-md);
      border-top: 1px solid var(--border);
    }

    .form-group {
      margin-bottom: var(--spacing-md);
    }

    .form-group label {
      display: block;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink);
      margin-bottom: var(--spacing-xs);
    }

    .form-group input,
    .form-group select {
      width: 100%;
      background: var(--paper);
      color: var(--ink);
      border: 1px solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 9px 12px;
      font-family: var(--font-sans);
      font-size: 0.9375rem;
      outline: none;
      transition: border-color 0.15s ease, background-color 0.15s ease, box-shadow 0.15s ease;
    }

    .form-group input:focus,
    .form-group select:focus {
      border-color: var(--ink);
      background: var(--surface-raised);
      box-shadow: 0 0 0 3px rgba(232, 213, 163, 0.4);
    }
  `],
})
export class ConnectorsComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly ts = inject(TranslationService);

  private orgId: string | null = null;
  readonly canManage = this.authService.getUserRole() === 'MANAGER';
  /** @deprecated keep for template compat — always false on this route */
  readonly isAdmin = false;

  connectors = signal<Connector[]>([]);
  loading = signal(true);
  error = signal<string | null>(null);

  globalConnectors = signal<Connector[]>([]);
  orgConnectors = signal<Connector[]>([]);

  showModal = signal(false);
  editingConnector = signal<Connector | null>(null);
  saving = signal(false);
  modalError = signal<string | null>(null);
  testingId = signal<string | null>(null);

  connectorForm = this.fb.group({
    name: ['', [Validators.required]],
    type: ['gitlab', [Validators.required]],
    base_url: ['', [Validators.required]],
    token: [''],
  });

  ngOnInit(): void {
    const user = this.authService.getUser();
    this.orgId = user?.organization_id ?? null;
    if (!this.orgId) {
      this.error.set(this.ts.translateInstant('connectors.loading_error'));
      this.loading.set(false);
      return;
    }
    this.http.get<ConnectorApiItem[]>(`/api/v1/organizations/${this.orgId}/connectors`)
      .pipe(catchError(() => { this.error.set(this.ts.translateInstant('connectors.loading_error')); return of([]); }))
      .subscribe(data => {
        const mapped = data.map(c => this.mapApiConnector(c));
        this.connectors.set(mapped);
        this.globalConnectors.set(mapped);
        this.orgConnectors.set([]);
        this.loading.set(false);
      });
  }

  private mapApiConnector(c: ConnectorApiItem): Connector {
    return {
      id: c.id,
      name: c.name,
      type: c.connector_type,
      status: this.normalizeStatus(c.status),
      global: false,
      organization_id: this.orgId ?? undefined,
    };
  }

  private normalizeStatus(s: string): 'active' | 'inactive' | 'error' {
    switch (s.toUpperCase()) {
      case 'ACTIVO': return 'active';
      case 'INACTIVO': return 'inactive';
      default: return 'error';
    }
  }

  openCreate(): void {
    this.editingConnector.set(null);
    this.connectorForm.reset({ name: '', type: 'gitlab', base_url: '', token: '' });
    this.modalError.set(null);
    this.showModal.set(true);
  }

  openEdit(c: Connector): void {
    this.editingConnector.set(c);
    this.connectorForm.patchValue({ name: c.name, type: c.type });
    this.modalError.set(null);
    this.showModal.set(true);
  }

  submitConnector(): void {
    if (this.connectorForm.invalid) { this.connectorForm.markAllAsTouched(); return; }
    this.saving.set(true);
    this.modalError.set(null);
    const editing = this.editingConnector();
    const body = editing
      ? { name: this.connectorForm.value.name }
      : {
          connector_type: this.implementationToType(this.connectorForm.value.type ?? ''),
          connector_implementation: (this.connectorForm.value.type ?? '').toUpperCase(),
          name: this.connectorForm.value.name,
          credentials: {
            token: this.connectorForm.value.token,
            base_url: this.connectorForm.value.base_url,
          },
        };
    const req = editing
      ? this.http.patch<ConnectorApiItem>(`/api/v1/organizations/${this.orgId}/connectors/${editing.id}`, body)
      : this.http.post<ConnectorApiItem>(`/api/v1/organizations/${this.orgId}/connectors`, body);
    req.pipe(catchError((err: HttpErrorResponse) => {
      this.modalError.set(err.error?.detail ?? this.ts.translateInstant('connectors.saving_error'));
      this.saving.set(false);
      return of(null);
    })).subscribe(raw => {
      if (raw) {
        const mapped = this.mapApiConnector(raw);
        if (editing) {
          this.globalConnectors.update(list => list.map(x => x.id === mapped.id ? mapped : x));
        } else {
          this.globalConnectors.update(list => [...list, mapped]);
        }
        this.showModal.set(false);
      }
      this.saving.set(false);
    });
  }

  toggleConnector(c: Connector): void {
    const newApiStatus = c.status === 'inactive' ? 'ACTIVO' : 'INACTIVO';
    this.http.patch<ConnectorApiItem>(`/api/v1/organizations/${this.orgId}/connectors/${c.id}`, { status: newApiStatus })
      .pipe(catchError(() => of(null)))
      .subscribe(raw => {
        if (raw) {
          const mapped = this.mapApiConnector(raw);
          this.globalConnectors.update(list => list.map(x => x.id === mapped.id ? mapped : x));
        }
      });
  }

  testConnector(c: Connector): void {
    this.testingId.set(c.id);
    this.http.post(`/api/v1/organizations/${this.orgId}/connectors/${c.id}/test`, {})
      .pipe(catchError(() => of(null)))
      .subscribe(() => this.testingId.set(null));
  }

  private implementationToType(impl: string): string {
    const map: Record<string, string> = {
      gitlab: 'REPO_CODIGO', github: 'REPO_CODIGO',
      bitbucket: 'REPO_CODIGO', gitea: 'REPO_CODIGO',
      jira: 'GESTOR_TAREAS', linear: 'GESTOR_TAREAS',
      trello: 'GESTOR_TAREAS', asana: 'GESTOR_TAREAS',
      confluence: 'SISTEMA_DOCUMENTAL', notion: 'SISTEMA_DOCUMENTAL',
      wikijs: 'SISTEMA_DOCUMENTAL', bookstack: 'SISTEMA_DOCUMENTAL',
      clickup: 'HERRAMIENTA_PLANIFICACION', taiga: 'HERRAMIENTA_PLANIFICACION',
      plane: 'HERRAMIENTA_PLANIFICACION', miro: 'HERRAMIENTA_PLANIFICACION',
      jira_sm: 'GESTION_CAMBIOS', glpi: 'GESTION_CAMBIOS',
      zammad: 'GESTION_CAMBIOS', redmine: 'GESTION_CAMBIOS',
    };
    return map[impl.toLowerCase()] ?? 'REPO_CODIGO';
  }

  statusLabel(status: string): string {
    const map: Record<string, string> = {
      active: this.ts.translateInstant('connectors.status_active'),
      inactive: this.ts.translateInstant('connectors.status_inactive'),
      error: this.ts.translateInstant('connectors.status_error'),
    };
    return map[status] ?? status;
  }
}
