import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService } from '../../services/toast.service';
import { TranslationService } from '../../i18n/translation.service';

@Component({
  selector: 'app-toast',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="toast-container" role="log" aria-live="polite" aria-atomic="false">
      @for (toast of toastService.toasts(); track toast.id) {
        <div class="toast" [class]="'toast-' + toast.type"
             [attr.role]="toast.type === 'error' ? 'alert' : 'status'"
             (click)="dismiss(toast.id)">
          <div class="toast-icon" aria-hidden="true">
            @switch (toast.type) {
              @case ('success') {
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true" focusable="false">
                  <circle cx="9" cy="9" r="8" stroke="currentColor" stroke-width="1.5"/>
                  <path d="M6 9l2 2 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              }
              @case ('error') {
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true" focusable="false">
                  <circle cx="9" cy="9" r="8" stroke="currentColor" stroke-width="1.5"/>
                  <path d="M9 6v4M9 12v.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
              }
              @case ('warning') {
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true" focusable="false">
                  <path d="M9 2L16 15H2L9 2z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
                  <path d="M9 7v4M9 13v.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
              }
              @case ('info') {
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true" focusable="false">
                  <circle cx="9" cy="9" r="8" stroke="currentColor" stroke-width="1.5"/>
                  <path d="M9 8v5M9 6v.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
              }
            }
          </div>
          <span class="toast-message">{{ toast.message }}</span>
          <button class="toast-close"
                  [attr.aria-label]="dismissLabel"
                  (click)="dismiss(toast.id); $event.stopPropagation()">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true" focusable="false">
              <path d="M10 4L4 10M4 4l6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
      }
    </div>
  `,
  styles: [`
    .toast-container {
      position: fixed;
      bottom: 1.5rem;
      right: 1.5rem;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      pointer-events: none;
    }

    .toast {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.875rem 1rem;
      border-radius: 0.5rem;
      box-shadow: 0 0.25rem 0.75rem rgba(0, 0, 0, 0.15), 0 0.0625rem 0.1875rem rgba(0, 0, 0, 0.1);
      min-width: 17.5rem;
      max-width: 25rem;
      pointer-events: auto;
      cursor: pointer;
      animation: slideIn 0.3s ease-out;
      font-family: var(--font-sans);
      font-size: 0.875rem;
      line-height: 1.4;
    }

    @keyframes slideIn {
      from {
        opacity: 0;
        transform: translateX(100%);
      }
      to {
        opacity: 1;
        transform: translateX(0);
      }
    }

    .toast-success {
      background: #ECFDF5;
      color: #065F46;
      border: 0.0625rem solid #A7F3D0;
    }

    .toast-error {
      background: #FEF2F2;
      color: #991B1B;
      border: 0.0625rem solid #FECACA;
    }

    .toast-warning {
      background: #FFFBEB;
      color: #92400E;
      border: 0.0625rem solid #FDE68A;
    }

    .toast-info {
      background: #EFF6FF;
      color: #1E40AF;
      border: 0.0625rem solid #BFDBFE;
    }

    .toast-icon {
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .toast-message {
      flex: 1;
    }

    .toast-close {
      flex-shrink: 0;
      background: none;
      border: none;
      padding: 0.25rem;
      cursor: pointer;
      opacity: 0.6;
      transition: opacity 0.15s ease;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .toast-close:hover {
      opacity: 1;
    }

    @media (max-width: 480px) {
      .toast-container {
        left: 1rem;
        right: 1rem;
        bottom: 1rem;
      }

      .toast {
        min-width: auto;
        max-width: none;
      }
    }
  `],
})
export class ToastComponent {
  readonly toastService = inject(ToastService);
  private readonly ts = inject(TranslationService);

  get dismissLabel(): string {
    return this.ts.translateInstant('a11y.dismiss_notification');
  }

  dismiss(id: number): void {
    this.toastService.dismiss(id);
  }
}
