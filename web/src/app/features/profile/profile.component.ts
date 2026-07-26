import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { catchError, of, EMPTY } from 'rxjs';
import { AuthService, TotpSetupResponse } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';

interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
  last_used_at: string | null;
}

interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  role: string;
  totp_enabled?: boolean;
}

interface UserNotificationPreferences {
  release_validated: boolean;
  release_invalidated: boolean;
  release_pending_reminder: boolean;
  weekly_digest: boolean;
}

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, TranslatePipe, RouterModule],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.scss'],
})
export class ProfileComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly ts = inject(TranslationService);
  private readonly router = inject(Router);

  profile = signal<UserProfile | null>(null);
  loading = signal(true);

  nameSaving = signal(false);
  nameSaved = signal(false);
  nameSaveError = signal<string | null>(null);

  pwSaving = signal(false);
  pwSaved = signal(false);
  pwSaveError = signal<string | null>(null);

  hasOrg = signal(!!this.authService.getUser()?.organization_id);
  isAdmin = signal(this.authService.getUserRole() === 'ADMIN');
  orgCreating = signal(false);
  orgCreated = signal(false);
  orgError = signal<string | null>(null);

  apiKeys = signal<ApiKey[]>([]);
  keysLoading = signal(true);
  newKeyValue = signal<string | null>(null);
  keyCopied = signal(false);
  keyCreating = signal(false);
  keyCreateError = signal<string | null>(null);

  totpSetupData = signal<TotpSetupResponse | null>(null);
  totpLoading = signal(false);
  totpError = signal<string | null>(null);
  totpSuccess = signal(false);

  orgForm = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(1), Validators.maxLength(100)]],
    slug: ['', [Validators.required, Validators.minLength(1), Validators.maxLength(50), Validators.pattern(/^[a-z0-9-]+$/)]],
  });

  nameForm = this.fb.group({
    display_name: ['', [Validators.required, Validators.minLength(1), Validators.maxLength(100)]],
  });

  keyForm = this.fb.group({
    name: ['', [Validators.required, Validators.maxLength(100)]],
    expires_in_days: [null as number | null],
  });

  totpEnableForm = this.fb.group({
    code: ['', [Validators.required, Validators.pattern(/^\d{6}$/)]],
  });

  totpDisableForm = this.fb.group({
    code: ['', [Validators.required, Validators.pattern(/^\d{6}$/)]],
  });

  pwForm = this.fb.group(
    {
      current_password: ['', [Validators.required]],
      new_password: ['', [Validators.required, Validators.minLength(8), Validators.maxLength(255)]],
      confirm_password: ['', [Validators.required]],
    },
    { validators: this.passwordsMatch }
  );

  deleteAccountForm = this.fb.group({
    password: ['', [Validators.required]],
  });

  showDeleteModal = signal(false);
  deleteAccountDeleting = signal(false);
  deleteAccountError = signal<string | null>(null);
  deleteAccountSuccess = signal(false);
  deleteOrgWarning = signal(false);
  mustTransferFirst = signal(false);
  deleteAccountChecking = signal(false);

  exportDataDownloading = signal(false);
  exportDataError = signal<string | null>(null);

  notifPrefs = signal<UserNotificationPreferences>({
    release_validated: true,
    release_invalidated: true,
    release_pending_reminder: false,
    weekly_digest: true,
  });
  notifPrefsLoading = signal(true);
  notifPrefsError = signal<string | null>(null);

  ngOnInit(): void {
    this.http.get<UserProfile>('/api/v1/users/me')
      .pipe(catchError(() => of(null)))
      .subscribe(user => {
        this.profile.set(user);
        if (user) {
          this.nameForm.patchValue({ display_name: user.display_name });
        }
        this.loading.set(false);
      });

    const userId = this.authService.getUser()?.id;
    if (userId) {
      this.http.get<ApiKey[]>(`/api/v1/users/${userId}/api-keys`)
        .pipe(catchError(() => of([] as ApiKey[])))
        .subscribe(keys => {
          this.apiKeys.set(keys);
          this.keysLoading.set(false);
        });
    } else {
      this.keysLoading.set(false);
    }

    this.loadNotifPrefs();
  }

  saveName(): void {
    if (this.nameForm.invalid) { this.nameForm.markAllAsTouched(); return; }
    this.nameSaving.set(true);
    this.nameSaved.set(false);
    this.nameSaveError.set(null);
    this.http.patch<UserProfile>('/api/v1/users/me', this.nameForm.value)
      .pipe(catchError((err: HttpErrorResponse) => {
        this.nameSaveError.set(err.error?.detail ?? this.ts.translateInstant('common.error_saving'));
        this.nameSaving.set(false);
        return of(null);
      }))
      .subscribe(user => {
        if (user) {
          this.profile.update(p => p ? { ...p, display_name: user.display_name } : p);
          this.nameSaved.set(true);
          setTimeout(() => this.nameSaved.set(false), 3000);
        }
        this.nameSaving.set(false);
      });
  }

  savePassword(): void {
    if (this.pwForm.invalid) { this.pwForm.markAllAsTouched(); return; }
    this.pwSaving.set(true);
    this.pwSaved.set(false);
    this.pwSaveError.set(null);
    const { current_password, new_password, confirm_password } = this.pwForm.value;
    this.http.post('/api/v1/users/me/password', { current_password, new_password, confirm_password })
      .pipe(catchError((err: HttpErrorResponse) => {
        this.pwSaveError.set(err.error?.detail ?? this.ts.translateInstant('profile_page.password_error'));
        this.pwSaving.set(false);
        return of(null);
      }))
      .subscribe(res => {
        if (res !== null) {
          this.pwSaved.set(true);
          this.pwForm.reset();
          setTimeout(() => this.pwSaved.set(false), 3000);
        }
        this.pwSaving.set(false);
      });
  }

  autoSlug(): void {
    const name = this.orgForm.get('name')?.value ?? '';
    const slug = name.toLowerCase().trim().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '').replace(/-+/g, '-').replace(/^-|-$/g, '');
    this.orgForm.patchValue({ slug }, { emitEvent: false });
  }

  createOrg(): void {
    if (this.orgForm.invalid) { this.orgForm.markAllAsTouched(); return; }
    this.orgCreating.set(true);
    this.orgError.set(null);
    this.http.post<{ id: string; name: string; slug: string }>('/api/v1/organizations', this.orgForm.value)
      .pipe(catchError((err: HttpErrorResponse) => {
        this.orgError.set(err.error?.detail ?? this.ts.translateInstant('profile_page.error.creating_org'));
        this.orgCreating.set(false);
        return of(null);
      }))
      .subscribe(org => {
        if (org) {
          this.orgCreated.set(true);
        }
        this.orgCreating.set(false);
      });
  }

  relogin(): void {
    this.authService.logout();
  }

  createKey(): void {
    if (this.keyForm.invalid) { this.keyForm.markAllAsTouched(); return; }
    const userId = this.authService.getUser()?.id;
    if (!userId) return;
    this.keyCreating.set(true);
    this.keyCreateError.set(null);
    this.newKeyValue.set(null);
    const { name, expires_in_days } = this.keyForm.value;
    const body: Record<string, unknown> = { name };
    if (expires_in_days) body['expires_in_days'] = expires_in_days;

    this.http.post<ApiKey & { key: string }>(`/api/v1/users/${userId}/api-keys`, body)
      .pipe(catchError((err: HttpErrorResponse) => {
        this.keyCreateError.set(err.error?.detail ?? this.ts.translateInstant('common.error_occurred'));
        this.keyCreating.set(false);
        return of(null);
      }))
      .subscribe(res => {
        if (res) {
          this.newKeyValue.set(res.key ?? null);
          this.apiKeys.update(keys => [res, ...keys]);
          this.keyForm.reset();
        }
        this.keyCreating.set(false);
      });
  }

  revokeKey(keyId: string): void {
    const userId = this.authService.getUser()?.id;
    if (!userId) return;
    this.http.delete(`/api/v1/users/${userId}/api-keys/${keyId}`)
      .pipe(catchError(() => of(null)))
      .subscribe(() => {
        this.apiKeys.update(keys => keys.filter(k => k.id !== keyId));
        if (this.newKeyValue()) this.newKeyValue.set(null);
      });
  }

  copyKey(): void {
    const key = this.newKeyValue();
    if (!key) return;
    const markCopied = () => {
      this.keyCopied.set(true);
      setTimeout(() => this.keyCopied.set(false), 2000);
    };
    if (navigator.clipboard) {
      navigator.clipboard.writeText(key).then(markCopied).catch(() => this.fallbackCopy(key, markCopied));
    } else {
      this.fallbackCopy(key, markCopied);
    }
  }

  private fallbackCopy(text: string, onSuccess: () => void): void {
    const el = document.createElement('textarea');
    el.value = text;
    el.style.cssText = 'position:fixed;opacity:0;top:0;left:0';
    document.body.appendChild(el);
    el.focus();
    el.select();
    Promise.resolve()
      .then(() => navigator.clipboard.writeText(text))
      .then(() => onSuccess())
      .catch(() => onSuccess());
    el.remove();
  }

  private passwordsMatch(group: import('@angular/forms').AbstractControl) {
    const pw = group.get('new_password')?.value;
    const confirm = group.get('confirm_password')?.value;
    return pw && confirm && pw !== confirm ? { mismatch: true } : null;
  }

  setupTotp(): void {
    this.totpLoading.set(true);
    this.totpError.set(null);
    this.authService.setup2fa()
      .pipe(catchError((err: HttpErrorResponse) => {
        this.totpError.set(err.error?.detail ?? this.ts.translateInstant('common.error_occurred'));
        this.totpLoading.set(false);
        return of(null);
      }))
      .subscribe(data => {
        if (data) this.totpSetupData.set(data);
        this.totpLoading.set(false);
      });
  }

  enableTotp(): void {
    if (this.totpEnableForm.invalid) { this.totpEnableForm.markAllAsTouched(); return; }
    this.totpLoading.set(true);
    this.totpError.set(null);
    const { code } = this.totpEnableForm.value;
    this.authService.enable2fa(code as string)
      .pipe(catchError((err: HttpErrorResponse) => {
        this.totpError.set(err.error?.detail ?? this.ts.translateInstant('common.error_occurred'));
        this.totpLoading.set(false);
        return of(null);
      }))
      .subscribe(res => {
        if (res) {
          this.profile.update(p => p ? { ...p, totp_enabled: true } : p);
          this.totpSetupData.set(null);
          this.totpEnableForm.reset();
          this.totpSuccess.set(true);
          setTimeout(() => this.totpSuccess.set(false), 3000);
        }
        this.totpLoading.set(false);
      });
  }

  disableTotp(): void {
    if (this.totpDisableForm.invalid) { this.totpDisableForm.markAllAsTouched(); return; }
    this.totpLoading.set(true);
    this.totpError.set(null);
    const { code } = this.totpDisableForm.value;
    this.authService.disable2fa(code!)
      .pipe(catchError((err: HttpErrorResponse) => {
        this.totpError.set(err.error?.detail ?? this.ts.translateInstant('common.error_occurred'));
        this.totpLoading.set(false);
        return of(null);
      }))
      .subscribe(res => {
        if (res) {
          this.profile.update(p => p ? { ...p, totp_enabled: false } : p);
          this.totpDisableForm.reset();
          this.totpSuccess.set(true);
          setTimeout(() => this.totpSuccess.set(false), 3000);
        }
        this.totpLoading.set(false);
      });
  }

  roleLabel(role: string): string {
    const map: Record<string, string> = {
      ADMIN: this.ts.translateInstant('profile_page.role_admin'),
      MANAGER: this.ts.translateInstant('profile_page.role_manager'),
      OPERATOR: this.ts.translateInstant('profile_page.role_operator'),
    };
    return map[role] ?? role;
  }

  openDeleteModal(): void {
    this.deleteAccountForm.reset();
    this.deleteAccountError.set(null);
    this.deleteAccountSuccess.set(false);
    this.deleteOrgWarning.set(false);
    this.mustTransferFirst.set(false);
    this.deleteAccountChecking.set(true);
    this.showDeleteModal.set(true);

    const orgId = this.authService.getUser()?.organization_id;
    if (!orgId) {
      this.deleteAccountChecking.set(false);
      return;
    }

    this.http.get<{ owner_id: string }>(`/api/v1/organizations/${orgId}`)
      .pipe(catchError(() => {
        this.deleteAccountChecking.set(false);
        return of(null);
      }))
      .subscribe(org => {
        if (org && org.owner_id === this.authService.getUser()?.id) {
          this.http.get<{ id: string }[]>(`/api/v1/organizations/${orgId}/users`)
            .pipe(catchError(() => {
              this.deleteAccountChecking.set(false);
              return of([]);
            }))
            .subscribe(members => {
              if (members.length <= 1) {
                this.deleteOrgWarning.set(true);
                } else {
                  this.mustTransferFirst.set(true);
                }
                this.deleteAccountChecking.set(false);
              });
          } else {
            this.deleteAccountChecking.set(false);
          }
        });
    }

  closeDeleteModal(): void {
    if (!this.deleteAccountDeleting()) {
      this.showDeleteModal.set(false);
      this.mustTransferFirst.set(false);
    }
  }

  confirmDeleteAccount(): void {
    if (this.deleteAccountForm.invalid) { this.deleteAccountForm.markAllAsTouched(); return; }
    this.deleteAccountDeleting.set(true);
    this.deleteAccountError.set(null);

    const { password } = this.deleteAccountForm.value;
    this.http.delete('/api/v1/users/me/account', { body: { password } })
      .pipe(catchError((err: HttpErrorResponse) => {
        const status = err.status;
        if (status === 400 || status === 401) {
          this.deleteAccountError.set(this.ts.translateInstant('profile_page.delete_account_wrong_password'));
        } else if (status === 403) {
          this.deleteAccountError.set(err.error?.detail ?? this.ts.translateInstant('profile_page.delete_account_error'));
        } else {
          this.deleteAccountError.set(this.ts.translateInstant('profile_page.delete_account_error'));
        }
        this.deleteAccountDeleting.set(false);
        return EMPTY;
      }))
      .subscribe(() => {
        this.deleteAccountSuccess.set(true);
        this.deleteAccountDeleting.set(false);
        setTimeout(() => {
          this.authService.logout();
        }, 2000);
      });
  }

  downloadData(): void {
    this.exportDataDownloading.set(true);
    this.exportDataError.set(null);

    this.http.get<object>('/api/v1/users/me/export')
      .pipe(catchError((err: HttpErrorResponse) => {
        this.exportDataError.set(this.ts.translateInstant('profile_page.export_data_error'));
        this.exportDataDownloading.set(false);
        return of(null);
      }))
      .subscribe(res => {
        if (res) {
          const blob = new Blob([JSON.stringify(res, null, 2)], { type: 'application/json' });
          const url = globalThis.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'svaes-user-data.json';
          document.body.appendChild(a);
          a.click();
          a.remove();
          globalThis.URL.revokeObjectURL(url);
        }
        this.exportDataDownloading.set(false);
      });
  }

  loadNotifPrefs(): void {
    this.http.get<UserNotificationPreferences>('/api/v1/notifications/preferences')
      .pipe(catchError(() => {
        this.notifPrefsLoading.set(false);
        return of(null);
      }))
      .subscribe(prefs => {
        if (prefs) this.notifPrefs.set(prefs);
        this.notifPrefsLoading.set(false);
      });
  }

  toggleNotifPref(key: keyof UserNotificationPreferences): void {
    const current = this.notifPrefs();
    const newValue = !current[key];
    this.notifPrefs.set({ ...current, [key]: newValue });

    this.http.patch('/api/v1/notifications/preferences', { [key]: newValue })
      .pipe(catchError(() => {
        this.notifPrefs.set(current);
        this.notifPrefsError.set(this.ts.translateInstant('common.error_saving'));
        setTimeout(() => this.notifPrefsError.set(null), 3000);
        return of(null);
      }))
      .subscribe();
  }
}
