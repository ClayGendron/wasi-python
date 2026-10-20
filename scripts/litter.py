"""Names an operating system or its helpers write into folders on their own:
macOS Finder and its folder-size cache, Windows Explorer, and a volume's own folders. No build
input reads them and no artifact may carry them. The judge keeps the same set and rules in
`tests/harness/paths.py`; a unit check holds the two equal."""

OS_LITTER = frozenset(
    {
        ".DS_Store",
        "Thumbs.db",
        "desktop.ini",
        "ehthumbs.db",
        "Icon\r",  # a folder's custom icon
        ".Spotlight-V100",  # the rest are a volume's root folders
        ".fseventsd",
        ".Trashes",
        ".TemporaryItems",
        ".DocumentRevisions-V100",
        ".apdisk",
    }
)


def is_litter(name: str) -> bool:
    """True for a name only an operating system leaves; AppleDouble `._x` files by their prefix."""
    return name in OS_LITTER or name.startswith("._")


def has_litter(rel: str) -> bool:
    """True when any part of a `/`-separated path is litter (a file inside a litter folder too)."""
    return any(is_litter(part) for part in rel.replace("\\", "/").split("/"))


def git_excludes() -> list[str]:
    """The pathspecs that keep every path `has_litter` names out of a `git add` (spec 097): each
    name, and anything inside it, at any depth, and the same for AppleDouble `._*`. git then never
    opens a litter file, which a desktop writer may rewrite or remove mid-add. No name in
    OS_LITTER holds a glob character, so each matches only itself."""
    globs = [*sorted(OS_LITTER), "._*"]
    return [f":(exclude,glob)**/{g}{tail}" for g in globs for tail in ("", "/**")]
