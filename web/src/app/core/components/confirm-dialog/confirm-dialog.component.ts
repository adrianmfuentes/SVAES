import { AfterViewInit, Component, ElementRef, ViewChild, inject, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TranslationService } from '../../i18n/translation.service';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './confirm-dialog.component.html',
  styleUrls: ['./confirm-dialog.component.scss'],
})
export class ConfirmDialogComponent implements AfterViewInit {
  @ViewChild('dialogEl') private readonly dialogElRef!: ElementRef<HTMLDialogElement>;

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

  ngAfterViewInit(): void {
    if (typeof this.dialogElRef.nativeElement.showModal === 'function') {
      this.dialogElRef.nativeElement.showModal();
    }
  }

  onOverlayClick(event: MouseEvent): void {
    if (event.target === this.dialogElRef.nativeElement) {
      this.onCancel();
    }
  }

  onDialogKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter') {
      event.preventDefault();
      this.onConfirm();
    }
  }

  onCancel(): void {
    this.cancelled.emit();
  }

  onConfirm(): void {
    this.confirmed.emit();
  }
}
