import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export type SeverityType = 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface Profile {
  id: string;
  name: string;
  description?: string;
  rules_count?: number;
  organization_id?: string;
  organization_name?: string;
  is_template?: boolean;
  is_default?: boolean;
  is_system?: boolean;
  created_at?: string;
  schedule?: string | null;
  schedule_last_run_at?: string | null;
}

export interface ProfileRule {
  id: string;
  rule_template: string;
  severity: SeverityType;
  connector_instance_id?: string;
  params: Record<string, unknown>;
  display_order: number;
  is_active: boolean;
  connector_types: string[];
}

export interface ProfileWithRules extends Profile {
  rules: ProfileRule[];
}

export interface UpdateRuleRequest {
  severity?: SeverityType | null;
  params: Record<string, unknown>;
}

export interface UpdateRuleResponse {
  id: string;
  is_active: boolean;
}

export interface AddRuleRequest {
  rule_template: string;
  severity?: SeverityType | null;
  params: Record<string, unknown>;
}

export interface AddRuleResponse {
  id: string;
  rule_template: string;
}

export interface UpdateProfileRequest {
  name: string;
  description: string;
  schedule: string;
}

export interface CreateProfileRequest {
  name: string;
  description: string;
  is_default: boolean;
}

@Injectable({ providedIn: 'root' })
export class ProfileService {
  private readonly http = inject(HttpClient);

  listProfiles(orgId: string): Observable<Profile[]> {
    return this.http.get<Profile[]>(`/api/v1/organizations/${orgId}/profiles`);
  }

  getProfileWithRules(profileId: string): Observable<ProfileWithRules> {
    return this.http.get<ProfileWithRules>(`/api/v1/profiles/${profileId}`);
  }

  updateRule(ruleId: string, body: UpdateRuleRequest): Observable<UpdateRuleResponse> {
    return this.http.patch<UpdateRuleResponse>(`/api/v1/rules/${ruleId}`, body);
  }

  addRule(profileId: string, body: AddRuleRequest): Observable<AddRuleResponse> {
    return this.http.post<AddRuleResponse>(`/api/v1/profiles/${profileId}/rules`, body);
  }

  deleteRule(ruleId: string): Observable<unknown> {
    return this.http.delete(`/api/v1/rules/${ruleId}`);
  }

  updateProfile(profileId: string, body: UpdateProfileRequest): Observable<Profile> {
    return this.http.patch<Profile>(`/api/v1/profiles/${profileId}`, body);
  }

  createProfile(orgId: string, body: CreateProfileRequest): Observable<Profile> {
    return this.http.post<Profile>(`/api/v1/organizations/${orgId}/profiles`, body);
  }

  deleteProfile(profileId: string): Observable<unknown> {
    return this.http.delete(`/api/v1/profiles/${profileId}`);
  }
}
