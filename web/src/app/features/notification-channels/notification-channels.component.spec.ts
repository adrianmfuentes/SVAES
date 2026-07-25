import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { NotificationChannelsComponent } from './notification-channels.component';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
import { ToastService } from '../../core/services/toast.service';
import { provideRouter } from '@angular/router';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

const authMock = {
  isAdmin: vi.fn().mockReturnValue(false),
  getUserRole: vi.fn().mockReturnValue('MANAGER'),
  getUser: vi.fn().mockReturnValue({ id: 'u1', organization_id: 'org-abc' }),
};

const toastMock = {
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
};

const mockChannelTypesResponse = {
  channel_types: ['SLACK', 'MS_TEAMS', 'GENERIC'],
  config_schemas: {
    SLACK: {
      webhook_url: { type: 'string', label: 'notification_channels.field.webhook_url', required: true },
    },
    MS_TEAMS: {
      webhook_url: { type: 'string', label: 'notification_channels.field.webhook_url', required: true },
    },
    GENERIC: {
      url: { type: 'string', label: 'notification_channels.field.url', required: true },
      signing_secret: { type: 'string', label: 'notification_channels.field.signing_secret', required: false, sensitive: true },
    },
  },
};

const mockChannel = {
  id: 'ch-1',
  organization_id: 'org-abc',
  channel_type: 'SLACK',
  enabled: true,
  config_data: { webhook_url: 'https://hooks.slack.com/test' },
  configured: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const loadAllRequests = (httpCtrl: HttpTestingController, channels?: unknown[]) => {
  httpCtrl.expectOne('/api/v1/notifications/channel-types').flush(mockChannelTypesResponse);
  httpCtrl.expectOne('/api/v1/notifications/channels').flush(channels ?? [mockChannel]);
};

describe('NotificationChannelsComponent', () => {
  let component: NotificationChannelsComponent;
  let fixture: ComponentFixture<NotificationChannelsComponent>;
  let httpCtrl: HttpTestingController;

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authMock },
        { provide: TranslationService, useValue: tsMock },
        { provide: ToastService, useValue: toastMock },
      ],
    });

    fixture = TestBed.createComponent(NotificationChannelsComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpCtrl?.verify();
    TestBed.resetTestingModule();
  });

  describe('ngOnInit', () => {
    it('should load channel types and channels', () => {
      component.ngOnInit();
      loadAllRequests(httpCtrl);
      expect(component.loading()).toBe(false);
      expect(component.channels()).toHaveLength(1);
      expect(Object.keys(component.configSchemas())).toHaveLength(3);
    });

    it('should set error when channel types fail', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/notifications/channel-types').flush('', { status: 500, statusText: 'Error' });
      expect(component.error()).toBe('notification_channels.loading_error');
    });

    it('should set error when channels fail', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/notifications/channel-types').flush(mockChannelTypesResponse);
      httpCtrl.expectOne('/api/v1/notifications/channels').flush('', { status: 500, statusText: 'Error' });
      expect(component.error()).toBe('notification_channels.loading_error');
    });
  });

  describe('channelFor', () => {
    it('should return undefined when no channels loaded', () => {
      expect(component.channelFor('SLACK')).toBeUndefined();
    });

    it('should return matching channel', () => {
      component.channels.set([mockChannel]);
      expect(component.channelFor('SLACK')).toEqual(mockChannel);
    });
  });

  describe('schemaFields', () => {
    it('should return fields for a type', () => {
      component.configSchemas.set(mockChannelTypesResponse.config_schemas);
      const fields = component.schemaFields('SLACK');
      expect(fields).toHaveLength(1);
      expect(fields[0][0]).toBe('webhook_url');
    });

    it('should return empty array for unknown type', () => {
      component.configSchemas.set(mockChannelTypesResponse.config_schemas);
      const fields = component.schemaFields('UNKNOWN');
      expect(fields).toHaveLength(0);
    });
  });

  describe('typeLabel', () => {
    it('should call translation service with type prefix', () => {
      component.typeLabel('SLACK');
      expect(tsMock.translateInstant).toHaveBeenCalledWith('notification_channels.type.SLACK');
    });
  });

  describe('fieldLabel', () => {
    it('should call translation service with label', () => {
      component.fieldLabel({ type: 'string', label: 'test.label', required: false });
      expect(tsMock.translateInstant).toHaveBeenCalledWith('test.label');
    });
  });

  describe('save', () => {
    beforeEach(() => {
      component.ngOnInit();
      loadAllRequests(httpCtrl);
    });

    it('should POST new channel', () => {
      const form = component.forms['GENERIC'];
      form.controls['url'].setValue('https://example.com/webhook');
      component.save('GENERIC');
      const req = httpCtrl.expectOne('/api/v1/notifications/channels');
      expect(req.request.method).toBe('POST');
      req.flush({ id: 'new-ch' });
      expect(toastMock.success).toHaveBeenCalled();
      loadAllRequests(httpCtrl);
    });

    it('should PATCH existing channel', () => {
      component.save('SLACK');
      const req = httpCtrl.expectOne('/api/v1/notifications/channels/ch-1');
      expect(req.request.method).toBe('PATCH');
      req.flush({ id: 'ch-1' });
      loadAllRequests(httpCtrl);
    });

    it('should show error toast on failure', () => {
      component.save('SLACK');
      httpCtrl.expectOne('/api/v1/notifications/channels/ch-1').flush(
        { detail: 'Save failed' },
        { status: 400, statusText: 'Bad Request' }
      );
      expect(toastMock.error).toHaveBeenCalledWith('Save failed');
    });

    it('should not submit if form is invalid', () => {
      component.forms['SLACK'].controls['webhook_url'].setValue('');
      component.forms['SLACK'].controls['webhook_url'].markAsTouched();
      component.save('SLACK');
      httpCtrl.expectNone('/api/v1/notifications/channels/ch-1');
      expect(component.forms['SLACK'].invalid).toBeTruthy();
    });
  });

  describe('sendTest', () => {
    beforeEach(() => {
      component.ngOnInit();
      loadAllRequests(httpCtrl);
    });

    it('should send test notification', () => {
      component.sendTest('SLACK');
      const req = httpCtrl.expectOne('/api/v1/notifications/channels/ch-1/test');
      expect(req.request.method).toBe('POST');
      req.flush({ delivered: true });
      expect(toastMock.success).toHaveBeenCalled();
    });

    it('should show warning when not delivered', () => {
      component.sendTest('SLACK');
      httpCtrl.expectOne('/api/v1/notifications/channels/ch-1/test').flush({ delivered: false });
      expect(toastMock.warning).toHaveBeenCalled();
    });

    it('should show error on failure', () => {
      component.sendTest('SLACK');
      httpCtrl.expectOne('/api/v1/notifications/channels/ch-1/test').flush(
        { detail: 'Test failed' },
        { status: 500, statusText: 'Error' }
      );
      expect(toastMock.error).toHaveBeenCalledWith('Test failed');
    });

    it('should not send if channel has no id', () => {
      component.channels.set([]);
      component.sendTest('GENERIC');
      httpCtrl.expectNone('/api/v1/notifications/channels/null/test');
      expect(component.testing()).toBeNull();
    });
  });

  describe('disable', () => {
    beforeEach(() => {
      component.ngOnInit();
      loadAllRequests(httpCtrl);
    });

    it('should DELETE channel', () => {
      component.disable('SLACK');
      const req = httpCtrl.expectOne('/api/v1/notifications/channels/ch-1');
      expect(req.request.method).toBe('DELETE');
      req.flush({});
      loadAllRequests(httpCtrl);
    });

    it('should show error on delete failure and reload', () => {
      component.disable('SLACK');
      httpCtrl.expectOne('/api/v1/notifications/channels/ch-1').flush('', { status: 500, statusText: 'Error' });
      expect(toastMock.error).toHaveBeenCalled();
      loadAllRequests(httpCtrl);
    });

    it('should not delete if channel has no id', () => {
      component.channels.set([]);
      component.disable('SLACK');
      httpCtrl.expectNone('/api/v1/notifications/channels/null');
      expect(component.deleting()).toBeNull();
    });
  });

  describe('template rendering', () => {
    it('should render loading skeleton', () => {
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector('.skeleton-list')).toBeTruthy();
      loadAllRequests(httpCtrl);
    });

    it('should render error state', () => {
      fixture.detectChanges();
      httpCtrl.expectOne('/api/v1/notifications/channel-types').flush('', { status: 500, statusText: 'Error' });
      fixture.detectChanges();
      const banner = fixture.nativeElement.querySelector('.error-banner');
      expect(banner).toBeTruthy();
      expect(banner.textContent).toContain('notification_channels.loading_error');
    });

    it('should render channel cards', () => {
      fixture.detectChanges();
      loadAllRequests(httpCtrl);
      fixture.detectChanges();
      const cards = fixture.nativeElement.querySelectorAll('.channel-card');
      expect(cards.length).toBeGreaterThanOrEqual(1);
    });

    it('should render configured status badge', () => {
      fixture.detectChanges();
      loadAllRequests(httpCtrl);
      fixture.detectChanges();
      const badge = fixture.nativeElement.querySelector('.status-configured');
      expect(badge).toBeTruthy();
      expect(badge.textContent).toContain('notification_channels.configured');
    });
  });
});
