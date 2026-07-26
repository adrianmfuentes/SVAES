import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Org {
  id: string;
  name: string;
  slug: string;
}

export interface GlobalUser {
  id: string;
  email: string;
  display_name: string;
  role: string;
  is_active: boolean;
}

export type AccessRequestStatus = 'PENDING' | 'APPROVED' | 'REJECTED';

export interface AccessRequest {
  id: string;
  requester_name: string;
  requester_email: string;
  organization_name: string;
  organization_description?: string;
  slug_preview?: string;
  status: AccessRequestStatus;
  created_at?: string;
  rejection_reason?: string;
}

@Injectable({ providedIn: 'root' })
export class AdminService {
  private readonly http = inject(HttpClient);

  getOrganizations(): Observable<Org[]> {
    return this.http.get<Org[]>('/api/v1/organizations');
  }

  getUsers(): Observable<GlobalUser[]> {
    return this.http.get<GlobalUser[]>('/api/v1/admin/users?limit=200');
  }

  getAccessRequests(status: AccessRequestStatus): Observable<AccessRequest[]> {
    return this.http.get<AccessRequest[]>(`/api/v1/access-requests?status=${status}`);
  }
}
