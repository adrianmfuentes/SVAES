import { Component, ElementRef, signal, viewChild } from '@angular/core';
import { RouterModule } from '@angular/router';
import { TranslatePipe } from '../../i18n/translate.pipe';
import { FeedbackModalComponent } from '../../../features/landing/feedback-modal/feedback-modal.component';

interface FooterSection {
  readonly id: string;
  readonly labelKey: string;
}

/** Footer shared by every public page: site map, account, project, legal links, glossary. */
@Component({
  selector: 'app-site-footer',
  standalone: true,
  imports: [RouterModule, TranslatePipe, FeedbackModalComponent],
  templateUrl: './site-footer.component.html',
  styleUrl: './site-footer.component.scss',
})
export class SiteFooterComponent {
  readonly showFeedback = signal(false);
  private readonly glossaryEl = viewChild<ElementRef<HTMLDialogElement>>('glossaryEl');

  readonly sections: readonly FooterSection[] = [
    { id: 'que-hace', labelKey: 'landing.nav_product' },
    { id: 'investigacion', labelKey: 'landing.nav_research' },
  ];

  readonly glossary: readonly string[] = ['rv', 'api', 'csv', 'pdf', 'tfg', 'tfm'];

  private get reduceMotion(): boolean {
    return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? true;
  }

  /**
   * On the home page, scroll smoothly and move focus to the section heading.
   * On any other page, let the router navigate to `/#section` (anchor scrolling does the rest).
   */
  goToSection(id: string, event: Event): void {
    if (window.location.pathname !== '/') return;
    const target = document.getElementById(id);
    if (!target) return;
    event.preventDefault();
    target.scrollIntoView({ behavior: this.reduceMotion ? 'auto' : 'smooth', block: 'start' });
    target.focus({ preventScroll: true });
    history.replaceState(null, '', `#${id}`);
  }

  scrollToTop(event: Event): void {
    event.preventDefault();
    window.scrollTo({ top: 0, behavior: this.reduceMotion ? 'auto' : 'smooth' });
    const main = document.querySelector<HTMLElement>('main');
    main?.focus({ preventScroll: true });
  }

  openFeedback(): void {
    this.showFeedback.set(true);
    document.body.style.overflow = 'hidden';
  }

  closeFeedback(): void {
    this.showFeedback.set(false);
    document.body.style.overflow = '';
  }

  openGlossary(): void {
    const dialog = this.glossaryEl()?.nativeElement;
    if (dialog && typeof dialog.showModal === 'function' && !dialog.open) dialog.showModal();
  }

  closeGlossary(): void {
    const dialog = this.glossaryEl()?.nativeElement;
    if (dialog && typeof dialog.close === 'function') dialog.close();
  }

  /** A click on the backdrop (the dialog element itself) closes it. */
  onGlossaryClick(event: MouseEvent): void {
    if (event.target === event.currentTarget) this.closeGlossary();
  }

  /** Keyboard support: backdrop click equivalent or Escape. */
  onGlossaryKeydown(event: KeyboardEvent): void {
    if (event.key === 'Escape' || (event.key === 'Enter' && event.target === event.currentTarget)) {
      this.closeGlossary();
    }
  }
}
