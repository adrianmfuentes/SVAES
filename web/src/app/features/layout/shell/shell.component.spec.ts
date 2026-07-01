import { TestBed, ComponentFixture } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { AuthService, MyOrganization } from '../../../core/services/auth.service';
import { TranslationService } from '../../../core/i18n/translation.service';
import { ShellComponent } from './shell.component';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

describe('ShellComponent', () => {
  let fixture: ComponentFixture<ShellComponent>;
  let component: ShellComponent;
  let authServiceMock: {
    isAdmin: ReturnType<typeof vi.fn>;
    logout: ReturnType<typeof vi.fn>;
    getUser: ReturnType<typeof vi.fn>;
    getUserRole: ReturnType<typeof vi.fn>;
    getOrganization: ReturnType<typeof vi.fn>;
    getMyOrganizations: ReturnType<typeof vi.fn>;
    switchOrganization: ReturnType<typeof vi.fn>;
  };

  const createFixture = () => {
    fixture?.destroy();
    fixture = TestBed.createComponent(ShellComponent);
    component = fixture.componentInstance;
  };

  beforeEach(async () => {
    vi.clearAllMocks();
    authServiceMock = {
      isAdmin: vi.fn().mockReturnValue(false),
      logout: vi.fn(),
      getUser: vi.fn().mockReturnValue({ id: 'u1', email: 'test@test.com', display_name: 'Test', organization_id: 'org-1' }),
      getUserRole: vi.fn().mockReturnValue('ADMIN'),
      getOrganization: vi.fn().mockReturnValue(of({ id: 'org-1', name: 'Test Org', slug: 'test-org' })),
      getMyOrganizations: vi.fn().mockReturnValue(of([{ organization_id: 'org-1', name: 'Test Org', slug: 'test-org', role: 'ADMIN', is_active: true }])),
      switchOrganization: vi.fn().mockReturnValue(of({})),
    };

    await TestBed.configureTestingModule({
      imports: [ShellComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authServiceMock },
        { provide: TranslationService, useValue: tsMock },
      ],
    }).compileComponents();

    createFixture();
    fixture.detectChanges();
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  describe('ngOnInit', () => {
    it('should set orgName from the active organization', () => {
      expect(component.orgName()).toBe('Test Org');
      expect(component.myOrganizations()).toHaveLength(1);
    });

    it('should fall back to org lookup when no active organization is found', () => {
      authServiceMock.getMyOrganizations.mockReturnValue(
        of([{ organization_id: 'org-2', name: 'Other Org', slug: 'other-org', role: 'ADMIN', is_active: false }] as MyOrganization[]),
      );
      createFixture();
      fixture.detectChanges();
      expect(authServiceMock.getOrganization).toHaveBeenCalledWith('org-1');
      expect(component.orgName()).toBe('Test Org');
    });

    it('should not fetch fallback org when no active org and no organization_id', () => {
      authServiceMock.getUser.mockReturnValue({ id: 'u1', email: 'test@test.com' });
      authServiceMock.getMyOrganizations.mockReturnValue(of([]));
      createFixture();
      fixture.detectChanges();
      expect(authServiceMock.getOrganization).not.toHaveBeenCalled();
      expect(component.orgName()).toBe('');
    });

    it('should fall back to org lookup on getMyOrganizations error when organization_id present', () => {
      authServiceMock.getMyOrganizations.mockReturnValue(throwError(() => new Error('fail')));
      createFixture();
      fixture.detectChanges();
      expect(authServiceMock.getOrganization).toHaveBeenCalledWith('org-1');
      expect(component.orgName()).toBe('Test Org');
    });

    it('should not fall back on getMyOrganizations error when no organization_id', () => {
      authServiceMock.getUser.mockReturnValue({ id: 'u1', email: 'test@test.com' });
      authServiceMock.getMyOrganizations.mockReturnValue(throwError(() => new Error('fail')));
      createFixture();
      fixture.detectChanges();
      expect(authServiceMock.getOrganization).not.toHaveBeenCalled();
    });

    it('should set orgName to empty string when fallback org lookup fails', () => {
      authServiceMock.getMyOrganizations.mockReturnValue(of([]));
      authServiceMock.getOrganization.mockReturnValue(throwError(() => new Error('fail')));
      createFixture();
      fixture.detectChanges();
      expect(component.orgName()).toBe('');
    });

    it('should set orgName to empty string when fallback org has no name', () => {
      authServiceMock.getMyOrganizations.mockReturnValue(of([]));
      authServiceMock.getOrganization.mockReturnValue(of(null));
      createFixture();
      fixture.detectChanges();
      expect(component.orgName()).toBe('');
    });
  });

  describe('hasMultipleOrganizations', () => {
    it('should be false with a single organization', () => {
      expect(component.hasMultipleOrganizations).toBe(false);
    });

    it('should be true with more than one organization', () => {
      component.myOrganizations.set([
        { organization_id: 'org-1', name: 'A', slug: 'a', role: 'ADMIN', is_active: true },
        { organization_id: 'org-2', name: 'B', slug: 'b', role: 'ADMIN', is_active: false },
      ] as MyOrganization[]);
      expect(component.hasMultipleOrganizations).toBe(true);
    });
  });

  describe('org menu toggling', () => {
    it('should toggle orgMenuOpen', () => {
      expect(component.orgMenuOpen()).toBe(false);
      component.toggleOrgMenu();
      expect(component.orgMenuOpen()).toBe(true);
      component.toggleOrgMenu();
      expect(component.orgMenuOpen()).toBe(false);
    });

    it('should close orgMenu', () => {
      component.orgMenuOpen.set(true);
      component.closeOrgMenu();
      expect(component.orgMenuOpen()).toBe(false);
    });
  });

  describe('switchOrganization', () => {
    const org: MyOrganization = { organization_id: 'org-2', name: 'Other Org', slug: 'other-org', role: 'ADMIN', is_active: false };

    it('should do nothing but close the menu when org is already active', () => {
      component.orgMenuOpen.set(true);
      component.switchOrganization({ ...org, is_active: true });
      expect(component.orgMenuOpen()).toBe(false);
      expect(authServiceMock.switchOrganization).not.toHaveBeenCalled();
    });

    it('should do nothing but close the menu when already switching', () => {
      component.switchingOrg.set(true);
      component.orgMenuOpen.set(true);
      component.switchOrganization(org);
      expect(component.orgMenuOpen()).toBe(false);
      expect(authServiceMock.switchOrganization).not.toHaveBeenCalled();
    });

    it('should call switchOrganization and reload on success', () => {
      const reloadSpy = vi.fn();
      const originalLocation = globalThis.location;
      Object.defineProperty(globalThis, 'location', {
        value: { reload: reloadSpy },
        writable: true,
      });

      component.switchOrganization(org);

      expect(authServiceMock.switchOrganization).toHaveBeenCalledWith('org-2');
      expect(component.switchingOrg()).toBe(true);
      expect(reloadSpy).toHaveBeenCalled();

      Object.defineProperty(globalThis, 'location', { value: originalLocation, writable: true });
    });

    it('should set switchOrgError on failure', () => {
      authServiceMock.switchOrganization.mockReturnValue(throwError(() => new Error('fail')));
      component.switchOrganization(org);
      expect(component.switchingOrg()).toBe(false);
      expect(component.switchOrgError()).toBe('shell.switch_org_error');
    });
  });

  describe('sidebar', () => {
    it('should toggle sidebarOpen', () => {
      expect(component.sidebarOpen).toBe(false);
      component.toggleSidebar();
      expect(component.sidebarOpen).toBe(true);
      component.toggleSidebar();
      expect(component.sidebarOpen).toBe(false);
    });

    it('should close sidebar', () => {
      component.sidebarOpen = true;
      component.closeSidebar();
      expect(component.sidebarOpen).toBe(false);
    });
  });

  describe('onEscape', () => {
    it('should close sidebar and org menu', () => {
      component.sidebarOpen = true;
      component.orgMenuOpen.set(true);
      component.onEscape();
      expect(component.sidebarOpen).toBe(false);
      expect(component.orgMenuOpen()).toBe(false);
    });
  });

  describe('onDocumentClick', () => {
    it('should do nothing when orgMenuOpen is false', () => {
      component.orgMenuOpen.set(false);
      const target = document.createElement('div');
      component.onDocumentClick({ target } as unknown as MouseEvent);
      expect(component.orgMenuOpen()).toBe(false);
    });

    it('should close menu when click target is outside .org-switcher', () => {
      component.orgMenuOpen.set(true);
      const target = document.createElement('div');
      document.body.appendChild(target);
      component.onDocumentClick({ target } as unknown as MouseEvent);
      expect(component.orgMenuOpen()).toBe(false);
      document.body.removeChild(target);
    });

    it('should keep menu open when click target is inside .org-switcher', () => {
      component.orgMenuOpen.set(true);
      const wrapper = document.createElement('div');
      wrapper.classList.add('org-switcher');
      const target = document.createElement('span');
      wrapper.appendChild(target);
      document.body.appendChild(wrapper);
      component.onDocumentClick({ target } as unknown as MouseEvent);
      expect(component.orgMenuOpen()).toBe(true);
      document.body.removeChild(wrapper);
    });
  });

  describe('isAdmin', () => {
    it('should return true when authService.isAdmin returns true', () => {
      authServiceMock.isAdmin.mockReturnValue(true);
      expect(component.isAdmin).toBe(true);
    });

    it('should return false when authService.isAdmin returns false', () => {
      authServiceMock.isAdmin.mockReturnValue(false);
      expect(component.isAdmin).toBe(false);
    });
  });

  describe('isManager / isOperator', () => {
    it('isManager should be true when role is MANAGER', () => {
      authServiceMock.getUserRole.mockReturnValue('MANAGER');
      expect(component.isManager).toBe(true);
      expect(component.isOperator).toBe(false);
    });

    it('isOperator should be true when role is OPERATOR', () => {
      authServiceMock.getUserRole.mockReturnValue('OPERATOR');
      expect(component.isOperator).toBe(true);
      expect(component.isManager).toBe(false);
    });
  });

  describe('displayName', () => {
    it('should prefer display_name when present', () => {
      authServiceMock.getUser.mockReturnValue({ email: 'a@b.com', display_name: 'Alice' });
      expect(component.displayName).toBe('Alice');
    });

    it('should fall back to email when display_name is missing', () => {
      authServiceMock.getUser.mockReturnValue({ email: 'a@b.com' });
      expect(component.displayName).toBe('a@b.com');
    });

    it('should return empty string when no user', () => {
      authServiceMock.getUser.mockReturnValue(null);
      expect(component.displayName).toBe('');
    });
  });

  describe('roleLabel', () => {
    it('should return admin label', () => {
      authServiceMock.getUserRole.mockReturnValue('ADMIN');
      expect(component.roleLabel).toBe('shell.role_admin');
    });

    it('should return manager label', () => {
      authServiceMock.getUserRole.mockReturnValue('MANAGER');
      expect(component.roleLabel).toBe('shell.role_manager');
    });

    it('should return operator label', () => {
      authServiceMock.getUserRole.mockReturnValue('OPERATOR');
      expect(component.roleLabel).toBe('shell.role_operator');
    });

    it('should return raw role for unknown role', () => {
      authServiceMock.getUserRole.mockReturnValue('UNKNOWN');
      expect(component.roleLabel).toBe('UNKNOWN');
    });
  });

  describe('logout', () => {
    it('should call authService.logout', () => {
      component.logout();
      expect(authServiceMock.logout).toHaveBeenCalled();
    });
  });
});
