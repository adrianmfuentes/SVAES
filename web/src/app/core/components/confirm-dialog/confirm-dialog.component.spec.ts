import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ConfirmDialogComponent } from './confirm-dialog.component';
import { TranslationService } from '../../i18n/translation.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
  currentLang: 'es',
  lang$: of('es'),
};

describe('ConfirmDialogComponent', () => {
  let component: ConfirmDialogComponent;

  let fixture: ReturnType<typeof TestBed.createComponent<ConfirmDialogComponent>>;

  beforeEach(() => {
    vi.clearAllMocks();
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        { provide: TranslationService, useValue: tsMock },
      ],
    });

    fixture = TestBed.createComponent(ConfirmDialogComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('title', 'Test Title');
    fixture.componentRef.setInput('message', 'Test Message');
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have default confirmText and cancelText', () => {
    expect(component.confirmText()).toBe('common.confirm');
    expect(component.cancelText()).toBe('common.cancel');
  });

  it('should increment dialogId across instances', () => {
    const fixture2 = TestBed.createComponent(ConfirmDialogComponent);
    const component2 = fixture2.componentInstance;
    fixture2.componentRef.setInput('title', 'Title 2');
    fixture2.componentRef.setInput('message', 'Msg 2');
    fixture2.detectChanges();
    expect(component2.dialogId).toBeGreaterThan(component.dialogId);
  });

  it('should set custom confirmText and cancelText via input', () => {
    fixture.componentRef.setInput('confirmText', 'custom.confirm');
    fixture.componentRef.setInput('cancelText', 'custom.cancel');
    expect(component.confirmText()).toBe('custom.confirm');
    expect(component.cancelText()).toBe('custom.cancel');
  });

  describe('cancelLabel', () => {
    it('should return translated a11y cancel label', () => {
      tsMock.translateInstant.mockReturnValue('Cancelar y cerrar');
      expect(component.cancelLabel).toBe('Cancelar y cerrar');
      expect(tsMock.translateInstant).toHaveBeenCalledWith('a11y.cancel_and_close');
    });
  });

  describe('confirmLabel', () => {
    it('should return translated a11y confirm label', () => {
      tsMock.translateInstant.mockReturnValue('Confirmar accion');
      expect(component.confirmLabel).toBe('Confirmar accion');
      expect(tsMock.translateInstant).toHaveBeenCalledWith('a11y.confirm_action');
    });
  });

  describe('onOverlayClick', () => {
    it('should call onCancel when target has dialog-overlay class', () => {
      const cancelledSpy = vi.fn();
      component.cancelled.subscribe(cancelledSpy);

      const target = { classList: { contains: vi.fn().mockReturnValue(true) } } as unknown as HTMLElement;
      component.onOverlayClick({ target } as unknown as MouseEvent);

      expect(cancelledSpy).toHaveBeenCalled();
    });

    it('should not call onCancel when target does not have dialog-overlay class', () => {
      const cancelledSpy = vi.fn();
      component.cancelled.subscribe(cancelledSpy);

      const target = { classList: { contains: vi.fn().mockReturnValue(false) } } as unknown as HTMLElement;
      component.onOverlayClick({ target } as unknown as MouseEvent);

      expect(cancelledSpy).not.toHaveBeenCalled();
    });
  });

  describe('onCancel', () => {
    it('should emit cancelled', () => {
      const spy = vi.fn();
      component.cancelled.subscribe(spy);
      component.onCancel();
      expect(spy).toHaveBeenCalled();
    });
  });

  describe('onConfirm', () => {
    it('should emit confirmed', () => {
      const spy = vi.fn();
      component.confirmed.subscribe(spy);
      component.onConfirm();
      expect(spy).toHaveBeenCalled();
    });
  });
});
