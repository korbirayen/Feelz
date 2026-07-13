# Screenshots

Placeholder folder - the main README references `text-dark.png` here (see
the commented-out `<!-- TODO -->` block near the top of README.md).

Verified live while building this feature set (via computer-use against the
running desktop app) that the UI renders correctly for:

- Text > Polarity, dark theme - a positive result ("Had an amazing day
  today, I feel grateful and full of energy!" -> 53% positive / 46% neutral).
- Text > Language Patterns - the crisis-resource panel triggering correctly
  at high confidence (98%) with the red accent bar and resource list.
- The nav rail's inactive-item contrast fix (was ~1.3:1, unreadable in light
  theme; fixed to ~5-8:1 - see `muted_nav_fg()` in Sentiment247.py).

Those screenshots couldn't be saved directly into this repo - the
computer-use tool that drove the verification controls an isolated VM
desktop, not this sandbox's filesystem. Recapture and drop them in here
(`text-dark.png` at minimum) whenever convenient, then uncomment the
reference in README.md.
