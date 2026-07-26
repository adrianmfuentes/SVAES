import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { ToastService } from '../../core/services/toast.service';
import { catchError, of } from 'rxjs';
import {
  ConfigSchemaField,
  NotificationChannel,
  NotificationChannelsService,
} from './services/notification-channels.service';

// EMAIL se gestiona por usuario en la página de perfil (preferencias de notificación);
// aquí solo viven los canales de equipo, que empujan a un webhook saliente compartido.
const OUTBOUND_TYPES = ['SLACK', 'MS_TEAMS', 'GENERIC'];

@Component({
  selector: 'app-notification-channels',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, TranslatePipe],
  templateUrl: './notification-channels.component.html',
  styleUrls: ['./notification-channels.component.scss'],
})
export class NotificationChannelsComponent implements OnInit {
  private readonly notificationChannelsService = inject(NotificationChannelsService);
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
    this.notificationChannelsService.getChannelTypes().pipe(
      catchError(() => { this.error.set(this.ts.translateInstant('notification_channels.loading_error')); return of(null); })
    ).subscribe(schemaRes => {
      if (!schemaRes) { this.loading.set(false); return; }
      this.configSchemas.set(schemaRes.config_schemas);
      this.notificationChannelsService.getChannels().pipe(
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
      ? this.notificationChannelsService.updateChannel(existing.id, body)
      : this.notificationChannelsService.createChannel(body);
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
    this.notificationChannelsService.testChannel(existing.id).pipe(
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
    this.notificationChannelsService.deleteChannel(existing.id).pipe(
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
