import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { FeedbackService, FeedbackPayload } from './feedback.service';

describe('FeedbackService', () => {
  let service: FeedbackService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [FeedbackService]
    });

    service = TestBed.inject(FeedbackService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  describe('submit', () => {
    it('should POST feedback to /api/v1/feedback', () => {
      const payload: FeedbackPayload = {
        name: 'Test User',
        email: 'test@example.com',
        rating: 5,
        comments: 'Great app!'
      };

      service.submit(payload).subscribe(response => {
        expect(response.status).toBe('ok');
      });

      const req = httpMock.expectOne('/api/v1/feedback');
      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(payload);
      req.flush({ status: 'ok' });
    });

    it('should send feedback with rating 1', () => {
      const payload: FeedbackPayload = {
        name: 'User',
        email: '',
        rating: 1,
        comments: 'Needs improvement'
      };

      service.submit(payload).subscribe();

      const req = httpMock.expectOne('/api/v1/feedback');
      expect(req.request.body.rating).toBe(1);
      req.flush({ status: 'ok' });
    });

    it('should handle various ratings', () => {
      const ratings = [1, 2, 3, 4, 5];

      ratings.forEach(rating => {
        const payload: FeedbackPayload = {
          name: 'Tester',
          email: 'test@test.com',
          rating,
          comments: 'Testing'
        };

        service.submit(payload).subscribe();
        const req = httpMock.expectOne('/api/v1/feedback');
        expect(req.request.body.rating).toBe(rating);
        req.flush({ status: 'ok' });
      });
    });
  });
});
