#!/bin/sh

# Return on failures
# Fail when expanding unset variables
# Trace each command before executing it
set -eEu

install_xcode_cloud_brew_dependencies () {
    brew update && brew install xcodegen pkl getsentry/tools/sentry-cli
}

setup_github_actions_environment() {
    xcode_select_for_github_actions
    
    unset HOMEBREW_NO_INSTALL_FROM_API
    export HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1
    
    brew update && brew install xcodegen swiftlint swiftformat git-lfs pkl
}

setup_github_actions_translations_environment() {
    xcode_select_for_github_actions
    
    unset HOMEBREW_NO_INSTALL_FROM_API
    export HOMEBREW_NO_INSTALLED_DEPENDENTS_CHECK=1

    brew update && brew install swiftgen mint localazy/tools/localazy

    mint install Asana/locheck
}

xcode_select_for_github_actions() {
    # We need to select it globally for our custom tools to use the same Xcode version.
    sudo xcode-select -s /Applications/Xcode_26.5.0.app
}

generate_what_to_test_notes() {
    if [[ -d "$CI_APP_STORE_SIGNED_APP_PATH" ]]; then
        TESTFLIGHT_DIR_PATH=TestFlight
        TESTFLIGHT_NOTES_FILE_NAME=WhatToTest.en-US.txt
        
        LATEST_TAG=""
        if [ "$CI_WORKFLOW" = "Release" ]; then
            # Use -v to invert grep, searching for non-nightlies
            LATEST_TAG=$(git tag --sort=-creatordate | grep -v 'nightly' | head -n1)
        elif [ "$CI_WORKFLOW" = "Nightly" ]; then
            LATEST_TAG=$(git tag --sort=-creatordate | grep 'nightly' | head -n1)
        fi

        if [[ -z "$LATEST_TAG" ]]; then
            echo "generate_what_to_test_notes: Failed fetching previous tag"
            return 0 # Continue even though this failed
        fi

        echo "generate_what_to_test_notes: latest tag is $LATEST_TAG"

        mkdir $TESTFLIGHT_DIR_PATH

        NOTES="$(git log --pretty='- %an: %s' "$LATEST_TAG"..HEAD)"

        echo "generate_what_to_test_notes: Generated notes:\n"$NOTES""

        echo "$NOTES" > $TESTFLIGHT_DIR_PATH/$TESTFLIGHT_NOTES_FILE_NAME
    fi
}

fetch_unshallow_repository() {
    # Xcode Cloud shallow clones the repo. We need to deepen it to fetch tags, commit history and be able to rebase main on develop at the end of releases.
    git fetch --unshallow --quiet
}

upload_dsyms_if_configured() {
    # Seventwos does not (yet) have its own Sentry organization/project provisioned.
    # UploadDSYMs requires SENTRY_ORG_SLUG, SENTRY_PROJECT_SLUG and SENTRY_URL to be
    # supplied explicitly and never falls back to Element's Sentry endpoints, so this
    # step is opt-in and only runs when a complete Seventwos-owned configuration is
    # present via CI environment variables (SENTRY_AUTH_TOKEN is validated separately
    # by the tool itself).
    if [ -n "${SENTRY_ORG_SLUG:-}" ] && [ -n "${SENTRY_PROJECT_SLUG:-}" ] && [ -n "${SENTRY_URL:-}" ] && [ -n "${SENTRY_AUTH_TOKEN:-}" ]; then
        swift run -q tools ci upload-dsyms \
            --dsym-path "$CI_ARCHIVE_PATH/dSYMs" \
            --org-slug "$SENTRY_ORG_SLUG" \
            --project-slug "$SENTRY_PROJECT_SLUG" \
            --url "$SENTRY_URL"
    elif [ "$CI_WORKFLOW" = "Release" ]; then
        # Release builds must fail closed rather than silently ship without crash
        # symbolication once Sentry is expected to be configured.
        echo "upload_dsyms_if_configured: SENTRY_ORG_SLUG, SENTRY_PROJECT_SLUG, SENTRY_URL and SENTRY_AUTH_TOKEN must all be set to upload dSYMs for a Release build." >&2
        return 1
    else
        echo "upload_dsyms_if_configured: skipping dSYM upload — Seventwos Sentry is not configured for this workflow (Element's Sentry endpoints are never used as a fallback)."
    fi
}
