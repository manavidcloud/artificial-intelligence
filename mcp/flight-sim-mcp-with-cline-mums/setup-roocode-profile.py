#!/usr/bin/env python3
"""
Setup Roo-Code Profile Script

This script reads environment variables and replaces placeholders in the settings.json file.
It supports an optional --model argument to override the default model name.

Usage:
    python setup-roocode-profile.py
    python setup-roocode-profile.py --model "custom/model-name"
"""

import os
import sys
import json
import argparse
from pathlib import Path


def setup_argument_parser():
    """Set up command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Setup Roo-Code profile by replacing placeholders with environment variables"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="openai/gpt-4.1-mini",
        help="Model name to use (default: openai/gpt-4.1-mini)"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="settings.json",
        help="Input settings file path (default: settings.json)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="settings.json",
        help="Output settings file path (default: settings.json)"
    )
    return parser


def read_environment_variables():
    """Read required environment variables."""
    env_vars = {
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        "OPENAI_API_BASE": os.environ.get("OPENAI_API_BASE")
    }
    
    # Check if required environment variables are set
    missing_vars = [key for key, value in env_vars.items() if value is None]
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    return env_vars


def update_json_values(settings_data, env_vars, model_name):
    """Update JSON values with environment variables."""
    # Navigate through the JSON structure and update values
    if "providerProfiles" in settings_data:
        if "apiConfigs" in settings_data["providerProfiles"]:
            # Update kodekey-profile configuration
            if "kodekey-profile" in settings_data["providerProfiles"]["apiConfigs"]:
                profile = settings_data["providerProfiles"]["apiConfigs"]["kodekey-profile"]
                
                # Update API key
                profile["openAiApiKey"] = env_vars["OPENAI_API_KEY"]
                
                # Update base URL
                profile["openAiBaseUrl"] = env_vars["OPENAI_API_BASE"]
                
                # Update model ID
                profile["openAiModelId"] = model_name
    
    return settings_data


def process_settings_file(input_path, output_path, model_name):
    """Process the settings file and update JSON values."""
    try:
        # Read environment variables
        env_vars = read_environment_variables()
        
        # Read and parse the JSON file
        with open(input_path, 'r') as f:
            settings_data = json.load(f)
        
        # Update JSON values
        settings_data = update_json_values(settings_data, env_vars, model_name)
        
        # Write the output file with proper formatting
        with open(output_path, 'w') as f:
            json.dump(settings_data, f, indent=2)
        
        print(f"✅ Successfully processed settings file")
        print(f"   Input: {input_path}")
        print(f"   Output: {output_path}")
        print(f"   Model: {model_name}")
        print(f"   API Base: {env_vars['OPENAI_API_BASE']}")
        
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in settings file - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: An unexpected error occurred - {e}")
        sys.exit(1)


def main():
    """Main function to execute the script."""
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    # Process the settings file
    process_settings_file(args.input, args.output, args.model)


if __name__ == "__main__":
    main()
