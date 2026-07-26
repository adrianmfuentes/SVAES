import { Component, inject, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { catchError, of } from 'rxjs';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import {
  AccessRequest,
  AccessRequestStatus,
  AdminService,
  GlobalUser,
  Org,
} from './services/admin.service';

type AdminTab = 'organizations' | 'users' | 'access-requests';


@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, TranslatePipe],
  templateUrl: './admin.component.html',
  styleUrls: ['./admin.component.scss'],
})
export class AdminComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly authService = inject(AuthService);
  readonly ts = inject(TranslationService);

  readonly currentUserId = this.authService.getUser()?.id ?? '';

  get tabs(): { id: AdminTab; label: string }[] {
    return [
      { id: 'organizations', label: this.ts.translateInstant('admin.tab_organizations') },
      { id: 'users', label: this.ts.translateInstant('admin.tab_users') },
      { id: 'access-requests', label: this.ts.translateInstant('admin.access_requests_title') },
    ];
  }

  activeTab = signal<AdminTab>('organizations');

  // Organizations
  orgs = signal<Org[]>([]);
  orgsLoading = signal(true);
  orgsError = signal<string | null>(null);

  // Users
  users = signal<GlobalUser[]>([]);
  usersLoading = signal(true);
  usersError = signal<string | null>(null);

  // Access Requests
  accessRequests = signal<AccessRequest[]>([]);
  arLoading = signal(true);
  arError = signal<string | null>(null);
  arSuccess = signal<string | null>(null);
  arStatus = signal<AccessRequestStatus>('PENDING');
  get accessRequestStatuses(): { value: AccessRequestStatus; label: string }[] {
    return [
      { value: 'PENDING', label: this.ts.translateInstant('admin.tab_pending') },
      { value: 'APPROVED', label: this.ts.translateInstant('admin.tab_approved') },
      { value: 'REJECTED', label: this.ts.translateInstant('admin.tab_rejected') },
    ];
  }

  private simpleHash(input: string): string {
    let hash = 0;
    for (let i = 0; i < input.length; i++) {
      const char = input.codePointAt(i)!;
      hash = ((hash << 5) - hash) + char;
      hash = Math.trunc(hash);
    }
    return Math.abs(hash).toString(16).slice(0, 8).padStart(8, '0');
  }

  relativeDate(iso: string | undefined): string {
    if (!iso) return '';
    const d = new Date(iso);
    const now = Date.now();
    const diff = now - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return this.ts.translateInstant('releases.relative_just_now');
    if (mins < 60) return this.ts.translateInstant('releases.relative_minutes', { n: mins });
    const hours = Math.floor(mins / 60);
    if (hours < 24) return this.ts.translateInstant('releases.relative_hours', { n: hours });
    const days = Math.floor(hours / 24);
    if (days < 30) return this.ts.translateInstant('releases.relative_days', { n: days });
    return d.toLocaleDateString(this.ts.currentLang === 'en' ? 'en-GB' : 'es-ES', { month: 'short', day: 'numeric' });
  }


  private readonly loaded = new Set<AdminTab>();

  ngOnInit(): void {
    this.loadTab('organizations');
  }

  setTab(tab: AdminTab): void {
    this.activeTab.set(tab);
    this.loadTab(tab);
  }

  private loadTab(tab: AdminTab): void {
    if (this.loaded.has(tab)) return;
    this.loaded.add(tab);
    switch (tab) {
      case 'organizations': this.loadOrgs(); break;
      case 'users': this.loadUsers(); break;
      case 'access-requests': this.loadAccessRequests(); break;
    }
  }

  // -- Organizations --------------------------------------------─

  private loadOrgs(): void {
    this.orgsLoading.set(true);
    this.adminService.getOrganizations()
      .pipe(catchError(() => { this.orgsError.set(this.ts.translateInstant('admin.loading_orgs_error')); return of([]); }))
      .subscribe(data => {
        const anonymized = data.map(org => ({
          ...org,
          name: `Organization ${this.simpleHash(org.id)}`,
        }));
        this.orgs.set(anonymized);
        this.orgsLoading.set(false);
      });
  }

  // -- Users ----------------------------------------------------─

  private loadUsers(): void {
    this.usersLoading.set(true);
    this.adminService.getUsers()
      .pipe(catchError(() => { this.usersError.set(this.ts.translateInstant('admin.loading_users_error')); return of([]); }))
      .subscribe(data => {
        const anonymized = data.map(user => ({
          ...user,
          email: `user-${this.simpleHash(user.id)}@anonymous.local`,
          display_name: `User ${this.simpleHash(user.id).slice(0, 6)}`,
        }));
        this.users.set(anonymized);
        this.usersLoading.set(false);
      });
  }

  // -- Access Requests ------------------------------------------─

  setArStatus(status: AccessRequestStatus): void {
    this.arStatus.set(status);
    this.arLoading.set(true);
    this.arError.set(null);
    this.arSuccess.set(null);
    this.loadAccessRequests();
  }

  private loadAccessRequests(): void {
    this.arLoading.set(true);
    this.adminService
      .getAccessRequests(this.arStatus())
      .pipe(
        catchError(() => {
          this.arError.set(this.ts.translateInstant('admin.error_loading_access_requests'));
          return of([]);
        }),
      )
      .subscribe((data) => {
        const anonymized = data.map(ar => ({
          ...ar,
          requester_name: `Requester ${this.simpleHash(ar.id).slice(0, 6)}`,
          requester_email: `req-${this.simpleHash(ar.id)}@anonymous.local`,
          organization_name: `Org ${this.simpleHash(ar.id).slice(0, 6)}`,
          slug_preview: undefined,
          organization_description: undefined,
        }));
        this.accessRequests.set(anonymized);
        this.arLoading.set(false);
      });
  }
}
