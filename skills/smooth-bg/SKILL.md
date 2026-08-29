---
name: smooth-bg
description: "Ultra-smooth background remover, edge anti-aliasing, and transparent PNG asset extractor for generated UI icons, illustrations, stickers, and mascots. Uses 4x supersampling, boundary-seed floodfill, signed distance field (SDF) matting, and color defringing to eliminate white halos and pixelated edges. Triggers: remove background, transparent asset, cutout, khử răng cưa, làm mịn viền, tách nền, transparent png, defringe, anti-aliasing matte."
metadata:
  last-verified: "2026-08-29"
  short-description: "4x supersampling SDF background removal and sub-pixel anti-aliased cutout pipeline."
---

# Smooth Background Remover & Sub-Pixel Anti-Aliased Matte

Extracts clean, high-fidelity transparent PNGs (RGBA) from generated UI assets, icons, logos, stickers, and illustrations with zero white halos and ultra-smooth vector-like edges.

## Why Standard Background Removal Fails on Generated Assets

1. **Inner detail loss:** Naive color replacement erases white eyes, teeth, highlights, and white clothing inside characters.
2. **Fringing & White halos:** Semi-transparent edge pixels blend with the white background, causing a visible white outline when placed on dark or colored surfaces.
3. **Pixelated / Jagged edges:** Direct alpha thresholding produces jagged stair-step contours.

## Solution Pipeline

This skill uses a mathematical 5-stage pipeline:
1. **4x Lanczos Supersampling:** Upscales the image into high-precision sub-pixel coordinate space.
2. **Boundary-Seed Floodfill:** Strictly identifies background regions starting from the outer image borders (`scipy.ndimage.label`), protecting all interior white regions.
3. **High-Precision Signed Distance Field (SDF):** Computes exact Euclidean distance from the boundary contour (`distance_transform_edt`).
4. **Smoothstep S-Curve Falloff (\(3t^2 - 2t^3\)):** Produces continuous, smooth alpha transitions.
5. **Color Defringing / Decontamination:** Extends the object's clean edge color into semi-transparent border pixels to completely eliminate background bleed.
6. **Lanczos Downsampling & Auto-Crop:** Resamples back to 1x resolution and tightly bounds the output.

---

## Quick Start / CLI Usage

### Requirements
```bash
pip install pillow numpy scipy
```

### Script Execution
The script is packaged at `scripts/remove-bg-smooth.py` (or within this skill at `scripts/remove-bg-smooth.py`):

```bash
# Single image
python3 scripts/remove-bg-smooth.py input.png output.png

# Batch process entire folder
python3 scripts/remove-bg-smooth.py --dir path/to/raw_images --out path/to/transparent_output

# Fine-tune sensitivity & softness
python3 scripts/remove-bg-smooth.py input.png output.png --threshold 25.0 --scale 4
```

---

## Options & Tuning Parameters

| Parameter | Default | Purpose |
| :--- | :--- | :--- |
| `--threshold` | `20.0` | Background color distance sensitivity (increase for noisy backgrounds, decrease for subtle tones). |
| `--scale` | `4` | Supersampling multiplier (4x provides crisp vector-grade anti-aliasing). |
| `--dir` | `None` | Process all `.png`, `.jpg`, `.webp` files in target directory. |
| `--out` | `None` | Output directory for batch results. |

---

## Programmatic Python Snippet

```python
from PIL import Image
import numpy as np
import scipy.ndimage as ndimage

def remove_bg_smooth(src_path, dst_path, scale=4, threshold=20.0):
    img = Image.open(src_path).convert("RGB")
    w, h = img.size
    high_img = img.resize((w * scale, h * scale), Image.Resampling.LANCZOS)
    arr = np.array(high_img).astype(np.float64)

    # Sample background color from outer border
    margin = 8 * scale
    corners = np.vstack([
        arr[0:margin, 0:margin, :3].reshape(-1, 3),
        arr[0:margin, -margin:, :3].reshape(-1, 3),
        arr[-margin:, 0:margin, :3].reshape(-1, 3),
        arr[-margin:, -margin:, :3].reshape(-1, 3)
    ])
    bg_color = np.median(corners, axis=0)

    # Seeded outer background detection
    diff = np.sqrt(np.sum((arr[:, :, :3] - bg_color) ** 2, axis=2))
    is_bg = diff < threshold
    labeled, _ = ndimage.label(is_bg, structure=ndimage.generate_binary_structure(2, 2))
    border_labels = np.unique(np.concatenate([labeled[0, :], labeled[-1, :], labeled[:, 0], labeled[:, -1]]))
    outer_bg = np.isin(labeled, border_labels[border_labels > 0])
    fg_mask = ~outer_bg

    # Signed distance field & smoothstep alpha
    dist_outside = ndimage.distance_transform_edt(outer_bg)
    dist_inside = ndimage.distance_transform_edt(fg_mask)
    sdf = dist_inside - dist_outside

    feather = 3.5 * scale
    inset = 1.2 * scale
    t = np.clip((sdf - inset + feather / 2.0) / feather, 0.0, 1.0)
    alpha = (t * t * (3.0 - 2.0 * t)) * 255.0

    # Defringing: extend clean foreground color
    solid_fg = sdf >= (inset + 1.0 * scale)
    if np.any(solid_fg):
        nearest = ndimage.distance_transform_edt(~solid_fg, return_distances=False, return_indices=True)
        decontaminated_rgb = arr[nearest[0], nearest[1], :3]
        blend = np.clip((sdf - inset + feather) / (feather * 1.5), 0.0, 1.0)[:, :, np.newaxis]
        final_rgb = arr * blend + decontaminated_rgb * (1.0 - blend)
    else:
        final_rgb = arr

    out_arr = np.zeros((h * scale, w * scale, 4), dtype=np.uint8)
    out_arr[:, :, :3] = np.clip(final_rgb, 0, 255).astype(np.uint8)
    out_arr[:, :, 3] = np.clip(alpha, 0, 255).astype(np.uint8)

    final_img = Image.fromarray(out_arr, mode="RGBA").resize((w, h), Image.Resampling.LANCZOS)
    final_img.save(dst_path, "PNG", optimize=True)
```
