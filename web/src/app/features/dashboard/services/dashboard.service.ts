import { Injectable, inject } from '@angular/core';
import { from, Observable } from 'rxjs';
import {
  getDashboardMetricsApiV1DashboardMetricsGet,
  listAccessibleProjectsApiV1ProjectsGet,
} from '../../../core/api';
import { client } from '../../../core/api/client.gen';
import { AuthService } from '../../../core/services/auth.service';

export interface TemporalPoint {
  date: string;
  valid: number;
  with_warnings: number;
  invalid: number;
}

export interface FailedRule {
  rule_id: string;
  rule_name: string;
  count: number;
  percentage: number;
}

export interface StatusDistribution {
  valid: number;
  with_warnings: number;
  invalid: number;
}

export interface DashboardMetrics {
  success_rate: number;
  total_releases: number;
  avg_validation_time_minutes: number;
  temporal_evolution: TemporalPoint[];
  top_failed_rules: FailedRule[];
  release_status_distribution: StatusDistribution;
}

export interface Project {
  id: string;
  name: string;
}

export interface RecentRelease {
  id: string;
  name: string;
  project_name?: string;
  verdict?: string;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private readonly authService = inject(AuthService);

  private get auth() {
    return () => this.authService.getToken() ?? undefined;
  }

  getMetrics(period: string, projectId: string): Observable<DashboardMetrics> {
    const query: Record<string, unknown> = {};
    if (period) query['period'] = period;
    if (projectId) query['project_id'] = projectId;

    return from(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      getDashboardMetricsApiV1DashboardMetricsGet({ query: query as any, auth: this.auth }).then(
        ({ data, error }) => {
          if (error) throw error;
          return data as DashboardMetrics;
        },
      ),
    );
  }

  getProjects(): Observable<Project[]> {
    return from(
      listAccessibleProjectsApiV1ProjectsGet({ auth: this.auth }).then(
        ({ data, error }) => {
          if (error) throw error;
          return (data as Project[]) ?? [];
        },
      ),
    );
  }

  getRecentReleases(): Observable<RecentRelease[]> {
    return from(
      client
        .get({
          url: '/api/v1/releases',
          query: { limit: 10, sort: 'created_at_desc' },
          auth: this.auth,
          security: [{ scheme: 'bearer', type: 'http' }],
        })
        .then(({ data, error }) => {
          if (error) throw error;
          return (data as RecentRelease[]) ?? [];
        }),
    );
  }
}
