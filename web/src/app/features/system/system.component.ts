import { Component, inject, OnInit, OnDestroy, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { RouterModule } from '@angular/router';
import { catchError, forkJoin, map, of, interval, Subscription, Observable } from 'rxjs';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';

interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

interface Org {
  id: string;
  name: string;
  slug: string;
}

interface AdminUser {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
}

type ServiceStatus = 'up' | 'down' | 'unknown';

interface RulesReloadResult {
  success: boolean;
  rules_loaded: number;
  message: string;
}

interface ServiceCard {
  name: string;
  status: ServiceStatus;
  detail?: string;
}

interface ProbeResult<T> {
  data: T | null;
  ok: boolean;
}

@Component({
  selector: 'app-system',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslatePipe],
  templateUrl: './system.component.html',
  styleUrls: ['./system.component.scss'],
})
export class SystemComponent implements OnInit, OnDestroy {
  private readonly http = inject(HttpClient);
  readonly ts = inject(TranslationService);

  loading = signal(true);
  apiVersion = signal<string | null>(null);
  services = signal<ServiceCard[]>([]);
  orgs = signal<Org[]>([]);
  users = signal<AdminUser[]>([]);

  reloading = signal(false);
  confirmingReload = signal(false);
  reloadResult = signal<RulesReloadResult | null>(null);
  reloadError = signal<string | null>(null);

  activeUserCount = computed(() => this.users().filter(u => u.is_active).length);

  anonymizedOrgs = computed(() =>
    this.orgs().map(org => ({
      ...org,
      name: `Organization ${this.simpleHash(org.id)}`,
    }))
  );

  secondsSince = signal(0);
  private lastRefresh = Date.now();
  private timerSub?: Subscription;

  ngOnInit(): void {
    this.loadAll();
    this.timerSub = interval(1000).subscribe(() =>
      this.secondsSince.set(Math.floor((Date.now() - this.lastRefresh) / 1000))
    );
  }

  ngOnDestroy(): void {
    this.timerSub?.unsubscribe();
  }

  loadAll(): void {
    this.loading.set(true);
    this.lastRefresh = Date.now();
    this.secondsSince.set(0);

    const probe = <T>(req: Observable<T>) =>
      req.pipe(map(d => ({ data: d, ok: true as const })),
               catchError(() => of({ data: null, ok: false as const })));

    forkJoin({
      health:    probe(this.http.get<HealthResponse>('/health')),
      orgs:      probe(this.http.get<Org[]>('/api/v1/organizations')),
      users:     probe(this.http.get<AdminUser[]>('/api/v1/admin/users?limit=200')),
      connTypes: probe(this.http.get<unknown[]>('/api/v1/connectors/types')),
    }).subscribe(({ health, orgs, users, connTypes }) => {
      const dataOk = orgs.ok || users.ok;

      this.apiVersion.set(health.data?.version ?? null);
      this.services.set(this.buildServiceCards(health, dataOk, connTypes));
      this.orgs.set(orgs.data ?? []);
      this.users.set(users.data ?? []);
      this.loading.set(false);
    });
  }

  private buildServiceCards(
    health: ProbeResult<HealthResponse>,
    dataOk: boolean,
    connTypes: ProbeResult<unknown[]>,
  ): ServiceCard[] {
    const apiUp = health.ok || dataOk;
    const dbUp = dataOk;
    const engUp = connTypes.ok;

    type Status = 'up' | 'unknown' | 'down';

    let dbStatus: Status;
    if (dbUp) {
      dbStatus = 'up';
    } else if (apiUp) {
      dbStatus = 'unknown';
    } else {
      dbStatus = 'down';
    }
    let engStatus: Status;
    if (engUp) {
      engStatus = 'up';
    } else if (apiUp) {
      engStatus = 'unknown';
    } else {
      engStatus = 'down';
    }
    const apiStatus: Status = apiUp ? 'up' : 'down';
    const redisStatus: Status = apiUp ? 'up' : 'unknown';

    return [
      { name: this.ts.translateInstant('system.service_api'), status: apiStatus, detail: this.apiDetail(health, dataOk) },
      { name: this.ts.translateInstant('system.service_db'), status: dbStatus, detail: this.dbDetail(dbUp, apiUp) },
      { name: this.ts.translateInstant('system.service_engine'), status: engStatus, detail: this.engineDetail(engUp, apiUp, connTypes) },
      { name: this.ts.translateInstant('system.service_redis'), status: redisStatus, detail: apiUp ? this.ts.translateInstant('system.detail_inferred') : this.ts.translateInstant('system.detail_not_verifiable') },
    ];
  }

  private apiDetail(health: ProbeResult<HealthResponse>, dataOk: boolean): string {
    if (health.ok) return `${health.data?.service ?? 'API'} v${health.data?.version ?? '?'}`;
    return dataOk ? this.ts.translateInstant('system.detail_responding') : this.ts.translateInstant('system.detail_no_response');
  }

  private dbDetail(dbUp: boolean, apiUp: boolean): string {
    if (dbUp) return this.ts.translateInstant('system.detail_accessible');
    return apiUp ? this.ts.translateInstant('system.detail_no_data') : this.ts.translateInstant('system.detail_inaccessible');
  }

  private engineDetail(engUp: boolean, apiUp: boolean, connTypes: ProbeResult<unknown[]>): string {
    if (engUp) {
      return Array.isArray(connTypes.data)
        ? this.ts.translateInstant('system.detail_types_loaded', { n: connTypes.data.length })
        : this.ts.translateInstant('system.detail_responding');
    }
    return apiUp ? this.ts.translateInstant('system.detail_no_data') : this.ts.translateInstant('system.detail_inaccessible');
  }

  executeReload(): void {
    this.reloading.set(true);
    this.reloadResult.set(null);
    this.reloadError.set(null);
    this.http.post<RulesReloadResult>('/api/v1/admin/rules/reload', {})
      .pipe(catchError((err: import('@angular/common/http').HttpErrorResponse) => {
        this.reloadError.set(err.error?.detail ?? this.ts.translateInstant('system.reload_error'));
        this.reloading.set(false);
        this.confirmingReload.set(false);
        return of(null);
      }))
      .subscribe(result => {
        if (result) {
          this.reloadResult.set(result);
        }
        this.reloading.set(false);
        this.confirmingReload.set(false);
      });
  }

  statusLabel(status: ServiceStatus): string {
    const map: Record<ServiceStatus, string> = {
      up: this.ts.translateInstant('system.status_healthy'),
      down: this.ts.translateInstant('system.status_unhealthy'),
      unknown: this.ts.translateInstant('system.status_unknown'),
    };
    return map[status] ?? status;
  }

  maskId(id: string): string {
    if (!id || id.length < 8) return '••••••••';
    return id.slice(0, 6) + '••••' + id.slice(-4);
  }

  private simpleHash(input: string): string {
    let hash = 0;
    for (let i = 0; i < input.length; i++) {
      const char = input.codePointAt(i)!;
      hash = ((hash << 5) - hash) + char;
      hash = Math.trunc(hash);
    }
    return Math.abs(hash).toString(16).slice(0, 8).padStart(8, '0');
  }
}
