from dataclasses import dataclass


@dataclass
class DimensionStyle:
    name: str
    display_name: str
    line_style_name: str = "solid_thin"
    text_color: str = "black"
    text_height_mm: float = 5.0
    arrow_size_mm: float = 5.0
    arrow_filled: bool = True
    extension_offset_mm: float = 1.0
    extension_overrun_mm: float = 2.0
    dim_line_extension_mm: float = 0.0
    text_gap_mm: float = 1.0
    decimal_places: int = 2


DEFAULT_DIMENSION_STYLES = {
    "gost_default": DimensionStyle(
        name="gost_default",
        display_name="ГОСТ по умолчанию",
        line_style_name="solid_thin",
        text_color="black",
        text_height_mm=5.0,
        arrow_size_mm=5.0,
        arrow_filled=True,
        extension_offset_mm=1.0,
        extension_overrun_mm=2.0,
        dim_line_extension_mm=0.0,
        text_gap_mm=1.0,
        decimal_places=2,
    ),
    "gost_compact": DimensionStyle(
        name="gost_compact",
        display_name="ГОСТ компактный",
        line_style_name="solid_thin",
        text_color="black",
        text_height_mm=2.5,
        arrow_size_mm=2.5,
        arrow_filled=True,
        extension_offset_mm=0.8,
        extension_overrun_mm=1.5,
        dim_line_extension_mm=0.0,
        text_gap_mm=0.8,
        decimal_places=2,
    ),
}
