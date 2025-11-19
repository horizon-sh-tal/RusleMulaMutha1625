import rasterio
import numpy as np

for year in [2014, 2015, 2016, 2017]:
    try:
        src = rasterio.open(f'temp/ndvi_{year}_raw.tif')
        data = src.read(1)
        valid = data[data != src.nodata]
        print(f'{year}: NDVI range [{valid.min():.3f}, {valid.max():.3f}], mean={valid.mean():.3f}, median={np.median(valid):.3f}')
        
        # Check for problematic values
        neg_count = np.sum(valid < -0.2)
        if neg_count > 0:
            print(f'  WARNING: {neg_count} pixels with NDVI < -0.2')
        
        src.close()
    except Exception as e:
        print(f'{year}: Error - {e}')
