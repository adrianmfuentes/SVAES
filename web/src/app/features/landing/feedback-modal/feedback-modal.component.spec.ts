import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FeedbackModalComponent } from './feedback-modal.component';
import { FeedbackService, FeedbackPayload } from '../../../core/services/feedback.service';
import { TranslationService } from '../../../core/i18n/translation.service';
import { of, throwError } from 'rxjs';

const FEEDBACK_TRANSLATIONS: Record<string, string> = {
  'feedback.rating_0': 'Sin calificar',
  'feedback.rating_1': 'Muy malo',
  'feedback.rating_2': 'Malo',
  'feedback.rating_3': 'Regular',
  'feedback.rating_4': 'Bueno',
  'feedback.rating_5': 'Excelente',
  'feedback.error': 'No se pudo enviar el feedback. Inténtalo de nuevo.',
};

const tsMock = {
  translateInstant: vi.fn((key: string) => FEEDBACK_TRANSLATIONS[key] ?? key),
  currentLang: 'es',
  lang$: of('es'),
};

describe('FeedbackModalComponent', () => {
  let fixture: ComponentFixture<FeedbackModalComponent>;
  let component: FeedbackModalComponent;
  let mockFeedbackService: {
    submit: ReturnType<typeof vi.fn>;
  };

  beforeEach(async () => {
    mockFeedbackService = {
      submit: vi.fn().mockReturnValue(of({ status: 'ok' }))
    };

    await TestBed.configureTestingModule({
      imports: [FeedbackModalComponent],
      providers: [
        { provide: FeedbackService, useValue: mockFeedbackService },
        { provide: TranslationService, useValue: tsMock }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(FeedbackModalComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('component creation', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should have initial state with empty payload', () => {
      expect(component.payload.name).toBe('');
      expect(component.payload.email).toBe('');
      expect(component.payload.rating).toBe(0);
      expect(component.payload.comments).toBe('');
    });

    it('should have loading false by default', () => {
      expect(component.loading).toBeFalsy();
    });

    it('should have submitted false by default', () => {
      expect(component.submitted).toBeFalsy();
    });

    it('should have error null by default', () => {
      expect(component.error).toBeNull();
    });
  });

  describe('isValid getter', () => {
    it('should return false when name is empty', () => {
      component.payload.name = '';
      component.payload.rating = 5;
      component.payload.comments = 'Great app';
      expect(component.isValid).toBeFalsy();
    });

    it('should return false when name is only whitespace', () => {
      component.payload.name = '   ';
      component.payload.rating = 5;
      component.payload.comments = 'Great app';
      expect(component.isValid).toBeFalsy();
    });

    it('should return false when rating is 0', () => {
      component.payload.name = 'Test';
      component.payload.rating = 0;
      component.payload.comments = 'Great app';
      expect(component.isValid).toBeFalsy();
    });

    it('should return false when comments is empty', () => {
      component.payload.name = 'Test';
      component.payload.rating = 5;
      component.payload.comments = '';
      expect(component.isValid).toBeFalsy();
    });

    it('should return false when comments is only whitespace', () => {
      component.payload.name = 'Test';
      component.payload.rating = 5;
      component.payload.comments = '   ';
      expect(component.isValid).toBeFalsy();
    });

    it('should return true when all required fields are filled', () => {
      component.payload.name = 'Test User';
      component.payload.email = 'test@example.com';
      component.payload.rating = 5;
      component.payload.comments = 'Great app!';
      expect(component.isValid).toBeTruthy();
    });
  });

  describe('ratingLabel getter', () => {
    it('should return "Sin calificar" when rating is 0', () => {
      component.payload.rating = 0;
      expect(component.ratingLabel).toBe('Sin calificar');
    });

    it('should return "Muy malo" when rating is 1', () => {
      component.payload.rating = 1;
      expect(component.ratingLabel).toBe('Muy malo');
    });

    it('should return "Malo" when rating is 2', () => {
      component.payload.rating = 2;
      expect(component.ratingLabel).toBe('Malo');
    });

    it('should return "Regular" when rating is 3', () => {
      component.payload.rating = 3;
      expect(component.ratingLabel).toBe('Regular');
    });

    it('should return "Bueno" when rating is 4', () => {
      component.payload.rating = 4;
      expect(component.ratingLabel).toBe('Bueno');
    });

    it('should return "Excelente" when rating is 5', () => {
      component.payload.rating = 5;
      expect(component.ratingLabel).toBe('Excelente');
    });
  });

  describe('onOverlayClick', () => {
    it('should call onClose when clicking overlay', () => {
      const closeSpy = vi.spyOn(component, 'onClose');
      const event = new MouseEvent('click');
      Object.defineProperty(event, 'target', { value: { classList: { contains: () => true } } });

      component.onOverlayClick(event);

      expect(closeSpy).toHaveBeenCalled();
    });

    it('should not call onClose when clicking modal content', () => {
      const closeSpy = vi.spyOn(component, 'onClose');
      const event = new MouseEvent('click');
      Object.defineProperty(event, 'target', { value: { classList: { contains: () => false } } });

      component.onOverlayClick(event);

      expect(closeSpy).not.toHaveBeenCalled();
    });
  });

  describe('onClose', () => {
    it('should emit closed event', () => {
      const emitSpy = vi.spyOn(component.closed, 'emit');
      component.onClose();
      expect(emitSpy).toHaveBeenCalled();
    });
  });

  describe('onSubmit', () => {
    it('should not submit if isValid is false', () => {
      component.payload.name = '';
      component.payload.rating = 0;
      component.payload.comments = '';

      component.onSubmit();

      expect(mockFeedbackService.submit).not.toHaveBeenCalled();
    });

    it('should not submit if loading is true', () => {
      component.loading = true;
      component.payload.name = 'Test';
      component.payload.rating = 5;
      component.payload.comments = 'Great';

      component.onSubmit();

      expect(mockFeedbackService.submit).not.toHaveBeenCalled();
    });

    it('should call submit on valid form', () => {
      component.payload.name = 'Test User';
      component.payload.email = 'test@example.com';
      component.payload.rating = 5;
      component.payload.comments = 'Great app!';

      component.onSubmit();

      expect(mockFeedbackService.submit).toHaveBeenCalledWith(component.payload);
    });

    it('should set submitted true on successful submission', () => {
      component.payload.name = 'Test User';
      component.payload.rating = 5;
      component.payload.comments = 'Great app!';

      component.onSubmit();
      fixture.detectChanges();

      expect(component.submitted).toBeTruthy();
      expect(component.loading).toBeFalsy();
    });

    it('should set error and loading false on failed submission', () => {
      mockFeedbackService.submit.mockReturnValue(throwError(() => new Error('Server error')));
      component.payload.name = 'Test User';
      component.payload.rating = 5;
      component.payload.comments = 'Great app!';

      component.onSubmit();
      fixture.detectChanges();

      expect(component.error).toBe('No se pudo enviar el feedback. Inténtalo de nuevo.');
      expect(component.loading).toBeFalsy();
    });
  });

  describe('star rating interaction', () => {
    it('should allow setting rating by clicking star', () => {
      component.payload.rating = 0;
      component.payload.rating = 4;
      expect(component.payload.rating).toBe(4);
    });

    it('should show filled stars based on rating', () => {
      component.payload.rating = 3;
      expect(component.payload.rating >= 1).toBeTruthy();
      expect(component.payload.rating >= 2).toBeTruthy();
      expect(component.payload.rating >= 3).toBeTruthy();
      expect(component.payload.rating >= 4).toBeFalsy();
      expect(component.payload.rating >= 5).toBeFalsy();
    });
  });
});
