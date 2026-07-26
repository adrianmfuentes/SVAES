import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ConnectorApiItem {
  id: string;
  name: string;
  connector_type: string;
  connector_implementation: string;
  status: string;
  created_at: string;
  last_tested_at?: string;
  webhook_enabled?: boolean;
}

export interface ConfigSchemaOption {
  value: string;
  label: string;
}

export interface ConfigSchemaField {
  type: string;
  label: string;
  required: boolean;
  sensitive?: boolean;
  default?: string;
  options?: ConfigSchemaOption[];
}

export interface ConnectorImplementation {
  implementation: string;
  metadata: { name: string; description?: string };
  config_schema: Record<string, ConfigSchemaField>;
}

export interface ConnectorTypesResponse {
  implementations: ConnectorImplementation[];
  by_type: Record<string, ConnectorImplementation[]>;
}

export interface ConnectorUpdateRequest {
  name?: string | null;
  config: Record<string, string>;
}

export interface ConnectorCreateRequest {
  connector_type: string;
  connector_implementation: string;
  name: string;
  credentials: Record<string, string>;
}

export interface ConnectorWebhookResponse {
  id: string;
  webhook_enabled: boolean;
  webhook_secret: string | null;
}

@Injectable({ providedIn: 'root' })
export class ConnectorService {
  private readonly http = inject(HttpClient);

  list(orgId: string): Observable<ConnectorApiItem[]> {
    return this.http.get<ConnectorApiItem[]>(`/api/v1/organizations/${orgId}/connectors`);
  }

  listTypes(): Observable<ConnectorTypesResponse> {
    return this.http.get<ConnectorTypesResponse>('/api/v1/connectors/types');
  }

  update(orgId: string, connectorId: string, body: ConnectorUpdateRequest): Observable<ConnectorApiItem> {
    return this.http.patch<ConnectorApiItem>(`/api/v1/organizations/${orgId}/connectors/${connectorId}`, body);
  }

  create(orgId: string, body: ConnectorCreateRequest): Observable<ConnectorApiItem> {
    return this.http.post<ConnectorApiItem>(`/api/v1/organizations/${orgId}/connectors`, body);
  }

  toggle(orgId: string, connectorId: string, status: string): Observable<ConnectorApiItem> {
    return this.http.post<ConnectorApiItem>(`/api/v1/organizations/${orgId}/connectors/${connectorId}/toggle`, { status });
  }

  test(orgId: string, connectorId: string): Observable<ConnectorApiItem> {
    return this.http.post<ConnectorApiItem>(`/api/v1/organizations/${orgId}/connectors/${connectorId}/test`, {});
  }

  setWebhook(orgId: string, connectorId: string, enabled: boolean, regenerateSecret: boolean): Observable<ConnectorWebhookResponse> {
    return this.http.post<ConnectorWebhookResponse>(
      `/api/v1/organizations/${orgId}/connectors/${connectorId}/webhook`,
      { enabled, regenerate_secret: regenerateSecret },
    );
  }
}
