"""Shared compact layout estimates for readable business-case workbooks."""
import textwrap

CASE_WIDTHS = [17, 28, 23, 32, 34, 48, 48, 40, 28, 22, 14, 22, 48, 18, 16]
TRACE_WIDTHS = [17, 42, 42, 26, 38, 48]


def row_height(values, widths):
    """Estimate wrapped lines without discarding explicit steps or long evidence paths.

    Excel has a 409-point row-height limit. Callers reject overflowing prose
    rather than clipping it; the source text must then be split or shortened.
    """
    lines = max((sum(max(1, len(textwrap.wrap(part, width=max(8, int(width * 0.95)),
                                             break_long_words=True, break_on_hyphens=False)))
                     for part in str(value or '').splitlines() or [''])
                 for value, width in zip(values, widths)), default=1)
    height = max(22, lines * 13.5 + 5)
    if height > 409:
        raise ValueError('Business-case text exceeds one readable Excel row. Shorten or restructure it before exporting.')
    return height
