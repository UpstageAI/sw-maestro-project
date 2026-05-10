# Subtree All-at-Once

A simple automation tool for managing multiple git subtrees from a single configuration.

## Quick Start

1. Configure your project in `global.config`:
```ini
ENTIRE_GIT_GROUP=https://github.com/username
ENTIRE_GIT_NAME=your-repo-name
DEFAULT_BRANCH=main
AUTO_PUSH=true
```

2. Create subtree configuration files in `.subtrees/`:
```ini
REPO_URL=https://github.com/owner/repo.git
BRANCH=main
PREFIX=path/to/subtree
MODE=auto
SQUASH=false
```

3. Run the setup script:
```bash
./subtree-setup.sh
```

## Features

- **Batch Processing**: Configure multiple subtrees and process them all at once
- **Auto Mode**: Automatically determines whether to add or pull based on existing directories
- **Flexible Operations**: Supports add, pull, and push operations
- **Squash Support**: Optional commit squashing for cleaner history

## Configuration Options

### Global Config
- `ENTIRE_GIT_GROUP`: Repository base URL
- `ENTIRE_GIT_NAME`: Main repository name
- `DEFAULT_BRANCH`: Default branch name
- `AUTO_PUSH`: Automatically push after processing

### Subtree Config
- `REPO_URL`: Remote repository URL
- `BRANCH`: Branch to track
- `PREFIX`: Local path for the subtree
- `MODE`: Operation mode (auto/add/pull/push)
- `SQUASH`: Enable commit squashing (true/false)
- `REMOTE_NAME`: Custom remote name (optional)
- `PUSH_BRANCH`: Target branch for push mode (optional)
