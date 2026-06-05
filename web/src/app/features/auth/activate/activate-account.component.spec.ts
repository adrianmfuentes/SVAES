import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { ActivatedRoute } from '@angular/router';
import { convertToParamMap } from '@angular/router';
import { of } from 'rxjs';
import { ActivateAccountComponent } from './activate-account.component';
import { TranslationService } from '../../../core/i18n/translation.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

const routeMock = {
  snapshot: {
    queryParamMap: { get: vi.fn().mockReturnValue(null) },
  },
};

describe('ActivateAccountComponent', () => {
  let component: ActivateAccountComponent;
  let httpCtrl: HttpTestingController;
  let router: Router;

  beforeEach(() => {
    vi.clearAllMocks();
    routeMock.snapshot.queryParamMap.get.mockReturnValue(null);
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TranslationService, useValue: tsMock },
        { provide: ActivatedRoute, useValue: routeMock },
      ],
    });

    const fixture = TestBed.createComponent(ActivateAccountComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
  });

  afterEach(() => httpCtrl.verify());

  describe('ngOnInit', () => {
    it('should stay on step 1 when no token in query params', () => {
      component.ngOnInit();
      expect(component.step()).toBe(1);
    });

    it('should skip to step 2 when token param present', () => {
      routeMock.snapshot.queryParamMap.get.mockReturnValue('mytoken123');
      component.ngOnInit();
      expect(component.step()).toBe(2);
      expect(component.activateForm.value.activation_code).toBe('mytoken123');
    });
  });

  describe('nextStep', () => {
    it('should not advance if activation_code is empty', () => {
      component.activateForm.patchValue({ activation_code: '' });
      component.nextStep();
      expect(component.step()).toBe(1);
    });

    it('should advance to step 2 when activation_code is valid', () => {
      component.activateForm.patchValue({ activation_code: 'VALID-TOKEN' });
      component.nextStep();
      expect(component.step()).toBe(2);
    });
  });

  describe('prevStep', () => {
    it('should return to step 1 and clear submitError', () => {
      component.step.set(2);
      component.submitError = 'some error';
      component.prevStep();
      expect(component.step()).toBe(1);
      expect(component.submitError).toBeNull();
    });
  });

  describe('updatePasswordChecks', () => {
    it('should update all checks for a strong password', () => {
      (component as any).updatePasswordChecks('Abcd1234!');
      expect(component.passwordChecks.minLength).toBe(true);
      expect(component.passwordChecks.uppercase).toBe(true);
      expect(component.passwordChecks.number).toBe(true);
      expect(component.passwordChecks.specialChar).toBe(true);
    });

    it('should fail checks for a weak password', () => {
      (component as any).updatePasswordChecks('abc');
      expect(component.passwordChecks.minLength).toBe(false);
      expect(component.passwordChecks.uppercase).toBe(false);
      expect(component.passwordChecks.number).toBe(false);
    });
  });

  describe('onSubmit', () => {
    beforeEach(() => {
      component.activateForm.patchValue({
        activation_code: 'TOKEN123',
        password: 'Secure1!',
        password_confirm: 'Secure1!',
      });
    });

    it('should not submit if form is invalid', () => {
      component.activateForm.patchValue({ password: '' });
      component.onSubmit();
      httpCtrl.expectNone('/api/v1/auth/activate');
    });

    it('should POST and set activationSuccess on success', () => {
      component.onSubmit();
      const req = httpCtrl.expectOne('/api/v1/auth/activate');
      expect(req.request.method).toBe('POST');
      req.flush({ access_token: 'access-tok' });
      expect(component.activationSuccess).toBe(true);
    });

    it('should set tokenExpired on 410 error', () => {
      component.onSubmit();
      httpCtrl.expectOne('/api/v1/auth/activate').flush(
        { detail: 'Token expired' },
        { status: 410, statusText: 'Gone' }
      );
      expect(component.tokenExpired).toBe(true);
    });

    it('should set submitError on generic error', () => {
      component.onSubmit();
      httpCtrl.expectOne('/api/v1/auth/activate').flush({}, { status: 500, statusText: 'Error' });
      expect(component.submitError).toBe('activate.error.generic');
    });
  });
});
