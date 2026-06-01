import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { forkJoin, Observable, of } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs/operators';

export interface DashboardMetrics {
  total_releases: number;
  valid_releases: number;
  invalid_releases: number;
  pending_releases: number;
  total_verifications: number;
  pass_rate: number;
}

export interface Project {
  id: string;
  name: string;
}

export interface RecentRelease {
  id: string;
  name?: string;
  version?: string;
  status?: string;
  verdict?: string;
  created_at: string;
  project_name?: string;
}

// Kept for sub-component type compatibility — backend does not provide these
export interface TemporalPoint { date: string; valid: number; with_warnings: number; invalid: number; }
export interface FailedRule { rule_id: string; rule_name: string; count: number; percentage: number; }

@Injectable({ providedIn: 'root' })
export class DashboardService {
  private readonly http = inject(HttpClient);

  getMetrics(): Observable<DashboardMetrics> {
    return this.http.get<DashboardMetrics>('/api/v1/dashboard/metrics');
  }

  getProjects(): Observable<Project[]> {
    return this.http.get<Project[]>('/api/v1/projects').pipe(
      catchError(() => of([] as Project[]))
    );
  }

  getRecentReleases(): Observable<RecentRelease[]> {
    return this.getProjects().pipe(
      switchMap(projects => {
        if (!projects.length) return of([] as RecentRelease[]);
        const calls = projects.slice(0, 5).map(p =>
          this.http.get<RecentRelease[]>(`/api/v1/projects/${p.id}/releases`).pipe(
            map(releases => releases.map(r => ({ ...r, project_name: p.name }))),
            catchError(() => of([] as RecentRelease[]))
          )
        );
        return forkJoin(calls).pipe(
          map(all =>
            all.flat()
              .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
              .slice(0, 10)
          )
        );
      }),
      catchError(() => of([] as RecentRelease[]))
    );
  }
}
