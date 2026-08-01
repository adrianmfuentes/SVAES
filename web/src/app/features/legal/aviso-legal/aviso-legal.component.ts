import { Component, OnInit, inject } from '@angular/core';
import { RouterModule } from '@angular/router';
import { TranslatePipe } from '../../../core/i18n/translate.pipe';
import { LangToggleComponent } from '../../../core/components/lang-toggle/lang-toggle.component';
import { SeoService } from '../../../core/services/seo.service';

@Component({
  selector: 'app-aviso-legal',
  standalone: true,
  imports: [RouterModule, TranslatePipe, LangToggleComponent],
  templateUrl: './aviso-legal.component.html',
  styleUrl: './aviso-legal.component.scss',
})
export class AvisoLegalComponent implements OnInit {
  private readonly seo = inject(SeoService);

  ngOnInit(): void {
    this.seo.setPage({
      title: 'Aviso Legal',
      description: 'Aviso legal y condiciones de uso de SVAES, sistema de verificación automática de entregas.',
      path: '/legal/aviso-legal',
    });
  }
}
