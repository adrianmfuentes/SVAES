import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';
import { TranslatePipe } from '../../../core/i18n/translate.pipe';
import { LangToggleComponent } from '../../../core/components/lang-toggle/lang-toggle.component';

@Component({
  selector: 'app-aviso-legal',
  standalone: true,
  imports: [RouterModule, TranslatePipe, LangToggleComponent],
  templateUrl: './aviso-legal.component.html',
  styleUrl: './aviso-legal.component.scss',
})
export class AvisoLegalComponent {}
