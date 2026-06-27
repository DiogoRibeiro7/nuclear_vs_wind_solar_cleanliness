"""Generate concise public-facing drafts from analysis outputs."""

from __future__ import annotations

from pathlib import Path


def build_cleanliness_article(summary_text: str, image_refs: list[str] | None = None) -> str:
    """Build a sober LinkedIn/Medium-ready article draft."""
    image_refs = image_refs or []
    figure_lines = [f"- {path}" for path in image_refs]
    figure_block = "\n".join(figure_lines)
    if figure_block:
        figure_block = f"\n\nFigures:\n{figure_block}"

    return f"""# Reading the nuclear vs. wind vs. solar claim through data\n\n{summary_text}\n\n## What this analysis does and does not claim\n\nThe result is not a political verdict. It is a comparison across lifecycle carbon intensity with uncertainty shown.\nIt is a statement that "cleaner" needs explicit metrics and context because carbon, safety, land use, and cost do not move in lockstep.\n\n{figure_block}\n\n## Caveats\n\n- Some data sources report summary statistics only.\n- Uncertainty is wide for life-cycle literature values.\n- Broader environmental cleanliness requires more metrics than carbon alone.\n""".strip()


def build_portuguese_draft(summary_text: str, image_refs: list[str] | None = None) -> str:
    """Build a short Portuguese reply draft for social-media posts."""
    image_refs = image_refs or []
    figure_lines = [f"- {path}" for path in image_refs]
    figure_block = "\n".join(figure_lines)
    if figure_block:
        figure_block = f"\n\nFiguras:\n{figure_block}"

    return f"""# Análise do argumento sobre energia nuclear, eólica e solar\n\n{summary_text}\n\nEm vez de reduzir a discussão a uma palavra, o resultado mostra:\n- Nuclear, eólica e solar são opções de baixa emissão no ciclo de vida.\n- A afirmação \"mais limpa\" é dependente do indicador usado.\n- Medições de incerteza são essenciais para não confundir média com certeza.\n\n{figure_block}\n\nLimitação: sem mais métricas (custos, uso do solo, água, resíduos), não existe uma conclusão universal sobre \"limpeza\".\n""".strip()


def write_article_outputs(summary_file: str | Path, output_dir: str | Path, figures: list[str] | None = None) -> tuple[Path, Path]:
    """Write English and Portuguese social-copy outputs."""
    summary = Path(summary_file).read_text(encoding="utf-8")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    en_path = output / "article_draft.md"
    pt_path = output / "artigo_descritivo.md"
    en_path.write_text(build_cleanliness_article(summary, figures), encoding="utf-8")
    pt_path.write_text(build_portuguese_draft(summary, figures), encoding="utf-8")
    return en_path, pt_path
