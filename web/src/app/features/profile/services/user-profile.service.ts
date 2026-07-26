import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  is_active: boolean;
  expires_at: string | null;
  created_at: string;
  last_used_at: string | null;
}

export interface UserProfile {
  id: string;
  email: string;
  display_name: string;
  role: string;
  totp_enabled?: boolean;
}

export interface UserNotificationPreferences {
  release_validated: boolean;
  release_invalidated: boolean;
  release_pending_reminder: boolean;
  weekly_digest: boolean;
}

export interface OrganizationSummary {
  id: string;
  name: string;
  slug: string;
}

export interface OrganizationOwnerInfo {
  owner_id: string;
}

export interface OrganizationUserSummary {
  id: string;
}

export interface UpdateProfileRequest {
  display_name?: string | null;
}

export interface ChangePasswordRequest {
  current_password?: string | null;
  new_password?: string | null;
  confirm_password?: string | null;
}

export interface CreateOrganizationRequest {
  name?: string | null;
  slug?: string | null;
}

@Injectable({ providedIn: 'root' })
export class UserProfileService {
  private readonly http = inject(HttpClient);

  getMe(): Observable<UserProfile> {
    return this.http.get<UserProfile>('/api/v1/users/me');
  }

  updateMe(data: UpdateProfileRequest): Observable<UserProfile> {
    return this.http.patch<UserProfile>('/api/v1/users/me', data);
  }

  changePassword(body: ChangePasswordRequest): Observable<unknown> {
    return this.http.post('/api/v1/users/me/password', body);
  }

  createOrganization(data: CreateOrganizationRequest): Observable<OrganizationSummary> {
    return this.http.post<OrganizationSummary>('/api/v1/organizations', data);
  }

  listApiKeys(userId: string): Observable<ApiKey[]> {
    return this.http.get<ApiKey[]>(`/api/v1/users/${userId}/api-keys`);
  }

  createApiKey(userId: string, body: Record<string, unknown>): Observable<ApiKey & { key: string }> {
    return this.http.post<ApiKey & { key: string }>(`/api/v1/users/${userId}/api-keys`, body);
  }

  revokeApiKey(userId: string, keyId: string): Observable<unknown> {
    return this.http.delete(`/api/v1/users/${userId}/api-keys/${keyId}`);
  }

  getOrganization(orgId: string): Observable<OrganizationOwnerInfo> {
    return this.http.get<OrganizationOwnerInfo>(`/api/v1/organizations/${orgId}`);
  }

  listOrganizationUsers(orgId: string): Observable<OrganizationUserSummary[]> {
    return this.http.get<OrganizationUserSummary[]>(`/api/v1/organizations/${orgId}/users`);
  }

  deleteAccount(password: string | null | undefined): Observable<unknown> {
    return this.http.delete('/api/v1/users/me/account', { body: { password } });
  }

  exportUserData(): Observable<object> {
    return this.http.get<object>('/api/v1/users/me/export');
  }

  getNotificationPreferences(): Observable<UserNotificationPreferences> {
    return this.http.get<UserNotificationPreferences>('/api/v1/notifications/preferences');
  }

  updateNotificationPreference(patch: Partial<UserNotificationPreferences>): Observable<unknown> {
    return this.http.patch('/api/v1/notifications/preferences', patch);
  }
}
