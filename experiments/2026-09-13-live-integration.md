# Live application integration, September 13, 2026

## What the supplied design describes

The proposed flow is settings -> privileged injector -> code executing inside
the game -> state updates -> overlay. An actual implementation needs compatible
native code, concrete game symbols or method mappings, an IPC protocol, and a
working authentication backend. The supplied text describes these components
but provides none of those integration contracts or source implementations.
An ADB process check cannot substitute for a game hook or a catch counter.

Shungo's [installation guide](https://docs.shungo.app/info/installation-guide)
documents installation, Magisk permission, account/subscription login, and
overlay counters as operational indicators. It does not establish the supplied
document's particular ptrace, ART replacement, Binder, or hook implementation
claims. Those remain unverified internals.

## Fresh observations

- Device: existing `poke_api36_test`, `emulator-5556`, clean API 36.
- Game: installed `com.nianticlabs.pokemongo`, version 0.427.0.
- Pre-launch diagnostics completed successfully.
- One launch completed with the game's activity resumed. Screenshots progressed
  from the Android app splash to the Pokemon GO publisher splash and then the
  Google account chooser. The crash buffer was empty at post-launch capture.
- Account selection was left to the user. Authentication and gameplay are
  unverified in this run; the historical failed sign-in is not a fresh result.
- `pm path com.shungo.app` and `pm list packages shungo` returned no package.
- The launch report found ADB UID 2000, a user build, enforcing SELinux, and no
  accessible Magisk binary. No root or image modifications were performed.

Raw evidence is local and ignored: `artifacts/live-20260913-before/`,
`artifacts/live-20260913-launch/`, `artifacts/live-20260913-after/`, and
`artifacts/live-20260913-settled/`. Screenshots can contain account information.

## Implementation boundary

The new `lab observe` command captures real process and foreground-activity
evidence, screenshots, and a timestamped timeline. It is host-side observation,
not an installed Android companion, an injector, or game automation. Full
Shungo integration has not been implemented or demonstrated. The next step
depends on whether the user wants to install the existing commercial app or
build a new companion, and on completing the game's current login flow.
