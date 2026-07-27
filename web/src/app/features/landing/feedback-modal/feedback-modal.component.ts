import { AfterViewInit, Component, ElementRef, ViewChild, inject, output } from '@angular/core';
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
  error: string | null = null;

  get isValid(): boolean {
    return !!this.payload.name?.trim() &&
           this.payload.rating > 0 &&
           !!this.payload.comments?.trim();
  }

  get ratingLabel(): string {
    const key = `feedback.rating_${this.payload.rating}`;
    return this.ts.translateInstant(key) || this.ts.translateInstant('feedback.rating_0');
  }

  ngAfterViewInit(): void {
    if (typeof this.dialogElRef.nativeElement.showModal === 'function') {
      this.dialogElRef.nativeElement.showModal();
    }
  }

  onOverlayClick(event: MouseEvent): void {
    if (event.target === this.dialogElRef.nativeElement) {
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
        this.error = this.ts.translateInstant('feedback.error');
        this.loading = false;
      },
    });
  }
}
