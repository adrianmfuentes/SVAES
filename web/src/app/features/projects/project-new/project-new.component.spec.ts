import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router, ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';
import { ProjectNewComponent } from './project-new.component';
import { AuthService } from '../../../core/services/auth.service';
import { TranslationService } from '../../../core/i18n/translation.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

const createMockActivatedRoute = (releaseId: string | null = null) => ({
  snapshot: {
    paramMap: {
      get: vi.fn().mockReturnValue(releaseId),
    },
  },
});

interface MockUser {
  id: string;
  email: string;
  display_name: string;
  role: 'VIEWER' | 'OPERATOR' | 'ADMIN' | 'MANAGER';
  organization_id: string;
}

interface Profile {
  id: string;
  name: string;
  is_system?: boolean;
  is_default?: boolean;
}

const createMockAuthService = (user: MockUser | null) => ({
  getUser: vi.fn(() => user),
  getUserRole: vi.fn(() => user?.role ?? ''),
});

const mockProfiles: Profile[] = [
  { id: 'prof-1', name: 'System Profile', is_system: true },
  { id: 'prof-2', name: 'Custom Default', is_default: true },
  { id: 'prof-3', name: 'Custom No Default' },
];

describe('ProjectNewComponent', () => {
  let component: ProjectNewComponent;
  let fixture: ComponentFixture<ProjectNewComponent>;
  let httpCtrl: HttpTestingController;
  let router: Router;
  let authService: ReturnType<typeof createMockAuthService>;
  const routerMock = { navigate: vi.fn() } as unknown as Router;

  const userWithOrg: MockUser = {
    id: 'user-1',
    email: 'test@test.com',
    display_name: 'Test User',
    role: 'MANAGER',
    organization_id: 'org-1',
  };

  beforeEach(() => {
    authService = createMockAuthService(userWithOrg);

    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authService },
        { provide: TranslationService, useValue: tsMock },
        { provide: Router, useValue: routerMock },
        { provide: ActivatedRoute, useValue: createMockActivatedRoute() },
      ],
    });

    fixture = TestBed.createComponent(ProjectNewComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
  });

  afterEach(() => {
    httpCtrl?.verify();
    TestBed.resetTestingModule();
  });

  describe('ngOnInit', () => {
    it('should load profiles on init', () => {
      component.ngOnInit();
      const req = httpCtrl.expectOne('/api/v1/organizations/org-1/profiles');
      expect(req.request.method).toBe('GET');
      req.flush(mockProfiles);

      expect(component.profiles()).toEqual(mockProfiles);
      expect(component.profilesLoading()).toBe(false);
    });

    it('should set loading false when orgId is missing', () => {
      authService.getUser.mockReturnValueOnce({ ...userWithOrg, organization_id: '' });
      component.ngOnInit();

      expect(component.profilesLoading()).toBe(false);
      httpCtrl.expectNone('/api/v1/organizations//profiles');
    });

    it('should set empty profiles on error', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/profiles').flush('', { status: 500, statusText: 'Error' });

      expect(component.profiles()).toEqual([]);
      expect(component.profilesLoading()).toBe(false);
    });

    it('should auto-select default custom profile', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/profiles').flush(mockProfiles);

      expect(component.form.get('profile_id')?.value).toBe('prof-2');
    });

    it('should auto-select system profile when no default custom', () => {
      const profilesWithoutDefault = [
        { id: 'prof-1', name: 'System Profile', is_system: true },
        { id: 'prof-3', name: 'Custom No Default' },
      ];
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/profiles').flush(profilesWithoutDefault);

      expect(component.form.get('profile_id')?.value).toBe('prof-1');
    });

    it('should show skeleton while loading', () => {
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/organizations/org-1/profiles').flush(mockProfiles);
      component.profilesLoading.set(true);
      fixture.detectChanges();

      expect(component.profilesLoading()).toBe(true);
      const skeletons = fixture.nativeElement.querySelectorAll('.skeleton');
      expect(skeletons.length).toBeGreaterThan(0);
    });
  });

  describe('customProfiles computed', () => {
    it('should return only non-system profiles', () => {
      vi.spyOn(component, 'ngOnInit').mockImplementation(() => {});
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/organizations/org-1/profiles').flush(mockProfiles);

      const custom = component.customProfiles();
      expect(custom).toHaveLength(2);
      expect(custom.every(p => !p.is_system)).toBe(true);
    });
  });

  describe('submit', () => {
    beforeEach(() => {
      vi.spyOn(component, 'ngOnInit').mockImplementation(() => {});
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/organizations/org-1/profiles').flush(mockProfiles);
    });

    it('should mark all fields touched if form is invalid', () => {
      const spy = vi.spyOn(component.form, 'markAllAsTouched');
      component.submit();
      expect(spy).toHaveBeenCalled();
      httpCtrl.expectNone('/api/v1/organizations/org-1/projects');
    });

    it('should not submit when form name is empty', () => {
      component.form.setValue({ name: '', description: 'desc', profile_id: 'prof-1' });
      component.submit();
      httpCtrl.expectNone('/api/v1/organizations/org-1/projects');
    });

    it('should POST project and navigate on success', () => {
      const navigateSpy = vi.spyOn(router, 'navigate');
      component.form.setValue({ name: 'New Project', description: 'Test desc', profile_id: 'prof-1' });
      component.submit();

      const req = httpCtrl.expectOne('/api/v1/organizations/org-1/projects');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual({ name: 'New Project', description: 'Test desc', profile_id: 'prof-1' });
      req.flush({ id: 'proj-new' });
      fixture.detectChanges();

      expect(navigateSpy).toHaveBeenCalledWith(['/app/projects']);
    });

    it('should set submitError on POST failure with detail', () => {
      component.form.setValue({ name: 'Bad', description: '', profile_id: 'prof-1' });
      component.submit();

      httpCtrl.expectOne('/api/v1/organizations/org-1/projects').flush(
        { detail: 'Project already exists' },
        { status: 400, statusText: 'Bad Request' }
      );
      fixture.detectChanges();

      expect(component.submitError()).toBe('Project already exists');
      expect(component.submitting()).toBe(false);
    });

    it('should set submitError on POST failure without detail', () => {
      component.form.setValue({ name: 'Bad', description: '', profile_id: 'prof-1' });
      component.submit();

      httpCtrl.expectOne('/api/v1/organizations/org-1/projects').flush({}, { status: 500, statusText: 'Error' });
      fixture.detectChanges();

      expect(component.submitError()).toBe('project_new.error');
    });

    it('should handle network error', () => {
      component.form.setValue({ name: 'New', description: '', profile_id: 'prof-1' });
      component.submit();

      httpCtrl.expectOne('/api/v1/organizations/org-1/projects').error(new ProgressEvent('NetworkError'));
      fixture.detectChanges();

      expect(component.submitError()).toBe('project_new.error');
    });

    it('should not submit if no orgId', () => {
      authService.getUser.mockReturnValueOnce({ ...userWithOrg, organization_id: '' });
      component.ngOnInit();

      component.form.setValue({ name: 'Test', description: '', profile_id: 'prof-1' });
      component.submit();
      httpCtrl.expectNone('/api/v1/organizations//projects');
    });
  });

  describe('form validation', () => {
    beforeEach(() => {
      vi.spyOn(component, 'ngOnInit').mockImplementation(() => {});
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/organizations/org-1/profiles').flush(mockProfiles);
    });

    it('should show required error when name is empty and touched', () => {
      component.form.get('name')?.setValue('');
      component.form.get('name')?.markAsTouched();
      fixture.detectChanges();

      const errorEl = fixture.nativeElement.querySelector('.field-error');
      expect(errorEl).toBeTruthy();
      expect(errorEl.textContent).toContain('project_new.name_required');
    });

    it('should show maxlength error when name exceeds limit', () => {
      const longName = 'a'.repeat(101);
      component.form.get('name')?.setValue(longName);
      component.form.get('name')?.markAsTouched();
      fixture.detectChanges();

      const errorEl = fixture.nativeElement.querySelector('.field-error');
      expect(errorEl).toBeTruthy();
      expect(errorEl.textContent).toContain('common.max_chars');
    });

    it('should show maxlength error for description', () => {
      const longDesc = 'a'.repeat(501);
      component.form.get('description')?.setValue(longDesc);
      component.form.get('description')?.markAsTouched();
      fixture.detectChanges();

      const errorEl = fixture.nativeElement.querySelector('.field-error');
      expect(errorEl).toBeTruthy();
    });

    it('should not show error when form is valid', () => {
      component.form.setValue({ name: 'Valid', description: '', profile_id: 'prof-1' });
      fixture.detectChanges();

      const errorEl = fixture.nativeElement.querySelector('.field-error');
      expect(errorEl).toBeFalsy();
    });
  });
});
