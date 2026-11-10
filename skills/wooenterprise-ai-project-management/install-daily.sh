#!/bin/sh
# Install (or reinstall) the daily WooEnterprise PM run: weekdays 7:30am local, emailed to EMAIL.
#   install-daily.sh [email]                full sweep (Slack, email, sheet edits) via headless claude
#   install-daily.sh --digest-only [email]  script-only digest, no sweep
# Remove with: launchctl unload ~/Library/LaunchAgents/com.nagomi.daily.plist && rm that file
# Re-run after a plugin update when using --digest-only: the job points at this copy of check_plan.py.
MODE=sweep
[ "$1" = "--digest-only" ] && MODE=digest && shift
EMAIL="${1:-$(git config --global user.email)}"
[ -n "$EMAIL" ] || { echo "Usage: install-daily.sh [--digest-only] you@example.com"; exit 1; }
DIR="$(cd "$(dirname "$0")" && pwd)"
DATA="${NAGOMI_HOME:-$HOME/.nagomi}"
PLIST="$HOME/Library/LaunchAgents/com.nagomi.daily.plist"

if [ "$MODE" = digest ]; then
  ARGS="<string>/opt/homebrew/bin/python3</string><string>$DIR/check_plan.py</string><string>--email</string><string>$EMAIL</string>"
else
  PROMPT="Run the nagomi:wooenterprise-ai-project-management skill, Job 5 (sweep updates), for every project in ~/.nagomi/projects.json. Email the digest to $EMAIL. Follow the never-override rule: skip and report any cell or row a person changed."
  TOOLS="Skill Read mcp__context-a8c__context-a8c-load-provider mcp__context-a8c__context-a8c-execute-tool Bash(gws:*) Bash(python3:*) mcp__claude_ai_Slack__slack_read_channel mcp__claude_ai_Slack__slack_read_thread mcp__claude_ai_Gmail__search_threads mcp__claude_ai_Gmail__get_thread mcp__claude_ai_Zoom_for_Claude__search_meetings mcp__claude_ai_Zoom_for_Claude__get_meeting_assets"
  ARGS="<string>$(command -v claude)</string><string>-p</string><string>$PROMPT</string><string>--allowedTools</string><string>$TOOLS</string>"
fi

days=""
for d in 1 2 3 4 5; do
  days="$days<dict><key>Weekday</key><integer>$d</integer><key>Hour</key><integer>7</integer><key>Minute</key><integer>30</integer></dict>"
done

cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.nagomi.daily</string>
  <key>ProgramArguments</key><array>$ARGS</array>
  <key>WorkingDirectory</key><string>$DATA</string>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
  <key>StartCalendarInterval</key><array>$days</array>
  <key>StandardOutPath</key><string>/tmp/nagomi-daily.log</string>
  <key>StandardErrorPath</key><string>/tmp/nagomi-daily.log</string>
</dict></plist>
PL

launchctl unload "$PLIST" 2>/dev/null
launchctl load "$PLIST" && echo "Installed ($MODE): weekdays 7:30am -> $EMAIL (log: /tmp/nagomi-daily.log)"
