# Design

## Register

product

## Color Strategy

Restrained. Tinted neutrals carry the interface; primary (deep harbor blue) is used sparingly for the one action that matters per screen (confirm, submit); accent (warm copper) marks secondary emphasis (totals, links). State communication (para enviar / sin email / filtrado, luego no contestado / contestado / pago / rebotado) uses a dedicated semantic layer (success / warning / danger / neutral) — this is functional signaling, not decoration, and is core to the product's design principle "estado antes que estética."

## Palette (OKLCH)

Seed: `oklch(0.450 0.074 200.0)` — hue 200 (harbor blue / teal). Seed chroma < 0.10, so a whisper-tinted background is used (per the low-chroma-seed exception) rather than pure white — the tint keeps the brand hue present even where color is used sparingly.

```css
:root {
  --bg: 0.99 0.004 200;
  --surface: 0.97 0.006 200;
  --ink: 0.22 0.02 200;
  --muted-ink: 0.48 0.014 200;
  --border: 0.90 0.008 200;

  --primary: 0.40 0.085 200;         /* harbor blue — primary actions */
  --primary-foreground: 0.995 0 0;

  --accent: 0.60 0.13 55;            /* warm copper — secondary emphasis, totals, links */
  --accent-foreground: 0.995 0 0;

  --success: 0.58 0.15 148;          /* pago / para-enviar listo */
  --success-foreground: 0.995 0 0;
  --warning: 0.68 0.15 75;           /* sin email / no contestado */
  --warning-foreground: 0.22 0.03 75;
  --danger: 0.56 0.20 25;            /* rebotado / dado de baja */
  --danger-foreground: 0.995 0 0;
  --neutral: 0.55 0.01 200;          /* filtrado / monto mínimo */
  --neutral-foreground: 0.995 0 0;

  --radius: 0.5rem;
}
```

Consumed via `oklch(var(--token))` in Tailwind (`tailwind.config.js`), replacing the stock shadcn `hsl(var(--token))` wiring.

Rules honored: ink-vs-bg contrast > 7:1, primary chroma 0.085 (well under the 0.23 ceiling), primary/accent hue distance 145° (clearly distinct), all saturated fills (primary/accent/success/danger) get white text; warning (light, high-chroma) gets dark text per the pale-fill exception.

## Typography

- Existing stack (no custom fonts installed) — system UI stack via Tailwind's default `font-sans`. Not revisited in this pass; a type pairing can be layered on later without touching structure.
- Numeric data (montos, conteos) uses `tabular-nums` so columns of numbers align.
- Scale: page title `text-2xl font-semibold`, section/table headers `text-sm font-medium text-muted-ink`, body `text-sm`, counts/badges `text-xs font-medium`.

## Layout & Components

- **No card-wrapping of tables.** Tables sit directly on `bg`, separated by `surface`-colored row dividers — cards were the stock pattern (`rounded border p-4 bg-gray-50`) and read as generic SaaS scaffolding per the anti-reference.
- **Status is a colored dot + label, never color alone** (colorblind-safe, WCAG-friendly): `● Monto mínimo` in `danger`/`warning`/`neutral` tokens rather than a bare colored badge.
- **Empty states are instructive, not blank.** "Sin email" and "Filtrados" tabs, when empty, say what that means and what to do next — not just a gray sentence.
- **Progress bar** uses `primary`, motion via `transition-[width] duration-300 ease-out-expo`-equivalent (Tailwind default `ease-out` is close enough; no bounce).
- shadcn primitives already in the repo (`Tabs`, `Badge`, `Dialog`, `Button`, `Skeleton`) are reused, not replaced.

## Motion

- Reduced motion respected via Tailwind's `motion-reduce:` variants on the one non-trivial transition (progress bar width, tab content fade).
- No entrance animations on data tables — the operator opens this screen to read numbers immediately, not to watch them arrive.
