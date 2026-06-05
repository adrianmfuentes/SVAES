import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of } from 'rxjs';
import { ConnectorsComponent } from './connectors.component';
import { AuthService } from '../../core/services/auth.service';
import { TranslationService } from '../../core/i18n/translation.service';
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

const apiConnector = {
  id: 'conn-1',
  name: 'My GitLab',
  connector_type: 'REPO_CODIGO',
  status: 'ACTIVO',
};

describe('ConnectorsComponent', () => {
  let component: ConnectorsComponent;
  let httpCtrl: HttpTestingController;

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: authMock },
        { provide: TranslationService, useValue: tsMock },
      ],
    });

    const fixture = TestBed.createComponent(ConnectorsComponent);
    component = fixture.componentInstance;
    httpCtrl = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpCtrl.verify());

  describe('ngOnInit', () => {
    it('should load connectors for the user org', () => {
      component.ngOnInit();
      const req = httpCtrl.expectOne('/api/v1/organizations/org-abc/connectors');
      req.flush([apiConnector]);
      expect(component.connectors()).toHaveLength(1);
      expect(component.connectors()[0].status).toBe('active');
      expect(component.loading()).toBe(false);
    });

    it('should set error when no orgId', () => {
      authMock.getUser.mockReturnValue(null);
      component.ngOnInit();
      httpCtrl.expectNone('/api/v1/organizations/org-abc/connectors');
      expect(component.error()).toBe('connectors.loading_error');
      expect(component.loading()).toBe(false);
      authMock.getUser.mockReturnValue({ id: 'u1', organization_id: 'org-abc' });
    });

    it('should set error on HTTP failure', () => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-abc/connectors').flush('', { status: 500, statusText: 'Error' });
      expect(component.error()).toBe('connectors.loading_error');
    });
  });

  describe('statusLabel', () => {
    it('should call translateInstant for known statuses', () => {
      component.statusLabel('active');
      expect(tsMock.translateInstant).toHaveBeenCalledWith('connectors.status_active');
      component.statusLabel('inactive');
      expect(tsMock.translateInstant).toHaveBeenCalledWith('connectors.status_inactive');
      component.statusLabel('error');
      expect(tsMock.translateInstant).toHaveBeenCalledWith('connectors.status_error');
    });

    it('should return status as-is for unknown values', () => {
      expect(component.statusLabel('unknown')).toBe('unknown');
    });
  });

  describe('openCreate / openEdit', () => {
    it('openCreate should reset form and show modal', () => {
      component.openCreate();
      expect(component.showModal()).toBe(true);
      expect(component.editingConnector()).toBeNull();
      expect(component.modalError()).toBeNull();
    });

    it('openEdit should populate form and show modal', () => {
      const conn = { id: 'c1', name: 'Test', type: 'gitlab', status: 'active' as const, global: false };
      component.openEdit(conn);
      expect(component.showModal()).toBe(true);
      expect(component.editingConnector()).toEqual(conn);
      expect(component.connectorForm.value.name).toBe('Test');
    });
  });

  describe('submitConnector', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-abc/connectors').flush([]);
    });

    it('should POST new connector', () => {
      component.openCreate();
      component.connectorForm.setValue({ name: 'New Conn', type: 'gitlab', base_url: 'https://gl.com', token: 'tok' });
      component.submitConnector();
      const req = httpCtrl.expectOne('/api/v1/organizations/org-abc/connectors');
      expect(req.request.method).toBe('POST');
      req.flush({ ...apiConnector, id: 'new-conn' });
      expect(component.showModal()).toBe(false);
      expect(component.globalConnectors()).toHaveLength(1);
    });

    it('should PATCH existing connector', () => {
      const existing = { id: 'conn-1', name: 'Old', type: 'gitlab', status: 'active' as const, global: false };
      component.globalConnectors.set([existing]);
      component.openEdit(existing);
      component.connectorForm.patchValue({ name: 'Updated', base_url: 'https://x.com', token: '' });
      component.submitConnector();
      const req = httpCtrl.expectOne('/api/v1/organizations/org-abc/connectors/conn-1');
      expect(req.request.method).toBe('PATCH');
      req.flush({ ...apiConnector, id: 'conn-1', name: 'Updated' });
      expect(component.showModal()).toBe(false);
    });

    it('should set modalError on failure', () => {
      component.openCreate();
      component.connectorForm.setValue({ name: 'X', type: 'gitlab', base_url: 'https://x.com', token: '' });
      component.submitConnector();
      httpCtrl.expectOne('/api/v1/organizations/org-abc/connectors').flush(
        { detail: 'Token invalid' },
        { status: 422, statusText: 'Unprocessable' }
      );
      expect(component.modalError()).toBe('Token invalid');
    });
  });

  describe('testConnector', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-abc/connectors').flush([]);
    });

    it('should set and clear testingId', () => {
      const conn = { id: 'conn-1', name: 'X', type: 'gitlab', status: 'active' as const, global: false };
      component.testConnector(conn);
      expect(component.testingId()).toBe('conn-1');
      httpCtrl.expectOne('/api/v1/organizations/org-abc/connectors/conn-1/test').flush({});
      expect(component.testingId()).toBeNull();
    });
  });

  describe('toggleConnector', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-abc/connectors').flush([]);
    });

    it('should PATCH with INACTIVO when connector is active', () => {
      const conn = { id: 'conn-1', name: 'X', type: 'gitlab', status: 'active' as const, global: false };
      component.globalConnectors.set([conn]);
      component.toggleConnector(conn);
      const req = httpCtrl.expectOne('/api/v1/organizations/org-abc/connectors/conn-1');
      expect(req.request.method).toBe('PATCH');
      expect(req.request.body.status).toBe('INACTIVO');
      req.flush({ id: 'conn-1', name: 'X', connector_type: 'REPO_CODIGO', status: 'INACTIVO', created_at: '2025-01-01T00:00:00Z' });
      expect(component.globalConnectors()[0].status).toBe('inactive');
    });

    it('should PATCH with ACTIVO when connector is inactive', () => {
      const conn = { id: 'conn-2', name: 'Y', type: 'jira', status: 'inactive' as const, global: false };
      component.globalConnectors.set([conn]);
      component.toggleConnector(conn);
      const req = httpCtrl.expectOne('/api/v1/organizations/org-abc/connectors/conn-2');
      expect(req.request.body.status).toBe('ACTIVO');
      req.flush({ id: 'conn-2', name: 'Y', connector_type: 'GESTOR_TAREAS', status: 'ACTIVO', created_at: '2025-01-01T00:00:00Z' });
      expect(component.globalConnectors()[0].status).toBe('active');
    });

    it('should handle toggle error gracefully', () => {
      const conn = { id: 'conn-1', name: 'X', type: 'gitlab', status: 'active' as const, global: false };
      component.globalConnectors.set([conn]);
      component.toggleConnector(conn);
      httpCtrl.expectOne('/api/v1/organizations/org-abc/connectors/conn-1').flush(
        {}, { status: 503, statusText: 'Error' }
      );
      expect(component.globalConnectors()[0].status).toBe('active');
    });
  });

  describe('submitConnector with different types', () => {
    beforeEach(() => {
      component.ngOnInit();
      httpCtrl.expectOne('/api/v1/organizations/org-abc/connectors').flush([]);
    });

    it('should map jira type to GESTOR_TAREAS', () => {
      component.openCreate();
      component.connectorForm.setValue({ name: 'Jira Conn', type: 'jira', base_url: 'https://jira.io', token: 'tok' });
      component.submitConnector();
      const req = httpCtrl.expectOne('/api/v1/organizations/org-abc/connectors');
      expect(req.request.body.connector_type).toBe('GESTOR_TAREAS');
      req.flush({ id: 'j1', name: 'Jira Conn', connector_type: 'GESTOR_TAREAS', status: 'ACTIVO', created_at: '2025-01-01T00:00:00Z' });
    });

    it('should map unknown type to REPO_CODIGO', () => {
      component.openCreate();
      component.connectorForm.setValue({ name: 'Unknown', type: 'unknown_tool', base_url: 'https://x.com', token: '' });
      component.submitConnector();
      const req = httpCtrl.expectOne('/api/v1/organizations/org-abc/connectors');
      expect(req.request.body.connector_type).toBe('REPO_CODIGO');
      req.flush({ id: 'u1', name: 'Unknown', connector_type: 'REPO_CODIGO', status: 'ACTIVO', created_at: '2025-01-01T00:00:00Z' });
    });

    it('should not submit if form is invalid', () => {
      component.openCreate();
      component.connectorForm.setValue({ name: '', type: 'gitlab', base_url: '', token: '' });
      component.submitConnector();
      httpCtrl.expectNone('/api/v1/organizations/org-abc/connectors');
    });
  });
});
