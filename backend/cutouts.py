"""Transparent cutouts of the product photos, so garments can float on the page without black/white boxes.

The provided photos sit on pure black or pure white (some with black side bars). We flood-fill the
background from the image border, soften the edge, trim, and center each garment at the same scale.
Originals in data/products are never modified; results are cached in backend/.cache/cutouts.

Run `python cutouts.py` to build the whole cache ahead of time (the API also builds on demand).
"""

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

PRODUCTS_DIR = Path(__file__).resolve().parent.parent / "data" / "products"
CACHE_DIR = Path(__file__).resolve().parent / ".cache" / "cutouts"
SENTINEL = (255, 0, 255)
OUTPUT_SIZE = 720
MARGIN = 0.07  # empty space around the garment, as a share of the square
SEED_STEP = 6  # px between flood-fill seeds along the border


# Flood-fill tolerances (sum of RGB differences). Tight enough that navy shadows on black and white
# garments on white survive; the strict pair is the retry when a garment still gets eaten.
# (A third, stricter pass was tried for photos whose shadows are as black as the backdrop; it left
# ragged edges and bitten hems, so those photos are kept as photos instead.)
TOLERANCES = [(26, 24), (14, 10)]
MIN_COVERAGE = 0.2  # a garment should fill at least this share of its own bounding box
# Share of transparent pixels inside the garment's outline. Good cutouts score <= 0.12; a photo whose
# shadows are as black as its backdrop scores ~0.3 and is left as a photo instead.
MAX_HOLE_RATIO = 0.2


def _tolerance(pixel: tuple[int, int, int], black_tol: int, white_tol: int) -> int | None:
    if max(pixel) <= 40:
        return black_tol  # black backdrop and black side bars
    if min(pixel) >= 228:
        return white_tol  # white backdrop
    return None


def _background_fill(image: Image.Image, black_tol: int, white_tol: int) -> Image.Image:
    width, height = image.size
    work = image.copy()
    # Seeds on the edge and on rings a few px inside it, so thin frames around a photo don't block the fill.
    seeds = []
    for inset in (0, 4, 10):
        right, bottom = width - 1 - inset, height - 1 - inset
        seeds += [(x, inset) for x in range(inset, right, SEED_STEP)] + [(x, bottom) for x in range(inset, right, SEED_STEP)]
        seeds += [(inset, y) for y in range(inset, bottom, SEED_STEP)] + [(right, y) for y in range(inset, bottom, SEED_STEP)]
    for seed in seeds:
        pixel = work.getpixel(seed)
        if pixel != SENTINEL and (tolerance := _tolerance(pixel, black_tol, white_tol)) is not None:
            ImageDraw.floodfill(work, seed, SENTINEL, thresh=tolerance)
    return work


def _coverage(alpha: Image.Image) -> float:
    box = alpha.getbbox()
    if not box:
        return 0.0
    region = alpha.crop(box)
    solid = region.point(lambda v: 255 if v > 128 else 0).histogram()[255]
    return solid / (region.width * region.height)


def hole_ratio(alpha: Image.Image) -> float:
    """Transparent share of each row between its first and last solid pixel (sampled)."""
    solid = alpha.point(lambda v: 255 if v > 128 else 0)
    width, height = solid.size
    px = solid.load()
    holes = span = 0
    for y in range(0, height, 3):
        xs = [x for x in range(0, width, 2) if px[x, y]]
        if len(xs) < 2:
            continue
        row = (xs[-1] - xs[0]) // 2 + 1
        span += row
        holes += row - len(xs)
    return holes / span if span else 1.0


def make_cutout(source: Path) -> Image.Image:
    image = Image.open(source).convert("RGB")
    width, height = image.size
    # Loosest first (cleanest edges); tighten if the garment got eaten (low coverage or full of holes).
    for black_tol, white_tol in TOLERANCES:
        work = _background_fill(image, black_tol, white_tol)
        diff = ImageChops.difference(work, Image.new("RGB", work.size, SENTINEL)).convert("L")
        mask = diff.point(lambda v: 255 if v > 0 else 0)
        if _coverage(mask) >= MIN_COVERAGE and hole_ratio(mask) <= MAX_HOLE_RATIO:
            break

    # Alpha is 0 wherever the fill reached; erode 1px to drop the JPEG fringe, then feather.
    diff = ImageChops.difference(work, Image.new("RGB", work.size, SENTINEL)).convert("L")
    alpha = diff.point(lambda v: 255 if v > 0 else 0)
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(0.9))

    cutout = image.convert("RGBA")
    cutout.putalpha(alpha)
    box = alpha.point(lambda v: 255 if v > 24 else 0).getbbox() or (0, 0, width, height)
    garment = cutout.crop(box)

    # Center on a square canvas so every product renders at a consistent scale.
    side = round(max(garment.size) / (1 - 2 * MARGIN))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(garment, ((side - garment.width) // 2, (side - garment.height) // 2), garment)
    return canvas.resize((OUTPUT_SIZE, OUTPUT_SIZE), Image.LANCZOS)


def _sources() -> dict[str, Path]:
    return {p.stem: p for p in PRODUCTS_DIR.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}}


def cutout_path(stem: str) -> Path | None:
    """Cached WebP cutout for a product image stem (e.g. 'branford-1-4-zip'), built on first use.

    Returns None when there's no product image with that stem (so paths can't escape the folder)
    or when the cutout failed the quality check; the frontend then shows the original photo.
    """
    source = _sources().get(stem)
    if source is None:
        return None
    target = CACHE_DIR / f"{stem}.webp"
    skip = CACHE_DIR / f"{stem}.skip"
    fresh = lambda p: p.exists() and p.stat().st_mtime >= source.stat().st_mtime
    if fresh(skip):
        return None
    if not fresh(target):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cutout = make_cutout(source)
        if hole_ratio(cutout.getchannel("A")) > MAX_HOLE_RATIO:
            skip.touch()
            target.unlink(missing_ok=True)
            return None
        cutout.save(target, "WEBP", quality=86, method=5)
    return target


def warm_cache() -> None:
    for stem in sorted(_sources()):
        cutout_path(stem)


if __name__ == "__main__":
    stems = sorted(_sources())
    skipped = [stem for i, stem in enumerate(stems, 1) if cutout_path(stem) is None]
    print(f"{len(stems) - len(skipped)}/{len(stems)} cutouts cached in {CACHE_DIR}")
    if skipped:
        print("Kept as photos (cutout failed the quality check):", ", ".join(skipped))
