import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { catchError, of } from 'rxjs';
import { AuthService } from '../../core/services/auth.service';

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
}

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <div class="profile-page">
      <div class="page-header">
        <h1 class="page-title">Mi perfil</h1>
      </div>

      <div *ngIf="loading()" class="skeleton-list">
        <div class="skeleton sk-row"></div>
        <div class="skeleton sk-row" style="width:60%"></div>
      </div>

      <div *ngIf="!loading()" class="profile-grid">

        <!-- Profile info card -->
        <div class="card">
          <h2 class="card-title">Informaci&oacute;n del perfil</h2>

          <div class="field-readonly">
            <div class="field-label">Correo electr&oacute;nico</div>
            <div class="field-value">{{ profile()?.email }}</div>
            <div class="field-hint">El email no se puede modificar.</div>
          </div>

          <div class="field-readonly">
            <div class="field-label">Rol</div>
            <div class="field-value">{{ roleLabel(profile()?.role ?? '') }}</div>
          </div>

          <form [formGroup]="nameForm" (ngSubmit)="saveName()">
            <div class="form-group">
              <label for="display-name">Nombre de visualizaci&oacute;n</label>
              <input
                id="display-name"
                type="text"
                formControlName="display_name"
                placeholder="Tu nombre"
              />
              <div class="field-error" *ngIf="nameForm.get('display_name')?.hasError('required') && nameForm.get('display_name')?.touched">
                El nombre es obligatorio.
              </div>
            </div>

            <div *ngIf="nameSaveError()" class="alert-error">{{ nameSaveError() }}</div>

            <div class="form-footer">
              <span class="save-confirm" *ngIf="nameSaved()">Nombre actualizado</span>
              <button type="submit" class="btn-primary" [disabled]="nameForm.invalid || nameSaving()">
                {{ nameSaving() ? 'Guardando…' : 'Guardar nombre' }}
              </button>
            </div>
          </form>
        </div>

        <!-- Organization card (only when user has no org and is not global admin) -->
        <div class="card" *ngIf="!hasOrg() && !isAdmin()">
          <h2 class="card-title">Crear organizaci&oacute;n</h2>

          <div *ngIf="orgCreated()" class="alert-success">
            Organizaci&oacute;n creada correctamente. Vuelve a iniciar sesi&oacute;n para acceder a tu espacio de trabajo.
            <div class="form-footer" style="border-top:none;padding-top:var(--spacing-sm);margin-top:var(--spacing-sm);">
              <button class="btn-primary" (click)="relogin()">Cerrar sesi&oacute;n</button>
            </div>
          </div>

          <form *ngIf="!orgCreated()" [formGroup]="orgForm" (ngSubmit)="createOrg()">
            <div class="form-group">
              <label for="org-name">Nombre</label>
              <input
                id="org-name"
                type="text"
                formControlName="name"
                placeholder="Mi organización"
                (input)="autoSlug()"
              />
              <div class="field-error" *ngIf="orgForm.get('name')?.hasError('required') && orgForm.get('name')?.touched">
                El nombre es obligatorio.
              </div>
            </div>

            <div class="form-group">
              <label for="org-slug">Slug</label>
              <input
                id="org-slug"
                type="text"
                formControlName="slug"
                placeholder="mi-organizacion"
              />
              <div class="field-hint">Solo letras min&uacute;sculas, n&uacute;meros y guiones.</div>
              <div class="field-error" *ngIf="orgForm.get('slug')?.hasError('required') && orgForm.get('slug')?.touched">
                El slug es obligatorio.
              </div>
              <div class="field-error" *ngIf="orgForm.get('slug')?.hasError('pattern') && orgForm.get('slug')?.touched">
                Solo letras min&uacute;sculas, n&uacute;meros y guiones.
              </div>
            </div>

            <div *ngIf="orgError()" class="alert-error">{{ orgError() }}</div>

            <div class="form-footer">
              <button type="submit" class="btn-primary" [disabled]="orgForm.invalid || orgCreating()">
                {{ orgCreating() ? 'Creando…' : 'Crear organización' }}
              </button>
            </div>
          </form>
        </div>

        <!-- Password card -->
        <div class="card">
          <h2 class="card-title">Cambiar contrase&ntilde;a</h2>

          <form [formGroup]="pwForm" (ngSubmit)="savePassword()">
            <div class="form-group">
              <label for="current-pw">Contrase&ntilde;a actual</label>
              <input
                id="current-pw"
                type="password"
                formControlName="current_password"
                autocomplete="current-password"
                placeholder="Tu contrase&ntilde;a actual"
              />
            </div>

            <div class="form-group">
              <label for="new-pw">Nueva contrase&ntilde;a</label>
              <input
                id="new-pw"
                type="password"
                formControlName="new_password"
                autocomplete="new-password"
                placeholder="M&iacute;nimo 8 caracteres"
              />
              <div class="field-error" *ngIf="pwForm.get('new_password')?.hasError('minlength') && pwForm.get('new_password')?.touched">
                M&iacute;nimo 8 caracteres.
              </div>
            </div>

            <div class="form-group">
              <label for="confirm-pw">Confirmar nueva contrase&ntilde;a</label>
              <input
                id="confirm-pw"
                type="password"
                formControlName="confirm_password"
                autocomplete="new-password"
                placeholder="Repite la nueva contrase&ntilde;a"
              />
              <div class="field-error" *ngIf="pwForm.errors?.['mismatch'] && pwForm.get('confirm_password')?.touched">
                Las contrase&ntilde;as no coinciden.
              </div>
            </div>

            <div *ngIf="pwSaveError()" class="alert-error">{{ pwSaveError() }}</div>

            <div class="form-footer">
              <span class="save-confirm" *ngIf="pwSaved()">Contrase&ntilde;a actualizada</span>
              <button type="submit" class="btn-primary" [disabled]="pwForm.invalid || pwSaving()">
                {{ pwSaving() ? 'Guardando…' : 'Cambiar contrase&ntilde;a' }}
              </button>
            </div>
          </form>
        </div>

        <!-- API Keys card -->
        <div class="card api-keys-card">
          <h2 class="card-title">API Keys</h2>

          <div *ngIf="newKeyValue()" class="new-key-banner">
            <div class="new-key-label">Copia esta clave ahora. No volver&aacute; a mostrarse.</div>
            <div class="new-key-row">
              <code class="new-key-value">{{ newKeyValue() }}</code>
              <button class="btn-copy" (click)="copyKey()">
                {{ keyCopied() ? 'Copiado' : 'Copiar' }}
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
                  <th>Nombre</th>
                  <th>Prefijo</th>
                  <th>Creada</th>
                  <th>Expira</th>
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
                    <button class="btn-danger-sm" (click)="revokeKey(k.id)">Revocar</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div *ngIf="!keysLoading() && apiKeys().length === 0 && !newKeyValue()" class="empty-keys">
            Sin API keys activas.
          </div>

          <div class="key-form-section">
            <h3 class="key-form-title">Nueva API key</h3>
            <form [formGroup]="keyForm" (ngSubmit)="createKey()">
              <div class="key-form-row">
                <div class="form-group form-group-flex">
                  <label for="key-name">Nombre</label>
                  <input
                    id="key-name"
                    type="text"
                    formControlName="name"
                    placeholder="p.ej. CI pipeline"
                    autocomplete="off"
                  />
                  <div class="field-error" *ngIf="keyForm.get('name')?.hasError('required') && keyForm.get('name')?.touched">
                    El nombre es obligatorio.
                  </div>
                </div>
                <div class="form-group form-group-narrow">
                  <label for="key-expires">Expira en d&iacute;as <span class="optional">(opc.)</span></label>
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
                  {{ keyCreating() ? 'Creando&hellip;' : 'Crear API key' }}
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

    .api-keys-card {
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
        this.nameSaveError.set(err.error?.detail ?? 'Error al guardar el nombre');
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
        this.pwSaveError.set(err.error?.detail ?? 'Error al cambiar la contraseña');
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
        this.orgError.set(err.error?.detail ?? 'Error al crear la organización');
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
        this.keyCreateError.set(err.error?.detail ?? 'Error al crear la API key');
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

  roleLabel(role: string): string {
    const map: Record<string, string> = {
      ADMIN: 'Administrador global',
      MANAGER: 'Manager',
      OPERATOR: 'Operator',
      VIEWER: 'Viewer',
    };
    return map[role] ?? role;
  }
}
