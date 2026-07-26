import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface OrgUser {
  id: string;
  email: string;
  display_name: string;
  role: 'OPERATOR' | 'ADMIN' | 'MANAGER';
  is_active: boolean;
}

export interface InviteMemberRequest {
  email: string;
  role: 'OPERATOR' | 'MANAGER';
}

export interface TransferOwnershipRequest {
  new_owner_id: string;
}

@Injectable({ providedIn: 'root' })
export class OrgService {
  private readonly http = inject(HttpClient);

  listMembers(orgId: string): Observable<OrgUser[]> {
    return this.http.get<OrgUser[]>(`/api/v1/organizations/${orgId}/users`);
  }

  inviteMember(orgId: string, body: InviteMemberRequest): Observable<unknown> {
    return this.http.post(`/api/v1/organizations/${orgId}/users/invite`, body);
  }

  removeMember(orgId: string, userId: string): Observable<unknown> {
    return this.http.delete(`/api/v1/organizations/${orgId}/users/${userId}`);
  }

  transferOwnership(orgId: string, body: TransferOwnershipRequest): Observable<unknown> {
    return this.http.post(`/api/v1/organizations/${orgId}/transfer-ownership`, body);
  }
}
