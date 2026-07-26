import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Project {
  id: string;
  name: string;
  description: string;
  profile_id: string | null;
  is_archived: boolean;
  created_at: string | null;
}

export interface ProjectProfile {
  id: string;
  name: string;
  is_system?: boolean;
  is_default?: boolean;
}

export interface ProjectUpdateRequest {
  name: string;
  description: string;
  profile_id: string | null;
}

export interface ProjectCreateRequest {
  name: string | null | undefined;
  description: string;
  profile_id: string | null | undefined;
}

export interface ProjectOption {
  id: string;
  name: string;
}

@Injectable({ providedIn: 'root' })
export class ProjectService {
  private readonly http = inject(HttpClient);

  list(orgId: string): Observable<Project[]> {
    return this.http.get<Project[]>(`/api/v1/organizations/${orgId}/projects`);
  }

  listAccessible(): Observable<ProjectOption[]> {
    return this.http.get<ProjectOption[]>('/api/v1/projects');
  }

  archive(orgId: string, projectId: string): Observable<unknown> {
    return this.http.post(`/api/v1/organizations/${orgId}/projects/${projectId}/archive`, {});
  }

  unarchive(orgId: string, projectId: string): Observable<unknown> {
    return this.http.post(`/api/v1/organizations/${orgId}/projects/${projectId}/unarchive`, {});
  }

  listProfiles(orgId: string): Observable<ProjectProfile[]> {
    return this.http.get<ProjectProfile[]>(`/api/v1/organizations/${orgId}/profiles`);
  }

  create(orgId: string, body: ProjectCreateRequest): Observable<{ id: string }> {
    return this.http.post<{ id: string }>(`/api/v1/organizations/${orgId}/projects`, body);
  }

  update(projectId: string, body: ProjectUpdateRequest): Observable<Project> {
    return this.http.patch<Project>(`/api/v1/projects/${projectId}`, body);
  }
}
