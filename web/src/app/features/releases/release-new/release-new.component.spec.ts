import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
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

describe('ReleaseNewComponent', () => {
  let component: ReleaseNewComponent;
  let httpCtrl: HttpTestingController;
  let router: Router;

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TranslationService, useValue: tsMock },
      ],
    });

    const fixture = TestBed.createComponent(ReleaseNewComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
  });

  afterEach(() => httpCtrl.verify());

  describe('ngOnInit', () => {
    it('should load projects on init', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/projects').flush(mockProjects);
      expect(component.projects()).toEqual(mockProjects);
      expect(component.projectsLoading()).toBe(false);
    });

    it('should set empty array on project load error', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/projects').flush('', { status: 500, statusText: 'Error' });
      expect(component.projects()).toEqual([]);
      expect(component.projectsLoading()).toBe(false);
    });
  });

  describe('submit', () => {
    beforeEach(() => {
      component.ngOnInit();
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
  });
});
