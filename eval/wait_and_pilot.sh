#!/usr/bin/env bash
# Wait for the daily quota to reset, then run the resumable pilot and regenerate the report.
# Usage: bash eval/wait_and_pilot.sh <seconds to wait>
cd "$(dirname "$0")/.."
export PATH="$PATH:$LOCALAPPDATA/Microsoft/WinGet/Packages/ezwinports.make_Microsoft.Winget.Source_8wekyb3d8bbwe/bin"
sleep "$1"
make up
make pilot 2>&1 | grep -vE 'approximate input|^\.venvs|^ERROR|^Please retry|^\* Quota'
make report
make down
