# Shungo installation and observed architecture

## Result

Installed official Shungo 1.7.0 (versionCode 170), package `com.shungo.app`, on
`poke_api36_test` / `emulator-5556`, Android 16/API 36. The user completed login.
The dashboard loaded but displayed **You need a subscription to use shungo**,
with Start disabled. This shows the account currently has no recognized
entitlement; it does not establish whether the user purchased under another
authentication provider. Overlay permission is still off. No automation ran.

## Actual opening sequence

1. Android launches `com.shungo.app.StartupActivity`.
2. First launch requested notification permission; it was granted.
3. `MainActivity` showed the Shungo sign-in screen.
4. Login opened Chrome Custom Tabs at `auth.shungo.app` with Google, Facebook,
   Discord, or username/password sign-in.
5. After the user's login, the app returned to its dashboard. Home, Stats,
   Account, mode selection, Sniper, Management and Other settings were visible.
6. Other settings visibly included Custom Name, Custom Cooldown, and Maximum
   Catches. No automation settings were changed.

These steps were captured on the actual emulator, not inferred from documentation.

## What the APK establishes

Static DEX/manifest inspection found:

| Component | Evidence and interpretation |
| --- | --- |
| Dashboard | MainActivity constructs a WebView with JavaScript and a native JavaScript bridge. The visual settings UI is supported by an Android wrapper. |
| Authentication | Auth0 authentication/redirect activities are registered. Browser login and return to MainActivity were also observed live. |
| Background execution | MainActivity can start InjectorService with `startForegroundService`. A foreground service is a separate lifecycle component from the dashboard screen. |
| Overlay | InjectorService checks overlay permission and constructs window type 2038 (`TYPE_APPLICATION_OVERLAY`) containing a WebView and an `Android` JavaScript interface. |
| Root commands | The service constructs a `su` process, supplies shell commands and identifies the game using `pidof com.nianticlabs.pokemongo`. This path has not executed in this test. |
| Payload delivery | Code handles injector download metadata including `url` and `injectormd5`, and commands identified as startPogo/inject. The injector is supplied separately. |
| Packaged code | ZIP inspection found one DEX, four assets and no `lib/*.so`. An embedded JAR contains a libsu RootServerMain helper, not the game's native injector. |

The resulting supported architecture is:

```text
Browser login -> Android dashboard/WebView -> foreground InjectorService
                                             |                  |
                                             v                  v
                                      root shell commands    WebView overlay
                                             |
                                             v
                              downloaded injector + game process
```

The precise payload mechanism (ptrace, inline hooks, ART manipulation, game
method mappings, IPC format) remains unverified. Neither generic injection
descriptions nor the presence of an InjectorService proves those details.

## What setup still needs

- An active subscription recognized under the same login provider used for
  purchase. The current dashboard does not recognize one.
- Overlay permission. Automatic approval review rejected the requested grant
  because drawing over other apps is a security-sensitive permission that needs
  explicit user approval. The command was not executed or worked around.
- Working root access and an environment compatible with both applications.
  This clean API 36 emulator has no detected Magisk installation. It was not
  patched. Shungo's official FAQ describes Mac M-series emulators and services
  such as UgPhone, not this Windows x86 emulator, as its emulator paths.
- Successful Pokemon GO login and gameplay, separately from Shungo login.
  Shungo authentication does not authenticate the game.

Official references: [installation](https://docs.shungo.app/info/installation-guide),
[root and emulator FAQ](https://docs.shungo.app/info/faq),
[injector troubleshooting](https://docs.shungo.app/common-issues/crash-failed-to-initialize).
The troubleshooting page documents an ART downgrade option, but does not prove
the pasted binary-copy recipe or justify applying it on this clean emulator.

## Building a similar companion

This is an implementation breakdown, not a claim to possess Shungo source:

1. Android application shell: startup, permissions, dashboard, persisted settings,
   browser login/callback, error reporting, and lifecycle handling.
2. Account backend: identity provider integration, server-side entitlements,
   device/session management, and secure update distribution.
3. Foreground service and overlay: start/stop control, permission checks,
   a defined JavaScript/native interface, and real status/counter updates.
4. Target integration: a version-specific native payload, verified target methods
   and state, IPC, process lifecycle handling, architecture compatibility and
   explicit success/failure signals. This is the missing major component in the
   supplied design. UI reproduction would not provide it.
5. Automation logic: rules driven by actual game events, action scheduling,
   limits, settings validation, recovery, and tests against an authorized target.
6. Maintenance: compatibility validation on every relevant game/Android update.

A sensible independent build proves dashboard/service/overlay/IPC against an
owned test application first, then addresses target integration as a distinct
engineering task. The download/install flow observed here does not establish
that copying the visible interface recreates the commercial product.

## Evidence and provenance

Official download page used `/api/assets/getAPKLink`; its returned CDN URL
delivered the APK. APK SHA-256:
`d2751496c75ced47b6b43bcfd6c96931091fa390f0af56d725ea4ca26df0e20b`.
APK v2 signature verification passed; no independent publisher fingerprint
comparison was available.

Raw/private evidence is ignored under `artifacts/shungo-20260913/`: download
response and link, badging/manifest, `static/`, `before-install/`, `first-launch/`,
`notifications-granted/`, `login-opened/`, `after-user-login/`, `other-settings/`,
and `other-expanded/`. Screenshots can contain the user's profile image.
