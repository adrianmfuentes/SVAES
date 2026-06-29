import { Component, inject, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FeedbackService, FeedbackPayload } from '../../../core/services/feedback.service';

@Component({
  selector: 'app-feedback-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="modal-overlay"
         role="dialog"
         aria-modal="true"
         aria-labelledby="feedback-title"
         (click)="onOverlayClick($event)"
         (keydown.escape)="onClose()">
      <div class="modal" role="document">
        <button class="modal-close" (click)="onClose()" aria-label="Cerrar">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
        </button>

        <h2 id="feedback-title" class="modal-title">Feedback UX</h2>
        <p class="modal-subtitle">Ayúdame a mejorar SVAES — tu opinión cuenta</p>

        @if (submitted) {
          <div class="alert-success" role="alert">
            <span class="alert-success-icon">✓</span>
            <span>¡Gracias por tu feedback!</span>
          </div>
        } @else {
          @if (error) {
            <div class="alert-error" role="alert">
              <span class="alert-error-icon">!</span>
              <span>{{ error }}</span>
            </div>
          }

          <form (ngSubmit)="onSubmit()" #feedbackForm="ngForm">
            <div class="form-group">
              <label for="fb-name">Nombre *</label>
              <input
                type="text"
                id="fb-name"
                name="name"
                [(ngModel)]="payload.name"
                required
                maxlength="100"
                placeholder="Tu nombre"
              />
            </div>

            <div class="form-group">
              <label for="fb-email">Email (opcional)</label>
              <input
                type="email"
                id="fb-email"
                name="email"
                [(ngModel)]="payload.email"
                maxlength="255"
                placeholder="tu@email.com"
              />
            </div>

            <div class="form-group">
              <label>Calificación UX *</label>
              <div class="stars" role="radiogroup" aria-label="Calificación del 0 al 5">
                @for (star of [1, 2, 3, 4, 5]; track star) {
                  <button
                    type="button"
                    class="star-btn"
                    [class.filled]="payload.rating >= star"
                    [attr.aria-label]="star + ' estrella'"
                    (click)="payload.rating = star"
                  >
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                    </svg>
                  </button>
                }
              </div>
              <span class="rating-label">{{ ratingLabel }}</span>
            </div>

            <div class="form-group">
              <label for="fb-comments">Comentarios *</label>
              <textarea
                id="fb-comments"
                name="comments"
                [(ngModel)]="payload.comments"
                required
                maxlength="2000"
                rows="4"
                placeholder="¿Qué está bien? ¿Qué falla? ¿Qué mejorarías?"
              ></textarea>
              <span class="char-count">{{ payload.comments.length }}/2000</span>
            </div>

            <div class="modal-actions">
              <button type="button" class="btn-secondary" (click)="onClose()">Cancelar</button>
              <button type="submit" class="btn-accent" [disabled]="!isValid || loading">
                @if (loading) {
                  Enviando...
                } @else {
                  Enviar Feedback
                }
              </button>
            </div>
          </form>
        }
      </div>
    </div>
  `,
  styles: [`
    .modal-overlay {
      position: fixed;
      top: 0;
      right: 0;
      bottom: 0;
      left: 0;
      inset: 0;
      background: var(--overlay);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10000;
      animation: fadeIn 0.15s ease-out;
      padding: var(--spacing-md);
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .modal {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-xl);
      max-width: 28rem;
      width: 100%;
      animation: scaleIn 0.15s ease-out;
      position: relative;
    }

    @keyframes scaleIn {
      from { opacity: 0; transform: scale(0.95); }
      to { opacity: 1; transform: scale(1); }
    }

    .modal-close {
      position: absolute;
      top: var(--spacing-md);
      right: var(--spacing-md);
      background: none;
      border: none;
      cursor: pointer;
      color: var(--muted);
      padding: var(--spacing-xs);
      border-radius: var(--rounded-sm);
      transition: color 0.15s ease;
    }

    .modal-close:hover {
      color: var(--ink);
    }

    .modal-title {
      font-family: var(--font-display);
      font-size: 1.5rem;
      font-weight: 400;
      color: var(--ink);
      margin: 0 0 var(--spacing-xs);
      padding-right: var(--spacing-xl);
    }

    .modal-subtitle {
      font-size: 0.875rem;
      color: var(--muted);
      margin: 0 0 var(--spacing-xl);
    }

    .alert-success {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background: var(--verdict-valid-bg);
      color: var(--verdict-valid);
      border: 0.0625rem solid var(--verdict-valid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.875rem;
      margin-bottom: var(--spacing-md);
    }

    .alert-error {
      display: flex;
      align-items: flex-start;
      gap: 0.5rem;
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
      border: 0.0625rem solid var(--verdict-invalid-border);
      border-radius: var(--rounded-md);
      padding: var(--spacing-sm) var(--spacing-md);
      font-size: 0.8125rem;
      margin-bottom: var(--spacing-md);
    }

    .alert-error-icon {
      flex-shrink: 0;
      margin-top: 0.0625rem;
    }

    .form-group {
      margin-bottom: var(--spacing-md);
    }

    label {
      display: block;
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--ink);
      margin-bottom: var(--spacing-xs);
    }

    input, textarea {
      width: 100%;
      font-family: var(--font-sans);
      font-size: 0.9375rem;
      background: var(--paper);
      color: var(--ink);
      border: 0.0625rem solid var(--border-strong);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 0.75rem;
      outline: none;
      transition: border-color 0.15s ease, background-color 0.15s ease;
      box-sizing: border-box;
    }

    input:focus, textarea:focus {
      border-color: var(--ink);
      background: var(--surface-raised);
      outline: 0.1875rem solid rgba(232, 213, 163, 0.4);
    }

    textarea {
      resize: vertical;
      min-height: 100px;
    }

    .stars {
      display: flex;
      gap: var(--spacing-xs);
      margin-bottom: var(--spacing-xs);
    }

    .star-btn {
      background: none;
      border: none;
      cursor: pointer;
      color: var(--border);
      padding: 2px;
      transition: color 0.15s ease, transform 0.1s ease;
    }

    .star-btn:hover {
      transform: scale(1.1);
    }

    .star-btn.filled {
      color: var(--accent-dark);
    }

    .rating-label {
      font-size: 0.75rem;
      color: var(--muted);
    }

    .char-count {
      display: block;
      text-align: right;
      font-size: 0.6875rem;
      color: var(--muted);
      margin-top: var(--spacing-xs);
    }

    .modal-actions {
      display: flex;
      gap: var(--spacing-sm);
      justify-content: flex-end;
      margin-top: var(--spacing-lg);
    }

    .btn-secondary {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: var(--spacing-sm);
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

    .btn-secondary:hover:not(:disabled) {
      background: var(--paper-secondary);
    }

    .btn-accent {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: var(--spacing-sm);
      background: var(--accent);
      color: var(--ink);
      border: 0.0625rem solid var(--accent-dark);
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

    .btn-accent:hover:not(:disabled) {
      background: var(--accent-dark);
    }

    .btn-accent:disabled, .btn-secondary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    @media (max-width: 22.5rem) {
      .modal { padding: var(--spacing-lg); }
      .modal-actions { flex-direction: column-reverse; }
      .btn-secondary, .btn-accent { width: 100%; }
    }
  `],
})
export class FeedbackModalComponent {
  private readonly feedbackService = inject(FeedbackService);

  readonly closed = output<void>();

  payload: FeedbackPayload = {
    name: '',
    email: '',
    rating: 0,
    comments: '',
  };

  loading = false;
  submitted = false;
  error: string | null = null;

  get isValid(): boolean {
    return !!this.payload.name?.trim() &&
           this.payload.rating > 0 &&
           !!this.payload.comments?.trim();
  }

  get ratingLabel(): string {
    const labels = [
      'Sin calificar',
      'Muy malo',
      'Malo',
      'Regular',
      'Bueno',
      'Excelente'
    ];
    return labels[this.payload.rating] || 'Sin calificar';
  }

  onOverlayClick(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('modal-overlay')) {
      this.onClose();
    }
  }

  onClose(): void {
    this.closed.emit();
  }

  onSubmit(): void {
    if (!this.isValid || this.loading) return;

    this.loading = true;
    this.error = null;

    this.feedbackService.submit(this.payload).subscribe({
      next: () => {
        this.submitted = true;
        this.loading = false;
        setTimeout(() => this.onClose(), 1500);
      },
      error: () => {
        this.error = 'No se pudo enviar el feedback. Inténtalo de nuevo.';
        this.loading = false;
      },
    });
  }
}
