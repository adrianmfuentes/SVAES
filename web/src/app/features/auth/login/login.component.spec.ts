import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';
import { provideRouter, Router } from '@angular/router';
import { LoginComponent } from './login.component';
import { AuthService } from '../../../core/services/auth.service';
import { TranslationService } from '../../../core/i18n/translation.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

const authMock = {
  isAuthenticated: vi.fn().mockReturnValue(false),
  isAdmin: vi.fn().mockReturnValue(false),
  login: vi.fn(),
  verify2fa: vi.fn(),
  storeTokens: vi.fn(),
};

describe('LoginComponent', () => {
  let component: LoginComponent;
  let router: Router;

  beforeEach(() => {
    vi.clearAllMocks();
    authMock.isAuthenticated.mockReturnValue(false);
    authMock.isAdmin.mockReturnValue(false);
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authMock },
        { provide: TranslationService, useValue: tsMock },
      ],
    });

    const fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
  });

  describe('ngOnInit', () => {
    it('should redirect to dashboard if already authenticated', () => {
      const navSpy = vi.spyOn(router, 'navigate');
      authMock.isAuthenticated.mockReturnValue(true);
      component.ngOnInit();
      expect(navSpy).toHaveBeenCalledWith(['/app/dashboard']);
    });

    it('should not redirect if not authenticated', () => {
      const navSpy = vi.spyOn(router, 'navigate');
      component.ngOnInit();
      expect(navSpy).not.toHaveBeenCalled();
    });
  });

  describe('fieldHasError', () => {
    it('should return false when field is pristine', () => {
      expect(component.fieldHasError('email')).toBe(false);
    });

    it('should return true when field is invalid and touched', () => {
      const ctrl = component.loginForm.get('email')!;
      ctrl.markAsTouched();
      expect(component.fieldHasError('email')).toBe(true);
    });
  });

  describe('onSubmit', () => {
    it('should mark all touched if form is invalid', () => {
      const spy = vi.spyOn(component.loginForm, 'markAllAsTouched');
      component.onSubmit();
      expect(spy).toHaveBeenCalled();
      expect(authMock.login).not.toHaveBeenCalled();
    });

    it('should navigate to dashboard on successful login', () => {
      const navSpy = vi.spyOn(router, 'navigate');
      authMock.login.mockReturnValue(of({ access_token: 'tok', refresh_token: 'ref', requires_2fa: false }));
      component.loginForm.setValue({ email: 'user@test.com', password: 'pass123' });
      component.onSubmit();
      expect(authMock.login).toHaveBeenCalledWith('user@test.com', 'pass123');
      expect(authMock.storeTokens).toHaveBeenCalled();
      expect(navSpy).toHaveBeenCalledWith(['/app/dashboard']);
    });

    it('should navigate to /app/system for admin login', () => {
      const navSpy = vi.spyOn(router, 'navigate');
      authMock.isAdmin.mockReturnValue(true);
      authMock.login.mockReturnValue(of({ access_token: 'tok', refresh_token: 'ref', requires_2fa: false }));
      component.loginForm.setValue({ email: 'admin@test.com', password: 'admin123' });
      component.onSubmit();
      expect(navSpy).toHaveBeenCalledWith(['/app/system']);
    });

    it('should set totpRequired when response requires_2fa', () => {
      authMock.login.mockReturnValue(of({ requires_2fa: true, totp_token: 'totp-tok' }));
      component.loginForm.setValue({ email: 'user@test.com', password: 'pass' });
      component.onSubmit();
      expect(component.totpRequired).toBe(true);
    });

    it('should set errorKey on HTTP error (401)', () => {
      const err = new HttpErrorResponse({ status: 401 });
      authMock.login.mockReturnValue(throwError(() => err));
      component.loginForm.setValue({ email: 'x@x.com', password: 'wrong' });
      component.onSubmit();
      expect(component.errorKey).toMatch(/login\.error\.(invalid_credentials|wrong_credentials)/);
    });

    it('should set no_connection error key for status 0', () => {
      const err = new HttpErrorResponse({ status: 0 });
      authMock.login.mockReturnValue(throwError(() => err));
      component.loginForm.setValue({ email: 'x@x.com', password: 'wrong' });
      component.onSubmit();
      expect(component.errorKey).toBe('login.error.no_connection');
    });
  });

  describe('onSubmitTotp', () => {
    it('should mark totp form touched if invalid', () => {
      const spy = vi.spyOn(component.totpForm, 'markAllAsTouched');
      component.onSubmitTotp();
      expect(spy).toHaveBeenCalled();
      expect(authMock.verify2fa).not.toHaveBeenCalled();
    });

    it('should call verify2fa and navigate on success', () => {
      const navSpy = vi.spyOn(router, 'navigate');
      authMock.verify2fa.mockReturnValue(of({ access_token: 'tok', refresh_token: 'ref' }));
      (component as any).pendingTotpToken = 'pending-totp';
      component.totpForm.setValue({ code: '123456' });
      component.onSubmitTotp();
      expect(authMock.verify2fa).toHaveBeenCalledWith('pending-totp', '123456');
      expect(navSpy).toHaveBeenCalledWith(['/app/dashboard']);
    });
  });

  describe('backToLogin', () => {
    it('should reset totpRequired and clear errorKey', () => {
      component.totpRequired = true;
      component.errorKey = 'some.error';
      component.totpForm.setValue({ code: '123456' });
      component.backToLogin();
      expect(component.totpRequired).toBe(false);
      expect(component.errorKey).toBeNull();
      expect(component.totpForm.value.code).toBeNull();
    });
  });

  describe('parseLoginErrorKey via onSubmit', () => {
    beforeEach(() => {
      component.loginForm.setValue({ email: 'x@x.com', password: 'pass' });
    });

    it('should set pending_activation error for 403', () => {
      authMock.login.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 403 })));
      component.onSubmit();
      expect(component.errorKey).toBe('login.error.pending_activation');
    });

    it('should set too_many error for 429', () => {
      authMock.login.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 429 })));
      component.onSubmit();
      expect(component.errorKey).toBe('login.error.too_many');
    });

    it('should set server error for 502', () => {
      authMock.login.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 502 })));
      component.onSubmit();
      expect(component.errorKey).toMatch(/login\.error\./);
    });

    it('should set server error for 504', () => {
      authMock.login.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 504 })));
      component.onSubmit();
      expect(component.errorKey).toMatch(/login\.error\./);
    });

    it('should use 401 detail message when short', () => {
      authMock.login.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 401, error: { detail: 'Cuenta desactivada' } })));
      component.onSubmit();
      expect(component.errorKey).toBe('Cuenta desactivada');
    });

    it('should return wrong_credentials for 401 without detail', () => {
      authMock.login.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 401, error: {} })));
      component.onSubmit();
      expect(component.errorKey).toBe('login.error.wrong_credentials');
    });
  });

  describe('onSubmitTotp errors', () => {
    it('should set error on verify2fa failure', () => {
      authMock.verify2fa.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 401, error: {} })));
      (component as any).pendingTotpToken = 'pending-totp';
      component.totpForm.setValue({ code: '999999' });
      component.onSubmitTotp();
      expect(authMock.verify2fa).toHaveBeenCalled();
      expect(component.errorKey).toMatch(/login\.error\./);
    });

    it('should not call verify2fa when totpForm invalid', () => {
      (component as any).pendingTotpToken = 'pending-totp';
      component.totpForm.setValue({ code: '' });
      component.onSubmitTotp();
      expect(authMock.verify2fa).not.toHaveBeenCalled();
    });

    it('should navigate to /app/system for admin after TOTP', () => {
      const navSpy = vi.spyOn(router, 'navigate');
      authMock.isAdmin.mockReturnValue(true);
      authMock.verify2fa.mockReturnValue(of({ access_token: 'tok', refresh_token: 'ref' }));
      (component as any).pendingTotpToken = 'pending-totp';
      component.totpForm.setValue({ code: '123456' });
      component.onSubmitTotp();
      expect(navSpy).toHaveBeenCalledWith(['/app/system']);
    });
  });
});
