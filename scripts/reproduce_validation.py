"""One-command reproducible benchmark and demonstration report artifacts."""
from pathlib import Path
import csv
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from poroscope.engine import InspectionConfig, inspect, threshold_sensitivity  # noqa: E402
from poroscope.reporting import build_bundle, png_bytes  # noqa: E402
from poroscope.synthetic import SCENARIOS, make_sample, reference_mask_image  # noqa: E402
from poroscope.validation import benchmark  # noqa: E402


def main() -> None:
    dest = ROOT / "output"
    dest.mkdir(exist_ok=True)
    rows = benchmark()
    with (dest / "synthetic_benchmark.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for index, scenario in enumerate(SCENARIOS, start=1):
        sample = make_sample(scenario, seed=11)
        (dest / f"scenario_{index}_image.png").write_bytes(png_bytes(sample.image))
        (dest / f"scenario_{index}_truth.png").write_bytes(png_bytes(reference_mask_image(sample)))
    demo = make_sample("Challenging | uneven light", seed=11)
    conf = InspectionConfig()
    result = inspect(demo.image, conf)
    (dest / "example_inspection_record.zip").write_bytes(
        build_bundle(result, "Synthetic challenge sample", demo.image, threshold_sensitivity(demo.image, conf))
    )
    print(f"Reproduced {len(rows)} benchmark cases and demonstration evidence in: {dest}")
    print(f"Mean synthetic Dice: {sum(row['dice'] for row in rows) / len(rows):.4f}")
    print("These are synthetic metrics, not field accuracy or industrial material certification.")


if __name__ == "__main__":
    main()
