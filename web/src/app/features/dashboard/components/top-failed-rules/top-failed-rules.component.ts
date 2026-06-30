import { Component, Input, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DecimalPipe } from '@angular/common';
import { FailedRule } from '../../services/dashboard.service';
import { TranslatePipe } from '../../../../core/i18n/translate.pipe';
import { TranslationService } from '../../../../core/i18n/translation.service';

@Component({
  selector: 'app-top-failed-rules',
  standalone: true,
  imports: [RouterLink, DecimalPipe, TranslatePipe],
  templateUrl: './top-failed-rules.component.html',
  styleUrls: ['./top-failed-rules.component.scss'],
})
export class TopFailedRulesComponent {
  private readonly ts = inject(TranslationService);

  @Input() rules: FailedRule[] = [];
  @Input() activePeriod = '30d';
  @Input() loading = false;
  @Input() error: string | null = null;

  translateRuleName(ruleId: string, ruleName: string): string {
    const translated = this.ts.translateInstant('rules.' + ruleId);
    if (translated && !translated.startsWith('rules.')) {
      return translated;
    }
    return ruleName;
  }
}
