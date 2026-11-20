import { AfterViewInit, ChangeDetectorRef, Component, ElementRef, ViewChild, inject, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FeedbackService, FeedbackPayload } from '../../../core/services/feedback.service';
import { TranslatePipe } from '../../../core/i18n/translate.pipe';
import { TranslationService } from '../../../core/i18n/translation.service';

@Component({
  selector: 'app-feedback-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, TranslatePipe],
  templateUrl: './feedback-modal.component.html',
  styleUrls: ['./feedback-modal.component.scss'],
})
export class FeedbackModalComponent implements AfterViewInit {
  @ViewChild('dialogEl') private readonly dialogElRef!: ElementRef<HTMLDialogElement>;

  private readonly changeDetector = inject(ChangeDetectorRef);
  private readonly feedbackService = inject(FeedbackService);
  private readonly ts = inject(TranslationService);

  readonly closed = output<void>();

  payload: FeedbackPayload = {
    name: '',
    email: '',
    rating: 0,
    comments: '',
  };

  loading = false;
  submitted = false;
  showErrors = false;
  error: string | null = null;

  private static readonly EMAIL_PATTERN = /^[^\s@]+@[^\s@.]+\.[^\s@]+$/;

  get emailInvalid(): boolean {
    const email = this.payload.email?.trim();
    return !!email && !FeedbackModalComponent.EMAIL_PATTERN.test(email);
  }

  get isValid(): boolean {
    return !!this.payload.name?.trim() &&
           this.payload.rating > 0 &&
           !!this.payload.comments?.trim() &&
           !this.emailInvalid;
  }

  get ratingLabel(): string {
    const key = `feedback.rating_${this.payload.rating}`;
    return this.ts.translateInstant(key) || this.ts.translateInstant('feedback.rating_0');
  }

  ngAfterViewInit(): void {
    if (typeof this.dialogElRef.nativeElement.showModal === 'function') {
      this.dialogElRef.nativeElement.showModal();
    }
    this.dialogElRef.nativeElement.querySelector<HTMLInputElement>('#fb-name')?.focus();
  }

  /** Radio-group keyboard support: arrows move and select, Home/End jump (WAI-ARIA APG). */
  onStarKeydown(event: KeyboardEvent, star: number): void {
    let next: number;
    switch (event.key) {
      case 'ArrowRight':
      case 'ArrowUp':
        next = Math.min(5, star + 1);
        break;
      case 'ArrowLeft':
      case 'ArrowDown':
        next = Math.max(1, star - 1);
        break;
      case 'Home':
        next = 1;
        break;
      case 'End':
        next = 5;
        break;
      default:
        return;
    }
    event.preventDefault();
    this.payload.rating = next;
    const inputs = this.dialogElRef.nativeElement.querySelectorAll<HTMLInputElement>('.stars input');
    inputs[next - 1]?.focus();
  }

  onOverlayClick(event: MouseEvent): void {
    if (event.target === this.dialogElRef.nativeElement) {
      this.onClose();
    }
  }

  onDialogKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && event.target === this.dialogElRef.nativeElement) {
      event.preventDefault();
      this.onClose();
    }
  }

  private focusFirstInvalid(): void {
    const root = this.dialogElRef.nativeElement;
    const target =
      (!this.payload.name?.trim() && root.querySelector<HTMLElement>('#fb-name')) ||
      (this.emailInvalid && root.querySelector<HTMLElement>('#fb-email')) ||
      (this.payload.rating === 0 && (root.querySelector<HTMLElement>('.stars input') || root.querySelector<HTMLElement>('.star-btn'))) ||
      (!this.payload.comments?.trim() && root.querySelector<HTMLElement>('#fb-comments'));
    if (target) target.focus();
  }

  onClose(): void {
    this.closed.emit();
  }

  onSubmit(): void {
    if (this.loading) return;
    if (!this.isValid) {
      this.showErrors = true;
      this.focusFirstInvalid();
      return;
    }

    this.loading = true;
    this.error = null;

    this.feedbackService.submit(this.payload).subscribe({
      next: () => {
        this.submitted = true;
        this.loading = false;
        this.changeDetector.markForCheck();
        setTimeout(() => this.onClose(), 1500);
      },
      error: () => {
        this.error = this.ts.translateInstant('feedback.error');
        this.loading = false;
        this.changeDetector.markForCheck();
      },
    });
  }
}
