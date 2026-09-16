# Seventwos Workspace for iOS

Seventwos Workspace for iOS is the native iOS client for the Seventwos workspace. It is built on top of a fork of [Element X iOS](https://github.com/element-hq/element-x-ios) and is being evolved for people and agents to communicate and collaborate over [Matrix](https://matrix.org/).

The project retains Element X's native-client approach: SwiftUI over the [Matrix Rust SDK](https://github.com/matrix-org/matrix-rust-sdk), exposed to Swift through its bindings. The shared Rust core provides Matrix synchronisation, local state, and end-to-end encryption while the application remains native to iOS.

## Status

This repository is in transition from its Element X foundation to a separately authored Seventwos application layer.

The current code includes inherited Element X iOS code, branding, and configuration. This fork redistributes that code under the GNU Affero General Public License v3 and must not be represented as an independently authored Seventwos implementation. The transition will replace the inherited application layer with Seventwos code while retaining the native-client architecture and the Apache-2.0 Matrix Rust SDK.

## Architecture

The intended iOS implementation includes:

- Swift and SwiftUI.
- Matrix Rust SDK integration through Swift bindings (via UniFFI).
- Client-side Matrix end-to-end encryption.
- Secure credential storage in the iOS Keychain.
- Background synchronisation.
- Apple push notifications for encrypted messages.

Element X is the upstream foundation and architectural reference for this workspace, not the target product identity.

## Repository role

The Seventwos workspace captures product intent and human direction. This repository captures the iOS implementation, review history, and upstream attribution.

Changes should make the transition from inherited application code explicit and auditable. New product code should follow the repository's architecture and contribution rules.

## Provenance and licence

This repository began as a fork of Element X iOS and is now maintained as Seventwos Workspace for iOS.

Copyright (c) 2025 Element Creations Ltd.

Copyright (c) 2022 - 2025 New Vector Ltd.

These upstream copyright notices are retained in recognition of the work on which this fork is based.

We license the repository-owned code under the GNU Affero General Public License v3 only. See [LICENSE](LICENSE) for the applicable terms. Third-party dependencies remain under their respective licences.

Our modifications and newly authored repository code use AGPL-3.0-only. When we distribute a modified version or make one available for users to interact with over a network, we provide the corresponding source as required by the AGPL.
