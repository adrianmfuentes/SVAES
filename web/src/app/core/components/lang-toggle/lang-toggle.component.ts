import { ApplicationRef, Component, Input, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { TranslationService } from '../../i18n/translation.service';

@Component({
  selector: 'app-lang-toggle',
  standalone: true,
  templateUrl: './lang-toggle.component.html',
  styleUrls: ['./lang-toggle.component.scss'],
})
export class LangToggleComponent {
  @Input() theme: 'dark' | 'light' = 'light';

  readonly ts = inject(TranslationService);
  private readonly appRef = inject(ApplicationRef);

  /** Reactive copy of the active language so the sliding thumb follows it under zoneless change detection. */
  private readonly lang = signal(this.ts.currentLang);

  constructor() {
    if (typeof this.ts.lang$?.pipe === 'function') {
      this.ts.lang$.pipe(takeUntilDestroyed()).subscribe((lang) => this.lang.set(lang));
    }
  }

  get currentLang(): string {
    this.lang(); // read the signal so the template re-renders on language change
    return this.ts.currentLang;
  }

  setLang(lang: string): void {
    if (lang === this.ts.currentLang) return;
    this.ts.loadTranslationsWithCache(lang).subscribe(() => {
      const apply = (): void => this.ts.setLanguage(lang);
      const root = document.documentElement;
      const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? true;

      if (reduceMotion) {
        apply();
        return;
      }

      // Fade the text out, swap the strings while it is invisible, fade it back in.
      // Opacity only: no transforms, so nothing appears to move while the layout settles.
      root.classList.add('lang-switching');
      setTimeout(async () => {
        apply();
        await this.appRef.whenStable();
        requestAnimationFrame(() => root.classList.remove('lang-switching'));
      }, 170);
    });
  }
}
