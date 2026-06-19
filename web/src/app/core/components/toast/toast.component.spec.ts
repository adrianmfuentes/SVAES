import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ToastComponent } from './toast.component';
import { ToastService, Toast } from '../../services/toast.service';
import { TranslationService } from '../../i18n/translation.service';

const tsMock = {
  translateInstant: vi.fn((key: string) => key),
};

describe('ToastComponent', () => {
  let component: ToastComponent;
  let fixture: ComponentFixture<ToastComponent>;
  let toastService: ToastService;

  const mockToasts: Toast[] = [
    { id: 1, message: 'Success message', type: 'success', duration: 4000 },
    { id: 2, message: 'Error message', type: 'error', duration: 5000 },
    { id: 3, message: 'Warning message', type: 'warning', duration: 4500 },
    { id: 4, message: 'Info message', type: 'info', duration: 4000 },
  ];

  beforeEach(() => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TranslationService, useValue: tsMock },
      ],
    });

    toastService = TestBed.inject(ToastService);
    fixture = TestBed.createComponent(ToastComponent);
    component = fixture.componentInstance;
  });

  afterEach(() => {
    TestBed.resetTestingModule();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have dismissLabel from translation service', () => {
    expect(component.dismissLabel).toBe('a11y.dismiss_notification');
    expect(tsMock.translateInstant).toHaveBeenCalledWith('a11y.dismiss_notification');
  });

  it('should render toasts from toastService', () => {
    toastService.show('Test success', 'success');
    toastService.show('Test error', 'error');
    fixture.detectChanges();

    const toastElements = fixture.nativeElement.querySelectorAll('.toast');
    expect(toastElements.length).toBe(2);
  });

  it('should apply correct class for success toast', () => {
    toastService.show('Success', 'success');
    fixture.detectChanges();

    const toastEl = fixture.nativeElement.querySelector('.toast-success');
    expect(toastEl).toBeTruthy();
    expect(toastEl.textContent).toContain('Success');
  });

  it('should apply correct class for error toast', () => {
    toastService.show('Error', 'error');
    fixture.detectChanges();

    const toastEl = fixture.nativeElement.querySelector('.toast-error');
    expect(toastEl).toBeTruthy();
    expect(toastEl.textContent).toContain('Error');
  });

  it('should apply correct class for warning toast', () => {
    toastService.show('Warning', 'warning');
    fixture.detectChanges();

    const toastEl = fixture.nativeElement.querySelector('.toast-warning');
    expect(toastEl).toBeTruthy();
    expect(toastEl.textContent).toContain('Warning');
  });

  it('should apply correct class for info toast', () => {
    toastService.show('Info', 'info');
    fixture.detectChanges();

    const toastEl = fixture.nativeElement.querySelector('.toast-info');
    expect(toastEl).toBeTruthy();
    expect(toastEl.textContent).toContain('Info');
  });

  it('should call dismiss when toast is clicked', () => {
    toastService.show('Click me', 'info');
    fixture.detectChanges();

    const toastEl = fixture.nativeElement.querySelector('.toast');
    toastEl.click();
    fixture.detectChanges();

    expect(toastService.toasts().length).toBe(0);
  });

  it('should call dismiss with correct id', () => {
    toastService.show('First', 'success');
    toastService.show('Second', 'error');
    fixture.detectChanges();

    const firstToast = fixture.nativeElement.querySelector('.toast');
    firstToast.click();
    fixture.detectChanges();

    expect(toastService.toasts().length).toBe(1);
    expect(toastService.toasts()[0].message).toBe('Second');
  });

  it('should stop propagation when close button is clicked', () => {
    toastService.show('Test', 'info');
    fixture.detectChanges();

    const closeBtn = fixture.nativeElement.querySelector('.toast-close');
    const stopPropagationSpy = vi.fn();
    closeBtn.addEventListener('click', stopPropagationSpy);

    closeBtn.click();
    fixture.detectChanges();

    expect(stopPropagationSpy).not.toHaveBeenCalled();
  });

  it('should render aria-label on close button', () => {
    toastService.show('Test', 'info');
    fixture.detectChanges();

    const closeBtn = fixture.nativeElement.querySelector('.toast-close');
    expect(closeBtn.getAttribute('aria-label')).toBe('a11y.dismiss_notification');
  });

  it('should have role alert for error toast', () => {
    toastService.show('Error toast', 'error');
    fixture.detectChanges();

    const toastEl = fixture.nativeElement.querySelector('.toast');
    expect(toastEl.getAttribute('role')).toBe('alert');
  });

  it('should have role status for non-error toasts', () => {
    toastService.show('Info toast', 'info');
    fixture.detectChanges();

    const toastEl = fixture.nativeElement.querySelector('.toast');
    expect(toastEl.getAttribute('role')).toBe('status');
  });

  it('should render all four toast types correctly', () => {
    mockToasts.forEach(toast => toastService.show(toast.message, toast.type));
    fixture.detectChanges();

    const toastElements = fixture.nativeElement.querySelectorAll('.toast');
    expect(toastElements.length).toBe(4);

    expect(fixture.nativeElement.querySelector('.toast-success')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('.toast-error')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('.toast-warning')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('.toast-info')).toBeTruthy();
  });
});
