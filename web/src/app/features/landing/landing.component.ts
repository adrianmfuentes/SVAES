import { AfterViewInit, Component, ElementRef, ViewChild, inject } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { LangToggleComponent } from '../../core/components/lang-toggle/lang-toggle.component';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterModule, TranslatePipe, LangToggleComponent],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss',
})
export class LandingComponent implements AfterViewInit {
  private readonly router = inject(Router);

  @ViewChild('accessInner') private accessInnerRef!: ElementRef<HTMLElement>;

  navigateToRequestAccess(): void {
    this.router.navigate(['/request-access']);
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
