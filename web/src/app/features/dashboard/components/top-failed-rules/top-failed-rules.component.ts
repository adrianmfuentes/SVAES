import { Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DecimalPipe } from '@angular/common';
import { FailedRule } from '../../services/dashboard.service';

@Component({
  selector: 'app-top-failed-rules',
  standalone: true,
  imports: [RouterLink, DecimalPipe],
  templateUrl: './top-failed-rules.component.html',
  styleUrls: ['./top-failed-rules.component.scss'],
})
export class TopFailedRulesComponent {
  @Input() rules: FailedRule[] = [];
  @Input() activePeriod = '30d';
  @Input() loading = false;
  @Input() error: string | null = null;
}
