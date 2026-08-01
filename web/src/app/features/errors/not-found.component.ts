import { Component, inject, OnInit } from '@angular/core';
import { RouterModule } from '@angular/router';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { TranslationService } from '../../core/i18n/translation.service';
import { SeoService } from '../../core/services/seo.service';

@Component({
  selector: 'app-not-found',
  standalone: true,
  imports: [RouterModule, TranslatePipe],
  templateUrl: './not-found.component.html',
  styleUrls: ['./not-found.component.scss'],
})
export class NotFoundComponent implements OnInit {
  private readonly ts = inject(TranslationService);
  private readonly seo = inject(SeoService);

  ngOnInit(): void {
    this.seo.setNoIndex(this.ts.translateInstant('errors.404.heading'));
  }
}
