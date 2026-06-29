import { AfterViewInit, Component, ElementRef, ViewChild, inject } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { LangToggleComponent } from '../../core/components/lang-toggle/lang-toggle.component';
import { FeedbackModalComponent } from './feedback-modal/feedback-modal.component';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterModule, TranslatePipe, LangToggleComponent, FeedbackModalComponent],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss',
})
export class LandingComponent implements AfterViewInit {
  private readonly router = inject(Router);

  @ViewChild('accessInner') private readonly accessInnerRef!: ElementRef<HTMLElement>;

  showFeedback = false;

  navigateToRequestAccess(): void {
    this.router.navigate(['/request-access']);
  }

  openFeedback(): void {
    this.showFeedback = true;
    document.body.style.overflow = 'hidden';
  }

  closeFeedback(): void {
    this.showFeedback = false;
    document.body.style.overflow = '';
  }

  ngAfterViewInit(): void {
    const el = this.accessInnerRef?.nativeElement;
    if (!el || typeof IntersectionObserver === 'undefined') {
      el?.classList.add('is-visible');
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.disconnect();
        }
      },
      { threshold: 0.15 },
    );

    observer.observe(el);
  }
}
