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
      inset: 0;
      background: rgba(0, 0, 0, 0.5);
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
      background: var(--color-surface, #ffffff);
      border-radius: 0.75rem;
      padding: 1.5rem;
      max-width: 24rem;
      width: 90%;
      box-shadow: 0 1rem 3rem rgba(0, 0, 0, 0.2);
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
      color: var(--color-warning, #D97706);
    }

    .dialog-title {
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--color-text, #1F2937);
      margin: 0 0 0.5rem 0;
    }

    .dialog-message {
      font-size: 0.875rem;
      color: var(--color-text-secondary, #6B7280);
      margin: 0 0 1.5rem 0;
      line-height: 1.5;
    }

    .dialog-actions {
      display: flex;
      gap: 0.75rem;
      justify-content: center;
    }

    .btn {
      padding: 0.625rem 1.25rem;
      font-size: 0.875rem;
      font-weight: 500;
      border-radius: 0.5rem;
      border: none;
      cursor: pointer;
      transition: all 0.15s ease;
      font-family: inherit;
    }

    .btn:focus-visible {
      outline: 2px solid var(--color-focus, #3B82F6);
      outline-offset: 2px;
    }

    .btn-secondary {
      background: var(--color-surface-secondary, #F3F4F6);
      color: var(--color-text, #1F2937);
    }

    .btn-secondary:hover {
      background: var(--color-surface-hover, #E5E7EB);
    }

    .btn-danger {
      background: var(--color-error, #DC2626);
      color: white;
    }

    .btn-danger:hover {
      background: var(--color-error-dark, #B91C1C);
    }

    @media (prefers-color-scheme: dark) {
      .dialog {
        background: var(--color-surface-dark, #1F2937);
      }
      .dialog-title {
        color: var(--color-text-dark, #F9FAFB);
      }
      .dialog-message {
        color: var(--color-text-secondary-dark, #9CA3AF);
      }
      .btn-secondary {
        background: var(--color-surface-secondary-dark, #374151);
        color: var(--color-text-dark, #F9FAFB);
      }
      .btn-secondary:hover {
        background: var(--color-surface-hover-dark, #4B5563);
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
