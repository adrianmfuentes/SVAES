import { TestBed, ComponentFixture } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { LandingComponent } from './landing.component';

describe('LandingComponent', () => {
  let fixture: ComponentFixture<LandingComponent>;
  let component: LandingComponent;
  let host: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LandingComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(LandingComponent);
    component = fixture.componentInstance;
    host = fixture.nativeElement as HTMLElement;
    fixture.detectChanges();
  });

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  it('renders one h1 and a heading for every section target', () => {
    expect(host.querySelectorAll('h1')).toHaveLength(1);
    for (const section of component.sections) {
      expect(host.querySelector(`#${section.id}`)).not.toBeNull();
    }
  });

  it('lists five sample rules in the record', () => {
    expect(host.querySelectorAll('.acta tbody tr')).toHaveLength(5);
  });

  it('toggles the mobile menu and exposes its state', () => {
    const toggle = host.querySelector<HTMLButtonElement>('.menu-toggle')!;
    expect(toggle.getAttribute('aria-expanded')).toBe('false');

    toggle.click();
    fixture.detectChanges();
    expect(toggle.getAttribute('aria-expanded')).toBe('true');

    component.closeMenu();
    fixture.detectChanges();
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
  });

  it('moves focus to the target heading when navigating to a section', () => {
    const scrollSpy = vi.fn();
    const target = host.querySelector<HTMLElement>('#reglas')!;
    target.scrollIntoView = scrollSpy;
    const event = new Event('click', { cancelable: true });

    component.goTo('reglas', event);

    expect(event.defaultPrevented).toBe(true);
    expect(scrollSpy).toHaveBeenCalled();
    expect(document.activeElement).toBe(target);
  });

});
