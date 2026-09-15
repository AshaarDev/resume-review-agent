"""Safe inline emphasis shared by manual resume output renderers."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class InlineSegment:
    text: str
    bold: bool = False
    italic: bool = False


_EMPHASIS = re.compile(
    r"\*\*\*(.+?)\*\*\*"
    r"|\*\*(.+?)\*\*"
    r"|\*(.+?)\*",
    re.DOTALL,
)
_DUPLICATE_BOLD_ITALIC = re.compile(
    r"(?<!\*)\*{6}(?!\*)(.+?)(?<!\*)\*{6}(?!\*)",
    re.DOTALL,
)
_DUPLICATE_BOLD = re.compile(
    r"(?<!\*)\*{4}(?!\*)(.+?)(?<!\*)\*{4}(?!\*)",
    re.DOTALL,
)


def normalize_inline_formatting(value: str) -> str:
    """Repair duplicated delimiters emitted by early rich-editor versions."""

    value = _DUPLICATE_BOLD_ITALIC.sub(r"***\1***", value)
    return _DUPLICATE_BOLD.sub(r"**\1**", value)


def parse_inline_formatting(value: str) -> list[InlineSegment]:
    """Parse bounded Markdown-style bold/italic markers without accepting HTML."""

    value = normalize_inline_formatting(value)
    segments: list[InlineSegment] = []
    cursor = 0
    for match in _EMPHASIS.finditer(value):
        if match.start() > cursor:
            segments.append(InlineSegment(value[cursor:match.start()]))
        if match.group(1) is not None:
            nested = parse_inline_formatting(match.group(1))
            segments.extend(
                InlineSegment(part.text, bold=True, italic=True)
                for part in nested
            )
        elif match.group(2) is not None:
            nested = parse_inline_formatting(match.group(2))
            segments.extend(
                InlineSegment(part.text, bold=True, italic=part.italic)
                for part in nested
            )
        else:
            nested = parse_inline_formatting(match.group(3))
            segments.extend(
                InlineSegment(part.text, bold=part.bold, italic=True)
                for part in nested
            )
        cursor = match.end()
    if cursor < len(value):
        segments.append(InlineSegment(value[cursor:]))
    if not segments:
        return [InlineSegment(value)]
    merged: list[InlineSegment] = []
    for segment in segments:
        if (
            merged
            and merged[-1].bold == segment.bold
            and merged[-1].italic == segment.italic
        ):
            previous = merged[-1]
            merged[-1] = InlineSegment(
                previous.text + segment.text,
                bold=segment.bold,
                italic=segment.italic,
            )
        else:
            merged.append(segment)
    return merged
