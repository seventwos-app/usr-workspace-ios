# Seventwos repository configuration

## Project configuration

The repository defaults to the Seventwos product identity:

```yaml
APP_DISPLAY_NAME: Seventwos Workspace
PRODUCTION_APP_NAME: Seventwos Workspace
APP_GROUP_IDENTIFIER: group.org.seventwos.workspace
BASE_BUNDLE_IDENTIFIER: org.seventwos.workspace
```

`DEVELOPMENT_TEAM` is intentionally empty because no Seventwos Apple Developer account exists yet. This permits unsigned simulator development without inheriting Element's signing identity. Set the team through secured release automation or a local build-setting override after the account exists, then run `xcodegen` to regenerate the project. Do not commit signing certificates, provisioning profiles, App Store Connect keys, or team credentials.

The production application domain is `workspace.seventwos.org`. The checked-in associated-domain, OAuth redirect, account-provider, provisioning-host, and push-gateway defaults use that domain. Before enabling those capabilities in a signed build, Seventwos infrastructure must provide:

- Matrix client discovery and the push gateway expected by the app.
- `apple-app-site-association` entries for `applinks` and `webcredentials` covering `org.seventwos.workspace`.
- The OAuth callback path `/oauth/ios/org.seventwos.workspace` and matching MAS client metadata.

## Runtime configuration

[AppSettings.swift](../ElementX/Sources/Application/Settings/AppSettings.swift) contains runtime service configuration. Required legal, policy, logo, and help URLs use `example.invalid` placeholders so the app cannot silently send users to inherited Element services or claim that unprovisioned Seventwos URLs exist. Replace every placeholder with an approved, live Seventwos URL before release; the manual **Release Readiness** workflow fails while any remain.

Analytics, Sentry, rageshake diagnostics, call analytics, and MapLibre are disabled in the checked-in `Components/Secrets/Secrets.swift`. To enable a Seventwos-owned deployment, inject the corresponding environment variables into trusted build automation and regenerate the file with:

```sh
pkl eval -o Components/Secrets/Secrets.swift Components/Secrets/Secrets.pkl
```

Never commit the generated values. Release automation must restore the checked-in nil configuration after the archive is produced, and reviewers should verify that `Components/Secrets/Secrets.swift` contains only `nil` values. Partial call telemetry configuration is ignored: all call PostHog and Sentry values must be present before call telemetry is enabled.

## Release preparation

Repository automation does not publish an App Store build or dispatch to Element infrastructure. Calendar version updates and release-readiness checks are manual workflows. The GitHub release command targets `GITHUB_REPOSITORY` and pushes only its current branch; it does not merge or rebase `main`.

Before creating a production archive:

1. Create Seventwos Apple Developer and App Store Connect accounts; configure the team, certificates, identifiers, app group, push entitlement, and provisioning profiles outside the repository.
2. Provision and verify the `workspace.seventwos.org` Matrix, OAuth, associated-domain, account-provisioning, and push services.
3. Publish approved legal, privacy, support, security, logo, and encryption-help pages, then replace all `example.invalid` placeholders.
4. Keep analytics, hosted diagnostics, maps, and call telemetry disabled unless Seventwos-owned endpoints and credentials are supplied through secret storage.
5. Run `xcodegen`, build and test the Release configuration, and manually run the **Release Readiness** workflow.
6. Review the archive's identifiers, entitlements, privacy disclosures, signing identity, and network destinations before uploading it to App Store Connect.