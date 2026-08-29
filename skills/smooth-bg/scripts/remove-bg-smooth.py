#!/usr/bin/env python3
"""
Smooth Transparent Image Background Remover & Anti-Aliasing Tool.

Uses 4x Supersampling, Connected-Component Background Floodfill,
Signed Distance Field (SDF) Edge Matting, and Color De-fringing to produce
ultra-smooth, high-quality transparent PNGs without jagged edges or white halos.

Requirements:
    pip install pillow numpy scipy

Usage:
    python3 remove_bg_smooth.py input.png [output.png]
    python3 remove_bg_smooth.py --dir /path/to/images/ [--out /path/to/output/]
"""

import sys
import os
import argparse
import numpy as np
from PIL import Image
import scipy.ndimage as ndimage


def remove_background_smooth(
    src_path: str,
    dst_path: str,
    scale: int = 4,
    color_threshold: float = 20.0,
    feather_width_px: float = 3.5,
    inset_shift_px: float = 1.2,
    crop_padding: int = 8,
):
    """
    Removes background and produces smooth, anti-aliased RGBA cutout.

    :param src_path: Path to input image (RGB or RGBA)
    :param dst_path: Path to save transparent PNG
    :param scale: Supersampling factor (default 4x for vector-like edges)
    :param color_threshold: Distance threshold for identifying background color
    :param feather_width_px: Soft transition width in supersampled space
    :param inset_shift_px: Inset shift in 1x space to cut cleanly into border stroke
    :param crop_padding: Padding around tight bounding box
    """
    img = Image.open(src_path).convert("RGB")
    w, h = img.size

    # 1. Supersample 4x using high-quality Lanczos resampling
    high_img = img.resize((w * scale, h * scale), Image.Resampling.LANCZOS)
    arr = np.array(high_img).astype(np.float64)

    # 2. Sample outer corner regions to get true background color
    margin = 8 * scale
    corners = np.vstack([
        arr[0:margin, 0:margin, :3].reshape(-1, 3),
        arr[0:margin, -margin:, :3].reshape(-1, 3),
        arr[-margin:, 0:margin, :3].reshape(-1, 3),
        arr[-margin:, -margin:, :3].reshape(-1, 3),
    ])
    bg_color = np.median(corners, axis=0)

    # 3. Calculate Euclidean color distance from background
    diff = np.sqrt(np.sum((arr[:, :, :3] - bg_color) ** 2, axis=2))

    # 4. Connected-component floodfill starting strictly from outer border
    # (Prevents erasing white details inside the foreground object like eyes/teeth)
    is_bg = diff < color_threshold
    structure = ndimage.generate_binary_structure(2, 2)
    labeled, _ = ndimage.label(is_bg, structure=structure)

    border_labels = np.unique(
        np.concatenate([
            labeled[0, :],
            labeled[-1, :],
            labeled[:, 0],
            labeled[:, -1],
        ])
    )
    border_labels = border_labels[border_labels > 0]
    outer_bg = np.isin(labeled, border_labels)
    fg_mask = ~outer_bg

    # 5. High precision Signed Distance Field (SDF) in supersampled space
    dist_outside = ndimage.distance_transform_edt(outer_bg)
    dist_inside = ndimage.distance_transform_edt(fg_mask)
    sdf = dist_inside - dist_outside

    # 6. Smoothstep (Hermite S-curve 3t^2 - 2t^3) alpha falloff
    feather_scaled = feather_width_px * scale
    inset_scaled = inset_shift_px * scale

    t = np.clip(
        (sdf - inset_scaled + feather_scaled / 2.0) / feather_scaled, 0.0, 1.0
    )
    alpha = (t * t * (3.0 - 2.0 * t)) * 255.0

    # 7. Color Decontamination / Defringing:
    # Extends the object's clean edge color outward to eliminate white halos/fringes
    solid_fg = sdf >= (inset_scaled + 1.0 * scale)
    if np.any(solid_fg):
        nearest_coords = ndimage.distance_transform_edt(
            ~solid_fg, return_distances=False, return_indices=True
        )
        decontaminated_rgb = arr[nearest_coords[0], nearest_coords[1], :3]
        blend_weight = np.clip(
            (sdf - inset_scaled + feather_scaled) / (feather_scaled * 1.5),
            0.0,
            1.0,
        )[:, :, np.newaxis]
        final_rgb = arr * blend_weight + decontaminated_rgb * (
            1.0 - blend_weight
        )
    else:
        final_rgb = arr

    out_4x = np.zeros((h * scale, w * scale, 4), dtype=np.uint8)
    out_4x[:, :, :3] = np.clip(final_rgb, 0, 255).astype(np.uint8)
    out_4x[:, :, 3] = np.clip(alpha, 0, 255).astype(np.uint8)

    img_4x = Image.fromarray(out_4x, mode="RGBA")

    # 8. Downsample back to target 1x resolution with Lanczos Anti-Aliasing
    final_img = img_4x.resize((w, h), Image.Resampling.LANCZOS)

    # 9. Crop to tight bounding box with padding
    bbox = final_img.getbbox()
    if bbox:
        crop_box = (
            max(0, bbox[0] - crop_padding),
            max(0, bbox[1] - crop_padding),
            min(w, bbox[2] + crop_padding),
            min(h, bbox[3] + crop_padding),
        )
        final_img = final_img.crop(crop_box)

    os.makedirs(os.path.dirname(os.path.abspath(dst_path)), exist_ok=True)
    final_img.save(dst_path, "PNG", optimize=True)
    print(
        f"✓ Successfully processed: {os.path.basename(src_path)} -> {dst_path} ({final_img.size})"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Ultra-Smooth Background Remover & Edge Anti-Aliasing"
    )
    parser.add_argument("input", nargs="?", help="Input image path or directory")
    parser.add_argument("output", nargs="?", help="Output image path or directory")
    parser.add_argument(
        "--dir", help="Process all images in directory", default=None
    )
    parser.add_argument(
        "--out", help="Output directory for batch processing", default=None
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=20.0,
        help="Background color sensitivity threshold (default: 20.0)",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=4,
        help="Supersampling factor (default: 4)",
    )
    args = parser.parse_args()

    target_dir = args.dir or (args.input if args.input and os.path.isdir(args.input) else None)

    if target_dir:
        out_dir = args.out or args.output or target_dir
        extensions = (".png", ".jpg", ".jpeg", ".webp")
        files = [
            f
            for f in os.listdir(target_dir)
            if f.lower().endswith(extensions) and not f.startswith(".")
        ]
        print(f"Processing {len(files)} images in {target_dir}...")
        for f in files:
            src = os.path.join(target_dir, f)
            name, _ = os.path.splitext(f)
            dst = os.path.join(out_dir, f"{name}.png")
            remove_background_smooth(
                src, dst, scale=args.scale, color_threshold=args.threshold
            )
    elif args.input:
        dst = (
            args.output
            if args.output
            else os.path.splitext(args.input)[0] + "_transparent.png"
        )
        remove_background_smooth(
            args.input, dst, scale=args.scale, color_threshold=args.threshold
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
