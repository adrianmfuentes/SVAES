import { Component, inject, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslationService } from '../../i18n/translation.service';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="dialog-overlay" 
         role="dialog" 
         aria-modal="true"
         [attr.aria-labelledby]="'dialog-title-' + dialogId"
         (click)="onOverlayClick($event)"
         (keydown.escape)="onCancel()">
      <div class="dialog" role="document">
        <div class="dialog-icon" aria-hidden="true">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M12 9v4M12 17h.01M12 3L2 21h20L12 3z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <h2 [id]="'dialog-title-' + dialogId" class="dialog-title">{{ title() }}</h2>
        <p class="dialog-message">{{ message() }}</p>
        <div class="dialog-actions">
          <button class="btn btn-secondary" 
                  (click)="onCancel()"
                  [attr.aria-label]="cancelLabel">
            {{ cancelText() }}
          </button>
          <button class="btn btn-danger" 
                  (click)="onConfirm()"
                  [attr.aria-label]="confirmLabel">
            {{ confirmText() }}
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .dialog-overlay {
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
    }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .dialog {
      background: var(--surface-raised);
      border: 0.0625rem solid var(--border);
      border-radius: var(--rounded-lg);
      padding: var(--spacing-lg);
      max-width: 24rem;
      width: 90%;
      animation: scaleIn 0.15s ease-out;
      text-align: center;
    }

    @keyframes scaleIn {
      from {
        opacity: 0;
        transform: scale(0.95);
      }
      to {
        opacity: 1;
        transform: scale(1);
      }
    }

    .dialog-icon {
      display: flex;
      justify-content: center;
      margin-bottom: 1rem;
      color: var(--verdict-warning);
    }

    .dialog-title {
      font-size: 1rem;
      font-weight: 600;
      color: var(--ink);
      margin: 0 0 0.5rem 0;
      line-height: 1.4;
    }

    .dialog-message {
      font-size: 0.875rem;
      color: var(--muted);
      margin: 0 0 1.5rem 0;
      line-height: 1.5;
    }

    .dialog-actions {
      display: flex;
      gap: 0.75rem;
      justify-content: center;
    }

    .btn {
      padding: 0.5625rem 1.125rem;
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      border-radius: var(--rounded-md);
      border: 0.0625rem solid;
      cursor: pointer;
      transition: all 0.15s ease;
      font-family: var(--font-sans);
    }

    .btn:focus-visible {
      outline: 0.1875rem solid var(--accent-dark);
      outline-offset: 0.125rem;
    }

    .btn-secondary {
      background: transparent;
      color: var(--ink);
      border-color: var(--border-strong);
    }

    .btn-secondary:hover:not(:disabled) {
      background: var(--paper-secondary);
    }

    .btn-danger {
      background: var(--verdict-invalid);
      color: var(--paper);
      border-color: var(--verdict-invalid);
    }

    .btn-danger:hover:not(:disabled) {
      background: var(--verdict-invalid-bg);
      color: var(--verdict-invalid);
    }

    .btn:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }

    @media (max-width: 22.5rem) {
      .dialog { padding: var(--spacing-md); width: 95%; }
      .dialog-title { font-size: 0.9375rem; }
      .dialog-message { font-size: 0.8125rem; margin-bottom: 1rem; }
      .dialog-actions {
        flex-direction: column-reverse;
        gap: var(--spacing-xs);
      }
      .btn {
        width: 100%;
        justify-content: center;
        padding: 0.625rem 1rem;
        min-height: 2.75rem;
        font-size: 0.625rem;
      }
    }
  `],
})
export class ConfirmDialogComponent {
  private readonly ts = inject(TranslationService);
  
  readonly title = input.required<string>();
  readonly message = input.required<string>();
  readonly confirmText = input<string>('common.confirm');
  readonly cancelText = input<string>('common.cancel');
  
  readonly confirmed = output<void>();
  readonly cancelled = output<void>();
  
  private static dialogCounter = 0;
  readonly dialogId = ++ConfirmDialogComponent.dialogCounter;

  get cancelLabel(): string {
    return this.ts.translateInstant('a11y.cancel_and_close');
  }

  get confirmLabel(): string {
    return this.ts.translateInstant('a11y.confirm_action');
  }

  onOverlayClick(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('dialog-overlay')) {
      this.onCancel();
    }
  }

  onCancel(): void {
    this.cancelled.emit();
  }

  onConfirm(): void {
    this.confirmed.emit();
  }
}
