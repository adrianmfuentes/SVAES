import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-not-found',
  standalone: true,
  imports: [RouterModule],
  template: `
    <div class="error-page">
      <code class="error-code">404</code>
      <h1 class="error-title">P&aacute;gina no encontrada</h1>
      <p class="error-text">
        La ruta solicitada no existe o ha sido movida.
      </p>
      <a routerLink="/" class="btn-primary">Volver al inicio</a>
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
export class NotFoundComponent {}
