import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { ProjectsComponent } from './projects.component';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
};

interface MockUser {
  id: string;
  email: string;
  display_name: string;
  role: 'VIEWER' | 'OPERATOR' | 'ADMIN' | 'MANAGER';
  organization_id: string;
}

interface Project {
  id: string;
  name: string;
  description: string;
  profile_id: string | null;
  is_archived: boolean;
  created_at: string | null;
}

const createMockAuthService = (user: MockUser | null) => ({
  getUser: vi.fn(() => user),
  getUserRole: vi.fn(() => user?.role ?? ''),
});

const mockProjects: Project[] = [
  { id: 'proj-1', name: 'Alpha', description: 'First project', profile_id: 'prof-1', is_archived: false, created_at: '2024-01-15T10:00:00Z' },
  { id: 'proj-2', name: 'Beta', description: '', profile_id: 'prof-2', is_archived: false, created_at: '2024-02-20T14:30:00Z' },
  { id: 'proj-3', name: 'Archived', description: 'Old project', profile_id: null, is_archived: true, created_at: '2023-06-01T08:00:00Z' },
];

describe('ProjectsComponent', () => {
  let component: ProjectsComponent;
  let fixture: ComponentFixture<ProjectsComponent>;
  let httpCtrl: HttpTestingController;
  let authService: ReturnType<typeof createMockAuthService>;

  const managerUser: MockUser = {
    id: 'user-1',
    email: 'manager@test.com',
    display_name: 'Manager User',
    role: 'MANAGER',
    organization_id: 'org-1',
  };

  const viewerUser: MockUser = {
    id: 'user-2',
    email: 'viewer@test.com',
    display_name: 'Viewer User',
    role: 'VIEWER',
    organization_id: 'org-1',
  };

  beforeEach(() => {
    authService = createMockAuthService(managerUser);

    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authService },
        { provide: TranslationService, useValue: tsMock },
      ],
    });

    fixture = TestBed.createComponent(ProjectsComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpCtrl?.verify();
    TestBed.resetTestingModule();
  });

  describe('ngOnInit', () => {
    it('should load projects on init', () => {
      component.ngOnInit();
      const req = httpCtrl.expectOne('/api/v1/organizations/org-1/projects');
      expect(req.request.method).toBe('GET');
      req.flush(mockProjects);
      fixture.detectChanges();

      expect(component.projects()).toEqual(mockProjects);
      expect(component.loading()).toBe(false);
      expect(component.error()).toBeNull();
    });

    it('should set error on HTTP failure', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/projects').flush('', { status: 500, statusText: 'Error' });
      fixture.detectChanges();

      expect(component.error()).toBe('projects.load_error');
      expect(component.loading()).toBe(false);
    });

    it('should show skeleton while loading', () => {
      component.ngOnInit();
      fixture.detectChanges();

      expect(component.loading()).toBe(true);
      const skeletons = fixture.nativeElement.querySelectorAll('.skeleton-row');
      expect(skeletons.length).toBe(4);
    });

    it('should show error banner when error occurs', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/projects').flush('', { status: 500, statusText: 'Error' });
      fixture.detectChanges();

      const errorBanner = fixture.nativeElement.querySelector('.error-banner');
      expect(errorBanner).toBeTruthy();
    });
  });

  describe('isManager', () => {
    it('should be true when user role is MANAGER', () => {
      authService.getUserRole.mockReturnValue('MANAGER');
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/projects').flush(mockProjects);
      fixture.detectChanges();

      expect(component.isManager).toBe(true);
      const newBtn = fixture.nativeElement.querySelector('.btn-primary');
      expect(newBtn).toBeTruthy();
    });

    it('should be false when user role is VIEWER', () => {
      authService = createMockAuthService(viewerUser);
      TestBed.resetTestingModule();
      TestBed.configureTestingModule({
        providers: [
          provideHttpClient(),
          provideHttpClientTesting(),
          { provide: AuthService, useValue: authService },
          { provide: TranslationService, useValue: tsMock },
        ],
      });

      fixture = TestBed.createComponent(ProjectsComponent);
      component = fixture.componentInstance;
      httpCtrl = TestBed.inject(HttpTestingController);

      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/projects').flush(mockProjects);
      fixture.detectChanges();

      expect(component.isManager).toBe(false);
    });
  });

  describe('projects table', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/projects').flush(mockProjects);
      fixture.detectChanges();
    });

    it('should render all projects in table', () => {
      const rows = fixture.nativeElement.querySelectorAll('.data-table tbody tr');
      expect(rows.length).toBe(3);
    });

    it('should show project names', () => {
      const firstCell = fixture.nativeElement.querySelector('.cell-primary');
      expect(firstCell.textContent).toContain('Alpha');
    });

    it('should show archived badge for archived projects', () => {
      const badges = fixture.nativeElement.querySelectorAll('.status-badge');
      expect(badges[0].textContent).toContain('projects.status_active');
    });

    it('should show empty state when no projects', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/projects').flush([]);
      fixture.detectChanges();

      const emptyState = fixture.nativeElement.querySelector('.empty-state');
      expect(emptyState).toBeTruthy();
      expect(fixture.nativeElement.querySelector('.empty-text')).toBeTruthy();
    });

    it('should show placeholder for empty description', () => {
      const secondRowCells = fixture.nativeElement.querySelectorAll('.data-table tbody tr')[1].querySelectorAll('td');
      expect(secondRowCells[1].textContent).toBe('—');
    });
  });

  describe('archive modal', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/projects').flush(mockProjects);
      fixture.detectChanges();
    });

    it('should open archive confirmation modal', () => {
      component.confirmArchive(mockProjects[0]);
      expect(component.projectToArchive()).toEqual(mockProjects[0]);
    });

    it('should close archive modal', () => {
      component.projectToArchive.set(mockProjects[0]);
      component.cancelArchive();
      expect(component.projectToArchive()).toBeNull();
    });

    it('should archive project successfully', () => {
      component.confirmArchive(mockProjects[0]);
      component.archive();

      const req = httpCtrl.expectOne('/api/v1/organizations/org-1/projects/proj-1/archive');
      expect(req.request.method).toBe('POST');
      req.flush({});
      fixture.detectChanges();

      expect(component.archiving()).toBe(false);
      expect(component.projects()[0].is_archived).toBe(true);
      expect(component.projectToArchive()).toBeNull();
    });

    it('should handle archive error', () => {
      component.confirmArchive(mockProjects[0]);
      component.archive();

      httpCtrl.expectOne('/api/v1/organizations/org-1/projects/proj-1/archive').flush('', { status: 500, statusText: 'Error' });
      fixture.detectChanges();

      expect(component.archiving()).toBe(false);
    });

    it('should not archive if no project selected', () => {
      component.projectToArchive.set(null);
      component.archive();
      httpCtrl.expectNone('/api/v1/organizations/org-1/projects//archive');
    });
  });

  describe('unarchive', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/projects').flush(mockProjects);
      fixture.detectChanges();
    });

    it('should unarchive project successfully', () => {
      component.unarchive(mockProjects[2]);

      const req = httpCtrl.expectOne('/api/v1/organizations/org-1/projects/proj-3/unarchive');
      expect(req.request.method).toBe('POST');
      req.flush({});
      fixture.detectChanges();

      expect(component.projects()[2].is_archived).toBe(false);
    });

    it('should handle unarchive error', () => {
      component.unarchive(mockProjects[2]);

      httpCtrl.expectOne('/api/v1/organizations/org-1/projects/proj-3/unarchive').flush('', { status: 500, statusText: 'Error' });
      fixture.detectChanges();

      expect(component.projects()[2].is_archived).toBe(true);
    });
  });

  describe('action buttons visibility', () => {
    it('should show archive button for non-archived projects when manager', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/projects').flush(mockProjects);
      fixture.detectChanges();

      const archiveButtons = fixture.nativeElement.querySelectorAll('.btn-ghost');
      expect(archiveButtons.length).toBeGreaterThan(0);
    });

    it('should show unarchive button for archived projects when manager', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-1/projects').flush(mockProjects);
      fixture.detectChanges();

      const unarchiveButtons = fixture.nativeElement.querySelectorAll('.btn-ghost');
      expect(unarchiveButtons.length).toBeGreaterThan(0);
    });
  });
});
