import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { catchError, of } from 'rxjs';
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

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, TranslatePipe],
  template: `
    <div class="profile-page">
      <div class="page-header">
        <h1 class="page-title">{{ 'profile_page.title' | t }}</h1>
      </div>

      <div *ngIf="loading()" class="skeleton-list">
        <div class="skeleton sk-row"></div>
        <div class="skeleton sk-row" style="width:60%"></div>
      </div>

      <div *ngIf="!loading()" class="profile-grid">

        <!-- Profile info card -->
        <div class="card">
          <h2 class="card-title">{{ 'profile_page.info' | t }}</h2>

          <div class="field-readonly">
            <div class="field-label">{{ 'common.email' | t }}</div>
            <div class="field-value">{{ profile()?.email }}</div>
            <div class="field-hint">{{ 'profile_page.email_cannot_change' | t }}</div>
          </div>

          <div class="field-readonly">
            <div class="field-label">{{ 'common.role' | t }}</div>
            <div class="field-value">{{ roleLabel(profile()?.role ?? '') }}</div>
          </div>

          <form [formGroup]="nameForm" (ngSubmit)="saveName()">
            <div class="form-group">
              <label for="display-name">{{ 'profile_page.display_name_label' | t }}</label>
              <input
                id="display-name"
                type="text"
                formControlName="display_name"
                [placeholder]="'profile_page.display_name_placeholder' | t"
              />
              <div class="field-error" *ngIf="nameForm.get('display_name')?.hasError('required') && nameForm.get('display_name')?.touched">
                {{ 'profile_page.name_required_error' | t }}
              </div>
            </div>

            <div *ngIf="nameSaveError()" class="alert-error">{{ nameSaveError() }}</div>

            <div class="form-footer">
              <span class="save-confirm" *ngIf="nameSaved()">{{ 'profile_page.name_saved_msg' | t }}</span>
              <button type="submit" class="btn-primary" [disabled]="nameForm.invalid || nameSaving()">
                {{ nameSaving() ? ('profile_page.saving' | t) : ('profile_page.save_name_btn' | t) }}
              </button>
            </div>
          </form>
        </div>

        <!-- Organization card (only when user has no org and is not global admin) -->
        <div class="card" *ngIf="!hasOrg() && !isAdmin()">
          <h2 class="card-title">{{ 'profile_page.create_org_title' | t }}</h2>

          <div *ngIf="orgCreated()" class="alert-success">
            {{ 'profile_page.org_created_msg' | t }}
            <div class="form-footer" style="border-top:none;padding-top:var(--spacing-sm);margin-top:var(--spacing-sm);">
              <button class="btn-primary" (click)="relogin()">{{ 'profile_page.logout_btn' | t }}</button>
            </div>
          </div>

          <form *ngIf="!orgCreated()" [formGroup]="orgForm" (ngSubmit)="createOrg()">
            <div class="form-group">
              <label for="org-name">{{ 'common.name' | t }}</label>
              <input
                id="org-name"
                type="text"
                formControlName="name"
                [placeholder]="'profile_page.org_name_placeholder' | t"
                (input)="autoSlug()"
              />
              <div class="field-error" *ngIf="orgForm.get('name')?.hasError('required') && orgForm.get('name')?.touched">
                {{ 'profile_page.name_required_error' | t }}
              </div>
            </div>

            <div class="form-group">
              <label for="org-slug">{{ 'profile_page.slug_label' | t }}</label>
              <input
                id="org-slug"
                type="text"
                formControlName="slug"
                [placeholder]="'profile_page.slug_placeholder' | t"
              />
              <div class="field-hint">{{ 'profile_page.slug_hint' | t }}</div>
              <div class="field-error" *ngIf="orgForm.get('slug')?.hasError('required') && orgForm.get('slug')?.touched">
                {{ 'profile_page.slug_required_error' | t }}
              </div>
              <div class="field-error" *ngIf="orgForm.get('slug')?.hasError('pattern') && orgForm.get('slug')?.touched">
                {{ 'profile_page.slug_pattern_error' | t }}
              </div>
            </div>

            <div *ngIf="orgError()" class="alert-error">{{ orgError() }}</div>

            <div class="form-footer">
              <button type="submit" class="btn-primary" [disabled]="orgForm.invalid || orgCreating()">
                {{ orgCreating() ? ('profile_page.creating' | t) : ('profile_page.create_org_btn' | t) }}
              </button>
            </div>
          </form>
        </div>

        <!-- Password card -->
        <div class="card">
          <h2 class="card-title">{{ 'profile_page.change_password' | t }}</h2>

          <form [formGroup]="pwForm" (ngSubmit)="savePassword()">
            <div class="form-group">
              <label for="current-pw">{{ 'profile_page.current_password' | t }}</label>
              <input
                id="current-pw"
                type="password"
                formControlName="current_password"
                autocomplete="current-password"
                [placeholder]="'profile_page.current_pw_placeholder' | t"
              />
            </div>

            <div class="form-group">
              <label for="new-pw">{{ 'profile_page.new_password' | t }}</label>
              <input
                id="new-pw"
                type="password"
                formControlName="new_password"
                autocomplete="new-password"
                [placeholder]="'profile_page.new_pw_placeholder' | t"
              />
              <div class="field-error" *ngIf="pwForm.get('new_password')?.hasError('minlength') && pwForm.get('new_password')?.touched">
                {{ 'profile_page.min_8_error' | t }}
              </div>
            </div>

            <div class="form-group">
              <label for="confirm-pw">{{ 'profile_page.confirm_password' | t }}</label>
              <input
                id="confirm-pw"
                type="password"
                formControlName="confirm_password"
                autocomplete="new-password"
                [placeholder]="'profile_page.confirm_pw_placeholder' | t"
              />
              <div class="field-error" *ngIf="pwForm.errors?.['mismatch'] && pwForm.get('confirm_password')?.touched">
                {{ 'profile_page.password_mismatch' | t }}
              </div>
            </div>

            <div *ngIf="pwSaveError()" class="alert-error">{{ pwSaveError() }}</div>

            <div class="form-footer">
              <span class="save-confirm" *ngIf="pwSaved()">{{ 'profile_page.pw_saved_msg' | t }}</span>
              <button type="submit" class="btn-primary" [disabled]="pwForm.invalid || pwSaving()">
                {{ pwSaving() ? ('profile_page.saving' | t) : ('profile_page.change_pw_btn' | t) }}
              </button>
            </div>
          </form>
        </div>

        <!-- 2FA card -->
        <div class="card twofa-card">
          <h2 class="card-title">{{ 'profile_page.2fa_title' | t }}</h2>

          <div class="field-readonly">
            <div class="field-label">{{ 'profile_page.2fa_status_label' | t }}</div>
            <div class="field-value">
              <span class="badge-2fa" [class.badge-enabled]="profile()?.totp_enabled" [class.badge-disabled]="!profile()?.totp_enabled">
                {{ (profile()?.totp_enabled ? 'profile_page.2fa_enabled' : 'profile_page.2fa_disabled') | t }}
              </span>
            </div>
            <div class="field-hint">{{ 'profile_page.2fa_hint' | t }}</div>
          </div>

          <!-- Setup / QR code section (only when not yet enabled) -->
          <div *ngIf="!profile()?.totp_enabled">
            <div *ngIf="!totpSetupData()" class="form-footer" style="border-top:none; padding-top:0; margin-top: var(--spacing-md);">
              <button class="btn-primary" [disabled]="totpLoading()" (click)="setupTotp()">
                {{ totpLoading() ? ('common.loading' | t) : ('profile_page.2fa_setup_btn' | t) }}
              </button>
            </div>

            <div *ngIf="totpSetupData()" class="totp-setup-panel">
              <p class="totp-instructions">{{ 'profile_page.2fa_scan_instructions' | t }}</p>
              <div class="totp-qr-wrap">
                <img [src]="totpSetupData()?.qr_data_url" alt="QR 2FA" class="totp-qr" />
              </div>
              <div class="totp-secret-wrap">
                <span class="totp-secret-label">{{ 'profile_page.2fa_manual_entry' | t }}</span>
                <code class="totp-secret">{{ totpSetupData()?.secret }}</code>
              </div>
              <form [formGroup]="totpEnableForm" (ngSubmit)="enableTotp()">
                <div class="form-group" style="margin-top: var(--spacing-md);">
                  <label for="totp-enable-code">{{ 'profile_page.2fa_code_label' | t }}</label>
                  <input
                    id="totp-enable-code"
                    type="text"
                    inputmode="numeric"
                    formControlName="code"
                    maxlength="6"
                    [placeholder]="'profile_page.2fa_code_placeholder' | t"
                  />
                  <div class="field-error" *ngIf="totpEnableForm.get('code')?.hasError('required') && totpEnableForm.get('code')?.touched">
                    {{ 'profile_page.2fa_code_required' | t }}
                  </div>
                  <div class="field-error" *ngIf="totpEnableForm.get('code')?.hasError('pattern') && totpEnableForm.get('code')?.touched">
                    {{ 'profile_page.2fa_code_invalid' | t }}
                  </div>
                </div>
                <div *ngIf="totpError()" class="alert-error">{{ totpError() }}</div>
                <div class="form-footer">
                  <span class="save-confirm" *ngIf="totpSuccess()">{{ 'profile_page.2fa_enabled_msg' | t }}</span>
                  <button type="submit" class="btn-primary" [disabled]="totpEnableForm.invalid || totpLoading()">
                    {{ totpLoading() ? ('common.loading' | t) : ('profile_page.2fa_enable_btn' | t) }}
                  </button>
                </div>
              </form>
            </div>
          </div>

          <!-- Disable section (only when enabled) -->
          <div *ngIf="profile()?.totp_enabled">
            <form [formGroup]="totpDisableForm" (ngSubmit)="disableTotp()">
              <div class="form-group" style="margin-top: var(--spacing-md);">
                <label for="totp-disable-code">{{ 'profile_page.2fa_code_label' | t }}</label>
                <input
                  id="totp-disable-code"
                  type="text"
                  inputmode="numeric"
                  formControlName="code"
                  maxlength="6"
                  [placeholder]="'profile_page.2fa_code_placeholder' | t"
                />
                <div class="field-error" *ngIf="totpDisableForm.get('code')?.hasError('required') && totpDisableForm.get('code')?.touched">
                  {{ 'profile_page.2fa_code_required' | t }}
                </div>
                <div class="field-error" *ngIf="totpDisableForm.get('code')?.hasError('pattern') && totpDisableForm.get('code')?.touched">
                  {{ 'profile_page.2fa_code_invalid' | t }}
                </div>
              </div>
              <div *ngIf="totpError()" class="alert-error">{{ totpError() }}</div>
              <div class="form-footer">
                <span class="save-confirm" *ngIf="totpSuccess()">{{ 'profile_page.2fa_disabled_msg' | t }}</span>
                <button type="submit" class="btn-danger-sm" style="padding: 9px 16px;" [disabled]="totpDisableForm.invalid || totpLoading()">
                  {{ totpLoading() ? ('common.loading' | t) : ('profile_page.2fa_disable_btn' | t) }}
                </button>
              </div>
            </form>
          </div>
        </div>

        <!-- API Keys card -->
        <div class="card api-keys-card">
          <h2 class="card-title">{{ 'profile_page.api_keys' | t }}</h2>

          <div *ngIf="newKeyValue()" class="new-key-banner">
            <div class="new-key-label">{{ 'profile_page.new_key_warning' | t }}</div>
            <div class="new-key-row">
              <code class="new-key-value">{{ newKeyValue() }}</code>
              <button class="btn-copy" (click)="copyKey()">
                {{ keyCopied() ? ('profile_page.copied_btn' | t) : ('profile_page.copy_btn' | t) }}
              </button>
            </div>
          </div>

          <div *ngIf="keysLoading()" class="skeleton-list">
            <div class="skeleton sk-row"></div>
            <div class="skeleton sk-row" style="width:80%"></div>
          </div>

          <div *ngIf="!keysLoading() && apiKeys().length > 0" class="data-table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>{{ 'common.name' | t }}</th>
                  <th>{{ 'profile_page.col_prefix' | t }}</th>
                  <th>{{ 'profile_page.created_at_label' | t }}</th>
                  <th>{{ 'profile_page.col_expires' | t }}</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let k of apiKeys()">
                  <td class="cell-primary">{{ k.name }}</td>
                  <td><code class="mono-sm">{{ k.prefix }}…</code></td>
                  <td class="cell-muted">{{ k.created_at | date:'dd MMM yyyy' }}</td>
                  <td class="cell-muted">{{ k.expires_at ? (k.expires_at | date:'dd MMM yyyy') : '—' }}</td>
                  <td class="cell-action">
                    <button class="btn-danger-sm" (click)="revokeKey(k.id)">{{ 'profile_page.revoke_btn' | t }}</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div *ngIf="!keysLoading() && apiKeys().length === 0 && !newKeyValue()" class="empty-keys">
            {{ 'profile_page.no_active_keys' | t }}
          </div>

          <div class="key-form-section">
            <h3 class="key-form-title">{{ 'profile_page.new_api_key_title' | t }}</h3>
            <form [formGroup]="keyForm" (ngSubmit)="createKey()">
              <div class="key-form-row">
                <div class="form-group form-group-flex">
                  <label for="key-name">{{ 'profile_page.key_name' | t }}</label>
                  <input
                    id="key-name"
                    type="text"
                    formControlName="name"
                    [placeholder]="'profile_page.key_name_placeholder' | t"
                    autocomplete="off"
                  />
                  <div class="field-error" *ngIf="keyForm.get('name')?.hasError('required') && keyForm.get('name')?.touched">
                    {{ 'profile_page.key_name_required' | t }}
                  </div>
                </div>
                <div class="form-group form-group-narrow">
                  <label for="key-expires">{{ 'profile_page.expires_days_label' | t }} <span class="optional">({{ 'profile_page.optional_abbr' | t }})</span></label>
                  <input
                    id="key-expires"
                    type="number"
                    formControlName="expires_in_days"
                    placeholder="365"
                    min="1"
                  />
                </div>
              </div>

              <div *ngIf="keyCreateError()" class="alert-error">{{ keyCreateError() }}</div>

              <div class="form-footer">
                <button type="submit" class="btn-primary" [disabled]="keyForm.invalid || keyCreating()">
                  {{ keyCreating() ? ('profile_page.creating_key' | t) : ('profile_page.create_key_btn' | t) }}
                </button>
              </div>
            </form>
          </div>
        </div>

      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }
    .profile-page { padding: 0; }

    .page-header {
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

    .profile-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: var(--spacing-lg);
      align-items: start;
    }

    .card {
      background: var(--surface-raised);
      border: 1px solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
    }

    .card-title {
      font-family: var(--font-display);
      font-size: 1.5rem;
      font-weight: 400;
      line-height: 1.2;
      letter-spacing: -0.01em;
      margin: 0 0 var(--spacing-lg);
      color: var(--ink);
    }

    .field-readonly {
      margin-bottom: var(--spacing-md);
      padding-bottom: var(--spacing-md);
      border-bottom: 1px solid var(--border);
    }

    .field-label {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 4px;
    }

    .field-value {
      font-size: 0.9375rem;
      color: var(--ink);
    }

    .field-hint {
      font-size: 0.75rem;
      color: var(--muted);
      margin-top: 2px;
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

    .form-group input {
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
      box-sizing: border-box;
    }

    .form-group input:focus {
      border-color: var(--ink);
      background: var(--surface-raised);
      box-shadow: 0 0 0 3px rgba(232, 213, 163, 0.4);
    }

    .field-error {
      font-size: 0.75rem;
      color: var(--verdict-invalid);
      margin-top: var(--spacing-xs);
    }

    .alert-error {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 1px solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    .form-footer {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: var(--spacing-md);
      padding-top: var(--spacing-md);
      border-top: 1px solid var(--border);
      margin-top: var(--spacing-md);
    }

    .save-confirm {
      font-size: 0.8125rem;
      color: var(--verdict-valid);
    }

    .skeleton-list {
      display: flex;
      flex-direction: column;
      gap: var(--spacing-sm);
    }

    .skeleton {
      border-radius: var(--rounded-md);
      background: linear-gradient(90deg, var(--paper-secondary) 25%, #e5e2db 50%, var(--paper-secondary) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.6s linear infinite;
    }

    .sk-row { height: 120px; }

    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }

    .alert-success {
      background: var(--verdict-valid-bg, #f0fdf4);
      color: var(--verdict-valid, #166534);
      border: 1px solid var(--verdict-valid-border, #bbf7d0);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    .api-keys-card,
    .twofa-card {
      grid-column: 1 / -1;
    }

    .new-key-banner {
      background: var(--verdict-valid-bg);
      border: 1px solid var(--verdict-valid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-md);
      margin-bottom: var(--spacing-md);
    }

    .new-key-label {
      font-size: 0.8125rem;
      font-weight: 600;
      color: var(--verdict-valid);
      margin-bottom: var(--spacing-sm);
    }

    .new-key-row {
      display: flex;
      align-items: center;
      gap: var(--spacing-sm);
    }

    .new-key-value {
      font-family: var(--font-mono);
      font-size: 0.8125rem;
      color: var(--ink);
      background: var(--surface-raised);
      border: 1px solid var(--border);
      border-radius: var(--rounded-md);
      padding: 6px 12px;
      flex: 1;
      word-break: break-all;
    }

    .btn-copy {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--verdict-valid);
      background: transparent;
      border: 1px solid var(--verdict-valid-border);
      border-radius: var(--rounded-md);
      padding: 6px 12px;
      cursor: pointer;
      white-space: nowrap;
      transition: background-color 0.12s ease;
    }

    .btn-copy:hover { background: var(--verdict-valid-bg); }

    .data-table-wrap {
      border: 1px solid var(--border);
      border-radius: var(--rounded-md);
      overflow: hidden;
      margin-bottom: var(--spacing-md);
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

    .cell-primary { font-weight: 500; }
    .cell-muted { color: var(--muted); }
    .cell-action { text-align: right; }

    .mono-sm {
      font-family: var(--font-mono);
      font-size: 0.6875rem;
      color: var(--muted);
    }

    .btn-danger-sm {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--verdict-invalid);
      background: transparent;
      border: 1px solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: 4px 10px;
      cursor: pointer;
      transition: background-color 0.12s ease;
    }

    .btn-danger-sm:hover { background: var(--verdict-invalid-bg); }

    .empty-keys {
      font-size: 0.8125rem;
      color: var(--muted);
      padding: var(--spacing-md) 0;
    }

    .key-form-section {
      border-top: 1px solid var(--border);
      padding-top: var(--spacing-md);
      margin-top: var(--spacing-md);
    }

    .key-form-title {
      font-family: var(--font-sans);
      font-size: 1rem;
      font-weight: 600;
      color: var(--ink);
      margin: 0 0 var(--spacing-md);
    }

    .key-form-row {
      display: flex;
      gap: var(--spacing-md);
      align-items: flex-start;
    }

    .form-group-flex { flex: 1; }
    .form-group-narrow { width: 140px; flex-shrink: 0; }

    .optional {
      font-weight: 400;
      text-transform: none;
      letter-spacing: 0;
      color: var(--muted);
      font-size: 0.75rem;
    }

    .badge-2fa {
      display: inline-block;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      border-radius: var(--rounded-sm);
      padding: 2px 8px;
    }

    .badge-enabled {
      background: var(--verdict-valid-bg);
      color: var(--verdict-valid);
      border: 1px solid var(--verdict-valid-border);
    }

    .badge-disabled {
      background: var(--paper-secondary);
      color: var(--muted);
      border: 1px solid var(--border);
    }

    .totp-setup-panel {
      margin-top: var(--spacing-md);
      padding-top: var(--spacing-md);
      border-top: 1px solid var(--border);
    }

    .totp-instructions {
      font-size: 0.8125rem;
      color: var(--muted);
      margin: 0 0 var(--spacing-md);
      line-height: 1.5;
    }

    .totp-qr-wrap {
      display: flex;
      justify-content: center;
      margin-bottom: var(--spacing-md);
    }

    .totp-qr {
      width: 180px;
      height: 180px;
      border: 1px solid var(--border);
      border-radius: var(--rounded-md);
      padding: 8px;
      background: white;
    }

    .totp-secret-wrap {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-bottom: var(--spacing-sm);
    }

    .totp-secret-label {
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .totp-secret {
      font-family: var(--font-mono);
      font-size: 0.8125rem;
      color: var(--ink);
      background: var(--paper-secondary);
      border: 1px solid var(--border);
      border-radius: var(--rounded-md);
      padding: 6px 10px;
      letter-spacing: 0.1em;
      word-break: break-all;
    }

    .alert-error {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 1px solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }
  `],
})
export class ProfileComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly ts = inject(TranslationService);

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
    navigator.clipboard.writeText(key).then(() => {
      this.keyCopied.set(true);
      setTimeout(() => this.keyCopied.set(false), 2000);
    });
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
      VIEWER: this.ts.translateInstant('profile_page.role_viewer'),
    };
    return map[role] ?? role;
  }
}
