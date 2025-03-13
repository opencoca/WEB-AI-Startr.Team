# Maintenance Guidelines

## Makefile Best Practices

### Always Add Reusable Operations to the Makefile

Whenever you find yourself performing operations that:
- Need to be run more than once
- Might need to be run by other team members
- Involve multiple steps or complex commands
- Are part of development, testing, or deployment workflows

**Add them to the Makefile as targets.**

Benefits:
1. **Documentation** - The Makefile serves as living documentation of common operations
2. **Reproducibility** - Ensures consistent execution across different environments
3. **Knowledge Sharing** - Makes it easier for new team members to perform complex tasks
4. **Error Reduction** - Reduces the chance of errors from manual command execution

### Example Targets

The Makefile includes several targets for common operations:

- **JSON Configuration Fix**: `make fix-json-configs` and `make docker-fix-json-configs`
  - Fixes JSON syntax errors by removing comments from configuration files
- **API Key Management**: `make init-env`, `make docker-update-keys`, and related commands
  - Manages API keys in local and Docker environments

## API Key Management

Proper API key management is critical for both security and functionality. The project supports API keys through:

1. **Environment Variables** - Set directly in the shell
2. **`.env` File** - A local file containing API keys (not committed to git)
3. **Docker Environment** - Environment variables passed to Docker containers

### API Key Management Workflows

The Makefile includes several targets to simplify API key management:

- **`make init-env`**: Creates a `.env` file from `.env.example` if one doesn't exist
- **`make verify-api-keys`**: Tests if your API keys are working correctly in the local environment
- **`make docker-update-keys`**: Updates the Docker container with API keys from your local `.env` file
- **`make docker-restart`**: Restarts the application inside Docker to apply new environment variables
- **`make docker-update-and-restart`**: Combines the update and restart operations
- **`make docker-verify-api-keys`**: Tests if your API keys are working correctly inside the Docker container

### Best Practices for API Keys

1. **Never commit API keys to git** - The `.env` file is in `.gitignore` for a reason
2. **Always verify API keys after updates** - Use the verification commands to ensure keys are working
3. **Update Docker after changing local keys** - When you update your `.env` file, run `make docker-update-and-restart`
4. **Include environment variables in documentation** - Make sure all required variables are in `.env.example`

## Codebase Cleanup Opportunities

As noted in the README.md, the following areas have been identified for potential cleanup:

1. **Duplicate Configuration Files**
   - Review and consolidate redundant configurations in config/CompanyConfig directories
   - Target: Streamline configuration management

2. **Outdated Dependencies**
   - Review and update packages in requirements.txt and Pipfile
   - Consider adding a `make update-deps` target to check and update dependencies

3. **Legacy Code Sections**
   - Identify and refactor older, less optimized implementations
   - Prioritize based on performance impact and maintenance burden

4. **Incomplete Documentation**
   - Add missing documentation to key components
   - Consider automated documentation tools

5. **Unused Files**
   - Identify and remove unused files to streamline the repository
   - Consider adding a `make cleanup` target to identify unused files

6. **Inconsistent Error Handling**
   - Standardize error handling approaches across different modules
   - Create consistent patterns for error reporting and recovery

7. **Environment Variable Management**
   - Improve how environment variables (especially API keys) are loaded and managed
   - Consider a more robust dotenv implementation with validation

## Configuration Improvements

The JSON configuration files currently have several issues that could be addressed:

1. **JSON Comments**: Standard JSON doesn't support comments, but they're useful for documentation. Options:
   - Switch to a format that supports comments (YAML, TOML, JSON5)
   - Use a preprocessing step (current approach with Makefile)
   - Use normal JSON fields for documentation

2. **Boolean Values**: Currently stored as strings ("True"/"False") rather than actual boolean values
   - Standardize on true/false boolean literals

3. **Schema Validation**: Add schema validation for configuration files to catch errors early

## Maintenance Process

When addressing technical debt or making maintenance improvements:

1. Document the issue in the GitHub issue tracker
2. Add appropriate targets to the Makefile for any recurring operations
3. Update this document with any new maintenance guidelines
4. Reference the issue in commit messages 