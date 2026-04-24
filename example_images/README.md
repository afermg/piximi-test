# Example Images

## GDC H&E Slide (`gdc_slice.tif`)

1024x1024 center crop from a whole-slide H&E image (SVS format) from GDC.

### Reproduce from source

```bash
# Download the original SVS (~1.2 GB)
curl -O -J "https://api.gdc.cancer.gov/data/216feaac-8b0c-468d-991f-0412215e7a02"

# Extract
tar -xzf gdc_download_*.tar.gz

# Slice with openslide (pip install openslide-python openslide-bin)
python3 -c "
import openslide
slide = openslide.OpenSlide('1a71145d-b7a9-4324-a608-fb9023970990/HCM-STAN-0846-C20-11D-S1-HE.C37FA733-2832-4B11-8367-14547D2633B8.svs')
w, h = slide.dimensions
region = slide.read_region((w//2 - 512, h//2 - 512), 0, (1024, 1024)).convert('RGB')
region.save('gdc_slice.tif', format='TIFF')
slide.close()
"
```
