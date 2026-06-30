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

export interface LoginStep1Response {
  requires_2fa: boolean;
  totp_token?: string;
  access_token?: string;
  refresh_token?: string;
  token_type?: string;
  user_id?: string;
  role?: string;
}

export interface TotpSetupResponse {
  totp_uri: string;
  secret: string;
  qr_data_url: string;
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
      const decoded = atob(payload.replaceAll('-', '+').replaceAll('_', '/'));
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

  login(email: string, password: string): Observable<LoginStep1Response> {
    return this.http.post<LoginStep1Response>('/api/v1/auth/login', { email, password }).pipe(
      tap((response) => {
        if (!response.requires_2fa && response.access_token) {
          this.storeTokens(response, email);
        }
      }),
    );
  }

  storeTokens(response: LoginStep1Response, email: string): void {
    if (!response.access_token) return;
    _accessToken = response.access_token;
    localStorage.setItem(this.TOKEN_KEY, response.access_token);
    if (response.refresh_token) {
      localStorage.setItem(this.REFRESH_KEY, response.refresh_token);
    }
    const payload = this.decodeToken(response.access_token);
    const user: UserInfo = {
      id: payload?.sub ?? response.user_id ?? '',
      email: payload?.email ?? email,
      display_name: payload?.email ?? email,
      role: payload?.role ?? response.role ?? 'USER',
      organization_id: payload?.organization_id,
    };
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
  }

  verify2fa(totpToken: string, code: string): Observable<LoginStep1Response> {
    return this.http.post<LoginStep1Response>('/api/v1/auth/2fa/verify', {
      totp_token: totpToken,
      code,
    });
  }

  setup2fa(): Observable<TotpSetupResponse> {
    return this.http.get<TotpSetupResponse>('/api/v1/auth/2fa/setup');
  }

  enable2fa(code: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>('/api/v1/auth/2fa/enable', { code });
  }

  disable2fa(code: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>('/api/v1/auth/2fa/disable', { code });
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

  getOrganization(organizationId: string): Observable<Organization | null> {
    return this.http.get<Organization>(`/api/v1/organizations/${organizationId}`);
  }
}
