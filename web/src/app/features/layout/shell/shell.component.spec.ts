import { TestBed, ComponentFixture } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { AuthService } from '../../../core/services/auth.service';
import { ShellComponent } from './shell.component';

describe('ShellComponent', () => {
  let fixture: ComponentFixture<ShellComponent>;
  let component: ShellComponent;
  let authServiceMock: { isAdmin: ReturnType<typeof vi.fn>; logout: ReturnType<typeof vi.fn>; getUser: ReturnType<typeof vi.fn>; getUserRole: ReturnType<typeof vi.fn>; getOrganization: ReturnType<typeof vi.fn>; getMyOrganizations: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    authServiceMock = {
      isAdmin: vi.fn().mockReturnValue(false),
      logout: vi.fn(),
      getUser: vi.fn().mockReturnValue({ id: 'u1', email: 'test@test.com', display_name: 'Test' }),
      getUserRole: vi.fn().mockReturnValue('ADMIN'),
      getOrganization: vi.fn().mockReturnValue(of({ id: 'org-1', name: 'Test Org', slug: 'test-org' })),
      getMyOrganizations: vi.fn().mockReturnValue(of([{ organization_id: 'org-1', name: 'Test Org', is_active: true }])),
    };

    await TestBed.configureTestingModule({
      imports: [ShellComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authServiceMock },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ShellComponent);
    component = fixture.componentInstance;

    fixture.detectChanges();
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  describe('isAdmin', () => {
    it('should return true when authService.isAdmin returns true', () => {
      authServiceMock.isAdmin.mockReturnValue(true);

      expect(component.isAdmin).toBe(true);
    });

    it('should return false when authService.isAdmin returns false', () => {
      authServiceMock.isAdmin.mockReturnValue(false);

      expect(component.isAdmin).toBe(false);
    });
  });

  describe('logout', () => {
    it('should call authService.logout', () => {
      component.logout();

      expect(authServiceMock.logout).toHaveBeenCalled();
    });
  });
});
