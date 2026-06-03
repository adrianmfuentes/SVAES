import { Component, inject } from '@angular/core';
import { RouterModule } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { TranslationService } from '../../core/i18n/translation.service';

@Component({
  selector: 'app-forbidden',
  standalone: true,
  imports: [RouterModule, TranslatePipe],
  template: `
    <div class="error-page">
      <code class="error-code">{{ 'errors.403.title' | t }}</code>
      <h1 class="error-title">{{ 'errors.403.heading' | t }}</h1>
      <p class="error-text">
        {{ 'errors.403.message' | t }}
      </p>
      @if (isAdmin) {
        <a routerLink="/app/system" class="btn-primary">{{ 'errors.403.system' | t }}</a>
      } @else {
        <a routerLink="/app/dashboard" class="btn-primary">{{ 'errors.403.dashboard' | t }}</a>
      }
    </div>
  `,
  styles: [`
    :host {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: calc(100vh - 80px);
    }

    .error-page {
      text-align: center;
      max-width: 460px;
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
      border: 1px solid var(--ink);
      border-radius: var(--rounded-md);
      padding: 9px 18px;
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
  `],
})
export class ForbiddenComponent {
  private readonly ts = inject(TranslationService);
  private readonly authService = inject(AuthService);
  readonly isAdmin = this.authService.isAdmin();
}
