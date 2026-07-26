import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { ToastService } from '../../core/services/toast.service';
import { catchError, of } from 'rxjs';
import {
  ConnectorApiItem,
  ConfigSchemaField,
  ConfigSchemaOption,
  ConnectorImplementation,
  ConnectorTypesResponse,
  ConnectorService,
} from './services/connector.service';

interface Connector {
  id: string;
  name: string;
  type: string;
  implementation: string;
  status: 'active' | 'inactive' | 'error';
  global: boolean;
  organization_id?: string;
  organization_name?: string;
  last_tested_at?: string;
  webhook_enabled?: boolean;
}

@Component({
  selector: 'app-connectors',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, TranslatePipe],
  templateUrl: './connectors.component.html',
  styleUrls: ['./connectors.component.scss'],
})
export class ConnectorsComponent implements OnInit {
  private readonly connectorService = inject(ConnectorService);
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

  showWebhookModal = signal(false);
  webhookConnector = signal<Connector | null>(null);
  webhookSecret = signal<string | null>(null);
  webhookSaving = signal(false);
  webhookError = signal<string | null>(null);

  connectorTypes = signal<ConnectorTypesResponse | null>(null);
  selectedType = signal<string | null>(null);
  selectedImplementation = signal<string | null>(null);
  availableImplementations = signal<ConnectorImplementation[]>([]);
  currentConfigSchema = signal<Record<string, ConfigSchemaField>>({});
  configFields = signal<{key: string, label: string, required: boolean, sensitive?: boolean, type?: string, options?: ConfigSchemaOption[]}[]>([]);

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
    this.connectorService.list(this.orgId)
      .pipe(catchError(() => { this.error.set(this.ts.translateInstant('connectors.loading_error')); return of([]); }))
      .subscribe(data => {
        const mapped = data.map(c => this.mapApiConnector(c));
        this.connectors.set(mapped);
        this.globalConnectors.set(mapped);
        this.orgConnectors.set([]);
        this.loading.set(false);
      });
    this.connectorService.listTypes()
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
      implementation: c.connector_implementation ?? existing?.implementation ?? '',
      status: this.normalizeStatus(c.status),
      global: false,
      organization_id: this.orgId ?? undefined,
      last_tested_at: c.last_tested_at ?? existing?.last_tested_at ?? undefined,
      webhook_enabled: c.webhook_enabled ?? existing?.webhook_enabled ?? false,
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
    const types = this.connectorTypes()?.by_type;
    const impls = types?.[c.type] ?? [];
    this.availableImplementations.set(impls);
    this.connectorForm.patchValue({ connectorType: c.type });
    if (c.implementation) {
      this.selectedImplementation.set(c.implementation);
      this.connectorForm.patchValue({ connectorImplementation: c.implementation });
      const implData = impls.find(i => i.implementation === c.implementation);
      if (implData) {
        const newSchema = implData.config_schema ?? {};
        this.currentConfigSchema.set(newSchema);
        this.addConfigFields(newSchema);
        this.updateConfigFields(newSchema);
      }
    }
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
      ? this.connectorService.update(this.orgId!, editing.id, body as { name?: string | null; config: Record<string, string> })
      : this.connectorService.create(this.orgId!, body as { connector_type: string; connector_implementation: string; name: string; credentials: Record<string, string> });
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
    this.connectorService.toggle(this.orgId!, c.id, newApiStatus)
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
    this.connectorService.test(this.orgId!, c.id)
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

  openWebhookConfig(c: Connector): void {
    this.webhookConnector.set(c);
    this.webhookSecret.set(null);
    this.webhookError.set(null);
    this.showWebhookModal.set(true);
  }

  closeWebhookModal(): void {
    this.showWebhookModal.set(false);
    this.webhookConnector.set(null);
    this.webhookSecret.set(null);
  }

  webhookUrlTemplate(): string {
    const c = this.webhookConnector();
    if (!c) return '';
    return `${window.location.origin}/api/v1/webhooks/source-control/{project_id}/${c.id}`;
  }

  private submitWebhookConfig(enabled: boolean, regenerateSecret: boolean): void {
    const c = this.webhookConnector();
    if (!c || !this.orgId) return;
    this.webhookSaving.set(true);
    this.webhookError.set(null);
    this.connectorService.setWebhook(this.orgId, c.id, enabled, regenerateSecret).pipe(
      catchError((err: HttpErrorResponse) => {
        this.webhookError.set(err.error?.detail ?? this.ts.translateInstant('common.error_occurred'));
        this.webhookSaving.set(false);
        return of(null);
      })
    ).subscribe(data => {
      if (data) {
        const updated: Connector = { ...c, webhook_enabled: data.webhook_enabled };
        this.webhookConnector.set(updated);
        this.globalConnectors.update(list => list.map(x => x.id === updated.id ? updated : x));
        if (data.webhook_secret) {
          this.webhookSecret.set(data.webhook_secret);
        }
      }
      this.webhookSaving.set(false);
    });
  }

  toggleWebhookEnabled(event: Event): void {
    const enabled = (event.target as HTMLInputElement).checked;
    this.submitWebhookConfig(enabled, false);
  }

  regenerateWebhookSecret(): void {
    this.submitWebhookConfig(true, true);
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
      type: field.type,
      options: field.options,
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
