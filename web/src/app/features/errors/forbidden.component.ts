import { Component, inject, OnInit } from '@angular/core';
import { RouterModule } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { TranslationService } from '../../core/i18n/translation.service';
import { SeoService } from '../../core/services/seo.service';

@Component({
  selector: 'app-forbidden',
  standalone: true,
  imports: [RouterModule, TranslatePipe],
  templateUrl: './forbidden.component.html',
  styleUrls: ['./forbidden.component.scss'],
})
export class ForbiddenComponent implements OnInit {
  private readonly ts = inject(TranslationService);
  private readonly authService = inject(AuthService);
  private readonly seo = inject(SeoService);
  readonly isAdmin = this.authService.isAdmin();

  ngOnInit(): void {
    this.seo.setNoIndex(this.ts.translateInstant('errors.403.heading'));
  }
}
