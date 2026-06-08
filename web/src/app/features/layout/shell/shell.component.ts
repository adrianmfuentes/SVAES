import { Component, inject } from '@angular/core';
import { RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../../core/services/auth.service';
import { TranslationService } from '../../../core/i18n/translation.service';
import { TranslatePipe } from '../../../core/i18n/translate.pipe';
import { LangToggleComponent } from '../../../core/components/lang-toggle/lang-toggle.component';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslatePipe, LangToggleComponent],
  templateUrl: './shell.component.html',
  styleUrl: './shell.component.scss',
})
export class ShellComponent {
  readonly authService = inject(AuthService);
  private readonly ts = inject(TranslationService);

  get isAdmin(): boolean {
    return this.authService.isAdmin();
  }

  get isManager(): boolean {
    return this.authService.getUserRole() === 'MANAGER';
  }

  get displayName(): string {
    const user = this.authService.getUser();
    return user?.display_name || user?.email || '';
  }

  get roleLabel(): string {
    const role = this.authService.getUserRole();
    const map: Record<string, string> = {
      ADMIN: this.ts.translateInstant('shell.role_admin'),
      MANAGER: this.ts.translateInstant('shell.role_manager'),
      OPERATOR: this.ts.translateInstant('shell.role_operator'),
      VIEWER: this.ts.translateInstant('shell.role_viewer'),
    };
    return map[role] ?? role;
  }

  logout(): void {
    this.authService.logout();
  }
}
