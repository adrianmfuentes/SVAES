import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService } from '../../services/toast.service';
import { TranslationService } from '../../i18n/translation.service';

@Component({
  selector: 'app-toast',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './toast.component.html',
  styleUrls: ['./toast.component.scss'],
})
export class ToastComponent {
  readonly toastService = inject(ToastService);
  private readonly ts = inject(TranslationService);

  get dismissLabel(): string {
    return this.ts.translateInstant('a11y.dismiss_notification');
  }

  dismiss(id: number): void {
    this.toastService.dismiss(id);
  }
}
