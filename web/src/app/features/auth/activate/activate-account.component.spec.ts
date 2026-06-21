import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';
import { FormBuilder, FormControl } from '@angular/forms';
import { ActivateAccountComponent, passwordMatchValidator, passwordStrengthValidator } from './activate-account.component';
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
      httpCtrl.expectOne('/api/v1/auth/activate').flush({}, { status: 500, statusText: 'Error' });
    });
  });

  describe('onSubmit loading behavior', () => {
    it('should set loading to true during request and false after via finalize', () => {
      fillValid();
      component.onSubmit();
      expect(component.loading).toBe(true);
      const req = httpCtrl.expectOne('/api/v1/auth/activate');
      req.flush({ access_token: 'access-tok' });
      expect(component.loading).toBe(false);
    });

    it('should set loading to false after error via finalize', () => {
      fillValid();
      component.onSubmit();
      expect(component.loading).toBe(true);
      const req = httpCtrl.expectOne('/api/v1/auth/activate');
      req.flush({}, { status: 500, statusText: 'Error' });
      expect(component.loading).toBe(false);
    });
  });

  describe('prevStep at step 1', () => {
    it('should clear submitError when already at step 1', () => {
      component.step.set(1);
      component.submitError = 'existing error';
      component.prevStep();
      expect(component.submitError).toBeNull();
    });
  });

  describe('constructor initialization', () => {
    it('should initialize passwordChecks with all false', () => {
      expect(component.passwordChecks).toEqual({
        minLength: false,
        uppercase: false,
        number: false,
        specialChar: false,
      });
    });

    it('should set up passwordSub in constructor', () => {
      const sub = (component as any).passwordSub;
      expect(sub).toBeDefined();
      expect(typeof sub.unsubscribe).toBe('function');
    });
  });

  describe('ngOnInit with token field marking', () => {
    it('should patch activation_code and advance to step 2 when token present', () => {
      routeMock.snapshot.queryParamMap.get.mockReturnValue('abc-token-123');
      component.ngOnInit();
      expect(component.step()).toBe(2);
      expect(component.activateForm.get('activation_code')?.value).toBe('abc-token-123');
    });
  });

  describe('nextStep marks field', () => {
    it('should mark activation_code as touched', () => {
      component.activateForm.patchValue({ activation_code: 'VALID' });
      const control = component.activateForm.get('activation_code')!;
      expect(control.touched).toBe(false);
      component.nextStep();
      expect(control.touched).toBe(true);
    });
  });

  describe('onSubmit network error', () => {
    it('should handle network error with status 0', () => {
      fillValid();
      component.onSubmit();
      const req = httpCtrl.expectOne('/api/v1/auth/activate');
      req.error(new ProgressEvent('error'));
      expect(component.submitError).toBe('activate.error.generic');
    });
  });

  describe('passwordMatchValidator', () => {
    it('should return null when passwords match', () => {
      const fb = new FormBuilder();
      const group = fb.group(
        { password: ['abc'], password_confirm: ['abc'] },
        { validators: passwordMatchValidator },
      );
      expect(group.hasError('mismatch')).toBe(false);
    });

    it('should return mismatch error when passwords differ', () => {
      const fb = new FormBuilder();
      const group = fb.group(
        { password: ['abc'], password_confirm: ['def'] },
        { validators: passwordMatchValidator },
      );
      expect(group.hasError('mismatch')).toBe(true);
    });

    it('should return null when controls are missing', () => {
      const fb = new FormBuilder();
      const group = fb.group({}, { validators: passwordMatchValidator });
      expect(group.errors).toBeNull();
    });
  });

  describe('passwordStrengthValidator', () => {
    it('should return null for strong password', () => {
      const control = new FormControl('Strong1!', passwordStrengthValidator);
      expect(control.hasError('passwordStrength')).toBe(false);
    });

    it('should return passwordStrength error for weak password', () => {
      const control = new FormControl('weak', passwordStrengthValidator);
      expect(control.hasError('passwordStrength')).toBe(true);
    });

    it('should return passwordStrength error for empty value', () => {
      const control = new FormControl('', passwordStrengthValidator);
      expect(control.hasError('passwordStrength')).toBe(true);
    });

    it('should return passwordStrength error when missing uppercase', () => {
      const control = new FormControl('abcdefg1!', passwordStrengthValidator);
      expect(control.hasError('passwordStrength')).toBe(true);
    });

    it('should return passwordStrength error when missing number', () => {
      const control = new FormControl('Abcdefgh!', passwordStrengthValidator);
      expect(control.hasError('passwordStrength')).toBe(true);
    });

    it('should return passwordStrength error when missing special char', () => {
      const control = new FormControl('Abcdefg1', passwordStrengthValidator);
      expect(control.hasError('passwordStrength')).toBe(true);
    });
  });

  describe('onSubmit extracts form values', () => {
    it('should extract activation_code, password, and password_confirm from form', () => {
      fillValid();
      component.onSubmit();
      const req = httpCtrl.expectOne('/api/v1/auth/activate');
      expect(req.request.body).toEqual({
        activation_token: 'TOKEN123',
        password: 'Secure1!',
        password_confirm: 'Secure1!',
      });
      req.flush({ access_token: 'access-tok' });
    });
  });

  describe('showPassword and showConfirm initial state', () => {
    it('should have showPassword default to false on new instance', () => {
      const newFixture = TestBed.createComponent(ActivateAccountComponent);
      const newComp = newFixture.componentInstance;
      expect(newComp.showPassword()).toBe(false);
    });

    it('should have showConfirm default to false on new instance', () => {
      const newFixture = TestBed.createComponent(ActivateAccountComponent);
      const newComp = newFixture.componentInstance;
      expect(newComp.showConfirm()).toBe(false);
    });
  });
});
