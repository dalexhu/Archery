# Downstream integration

Branch `downstream/integration` combines the following work on upstream
`a2675e236da8395940d7316483cdc54b177d2702`.

| Source | Integrated behavior |
| --- | --- |
| #3267, through `4e098abd` | Chinese/English UI and persistent language preference |
| #3268, `bc3c374c` | Doris cloud-vendor version parsing |
| #3269, `d465df68` | Python 3.14 / Debian 12 Bookworm base and native client setup |
| Runtime follow-up, `82a26e6a` / `41234847` | Django 5.2, storage settings, framework regressions and image smoke checks |
| #3270, through `788e07f3` | Driver/security dependencies and safe SSH tunnel cleanup |
| #3271, `115e2c49` | SHA-pinned Node 24 compatible Actions |
| #3275, `a297b99a` | PostgreSQL time/timetz JSON serialization |

The existing connection-mock isolation fix is included through #3267.
Individual commits retain their source messages to support later upstream
synchronization.

## Local build

The application Dockerfile uses the locally built downstream base.

```sh
docker build --platform linux/amd64 -f src/docker/Dockerfile-base -t archery-downstream-base:integration .
docker build --platform linux/amd64 -f src/docker/Dockerfile -t archery-downstream:integration .
docker run --rm --network none --entrypoint bash   -e EXPECTED_DEBIAN_CODENAME=bookworm   -e EXPECTED_PYTHON_VERSION=3.14   -e SECRET_KEY=isolated-downstream-image-smoke-check-only   archery-downstream:integration /opt/archery/src/docker/smoke-test.sh
```

CI builds the same images on pushes to this branch. Django CI covers Python
3.11, 3.12 and 3.14 using temporary MySQL/Redis services.

## Compatibility requirements

- The application metadata database requires MySQL 8.0.11+ or MariaDB 10.5+.
- PyMongo requires MongoDB Server 4.4+ for managed MongoDB connections.
- External binlog consumers using MINIMAL metadata need
  `use_column_name_cache=True` for named row fields.
- Custom storage overrides use Django's `STORAGES` setting.
- Upgrades require review of Django migrations, application data backups and
  rollback planning.
- The image targets linux/amd64 because of bundled native tools. Legacy Mongo
  shell and live authentication/database integrations still require validation.

This branch is the integration candidate for a future downstream release.

## Integration validation

The combined Python 3.14.10 / Django 5.2.19 application passed 1691 tests
with 1 skipped and 164 subtests passed. Tests used fresh MySQL 8.0 and Redis 7.4
containers on an internal Docker network, with temporary storage and synthetic
data. Both the base and application images built successfully. Network-disabled
image smoke checks, dependency consistency, Black and workflow syntax checks
also passed.
