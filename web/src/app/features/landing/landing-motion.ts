/**
 * Landing motion (GSAP + Lenis), loaded lazily in the browser only.
 *
 * Restrained on purpose: the headline resolves word by word out of a soft
 * blur, the verification record fills in row by row as it scrolls into view,
 * and the rest of the page rises in once. Content is visible by default, so
 * nothing here is needed to read the page, and none of it runs under
 * prefers-reduced-motion.
 */
import type Lenis from 'lenis';

export interface LandingMotion {
  scrollTo(target: HTMLElement): void;
  scrollTop(): void;
  destroy(): void;
}

export async function initLandingMotion(host: HTMLElement): Promise<LandingMotion> {
  // Smooth scrolling only for mouse and trackpad: touch devices keep their native, cheaper scroll
  // (and never download the Lenis chunk).
  const fine = window.matchMedia('(pointer: fine)').matches;
  const [{ gsap }, { ScrollTrigger }, lenisModule] = await Promise.all([
    import('gsap'),
    import('gsap/ScrollTrigger'),
    fine ? import('lenis') : Promise.resolve(null),
  ]);
  gsap.registerPlugin(ScrollTrigger);

  const q = <T extends Element>(sel: string): T[] => Array.from(host.querySelectorAll<T>(sel));

  const lenis: Lenis | null = lenisModule
    ? new lenisModule.default({ lerp: 0.09, wheelMultiplier: 0.85 })
    : null;
  const tick = (time: number): void => lenis?.raf(time * 1000);
  if (lenis) {
    lenis.on('scroll', ScrollTrigger.update);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);
  }

  const ctx = gsap.context(() => {
    const ease = 'expo.out';

    // The hero entrance is plain CSS (see landing.component.scss) so it never waits for this module.

    // Record: the panel and its rows appear once it is on screen.
    const acta = q('.acta')[0];
    if (acta) {
      gsap.fromTo(
        acta,
        { opacity: 0, y: 48 },
        {
          opacity: 1,
          y: 0,
          duration: 1.2,
          ease,
          scrollTrigger: { trigger: acta, start: 'top 88%', once: true },
        },
      );
      gsap.fromTo(
        q('.acta tbody tr'),
        { opacity: 0, y: 10 },
        {
          opacity: 1,
          y: 0,
          duration: 0.6,
          stagger: 0.09,
          ease,
          delay: 0.35,
          scrollTrigger: { trigger: acta, start: 'top 80%', once: true },
        },
      );
    }

    // Everything else rises in once, quietly.
    q('.proc__head, .proc__row, .rules__head, .verdicts__item, .conn__head, .connectors__row, .research__head, .research__text, .research__visual').forEach(
      (el) => {
        gsap.from(el, {
          opacity: 0,
          y: 32,
          duration: 1,
          ease,
          scrollTrigger: { trigger: el, start: 'top 90%', once: true },
        });
      },
    );
    // From here GSAP owns the initial states; the CSS hold is no longer needed.
    document.documentElement.classList.add('motion-done');
  }, host);

  return {
    scrollTop: () => {
      if (lenis) lenis.scrollTo(0, { duration: 1.3 });
      else window.scrollTo({ top: 0, behavior: 'smooth' });
    },
    scrollTo: (target) => {
      if (lenis) lenis.scrollTo(target, { offset: -68, duration: 1.3 });
      else target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    },
    destroy: () => {
      ctx.revert();
      document.documentElement.classList.remove('motion-done');
      gsap.ticker.remove(tick);
      lenis?.destroy();
    },
  };
}
