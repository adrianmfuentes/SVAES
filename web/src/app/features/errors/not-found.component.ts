import { Component, inject } from '@angular/core';
import { RouterModule } from '@angular/router';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { TranslationService } from '../../core/i18n/translation.service';

@Component({
  selector: 'app-not-found',
  standalone: true,
  imports: [RouterModule, TranslatePipe],
  template: `
    <div class="error-page">
      <code class="error-code">{{ 'errors.404.title' | t }}</code>
      <h1 class="error-title">{{ 'errors.404.heading' | t }}</h1>
      <p class="error-text">
        {{ 'errors.404.message' | t }}
      </p>
      <a routerLink="/" class="btn-primary">{{ 'errors.404.home' | t }}</a>
    </div>
  `,
  styles: [`
    :host {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
      background: var(--paper);
    }

    .error-page {
      text-align: center;
      max-width: 28.75rem;
      padding: var(--spacing-xl);
    }

    .error-code {
      display: block;
      font-family: var(--font-mono);
      font-size: 6rem;
      font-weight: 400;
      line-height: 1;
      color: var(--border-strong);
      margin-bottom: var(--spacing-md);
    }

    .error-title {
      font-family: var(--font-display);
      font-size: 2.25rem;
      font-weight: 400;
      line-height: 1.1;
      letter-spacing: -0.02em;
      color: var(--ink);
      margin: 0 0 var(--spacing-sm);
    }

    .error-text {
      font-family: var(--font-sans);
      font-size: 0.9375rem;
      line-height: 1.65;
      color: var(--muted);
      margin: 0 0 var(--spacing-xl);
    }

    .btn-primary {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: var(--ink);
      color: var(--paper);
      border: 0.0625rem solid var(--ink);
      border-radius: var(--rounded-md);
      padding: 0.5625rem 1.125rem;
      font-family: var(--font-sans);
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      cursor: pointer;
      text-decoration: none;
      transition: background-color 0.15s ease;
    }

    .btn-primary:hover { background: var(--ink-secondary); }

    @media (max-width: 48rem) {
      .error-page { padding: var(--spacing-xl) var(--spacing-md); }
      .error-code { font-size: 4rem; }
      .error-title { font-size: 1.75rem; }
    }
  `],
})
export class NotFoundComponent {
  private readonly ts = inject(TranslationService);
}
