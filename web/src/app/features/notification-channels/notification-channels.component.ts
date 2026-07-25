import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { ToastService } from '../../core/services/toast.service';
import { catchError, of } from 'rxjs';

interface ConfigSchemaField {
  type: string;
  label: string;
  required: boolean;
  sensitive?: boolean;
}

interface ChannelTypesResponse {
  channel_types: string[];
  config_schemas: Record<string, Record<string, ConfigSchemaField>>;
}

interface NotificationChannel {
  id: string | null;
  organization_id: string;
  channel_type: string;
  enabled: boolean;
  config_data: Record<string, unknown>;
  configured: boolean;
  created_at: string | null;
  updated_at: string | null;
}

// EMAIL se gestiona por usuario en la página de perfil (preferencias de notificación);
// aquí solo viven los canales de equipo, que empujan a un webhook saliente compartido.
const OUTBOUND_TYPES = ['SLACK', 'MS_TEAMS', 'GENERIC'];

@Component({
  selector: 'app-notification-channels',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, TranslatePipe],
  template: `
    <div class="notif-page">
      <div class="page-header">
        <div class="page-header-left">
          <h1 class="page-title">{{ 'notification_channels.title' | t }}</h1>
        </div>
      </div>
      <p class="page-subtitle">{{ 'notification_channels.subtitle' | t }}</p>

      <div *ngIf="loading()" class="skeleton-list">
        <div class="skeleton skeleton-card" *ngFor="let i of [1,2,3]"></div>
      </div>

      <div *ngIf="error() && !loading()" class="error-banner">{{ error() }}</div>

      <div *ngIf="!loading() && !error()" class="channels-grid">
        <div class="channel-card" *ngFor="let type of outboundTypes">
          <form [formGroup]="forms[type]" (ngSubmit)="save(type)">
            <div class="channel-card-header">
              <div class="channel-card-title-group">
                <h3>{{ typeLabel(type) }}</h3>
                <span class="status-badge" [ngClass]="channelFor(type)?.configured ? 'status-configured' : 'status-unconfigured'">
                  {{ (channelFor(type)?.configured ? 'notification_channels.configured' : 'notification_channels.not_configured') | t }}
                </span>
              </div>
              <label class="toggle-label" *ngIf="canManage">
                <input type="checkbox" formControlName="enabled" />
                {{ 'notification_channels.enabled' | t }}
              </label>
            </div>

            <div class="form-group" *ngFor="let entry of schemaFields(type)">
              <label [attr.for]="type + '-' + entry[0]">
                {{ fieldLabel(entry[1]) }}<span *ngIf="entry[1].required" class="required-star" aria-hidden="true">*</span>
              </label>
              <input
                [id]="type + '-' + entry[0]"
                [type]="entry[1].sensitive ? 'password' : 'text'"
                [formControlName]="entry[0]"
                [attr.aria-required]="entry[1].required"
                [readonly]="!canManage"
              />
            </div>

            <p *ngIf="channelFor(type)?.updated_at as updatedAt" class="form-hint">
              {{ 'notification_channels.last_updated' | t }}: {{ updatedAt | date:'short' }}
            </p>

            <div class="channel-card-actions" *ngIf="canManage">
              <button type="submit" class="btn-primary btn-sm" [disabled]="saving() === type">
                {{ saving() === type ? ('common.saving' | t) : ('common.save' | t) }}
              </button>
              <button
                type="button"
                class="btn-secondary btn-sm"
                [disabled]="!channelFor(type)?.configured || testing() === type"
                (click)="sendTest(type)"
              >
                {{ testing() === type ? ('notification_channels.testing' | t) : ('notification_channels.send_test' | t) }}
              </button>
              <button
                type="button"
                class="btn-ghost btn-danger-ghost btn-sm"
                *ngIf="channelFor(type)?.configured"
                [disabled]="deleting() === type"
                (click)="disable(type)"
              >
                {{ 'common.delete' | t }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }
    .notif-page { padding: 0; }

    .page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--spacing-xs); }
    .page-title {
      font-family: var(--font-display);
      font-size: 2.25rem;
      font-weight: 400;
      line-height: 1.1;
      letter-spacing: -0.02em;
      margin: 0;
      color: var(--ink);
    }
    .page-subtitle { color: var(--muted); font-size: 0.8125rem; margin: 0 0 var(--spacing-lg); }

    .error-banner {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 0.0625rem solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    .skeleton-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr)); gap: var(--spacing-md); }
    .skeleton { border-radius: var(--rounded-md); background: linear-gradient(90deg, var(--paper-secondary) 25%, #e5e2db 50%, var(--paper-secondary) 75%); background-size: 200% 100%; animation: shimmer 1.6s linear infinite; }
    .skeleton-card { height: 12rem; }
    @keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

    .channels-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(20rem, 1fr));
      gap: var(--spacing-md);
    }

    .channel-card {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-md);
    }

    .channel-card-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: var(--spacing-sm);
      margin-bottom: var(--spacing-md);
    }

    .channel-card-title-group { display: flex; align-items: center; gap: var(--spacing-sm); flex-wrap: wrap; }

    .channel-card-header h3 { margin: 0; font-size: 1rem; font-weight: 600; color: var(--ink); }

    .status-badge {
      font-family: var(--font-sans);
      font-size: 0.625rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      padding: 0.125rem 0.4375rem;
      border-radius: var(--rounded-sm);
    }
    .status-configured { background: #e8f5e9; color: #2e7d32; }
    .status-unconfigured { background: var(--paper-secondary); color: var(--muted); }

    .toggle-label {
      display: flex;
      align-items: center;
      gap: 0.375rem;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--muted);
      white-space: nowrap;
    }

    .form-group { margin-bottom: var(--spacing-sm); }
    .form-group label {
      display: block;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--ink);
      margin-bottom: var(--spacing-xs);
    }
    .required-star { color: var(--verdict-invalid); margin-left: 0.25rem; font-size: 0.75rem; }

    .form-group input {
      width: 100%;
      background: var(--paper);
      color: var(--ink);
      border: 0.0625rem solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 0.5rem 0.625rem;
      font-family: var(--font-sans);
      font-size: 0.8125rem;
      outline: none;
    }
    .form-group input:focus { border-color: var(--ink); background: var(--surface-raised); box-shadow: 0 0 0 0.1875rem rgba(232, 213, 163, 0.4); }
    .form-group input[readonly] { opacity: 0.7; cursor: not-allowed; }

    .form-hint { font-size: 0.75rem; color: var(--muted); margin: 0 0 var(--spacing-sm); }

    .channel-card-actions { display: flex; gap: var(--spacing-xs); flex-wrap: wrap; margin-top: var(--spacing-sm); }

    .btn-primary {
      background: var(--ink); color: var(--paper); border: 0.0625rem solid var(--ink);
      border-radius: var(--rounded-md); font-family: var(--font-sans); font-weight: 600;
      letter-spacing: 0.06em; text-transform: uppercase; cursor: pointer;
    }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

    .btn-secondary {
      background: transparent; color: var(--ink); border: 0.0625rem solid var(--border-strong);
      border-radius: var(--rounded-md); font-family: var(--font-sans); font-weight: 600;
      letter-spacing: 0.06em; text-transform: uppercase; cursor: pointer;
    }
    .btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }

    .btn-ghost {
      background: none; border: 0.0625rem solid transparent; color: var(--muted);
      border-radius: var(--rounded-md); font-family: var(--font-sans); font-weight: 600;
      letter-spacing: 0.06em; text-transform: uppercase; cursor: pointer;
    }
    .btn-danger-ghost { color: var(--verdict-invalid); }
    .btn-danger-ghost:hover:not(:disabled) { background: var(--verdict-invalid-bg); border-color: var(--verdict-invalid-border); }

    .btn-sm { font-size: 0.6875rem; padding: 0.375rem 0.75rem; }

    @media (max-width: 48rem) {
      .channels-grid { grid-template-columns: 1fr; }
      .page-title { font-size: 1.75rem; }
    }
  `],
})
export class NotificationChannelsComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly authService = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly ts = inject(TranslationService);
  private readonly toast = inject(ToastService);

  readonly canManage = this.authService.getUserRole() === 'MANAGER' || this.authService.getUserRole() === 'ADMIN';
  readonly outboundTypes = OUTBOUND_TYPES;

  loading = signal(true);
  error = signal<string | null>(null);
  channels = signal<NotificationChannel[]>([]);
  configSchemas = signal<Record<string, Record<string, ConfigSchemaField>>>({});
  saving = signal<string | null>(null);
  testing = signal<string | null>(null);
  deleting = signal<string | null>(null);

  forms: Record<string, FormGroup> = {};

  ngOnInit(): void {
    this.loadAll();
  }

  private loadAll(): void {
    this.loading.set(true);
    this.error.set(null);
    this.http.get<ChannelTypesResponse>('/api/v1/notifications/channel-types').pipe(
      catchError(() => { this.error.set(this.ts.translateInstant('notification_channels.loading_error')); return of(null); })
    ).subscribe(schemaRes => {
      if (!schemaRes) { this.loading.set(false); return; }
      this.configSchemas.set(schemaRes.config_schemas);
      this.http.get<NotificationChannel[]>('/api/v1/notifications/channels').pipe(
        catchError(() => { this.error.set(this.ts.translateInstant('notification_channels.loading_error')); return of([] as NotificationChannel[]); })
      ).subscribe(channels => {
        this.channels.set(channels);
        this.buildForms();
        this.loading.set(false);
      });
    });
  }

  private buildForms(): void {
    for (const type of this.outboundTypes) {
      const channel = this.channelFor(type);
      const schema = this.configSchemas()[type] ?? {};
      const controls: Record<string, unknown> = {
        enabled: [channel?.enabled ?? false],
      };
      for (const [field, def] of Object.entries(schema)) {
        const currentValue = (channel?.config_data?.[field] as string) ?? '';
        controls[field] = [currentValue, def.required ? [Validators.required] : []];
      }
      this.forms[type] = this.fb.group(controls);
      if (!this.canManage) {
        this.forms[type].disable();
      }
    }
  }

  channelFor(type: string): NotificationChannel | undefined {
    return this.channels().find(c => c.channel_type === type);
  }

  schemaFields(type: string): [string, ConfigSchemaField][] {
    return Object.entries(this.configSchemas()[type] ?? {});
  }

  save(type: string): void {
    const form = this.forms[type];
    if (!form || form.invalid) { form?.markAllAsTouched(); return; }
    this.saving.set(type);
    const { enabled, ...configData } = form.getRawValue();
    const existing = this.channelFor(type);
    const body = { channel_type: type, enabled: !!enabled, config_data: configData };
    const req = existing?.configured
      ? this.http.patch(`/api/v1/notifications/channels/${existing.id}`, body)
      : this.http.post('/api/v1/notifications/channels', body);
    req.pipe(
      catchError((err: HttpErrorResponse) => {
        this.toast.error(err.error?.detail ?? this.ts.translateInstant('notification_channels.saving_error'));
        this.saving.set(null);
        return of(null);
      })
    ).subscribe(result => {
      if (result) {
        this.toast.success(this.ts.translateInstant('notification_channels.saved'));
        this.loadAll();
      }
      this.saving.set(null);
    });
  }

  sendTest(type: string): void {
    const existing = this.channelFor(type);
    if (!existing?.id) return;
    this.testing.set(type);
    this.http.post<{ delivered: boolean }>(`/api/v1/notifications/channels/${existing.id}/test`, {}).pipe(
      catchError((err: HttpErrorResponse) => {
        this.toast.error(err.error?.detail ?? this.ts.translateInstant('notification_channels.test_error'));
        this.testing.set(null);
        return of(null);
      })
    ).subscribe(result => {
      if (result) {
        if (result.delivered) {
          this.toast.success(this.ts.translateInstant('notification_channels.test_delivered'));
        } else {
          this.toast.warning(this.ts.translateInstant('notification_channels.test_failed'));
        }
      }
      this.testing.set(null);
    });
  }

  disable(type: string): void {
    const existing = this.channelFor(type);
    if (!existing?.id) return;
    this.deleting.set(type);
    this.http.delete(`/api/v1/notifications/channels/${existing.id}`).pipe(
      catchError(() => {
        this.toast.error(this.ts.translateInstant('notification_channels.deleting_error'));
        this.deleting.set(null);
        return of(null);
      })
    ).subscribe(() => {
      this.deleting.set(null);
      this.loadAll();
    });
  }

  typeLabel(type: string): string {
    return this.ts.translateInstant('notification_channels.type.' + type);
  }

  fieldLabel(def: ConfigSchemaField): string {
    return this.ts.translateInstant(def.label);
  }
}
