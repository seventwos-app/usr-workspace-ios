# Seventwos Workspace for iOS

Seventwos Workspace for iOS is the native mobile client for the Seventwos workspace. It is being built for people and agents to communicate and collaborate over [Matrix](https://matrix.org/).

The target application uses SwiftUI over the [Matrix Rust SDK](https://github.com/matrix-org/matrix-rust-sdk), exposed to Swift through [UniFFI](https://mozilla.github.io/uniffi-rs/). The shared Rust core provides Matrix synchronisation, local state, and end-to-end encryption while the application remains native to iOS.

## Status

This repository is in transition and is not yet a separately authored Seventwos client.

It currently contains code derived from [Element X iOS](https://github.com/element-hq/element-x-ios), including Element branding and configuration. That inherited code remains subject to Element X's licence terms. Do not represent a build from the current repository as an independent Seventwos implementation.

The migration will replace the inherited application layer with separately authored Seventwos code while retaining the architectural pattern of a native SwiftUI client backed by the Apache-2.0 Matrix Rust SDK.

## Architecture

The intended iOS architecture includes:

- Swift 6 and SwiftUI.
- Matrix Rust SDK integration through Swift Package Manager and UniFFI.
- Client-side Matrix end-to-end encryption.
- Secure credential storage in the Apple Keychain.
- Background synchronisation.
- An iOS Notification Service Extension for encrypted notifications.

Element X is an architectural reference, not the target application codebase.

## Development

Development requires macOS, Homebrew, and the Xcode version selected by `ci_scripts/ci_common.sh`.

After cloning the repository, run:

```sh
swift run tools setup-project
```

The setup command installs the required tools, configures the repository's Git hooks, and generates the Xcode project.

The project uses [XcodeGen](https://github.com/yonaskolb/XcodeGen). Change `project.yml`, `app.yml`, or the relevant target configuration instead of editing `ElementX.xcodeproj` directly.

Dependencies are resolved with Swift Package Manager. To use a locally built Matrix Rust SDK, run:

```sh
swift run tools build-sdk
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development workflow.

## Repository role

The workspace captures intent and human direction. This repository captures implementation, review, and attribution.

Changes should make the transition away from inherited application code explicit and auditable. New product code should follow the repository architecture and contribution rules in [AGENTS.md](AGENTS.md).

## Provenance and licence

The current codebase is derived from Element X iOS, which is dual-licensed under the GNU Affero General Public License v3 or a paid Element Commercial License.

Copyright (c) 2025 - 2026 Element Creations Ltd.

Copyright (c) 2022 - 2025 New Vector Ltd.

See [LICENSE](LICENSE) and [LICENSE-COMMERCIAL](LICENSE-COMMERCIAL) for the terms that apply to inherited code.

The licensing of future separately authored Seventwos components must be documented when those components are introduced. Their inclusion does not alter the licence obligations of inherited Element X code.
