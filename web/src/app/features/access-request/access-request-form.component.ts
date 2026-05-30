import { Component, inject, signal } from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { RouterModule } from '@angular/router';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { catchError, of } from 'rxjs';

interface AccessRequestResponse {
  id: string;
  status: string;
}

function generateSlug(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');
}

@Component({
  selector: 'app-access-request-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule],
  template: `
    <div class="request-page">
      <a routerLink="/" class="request-back">
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
          <path d="M7.5 2.5L4 6l3.5 3.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        Volver al inicio
      </a>

      <main class="request-main">
        <div class="request-card">

          <!-- Success state -->
          <ng-container *ngIf="submitted(); else formBlock">
            <div class="success-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="var(--verdict-valid)" stroke-width="1.5"/>
                <path d="M8 12l3 3 5-5" stroke="var(--verdict-valid)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <h2 class="card-title">Request submitted</h2>
            <p class="card-desc">You will receive an email when the administrator reviews it.</p>
          </ng-container>

          <!-- Form state -->
          <ng-template #formBlock>
            <h2 class="card-title">Request access to SVAES</h2>
            <p class="card-subtitle">Your request will be reviewed by the system administrator.</p>

            <div class="alert-error" *ngIf="errorMessage()">
              <svg class="alert-icon" width="14" height="14" viewBox="0 0 14 14" fill="none">
                <circle cx="7" cy="7" r="6" stroke="currentColor" stroke-width="1.2"/>
                <path d="M7 4v3.5M7 10v.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
              </svg>
              <span>{{ errorMessage() }}</span>
            </div>

            <form [formGroup]="requestForm" (ngSubmit)="onSubmit()" novalidate>
              <div class="form-group">
                <label for="requester-name">Full name</label>
                <input
                  id="requester-name"
                  type="text"
                  formControlName="requester_name"
                  autocomplete="name"
                  placeholder="Jane Smith"
                  [class.input-error]="fieldHasError('requester_name')"
                />
                <div class="field-error" *ngIf="requestForm.get('requester_name')?.hasError('required') && requestForm.get('requester_name')?.touched">
                  Full name is required.
                </div>
                <div class="field-error" *ngIf="requestForm.get('requester_name')?.hasError('minlength') && requestForm.get('requester_name')?.touched">
                  Name must be at least 2 characters.
                </div>
                <div class="field-error" *ngIf="requestForm.get('requester_name')?.hasError('maxlength') && requestForm.get('requester_name')?.touched">
                  Name must be at most 80 characters.
                </div>
              </div>

              <div class="form-group">
                <label for="requester-email">Work email</label>
                <input
                  id="requester-email"
                  type="email"
                  formControlName="requester_email"
                  autocomplete="email"
                  placeholder="jane@example.com"
                  [class.input-error]="fieldHasError('requester_email')"
                />
                <div class="field-error" *ngIf="requestForm.get('requester_email')?.hasError('required') && requestForm.get('requester_email')?.touched">
                  Work email is required.
                </div>
                <div class="field-error" *ngIf="requestForm.get('requester_email')?.hasError('email') && requestForm.get('requester_email')?.touched">
                  Enter a valid email address.
                </div>
              </div>

              <div class="form-group">
                <label for="org-name">Organization name</label>
                <input
                  id="org-name"
                  type="text"
                  formControlName="organization_name"
                  placeholder="Acme Corp"
                  (input)="updateSlug()"
                  [class.input-error]="fieldHasError('organization_name')"
                />
                <div class="field-error" *ngIf="requestForm.get('organization_name')?.hasError('required') && requestForm.get('organization_name')?.touched">
                  Organization name is required.
                </div>
                <div class="field-error" *ngIf="requestForm.get('organization_name')?.hasError('minlength') && requestForm.get('organization_name')?.touched">
                  Organization name must be at least 3 characters.
                </div>
                <div class="field-error" *ngIf="requestForm.get('organization_name')?.hasError('maxlength') && requestForm.get('organization_name')?.touched">
                  Organization name must be at most 80 characters.
                </div>
                <div class="slug-preview" *ngIf="slugPreview()">
                  <span class="slug-label">Slug preview</span>
                  <code class="slug-value">{{ slugPreview() }}</code>
                </div>
              </div>

              <div class="form-group">
                <label for="org-description">Organization description</label>
                <textarea
                  id="org-description"
                  formControlName="organization_description"
                  placeholder="Briefly describe what your organization does (optional)"
                  rows="3"
                  (input)="updateCharCount()"
                ></textarea>
                <div class="char-counter" [class.char-counter-over]="charCount() > 500">
                  {{ charCount() }}/500
                </div>
                <div class="field-error" *ngIf="requestForm.get('organization_description')?.hasError('maxlength') && requestForm.get('organization_description')?.touched">
                  Description must be at most 500 characters.
                </div>
              </div>

              <button
                type="submit"
                class="btn-primary full-width btn-submit"
                [disabled]="requestForm.invalid || loading()"
                [class.btn-loading]="loading()"
              >
                <span *ngIf="!loading()">Submit request</span>
                <span *ngIf="loading()">Submitting&hellip;</span>
              </button>
            </form>
          </ng-template>

        </div>
      </main>

      <footer class="request-footer">
        <span>&copy; 2026 SVAES</span>
        <nav class="footer-links">
          <a routerLink="/legal/privacidad">Privacidad</a>
          <span aria-hidden="true">&middot;</span>
          <a routerLink="/legal/aviso-legal">Aviso legal</a>
        </nav>
      </footer>
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
      }

      .request-page {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        background: var(--paper);
      }

      .request-back {
        position: absolute;
        top: var(--spacing-lg);
        left: var(--spacing-lg);
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-family: var(--font-sans);
        font-size: 0.8125rem;
        font-weight: 500;
        color: var(--muted);
        transition: color 0.15s ease;
        text-decoration: none;
        z-index: 5;
      }

      .request-back:hover {
        color: var(--ink);
      }

      .request-back svg {
        flex-shrink: 0;
      }

      .request-main {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: var(--spacing-xl);
      }

      .request-card {
        background: var(--surface-raised);
        border: 1px solid var(--border);
        border-radius: var(--rounded-lg);
        padding: var(--spacing-xl);
        width: 100%;
        max-width: 400px;
      }

      .card-title {
        font-family: var(--font-display);
        font-size: 1.5rem;
        font-weight: 400;
        line-height: 1.2;
        letter-spacing: -0.01em;
        color: var(--ink);
        margin: 0 0 var(--spacing-sm);
      }

      .card-subtitle {
        font-family: var(--font-sans);
        font-size: 0.8125rem;
        color: var(--muted);
        line-height: 1.5;
        margin: 0 0 var(--spacing-lg);
      }

      .card-desc {
        font-family: var(--font-sans);
        font-size: 0.9375rem;
        color: var(--muted);
        line-height: 1.65;
        margin: 0;
      }

      .success-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 48px;
        height: 48px;
        border-radius: var(--rounded-full);
        background: var(--verdict-valid-bg);
        margin-bottom: var(--spacing-md);
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
      .form-group textarea {
        width: 100%;
        background: var(--paper);
        color: var(--ink);
        border: 1px solid var(--border-strong);
        border-radius: var(--rounded-md);
        padding: 9px 12px;
        font-family: var(--font-sans);
        font-size: 0.9375rem;
        line-height: 1.5;
        outline: none;
        transition: border-color 0.15s ease, background-color 0.15s ease, box-shadow 0.15s ease;
      }

      .form-group textarea {
        resize: vertical;
        min-height: 72px;
      }

      .form-group input:focus,
      .form-group textarea:focus {
        border-color: var(--ink);
        background: var(--surface-raised);
        box-shadow: 0 0 0 3px rgba(232, 213, 163, 0.4);
      }

      .form-group input.input-error,
      .form-group textarea.input-error {
        border-color: var(--verdict-invalid-border);
        background: var(--verdict-invalid-bg);
      }

      .form-group input::placeholder,
      .form-group textarea::placeholder {
        color: var(--muted);
        opacity: 0.6;
      }

      .field-error {
        font-family: var(--font-sans);
        font-size: 0.75rem;
        color: var(--verdict-invalid);
        margin-top: var(--spacing-xs);
      }

      .slug-preview {
        display: flex;
        align-items: center;
        gap: var(--spacing-xs);
        margin-top: var(--spacing-xs);
      }

      .slug-label {
        font-family: var(--font-sans);
        font-size: 0.6875rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--muted);
      }

      .slug-value {
        font-family: var(--font-mono);
        font-size: 0.6875rem;
        color: var(--muted);
      }

      .char-counter {
        font-family: var(--font-mono);
        font-size: 0.6875rem;
        color: var(--muted);
        text-align: right;
        margin-top: var(--spacing-xs);
      }

      .char-counter-over {
        color: var(--verdict-invalid);
      }

      .btn-submit {
        margin-top: var(--spacing-sm);
        width: 100%;
        height: 40px;
        transition: opacity 0.2s ease;
      }

      .btn-submit.btn-loading {
        opacity: 0.7;
        cursor: wait;
      }

      .alert-error {
        display: flex;
        align-items: flex-start;
        gap: var(--spacing-sm);
        background: var(--verdict-invalid-bg);
        color: var(--verdict-invalid);
        border: 1px solid var(--verdict-invalid-border);
        border-radius: var(--rounded-md);
        padding: var(--spacing-sm) var(--spacing-md);
        font-family: var(--font-sans);
        font-size: 0.8125rem;
        line-height: 1.5;
        margin-bottom: var(--spacing-md);
      }

      .alert-icon {
        flex-shrink: 0;
        margin-top: 2px;
      }

      .request-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: var(--spacing-md) var(--spacing-lg);
        border-top: 1px solid var(--border);
        background: var(--paper);
        font-size: 0.75rem;
        color: var(--muted);
      }

      .footer-links {
        display: flex;
        align-items: center;
        gap: var(--spacing-md);
      }

      .footer-links a {
        color: var(--muted);
        transition: color 0.15s ease;
      }

      .footer-links a:hover {
        color: var(--ink);
      }

      @media (max-width: 480px) {
        .request-main {
          padding: var(--spacing-lg);
        }

        .request-card {
          padding: var(--spacing-lg);
        }

        .request-back {
          top: var(--spacing-md);
          left: var(--spacing-md);
        }
      }
    `,
  ],
})
export class AccessRequestFormComponent {
  private readonly fb = inject(FormBuilder);
  private readonly http = inject(HttpClient);

  readonly requestForm = this.fb.group({
    requester_name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(80)]],
    requester_email: ['', [Validators.required, Validators.email]],
    organization_name: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(80)]],
    organization_description: ['', [Validators.maxLength(500)]],
  });

  readonly loading = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly submitted = signal(false);
  readonly slugPreview = signal('');
  readonly charCount = signal(0);

  fieldHasError(name: string): boolean {
    const ctrl = this.requestForm.get(name);
    return !!(ctrl && ctrl.invalid && ctrl.touched);
  }

  updateSlug(): void {
    const name = this.requestForm.get('organization_name')?.value ?? '';
    this.slugPreview.set(generateSlug(name));
  }

  updateCharCount(): void {
    const desc = this.requestForm.get('organization_description')?.value ?? '';
    this.charCount.set(desc.length);
  }

  onSubmit(): void {
    if (this.requestForm.invalid || this.loading()) {
      this.requestForm.markAllAsTouched();
      return;
    }

    this.loading.set(true);
    this.errorMessage.set(null);

    const body = this.requestForm.value;

    this.http
      .post<AccessRequestResponse>('/api/v1/access-requests', body)
      .pipe(
        catchError((err: HttpErrorResponse) => {
          if (err.status === 409) {
            this.errorMessage.set(
              'An account or pending request already exists for this email.',
            );
          } else if (err.status === 0 || !err.status) {
            this.errorMessage.set(
              'Could not connect to the server. Check your internet connection.',
            );
          } else {
            this.errorMessage.set(
              'An unexpected error occurred. Please try again.',
            );
          }
          this.loading.set(false);
          return of(null);
        }),
      )
      .subscribe((response) => {
        if (response) {
          this.submitted.set(true);
        }
        this.loading.set(false);
      });
  }
}
