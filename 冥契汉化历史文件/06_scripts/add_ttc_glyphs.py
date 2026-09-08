"""Append missing translated glyphs to the game's TTC fonts."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTCollection, TTFont

from patch_ttc_cmap_aliases import (
    aliases_for_missing,
    cmap_mapping,
    format4_offset,
    ttc_font_offsets,
)


def translation_characters(sheet: Path) -> set[str]:
    characters: set[str] = set()
    with sheet.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            characters.update(row.get("translation", ""))
    return characters


def make_glyph(source: TTFont, name: str, scale: float):
    source_glyph = source.getGlyphSet()[name]
    recording = DecomposingRecordingPen(source.getGlyphSet())
    source_glyph.draw(recording)
    glyph_pen = TTGlyphPen(None)
    recording.replay(TransformPen(glyph_pen, (scale, 0, 0, scale, 0, 0)))
    return glyph_pen.glyph()


def add_to_face(font: TTFont, source: TTFont, characters: list[str]) -> int:
    cmap = font.getBestCmap()
    source_cmap = source.getBestCmap()
    order = list(font.getGlyphOrder())
    new_names: list[str] = []
    glyphs = font["glyf"]
    scale = font["head"].unitsPerEm / source["head"].unitsPerEm

    reference_name = cmap.get(ord("界")) or cmap.get(ord("世"))
    if reference_name is None:
        raise ValueError("game font has no CJK reference glyph")
    reference_metrics = font["hmtx"].metrics[reference_name]
    vertical_metrics = None
    if "vmtx" in font:
        vertical_metrics = font["vmtx"].metrics.get(reference_name)

    added = 0
    for character in characters:
        codepoint = ord(character)
        source_name = source_cmap.get(codepoint)
        if source_name is None:
            raise ValueError(f"source font lacks U+{codepoint:04X}")
        glyph_name = f"cn{codepoint:04X}"
        while glyph_name in glyphs:
            glyph_name += "_"
        glyphs[glyph_name] = make_glyph(source, source_name, scale)
        new_names.append(glyph_name)
        font["hmtx"].metrics[glyph_name] = reference_metrics
        if vertical_metrics is not None:
            font["vmtx"].metrics[glyph_name] = vertical_metrics
        for table in font["cmap"].tables:
            if table.format == 4:
                table.cmap[codepoint] = glyph_name
        cmap[codepoint] = glyph_name
        added += 1
    font.setGlyphOrder(order + new_names)
    return added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ttc", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("sheet", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    characters = translation_characters(args.sheet)
    collection = TTCollection(str(args.ttc))
    source = TTFont(str(args.source))
    source_data = args.ttc.read_bytes()
    first_face = ttc_font_offsets(source_data)[0]
    base_mapping = cmap_mapping(source_data, format4_offset(source_data, first_face)[0])
    aliases = aliases_for_missing(characters, base_mapping)
    missing = sorted(
        set(characters) - set(chr(codepoint) for codepoint in base_mapping) - set(aliases),
        key=ord,
    )
    # Use Simplified Chinese outlines for every translated CJK character and
    # supported non-ASCII punctuation, including characters already present in
    # the original Japanese font. This prevents a valid Unicode lookup from
    # still rendering a traditional/Japanese-style glyph or a blank mark.
    translated_chars = sorted(
        {character for character in characters if ord(character) > 0x7F},
        key=ord,
    )
    total = 0
    for font in collection.fonts:
        total += add_to_face(font, source, translated_chars)
        font.recalcBBoxes = True
        font.recalcTimestamp = False
    args.output.parent.mkdir(parents=True, exist_ok=True)
    collection.save(str(args.output))
    print(f"glyphs_added={total}")
    print(f"unique_characters={len(translated_chars)}")
    print(f"output={args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
