#!/bin/sh

set -eu

project_root="${1:-$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)}"

fail() {
    echo "release-readiness: $1" >&2
    exit 1
}

app_config="$project_root/app.yml"
app_settings="$project_root/ElementX/Sources/Application/Settings/AppSettings.swift"
secrets="$project_root/Components/Secrets/Secrets.swift"
target_config="$project_root/ElementX/SupportingFiles/target.yml"
entitlements="$project_root/ElementX/SupportingFiles/ElementX.entitlements"
bug_report_service="$project_root/ElementX/Sources/Services/BugReport/BugReportService.swift"

for file in "$app_config" "$app_settings" "$secrets" "$target_config" "$entitlements" "$bug_report_service"; do
    [ -f "$file" ] || fail "missing required file: $file"
done

grep -Fq "BASE_BUNDLE_IDENTIFIER: org.seventwos.workspace" "$app_config" ||
    fail "BASE_BUNDLE_IDENTIFIER must be org.seventwos.workspace."

grep -Fq "APP_GROUP_IDENTIFIER: group.org.seventwos.workspace" "$app_config" ||
    fail "APP_GROUP_IDENTIFIER must be group.org.seventwos.workspace."

grep -Fq "workspace.seventwos.org" "$app_settings" ||
    fail "workspace.seventwos.org must be configured as the production application domain."

if grep -Eq 'DEVELOPMENT_TEAM:[[:space:]]*""' "$app_config"; then
    fail "configure the Seventwos Apple Development Team before release."
fi

if grep -Fq "example.invalid" "$app_settings"; then
    fail "replace documented policy and help URL placeholders before release."
fi

if grep -Eiq 'element\.io|vector\.im|sentry\.tools\.element\.io|posthog-element-call\.element\.io' \
    "$app_config" \
    "$app_settings" \
    "$secrets" \
    "$target_config" \
    "$entitlements" \
    "$bug_report_service"; then
    fail "inherited Element production service configuration remains."
fi

if grep -Eq 'CLASSIC_APP_GROUP_IDENTIFIER|CLASSIC_APP_KEYCHAIN_ACCESS_GROUP_IDENTIFIER' \
    "$target_config" "$entitlements"; then
    fail "inherited Classic app entitlements remain."
fi

echo "release-readiness: repository configuration is ready."
