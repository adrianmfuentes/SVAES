import { Component, Input, inject } from '@angular/core';
import { TranslationService } from '../../i18n/translation.service';

@Component({
  selector: 'app-lang-toggle',
  standalone: true,
  template: `
    <div class="lt" [class.lt--dark]="theme === 'dark'" role="group" [attr.aria-label]="ts.translateInstant('common.language')">
      <button class="lt-btn" [class.lt-btn--on]="currentLang === 'es'"
              [attr.aria-label]="ts.translateInstant('a11y.lang_es')"
              [attr.aria-pressed]="currentLang === 'es'"
              (click)="setLang('es')">ES</button>
      <button class="lt-btn" [class.lt-btn--on]="currentLang === 'en'"
              [attr.aria-label]="ts.translateInstant('a11y.lang_en')"
              [attr.aria-pressed]="currentLang === 'en'"
              (click)="setLang('en')">EN</button>
    </div>
  `,
  styles: [`
    :host { display: inline-flex; }

    .lt {
      display: inline-flex;
      border-radius: var(--rounded-sm);
      background: var(--paper-secondary);
      border: 0.0625rem solid var(--border);
      padding: 0.125rem;
      gap: 0.125rem;
    }

    .lt--dark {
      background: rgba(246, 244, 240, 0.08);
      border-color: rgba(246, 244, 240, 0.12);
    }

    .lt-btn {
      font-family: var(--font-sans);
      font-size: 0.625rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      background: none;
      border: none;
      border-radius: 0.0625rem;
      padding: 0.1875rem 0.5rem;
      cursor: pointer;
      color: var(--muted);
      transition: color 0.12s ease, background-color 0.12s ease;
      line-height: 1.4;
    }

    .lt-btn--on {
      background: var(--surface-raised);
      color: var(--ink);
      box-shadow: 0 0.0625rem 0.125rem rgba(13, 15, 18, 0.08);
    }

    .lt-btn:not(.lt-btn--on):hover {
      color: var(--ink);
    }

    /* dark variant */
    .lt--dark .lt-btn {
      color: rgba(246, 244, 240, 0.4);
    }

    .lt--dark .lt-btn--on {
      background: rgba(246, 244, 240, 0.14);
      color: var(--paper);
      box-shadow: none;
    }

    .lt--dark .lt-btn:not(.lt-btn--on):hover {
      color: rgba(246, 244, 240, 0.75);
    }
  `],
})
export class LangToggleComponent {
  @Input() theme: 'dark' | 'light' = 'light';

  readonly ts = inject(TranslationService);

  get currentLang(): string {
    return this.ts.currentLang;
  }

  setLang(lang: string): void {
    if (lang === this.ts.currentLang) return;
    // Load translations FIRST, then emit the language change so the pipe
    // re-translates only after this.translations is already updated.
    this.ts.loadTranslationsWithCache(lang).subscribe(() => {
      this.ts.setLanguage(lang);
    });
  }
}
