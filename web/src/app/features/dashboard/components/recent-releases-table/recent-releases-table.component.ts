import { Component, Input, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { NgClass } from '@angular/common';
import { RecentRelease } from '../../services/dashboard.service';
import { TranslatePipe } from '../../../../core/i18n/translate.pipe';
import { TranslationService } from '../../../../core/i18n/translation.service';

@Component({
  selector: 'app-recent-releases-table',
  standalone: true,
  imports: [RouterLink, NgClass, TranslatePipe],
  templateUrl: './recent-releases-table.component.html',
  styleUrls: ['./recent-releases-table.component.scss'],
})
export class RecentReleasesTableComponent {
  private readonly ts = inject(TranslationService);

  @Input() releases: RecentRelease[] = [];
  @Input() loading = false;
  @Input() error: string | null = null;

  relativeDate(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return this.ts.translateInstant('releases.relative_just_now');
    if (mins < 60) return this.ts.translateInstant('releases.relative_minutes', { n: mins });
    const hours = Math.floor(mins / 60);
    if (hours < 24) return this.ts.translateInstant('releases.relative_hours', { n: hours });
    return this.ts.translateInstant('releases.relative_days', { n: Math.floor(hours / 24) });
  }

  verdictClass(verdict = ''): Record<string, boolean> {
    return {
      'badge--valid': verdict === 'VALID',
      'badge--warning': verdict === 'WITH_WARNINGS',
      'badge--invalid': verdict === 'INVALID',
      'badge--unevaluated': !verdict || verdict === 'NOT_EVALUATED',
    };
  }

  shortId(id: string): string {
    return id.slice(0, 8);
  }
}
