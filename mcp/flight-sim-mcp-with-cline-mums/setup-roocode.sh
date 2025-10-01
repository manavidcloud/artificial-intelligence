#!/bin/bash

# Setup script for Roo-Code with logging
LOG_FILE="/root/roocode-setup.log"

# Source bash profile to load environment variables from quiz app
if [ -f /root/.bash_profile ]; then
    source /root/.bash_profile
fi

# Export environment variables if they exist
export OPENAI_API_KEY="${OPENAI_API_KEY}"
export OPENAI_API_BASE="${OPENAI_API_BASE}"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to log and execute commands
log_exec() {
    log "Executing: $1"
    eval "$1" 2>&1 | tee -a "$LOG_FILE"
    local status=$?
    if [ $status -eq 0 ]; then
        log "✓ Success: $1"
    else
        log "✗ Failed: $1 (exit code: $status)"
    fi
    return $status
}

# Start logging
log "========================================="
log "Starting Roo-Code setup script"
log "========================================="

# Log environment info
log "Environment Information:"
log "User: $(whoami)"
log "Working Directory: $(pwd)"
log "Python Version: $(python3 --version 2>&1)"

# Debug: Check if bash_profile was sourced
if [ -f /root/.bash_profile ]; then
    log "Sourced /root/.bash_profile"
else
    log "WARNING: /root/.bash_profile not found"
fi

# Debug: Show all environment variables with OPENAI or AI_KEYS
log "Environment variables containing OPENAI or AI_KEYS:"
env | grep -E "(OPENAI|AI_KEYS)" | while read line; do
    key=$(echo "$line" | cut -d= -f1)
    value=$(echo "$line" | cut -d= -f2-)
    if [[ "$key" == *"KEY"* ]]; then
        # Mask API keys
        log "  $key=${value:0:10}..."
    else
        log "  $line"
    fi
done

log "OPENAI_API_KEY: ${OPENAI_API_KEY:0:10}..." # Show first 10 chars only
log "OPENAI_API_BASE: $OPENAI_API_BASE"

# Step 1: Create virtual environment
log ""
log "Step 1: Creating Python virtual environment"
log_exec "python3 -m venv /root/venv"

# Step 2: Activate virtual environment and run setup script
log ""
log "Step 2: Running setup-roocode-profile.py"
log_exec "source /root/venv/bin/activate && python /root/setup-roocode-profile.py --input /root/settings.json --output /root/settings.json"

# Check if settings.json was created/modified successfully
if [ -f "/root/settings.json" ]; then
    log "Settings file exists at /root/settings.json"
    log "Settings file content (first 200 chars):"
    head -c 200 /root/settings.json | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"
else
    log "ERROR: Settings file not found at /root/settings.json"
fi

# Step 3: Install VS Code extensions
log ""
log "Step 3: Installing VS Code extensions"

# Install Claude Dev extension
log "Installing claude-dev extension..."
log_exec "code-server --install-extension /root/claude-dev-3.17.11.vsix"

# Install Roo-Cline extension
log "Installing roo-cline extension..."
log_exec "code-server --install-extension /root/roo-cline-3.22.5.vsix"

# Verify extensions are installed
log ""
log "Step 4: Verifying installations"
log "Listing installed extensions:"
log_exec "code-server --list-extensions"

# Check if Roo-Coder profile directory exists
PROFILE_DIR="/root/.roo-coder/profiles/default"
if [ ! -d "$PROFILE_DIR" ]; then
    log "Creating Roo-Coder profile directory: $PROFILE_DIR"
    log_exec "mkdir -p $PROFILE_DIR"
fi

# Copy settings.json to profile directory if needed
if [ -f "/root/settings.json" ] && [ -d "$PROFILE_DIR" ]; then
    log "Copying settings.json to profile directory"
    log_exec "cp /root/settings.json $PROFILE_DIR/settings.json"
fi

# Final status
log ""
log "========================================="
log "Setup script completed"
log "Log file saved at: $LOG_FILE"
log "========================================="

# Return success
exit 0