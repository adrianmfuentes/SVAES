import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { AccessRequestFormComponent } from './access-request-form.component';
import { TranslationService } from '../../core/i18n/translation.service';
import { provideRouter } from '@angular/router';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

describe('AccessRequestFormComponent', () => {
  let component: AccessRequestFormComponent;
  let httpCtrl: HttpTestingController;

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

    const fixture = TestBed.createComponent(AccessRequestFormComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpCtrl.verify());

  describe('step1Valid / step2Valid', () => {
    it('step1Valid should be false when fields are empty', () => {
      expect(component.step1Valid).toBe(false);
    });

    it('step1Valid should be true when requester_name and requester_email are valid', () => {
      component.requestForm.patchValue({ requester_name: 'Jane Smith', requester_email: 'jane@example.com' });
      expect(component.step1Valid).toBe(true);
    });

    it('step2Valid should be false when organization_name is empty', () => {
      expect(component.step2Valid).toBe(false);
    });

    it('step2Valid should be true when organization_name is valid', () => {
      component.requestForm.patchValue({ organization_name: 'Acme Corp', organization_description: '' });
      expect(component.step2Valid).toBe(true);
    });
  });

  describe('fieldHasError', () => {
    it('should return false for pristine field', () => {
      expect(component.fieldHasError('requester_name')).toBe(false);
    });

    it('should return true for touched invalid field', () => {
      component.requestForm.get('requester_name')?.markAsTouched();
      expect(component.fieldHasError('requester_name')).toBe(true);
    });
  });

  describe('updateSlug', () => {
    it('should set slugPreview based on organization_name', () => {
      component.requestForm.patchValue({ organization_name: 'Acme Corp' });
      component.updateSlug();
      expect(component.slugPreview()).toBe('acme-corp');
    });

    it('should handle empty organization_name', () => {
      component.requestForm.patchValue({ organization_name: '' });
      component.updateSlug();
      expect(component.slugPreview()).toBe('');
    });
  });

  describe('updateCharCount', () => {
    it('should update charCount to description length', () => {
      component.requestForm.patchValue({ organization_description: 'Hello world' });
      component.updateCharCount();
      expect(component.charCount()).toBe(11);
    });
  });

  describe('prevStep', () => {
    it('should decrease currentStep when > 1', () => {
      component.currentStep.set(2);
      component.prevStep();
      expect(component.currentStep()).toBe(1);
    });

    it('should not go below step 1', () => {
      component.currentStep.set(1);
      component.prevStep();
      expect(component.currentStep()).toBe(1);
    });
  });

  describe('handleFormSubmit', () => {
    it('should advance to step 2 when step 1 is valid', () => {
      component.requestForm.patchValue({ requester_name: 'Jane Smith', requester_email: 'jane@example.com' });
      component.currentStep.set(1);
      component.handleFormSubmit();
      expect(component.currentStep()).toBe(2);
    });

    it('should stay on step 1 if step 1 invalid', () => {
      component.currentStep.set(1);
      component.handleFormSubmit();
      expect(component.currentStep()).toBe(1);
    });

    it('should advance to step 3 when step 2 is valid', () => {
      component.requestForm.patchValue({ organization_name: 'Valid Org', organization_description: '' });
      component.currentStep.set(2);
      component.handleFormSubmit();
      expect(component.currentStep()).toBe(3);
    });
  });

  describe('onSubmit', () => {
    const fillValid = (comp: AccessRequestFormComponent) => {
      comp.requestForm.patchValue({
        requester_name: 'Jane Smith',
        requester_email: 'jane@example.com',
        organization_name: 'Acme Corp',
        organization_description: 'A great company',
      });
    };

    it('should POST and set submitted on success', () => {
      fillValid(component);
      component.onSubmit();
      const req = httpCtrl.expectOne('/api/v1/access-requests');
      expect(req.request.method).toBe('POST');
      req.flush({ id: 'req-1' });
      expect(component.submitted()).toBe(true);
    });

    it('should set conflict error on 409', () => {
      fillValid(component);
      component.onSubmit();
      httpCtrl.expectOne('/api/v1/access-requests').flush({}, { status: 409, statusText: 'Conflict' });
      expect(component.errorMessage()).toBe('access_request.error.conflict');
    });

    it('should set no_connection error on status 0', () => {
      fillValid(component);
      component.onSubmit();
      httpCtrl.expectOne('/api/v1/access-requests').flush({}, { status: 0, statusText: '' });
      expect(component.errorMessage()).toBe('login.error.no_connection');
    });
  });
});
