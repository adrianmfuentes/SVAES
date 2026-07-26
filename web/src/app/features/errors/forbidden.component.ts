import { Component, inject } from '@angular/core';
import { RouterModule } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { TranslationService } from '../../core/i18n/translation.service';

@Component({
  selector: 'app-forbidden',
  standalone: true,
  imports: [RouterModule, TranslatePipe],
  templateUrl: './forbidden.component.html',
  styleUrls: ['./forbidden.component.scss'],
})
export class ForbiddenComponent {
  private readonly ts = inject(TranslationService);
  private readonly authService = inject(AuthService);
  readonly isAdmin = this.authService.isAdmin();
}
