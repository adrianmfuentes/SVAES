import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';
import { ActivateAccountComponent } from './activate-account.component';
import { TranslationService } from '../../../core/i18n/translation.service';
import { AuthService } from '../../../core/services/auth.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

const authMock = {
  storeTokens: vi.fn(),
};

const routeMock = {
  snapshot: {
    queryParamMap: { get: vi.fn().mockReturnValue(null) },
  },
};

describe('ActivateAccountComponent', () => {
  let component: ActivateAccountComponent;
  let httpCtrl: HttpTestingController;

  const fillValid = () => {
    component.activateForm.patchValue({
      activation_code: 'TOKEN123',
      password: 'Secure1!',
      password_confirm: 'Secure1!',
    });
  };

  beforeEach(() => {
    vi.clearAllMocks();
    routeMock.snapshot.queryParamMap.get.mockReturnValue(null);
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TranslationService, useValue: tsMock },
        { provide: AuthService, useValue: authMock },
        { provide: ActivatedRoute, useValue: routeMock },
      ],
    });

    const fixture = TestBed.createComponent(ActivateAccountComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpCtrl?.verify();
    TestBed.resetTestingModule();
  });

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
    it('should not submit if form is invalid', () => {
      fillValid();
      component.activateForm.patchValue({ password: '' });
      component.onSubmit();
      httpCtrl.expectNone('/api/v1/auth/activate');
    });

    it('should not submit if loading is true', () => {
      fillValid();
      component.loading = true;
      component.onSubmit();
      httpCtrl.expectNone('/api/v1/auth/activate');
    });

    it('should POST and set activationSuccess on success', () => {
      fillValid();
      component.onSubmit();
      const req = httpCtrl.expectOne('/api/v1/auth/activate');
      expect(req.request.method).toBe('POST');
      req.flush({ access_token: 'access-tok' });
      expect(component.activationSuccess).toBe(true);
    });

    it('should set tokenExpired on 400 error', () => {
      fillValid();
      component.onSubmit();
      httpCtrl.expectOne('/api/v1/auth/activate').flush(
        { detail: 'Bad request' },
        { status: 400, statusText: 'Bad Request' },
      );
      expect(component.tokenExpired).toBe(true);
    });

    it('should set tokenExpired on 410 error', () => {
      fillValid();
      component.onSubmit();
      httpCtrl.expectOne('/api/v1/auth/activate').flush(
        { detail: 'Token expired' },
        { status: 410, statusText: 'Gone' }
      );
      expect(component.tokenExpired).toBe(true);
    });

    it('should set submitError on generic error', () => {
      fillValid();
      component.onSubmit();
      httpCtrl.expectOne('/api/v1/auth/activate').flush({}, { status: 500, statusText: 'Error' });
      expect(component.submitError).toBe('activate.error.generic');
    });
  });

  describe('showPassword / showConfirm toggles', () => {
    it('should toggle showPassword', () => {
      expect(component.showPassword()).toBe(false);
      component.showPassword.set(true);
      expect(component.showPassword()).toBe(true);
    });

    it('should toggle showConfirm', () => {
      expect(component.showConfirm()).toBe(false);
      component.showConfirm.set(true);
      expect(component.showConfirm()).toBe(true);
    });
  });

  describe('password subscription', () => {
    it('should update passwordChecks when password value changes', () => {
      component.activateForm.get('password')!.setValue('Abcd1234!');
      expect(component.passwordChecks.minLength).toBe(true);
      expect(component.passwordChecks.uppercase).toBe(true);
      expect(component.passwordChecks.number).toBe(true);
      expect(component.passwordChecks.specialChar).toBe(true);
    });

    it('should update passwordChecks for weak password via valueChanges', () => {
      component.activateForm.get('password')!.setValue('abc');
      expect(component.passwordChecks.minLength).toBe(false);
      expect(component.passwordChecks.uppercase).toBe(false);
      expect(component.passwordChecks.number).toBe(false);
      expect(component.passwordChecks.specialChar).toBe(false);
    });
  });

  describe('ngOnDestroy', () => {
    it('should unsubscribe from password subscription', () => {
      const sub = (component as any).passwordSub;
      const spy = vi.spyOn(sub, 'unsubscribe');
      component.ngOnDestroy();
      expect(spy).toHaveBeenCalled();
    });
  });

  describe('form validators', () => {
    it('should detect password mismatch via form-level validator', () => {
      component.activateForm.patchValue({
        password: 'Secure1!',
        password_confirm: 'Different1!',
      });
      expect(component.activateForm.hasError('mismatch')).toBe(true);
    });

    it('should not have mismatch error when passwords match', () => {
      component.activateForm.patchValue({
        password: 'Secure1!',
        password_confirm: 'Secure1!',
      });
      expect(component.activateForm.hasError('mismatch')).toBe(false);
    });

    it('should fail passwordStrength validator for weak password', () => {
      component.activateForm.get('password')!.setValue('weak');
      expect(component.activateForm.get('password')!.hasError('passwordStrength')).toBe(true);
    });

    it('should pass passwordStrength validator for strong password', () => {
      component.activateForm.get('password')!.setValue('Strong1!');
      expect(component.activateForm.get('password')!.hasError('passwordStrength')).toBe(false);
    });
  });

  describe('authService interaction', () => {
    it('should call authService.storeTokens on successful activation', () => {
      fillValid();
      component.onSubmit();
      const req = httpCtrl.expectOne('/api/v1/auth/activate');
      req.flush({ access_token: 'access-tok', refresh_token: 'refresh-tok' });
      expect(authMock.storeTokens).toHaveBeenCalledWith(
        { requires_2fa: false, access_token: 'access-tok', refresh_token: 'refresh-tok' },
        '',
      );
    });
  });

  describe('onSubmit', () => {
    it('should clear submitError before sending', () => {
      fillValid();
      component.submitError = 'previous error';
      component.onSubmit();
      expect(component.submitError).toBeNull();
    });
  });
});
