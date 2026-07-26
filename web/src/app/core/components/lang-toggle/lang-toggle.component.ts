import { Component, Input, inject } from '@angular/core';
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

  get currentLang(): string {
    return this.ts.currentLang;
  }

  setLang(lang: string): void {
    if (lang === this.ts.currentLang) return;
    this.ts.loadTranslationsWithCache(lang).subscribe(() => {
      this.ts.setLanguage(lang);
    });
  }
}
