import { DestroyRef, afterNextRender, inject, signal } from '@angular/core';

/**
 * In-page table of contents for the legal documents: smooth scroll without reloading the page,
 * focus moved to the target (WCAG 2.4.3), and the section being read marked as current.
 */
export abstract class TocNavigation {
  private readonly destroyRef = inject(DestroyRef);

  readonly active = signal<string | null>(null);

  constructor() {
    afterNextRender(() => {
      if (typeof IntersectionObserver === 'undefined') return;
      const sections = Array.from(document.querySelectorAll<HTMLElement>('.legal-section[id]'));
      const observer = new IntersectionObserver(
        (entries) => {
          for (const entry of entries) {
            if (entry.isIntersecting) this.active.set(entry.target.id);
          }
        },
        { rootMargin: '-20% 0px -65% 0px' },
      );
      sections.forEach((s) => observer.observe(s));
      this.destroyRef.onDestroy(() => observer.disconnect());
    });
  }

  goTo(id: string, event: Event): void {
    event.preventDefault();
    const target = document.getElementById(id);
    if (!target) return;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? true;
    target.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
    target.setAttribute('tabindex', '-1');
    target.focus({ preventScroll: true });
    this.active.set(id);
    // <base href="/"> would resolve a bare "#id" against the site root, so keep the path.
    history.replaceState(null, '', `${location.pathname}#${id}`);
  }
}
