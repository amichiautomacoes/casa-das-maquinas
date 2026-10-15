"""Registro local das paginas; cada modulo possui suas secoes e seu layout."""

from collections.abc import Callable
from dataclasses import dataclass

from . import (
    mix_vendas_produtos,
    performance_midia,
    saude_clientes_retencao,
    visao_geral_executiva,
)


@dataclass(frozen=True)
class Page:
    slug: str
    title: str
    layout: Callable[..., object]
    has_metric_selector: bool = False


PAGES = (
    Page("visao-geral-executiva", visao_geral_executiva.TITLE,
         visao_geral_executiva.layout, has_metric_selector=True),
    Page("performance-midia", performance_midia.TITLE, performance_midia.layout),
    Page("mix-vendas-produtos", mix_vendas_produtos.TITLE, mix_vendas_produtos.layout),
    Page("saude-clientes-retencao", saude_clientes_retencao.TITLE,
         saude_clientes_retencao.layout),
)


def get_page(slug: str | None, pages: tuple[Page, ...] = PAGES) -> Page:
    return next((page for page in pages if page.slug == slug), pages[0])
