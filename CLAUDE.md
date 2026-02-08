# n8n-client Development Guide

## Release Process

### Publishing to PyPI

This project uses GitHub Actions with PyPI Trusted Publishers for automated releases.

#### Prerequisites
- Trusted Publisher configured on PyPI for `n8n-client`
- Owner: `pokgak`
- Repository: `n8n-client`
- Workflow: `publish.yml`

#### Release Steps

1. **Update version** in `pyproject.toml`:
   ```toml
   version = "x.y.z"
   ```

2. **Commit and push changes**:
   ```bash
   git add pyproject.toml
   git commit -m "Bump version to x.y.z"
   git push
   ```

3. **Create and push tag**:
   ```bash
   git tag vx.y.z
   git push origin vx.y.z
   ```

4. **Create GitHub release**:
   ```bash
   gh release create vx.y.z --title "vx.y.z" --notes ""
   ```

5. **Monitor workflow**:
   ```bash
   gh run list --limit 3
   gh run watch
   ```

The GitHub Action will automatically build and publish to PyPI.

Package will be available at: https://pypi.org/project/n8n-client/

#### Manual Build (for testing)

```bash
# Build package locally
uv build

# Check built packages
ls -lh dist/
```

## Package Info

- **Package name**: `n8n-client`
- **Command**: `n8n-client`
- **GitHub**: https://github.com/pokgak/n8n-client
- **PyPI**: https://pypi.org/project/n8n-client/
