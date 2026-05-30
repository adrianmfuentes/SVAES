import { Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { NgClass } from '@angular/common';
import { RecentRelease } from '../../services/dashboard.service';

@Component({
  selector: 'app-recent-releases-table',
  standalone: true,
  imports: [RouterLink, NgClass],
  templateUrl: './recent-releases-table.component.html',
  styleUrls: ['./recent-releases-table.component.scss'],
})
export class RecentReleasesTableComponent {
  @Input() releases: RecentRelease[] = [];
  @Input() loading = false;
  @Input() error: string | null = null;

  relativeDate(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
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
