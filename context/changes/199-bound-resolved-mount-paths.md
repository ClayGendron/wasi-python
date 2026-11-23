# 199: Bound resolved mount paths

## Changelog

### Security

- **Mount paths stay within 4,096 bytes.** Relative lookups and renames that would take a provider path over the limit return `ENAMETOOLONG` before the provider receives the change. [Serve files from your own code](https://claygendron.github.io/wasi-python/how-to/mounts/)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "199"
units = 3
```
