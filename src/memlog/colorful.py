# File: colorful.py
# Date: 2026/2/27
# Desc:
import enum
from typing import Optional
import click
from humanfriendly import text

from .enums import StyleColor


def colorful(text: str, bold: bool = False, fg: Optional[StyleColor] = None, bg: Optional[StyleColor] = None,
             underline: Optional[bool] = None, overline: Optional[bool] = None, italic: Optional[bool] = None,
             reset: bool = True,):
    return click.style(text, bold=bold, fg=fg.value if fg else None, bg=bg.value if bg else None,
                       underline=underline, overline=overline, italic=italic,reset=reset)

def remove_color(text: str) -> str:
    return click.unstyle(text)

def colorful_title(text: str) -> str:
    return colorful(text, bold=True,bg=StyleColor.BLACK, fg=StyleColor.WHITE)

def colorful_head(text):
    return colorful(text, fg=StyleColor.MAGENTA)


def colorful_traceback(text):
    return colorful(text, fg=StyleColor.BLUE)


def colorful_size(text):
    return colorful(text, fg=StyleColor.CYAN)


def colorful_count(text):
    return colorful(text, fg=StyleColor.CYAN)


def colorful_size_diff(text):
    return colorful(text, fg=StyleColor.GREEN if text.startswith('-') else StyleColor.YELLOW)
