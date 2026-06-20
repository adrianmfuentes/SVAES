import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, ActivatedRoute } from '@angular/router';
import { of } from 'rxjs';
import { ResetPasswordComponent } from './reset-password.component';
import { TranslationService } from '../../../core/i18n/translation.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

describe('ResetPasswordComponent', () => {
  let component: ResetPasswordComponent;
  let httpCtrl: HttpTestingController;

  const routeMock = {
    snapshot: {
      queryParamMap: {
        get: vi.fn().mockReturnValue(null),
      },
    },
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
        { provide: ActivatedRoute, useValue: routeMock },
      ],
    });

    const fixture = TestBed.createComponent(ResetPasswordComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpCtrl?.verify();
    TestBed.resetTestingModule();
  });

  it('should create with initial state', () => {
    expect(component.token).toBeNull();
    expect(component.loading).toBe(false);
    expect(component.done).toBe(false);
    expect(component.errorKey).toBeNull();
  });

  describe('form validators', () => {
    describe('passwordStrengthValidator', () => {
      it('should return null for a strong password', () => {
        const ctrl = component.form.controls.password;
        ctrl.setValue('Abcd1234!');
        expect(ctrl.errors).toBeNull();
      });

      it('should return error for too short password', () => {
        const ctrl = component.form.controls.password;
        ctrl.setValue('Ab1!');
        expect(ctrl.errors).toEqual({ passwordStrength: true });
      });

      it('should return error for password without uppercase', () => {
        const ctrl = component.form.controls.password;
        ctrl.setValue('abcd1234!');
        expect(ctrl.errors).toEqual({ passwordStrength: true });
      });

      it('should return error for password without number', () => {
        const ctrl = component.form.controls.password;
        ctrl.setValue('Abcdefgh!');
        expect(ctrl.errors).toEqual({ passwordStrength: true });
      });

      it('should return error for password without special char', () => {
        const ctrl = component.form.controls.password;
        ctrl.setValue('Abcd1234');
        expect(ctrl.errors).toEqual({ passwordStrength: true });
      });

      it('should return both required and passwordStrength errors for empty value', () => {
        const ctrl = component.form.controls.password;
        ctrl.setValue('');
        expect(ctrl.errors).toEqual({ required: true, passwordStrength: true });
      });
    });

    describe('passwordMatchValidator', () => {
      it('should return null when passwords match', () => {
        component.form.patchValue({
          password: 'Abcd1234!',
          password_confirm: 'Abcd1234!',
        });
        expect(component.form.errors).toBeNull();
      });

      it('should return mismatch error when passwords differ', () => {
        component.form.patchValue({
          password: 'Abcd1234!',
          password_confirm: 'Different1!',
        });
        expect(component.form.errors).toEqual({ mismatch: true });
      });

      it('should return null when both controls are empty', () => {
        component.form.patchValue({
          password: '',
          password_confirm: '',
        });
        expect(component.form.errors).toBeNull();
      });
    });
  });

  describe('ngOnInit', () => {
    it('should set token to null when no token in query params', () => {
      component.ngOnInit();
      expect(component.token).toBeNull();
    });

    it('should set token when token param present', () => {
      routeMock.snapshot.queryParamMap.get.mockReturnValue('reset-token-123');
      component.ngOnInit();
      expect(component.token).toBe('reset-token-123');
    });
  });

  describe('onSubmit', () => {
    const fillValid = () => {
      component.token = 'valid-token';
      component.form.patchValue({
        password: 'Abcd1234!',
        password_confirm: 'Abcd1234!',
      });
    };

    it('should not submit if form is invalid (markAllAsTouched)', () => {
      component.token = 'token';
      component.form.patchValue({ password: 'weak' });
      const spy = vi.spyOn(component.form, 'markAllAsTouched');
      component.onSubmit();
      expect(spy).toHaveBeenCalled();
      httpCtrl.expectNone('/api/v1/auth/reset-password');
    });

    it('should not submit if loading is true', () => {
      fillValid();
      component.loading = true;
      const spy = vi.spyOn(component.form, 'markAllAsTouched');
      component.onSubmit();
      expect(spy).toHaveBeenCalled();
      httpCtrl.expectNone('/api/v1/auth/reset-password');
    });

    it('should not submit if no token', () => {
      component.form.patchValue({
        password: 'Abcd1234!',
        password_confirm: 'Abcd1234!',
      });
      component.token = null;
      const spy = vi.spyOn(component.form, 'markAllAsTouched');
      component.onSubmit();
      expect(spy).toHaveBeenCalled();
      httpCtrl.expectNone('/api/v1/auth/reset-password');
    });

    it('should POST and set done on success', () => {
      fillValid();
      component.onSubmit();
      expect(component.loading).toBe(true);
      expect(component.errorKey).toBeNull();
      const req = httpCtrl.expectOne('/api/v1/auth/reset-password');
      expect(req.request.method).toBe('POST');
      expect(req.request.body.token).toBe('valid-token');
      req.flush({});
      expect(component.done).toBe(true);
      expect(component.loading).toBe(false);
    });

    it('should set expired_token error on 410', () => {
      fillValid();
      component.onSubmit();
      httpCtrl.expectOne('/api/v1/auth/reset-password').flush(
        { detail: 'expired' },
        { status: 410, statusText: 'Gone' },
      );
      expect(component.errorKey).toBe('reset_password.error.expired_token');
      expect(component.loading).toBe(false);
    });

    it('should set invalid_token error on 400', () => {
      fillValid();
      component.onSubmit();
      httpCtrl.expectOne('/api/v1/auth/reset-password').flush(
        { detail: 'invalid' },
        { status: 400, statusText: 'Bad Request' },
      );
      expect(component.errorKey).toBe('reset_password.error.invalid_token');
      expect(component.loading).toBe(false);
    });

    it('should set internal error on other errors', () => {
      fillValid();
      component.onSubmit();
      httpCtrl.expectOne('/api/v1/auth/reset-password').flush(
        {},
        { status: 500, statusText: 'Internal Server Error' },
      );
      expect(component.errorKey).toBe('reset_password.error.internal');
      expect(component.loading).toBe(false);
    });
  });
});
