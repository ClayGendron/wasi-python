# 197: Protect missing host interpreter folders

## Changelog

### Security

- **Host Python folders are protected before creation.** Writable grants and roots that overlap a configured host interpreter folder are refused even when the folder is missing. This includes the enabled user site. [Grant folders](https://claygendron.github.io/wasi-python/how-to/grants/#what-the-runner-refuses)

## Package rows

None.

## Claims

```toml
[[claim]]
spec = "197"
units = 4
```
