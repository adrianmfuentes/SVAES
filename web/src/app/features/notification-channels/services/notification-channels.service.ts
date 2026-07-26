import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ConfigSchemaField {
  type: string;
  label: string;
  required: boolean;
  sensitive?: boolean;
}

export interface ChannelTypesResponse {
  channel_types: string[];
  config_schemas: Record<string, Record<string, ConfigSchemaField>>;
}

export interface NotificationChannel {
  id: string | null;
  organization_id: string;
  channel_type: string;
  enabled: boolean;
  config_data: Record<string, unknown>;
  configured: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface SaveChannelBody {
  channel_type: string;
  enabled: boolean;
  config_data: Record<string, unknown>;
}

@Injectable({ providedIn: 'root' })
export class NotificationChannelsService {
  private readonly http = inject(HttpClient);

  getChannelTypes(): Observable<ChannelTypesResponse> {
    return this.http.get<ChannelTypesResponse>('/api/v1/notifications/channel-types');
  }

  getChannels(): Observable<NotificationChannel[]> {
    return this.http.get<NotificationChannel[]>('/api/v1/notifications/channels');
  }

  createChannel(body: SaveChannelBody): Observable<unknown> {
    return this.http.post('/api/v1/notifications/channels', body);
  }

  updateChannel(id: string | null, body: SaveChannelBody): Observable<unknown> {
    return this.http.patch(`/api/v1/notifications/channels/${id}`, body);
  }

  testChannel(id: string): Observable<{ delivered: boolean }> {
    return this.http.post<{ delivered: boolean }>(`/api/v1/notifications/channels/${id}/test`, {});
  }

  deleteChannel(id: string): Observable<unknown> {
    return this.http.delete(`/api/v1/notifications/channels/${id}`);
  }
}
