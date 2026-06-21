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

    it('should return false for valid touched field', () => {
      component.requestForm.patchValue({ requester_name: 'Jane Smith' });
      component.requestForm.get('requester_name')?.markAsTouched();
      expect(component.fieldHasError('requester_name')).toBe(false);
    });

    it('should return false for non-existent field', () => {
      expect(component.fieldHasError('nonexistent_field')).toBe(false);
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

    it('should remove special characters from slug', () => {
      component.requestForm.patchValue({ organization_name: 'Hola & Mundo!' });
      component.updateSlug();
      expect(component.slugPreview()).toBe('hola-mundo');
    });

    it('should strip non-alphanumeric chars and collapse hyphens', () => {
      component.requestForm.patchValue({ organization_name: 'Test   Org___Name' });
      component.updateSlug();
      expect(component.slugPreview()).toBe('test-orgname');
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

    it('should mark step 1 fields as touched when invalid', () => {
      component.currentStep.set(1);
      component.handleFormSubmit();
      expect(component.requestForm.get('requester_name')?.touched).toBe(true);
      expect(component.requestForm.get('requester_email')?.touched).toBe(true);
    });

    it('should advance to step 3 when step 2 is valid', () => {
      component.requestForm.patchValue({ organization_name: 'Valid Org', organization_description: '' });
      component.currentStep.set(2);
      component.handleFormSubmit();
      expect(component.currentStep()).toBe(3);
    });

    it('should stay on step 2 if step 2 invalid', () => {
      component.currentStep.set(2);
      component.requestForm.patchValue({ organization_name: '' });
      component.handleFormSubmit();
      expect(component.currentStep()).toBe(2);
    });

    it('should mark step 2 fields as touched when invalid', () => {
      component.currentStep.set(2);
      component.handleFormSubmit();
      expect(component.requestForm.get('organization_name')?.touched).toBe(true);
      expect(component.requestForm.get('organization_description')?.touched).toBe(true);
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

    it('should set submission error on generic server error', () => {
      fillValid(component);
      component.onSubmit();
      httpCtrl.expectOne('/api/v1/access-requests').flush({}, { status: 503, statusText: 'Service Unavailable' });
      expect(component.errorMessage()).toBe('access_request.error.submission');
    });

    it('should not submit if form is invalid (markAllAsTouched)', () => {
      const spy = vi.spyOn(component.requestForm, 'markAllAsTouched');
      component.onSubmit();
      expect(spy).toHaveBeenCalled();
      httpCtrl.expectNone('/api/v1/access-requests');
    });

    it('should not submit if loading is true', () => {
      fillValid(component);
      component.loading.set(true);
      const spy = vi.spyOn(component.requestForm, 'markAllAsTouched');
      component.onSubmit();
      expect(spy).toHaveBeenCalled();
      httpCtrl.expectNone('/api/v1/access-requests');
    });
  });

  describe('handleFormSubmit step 3', () => {
    it('should call onSubmit when on step 3 and form is valid', () => {
      component.requestForm.patchValue({
        requester_name: 'Jane Smith',
        requester_email: 'jane@example.com',
        organization_name: 'Acme Corp',
        organization_description: 'A great company',
      });
      component.currentStep.set(3);
      component.handleFormSubmit();
      const req = httpCtrl.expectOne('/api/v1/access-requests');
      req.flush({ id: 'req-2' });
      expect(component.submitted()).toBe(true);
    });

    it('should markAllAsTouched when step 3 form is invalid', () => {
      component.currentStep.set(3);
      component.requestForm.patchValue({ requester_name: '' });
      const spy = vi.spyOn(component.requestForm, 'markAllAsTouched');
      component.handleFormSubmit();
      expect(spy).toHaveBeenCalled();
      httpCtrl.expectNone('/api/v1/access-requests');
    });
  });

  describe('loading state', () => {
    it('should set loading true during submission', () => {
      component.requestForm.patchValue({
        requester_name: 'Jane Smith',
        requester_email: 'jane@example.com',
        organization_name: 'Acme Corp',
        organization_description: 'A great company',
      });
      component.currentStep.set(3);
      component.handleFormSubmit();
      expect(component.loading()).toBe(true);
      httpCtrl.expectOne('/api/v1/access-requests');
    });

    it('should set loading false after error', () => {
      component.requestForm.patchValue({
        requester_name: 'Jane Smith',
        requester_email: 'jane@example.com',
        organization_name: 'Acme Corp',
        organization_description: 'A great company',
      });
      component.onSubmit();
      httpCtrl.expectOne('/api/v1/access-requests').flush({}, { status: 503, statusText: 'Service Unavailable' });
      expect(component.loading()).toBe(false);
    });
  });

  describe('handleFormSubmit step 2 markAsTouched', () => {
    it('should mark step 2 fields as touched when invalid', () => {
      component.currentStep.set(2);
      component.requestForm.patchValue({ organization_name: '' });
      component.handleFormSubmit();
      expect(component.requestForm.get('organization_name')?.touched).toBe(true);
      expect(component.requestForm.get('organization_description')?.touched).toBe(true);
      expect(component.currentStep()).toBe(2);
    });
  });

  describe('generateSlug edge cases (via updateSlug)', () => {
    it('should generate slug from normal name', () => {
      component.requestForm.patchValue({ organization_name: 'My Test Organization' });
      component.updateSlug();
      expect(component.slugPreview()).toBe('my-test-organization');
    });

    it('should handle name with special characters', () => {
      component.requestForm.patchValue({ organization_name: 'Test@#Company!' });
      component.updateSlug();
      expect(component.slugPreview()).toBe('testcompany');
    });

    it('should collapse multiple spaces into single hyphen', () => {
      component.requestForm.patchValue({ organization_name: 'Hello    World' });
      component.updateSlug();
      expect(component.slugPreview()).toBe('hello-world');
    });

    it('should preserve existing hyphens', () => {
      component.requestForm.patchValue({ organization_name: 'already-hyphenated-name' });
      component.updateSlug();
      expect(component.slugPreview()).toBe('already-hyphenated-name');
    });

    it('should strip leading and trailing hyphens', () => {
      component.requestForm.patchValue({ organization_name: '-Leading Trailing-' });
      component.updateSlug();
      expect(component.slugPreview()).toBe('leading-trailing');
    });

    it('should return empty string for empty input', () => {
      component.requestForm.patchValue({ organization_name: '' });
      component.updateSlug();
      expect(component.slugPreview()).toBe('');
    });
  });

  describe('handleFormSubmit step 1 with invalid email', () => {
    it('should mark fields as touched and stay on step 1 when email is invalid', () => {
      component.currentStep.set(1);
      component.requestForm.patchValue({ requester_name: 'Jane', requester_email: 'not-an-email' });
      component.handleFormSubmit();
      expect(component.requestForm.get('requester_name')?.touched).toBe(true);
      expect(component.requestForm.get('requester_email')?.touched).toBe(true);
      expect(component.currentStep()).toBe(1);
    });
  });

  describe('handleFormSubmit step 2 with over-500-char description', () => {
    it('should stay on step 2 and mark fields as touched when description exceeds 500 chars', () => {
      component.currentStep.set(2);
      component.requestForm.patchValue({
        organization_name: 'Valid Org',
        organization_description: 'x'.repeat(501),
      });
      component.handleFormSubmit();
      expect(component.currentStep()).toBe(2);
      expect(component.requestForm.get('organization_name')?.touched).toBe(true);
      expect(component.requestForm.get('organization_description')?.touched).toBe(true);
    });
  });

  describe('prevStep from step 3', () => {
    it('should go to step 2 when currentStep is 3', () => {
      component.currentStep.set(3);
      component.prevStep();
      expect(component.currentStep()).toBe(2);
    });
  });

  describe('updateSlug with non-latin characters', () => {
    it('should remove non-latin characters from slug', () => {
      component.requestForm.patchValue({ organization_name: '组织测试' });
      component.updateSlug();
      expect(component.slugPreview()).toBe('');
    });

    it('should keep latin characters and remove non-latin ones', () => {
      component.requestForm.patchValue({ organization_name: 'Empresa 组织' });
      component.updateSlug();
      expect(component.slugPreview()).toBe('empresa');
    });
  });

  describe('updateCharCount edge cases', () => {
    it('should set charCount to 0 for empty description', () => {
      component.requestForm.patchValue({ organization_description: '' });
      component.updateCharCount();
      expect(component.charCount()).toBe(0);
    });

    it('should set charCount for description over 500 chars', () => {
      component.requestForm.patchValue({ organization_description: 'x'.repeat(501) });
      component.updateCharCount();
      expect(component.charCount()).toBe(501);
    });
  });

  describe('onSubmit when response is null', () => {
    const fillValid = (comp: AccessRequestFormComponent) => {
      comp.requestForm.patchValue({
        requester_name: 'Jane Smith',
        requester_email: 'jane@example.com',
        organization_name: 'Acme Corp',
        organization_description: 'A great company',
      });
    };

    it('should not set submitted when catchError returns null response', () => {
      fillValid(component);
      component.onSubmit();
      httpCtrl.expectOne('/api/v1/access-requests').flush({}, { status: 0, statusText: '' });
      expect(component.submitted()).toBe(false);
      expect(component.loading()).toBe(false);
    });
  });

  describe('loading false after successful submission', () => {
    const fillValid = (comp: AccessRequestFormComponent) => {
      comp.requestForm.patchValue({
        requester_name: 'Jane Smith',
        requester_email: 'jane@example.com',
        organization_name: 'Acme Corp',
        organization_description: 'A great company',
      });
    };

    it('should set loading to false after successful submission', () => {
      fillValid(component);
      component.onSubmit();
      httpCtrl.expectOne('/api/v1/access-requests').flush({ id: 'req-1' });
      expect(component.loading()).toBe(false);
      expect(component.submitted()).toBe(true);
    });
  });

  describe('errorMessage cleared before new submission', () => {
    const fillValid = (comp: AccessRequestFormComponent) => {
      comp.requestForm.patchValue({
        requester_name: 'Jane Smith',
        requester_email: 'jane@example.com',
        organization_name: 'Acme Corp',
        organization_description: 'A great company',
      });
    };

    it('should clear errorMessage when starting a new submission', () => {
      fillValid(component);
      component.errorMessage.set('previous error');
      component.onSubmit();
      expect(component.errorMessage()).toBeNull();
      httpCtrl.expectOne('/api/v1/access-requests');
    });
  });

  describe('handleFormSubmit step 3 when loading is true', () => {
    it('should call markAllAsTouched and not submit when loading', () => {
      component.requestForm.patchValue({
        requester_name: 'Jane Smith',
        requester_email: 'jane@example.com',
        organization_name: 'Acme Corp',
        organization_description: 'A great company',
      });
      component.currentStep.set(3);
      component.loading.set(true);
      const spy = vi.spyOn(component.requestForm, 'markAllAsTouched');
      component.handleFormSubmit();
      expect(spy).toHaveBeenCalled();
      httpCtrl.expectNone('/api/v1/access-requests');
    });
  });

  describe('onSubmit sets loading and clears errorMessage', () => {
    const fillValid = (comp: AccessRequestFormComponent) => {
      comp.requestForm.patchValue({
        requester_name: 'Jane Smith',
        requester_email: 'jane@example.com',
        organization_name: 'Acme Corp',
        organization_description: 'A great company',
      });
    };

    it('should set loading to true and errorMessage to null before making request', () => {
      fillValid(component);
      component.errorMessage.set('previous error');
      component.onSubmit();
      expect(component.loading()).toBe(true);
      expect(component.errorMessage()).toBeNull();
      httpCtrl.expectOne('/api/v1/access-requests');
    });
  });
});
