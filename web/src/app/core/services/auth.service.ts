import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

let _accessToken: string | null = null;

export function setAccessToken(token: string): void {
  _accessToken = token;
}

export function getAccessToken(): string | null {
  return _accessToken;
}

export function clearAccessToken(): void {
  _accessToken = null;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
}

export interface UserInfo {
  id: string;
  email: string;
  display_name: string;
  role: string;
  organization_id?: string;
}

interface JwtPayload {
  sub: string;
  email?: string;
  role?: string;
  organization_id?: string;
  exp?: number;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  private readonly TOKEN_KEY = 'access_token';
  private readonly REFRESH_KEY = 'refresh_token';
  private readonly USER_KEY = 'user';

  decodeToken(token: string): JwtPayload | null {
    try {
      const payload = token.split('.')[1];
      const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
      return JSON.parse(decoded) as JwtPayload;
    } catch {
      return null;
    }
  }

  isAdmin(): boolean {
    const token = this.getToken();
    if (!token) return false;
    return this.decodeToken(token)?.role === 'ADMIN';
  }

  login(email: string, password: string, orgId?: string): Observable<LoginResponse> {
    return this.http
      .post<LoginResponse>('/api/v1/auth/login', { email, password })
      .pipe(
        tap((response) => {
          _accessToken = response.access_token;
          localStorage.setItem(this.TOKEN_KEY, response.access_token);
          localStorage.setItem(this.REFRESH_KEY, response.refresh_token);
          const payload = this.decodeToken(response.access_token);
          const user: UserInfo = {
            id: payload?.sub ?? '',
            email: payload?.email ?? email,
            display_name: payload?.email ?? email,
            role: payload?.role ?? 'USER',
            organization_id: payload?.organization_id ?? orgId,
          };
          localStorage.setItem(this.USER_KEY, JSON.stringify(user));
        }),
      );
  }

  logout(): void {
    _accessToken = null;
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.REFRESH_KEY);
    localStorage.removeItem(this.USER_KEY);
    this.router.navigate(['/']);
  }

  isAuthenticated(): boolean {
    return !!_accessToken || !!localStorage.getItem(this.TOKEN_KEY);
  }

  getToken(): string | null {
    return _accessToken ?? localStorage.getItem(this.TOKEN_KEY);
  }

  getUser(): UserInfo | null {
    const raw = localStorage.getItem(this.USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as UserInfo;
    } catch {
      return null;
    }
  }

  getUserRole(): string {
    const token = this.getToken();
    if (token) {
      const role = this.decodeToken(token)?.role;
      if (role) return role;
    }
    return this.getUser()?.role ?? '';
  }

  getOrganizations(): Observable<Organization[]> {
    return this.http.get<Organization[]>('/api/v1/organizations');
  }
}
