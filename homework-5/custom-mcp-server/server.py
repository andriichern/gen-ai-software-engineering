from pathlib import Path
from fastmcp import FastMCP


LOREM_PATH = Path(__file__).parent / "lorem-ipsum.md"
DEFAULT_WORD_COUNT = 30

mcp = FastMCP("lorem-ipsum-server")

def _read_words(word_count: int = DEFAULT_WORD_COUNT) -> str:
    if word_count < 0:
        raise ValueError(f"word_count must be >= 0, got {word_count}")
    words = LOREM_PATH.read_text(encoding="utf-8").split()
    return " ".join(words[:word_count])


@mcp.resource("lorem://ipsum")
def lorem_default() -> str:
    """Default word_count (30) slice of lorem-ipsum.md."""
    return _read_words(DEFAULT_WORD_COUNT)


@mcp.resource("lorem://ipsum/{word_count}")
def lorem_with_count(word_count: int) -> str:
    """Parameterized slice of lorem-ipsum.md, e.g. lorem://ipsum/50."""
    return _read_words(word_count)


@mcp.tool()
def read(word_count: int | None = None) -> str:
    """Return the first `word_count` words of lorem-ipsum.md (default 30)."""
    return _read_words(word_count if word_count is not None else DEFAULT_WORD_COUNT)


if __name__ == "__main__":
    mcp.run()
