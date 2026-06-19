import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router, ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';
import { ReleaseNewComponent } from './release-new.component';
import { TranslationService } from '../../../core/i18n/translation.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

const mockProjects = [
  { id: 'proj-1', name: 'Alpha' },
  { id: 'proj-2', name: 'Beta' },
];

const createMockActivatedRoute = (releaseId: string | null = null) => ({
  snapshot: {
    paramMap: {
      get: vi.fn().mockReturnValue(releaseId),
    },
  },
});

describe('ReleaseNewComponent', () => {
  let component: ReleaseNewComponent;
  let fixture: ComponentFixture<ReleaseNewComponent>;
  let httpCtrl: HttpTestingController;
  let router: Router;
  let route: ActivatedRoute;

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TranslationService, useValue: tsMock },
        { provide: ActivatedRoute, useValue: createMockActivatedRoute() },
      ],
    });

    fixture = TestBed.createComponent(ReleaseNewComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    route = TestBed.inject(ActivatedRoute);
  });

  afterEach(() => {
    httpCtrl?.verify();
    TestBed.resetTestingModule();
  });

  describe('ngOnInit', () => {
    it('should load projects on init', () => {
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/projects').flush(mockProjects);
      expect(component.projects()).toEqual(mockProjects);
      expect(component.loading()).toBe(false);
    });

    it('should set empty array on project load error', () => {
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/projects').flush('', { status: 500, statusText: 'Error' });
      expect(component.projects()).toEqual([]);
      expect(component.loading()).toBe(false);
    });

    it('should not be in edit mode when no release id', () => {
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/projects').flush(mockProjects);
      expect(component.isEditMode()).toBe(false);
    });

    it('should enter edit mode when release id is present', () => {
      const releaseId = 'rel-123';
      TestBed.resetTestingModule();
      TestBed.configureTestingModule({
        providers: [
          provideRouter([]),
          provideHttpClient(),
          provideHttpClientTesting(),
          { provide: TranslationService, useValue: tsMock },
          { provide: ActivatedRoute, useValue: createMockActivatedRoute(releaseId) },
        ],
      });

      const editFixture = TestBed.createComponent(ReleaseNewComponent);
      const editComponent = editFixture.componentInstance;
      const editHttpCtrl = TestBed.inject(HttpTestingController);
      const editRouter = TestBed.inject(Router);

      editFixture.detectChanges();
      const req = editHttpCtrl.expectOne(`/api/v1/releases/${releaseId}`);
      expect(req.request.method).toBe('GET');
      req.flush({ id: releaseId, name: 'Test Release', version: '1.0.0', description: 'Test desc' });

      expect(editComponent.isEditMode()).toBe(true);
      expect(editComponent.releaseId).toBe(releaseId);
      editHttpCtrl.verify();
    });

    it('should navigate away on release load error', () => {
      const releaseId = 'rel-123';
      const navigateSpy = vi.spyOn(router, 'navigate');

      TestBed.resetTestingModule();
      TestBed.configureTestingModule({
        providers: [
          provideRouter([]),
          provideHttpClient(),
          provideHttpClientTesting(),
          { provide: TranslationService, useValue: tsMock },
          { provide: ActivatedRoute, useValue: createMockActivatedRoute(releaseId) },
        ],
      });

      const editFixture = TestBed.createComponent(ReleaseNewComponent);
      const editComponent = editFixture.componentInstance;
      const editHttpCtrl = TestBed.inject(HttpTestingController);
      const editRouterSpy = vi.spyOn(TestBed.inject(Router), 'navigate');

      editFixture.detectChanges();
      editHttpCtrl.expectOne(`/api/v1/releases/${releaseId}`).flush('', { status: 500, statusText: 'Error' });

      expect(editRouterSpy).toHaveBeenCalledWith(['/app/releases']);
      editHttpCtrl.verify();
    });

    it('should load release and patch form values', () => {
      const releaseId = 'rel-123';
      TestBed.resetTestingModule();
      TestBed.configureTestingModule({
        providers: [
          provideRouter([]),
          provideHttpClient(),
          provideHttpClientTesting(),
          { provide: TranslationService, useValue: tsMock },
          { provide: ActivatedRoute, useValue: createMockActivatedRoute(releaseId) },
        ],
      });

      const editFixture = TestBed.createComponent(ReleaseNewComponent);
      const editComponent = editFixture.componentInstance;
      const editHttpCtrl = TestBed.inject(HttpTestingController);

      editFixture.detectChanges();
      editHttpCtrl.expectOne(`/api/v1/releases/${releaseId}`).flush({
        name: 'My Release',
        version: '2.0.0',
        description: 'Updated desc',
      });

      expect(editComponent.form.get('name')?.value).toBe('My Release');
      expect(editComponent.form.get('version')?.value).toBe('2.0.0');
      expect(editComponent.form.get('description')?.value).toBe('Updated desc');
      editHttpCtrl.verify();
    });
  });

  describe('isManager', () => {
    it('should return false for non-manager roles', () => {
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/projects').flush(mockProjects);
      expect(component.isManager).toBe(false);
    });
  });

  describe('submit', () => {
    beforeEach(() => {
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/projects').flush(mockProjects);
    });

    it('should mark all fields touched if form is invalid', () => {
      const spy = vi.spyOn(component.form, 'markAllAsTouched');
      component.submit();
      expect(spy).toHaveBeenCalled();
      httpCtrl.expectNone('/api/v1/projects/proj-1/releases');
    });

    it('should POST release and navigate on success', () => {
      const navigateSpy = vi.spyOn(router, 'navigate');
      component.form.setValue({ project_id: 'proj-1', name: 'My Release', version: '1.0.0', description: '' });
      component.submit();
      const req = httpCtrl.expectOne('/api/v1/projects/proj-1/releases');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toMatchObject({ name: 'My Release', version: '1.0.0' });
      req.flush({ id: 'new-rel-id', status: 'pending' });
      expect(navigateSpy).toHaveBeenCalledWith(['/app/releases', 'new-rel-id']);
    });

    it('should set submitError on POST failure', () => {
      component.form.setValue({ project_id: 'proj-1', name: 'Bad', version: '1.0.0', description: '' });
      component.submit();
      httpCtrl.expectOne('/api/v1/projects/proj-1/releases').flush(
        { detail: 'Server error' },
        { status: 500, statusText: 'Error' }
      );
      expect(component.submitError()).toBe('Server error');
      expect(component.submitting()).toBe(false);
    });

    it('should fall back to translated error key if detail missing', () => {
      component.form.setValue({ project_id: 'proj-1', name: 'Bad', version: '1.0.0', description: '' });
      component.submit();
      httpCtrl.expectOne('/api/v1/projects/proj-1/releases').flush({}, { status: 500, statusText: 'Error' });
      expect(tsMock.translateInstant).toHaveBeenCalledWith('release_new.error');
    });

    it('should not submit when loading', () => {
      component.submitting.set(true);
      component.form.setValue({ project_id: 'proj-1', name: 'My Release', version: '1.0.0', description: '' });
      const navigateSpy = vi.spyOn(router, 'navigate').mockReturnValue(Promise.resolve(true));
      component.submit();
      const req = httpCtrl.expectOne('/api/v1/projects/proj-1/releases');
      req.flush({ id: 'new-rel-id', status: 'pending' });
      expect(navigateSpy).toHaveBeenCalled();
    });
  });

  describe('edit mode submit', () => {
    it('should PATCH release and navigate on success', () => {
      const releaseId = 'rel-123';
      TestBed.resetTestingModule();
      TestBed.configureTestingModule({
        providers: [
          provideRouter([]),
          provideHttpClient(),
          provideHttpClientTesting(),
          { provide: TranslationService, useValue: tsMock },
          { provide: ActivatedRoute, useValue: createMockActivatedRoute(releaseId) },
        ],
      });

      const editFixture = TestBed.createComponent(ReleaseNewComponent);
      const editComponent = editFixture.componentInstance;
      const editHttpCtrl = TestBed.inject(HttpTestingController);
      const editRouter = TestBed.inject(Router);
      const navigateSpy = vi.spyOn(editRouter, 'navigate');

      editFixture.detectChanges();
      editHttpCtrl.expectOne(`/api/v1/releases/${releaseId}`).flush({
        name: 'Old Name',
        version: '1.0.0',
        description: '',
      });

      editComponent.releaseId = releaseId;
      editComponent.form.setValue({ project_id: '', name: 'Updated Release', version: '2.0.0', description: 'Updated' });
      editComponent.submit();

      const req = editHttpCtrl.expectOne(`/api/v1/releases/${releaseId}`);
      expect(req.request.method).toBe('PATCH');
      req.flush({ id: releaseId });

      expect(navigateSpy).toHaveBeenCalledWith(['/app/releases', releaseId]);
      editHttpCtrl.verify();
    });

    it('should set edit_error on PATCH failure', () => {
      const releaseId = 'rel-123';
      TestBed.resetTestingModule();
      TestBed.configureTestingModule({
        providers: [
          provideRouter([]),
          provideHttpClient(),
          provideHttpClientTesting(),
          { provide: TranslationService, useValue: tsMock },
          { provide: ActivatedRoute, useValue: createMockActivatedRoute(releaseId) },
        ],
      });

      const editFixture = TestBed.createComponent(ReleaseNewComponent);
      const editComponent = editFixture.componentInstance;
      const editHttpCtrl = TestBed.inject(HttpTestingController);

      editFixture.detectChanges();
      editHttpCtrl.expectOne(`/api/v1/releases/${releaseId}`).flush({
        name: 'Old Name',
        version: '1.0.0',
        description: '',
      });

      editComponent.releaseId = releaseId;
      editComponent.form.setValue({ project_id: '', name: 'Updated', version: '2.0.0', description: '' });
      editComponent.submit();

      editHttpCtrl.expectOne(`/api/v1/releases/${releaseId}`).flush(
        { detail: 'Edit failed' },
        { status: 500, statusText: 'Error' }
      );

      expect(editComponent.submitError()).toBe('Edit failed');
      expect(editComponent.submitting()).toBe(false);
      editHttpCtrl.verify();
    });
  });

  describe('form validation', () => {
    beforeEach(() => {
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/projects').flush(mockProjects);
    });

    it('should show required error when project is not selected', () => {
      component.form.setValue({ project_id: '', name: 'My Release', version: '1.0.0', description: '' });
      component.form.get('project_id')?.markAsTouched();
      component.submit();

      expect(component.form.get('project_id')?.hasError('required')).toBe(true);
    });

    it('should show required error when name is empty', () => {
      component.form.setValue({ project_id: 'proj-1', name: '', version: '1.0.0', description: '' });
      component.form.get('name')?.markAsTouched();
      fixture.detectChanges();

      const errorEl = fixture.nativeElement.querySelector('.field-error');
      expect(errorEl).toBeTruthy();
    });

    it('should show maxlength error when name exceeds limit', () => {
      const longName = 'a'.repeat(101);
      component.form.setValue({ project_id: 'proj-1', name: longName, version: '1.0.0', description: '' });
      component.form.get('name')?.markAsTouched();
      component.submit();

      expect(component.form.get('name')?.hasError('maxlength')).toBe(true);
    });

    it('should show maxlength error when description exceeds limit', () => {
      const longDesc = 'a'.repeat(1001);
      component.form.setValue({ project_id: 'proj-1', name: 'Valid', version: '1.0.0', description: longDesc });
      component.form.get('description')?.markAsTouched();
      component.submit();

      expect(component.form.get('description')?.hasError('maxlength')).toBe(true);
    });
  });
});
