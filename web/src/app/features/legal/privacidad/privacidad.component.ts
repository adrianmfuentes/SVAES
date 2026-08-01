import { Component, OnInit, inject } from '@angular/core';
import { RouterModule } from '@angular/router';
import { TranslatePipe } from '../../../core/i18n/translate.pipe';
import { LangToggleComponent } from '../../../core/components/lang-toggle/lang-toggle.component';
import { SeoService } from '../../../core/services/seo.service';

@Component({
  selector: 'app-privacidad',
  standalone: true,
  imports: [RouterModule, TranslatePipe, LangToggleComponent],
  templateUrl: './privacidad.component.html',
  styleUrl: './privacidad.component.scss',
})
export class PrivacidadComponent implements OnInit {
  private readonly seo = inject(SeoService);

  ngOnInit(): void {
    this.seo.setPage({
      title: 'Política de Privacidad',
      description: 'Política de privacidad y protección de datos de SVAES, sistema de verificación automática de entregas.',
      path: '/legal/privacidad',
    });
  }
}
