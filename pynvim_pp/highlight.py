from dataclasses import dataclass
from typing import AbstractSet, Optional

from .atomic import Atomic


@dataclass(frozen=True)
class HLgroup:
    name: str
    default: bool = True
    cterm: AbstractSet[str] = frozenset()
    ctermfg: Optional[int] = None
    ctermbg: Optional[int] = None
    gui: AbstractSet[str] = frozenset()
    guifg: Optional[str] = None
    guibg: Optional[str] = None


def highlight(*groups: HLgroup) -> Atomic:
    atomic = Atomic()
    for group in groups:
        name = group.name
        df = "default" if group.default else ""
        _cterm = ",".join(group.cterm) or "NONE"
        cterm = f"cterm={_cterm}"
        ctermfg = f"ctermfg={group.ctermfg}" if group.ctermfg else ""
        ctermbg = f"ctermbg={group.ctermbg}" if group.ctermbg else ""
        gui = f"gui={','.join(group.gui) or 'NONE'}"
        guifg = f"guifg={group.guifg}" if group.guifg else ""
        guibg = f"guibg={group.guibg}" if group.guibg else ""

        hl_line = (
            f"highlight {df} {name} {cterm} {ctermfg} {ctermbg} {gui} {guifg} {guibg}"
        )

        atomic.command(hl_line)

    return atomic


def hl_link(default: bool, **links: str) -> Atomic:
    df = "default" if default else ""
    atomic = Atomic()
    for src, dest in links.items():
        link = f"highlight {df} link {src} {dest}"
        atomic.command(link)
    return atomic
