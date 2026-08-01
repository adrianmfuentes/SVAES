import { AfterViewInit, Component, ElementRef, OnInit, ViewChild, inject } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { LangToggleComponent } from '../../core/components/lang-toggle/lang-toggle.component';
import { FeedbackModalComponent } from './feedback-modal/feedback-modal.component';
import { SeoService } from '../../core/services/seo.service';

@Component({
  selector: 'app-landing',
  standalone: true,
  imports: [RouterModule, TranslatePipe, LangToggleComponent, FeedbackModalComponent],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.scss',
})
export class LandingComponent implements OnInit, AfterViewInit {
  private readonly router = inject(Router);
  private readonly seo = inject(SeoService);

  @ViewChild('accessInner') private readonly accessInnerRef!: ElementRef<HTMLElement>;

  showFeedback = false;

  ngOnInit(): void {
    this.seo.setPage({
      title: 'SVAES — Verificación Automática de Entregas',
      description:
        'Conecte sus herramientas de desarrollo, defina reglas de verificación y obtenga trazabilidad completa de cada release. Infraestructura honesta para equipos que operan con exigencia.',
      path: '/',
    });
  }

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
