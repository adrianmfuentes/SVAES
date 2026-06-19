import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { ToastService } from '../../core/services/toast.service';
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
  last_tested_at?: string;
}

interface ConfigSchemaField {
  type: string;
  label: string;
  required: boolean;
  sensitive?: boolean;
  default?: string;
}

interface ConnectorImplementation {
  implementation: string;
  metadata: { name: string; description?: string };
  config_schema: Record<string, ConfigSchemaField>;
}

interface ConnectorTypesResponse {
  implementations: ConnectorImplementation[];
  by_type: Record<string, ConnectorImplementation[]>;
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
                <th scope="col">{{ 'connectors.table_name' | t }}</th>
                <th scope="col">{{ 'connectors.table_type' | t }}</th>
                <th scope="col">{{ 'connectors.table_status' | t }}</th>
                <th scope="col">{{ 'connectors.last_tested' | t }}</th>
                <th scope="col" *ngIf="canManage"></th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let c of globalConnectors()">
                <td class="cell-primary">{{ c.name }}</td>
                <td><span class="type-chip">{{ typeLabel(c.type) }}</span></td>
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
            <input id="conn-name" type="text" formControlName="name" [placeholder]="'connectors.name_placeholder' | t" />
          </div>
          <div class="form-group" *ngIf="connectorTypes()">
            <label for="conn-type">{{ 'connectors.category_label' | t }}</label>
            <select id="conn-type" formControlName="connectorType" (change)="onTypeChange($event)">
              <option value="">-- {{ 'connectors.select_category' | t }} --</option>
              <option *ngFor="let type of getConnectorTypes()" [value]="type">{{ typeLabel(type) | t }}</option>
            </select>
          </div>
          <div class="form-group" *ngIf="selectedType()">
            <label for="conn-implementation">{{ 'connectors.system_label' | t }}</label>
            <select id="conn-implementation" formControlName="connectorImplementation" (change)="onImplementationChange($event)">
              <option value="">-- {{ 'connectors.select_system' | t }} --</option>
              <option *ngFor="let impl of availableImplementations()" [value]="impl.implementation">{{ impl.metadata.name }}</option>
            </select>
          </div>
          <ng-container *ngIf="selectedImplementation() && currentConfigSchema()">
            <div class="form-group" *ngFor="let field of getConfigFields()" [ngClass]="{'has-error': shouldShowError(field.key)}">
              <label for="field-{{ field.key }}">{{ field.label }}</label>
              <input *ngIf="!field.sensitive"
                id="field-{{ field.key }}"
                type="text"
                [formControlName]="field.key"
                [placeholder]="field.label" />
              <input *ngIf="field.sensitive"
                id="field-{{ field.key }}"
                type="password"
                [formControlName]="field.key"
                [placeholder]="field.label" />
            </div>
          </ng-container>
          <div *ngIf="modalError()" class="error-banner error-banner-sm">{{ modalError() }}</div>
          <div class="modal-footer">
            <button type="button" class="btn-secondary" (click)="showModal.set(false)">{{ 'common.cancel' | t }}</button>
            <button type="submit" class="btn-primary" [disabled]="saving() || !isFormValid()">
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
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 0.125rem 0.5rem;
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
      border: 0.0625rem solid var(--border);
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
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-sm);
      padding: 0.0625rem 0.375rem;
    }

    .status-dot {
      display: inline-block;
      width: 0.375rem;
      height: 0.375rem;
      border-radius: 50%;
      margin-right: 0.375rem;
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
      border: 0.0625rem solid transparent;
      border-radius: var(--rounded-md);
      padding: 0.25rem 0.625rem;
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
      border: 0.0625rem solid var(--ink);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 1.125rem;
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
      border: 0.0625rem solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 1.125rem;
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
      border: 0.0625rem solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    .error-banner-sm { margin-bottom: 0; margin-top: var(--spacing-sm); }

    .alert-success {
      background: var(--verdict-valid-bg, #f0fdf4);
      color: var(--verdict-valid, #166534);
      border: 0.0625rem solid var(--verdict-valid-border, #bbf7d0);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    .alert-error {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 0.0625rem solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    .skeleton-list { display: flex; flex-direction: column; gap: var(--spacing-sm); }

    .skeleton {
      border-radius: var(--rounded-md);
      background: linear-gradient(90deg, var(--paper-secondary) 25%, #e5e2db 50%, var(--paper-secondary) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.6s linear infinite;
    }

    .skeleton-row { height: 2.75rem; }

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
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
      width: 30rem;
      max-width: calc(100vw - 3rem);
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
      padding: 0 0.25rem;
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
      border-top: 0.0625rem solid var(--border);
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
      border: 0.0625rem solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 0.75rem;
      font-family: var(--font-sans);
      font-size: 0.9375rem;
      outline: none;
      transition: border-color 0.15s ease, background-color 0.15s ease, box-shadow 0.15s ease;
    }

    .form-group input:focus,
    .form-group select:focus {
      border-color: var(--ink);
      background: var(--surface-raised);
      box-shadow: 0 0 0 0.1875rem rgba(232, 213, 163, 0.4);
    }

    .form-group.has-error input,
    .form-group.has-error select {
      border-color: var(--verdict-invalid);
    }

    @media (max-width: 48rem) {
      .page-header { flex-wrap: wrap; }

      .page-title { font-size: 1.75rem; }

      .filters-bar {
        flex-wrap: wrap;
        gap: var(--spacing-sm);
      }

      .data-table-wrap { overflow-x: auto; }
    }
  `],
})
export class ConnectorsComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly ts = inject(TranslationService);
  private readonly toast = inject(ToastService);

  private orgId: string | null = null;
  readonly canManage = this.authService.getUserRole() === 'MANAGER';
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

  connectorTypes = signal<ConnectorTypesResponse | null>(null);
  selectedType = signal<string | null>(null);
  selectedImplementation = signal<string | null>(null);
  availableImplementations = signal<ConnectorImplementation[]>([]);
  currentConfigSchema = signal<Record<string, ConfigSchemaField>>({});
  configFields = signal<{key: string, label: string, required: boolean, sensitive?: boolean}[]>([]);

  connectorForm = this.fb.group({
    name: ['', [Validators.required]],
    connectorType: ['', [Validators.required]],
    connectorImplementation: ['', [Validators.required]],
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
    this.http.get<ConnectorTypesResponse>('/api/v1/connectors/types')
      .pipe(catchError(() => of(null)))
      .subscribe(data => {
        if (data) {
          this.connectorTypes.set(data);
        }
      });
  }

  private mapApiConnector(c: ConnectorApiItem, existing?: Connector): Connector {
    return {
      id: c.id,
      name: c.name,
      type: c.connector_type ?? existing?.type ?? 'UNKNOWN',
      status: this.normalizeStatus(c.status),
      global: false,
      organization_id: this.orgId ?? undefined,
      last_tested_at: c.last_tested_at ?? existing?.last_tested_at ?? undefined,
    };
  }

  private normalizeStatus(s: string | undefined | null): 'active' | 'inactive' | 'error' {
    if (!s) return 'error';
    switch (s.toUpperCase()) {
      case 'ACTIVO': return 'active';
      case 'INACTIVO': return 'inactive';
      default: return 'error';
    }
  }

  openCreate(): void {
    this.editingConnector.set(null);
    this.selectedType.set(null);
    this.selectedImplementation.set(null);
    this.availableImplementations.set([]);
    const oldSchema = this.currentConfigSchema();
    this.removeConfigFieldsForSchema(oldSchema);
    this.currentConfigSchema.set({});
    this.configFields.set([]);
    this.connectorForm.reset({ name: '', connectorType: '', connectorImplementation: '' });
    this.modalError.set(null);
    this.showModal.set(true);
  }

  openEdit(c: Connector): void {
    this.editingConnector.set(c);
    this.modalError.set(null);
    const oldSchema = this.currentConfigSchema();
    this.removeConfigFieldsForSchema(oldSchema);
    this.currentConfigSchema.set({});
    this.configFields.set([]);
    this.connectorForm.reset({ name: c.name, connectorType: '', connectorImplementation: '' });
    this.selectedType.set(c.type);
    this.selectedImplementation.set(null);
    this.availableImplementations.set([]);
    this.connectorForm.patchValue({ connectorType: c.type });
    const types = this.connectorTypes()?.by_type;
    this.availableImplementations.set(types?.[c.type] ?? []);
    this.showModal.set(true);
  }

  submitConnector(): void {
    if (this.connectorForm.invalid || !this.selectedImplementation()) { this.connectorForm.markAllAsTouched(); return; }
    this.saving.set(true);
    this.modalError.set(null);
    const editing = this.editingConnector();
    const credentials: Record<string, string> = {};
    const schema = this.currentConfigSchema();
    for (const key of Object.keys(schema)) {
      const value = this.connectorForm.get(key)?.value;
      if (value) {
        credentials[key] = value;
      }
    }
    const body = editing
      ? { name: this.connectorForm.value.name, config: credentials }
      : {
          connector_type: this.connectorForm.value.connectorType ?? '',
          connector_implementation: this.connectorForm.value.connectorImplementation ?? '',
          name: this.connectorForm.value.name ?? '',
          credentials,
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
        const mapped = this.mapApiConnector(raw, editing ?? undefined);
        if (editing) {
          this.globalConnectors.update(list => list.map(x => x.id === mapped.id ? mapped : x));
          this.toast.success(this.ts.translateInstant('common.updated_successfully'));
        } else {
          this.globalConnectors.update(list => [...list, mapped]);
          this.toast.success(this.ts.translateInstant('common.created_successfully'));
        }
        this.showModal.set(false);
      }
      this.saving.set(false);
    });
  }

  toggleConnector(c: Connector): void {
    const newApiStatus = c.status === 'inactive' ? 'ACTIVO' : 'INACTIVO';
    this.http.post<ConnectorApiItem>(`/api/v1/organizations/${this.orgId}/connectors/${c.id}/toggle`, { status: newApiStatus })
      .pipe(catchError(() => {
        this.toast.error(this.ts.translateInstant('common.error_occurred'));
        return of(null);
      }))
      .subscribe(raw => {
        if (raw) {
          const mapped = this.mapApiConnector(raw, c);
          this.globalConnectors.update(list => list.map(x => x.id === mapped.id ? mapped : x));
          const msg = c.status === 'inactive'
            ? this.ts.translateInstant('connectors.toggle_on')
            : this.ts.translateInstant('connectors.toggle_off');
          this.toast.success(msg);
        }
      });
  }

  testConnector(c: Connector): void {
    this.testingId.set(c.id);
    this.http.post<ConnectorApiItem>(`/api/v1/organizations/${this.orgId}/connectors/${c.id}/test`, {})
      .pipe(catchError(() => {
        this.toast.error(this.ts.translateInstant('connectors.test_failure'));
        this.testingId.set(null);
        return of(null);
      }))
      .subscribe(raw => {
        this.testingId.set(null);
        if (raw) {
          const mapped = this.mapApiConnector(raw, c);
          this.globalConnectors.update(list => list.map(x => x.id === mapped.id ? mapped : x));
          this.toast.success(this.ts.translateInstant('connectors.test_success'));
        }
      });
  }

  statusLabel(status: string): string {
    const map: Record<string, string> = {
      active: this.ts.translateInstant('connectors.status_active'),
      inactive: this.ts.translateInstant('connectors.status_inactive'),
      error: this.ts.translateInstant('connectors.status_error'),
    };
    return map[status] ?? status;
  }

  getConnectorTypes(): string[] {
    const types = this.connectorTypes()?.by_type;
    return types ? Object.keys(types) : [];
  }

  typeLabel(type: string): string {
    const translated = this.ts.translateInstant('connector_type.' + type);
    return translated === 'connector_type.' + type ? type : translated;
  }

  onTypeChange(event: Event): void {
    const type = (event.target as HTMLSelectElement).value;
    this.selectedType.set(type);
    this.selectedImplementation.set(null);
    const impls = this.connectorTypes()?.by_type[type] ?? [];
    this.availableImplementations.set(impls);
    this.connectorForm.patchValue({ connectorImplementation: '' });
    const oldSchema = this.currentConfigSchema();
    this.currentConfigSchema.set({});
    this.removeConfigFieldsForSchema(oldSchema);
    this.configFields.set([]);
  }

  onImplementationChange(event: Event): void {
    const impl = (event.target as HTMLSelectElement).value;
    this.selectedImplementation.set(impl);
    const implData = this.availableImplementations().find(i => i.implementation === impl);
    if (implData) {
      const newSchema = implData.config_schema ?? {};
      const oldSchema = this.currentConfigSchema();
      this.currentConfigSchema.set(newSchema);
      this.removeConfigFieldsForSchema(oldSchema);
      this.addConfigFields(newSchema);
      this.updateConfigFields(newSchema);
    }
  }

  getConfigFields() {
    return this.configFields();
  }

  private updateConfigFields(schema: Record<string, ConfigSchemaField>): void {
    this.configFields.set(Object.entries(schema).map(([key, field]) => ({
      key,
      label: field.label,
      required: field.required,
      sensitive: field.sensitive,
    })));
  }

  shouldShowError(fieldKey: string): boolean {
    const control = this.connectorForm.get(fieldKey);
    return !!(control && control.invalid && control.touched);
  }

  isFormValid(): boolean {
    if (this.connectorForm.invalid) return false;
    if (!this.selectedImplementation()) return false;
    const schema = this.currentConfigSchema();
    for (const [key, field] of Object.entries(schema)) {
      if (field.required) {
        const value = this.connectorForm.get(key)?.value;
        if (!value) return false;
      }
    }
    return true;
  }

  private addConfigFields(schema: Record<string, ConfigSchemaField>): void {
    for (const [key, field] of Object.entries(schema)) {
      const validators = field.required ? [Validators.required] : [];
      (this.connectorForm as any).addControl(key, this.fb.control(field.default ?? '', validators));
    }
  }

  private removeConfigFieldsForSchema(schema: Record<string, ConfigSchemaField>): void {
    for (const key of Object.keys(schema)) {
      if (this.connectorForm.contains(key)) {
        (this.connectorForm as any).removeControl(key);
      }
    }
  }
}
