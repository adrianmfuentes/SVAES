import { Component, inject, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { TranslationService } from './core/i18n/translation.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  template: '<router-outlet></router-outlet>',
  styles: [
    `:host { display: block; height: 100vh; }`,
  ],
})
export class App implements OnInit {
  private readonly ts = inject(TranslationService);

  ngOnInit(): void {
    this.updateHtmlLang(this.ts.currentLang);
    this.ts.lang$.subscribe(lang => this.updateHtmlLang(lang));
  }

  private updateHtmlLang(lang: string): void {
    document.documentElement.lang = lang;
  }
}
