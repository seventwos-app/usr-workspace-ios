#!/bin/sh

source ci_common.sh

# Move to the project root
cd ..

# Xcode Cloud shallow clones the repo. We need to deepen it to fetch tags, commit history and be able to rebase main on develop at the end of releases.
fetch_unshallow_repository

# Upload dsyms when Seventwos-owned Sentry configuration is present.
# Perform this step before releasing to github in case it fails.
upload_dsyms_if_configured

generate_what_to_test_notes

if [ "$CI_WORKFLOW" = "Release" ]; then
    swift run -q tools ci release-to-github
elif [ "$CI_WORKFLOW" = "Nightly" ]; then
    swift run -q tools ci tag-nightly --build-number "$CI_BUILD_NUMBER"
fi
