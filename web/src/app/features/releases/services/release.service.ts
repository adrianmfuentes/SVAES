import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ReleaseDetail {
  id: string;
  name: string;
  version: string;
  description: string;
  status: string;
  project_id: string;
  profile_id: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  organization_id?: string;
  project_name?: string;
  organization_name?: string;
  pending_task_id?: string | null;
}

export interface VerificationProgress {
  current: number;
  total: number;
  stage: string;
  pct: number;
}

export interface Artifact {
  id: string;
  release_id: string;
  connector_instance_id: string;
  connector_implementation: string;
  artifact_type: string;
  external_ref: string;
  description?: string;
  metadata?: Record<string, unknown>;
  created_at?: string;
}

export interface RuleResult {
  rule_id: string;
  rule_name?: string;
  connector?: string;
  status?: string;
  result?: string;
  message?: string;
  evidence?: string;
  evidence_params?: Record<string, string | number>;
  severity?: string;
}

export interface VerificationResult {
  id: string;
  release_id: string;
  verdict: string;
  rule_results: RuleResult[];
  summary: Record<string, number> | string;
  profile_snapshot?: Record<string, unknown>;
  duration_ms: number;
  executed_at: string;
}

export interface ProfileRule {
  rule_template: string;
  connector_types: string[];
  connector_types_mode: string;
}

export interface BrowseItem {
  ref: string;
  title: string;
  subtitle: string;
}

export interface ReleaseSummary {
  id: string;
  name?: string;
  verdict: string;
  organization_id?: string;
  organization_name?: string;
  created_at: string;
  created_by?: string;
}

export interface ImportArtifactsRequest {
  artifacts: {
    connector_instance_id: string;
    connector_implementation: string;
    artifact_type: string;
    external_ref: string;
    description: string;
  }[];
}

export interface ReleaseEditable {
  id: string;
  name: string;
  version: string;
  description: string;
  project_id?: string;
}

export type ReleaseWriteRequest = Record<string, unknown>;

@Injectable({ providedIn: 'root' })
export class ReleaseService {
  private readonly http = inject(HttpClient);

  listAll(): Observable<ReleaseSummary[]> {
    return this.http.get<ReleaseSummary[]>('/api/v1/releases');
  }

  deleteRelease(id: string): Observable<unknown> {
    return this.http.delete(`/api/v1/releases/${id}`);
  }

  getRelease(id: string): Observable<ReleaseDetail> {
    return this.http.get<ReleaseDetail>(`/api/v1/releases/${id}`);
  }

  getReleaseForEdit(id: string): Observable<ReleaseEditable> {
    return this.http.get<ReleaseEditable>(`/api/v1/releases/${id}`);
  }

  updateRelease(id: string, body: ReleaseWriteRequest): Observable<{ id: string }> {
    return this.http.patch<{ id: string }>(`/api/v1/releases/${id}`, body);
  }

  createRelease(projectId: string, body: ReleaseWriteRequest): Observable<{ id: string; status: string }> {
    return this.http.post<{ id: string; status: string }>(`/api/v1/projects/${projectId}/releases`, body);
  }

  listArtifacts(id: string): Observable<Artifact[]> {
    return this.http.get<Artifact[]>(`/api/v1/releases/${id}/artifacts`);
  }

  getResults(id: string): Observable<VerificationResult[]> {
    return this.http.get<VerificationResult[]>(`/api/v1/releases/${id}/results`);
  }

  getResultDetail(id: string, resultId: string): Observable<VerificationResult> {
    return this.http.get<VerificationResult>(`/api/v1/releases/${id}/results/${resultId}`);
  }

  verify(id: string): Observable<{ task_id: string; status: string }> {
    return this.http.post<{ task_id: string; status: string }>(`/api/v1/releases/${id}/verify`, {});
  }

  cancel(id: string): Observable<{ cancelled: boolean }> {
    return this.http.post<{ cancelled: boolean }>(`/api/v1/releases/${id}/cancel`, {});
  }

  getTaskStatus(taskId: string): Observable<{ progress?: VerificationProgress }> {
    return this.http.get<{ progress?: VerificationProgress }>(`/api/v1/tasks/${taskId}`);
  }

  importArtifacts(id: string, body: ImportArtifactsRequest): Observable<unknown> {
    return this.http.post(`/api/v1/releases/${id}/artifacts/import`, body);
  }

  deleteArtifact(id: string, artifactId: string): Observable<unknown> {
    return this.http.delete(`/api/v1/releases/${id}/artifacts/${artifactId}`);
  }

  exportResultPdf(id: string, resultId: string, lang: string): Observable<Blob> {
    return this.http.get(
      `/api/v1/releases/${id}/results/${resultId}/export?format=pdf&lang=${lang}`,
      { responseType: 'blob' },
    );
  }

  getProfileRules(profileId: string): Observable<{ rules: ProfileRule[] }> {
    return this.http.get<{ rules: ProfileRule[] }>(`/api/v1/profiles/${profileId}`);
  }

  browseConnector(orgId: string, connectorId: string, q: string): Observable<BrowseItem[]> {
    return this.http.get<BrowseItem[]>(
      `/api/v1/organizations/${orgId}/connectors/${connectorId}/browse`,
      { params: q ? { q } : {} },
    );
  }
}
