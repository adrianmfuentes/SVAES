import { Component, inject, HostListener, signal, OnInit } from '@angular/core';
import { RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService, MyOrganization } from '../../../core/services/auth.service';
import { TranslationService } from '../../../core/i18n/translation.service';
import { TranslatePipe } from '../../../core/i18n/translate.pipe';
import { LangToggleComponent } from '../../../core/components/lang-toggle/lang-toggle.component';
import { ToastComponent } from '../../../core/components/toast/toast.component';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslatePipe, LangToggleComponent, ToastComponent],
  templateUrl: './shell.component.html',
  styleUrl: './shell.component.scss',
})
export class ShellComponent implements OnInit {
  readonly authService = inject(AuthService);
  private readonly ts = inject(TranslationService);

  sidebarOpen = false;
  orgName = signal<string>('');
  myOrganizations = signal<MyOrganization[]>([]);
  orgMenuOpen = signal(false);
  switchingOrg = signal(false);
  switchOrgError = signal<string | null>(null);

  ngOnInit(): void {
    const user = this.authService.getUser();
    const orgId = user?.organization_id;

    this.authService.getMyOrganizations().subscribe({
      next: (orgs) => {
        this.myOrganizations.set(orgs);
        const active = orgs.find((o) => o.is_active);
        if (active) {
          this.orgName.set(active.name);
        } else if (orgId) {
          this.loadOrgNameFallback(orgId);
        }
      },
      error: () => {
        if (orgId) this.loadOrgNameFallback(orgId);
      },
    });
  }

  private loadOrgNameFallback(orgId: string): void {
    this.authService.getOrganization(orgId).subscribe({
      next: (org) => this.orgName.set(org?.name ?? ''),
      error: () => this.orgName.set(''),
    });
  }

  get hasMultipleOrganizations(): boolean {
    return this.myOrganizations().length > 1;
  }

  toggleOrgMenu(): void {
    this.orgMenuOpen.update((open) => !open);
  }

  closeOrgMenu(): void {
    this.orgMenuOpen.set(false);
  }

  switchOrganization(org: MyOrganization): void {
    if (org.is_active || this.switchingOrg()) {
      this.closeOrgMenu();
      return;
    }
    this.switchingOrg.set(true);
    this.switchOrgError.set(null);
    this.authService.switchOrganization(org.organization_id).subscribe({
      next: () => globalThis.location.reload(),
      error: () => {
        this.switchingOrg.set(false);
        this.switchOrgError.set(this.ts.translateInstant('shell.switch_org_error'));
      },
    });
  }

  toggleSidebar(): void { this.sidebarOpen = !this.sidebarOpen; }
  closeSidebar(): void { this.sidebarOpen = false; }

  @HostListener('window:keydown.escape')
  onEscape(): void { this.sidebarOpen = false; this.orgMenuOpen.set(false); }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.orgMenuOpen()) return;
    const target = event.target as HTMLElement;
    if (!target.closest('.org-switcher')) {
      this.orgMenuOpen.set(false);
    }
  }

  get isAdmin(): boolean {
    return this.authService.isAdmin();
  }

  get isManager(): boolean {
    return this.authService.getUserRole() === 'MANAGER';
  }

  get isOperator(): boolean {
    return this.authService.getUserRole() === 'OPERATOR';
  }

  get displayName(): string {
    const user = this.authService.getUser();
    return user?.display_name || user?.email || '';
  }

  get roleLabel(): string {
    const role = this.authService.getUserRole();
    const map: Record<string, string> = {
      ADMIN: this.ts.translateInstant('shell.role_admin'),
      MANAGER: this.ts.translateInstant('shell.role_manager'),
      OPERATOR: this.ts.translateInstant('shell.role_operator'),
    };
    return map[role] ?? role;
  }

  logout(): void {
    this.authService.logout();
  }
}
